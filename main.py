import os
import sys
import json
import logging
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import deque
import psutil


from flask import Flask, jsonify, request

# --- Basic Setup ---
# Determine the absolute path of the project's root directory.
# This makes the script portable and runnable from any location.
APP_ROOT = Path(__file__).parent.resolve()

# --- Logging Configuration ---
# Create a 'logs' directory if it doesn't exist.
LOGS_DIR = APP_ROOT / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / 'flask_app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# --- Application Configuration ---
class Config:

    # --- Paths for Data Files ---
    REPORTS_DIR = APP_ROOT / 'reports_json'
    SUCCESS_FILE = REPORTS_DIR / 'successful_logins.json'
    RETRY_FILE = REPORTS_DIR / 'retry_accounts.json'
    FAILED_FILE = REPORTS_DIR / 'failed_logins.json'

    # --- Path for the target script to run ---
    # This robustly points to a sibling directory of the app's folder.
    MAIN_SCRIPT = APP_ROOT.parent / 'psn_hit_check' / 'main.py'

    # --- Paths for Log Files ---
    PROCESS_LOG_FILE = LOGS_DIR / 'login_process.log'
    PROCESS_STDOUT_LOG = LOGS_DIR / 'process_stdout.log'
    PROCESS_STDERR_LOG = LOGS_DIR / 'process_stderr.log'

    # --- Default Values ---
    DEFAULT_RECENT_LIMIT = 10
    LOG_TAIL_LINES = 50


class ProcessStatus:
    STARTED = "started"
    STOPPED = "stopped"
    RUNNING = "running"
    ALREADY_RUNNING = "already_running"
    NOT_RUNNING = "not_running"
    ERROR = "error"



class ProcessManager:
    _process: Optional[subprocess.Popen] = None
    _lock = threading.Lock()

    def _cleanup_process(self):
        ProcessManager._process = None
        logger.info("Process reference has been cleaned up.")

    def is_running(self) -> bool:
        if ProcessManager._process is None:
            return False

        # poll() is non-blocking. It returns None if running, or an exit code if finished.
        if ProcessManager._process.poll() is not None:
            logger.info(f"Process found to be finished with exit code: {ProcessManager._process.returncode}")
            self._cleanup_process()
            return False

        return True

    def start(self) -> Dict[str, Any]:
        with self._lock:
            if self.is_running():
                logger.warning("Attempted to start an already running process.")
                return {"status": ProcessStatus.ALREADY_RUNNING, "message": "Process is already running."}

            try:
                if not Config.MAIN_SCRIPT.exists():
                    error_msg = f"Main script not found at {Config.MAIN_SCRIPT}"
                    logger.error(error_msg)
                    return {"status": ProcessStatus.ERROR, "message": error_msg}

                logger.info(f"Starting process: {Config.MAIN_SCRIPT}")

                command = [sys.executable, str(Config.MAIN_SCRIPT)]

                ProcessManager._process = subprocess.Popen(
                    command,
                    stdout=open(Config.PROCESS_STDOUT_LOG, 'a', encoding='utf-8'),
                    stderr=open(Config.PROCESS_STDERR_LOG, 'a', encoding='utf-8'),
                    text=True
                )

                pid = ProcessManager._process.pid
                logger.info(f"Successfully started checker process with PID: {pid}")
                return {"status": ProcessStatus.STARTED, "pid": pid}

            except Exception as e:
                logger.critical(f"Failed to start process: {e}", exc_info=True)
                self._cleanup_process()
                return {"status": ProcessStatus.ERROR, "message": f"An unexpected error occurred: {e}"}

    def stop(self) -> Dict[str, Any]:
        with self._lock:
            if not self.is_running():
                logger.warning("Attempted to stop a non-running process.")
                return {"status": ProcessStatus.NOT_RUNNING, "message": "Process is not running."}

            try:
                pid = ProcessManager._process.pid
                logger.info(f"Attempting to terminate process tree for PID: {pid}")

                parent = psutil.Process(pid)
                children = parent.children(recursive=True)

                logger.info(f"Found {len(children)} child processes to terminate.")

                for child in children:
                    try:
                        child.terminate()
                        logger.info(f"Terminated child process {child.pid}")
                    except psutil.NoSuchProcess:
                        logger.warning(f"Child process {child.pid} already gone.")

                gone, alive = psutil.wait_procs(children, timeout=3)
                for p in alive:
                    logger.warning(f"Child process {p.pid} did not terminate, killing it.")
                    p.kill()

                try:
                    parent.terminate()
                    logger.info(f"Terminated main process {pid}")
                    parent.wait(timeout=5)
                except psutil.NoSuchProcess:
                     logger.warning(f"Main process {pid} already gone.")
                except psutil.TimeoutExpired:
                    logger.warning(f"Main process {pid} did not terminate, killing it.")
                    parent.kill()
                    parent.wait()

                self._cleanup_process()
                return {"status": ProcessStatus.STOPPED}

            except psutil.NoSuchProcess:
                logger.warning(f"Process with PID {pid} not found. It may have already finished.")
                self._cleanup_process()
                return {"status": ProcessStatus.STOPPED, "message": "Process was already gone."}
            except Exception as e:
                logger.critical(f"An error occurred while stopping process tree: {e}", exc_info=True)
                return {"status": ProcessStatus.ERROR, "message": f"An unexpected error occurred: {e}"}

    def get_process_info(self) -> Dict[str, Any]:
        with self._lock:
            if self.is_running():
                return {
                    "running": True,
                    "pid": ProcessManager._process.pid,
                    "status": ProcessStatus.RUNNING
                }

            return {
                "running": False,
                "pid": None,
                "status": ProcessStatus.STOPPED
            }


