import os
import socket
import platform
import subprocess
import time
from threading import Thread
from typing import Tuple
from utils.logging_manager import LoggingManager

class PrinterManager:
    def __init__(self, printer_ip: str, printer_port: int = 9100, logger: LoggingManager = None):
        self.printer_ip = printer_ip
        self.printer_port = printer_port
        self.logger = logger

    def print_file(self, file_path: str) -> bool:
        """Send a file to the printer."""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            with open(file_path, "rb") as pdf_file:
                pdf_data = pdf_file.read()
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as printer_socket:
                printer_socket.connect((self.printer_ip, self.printer_port))
                printer_socket.sendall(pdf_data)
            
            if self.logger:
                self.logger.log_printer_operation("Print", self.printer_ip, True, f"File: {file_path}")
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.log_error(e, f"print_file - File: {file_path}")
            return False

    def test_connection(self) -> Tuple[bool, str]:
        """Test both ping and port 9100 connection to the printer."""
        # First test ping
        if not self.ping_printer():
            if self.logger:
                self.logger.log_printer_operation("Connection Test", self.printer_ip, False, "Ping failed")
            return False, "Printer is not responding to ping"
            
        try:
            # Try to connect to port 9100 (standard printer port)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)  # 2 second timeout
            result = sock.connect_ex((self.printer_ip, self.printer_port))
            sock.close()
            
            if result == 0:
                if self.logger:
                    self.logger.log_printer_operation("Connection Test", self.printer_ip, True, "Ping and port test successful")
                return True, "Printer connection successful"
            else:
                if self.logger:
                    self.logger.log_printer_operation("Connection Test", self.printer_ip, False, "Port test failed")
                return False, "Printer port 9100 is not accessible"
                
        except Exception as e:
            if self.logger:
                self.logger.log_error(e, "test_connection")
            return False, f"Connection error: {str(e)}"

    def ping_printer(self) -> bool:
        """Test if a printer is reachable at the given IP address."""
        try:
            # For Windows
            if platform.system().lower() == "windows":
                ping_cmd = ["ping", "-n", "1", "-w", "1000", self.printer_ip]
            # For Unix/Linux/macOS
            else:
                ping_cmd = ["ping", "-c", "1", "-W", "1", self.printer_ip]
            
            result = subprocess.run(ping_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            success = result.returncode == 0
            
            if self.logger:
                self.logger.log_printer_operation("Ping", self.printer_ip, success)
            
            return success
            
        except Exception as e:
            if self.logger:
                self.logger.log_error(e, "ping_printer")
            return False

    def delete_file_after_delay(self, file_path: str, delay: int = 10):
        """Delete the file after a specified delay."""
        def delete_file():
            time.sleep(delay)
            try:
                os.remove(file_path)
                if self.logger:
                    self.logger.log_system_event("File Cleanup", f"Deleted temporary file: {file_path}")
            except Exception as e:
                if self.logger:
                    self.logger.log_error(e, f"delete_file_after_delay - File: {file_path}")

        Thread(target=delete_file, daemon=True).start() 