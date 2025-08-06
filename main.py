"""
Flask Server for BasoKa Process Management
Provides API endpoints for managing and monitoring a checker process via Telegram bot.
(Simplified version without threading)
"""

import os
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from flask import Flask, jsonify, request


# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/flask_app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Config:
    """Application configuration"""
    SUCCESS_FILE = Path(r"D:\Amir\Code\PNSHit\psn_hit_check\reports_json\successful_logins.json")
    RETRY_FILE = Path(r"D:\Amir\Code\PNSHit\psn_hit_check\reports_json\retry_accounts.json")
    FAILED_FILE = Path(r"D:\Amir\Code\PNSHit\psn_hit_check\reports_json\failed_logins.json")
    MAIN_SCRIPT = r"D:\Amir\Code\PNSHit\psn_hit_check\main.py"
    LOG_FILE = Path(r"D:\Amir\Code\PNSHit\psn_hit_check\logs\login_process.log")
    DEFAULT_RECENT_LIMIT = 10
    LOG_TAIL_LINES = 50


class ProcessManager:
    """Manages the checker process lifecycle without threads."""

    _process = None # Class attribute to hold the single process instance

    def _cleanup_process(self):
        """Resets process state."""
        ProcessManager._process = None
        logger.info("Process has been cleaned up.")

    def is_running(self) -> bool:
        """Check if the process is currently running."""
        if ProcessManager._process is None:
            return False

        # poll() is non-blocking. It returns None if the process is running,
        # or the exit code if it has finished.
        if ProcessManager._process.poll() is not None:
            logger.info(f"Process found to be finished with exit code: {ProcessManager._process.returncode}")
            self._cleanup_process()
            return False

        return True

    def start(self) -> Dict[str, Any]:
        """Start the checker process."""
        if self.is_running():
            logger.warning("Attempt to start already running process")
            return {"status": "already_running", "message": "Process is already running"}

        try:
            env = os.environ.copy()
            env.pop('SELENIUM_HEADLESS', None)

            # Popen is non-blocking and starts the process in the background.
            ProcessManager._process = subprocess.Popen(
                ["uv", "run", "python", Config.MAIN_SCRIPT],
                stdout=open('logs/process_stdout.log', 'a'),
                stderr=open('logs/process_stderr.log', 'a'),
                text=True,
                env=env
            )

            pid = ProcessManager._process.pid
            logger.info(f"Started checker process with PID: {pid}")
            return {"status": "started", "pid": pid}

        except Exception as e:
            logger.error(f"Failed to start process: {e}")
            self._cleanup_process()
            return {"status": "error", "message": str(e)}

    def stop(self) -> Dict[str, Any]:
        """Stop the checker process."""
        if not self.is_running():
            logger.warning("Attempt to stop non-running process")
            return {"status": "not_running", "message": "Process is not running"}

        try:
            pid = ProcessManager._process.pid
            logger.info(f"Attempting to stop process with PID: {pid}")

            # Use taskkill for a more forceful stop on Windows.
            # check=False prevents an exception if the process is already gone.
            result = subprocess.run(
                ['taskkill', '/F', '/T', '/PID', str(pid)],
                capture_output=True, text=True, check=False
            )

            # Log an error only if taskkill failed for an unexpected reason.
            if result.returncode != 0 and "not found" not in result.stderr.lower():
                logger.error(f"taskkill failed for PID {pid}. Stderr: {result.stderr}")
                return {"status": "error", "message": f"taskkill failed: {result.stderr}"}

            self._cleanup_process()
            logger.info(f"Successfully stopped process tree for PID {pid}.")
            return {"status": "stopped"}

        except Exception as e:
            logger.error(f"Failed to stop process: {e}")
            return {"status": "error", "message": str(e)}

    def get_process_info(self) -> Dict[str, Any]:
        """Get detailed process information."""
        if self.is_running():
            return {
                "running": True,
                "pid": ProcessManager._process.pid,
                "status": "running"
            }

        return {
            "running": False,
            "pid": None,
            "status": "stopped"
        }


