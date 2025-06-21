import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional

class LoggingManager:
    def __init__(self, log_file_path: str, max_bytes: int = 5242880, backup_count: int = 5):
        """Initialize the logging manager.
        
        Args:
            log_file_path: Path to the log file
            max_bytes: Maximum size of log file before rotation (default 5MB)
            backup_count: Number of backup files to keep (default 5)
        """
        self.log_file_path = log_file_path
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self._configure_logging()

    def _configure_logging(self):
        """Configure the logging system with enhanced formatting."""
        # Create logs directory if it doesn't exist
        os.makedirs(os.path.dirname(self.log_file_path), exist_ok=True)

        # Create a custom formatter
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(module)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Configure file handler with rotation
        file_handler = RotatingFileHandler(
            self.log_file_path,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count
        )
        file_handler.setFormatter(formatter)

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # Remove any existing handlers to avoid duplicates
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        root_logger.addHandler(file_handler)

    def log_startup(self, app_version: str):
        """Log application startup information."""
        logging.info("=" * 50)
        logging.info(f"Application Starting - Version {app_version}")
        logging.info(f"Log file: {self.log_file_path}")
        logging.info(f"Startup time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logging.info("=" * 50)

    def log_shutdown(self):
        """Log application shutdown information."""
        logging.info("=" * 50)
        logging.info("Application Shutting Down")
        logging.info(f"Shutdown time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logging.info("=" * 50)

    def log_error(self, error: Exception, context: str = ""):
        """Log an error with full traceback and context."""
        if context:
            logging.error(f"Error in {context}:")
        logging.exception(error)

    def log_database_operation(self, operation: str, details: str, success: bool):
        """Log database operations with consistent formatting."""
        status = "SUCCESS" if success else "FAILED"
        logging.info(f"Database Operation [{status}] - {operation}: {details}")

    def log_user_action(self, user: str, action: str, details: Optional[str] = None):
        """Log user actions with consistent formatting."""
        log_msg = f"User Action: {user} - {action}"
        if details:
            log_msg += f" - {details}"
        logging.info(log_msg)

    def log_system_event(self, event_type: str, details: str):
        """Log system events with consistent formatting."""
        logging.info(f"System Event [{event_type}]: {details}")

    def log_security_event(self, event_type: str, user: str, details: str):
        """Log security-related events with consistent formatting."""
        logging.warning(f"Security Event [{event_type}] - User: {user} - {details}")

    def log_printer_operation(self, operation: str, printer_ip: str, success: bool, details: Optional[str] = None):
        """Log printer operations with consistent formatting."""
        status = "SUCCESS" if success else "FAILED"
        log_msg = f"Printer Operation [{status}] - {operation} - Printer: {printer_ip}"
        if details:
            log_msg += f" - {details}"
        logging.info(log_msg) 