import logging
import os
import socket
import sqlite3
import traceback
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any

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

    def log_error(self, error: Exception, context: str = "", 
                 user: Optional[str] = None, additional_data: Optional[Dict[str, Any]] = None):
        """Log an error with full traceback, context, and enhanced details."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Build error context
        error_parts = [f"ERROR [{type(error).__name__}]"]
        
        if context:
            error_parts.append(f"Context: {context}")
            
        if user:
            error_parts.append(f"User: {user}")
            
        error_parts.append(f"Message: {str(error)}")
        
        # Add additional context data
        if additional_data:
            for key, value in additional_data.items():
                error_parts.append(f"{key}: {value}")
                
        error_parts.append(f"Time: {timestamp}")
        
        # Log the structured error message
        error_msg = " | ".join(error_parts)
        logging.error(error_msg)
        
        # Log the full traceback on a separate line for readability
        logging.error(f"Traceback:\n{traceback.format_exc()}")
        
        # Log system info for critical errors
        if isinstance(error, (sqlite3.Error, ConnectionError, OSError)):
            try:
                hostname = socket.gethostname()
                logging.error(f"System Context: Host={hostname}")
            except:
                pass

    def log_database_operation(self, operation: str, details: str, success: bool):
        """Log database operations with consistent formatting."""
        status = "SUCCESS" if success else "FAILED"
        logging.info(f"Database Operation [{status}] - {operation}: {details}")

    def log_user_action(self, user: str, action: str, details: Optional[str] = None, 
                       user_name: Optional[str] = None, user_role: Optional[str] = None,
                       session_info: Optional[Dict[str, Any]] = None):
        """Log user actions with enhanced context and formatting."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Build comprehensive log message
        log_parts = [f"USER_ACTION [{action}]"]
        
        # Add user identification
        if user_name:
            log_parts.append(f"User: {user_name} ({user})")
        else:
            log_parts.append(f"User: {user}")
            
        if user_role:
            log_parts.append(f"Role: {user_role}")
        
        # Add action details
        if details:
            log_parts.append(f"Details: {details}")
            
        # Add session context if available
        if session_info:
            if 'ip_address' in session_info:
                log_parts.append(f"IP: {session_info['ip_address']}")
            if 'device_info' in session_info:
                log_parts.append(f"Device: {session_info['device_info']}")
                
        # Add timestamp
        log_parts.append(f"Time: {timestamp}")
        
        log_msg = " | ".join(log_parts)
        logging.info(log_msg)

    def log_system_event(self, event_type: str, details: str):
        """Log system events with consistent formatting."""
        logging.info(f"System Event [{event_type}]: {details}")

    def log_security_event(self, event_type: str, user: str, details: str, 
                          severity: str = "WARNING", user_name: Optional[str] = None,
                          ip_address: Optional[str] = None, attempt_count: Optional[int] = None):
        """Log security-related events with enhanced details and severity levels."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Build security event message
        security_parts = [f"SECURITY_EVENT [{event_type}]"]
        security_parts.append(f"Severity: {severity}")
        
        if user_name:
            security_parts.append(f"User: {user_name} ({user})")
        else:
            security_parts.append(f"User: {user}")
            
        if ip_address:
            security_parts.append(f"IP: {ip_address}")
            
        if attempt_count:
            security_parts.append(f"Attempt: {attempt_count}")
            
        security_parts.append(f"Details: {details}")
        security_parts.append(f"Time: {timestamp}")
        
        security_msg = " | ".join(security_parts)
        
        # Log at appropriate level based on severity
        if severity == "CRITICAL":
            logging.critical(security_msg)
        elif severity == "ERROR":
            logging.error(security_msg)
        else:
            logging.warning(security_msg)

    def log_printer_operation(self, operation: str, printer_ip: str, success: bool, details: Optional[str] = None):
        """Log printer operations with consistent formatting."""
        status = "SUCCESS" if success else "FAILED"
        log_msg = f"Printer Operation [{status}] - {operation} - Printer: {printer_ip}"
        if details:
            log_msg += f" - {details}"
        logging.info(log_msg)
    
    def log_authentication_attempt(self, user: str, auth_method: str, success: bool, 
                                 user_name: Optional[str] = None, failure_reason: Optional[str] = None,
                                 ip_address: Optional[str] = None):
        """Log authentication attempts with detailed context."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status = "SUCCESS" if success else "FAILED"
        
        auth_parts = [f"AUTH_ATTEMPT [{status}]"]
        auth_parts.append(f"Method: {auth_method}")
        
        if user_name:
            auth_parts.append(f"User: {user_name} ({user})")
        else:
            auth_parts.append(f"User: {user}")
            
        if ip_address:
            auth_parts.append(f"IP: {ip_address}")
            
        if not success and failure_reason:
            auth_parts.append(f"Reason: {failure_reason}")
            
        auth_parts.append(f"Time: {timestamp}")
        
        auth_msg = " | ".join(auth_parts)
        
        if success:
            logging.info(auth_msg)
        else:
            logging.warning(auth_msg)
    
    def log_clock_operation(self, user: str, operation: str, success: bool, 
                           user_name: Optional[str] = None, user_role: Optional[str] = None,
                           timestamp: Optional[str] = None, additional_info: Optional[Dict[str, Any]] = None):
        """Log clock-in/out operations with comprehensive details."""
        log_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status = "SUCCESS" if success else "FAILED"
        
        clock_parts = [f"CLOCK_OPERATION [{status}]"]
        clock_parts.append(f"Operation: {operation}")
        
        if user_name:
            clock_parts.append(f"User: {user_name} ({user})")
        else:
            clock_parts.append(f"User: {user}")
            
        if user_role:
            clock_parts.append(f"Role: {user_role}")
            
        if timestamp:
            clock_parts.append(f"ActionTime: {timestamp}")
            
        if additional_info:
            for key, value in additional_info.items():
                clock_parts.append(f"{key}: {value}")
                
        clock_parts.append(f"LogTime: {log_timestamp}")
        
        clock_msg = " | ".join(clock_parts)
        
        if success:
            logging.info(clock_msg)
        else:
            logging.error(clock_msg)
    
    def log_admin_action(self, admin_user: str, action: str, target: Optional[str] = None,
                        admin_name: Optional[str] = None, details: Optional[str] = None,
                        success: bool = True):
        """Log administrative actions with enhanced audit trail."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status = "SUCCESS" if success else "FAILED"
        
        admin_parts = [f"ADMIN_ACTION [{status}]"]
        admin_parts.append(f"Action: {action}")
        
        if admin_name:
            admin_parts.append(f"Admin: {admin_name} ({admin_user})")
        else:
            admin_parts.append(f"Admin: {admin_user}")
            
        if target:
            admin_parts.append(f"Target: {target}")
            
        if details:
            admin_parts.append(f"Details: {details}")
            
        admin_parts.append(f"Time: {timestamp}")
        
        admin_msg = " | ".join(admin_parts)
        
        if success:
            logging.info(admin_msg)
        else:
            logging.error(admin_msg)
    
    def log_database_backup(self, backup_type: str, success: bool, file_path: Optional[str] = None,
                           records_count: Optional[int] = None, error_msg: Optional[str] = None):
        """Log database backup operations with detailed information."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status = "SUCCESS" if success else "FAILED"
        
        backup_parts = [f"DATABASE_BACKUP [{status}]"]
        backup_parts.append(f"Type: {backup_type}")
        
        if file_path:
            backup_parts.append(f"Path: {file_path}")
            
        if records_count is not None:
            backup_parts.append(f"Records: {records_count}")
            
        if not success and error_msg:
            backup_parts.append(f"Error: {error_msg}")
            
        backup_parts.append(f"Time: {timestamp}")
        
        backup_msg = " | ".join(backup_parts)
        
        if success:
            logging.info(backup_msg)
        else:
            logging.error(backup_msg)
    
    def log_performance_metric(self, operation: str, duration_ms: float, 
                              records_processed: Optional[int] = None,
                              additional_metrics: Optional[Dict[str, Any]] = None):
        """Log performance metrics for monitoring system health."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        perf_parts = [f"PERFORMANCE_METRIC"]
        perf_parts.append(f"Operation: {operation}")
        perf_parts.append(f"Duration: {duration_ms:.2f}ms")
        
        if records_processed is not None:
            perf_parts.append(f"Records: {records_processed}")
            
        if additional_metrics:
            for key, value in additional_metrics.items():
                perf_parts.append(f"{key}: {value}")
                
        perf_parts.append(f"Time: {timestamp}")
        
        perf_msg = " | ".join(perf_parts)
        logging.info(perf_msg) 