class DataManager:
    """Manages JSON data files for login tracking"""

    @staticmethod
    def read_json_file(file_path: Path) -> List[Dict[str, Any]]:
        """Safely read JSON data from file"""
        try:
            if not file_path.exists():
                logger.debug(f"File {file_path} does not exist, returning empty list")
                return []

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error reading {file_path}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return []

    @staticmethod
    def get_recent_items(data: List[Dict[str, Any]], limit: int = None) -> List[Dict[str, Any]]:
        """Get most recent items sorted by timestamp"""
        if limit is None:
            limit = Config.DEFAULT_RECENT_LIMIT

        try:
            return sorted(
                data,
                key=lambda x: x.get("timestamp", ""),
                reverse=True
            )[:limit]
        except Exception as e:
            logger.error(f"Error sorting data: {e}")
            return data[:limit] if data else []

    @classmethod
    def get_login_statistics(cls) -> Dict[str, Any]:
        """Get comprehensive login statistics"""
        try:
            success_data = cls.read_json_file(Config.SUCCESS_FILE)
            failed_data = cls.read_json_file(Config.FAILED_FILE)
            retry_data = cls.read_json_file(Config.RETRY_FILE)
            return {
                "success_count": len(success_data),
                "failed_count": len(failed_data),
                "retry_count": len(retry_data),
                "total_attempts": len(success_data) + len(failed_data) + len(retry_data),
                "latest_success": cls.get_recent_items(success_data),
                "latest_failures": cls.get_recent_items(failed_data),
                "latest_retries": cls.get_recent_items(retry_data),
                "last_updated": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting login statistics: {e}")
            return {
                "success_count": 0,
                "failed_count": 0,
                "retry_count": 0,
                "total_attempts": 0,
                "latest_success": [],
                "latest_failures": [],
                "latest_retries": [],
                "last_updated": datetime.now().isoformat(),
                "error": str(e)
            }


class LogManager:
    """Manages application logs"""

    @staticmethod
    def get_recent_logs(lines: int = None) -> Dict[str, Any]:
        """Get recent log entries"""
        if lines is None:
            lines = Config.LOG_TAIL_LINES

        try:
            if not Config.LOG_FILE.exists():
                logger.warning(f"Log file {Config.LOG_FILE} not found")
                return {
                    "log": "Log file not found",
                    "lines_count": 0,
                    "file_exists": False
                }

            with open(Config.LOG_FILE, "r", encoding="utf-8") as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

            return {
                "log": "".join(recent_lines),
                "lines_count": len(recent_lines),
                "total_lines": len(all_lines),
                "file_exists": True
            }

        except Exception as e:
            logger.error(f"Error reading log file: {e}")
            return {
                "log": f"Error reading log file: {str(e)}",
                "lines_count": 0,
                "error": str(e)
            }


# Initialize managers
process_manager = ProcessManager()
data_manager = DataManager()
log_manager = LogManager()

# Create Flask app
app = Flask(__name__)


def ensure_directories():
    """Ensure all required directories exist"""
    Config.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    Config.SUCCESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    Config.FAILED_FILE.parent.mkdir(parents=True, exist_ok=True)
    Path('logs').mkdir(exist_ok=True) # For stdout/stderr logs


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "error": "Endpoint not found",
        "message": "The requested endpoint does not exist"
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred"
    }), 500


# API Endpoints
@app.route("/status", methods=["GET"])
def get_status():
    """Get comprehensive system status including login statistics and process info"""
    logger.info("Status endpoint called")
    try:
        login_stats = data_manager.get_login_statistics()
        process_info = process_manager.get_process_info()
        response = {
            **login_stats,
            "process": process_info,
            "server_status": "healthy"
        }
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error in get_status: {e}", exc_info=True)
        return jsonify({"error": "Failed to get status", "message": str(e)}), 500


@app.route("/start", methods=["POST", "GET"])
def start_checker():
    """Start the checker process"""
    if request.method == "GET":
        return jsonify({"message": "To start the checker, send a POST request to this endpoint"})

    result = process_manager.start()
    status_code = 200 if result["status"] in ["started", "already_running"] else 400
    logger.info(f"Start request: {result}")
    return jsonify(result), status_code


@app.route("/stop", methods=["POST"])
def stop_checker():
    """Stop the checker process"""
    result = process_manager.stop()
    status_code = 200 if result["status"] in ["stopped", "not_running"] else 400
    logger.info(f"Stop request: {result}")
    return jsonify(result), status_code


@app.route("/is_running", methods=["GET"])
def is_running():
    """Check if the checker process is running"""
    return jsonify(process_manager.get_process_info())


@app.route("/log", methods=["GET"])
def get_log():
    """Get recent log entries"""
    try:
        lines = request.args.get('lines', type=int)
        log_data = log_manager.get_recent_logs(lines)
        return jsonify(log_data)
    except Exception as e:
        logger.error(f"Error in get_log: {e}")
        return jsonify({"log": f"Error retrieving logs: {str(e)}", "error": str(e)}), 500


if __name__ == "__main__":
    ensure_directories()
    logger.info("Starting BasoKa Flask Reporter Server (Simplified Version)")

    try:
        app.run(
            host="0.0.0.0",
            port=8000,
            debug=True,
            threaded=True # Flask's threaded=True is fine, it handles requests in threads
        )
    except Exception as e:
        logger.error(f"Failed to start Flask server: {e}")
        raise
