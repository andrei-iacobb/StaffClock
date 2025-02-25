import os
import sqlite3
import logging
from datetime import datetime
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QPushButton, QApplication)
from PyQt6.QtCore import Qt, QTimer, QTime
from enhanced_backup import EnhancedBackupSystem

class StaffClockInOutSystem(QMainWindow):
    def __init__(self, path_manager, database_manager, timesheet_generator):
        super().__init__()
        self.path_manager = path_manager
        self.database_manager = database_manager
        self.timesheet_generator = timesheet_generator
        
        # Initialize UI elements before using them
        self.role_entry = None
        self.setup_ui()
        
        # Set window properties
        screen = QApplication.primaryScreen()
        if screen:
            rect = screen.availableGeometry()
            self.setFixedSize(rect.width(), rect.height())
            self.update_screen_dimensions(rect)
            
        # Initialize backup system
        self.backup_paths = {
            'database': self.path_manager.database_path,
            'logs': self.path_manager.log_file,
            'settings': self.path_manager.settings_file_path,
            'logo': self.path_manager.logo_path
        }
        self.backup_system = EnhancedBackupSystem(self.backup_paths)
        self.backup_system.backup_complete.connect(self.handle_backup_complete)
        self.backup_system.start()

    def setup_ui(self):
        # Create central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(self.central_widget)
        
        # Create role entry and other UI elements
        self.role_entry = QLineEdit()
        self.role_entry.setReadOnly(True)
        
        # Add other UI elements as needed
        # ... (your existing UI setup code)

    def on_staff_code_change(self, staff_code):
        if not hasattr(self, 'role_entry') or self.role_entry is None:
            logging.error("role_entry not properly initialized")
            return
            
        try:
            conn = sqlite3.connect(self.path_manager.database_path)
            cursor = conn.cursor()
            cursor.execute('SELECT name, role FROM staff WHERE code = ?', (staff_code,))
            staff = cursor.fetchone()
            
            if staff:
                self.role_entry.setText(staff[1] if staff[1] else '')
            else:
                self.role_entry.clear()
                
        except Exception as e:
            logging.error(f"Error in on_staff_code_change: {e}")
            self.role_entry.clear()
        finally:
            if conn:
                conn.close()

    def handle_backup_complete(self, message):
        logging.info(message)
        if "failed" in message.lower():
            self.show_message(message, "warning")

    def show_message(self, message, level="info"):
        # Implement your message display logic here
        pass

    def update_screen_dimensions(self, rect):
        # Update screen dimensions in settings if needed
        pass

    def closeEvent(self, event):
        try:
            # Stop all threads
            if hasattr(self, 'backup_system'):
                self.backup_system.stop()
                self.backup_system.wait()
            if hasattr(self, 'timesheet_checker'):
                self.timesheet_checker.stop()
                self.timesheet_checker.wait()
                
            # Clear UI elements
            if hasattr(self, 'role_entry'):
                self.role_entry.deleteLater()
                self.role_entry = None
                
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
        finally:
            super().closeEvent(event) 