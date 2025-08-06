"""
Flask Server for BasoKa Process Management
Provides API endpoints for managing and monitoring a checker process via Telegram bot.
"""

import os
import json
import logging
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from flask import Flask, jsonify, request


# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/flask_app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Config:
    """Application configuration"""
    
    # File paths - Using raw strings to avoid escape sequence warnings
    SUCCESS_FILE = Path(r"D:\Amir\Code\PNSHit\psn_hit_check\reports_json\successful_logins.json")
    FAILED_FILE = Path(r"D:\Amir\Code\PNSHit\psn_hit_check\reports_json\failed_logins.json")
    MAIN_SCRIPT = r"D:\Amir\Code\PNSHit\psn_hit_check\main.py"  # Changed from main.py to avoid conflicts
    LOG_FILE = Path(r"D:\Amir\Code\PNSHit\psn_hit_check\logs\login_process.log")
    
    # Process settings
    DEFAULT_RECENT_LIMIT = 5
    LOG_TAIL_LINES = 50


class ProcessManager:
    """Manages the checker process lifecycle"""
    
    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
    
    def is_running(self) -> bool:
        """Check if the process is currently running"""
        with self._lock:
            return self._process is not None and self._process.poll() is None
    
    def start(self) -> Dict[str, Any]:
        """Start the checker process"""
        with self._lock:
            if self.is_running():
                logger.warning("Attempt to start already running process")
                return {"status": "already_running", "message": "Process is already running"}
            
            try:
                # Set environment variables for headless operation
                env = os.environ.copy()
                env['DISPLAY'] = ':99'  # Virtual display for Linux
                env['SELENIUM_HEADLESS'] = 'true'  # Custom flag for your bot
                
                self._process = subprocess.Popen(
                    ["python", Config.MAIN_SCRIPT],
                    stdout=subprocess.PIPE,  # Capture output for logging
                    stderr=subprocess.PIPE,  # Capture errors for logging
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    env=env  # Pass environment variables
                )
                logger.info(f"Started checker process with PID: {self._process.pid}")
                return {"status": "started", "pid": self._process.pid}
            
            except Exception as e:
                logger.error(f"Failed to start process: {e}")
                return {"status": "error", "message": str(e)}
    
    def stop(self) -> Dict[str, Any]:
        """Stop the checker process"""
        with self._lock:
            if not self.is_running():
                logger.warning("Attempt to stop non-running process")
                return {"status": "not_running", "message": "Process is not running"}
            
            try:
                self._process.terminate()
                # Wait a bit for graceful shutdown
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning("Process didn't terminate gracefully, killing it")
                    self._process.kill()
                
                logger.info("Stopped checker process")
                return {"status": "stopped"}
            
            except Exception as e:
                logger.error(f"Failed to stop process: {e}")
                return {"status": "error", "message": str(e)}
    
    def get_process_info(self) -> Dict[str, Any]:
        """Get detailed process information"""
        with self._lock:
            # Check if running without calling is_running() to avoid deadlock
            running = self._process is not None and self._process.poll() is None
            
            if not running:
                return {
                    "running": False,
                    "pid": None,
                    "status": "stopped"
                }
            
            return {
                "running": True,
                "pid": self._process.pid,
                "status": "running"
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
            
            return {
                "success_count": len(success_data),
                "failed_count": len(failed_data),
                "total_attempts": len(success_data) + len(failed_data),
                "latest_success": cls.get_recent_items(success_data),
                "latest_failures": cls.get_recent_items(failed_data),
                "last_updated": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error getting login statistics: {e}")
            return {
                "success_count": 0,
                "failed_count": 0,
                "total_attempts": 0,
                "latest_success": [],
                "latest_failures": [],
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
        logger.debug("Getting login statistics...")
        login_stats = data_manager.get_login_statistics()
        logger.debug(f"Login stats: {login_stats}")
        
        logger.debug("Getting process info...")
        process_info = process_manager.get_process_info()
        logger.debug(f"Process info: {process_info}")
        
        response = {
            **login_stats,
            "process": process_info,
            "server_status": "healthy"
        }
        
        logger.info("Status request completed successfully")
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error in get_status: {e}", exc_info=True)
        return jsonify({
            "error": "Failed to get status",
            "message": str(e)
        }), 500


@app.route("/start", methods=["POST"])
def start_checker():
    """Start the checker process"""
    try:
        result = process_manager.start()
        status_code = 200 if result["status"] in ["started"] else 400
        
        logger.info(f"Start request: {result}")
        return jsonify(result), status_code
    
    except Exception as e:
        logger.error(f"Error in start_checker: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/stop", methods=["POST"])
def stop_checker():
    """Stop the checker process"""
    try:
        result = process_manager.stop()
        status_code = 200 if result["status"] in ["stopped"] else 400
        
        logger.info(f"Stop request: {result}")
        return jsonify(result), status_code
    
    except Exception as e:
        logger.error(f"Error in stop_checker: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/is_running", methods=["GET"])
def is_running():
    """Check if the checker process is running"""
    try:
        process_info = process_manager.get_process_info()
        
        logger.debug(f"Is running check: {process_info}")
        return jsonify(process_info)
    
    except Exception as e:
        logger.error(f"Error in is_running: {e}")
        return jsonify({
            "running": False,
            "error": str(e)
        }), 500


@app.route("/log", methods=["GET"])
def get_log():
    """Get recent log entries"""
    try:
        # Get optional lines parameter from query string
        lines = request.args.get('lines', type=int)
        log_data = log_manager.get_recent_logs(lines)
        
        logger.debug(f"Log request completed, returned {log_data.get('lines_count', 0)} lines")
        return jsonify(log_data)
    
    except Exception as e:
        logger.error(f"Error in get_log: {e}")
        return jsonify({
            "log": f"Error retrieving logs: {str(e)}",
            "error": str(e)
        }), 500


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    })


if __name__ == "__main__":
    # Ensure required directories exist
    ensure_directories()
    
    logger.info("Starting BasoKa Flask Reporter Server")
    logger.info(f"Success file: {Config.SUCCESS_FILE.absolute()}")
    logger.info(f"Failed file: {Config.FAILED_FILE.absolute()}")
    logger.info(f"Log file: {Config.LOG_FILE.absolute()}")
    
    try:
        app.run(
            host="0.0.0.0", 
            port=8000,
            debug=True,  # Enable debug mode
            threaded=True
        )
    except Exception as e:
        logger.error(f"Failed to start Flask server: {e}")
        raise
        raise