class DataManager:

    @staticmethod
    def read_json_file(file_path: Path) -> List[Dict[str, Any]]:
        if not file_path.exists():
            return []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error reading or parsing JSON from {file_path}: {e}")
            return []

    @staticmethod
    def get_recent_items(data: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        if not data:
            return []
        try:
            return sorted(
                data,
                key=lambda x: x.get("timestamp", ""),
                reverse=True
            )[:limit]
        except Exception as e:
            logger.error(f"Failed to sort data for recent items: {e}")
            # Return a simple slice as a fallback.
            return data[:limit]

    @classmethod
    def get_login_statistics(cls) -> Dict[str, Any]:
        try:
            success_data = cls.read_json_file(Config.SUCCESS_FILE)
            failed_data = cls.read_json_file(Config.FAILED_FILE)
            retry_data = cls.read_json_file(Config.RETRY_FILE)
            limit = Config.DEFAULT_RECENT_LIMIT

            return {
                "success_count": len(success_data),
                "failed_count": len(failed_data),
                "retry_count": len(retry_data),
                "total_attempts": len(success_data) + len(failed_data) + len(retry_data),
                "latest_success": cls.get_recent_items(success_data, limit),
                "latest_failures": cls.get_recent_items(failed_data, limit),
                "latest_retries": cls.get_recent_items(retry_data, limit),
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error compiling login statistics: {e}", exc_info=True)
            return {"error": "Failed to retrieve login statistics."}


class LogManager:

    @staticmethod
    def get_recent_logs(lines: int) -> Dict[str, Any]:
        log_file = Config.PROCESS_LOG_FILE
        if not log_file.exists():
            logger.warning(f"Log file not found: {log_file}")
            return {"log": "Log file not found.", "lines_count": 0}

        try:
            with open(log_file, "r", encoding="utf-8") as f:
                log_lines = deque(f, lines)
            return {
                "log": "".join(log_lines),
                "lines_count": len(log_lines)
            }
        except IOError as e:
            logger.error(f"Error reading log file {log_file}: {e}")
            return {"log": f"Error reading log file: {e}", "lines_count": 0, "error": str(e)}


app = Flask(__name__)
process_manager = ProcessManager()
data_manager = DataManager()
log_manager = LogManager()


def ensure_directories():
    try:
        Config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("Verified that all necessary directories exist.")
    except Exception as e:
        logger.critical(f"Could not create necessary directories: {e}", exc_info=True)
        raise

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not Found", "message": "The requested endpoint does not exist."}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal Server Error: {error}", exc_info=True)
    return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred on the server."}), 500


# --- API Endpoints ---
@app.route("/status", methods=["GET"])
def get_status():
    logger.info("GET /status - Request received")
    try:
        login_stats = data_manager.get_login_statistics()
        process_info = process_manager.get_process_info()
        response = {
            "server_status": "healthy",
            "process_info": process_info,
            "login_stats": login_stats,
            "timestamp": datetime.now().isoformat()
        }
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error in /status endpoint: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve status"}), 500


@app.route("/start", methods=["POST"])
def start_checker():
    logger.info("POST /start - Request received")
    result = process_manager.start()
    status_code = 200 if result["status"] in [ProcessStatus.STARTED, ProcessStatus.ALREADY_RUNNING] else 400
    return jsonify(result), status_code


@app.route("/stop", methods=["POST"])
def stop_checker():
    logger.info("POST /stop - Request received")
    result = process_manager.stop()
    status_code = 200 if result["status"] in [ProcessStatus.STOPPED, ProcessStatus.NOT_RUNNING] else 400
    return jsonify(result), status_code


@app.route("/log", methods=["GET"])
def get_log():
    logger.info("GET /log - Request received")
    try:
        lines_str = request.args.get('lines', str(Config.LOG_TAIL_LINES))
        if not lines_str.isdigit() or int(lines_str) <= 0:
            return jsonify({"error": "Invalid 'lines' parameter. Must be a positive integer."}), 400

        lines = int(lines_str)
        log_data = log_manager.get_recent_logs(lines)
        return jsonify(log_data)
    except Exception as e:
        logger.error(f"Error in /log endpoint: {e}", exc_info=True)
        return jsonify({"error": f"Failed to retrieve logs: {e}"}), 500


# --- Main Execution ---
if __name__ == "__main__":
    ensure_directories()
    try:
        app.run(host="0.0.0.0", port=8000, debug=False, threaded=True)
    except Exception as e:
        logger.critical(f"Failed to start Flask server: {e}", exc_info=True)
        sys.exit(1)
