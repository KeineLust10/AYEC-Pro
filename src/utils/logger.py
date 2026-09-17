import logging
import os
import sys
import tempfile
from logging.handlers import RotatingFileHandler
import traceback
from src.utils.path_helper import PathHelper

class NotificationHandler(logging.Handler):
    """
    Custom logging handler that sends errors to an in-app notification system.
    """
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def emit(self, record):
        if record.levelno >= logging.ERROR:
            try:
                msg = self.format(record)
                # Usually we want a shorter message for notifications
                short_msg = record.getMessage()
                self.callback(short_msg, "error")
            except Exception:
                self.handleError(record)

def setup_logger(name="AYECProLogger", log_file=None, level=logging.INFO):
    """
    Sets up a logger with rotating file handler and console handler.
    Configures the root logger if name is "AYECProLogger".
    """
    if log_file is None:
        log_file = PathHelper.get_log_path()
    
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s')
    
    # Console Handler
    console_handler = None
    if sys.stdout is not None:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)

    file_handler = None
    file_candidates = [log_file]
    temp_fallback = os.path.join(tempfile.gettempdir(), "ayecpro_app_debug.log")
    if temp_fallback not in file_candidates:
        file_candidates.append(temp_fallback)

    for candidate in file_candidates:
        try:
            candidate_dir = os.path.dirname(candidate)
            if candidate_dir:
                os.makedirs(candidate_dir, exist_ok=True)
            file_handler = RotatingFileHandler(
                candidate,
                maxBytes=5 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            break
        except Exception:
            file_handler = None

    if name == "AYECProLogger":
        # Configure Root Logger to catch everything from all libraries
        root = logging.getLogger()
        root.setLevel(level)
        if not root.handlers:
            if file_handler is not None:
                root.addHandler(file_handler)
            if console_handler is not None:
                root.addHandler(console_handler)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False
    
    # Add handlers only if they don't exist to avoid double logging
    if not logger.handlers:
        if file_handler is not None:
            logger.addHandler(file_handler)
        if console_handler is not None:
            logger.addHandler(console_handler)
    
    return logger

# Create a global instance
logger = setup_logger()

def send_telemetry_to_server(error_msg, stack_trace):
    def worker():
        try:
            import requests
            import os
            import platform
            from src.utils.path_helper import PathHelper
            import sqlite3
            
            db_path = PathHelper.get_db_path("ayecpro.db")
            tenant_id = "Unknown"
            url = os.environ.get("AYEC_WEB_SYNC_URL", "https://api.ayecpro.com")
            
            if os.path.exists(db_path):
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT value FROM settings WHERE key='web_sync_tenant_id'")
                    row = cursor.fetchone()
                    if row:
                        tenant_id = row[0]
                    cursor.execute("SELECT value FROM settings WHERE key='web_sync_url'")
                    row = cursor.fetchone()
                    if row:
                        url = row[0]
                    conn.close()
                except Exception:
                    pass
            
            payload = {
                "tenant_id": tenant_id,
                "version": "v1.0.0",
                "os_info": f"{platform.system()} {platform.release()}",
                "error_message": error_msg,
                "stack_trace": stack_trace
            }
            requests.post(f"{url.rstrip('/')}/api/control/telemetry/errors", json=payload, timeout=5)
        except Exception:
            pass

    import threading
    t = threading.Thread(target=worker, daemon=True)
    t.start()


def log_exception(exc_type, exc_value, exc_traceback):
    """
    Custom exception hook to log unhandled exceptions.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    stack_trace = "".join(tb_lines)
    logger.critical("Uncaught Exception:", exc_info=(exc_type, exc_value, exc_traceback))
    
    try:
        send_telemetry_to_server(str(exc_value), stack_trace)
    except Exception:
        pass

def install_exception_hook():
    """
    Installs the custom exception hook.
    """
    sys.excepthook = log_exception
