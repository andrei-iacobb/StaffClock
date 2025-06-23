import os
import shutil
import sqlite3
import datetime
import random
import socket
import calendar
import pyglet
from functools import partial
import logging
from threading import Thread
import json
import subprocess
import platform
import zipfile

from PyQt6.QtCore import QCoreApplication
# --- BEGIN HACK for macOS Qt Plugin Path ---
# On some macOS systems with Homebrew, Qt can't find its platform plugins.
# This code explicitly adds the likely path to the library paths.
import sys
if sys.platform == "darwin":  # darwin is the name for macOS
    # Path determined from `find /opt/homebrew -name "libqcocoa.dylib"`
    QCoreApplication.addLibraryPath("/opt/homebrew/Cellar/qt/6.9.0/share/qt/plugins/platforms")
# --- END HACK ---


import subprocess
import time
import sys
from datetime import datetime, timedelta
from os import mkdir, write
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QDialog, QMessageBox, QDialogButtonBox, QTableWidget, QHeaderView, QAbstractItemView,
    QTableWidgetItem, QCompleter, QGridLayout, QFrame, QProgressBar, QTextEdit, QTabWidget, QListWidget, QInputDialog
)
from PyQt6.QtCore import Qt, QTimer, QTime, QEvent, QUrl, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QImage, QScreen, QColor
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView


from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from timesheetDailyCheck import TimesheetCheckerThread
from dailyBackUp import DailyBackUp
from utils.logging_manager import LoggingManager
from fingerprint_manager import FingerprintManager, detect_digitalPersona_device
from progressive_timesheet_generator import (
    start_progressive_timesheet_generation, 
    ProgressiveTimesheetDialog,
    ProgressiveTimesheetGenerator
)

# Application version
APP_VERSION = "1.0.0"

# Global Paths
tempPath = permanentPath = databasePath = settingsFilePath = log_file = logoPath = ""

# Initialize logging manager
logger = None

def get_os_specific_path():
    global tempPath, permanentPath, databasePath, settingsFilePath, log_file, logoPath, logger

    # Use the user's home directory to store application data
    # This is more robust and avoids permissions issues in Program Files
    home_dir = os.path.expanduser("~")
    base_path = os.path.join(home_dir, "StaffClock_Data")

    # The original "ProgramData" is now the base path
    program_data_path = base_path 
    tempPath = os.path.join(base_path, "TempData")
    permanentPath = os.path.join(base_path, "Timesheets")
    backup_folder = os.path.join(base_path, "Backups")

    for folder in [program_data_path, tempPath, permanentPath, backup_folder]:
        os.makedirs(folder, exist_ok=True)

    settingsFilePath = os.path.join(program_data_path, "settings.json")
    log_file = os.path.join(program_data_path, "staff_clock_system.log")
    logoPath = os.path.join(program_data_path, "Logo.png")
    databasePath = os.path.join(program_data_path, "staff_hours.db")

    # Initialize logging manager
    logger = LoggingManager(log_file)
    logger.log_startup(APP_VERSION)

    configure_logging()

    # Get screen dimensions before checking files
    app = QApplication.instance() or QApplication(sys.argv)
    screen = app.primaryScreen()
    if screen:
        rect = screen.availableGeometry()
    else:
        rect = None

    check_and_restore_file(databasePath, backup_folder, generate_default_database)
    check_and_restore_file(settingsFilePath, backup_folder, lambda path: generate_default_settings(path, rect))
    # Logo is optional - check for it, but don't crash if it's missing.
    # The application will copy it from a source location if it exists.
    check_and_restore_file(logoPath, backup_folder, generate_default=None, is_critical=False)


def check_and_restore_file(primary_path, backup_folder, generate_default=None, is_critical=True):
    """
    Checks if a primary file exists. If not, it attempts to restore from the latest backup.
    If no backup is found, it can generate a default file.
    """
    if os.path.exists(primary_path):
        logging.info(f"File found: {primary_path}")
        return

    zip_files = sorted(
        [os.path.join(backup_folder, f) for f in os.listdir(backup_folder) if f.endswith('.zip')],
        key=os.path.getmtime,
        reverse=True
    )

    for zip_file in zip_files:
        try:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                if os.path.basename(primary_path) in zip_ref.namelist():
                    zip_ref.extract(os.path.basename(primary_path), os.path.dirname(primary_path))
                    logging.info(f"Restored {primary_path} from backup {zip_file}")
                    return
        except zipfile.BadZipFile:
            logging.error(f"Corrupted zip file: {zip_file}")

    # Handle source file for logo if it's missing from the data directory
    if primary_path == logoPath:
        source_logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Logo.png")
        if os.path.exists(source_logo_path):
            try:
                shutil.copy2(source_logo_path, primary_path)
                logging.info(f"Copied default logo from {source_logo_path} to {primary_path}")
                return
            except Exception as e:
                logging.error(f"Failed to copy logo file: {e}")

    if generate_default:
        logging.warning(f"No backup found for {primary_path}. Generating default.")
        generate_default(primary_path)
        return

    if is_critical:
        logging.error(f"CRITICAL: Required file not found: {primary_path}. No backup available.")
        QMessageBox.critical(None, "Critical File Missing", f"A critical file is missing and could not be restored from backup:\n\n{primary_path}\n\nThe application cannot continue.")
        sys.exit(1)
    else:
        logging.warning(f"Optional file not found: {primary_path}. Continuing without it.")

def generate_default_database(path):
    conn = sqlite3.connect(path)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS staff (
            name TEXT NOT NULL,
            code TEXT UNIQUE PRIMARY KEY,
            fingerprint TEXT,
            role TEXT,
            notes TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS clock_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_code TEXT NOT NULL,
            clock_in_time TEXT,
            clock_out_time TEXT,
            notes TEXT,
            break_time TEXT,
            FOREIGN KEY(staff_code) REFERENCES staff(code)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS archive_records (
            staff_name TEXT,
            staff_code TEXT,
            clock_in TEXT,
            clock_out TEXT,
            notes TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            car_reg TEXT,
            purpose TEXT,
            time_in TEXT,
            time_out TEXT
        )
    ''')

    conn.commit()
    conn.close()
    logging.info(f"Default database created at {path}")

def generate_default_settings(path, rect=None):
    default_settings = {
        "start_day": 21,
        "end_day": 20,
        "printer_IP": "10.60.1.146",
        "width": rect.width() if rect else 1920,  # Default fallback width
        "height": rect.height() if rect else 1080,  # Default fallback height
        "admin_pin": "123456",
        "exit_code": "654321"
    }
    with open(path, "w") as file:
        json.dump(default_settings, file, indent=4)
    logging.info(f"Default settings file created at {path}")

def configure_logging():
    logging.basicConfig(
        filename=log_file,
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logging.info(f"Logging initialized on {datetime.now().date()}")

# Application version
APP_VERSION = "1.0.0"

# Global Paths
tempPath = permanentPath = databasePath = settingsFilePath = log_file = logoPath = ""

# Initialize logging manager
logger = None

def get_os_specific_path():
    global tempPath, permanentPath, databasePath, settingsFilePath, log_file, logoPath, logger

    # Use the user's home directory to store application data
    # This is more robust and avoids permissions issues in Program Files
    home_dir = os.path.expanduser("~")
    base_path = os.path.join(home_dir, "StaffClock_Data")

    # The original "ProgramData" is now the base path
    program_data_path = base_path 
    tempPath = os.path.join(base_path, "TempData")
    permanentPath = os.path.join(base_path, "Timesheets")
    backup_folder = os.path.join(base_path, "Backups")

    for folder in [program_data_path, tempPath, permanentPath, backup_folder]:
        os.makedirs(folder, exist_ok=True)

    settingsFilePath = os.path.join(program_data_path, "settings.json")
    log_file = os.path.join(program_data_path, "staff_clock_system.log")
    logoPath = os.path.join(program_data_path, "Logo.png")
    databasePath = os.path.join(program_data_path, "staff_hours.db")

    # Initialize logging manager
    logger = LoggingManager(log_file)
    logger.log_startup(APP_VERSION)

    configure_logging()

    # Get screen dimensions before checking files
    screen = QApplication.primaryScreen()
    if screen:
        rect = screen.availableGeometry()
    else:
        rect = None

    check_and_restore_file(databasePath, backup_folder, generate_default_database)
    check_and_restore_file(settingsFilePath, backup_folder, lambda path: generate_default_settings(path, rect))
    # Logo is optional - check for it, but don't crash if it's missing.
    # The application will copy it from a source location if it exists.
    check_and_restore_file(logoPath, backup_folder, generate_default=None, is_critical=False)


def check_and_restore_folder(folder_path, backup_folder):
    if os.path.exists(folder_path):
        logging.info(f"Folder found: {folder_path}")
        return

    zip_files = sorted(
        [os.path.join(backup_folder, f) for f in os.listdir(backup_folder) if f.endswith('.zip')],
        key=os.path.getmtime,
        reverse=True
    )

    for zip_file in zip_files:
        try:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                folder_name = os.path.basename(folder_path)
                folder_files = [f for f in zip_ref.namelist() if f.startswith(f"{folder_name}/")]
                if folder_files:
                    zip_ref.extractall(os.path.dirname(folder_path))
                    logging.info(f"Restored folder '{folder_path}' from backup '{zip_file}'.")
                    return
        except zipfile.BadZipFile:
            logging.error(f"Corrupted zip file: {zip_file}")

    logging.warning(f"No backup found for folder '{folder_path}'. Creating new folder.")
    os.makedirs(folder_path, exist_ok=True)

def check_and_restore_file(primary_path, backup_folder, generate_default=None, is_critical=True):
    """
    Checks if a primary file exists. If not, it attempts to restore from the latest backup.
    If no backup is found, it can generate a default file.
    Args:
        primary_path (str): The path to the file to check.
        backup_folder (str): The path to the folder containing zip backups.
        generate_default (function, optional): A function to call to create a default file.
        is_critical (bool): If True, the application will exit if the file cannot be found or restored.
    """
    if os.path.exists(primary_path):
        logging.info(f"File found: {primary_path}")
        return

    zip_files = sorted(
        [os.path.join(backup_folder, f) for f in os.listdir(backup_folder) if f.endswith('.zip')],
        key=os.path.getmtime,
        reverse=True
    )

    for zip_file in zip_files:
        try:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                if os.path.basename(primary_path) in zip_ref.namelist():
                    zip_ref.extract(os.path.basename(primary_path), os.path.dirname(primary_path))
                    logging.info(f"Restored {primary_path} from backup {zip_file}")
                    return
        except zipfile.BadZipFile:
            logging.error(f"Corrupted zip file: {zip_file}")

    # Handle source file for logo if it's missing from the data directory
    if primary_path == logoPath:
        source_logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Logo.png")
        if os.path.exists(source_logo_path):
            try:
                shutil.copy2(source_logo_path, primary_path)
                logging.info(f"Copied default logo from {source_logo_path} to {primary_path}")
                return
            except Exception as e:
                logging.error(f"Failed to copy logo file: {e}")

    if generate_default:
        logging.warning(f"No backup found for {primary_path}. Generating default.")
        generate_default(primary_path)
        return

    if is_critical:
        logging.error(f"CRITICAL: Required file not found: {primary_path}. No backup available.")
        # In a real GUI app, you might show a message box here before exiting.
        QMessageBox.critical(None, "Critical File Missing", f"A critical file is missing and could not be restored from backup:\n\n{primary_path}\n\nThe application cannot continue.")
        sys.exit(1)
    else:
        logging.warning(f"Optional file not found: {primary_path}. Continuing without it.")

def generate_default_database(path):
    conn = sqlite3.connect(path)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS staff (
            name TEXT NOT NULL,
            code TEXT UNIQUE PRIMARY KEY,
            fingerprint TEXT,
            role TEXT,
            notes TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS clock_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_code TEXT NOT NULL,
            clock_in_time TEXT,
            clock_out_time TEXT,
            notes TEXT,
            break_time TEXT,
            FOREIGN KEY(staff_code) REFERENCES staff(code)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS archive_records (
            staff_name TEXT,
            staff_code TEXT,
            clock_in TEXT,
            clock_out TEXT,
            notes TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            car_reg TEXT,
            purpose TEXT,
            time_in TEXT,
            time_out TEXT
        )
    ''')

    conn.commit()
    conn.close()
    logging.info(f"Default database created at {path}")

def generate_default_settings(path, rect=None):
    default_settings = {
        "start_day": 21,
        "end_day": 20,
        "printer_IP": "10.60.1.146",
        "width": rect.width() if rect else 1920,  # Default fallback width
        "height": rect.height() if rect else 1080,  # Default fallback height
        "admin_pin": "123456",
        "exit_code": "654321"
    }
    with open(path, "w") as file:
        json.dump(default_settings, file, indent=4)
    logging.info(f"Default settings file created at {path}")

def configure_logging():
    logging.basicConfig(
        filename=log_file,
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logging.info(f"Logging initialized on {datetime.now().date()}")

class FingerprintEnrollmentDialog(QDialog):
    """Built-in fingerprint enrollment dialog with visual guidance."""
    
    def __init__(self, staff_code: str, staff_name: str, parent=None):
        super().__init__(parent)
        self.staff_code = staff_code
        self.staff_name = staff_name
        self.fingerprint_manager = None
        self.enrollment_thread = None
        self.current_step = 0
        self.total_samples = 5
        
        self.setWindowTitle(f"Fingerprint Enrollment - {staff_name}")
        self.setModal(True)
        
        # Match main app colors
        self.colors = {
            'primary': '#1a73e8',      # Blue
            'success': '#34a853',      # Green
            'danger': '#ea4335',       # Red
            'warning': '#fbbc05',      # Yellow
            'dark': '#202124',         # Dark gray
            'light': '#ffffff',        # White
            'gray': '#5f6368',         # Medium gray
            'lighter_dark': '#303134', # Lighter dark for sections
        }
        
        self.setup_ui()
        self.initialize_fingerprint_manager()
        self.update_ui_for_step(0)
    
    def setup_ui(self):
        """Set up the user interface matching the main app's dark theme."""
        # Increase dialog size to reduce crowdedness
        self.setFixedSize(650, 750)
        self.setStyleSheet(f"""
            QDialog {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 {self.colors['dark']},
                    stop: 1 {self.colors['dark']}ee
                );
                border-radius: 15px;
            }}
        """)
        
        # Main layout with improved spacing
        layout = QVBoxLayout(self)
        layout.setSpacing(30)  # Increased from 25
        layout.setContentsMargins(35, 35, 35, 35)  # Reduced margins to give more space
        
        # Header section with better spacing
        header_layout = QVBoxLayout()
        header_layout.setSpacing(15)  # Increased from 12
        
        # Title - slightly smaller to save space
        title_label = QLabel("Fingerprint Enrollment")
        title_label.setFont(QFont("Arial", 28, QFont.Weight.Medium))  # Reduced from 32
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(f"color: {self.colors['light']};")
        header_layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel(f"Setting up biometric access for {self.staff_name}")
        subtitle_label.setFont(QFont("Arial", 16))
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet(f"color: {self.colors['gray']};")
        subtitle_label.setWordWrap(True)  # Allow text wrapping for long names
        header_layout.addWidget(subtitle_label)
        
        layout.addLayout(header_layout)
        
        # Progress section with reduced padding
        progress_frame = QFrame()
        progress_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['lighter_dark']};
                border: 1px solid {self.colors['gray']};
                border-radius: 10px;
                padding: 15px;
            }}
        """)
        progress_layout = QVBoxLayout(progress_frame)
        progress_layout.setSpacing(10)  # Reduced from 12
        
        self.progress_label = QLabel("Ready to start")
        self.progress_label.setFont(QFont("Arial", 15, QFont.Weight.Medium))  # Slightly smaller
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setStyleSheet(f"color: {self.colors['light']};")
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(self.total_samples)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(10)  # Slightly larger for better visibility
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 5px;
                background-color: {self.colors['gray']};
            }}
            QProgressBar::chunk {{
                background-color: {self.colors['success']};
                border-radius: 5px;
            }}
        """)
        progress_layout.addWidget(self.progress_bar)
        
        self.sample_counter = QLabel("0 of 5 samples captured")
        self.sample_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sample_counter.setFont(QFont("Arial", 12))
        self.sample_counter.setStyleSheet(f"color: {self.colors['gray']};")
        progress_layout.addWidget(self.sample_counter)
        
        layout.addWidget(progress_frame)
        
        # Central fingerprint guide with improved layout
        visual_frame = QFrame()
        visual_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['lighter_dark']};
                border: 2px solid {self.colors['primary']};
                border-radius: 10px;
                padding: 25px 20px;
            }}
        """)
        visual_layout = QVBoxLayout(visual_frame)
        visual_layout.setSpacing(20)  # Increased from 15
        
        self.finger_guide = QLabel()
        self.finger_guide.setFixedHeight(120)  # Increased from 100
        self.finger_guide.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.finger_guide.setFont(QFont("Arial", 24, QFont.Weight.Bold))  # Increased from 20
        self.update_finger_guide("ready")
        visual_layout.addWidget(self.finger_guide)
        
        # Instruction text
        self.instruction_label = QLabel("Click 'Start Enrollment' to begin")
        self.instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instruction_label.setFont(QFont("Arial", 14))
        self.instruction_label.setStyleSheet(f"color: {self.colors['gray']};")
        self.instruction_label.setWordWrap(True)
        visual_layout.addWidget(self.instruction_label)
        
        layout.addWidget(visual_frame)
        
        # Status section with more breathing room
        self.status_label = QLabel("")
        self.status_label.setFont(QFont("Arial", 15, QFont.Weight.Bold))  # Slightly smaller
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFixedHeight(40)  # Increased from 35
        self.status_label.setStyleSheet(f"color: {self.colors['light']};")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Add some spacing before buttons
        layout.addSpacing(10)
        
        # Buttons with improved spacing
        button_layout = QHBoxLayout()
        button_layout.setSpacing(25)  # Increased from 20
        
        cancel_button = QPushButton("Cancel")
        cancel_button.setFont(QFont("Arial", 15))  # Slightly smaller
        cancel_button.setMinimumSize(130, 45)  # Slightly smaller
        cancel_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['gray']};
                color: {self.colors['light']};
                border-radius: 10px;
                border: none;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {self.colors['gray']}dd;
            }}
        """)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        self.start_button = QPushButton("Start Enrollment")
        self.start_button.setFont(QFont("Arial", 15))  # Slightly smaller
        self.start_button.setMinimumSize(170, 45)  # Slightly smaller
        self.start_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['success']};
                color: {self.colors['light']};
                border-radius: 10px;
                border: none;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {self.colors['success']}dd;
            }}
            QPushButton:disabled {{
                background-color: {self.colors['gray']};
                color: {self.colors['light']}aa;
            }}
        """)
        self.start_button.clicked.connect(self.start_enrollment)
        button_layout.addWidget(self.start_button)
        
        layout.addLayout(button_layout)
    
    def update_finger_guide(self, state: str):
        """Update the finger placement visual guide."""
        guides = {
            "ready": "🖐️\nReady to scan",
            "scanning": "👆\nScanning...",
            "good": "✅\nSample captured!",
            "bad": "❌\nTry again",
            "lift": "↗️\nLift finger"
        }
        
        colors = {
            "ready": self.colors['primary'],
            "scanning": self.colors['warning'], 
            "good": self.colors['success'],
            "bad": self.colors['danger'],
            "lift": self.colors['light']
        }
        
        text = guides.get(state, guides["ready"])
        color = colors.get(state, self.colors['primary'])
        
        self.finger_guide.setText(text)
        self.finger_guide.setStyleSheet(f"color: {color};")
    
    def update_ui_for_step(self, step: int):
        """Update UI for current enrollment step."""
        self.current_step = step
        
        if step == 0:
            self.progress_label.setText("Ready to start")
            self.status_label.setText("")
            self.status_label.setStyleSheet(f"color: {self.colors['light']};")
            self.instruction_label.setText("Click 'Start Enrollment' to begin")
            self.start_button.setText("Start Enrollment")
            self.start_button.setEnabled(True)
        
        elif step > 0 and step <= self.total_samples:
            self.progress_label.setText(f"Capturing sample {step} of {self.total_samples}")
            self.sample_counter.setText(f"{step-1} of {self.total_samples} samples captured")
            self.progress_bar.setValue(step-1)
            self.instruction_label.setText("Place your finger on the scanner")
            self.start_button.setText("Scanning...")
            self.start_button.setEnabled(False)
            self.status_label.setStyleSheet(f"color: {self.colors['light']};")
            
        else:
            # Completion state
            self.progress_label.setText("Enrollment completed!")
            self.status_label.setText("✅ Fingerprint enrolled successfully")
            self.status_label.setStyleSheet(f"color: {self.colors['success']};")
            self.sample_counter.setText(f"{self.total_samples} of {self.total_samples} samples captured")
            self.progress_bar.setValue(self.total_samples)
            self.instruction_label.setText("You can now use fingerprint authentication")
            self.start_button.setText("Finish")
            self.start_button.setEnabled(True)
    
    def initialize_fingerprint_manager(self):
        """Initialize the fingerprint manager."""
        try:
            from fingerprint_manager import FingerprintManager
            self.fingerprint_manager = FingerprintManager()
            success, msg = self.fingerprint_manager.initialize_device()
            
            if not success:
                self.status_label.setText("❌ Fingerprint device not available")
                self.status_label.setStyleSheet(f"color: {self.colors['danger']};")
                self.start_button.setEnabled(False)
                
        except Exception as e:
            self.status_label.setText(f"❌ Error: {str(e)}")
            self.status_label.setStyleSheet(f"color: {self.colors['danger']};")
            self.start_button.setEnabled(False)
    
    def start_enrollment(self):
        """Start the fingerprint enrollment process."""
        if self.current_step == 0:
            self.update_ui_for_step(1)
            self.update_finger_guide("ready")
            self.start_actual_enrollment()
        elif self.current_step > self.total_samples:
            self.accept()
    
    def start_actual_enrollment(self):
        """Start the actual fingerprint enrollment."""
        try:
            self.update_finger_guide("scanning")
            self.status_label.setText("Initializing enrollment...")
            
            from fingerprint_manager import FingerprintThread
            from biometric_enrollment import BiometricProfileEnrollment
            
            # Create a custom enrollment thread that provides sample-by-sample updates
            class EnhancedEnrollmentThread(FingerprintThread):
                sample_progress = pyqtSignal(int, int, str, float)  # current_sample, total_samples, status, quality
                
                def run(self):
                    """Run enrollment with sample-by-sample feedback."""
                    try:
                        # Get the enrollment system
                        enrollment_system = self.manager.enrollment_system
                        
                        if not enrollment_system.device.connected:
                            self.finished.emit(False, "Device not connected", {})
                            return
                            
                        # Check if already enrolled
                        if self.manager._is_employee_enrolled(self.kwargs['employee_id']):
                            self.finished.emit(False, f"Employee {self.kwargs['employee_id']} already enrolled", {})
                            return
                        
                        # Custom enrollment with live feedback
                        staff_code = self.kwargs['employee_id']
                        staff_name = self.kwargs['employee_name']
                        samples = []
                        quality_scores = []
                        required_samples = 5
                        
                        self.sample_progress.emit(0, required_samples, "Starting enrollment...", 0.0)
                        
                        for sample_num in range(1, required_samples + 1):
                            self.sample_progress.emit(sample_num, required_samples, f"SAMPLE {sample_num}/{required_samples}", 0.0)
                            self.sample_progress.emit(sample_num, required_samples, f"Please place your finger on the scanner for sample {sample_num}", 0.0)
                            
                            # Capture fingerprint sample
                            capture_start = time.time()
                            fingerprint_image = enrollment_system.device.capture_fingerprint()
                            capture_time = time.time() - capture_start
                            
                            if fingerprint_image is None:
                                self.sample_progress.emit(sample_num, required_samples, f"Failed to capture sample {sample_num}. Retrying...", 0.0)
                                sample_num -= 1  # Retry this sample
                                continue
                            
                            # Analyze quality
                            quality_score = enrollment_system._calculate_quality_score(fingerprint_image)
                            
                            if quality_score < enrollment_system.quality_threshold:
                                self.sample_progress.emit(sample_num, required_samples, f"Sample quality too low ({quality_score:.3f}). Please try again.", quality_score)
                                sample_num -= 1  # Retry this sample
                                continue
                            
                            # Check consistency with previous samples
                            if samples and not enrollment_system._check_sample_consistency(fingerprint_image, samples):
                                self.sample_progress.emit(sample_num, required_samples, "Sample not consistent. Please try again.", quality_score)
                                sample_num -= 1  # Retry this sample
                                continue
                            
                            # Extract minutiae
                            minutiae = enrollment_system._extract_minutiae(fingerprint_image)
                            
                            # Store successful sample
                            sample_data = {
                                'image': fingerprint_image,
                                'quality': quality_score,
                                'minutiae': minutiae,
                                'capture_time': capture_time,
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            samples.append(sample_data)
                            quality_scores.append(quality_score)
                            
                            self.sample_progress.emit(sample_num, required_samples, f"✓ Sample {sample_num} captured successfully (Quality: {quality_score:.3f})", quality_score)
                            
                            if sample_num < required_samples:
                                self.sample_progress.emit(sample_num, required_samples, "Please lift your finger and place it again for the next sample...", quality_score)
                                time.sleep(2)  # Brief pause between samples
                        
                        # Build and store profile
                        if len(samples) >= required_samples:
                            self.sample_progress.emit(required_samples, required_samples, "Building biometric profile...", 0.0)
                            
                            # Build comprehensive biometric profile
                            profile_data = enrollment_system._build_biometric_profile(samples)
                            
                            # Calculate enrollment statistics
                            enrollment_stats = {
                                'staff_code': staff_code,
                                'staff_name': staff_name,
                                'samples_captured': len(samples),
                                'average_quality': np.mean(quality_scores),
                                'min_quality': np.min(quality_scores),
                                'max_quality': np.max(quality_scores),
                                'minutiae_count': np.mean([len(s['minutiae']) for s in samples])
                            }
                            
                            # Store profile
                            success = enrollment_system._store_biometric_profile(
                                staff_code, staff_name, profile_data, 
                                quality_scores, samples, enrollment_stats
                            )
                            
                            if success:
                                # Link to main database
                                biometric_user_id = f"emp_{staff_code}_{int(time.time())}"
                                self.manager._link_employee_to_biometric(staff_code, staff_name, biometric_user_id)
                                
                                message = f"🎉 Biometric profile enrolled successfully for {staff_name}\n   Average Quality: {enrollment_stats['average_quality']:.3f}\n   Total Samples: {len(samples)}\n   Minutiae Count: {enrollment_stats['minutiae_count']:.1f}"
                                self.finished.emit(True, message, enrollment_stats)
                            else:
                                self.finished.emit(False, "Failed to store biometric profile", {})
                        else:
                            self.finished.emit(False, f"Insufficient samples captured ({len(samples)}/{required_samples})", {})
                    
                    except Exception as e:
                        self.finished.emit(False, f"Enrollment error: {str(e)}", {})
            
            # Create and start enhanced enrollment thread
            from PyQt6.QtCore import pyqtSignal
            import numpy as np
            from datetime import datetime
            import time
            
            self.enrollment_thread = EnhancedEnrollmentThread(
                self.fingerprint_manager,
                'enroll',
                employee_id=self.staff_code,
                employee_name=self.staff_name
            )
            
            # Connect signals
            self.enrollment_thread.finished.connect(self.on_enrollment_complete)
            self.enrollment_thread.sample_progress.connect(self.on_sample_progress)
            self.enrollment_thread.start()
            
        except Exception as e:
            self.status_label.setText(f"❌ Error: {str(e)}")
            self.status_label.setStyleSheet(f"color: {self.colors['danger']};")
    
    def on_sample_progress(self, current_sample: int, total_samples: int, status: str, quality: float):
        """Handle sample-by-sample progress updates."""
        if current_sample > 0 and current_sample <= total_samples:
            # Update progress
            self.progress_label.setText(f"Capturing sample {current_sample} of {total_samples}")
            self.sample_counter.setText(f"{current_sample-1} of {total_samples} samples captured")
            self.progress_bar.setValue(current_sample-1)
            
            # Update status with detailed feedback
            if "✓" in status:
                self.status_label.setText(status)
                self.status_label.setStyleSheet(f"color: {self.colors['success']};")
                self.update_finger_guide("good")
                # Brief pause to show success
                QTimer.singleShot(1000, lambda: self.update_finger_guide("lift"))
            elif "Failed" in status or "quality too low" in status or "not consistent" in status:
                self.status_label.setText(status)
                self.status_label.setStyleSheet(f"color: {self.colors['danger']};")
                self.update_finger_guide("bad")
            elif "Please place" in status:
                self.status_label.setText(status)
                self.status_label.setStyleSheet(f"color: {self.colors['light']};")
                self.update_finger_guide("ready")
            elif "lift your finger" in status:
                self.status_label.setText(status)
                self.status_label.setStyleSheet(f"color: {self.colors['light']};")
                self.update_finger_guide("lift")
            elif "SAMPLE" in status:
                self.status_label.setText(status)
                self.status_label.setStyleSheet(f"color: {self.colors['primary']};")
                self.update_finger_guide("scanning")
            else:
                self.status_label.setText(status)
                self.status_label.setStyleSheet(f"color: {self.colors['light']};")
        else:
            # General status update
            self.status_label.setText(status)
            self.status_label.setStyleSheet(f"color: {self.colors['light']};")

    def on_enrollment_complete(self, success: bool, message: str, stats: dict):
        """Handle enrollment completion."""
        if success:
            self.current_step = self.total_samples + 1
            self.update_ui_for_step(self.current_step)
            self.update_finger_guide("good")
        else:
            self.status_label.setText(f"❌ Enrollment failed: {message}")
            self.status_label.setStyleSheet(f"color: {self.colors['danger']};")
            self.update_finger_guide("bad")
            self.start_button.setText("Retry")
            self.start_button.setEnabled(True)


if __name__ == "__main__":
    get_os_specific_path()


class StaffClockInOutSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        logger.log_system_event("Initialization", "Starting StaffClockInOutSystem")
        
        screen = QApplication.primaryScreen()
        if screen:
            rect = screen.availableGeometry()
            self.setFixedSize(rect.width(), rect.height())
            
            # Update settings with current screen dimensions
            self.update_screen_dimensions(rect)
            logger.log_system_event("Screen", f"Screen dimensions set to {rect.width()}x{rect.height()}")
            
        self.role_entry = QLineEdit()
        self.setWindowTitle("Staff Digital Timesheet System")
        self.showMaximized()
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        logging.info("UI setup complete.")

        # Ensure visitors table exists
        self.ensure_visitors_table()

        # Define color scheme for UI components
        self.COLORS = {
            'primary': '#1a73e8',      # Blue
            'success': '#34a853',      # Green
            'danger': '#ea4335',       # Red
            'warning': '#fbbc05',      # Yellow
            'dark': '#202124',         # Dark gray
            'light': '#ffffff',        # White
            'gray': '#5f6368',         # Medium gray
            'text': '#3c4043',         # Text color
            'border': '#dadce0',       # Border color
            'purple': '#9c27b0',       # Purple for visitor button
            'brown': '#795548',        # Brown for admin button
            'lighter_dark': '#303134', # Lighter dark for sections
        }

        self.isWindowed = False
        # Paths
        self.backup_folder = os.path.join(os.path.dirname(__file__), "Backups")
        self.database_path = databasePath
        self.log_file_path = log_file
        self.settings_path = settingsFilePath
        
        # Initialize archive database folder
        self.archive_folder = os.path.join(os.path.dirname(__file__), "Archive_Databases")
        os.makedirs(self.archive_folder, exist_ok=True)
        
        # Initialize real-time backup database
        self.realtime_backup_path = os.path.join(os.path.dirname(__file__), "Backups", "realtime_backup.db")
        self.initialize_realtime_backup()
        
        # Initialize optimized fingerprint system
        self.fingerprint_manager = FingerprintManager(self.database_path)
        
        # Properly initialize the fingerprint device
        fingerprint_init_success, fingerprint_init_msg = self.fingerprint_manager.initialize_device()
        
        if fingerprint_init_success:
            self.fingerprint_device_available = True
            logging.info(f"Fast fingerprint device ready: {fingerprint_init_msg}")
        else:
            self.fingerprint_device_available = False
            logging.warning(f"Fingerprint device not available: {fingerprint_init_msg}")

        self.daily_backup_thread = DailyBackUp(
            backup_folder=os.path.join(os.path.dirname(__file__), "Backups"),
            database_path=databasePath,
            log_file_path=log_file,
            settings_path=settingsFilePath,
            logo_path=logoPath,
        )

        self.daily_backup_thread.daily_back_up.connect(self.handle_backup_complete)
        self.daily_backup_thread.start()

        self.break_start_time = None  # Tracks when the break started
        self.on_break = False  # Tracks whether the staff is on break
        self.admin_was_open = False  # Track admin window state
        
        # Continuous fingerprint scanning
        self.continuous_fingerprint_active = False
        self.fingerprint_scan_timer = None

        # UI Components
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_time)
        self.clock_timer.start(1000)
        

        # Load settings
        self.settings = self.load_settings()
        self.setup_ui()
        self.showFullScreen()

        logging.info(f"Settings loaded: {self.settings}")
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        logging.info("Initializing TimesheetCheckerThread...")
        self.timesheet_checker = TimesheetCheckerThread(settingsFilePath)
        self.timesheet_checker.timesheet_generated.connect(self.handle_timesheet_generated)
        self.timesheet_checker.start()
        
        # Fingerprint scanning is now manual via button - no automatic scanning
        logging.info("StaffClockInOutSystem initialization complete")

    def initialize_realtime_backup(self):
        """Initialize the real-time backup database."""
        try:
            os.makedirs(os.path.dirname(self.realtime_backup_path), exist_ok=True)
            conn = sqlite3.connect(self.realtime_backup_path)
            c = conn.cursor()
            
            # Create backup tables with timestamp
            c.execute('''
                CREATE TABLE IF NOT EXISTS backup_clock_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_id INTEGER,
                    staff_code TEXT NOT NULL,
                    clock_in_time TEXT,
                    clock_out_time TEXT,
                    notes TEXT,
                    break_time TEXT,
                    backup_timestamp TEXT NOT NULL
                )
            ''')
            
            c.execute('''
                CREATE TABLE IF NOT EXISTS backup_staff (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_code TEXT,
                    name TEXT NOT NULL,
                    role TEXT,
                    notes TEXT,
                    backup_timestamp TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
            logging.info("Real-time backup database initialized successfully")
            
        except Exception as e:
            logging.error(f"Failed to initialize real-time backup database: {e}")

    def backup_clock_record(self, record_id, staff_code, clock_in_time, clock_out_time, notes=None, break_time=None):
        """Immediately backup a clock record after it's created/updated."""
        try:
            backup_timestamp = datetime.now().isoformat()
            conn = sqlite3.connect(self.realtime_backup_path)
            c = conn.cursor()
            
            c.execute('''
                INSERT INTO backup_clock_records 
                (original_id, staff_code, clock_in_time, clock_out_time, notes, break_time, backup_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (record_id, staff_code, clock_in_time, clock_out_time, notes, break_time, backup_timestamp))
            
            conn.commit()
            conn.close()
            logging.info(f"Real-time backup created for clock record ID: {record_id}")
            
        except Exception as e:
            logging.error(f"Failed to create real-time backup for clock record: {e}")

    def backup_staff_record(self, staff_code, name, role=None, notes=None):
        """Immediately backup a staff record after it's created/updated."""
        try:
            backup_timestamp = datetime.now().isoformat()
            conn = sqlite3.connect(self.realtime_backup_path)
            c = conn.cursor()
            
            c.execute('''
                INSERT INTO backup_staff 
                (original_code, name, role, notes, backup_timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (staff_code, name, role, notes, backup_timestamp))
            
            conn.commit()
            conn.close()
            logging.info(f"Real-time backup created for staff: {name}")
            
        except Exception as e:
            logging.error(f"Failed to create real-time backup for staff record: {e}")

    def archive_current_database(self):
        """Archive the current database and reset it for a fresh start."""
        try:
            # Create archive filename with current date
            archive_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            archive_filename = f"database_archive_{archive_date}.db"
            archive_path = os.path.join(self.archive_folder, archive_filename)
            
            logging.info(f"Starting database archival process for {archive_date}")
            
            # Copy current database to archive
            shutil.copy2(self.database_path, archive_path)
            logging.info(f"Database copied to archive: {archive_path}")
            
            # Reset the current database (clear records but keep structure)
            self.reset_current_database()
            
            # Show success message
            self.msg(f"Database archived successfully as {archive_filename}", "info", "Archive Complete")
            logging.info(f"Database archival completed successfully")
            
        except Exception as e:
            logging.error(f"Failed to archive database: {e}")
            self.msg(f"Error archiving database: {str(e)}", "warning", "Archive Error")

    def reset_current_database(self):
        """Reset the current database by clearing all records but keeping structure and staff."""
        try:
            conn = sqlite3.connect(self.database_path)
            c = conn.cursor()
            
            # Count records before deletion for logging
            c.execute('SELECT COUNT(*) FROM clock_records')
            clock_records_count = c.fetchone()[0]
            
            c.execute('SELECT COUNT(*) FROM visitors')
            visitors_count = c.fetchone()[0]
            
            logging.info(f"About to clear database: {clock_records_count} clock records, {visitors_count} visitor records")
            
            # Clear clock records (this is the main data we want to reset monthly)
            c.execute('DELETE FROM clock_records')
            
            # Clear visitor records (these can be reset monthly too)
            c.execute('DELETE FROM visitors')
            
            # Clear archive records (if any exist)
            c.execute('DELETE FROM archive_records')
            
            # Note: We keep the staff table intact so employees don't need to be re-added
            
            conn.commit()
            conn.close()
            
            logging.info(f"Current database reset successfully - cleared {clock_records_count} clock records, {visitors_count} visitor records")
            
        except Exception as e:
            logging.error(f"Failed to reset current database: {e}")
            raise

    def get_archive_databases(self):
        """Get a list of all archive databases with their creation dates."""
        try:
            archive_files = []
            if os.path.exists(self.archive_folder):
                for filename in os.listdir(self.archive_folder):
                    if filename.endswith(".db") and ("archive" in filename.lower()):
                        file_path = os.path.join(self.archive_folder, filename)
                        
                        # Handle different archive naming patterns
                        date_part = None
                        if filename.startswith("database_archive_"):
                            date_part = filename.replace("database_archive_", "").replace(".db", "")
                        elif filename.startswith("manual_archive_"):
                            date_part = filename.replace("manual_archive_", "").replace(".db", "")
                        
                        if date_part:
                            try:
                                archive_date = datetime.strptime(date_part, "%Y-%m-%d_%H-%M-%S")
                                archive_files.append({
                                    'filename': filename,
                                    'path': file_path,
                                    'date': archive_date,
                                    'size': os.path.getsize(file_path),
                                    'type': 'Manual' if filename.startswith("manual_") else 'Automatic'
                                })
                            except ValueError:
                                # Try alternative date formats or skip
                                try:
                                    # Handle any other potential date formats
                                    file_stat = os.path.getmtime(file_path)
                                    archive_date = datetime.fromtimestamp(file_stat)
                                    archive_files.append({
                                        'filename': filename,
                                        'path': file_path,
                                        'date': archive_date,
                                        'size': os.path.getsize(file_path),
                                        'type': 'Unknown'
                                    })
                                except:
                                    continue
            
            # Sort by date (newest first)
            archive_files.sort(key=lambda x: x['date'], reverse=True)
            return archive_files
            
        except Exception as e:
            logging.error(f"Failed to get archive databases: {e}")
            return []

    def ensure_visitors_table(self):
        """Ensure the visitors table exists in the database."""
        try:
            conn = sqlite3.connect(databasePath)
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS visitors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    car_reg TEXT,
                    purpose TEXT,
                    time_in TEXT,
                    time_out TEXT
                )
            ''')
            conn.commit()
            logging.info("Visitors table checked/created successfully")
        except sqlite3.Error as e:
            logging.error(f"Error ensuring visitors table exists: {e}")
        finally:
            conn.close()

    def handle_timesheet_generated(self, message):
        logging.info(message)
        self.generate_all_timesheets(self.settings["end_day"])
        
        # After generating timesheets, archive the database
        self.archive_current_database()

    def closeEvent(self, event):
        # Log shutdown
        logger.log_shutdown()
        
        # Stop continuous fingerprint scanning
        if hasattr(self, 'continuous_fingerprint_active') and self.continuous_fingerprint_active:
            self.stop_continuous_fingerprint_scanning()
        
        # Ensure the thread stops when the app closes
        self.daily_backup_thread.stop()
        self.daily_backup_thread.wait()
        super().closeEvent(event)

    def handle_backup_complete(self, message):
        logging.info(message)
        self.msg("Daily backup completed.", "info", "Backup")

    def update_time(self):
        """Update the clock label with the current time."""
        current_time = QTime.currentTime().toString("HH:mm:ss")
        self.clock_label.setText(current_time)

    def load_settings(self):
        settings_file = settingsFilePath
        default_settings = {
            "start_day": 21, 
            "end_day": 20, 
            "printer_IP": "10.60.1.146",
            "admin_pin": "123456",
            "exit_code": "654321"
        }

        if os.path.exists(settings_file):
            with open(settings_file, "r") as file:
                settings = json.load(file)
                # Ensure new settings exist in loaded file
                for key, value in default_settings.items():
                    if key not in settings:
                        settings[key] = value
                return settings
        else:
            with open(settings_file, "w") as file:
                json.dump(default_settings, file)
            return default_settings

    def save_settings(self):
        with open(settingsFilePath, "w") as file:
            json.dump(self.settings, file)

    def check_timesheet_generation(self):
        today = datetime.now()
        start_day = self.settings["start_day"]
        end_day = self.settings["end_day"]

        # Determine the end of the timesheet period
        if today.day == end_day:
            # 🚀 NEW: Start Progressive Generation instead of blocking
            self.start_integrated_progressive_generation()

    def start_integrated_progressive_generation(self):
        '''Start the progressive timesheet generation with cool UI.'''
        try:
            # Show the progressive generation dialog
            self.progressive_dialog = start_progressive_timesheet_generation(
                databasePath, parent_window=self
            )
            
            # Log the start
            logging.info("Progressive timesheet generation started")
            
            # Show notification to admin
            self.msg("🚀 Progressive Timesheet Generation Started\n\n"
                    "• Completed workers: Timesheets generated immediately\n"
                    "• Active workers: Monitored automatically in background\n"
                    "• Real-time progress tracking in the new window\n"
                    "• Timesheets auto-generated when workers clock out\n\n"
                    "You can continue using the system normally!", 
                    "info", "Smart Timesheet Generation")
                    
        except Exception as e:
            self.msg(f"Failed to start progressive generation: {e}", "warning", "Error")
            logging.error(f"Progressive generation failed: {e}")

    def check_background_monitoring_status(self):
        '''Check and display the status of background timesheet monitoring.'''
        try:
            from background_timesheet_monitor import get_background_monitor
            
            monitor = get_background_monitor()
            
            if monitor and monitor.monitoring_active:
                status = monitor.get_monitoring_status()
                
                message = f"🔄 Background Timesheet Monitoring Active\n\n"
                message += f"• Monitoring {status['pending_workers']} workers with active shifts\n"
                message += f"• Check interval: {status['check_interval']} seconds\n"
                message += f"• Timesheets auto-generated: {status['total_generated']}\n\n"
                
                if status['worker_list']:
                    message += "Active workers being monitored:\n"
                    # Get worker names from database
                    conn = sqlite3.connect(databasePath)
                    c = conn.cursor()
                    for staff_code in status['worker_list']:
                        c.execute('SELECT name FROM staff WHERE code = ?', (staff_code,))
                        result = c.fetchone()
                        name = result[0] if result else 'Unknown'
                        message += f"• {name} ({staff_code})\n"
                    conn.close()
                
                message += "\nTimesheets will be generated automatically when workers clock out."
                
                self.msg(message, "info", "Background Monitoring Status")
                
            else:
                self.msg("📭 No Background Monitoring Active\n\n"
                        "All workers have completed their shifts or\n"
                        "no monitoring session has been started.", 
                        "info", "Background Monitoring Status")
                
        except Exception as e:
            self.msg(f"Error checking monitoring status: {e}", "warning", "Error")
            logging.error(f"Error checking background monitoring status: {e}")

    def stop_background_monitoring(self):
        '''Stop the background timesheet monitoring service.'''
        try:
            from background_timesheet_monitor import stop_background_monitoring
            
            stop_background_monitoring()
            
            self.msg("🛑 Background Monitoring Stopped\n\n"
                    "Automatic timesheet generation has been disabled.\n"
                    "You can restart it using Progressive Generation.", 
                    "info", "Monitoring Stopped")
            
            logging.info("Background timesheet monitoring stopped by user")
            
        except Exception as e:
            self.msg(f"Error stopping monitoring: {e}", "warning", "Error")
            logging.error(f"Error stopping background monitoring: {e}")

    def setup_ui(self):
        # Ensure central widget is persistently defined
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Main layout
        main_layout = QVBoxLayout(self.central_widget)

        # Header with Logo and Title
        header_layout = QHBoxLayout()
        
        # --- Logo ---
        self.logo_label = QLabel()
        if os.path.exists(logoPath):
            pixmap = QPixmap(logoPath)
            if not pixmap.isNull():
                 self.logo_label.setPixmap(pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                logging.warning(f"Failed to load logo image from {logoPath}")
        else:
            logging.warning(f"Logo file not found at {logoPath}, displaying placeholder.")
            # Optionally set a placeholder color or text
            self.logo_label.setFixedSize(150, 150)
            self.logo_label.setText("Logo")
            self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.logo_label.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")

        header_layout.addWidget(self.logo_label)

        # Title
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setSpacing(10)

        title_label = QLabel("Staff Digital Timesheet System")
        title_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        title_layout.addWidget(title_label)

        subtitle_label = QLabel("Manage your staff timesheets efficiently")
        subtitle_label.setFont(QFont("Arial", 16))
        subtitle_layout = QVBoxLayout()
        subtitle_layout.addWidget(subtitle_label)
        subtitle_layout.addStretch()
        title_layout.addLayout(subtitle_layout)

        main_layout.addLayout(header_layout)
        main_layout.addLayout(title_layout)

        # Staff Code Input Section with modern styling
        staff_code_layout = QVBoxLayout()
        staff_code_layout.setSpacing(15)
        
        staff_code_label = QLabel("Enter Staff Code")
        staff_code_label.setFont(QFont("Arial", 38, QFont.Weight.Medium))
        staff_code_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        staff_code_label.setStyleSheet(f"color: {self.COLORS['light']};")

        self.staff_code_entry = QLineEdit()
        self.staff_code_entry.setFont(QFont("Arial", 26))
        self.staff_code_entry.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.staff_code_entry.setPlaceholderText("Enter your 4-digit code")
        self.staff_code_entry.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.COLORS['dark']};
                color: {self.COLORS['light']};
                border: 2px solid {self.COLORS['gray']};
                border-radius: 10px;
                padding: 15px;
                margin: 10px 0px;
            }}
            QLineEdit:focus {{
                border: 2px solid {self.COLORS['primary']};
            }}
        """)
        self.staff_code_entry.textChanged.connect(self.on_staff_code_change)

        self.greeting_label = QLabel("")
        self.greeting_label.setFont(QFont("Arial", 20, QFont.Weight.Medium))
        self.greeting_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.greeting_label.setStyleSheet(f"color: {self.COLORS['light']};")

        staff_code_layout.addWidget(staff_code_label)
        staff_code_layout.addWidget(self.staff_code_entry)
        staff_code_layout.addWidget(self.greeting_label)
        main_layout.addLayout(staff_code_layout)

        # Visitor Button with modern styling
        visitor_button = QPushButton("Visitor")
        visitor_button.setFont(QFont("Arial", 18))
        visitor_button.setMinimumSize(300, 60)
        visitor_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.COLORS['purple']};
                color: {self.COLORS['light']};
                border-radius: 10px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {self.COLORS['purple']}dd;
            }}
        """)
        visitor_button.clicked.connect(self.open_visitor_form)
        main_layout.addWidget(visitor_button, alignment=Qt.AlignmentFlag.AlignCenter)

        # Buttons Layout
        button_layout = QVBoxLayout()
        button_layout.setSpacing(20)

        # Clock In and Out Buttons Layout
        clock_buttons_layout = QHBoxLayout()
        clock_buttons_layout.setSpacing(20)

        # Fingerprint Scan Button
        if self.fingerprint_device_available:
            self.fingerprint_scan_button = QPushButton("🔍 Scan Fingerprint")
            self.fingerprint_scan_button.setFont(QFont("Inter", 16, QFont.Weight.Medium))
            self.fingerprint_scan_button.setMinimumSize(300, 55)
            self.fingerprint_scan_button.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(
                        x1: 0, y1: 0, x2: 0, y2: 1,
                        stop: 0 {self.COLORS['primary']},
                        stop: 1 {self.COLORS['primary']}cc
                    );
                    color: white;
                    border: none;
                    border-radius: 12px;
                    padding: 15px;
                    margin: 10px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: qlineargradient(
                        x1: 0, y1: 0, x2: 0, y2: 1,
                        stop: 0 {self.COLORS['primary']}dd,
                        stop: 1 {self.COLORS['primary']}aa
                    );
                    transform: translateY(-2px);
                }}
                QPushButton:pressed {{
                    background: {self.COLORS['primary']}88;
                    transform: translateY(0px);
                }}
                QPushButton:disabled {{
                    background: {self.COLORS['gray']};
                    color: {self.COLORS['text']}88;
                }}
            """)
            self.fingerprint_scan_button.clicked.connect(self.start_fingerprint_scan)
            button_layout.addWidget(self.fingerprint_scan_button)
            
            # Status label for feedback during scanning
            self.fingerprint_status_label = QLabel("Ready to scan")
            self.fingerprint_status_label.setFont(QFont("Inter", 11))
            self.fingerprint_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.fingerprint_status_label.setStyleSheet(f"""
                QLabel {{
                    color: {self.COLORS['text']};
                    background-color: {self.COLORS['light']};
                    border: 1px solid {self.COLORS['border']};
                    border-radius: 8px;
                    padding: 8px;
                    margin: 5px 10px;
                }}
            """)
            button_layout.addWidget(self.fingerprint_status_label)
        else:
            # Show unavailable status if no fingerprint device
            fingerprint_unavailable_label = QLabel("❌ Fingerprint Scanner: Unavailable")
            fingerprint_unavailable_label.setFont(QFont("Inter", 12))
            fingerprint_unavailable_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fingerprint_unavailable_label.setStyleSheet(f"""
                QLabel {{
                    color: {self.COLORS['gray']};
                    background-color: {self.COLORS['light']};
                    border: 2px solid {self.COLORS['gray']};
                    border-radius: 10px;
                    padding: 15px;
                    margin: 10px;
                }}
            """)
            button_layout.addWidget(fingerprint_unavailable_label)

        # Clock In Button
        self.clock_in_button = self.create_styled_button(
            "Enter Building",
            self.COLORS['success'],
            lambda: self.clock_action('in', self.staff_code_entry.text())
        )
        clock_buttons_layout.addWidget(self.clock_in_button)

        # Clock Out Button
        self.clock_out_button = self.create_styled_button(
            "Exit Building",
            self.COLORS['danger'],
            lambda: self.clock_action('out', self.staff_code_entry.text())
        )
        clock_buttons_layout.addWidget(self.clock_out_button)

        # Admin and Exit Buttons
        self.admin_button = self.create_styled_button(
            "Admin",
            self.COLORS['brown'],
            self.open_admin_tab
        )
        self.admin_button.hide()
        button_layout.addWidget(self.admin_button)

        self.exit_button = self.create_styled_button(
            "Exit",
            self.COLORS['gray'],
            self.close
        )
        self.exit_button.hide()
        button_layout.addWidget(self.exit_button)

        main_layout.addLayout(button_layout)
        main_layout.addLayout(clock_buttons_layout)

        self.central_widget.installEventFilter(self)

        # Clock display
        self.clock_label = QLabel()
        self.clock_label.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        self.clock_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.clock_label.setStyleSheet(f"""
            QLabel {{
                color: {self.COLORS['light']};
                background-color: {self.COLORS['lighter_dark']};
                border: 2px solid {self.COLORS['border']};
                border-radius: 15px;
                padding: 20px;
                margin: 15px;
            }}
        """)
        main_layout.addWidget(self.clock_label)

        # Modern footer
        footer = self.create_footer()
        main_layout.addWidget(footer)

        # Set modern gradient background
        self.setStyleSheet(f"""
            QMainWindow {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 {self.COLORS['dark']},
                    stop: 1 {self.COLORS['dark']}ee
                );
            }}
        """)

    def create_styled_button(self, text, color, callback):
        """Create a consistently styled button."""
        button = QPushButton(text)
        button.setFont(QFont("Inter", 18))
        button.setMinimumSize(300, 60)
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: {self.COLORS['light']};
                border-radius: 10px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {color}dd;
            }}
        """)
        button.clicked.connect(callback)
        return button

    def create_footer(self):
        """Create a modern footer."""
        footer = QLabel("© 2025 Andrei Iacob. All rights reserved.")
        footer.setFont(QFont("Inter", 10))
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setFixedHeight(40)
        footer.setStyleSheet(f"""
            color: {self.COLORS['gray']};
            margin: 10px 0px;
            padding: 5px;
        """)
        return footer




    def start_fingerprint_scan(self):
        """Start fingerprint scanning when button is clicked."""
        if not self.fingerprint_device_available:
            return
        
        # Disable the button during scanning
        self.fingerprint_scan_button.setEnabled(False)
        self.fingerprint_scan_button.setText("🔄 Scanning...")
        
        # Update status
        self.fingerprint_status_label.setText("👆 Place finger on scanner")
        self.fingerprint_status_label.setStyleSheet(f"""
            QLabel {{
                color: {self.COLORS['warning']};
                background-color: {self.COLORS['light']};
                border: 1px solid {self.COLORS['warning']};
                border-radius: 8px;
                padding: 8px;
                margin: 5px 10px;
            }}
        """)
        
        # Start the fingerprint authentication
        self.perform_fingerprint_authentication()
        
        logging.info("Fingerprint scan initiated by user")
    
    def reset_fingerprint_ui(self):
        """Reset the fingerprint UI to ready state."""
        if hasattr(self, 'fingerprint_scan_button'):
            self.fingerprint_scan_button.setEnabled(True)
            self.fingerprint_scan_button.setText("🔍 Scan Fingerprint")
        
        if hasattr(self, 'fingerprint_status_label'):
            self.fingerprint_status_label.setText("Ready to scan")
            self.fingerprint_status_label.setStyleSheet(f"""
                QLabel {{
                    color: {self.COLORS['text']};
                    background-color: {self.COLORS['light']};
                    border: 1px solid {self.COLORS['border']};
                    border-radius: 8px;
                    padding: 8px;
                    margin: 5px 10px;
                }}
            """)
    
    
    
    def perform_fingerprint_authentication(self):
        """Perform actual fingerprint authentication when finger is detected."""
        try:
            from fingerprint_manager import FingerprintThread
            
            # Full authentication scan with normal timeout
            self.fingerprint_thread = FingerprintThread(
                self.fingerprint_manager, 
                'authenticate',
                timeout=3  # Normal timeout for actual authentication
            )
            
            # Connect completion signal
            self.fingerprint_thread.finished.connect(self._on_fingerprint_authentication_result)
            self.fingerprint_thread.start()
            
        except Exception as e:
            logging.error(f"Fingerprint authentication error: {e}")
            # Resume finger detection
            QTimer.singleShot(1000, self.start_finger_detection_mode)
    
    def _on_fingerprint_authentication_result(self, success: bool, message: str, data: dict):
        """Handle fingerprint authentication result."""
        try:
            if success and data.get('employee_id'):
                staff_code = data['employee_id']
                
                # Auto-fill staff code
                self.staff_code_entry.setText(staff_code)
                
                # Update status to show recognition
                self.fingerprint_status_label.setText(f"✅ Recognized: {staff_code}")
                self.fingerprint_status_label.setStyleSheet(f"""
                    QLabel {{
                        color: {self.COLORS['success']};
                        background-color: {self.COLORS['light']};
                        border: 1px solid {self.COLORS['success']};
                        border-radius: 8px;
                        padding: 8px;
                        margin: 5px 10px;
                    }}
                """)
                
                # Show success message
                self.msg(f"Fingerprint recognized: {staff_code}", "info", "Welcome")
                logging.info(f"Fingerprint authentication successful: {staff_code}")
                
                # Reset UI after 3 seconds
                QTimer.singleShot(3000, self.reset_fingerprint_ui)
                
            elif "No fingerprint detected" in message:
                # No finger was placed
                self.fingerprint_status_label.setText("⚠️ No finger detected")
                self.fingerprint_status_label.setStyleSheet(f"""
                    QLabel {{
                        color: {self.COLORS['warning']};
                        background-color: {self.COLORS['light']};
                        border: 1px solid {self.COLORS['warning']};
                        border-radius: 8px;
                        padding: 8px;
                        margin: 5px 10px;
                    }}
                """)
                
                # Reset UI after 2 seconds
                QTimer.singleShot(2000, self.reset_fingerprint_ui)
                
            elif ("Authentication failed" in message or 
                  "Fingerprint verification failed" in message or
                  "not recognized" in message.lower()):
                # Fingerprint was detected but not recognized
                self.fingerprint_status_label.setText("❌ Not recognized")
                self.fingerprint_status_label.setStyleSheet(f"""
                    QLabel {{
                        color: {self.COLORS['danger']};
                        background-color: {self.COLORS['light']};
                        border: 1px solid {self.COLORS['danger']};
                        border-radius: 8px;
                        padding: 8px;
                        margin: 5px 10px;
                    }}
                """)
                
                # Show debug popup
                self.msg(f"Fingerprint scanned but not recognized: {message}", "warning", "Debug Info")
                logging.warning(f"Fingerprint not recognized: {message}")
                
                # Reset UI after 3 seconds
                QTimer.singleShot(3000, self.reset_fingerprint_ui)
                
            else:
                # Other errors
                self.fingerprint_status_label.setText(f"❌ Error: {message}")
                self.fingerprint_status_label.setStyleSheet(f"""
                    QLabel {{
                        color: {self.COLORS['danger']};
                        background-color: {self.COLORS['light']};
                        border: 1px solid {self.COLORS['danger']};
                        border-radius: 8px;
                        padding: 8px;
                        margin: 5px 10px;
                    }}
                """)
                
                logging.warning(f"Fingerprint authentication error: {message}")
                
                # Reset UI after 2 seconds
                QTimer.singleShot(2000, self.reset_fingerprint_ui)
                
        except Exception as e:
            logging.error(f"Error processing fingerprint authentication result: {e}")
            # Reset UI
            QTimer.singleShot(1000, self.reset_fingerprint_ui)

    def clock_action(self, action, staff_code):
        logger.log_system_event("Clock Action", f"Processing {action} for staff code {staff_code}")
        conn = sqlite3.connect(databasePath)
        c = conn.cursor()

        try:
            # Check if the staff exists
            c.execute('SELECT * FROM staff WHERE code = ?', (staff_code,))
            staff = c.fetchone()
            if not staff:
                logger.log_error(ValueError(f"Invalid staff code: {staff_code}"), "clock_action")
                conn.close()
                self.msg("Invalid user ID or staff code.", "warning", "Error")
                return

            if action == 'in':
                # Check if already clocked in but not on break
                c.execute('SELECT id FROM clock_records WHERE staff_code = ? AND clock_out_time IS NULL', (staff_code,))
                clock_record = c.fetchone()

                if clock_record:
                    if not self.on_break:
                        # Start Break
                        self.break_start_time = datetime.now()
                        self.on_break = True
                        logger.log_user_action(staff_code, "Break Start", f"Break started at {self.break_start_time}")
                        self.msg("Break started.", "info", "Success")
                    else:
                        logger.log_user_action(staff_code, "Break Error", "Attempted to start break while already on break")
                        self.msg("You are already on break.", "warning", "Warning")
                else:
                    # Regular Clock-In
                    clock_in_time = datetime.now().isoformat()
                    c.execute('INSERT INTO clock_records (staff_code, clock_in_time) VALUES (?, ?)',
                              (staff_code, clock_in_time))
                    conn.commit()
                    
                    # Get the record ID for backup
                    record_id = c.lastrowid
                    
                    # Create real-time backup
                    self.backup_clock_record(record_id, staff_code, clock_in_time, None)
                    
                    time_in = datetime.fromisoformat(clock_in_time).strftime('%H:%M')
                    logger.log_user_action(staff_code, "Clock In", f"Clocked in at {time_in}")
                    self.msg(f'Clock-in recorded successfully at {time_in}', 'info', 'Success')

            elif action == 'out':
                # Check if on break
                if self.on_break:
                    # End Break
                    break_end_time = datetime.now()
                    break_duration = (break_end_time - self.break_start_time).total_seconds() / 60
                    c.execute('UPDATE clock_records SET break_time = ? WHERE staff_code = ? AND clock_out_time IS NULL',
                              (str(break_duration), staff_code))
                    conn.commit()
                    
                    # Get the updated record for backup
                    c.execute('SELECT id, clock_in_time, clock_out_time, notes FROM clock_records WHERE staff_code = ? AND clock_out_time IS NULL', (staff_code,))
                    updated_record = c.fetchone()
                    if updated_record:
                        self.backup_clock_record(updated_record[0], staff_code, updated_record[1], updated_record[2], updated_record[3], str(break_duration))
                    
                    self.on_break = False
                    self.break_start_time = None
                    logger.log_user_action(staff_code, "Break End", f"Break ended. Duration: {break_duration:.2f} minutes")
                    self.msg(f"Break ended. Duration: {break_duration:.2f} minutes.", "info", "Success")
                else:
                    # Regular Clock-Out
                    clock_out_time = datetime.now().isoformat()
                    c.execute('SELECT id FROM clock_records WHERE staff_code = ? AND clock_out_time IS NULL', (staff_code,))
                    clock_record = c.fetchone()
                    if not clock_record:
                        logger.log_error(ValueError(f"No active clock-in found for staff code: {staff_code}"), "clock_action")
                        conn.close()
                        self.msg("You are not clocked in.", "warning", "Error")
                        return
                    c.execute('UPDATE clock_records SET clock_out_time = ? WHERE id = ?', (clock_out_time, clock_record[0]))
                    conn.commit()
                    
                    # Get the updated record for backup
                    c.execute('SELECT clock_in_time, notes, break_time FROM clock_records WHERE id = ?', (clock_record[0],))
                    updated_record = c.fetchone()
                    if updated_record:
                        self.backup_clock_record(clock_record[0], staff_code, updated_record[0], clock_out_time, updated_record[1], updated_record[2])
                    
                    time_out = datetime.fromisoformat(clock_out_time).strftime('%H:%M')
                    logger.log_user_action(staff_code, "Clock Out", f"Clocked out at {time_out}")
                    self.msg(f'Clock-out recorded successfully at {time_out}', 'info', 'Success')

            else:
                logger.log_error(ValueError(f"Unknown action: {action}"), "clock_action")
                conn.close()
                self.msg(f'Unknown action: {action}', 'warning', 'Error')

        except Exception as e:
            logger.log_error(e, f"clock_action - Action: {action}, Staff Code: {staff_code}")
            self.msg(f"An error occurred: {str(e)}", "warning", "Error")
        finally:
            conn.close()

    def msg(self, message, state, title):
        msgBox = QMessageBox()
        msgBox.setWindowTitle(title)
        msgBox.setText(message)
        if state == "info":
            msgBox.setIcon(QMessageBox.Icon.Information)
        elif state == "warning":
            msgBox.setIcon(QMessageBox.Icon.Warning)
        elif state == "critical":
            msgBox.setIcon(QMessageBox.Icon.Critical)
        closeTimer =  QTimer(msgBox, singleShot = True, interval = 3000, timeout = msgBox.close)
        closeTimer.start()
        msgBox.exec()

    def process_clock_action(self, user_id, action="in"):
        """Process clock-in or clock-out based on user ID or staff code."""
        conn = sqlite3.connect(databasePath)
        c = conn.cursor()

        # Check if the staff exists
        c.execute('SELECT * FROM staff WHERE code = ?', (user_id,))
        staff = c.fetchone()
        if not staff:
            conn.close()
            self.msg("Invalid user ID or staff code.", "warning", "Error")
            return

        if action == "in":
            self.clock_action("in", user_id)
        elif action == "out":
            self.clock_action("out", user_id)
        else:
            self.msg(f"Unknown action: {action}", "warning", "Error")
        conn.close()

    def on_staff_code_change(self):
        staff_code = self.staff_code_entry.text()
        if len(staff_code) == 4 and staff_code.isdigit():
            conn = sqlite3.connect(databasePath)
            c = conn.cursor()
            c.execute('SELECT name, role FROM staff WHERE code = ?', (staff_code,))
            staff = c.fetchone()
            conn.close()
            if staff:
                self.greeting_label.setText(f'Hello, {staff[0]}!')
                if hasattr(self, 'role_entry'):
                    self.role_entry.setText(staff[1] if staff[1] else '')

                # Check if clocked in
                conn = sqlite3.connect(databasePath)
                c = conn.cursor()
                c.execute('SELECT id FROM clock_records WHERE staff_code = ? AND clock_out_time IS NULL', (staff_code,))
                clock_record = c.fetchone()
                conn.close()

                if clock_record:
                    if self.on_break:
                        self.clock_out_button.setText("End Break")
                    else:
                        self.clock_in_button.setText("Start Break")
                else:
                    self.clock_in_button.setText("Enter Building")
            else:
                self.greeting_label.setText("")
                if hasattr(self, 'role_entry'):
                    self.role_entry.setText("")
        elif staff_code == self.settings.get("admin_pin", "123456"):  # Admin code
            self.greeting_label.setText("Admin Mode Activated")
            self.admin_button.show()
            self.admin_button.click()
            self.admin_button.setVisible(True)  # Show the admin button
        elif staff_code == self.settings.get("exit_code", "654321"):  # Exit code
            self.greeting_label.setText("Exit Mode Activated")
            self.close()
        elif staff_code =='111111':  # Fire code (keep hardcoded for safety)
            self.greeting_label.setText("Fire!!!!!!")
            self.fire()
        else:
            self.greeting_label.setText('')
            self.admin_button.hide()

    def fire(self):
        logging.info("Fire system triggered!")
        
        try:
            # First handle staff records
            logging.info("Gathering current time and staff records")
            time_now = datetime.now().strftime('%Y-%m-%d')
            
            conn = sqlite3.connect(databasePath)
            c = conn.cursor()

            # Get staff records
            c.execute('''
                SELECT s.name, c.clock_in_time
                FROM clock_records c
                JOIN staff s ON c.staff_code = s.code
                WHERE DATE(c.clock_in_time) = ?
            ''', (time_now,))
            staff_records = c.fetchall()

            # Get visitor records - modified query to get current visitors
            c.execute('''
                SELECT name, car_reg, purpose, time_in 
                FROM visitors 
                WHERE DATE(time_in) = ? 
                AND (time_out IS NULL OR DATE(time_out) > ?)
            ''', (time_now, time_now))
            visitor_records = c.fetchall()

            logging.info(f"Found {len(staff_records)} staff records and {len(visitor_records)} visitor records")
            conn.close()

            # Remove duplicates and keep only the first occurrence of each staff name
            unique_records = {}
            for record in staff_records:
                name = record[0]
                clock_in_time = record[1]
                if name not in unique_records:
                    unique_records[name] = clock_in_time

            if not unique_records and not visitor_records:
                self.msg("No staff or visitors in the building.", "info", "Fire List")
                return

            # Generate the staff PDF
            doc = SimpleDocTemplate('fire.pdf')
            elements = []
            styles = getSampleStyleSheet()

            # Add title and current time
            elements.append(Paragraph("FIRE EVACUATION LIST", styles['Title']))
            current_time = datetime.now().strftime("%d/%m/%Y %H:%M")
            elements.append(Paragraph(f"Generated at: {current_time}", styles['Normal']))
            elements.append(Spacer(1, 20))

            # Add staff section
            if unique_records:
                elements.append(Paragraph("Staff Currently In Building:", styles['Heading2']))
                elements.append(Spacer(1, 12))

                # Create staff table
                staff_data = [["Name", "Clock In Time"]]
                for name, clock_in_time in unique_records.items():
                    readable_time = datetime.fromisoformat(clock_in_time).strftime('%H:%M')
                    staff_data.append([name, readable_time])

                staff_table = Table(staff_data, colWidths=[300, 100])  # Set specific column widths
                staff_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                elements.append(staff_table)
                elements.append(Spacer(1, 20))

            # Add visitors section
            if visitor_records:
                elements.append(Paragraph("Visitors Currently In Building:", styles['Heading2']))
                elements.append(Spacer(1, 12))

                # Create visitors table
                visitor_data = [["Name", "Car Registration", "Purpose", "Time In"]]
                for visitor in visitor_records:
                    name, car_reg, purpose, time_in = visitor[0:4]
                    time_in_formatted = datetime.fromisoformat(time_in).strftime('%H:%M') if time_in else "N/A"
                    visitor_data.append([name, car_reg, purpose, time_in_formatted])

                visitor_table = Table(visitor_data, colWidths=[150, 100, 150, 100])  # Set specific column widths
                visitor_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                elements.append(visitor_table)

            # Add footer with signature lines
            elements.append(Spacer(1, 30))
            elements.append(Paragraph("Fire Marshal Signature: _______________________", styles['Normal']))
            elements.append(Spacer(1, 20))
            elements.append(Paragraph("Time Completed: _______________________", styles['Normal']))

            # Build and print the document
            doc.build(elements)
            self.print_via_jetdirect('fire.pdf')
            self.msg("Fire list printed successfully.", "info", "Fire List")

        except Exception as e:
            self.msg(f"Error generating fire list: {e}", "warning", "Error")
            logging.error(f"Error in fire system: {e}")

    def open_settings_menu(self):
        """
        Open the settings dialog, including start day, end day, and printer IP settings.
        """
        settings_dialog = QDialog(self)
        settings_dialog.setWindowTitle("Settings")
        settings_dialog.setFixedSize(500, 400)
        settings_dialog.setStyleSheet(f"""
            QDialog {{
                background: {self.COLORS['dark']};
                color: {self.COLORS['light']};
            }}
            QLabel {{
                color: {self.COLORS['light']};
                font-family: Arial;
            }}
            QLineEdit {{
                background-color: {self.COLORS['dark']};
                color: {self.COLORS['light']};
                border: 2px solid {self.COLORS['gray']};
                border-radius: 8px;
                padding: 8px;
                font-family: Arial;
            }}
            QLineEdit:focus {{
                border: 2px solid {self.COLORS['primary']};
            }}
            QPushButton {{
                background-color: {self.COLORS['primary']};
                color: {self.COLORS['light']};
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-family: Arial;
            }}
            QPushButton:hover {{
                background-color: {self.COLORS['primary']}dd;
            }}
        """)

        layout = QVBoxLayout(settings_dialog)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # Start Day and End Day (Side by Side)
        day_layout = QHBoxLayout()
        start_label = QLabel("Start Day:")
        start_label.setFont(QFont("Inter", 12))
        self.start_day_input = QLineEdit(str(self.settings["start_day"]))
        self.start_day_input.setFont(QFont("Inter", 12))
        self.start_day_input.setFixedWidth(80)

        end_label = QLabel("End Day:")
        end_label.setFont(QFont("Inter", 12))
        self.end_day_input = QLineEdit(str(self.settings["end_day"]))
        self.end_day_input.setFont(QFont("Inter", 12))
        self.end_day_input.setFixedWidth(80)

        day_layout.addWidget(start_label)
        day_layout.addWidget(self.start_day_input)
        day_layout.addSpacing(40)  # Add some space between Start and End inputs
        day_layout.addWidget(end_label)
        day_layout.addWidget(self.end_day_input)
        layout.addLayout(day_layout)

        # Printer IP Address Input
        ip_label = QLabel("Printer IP:")
        ip_label.setFont(QFont("Inter", 12))
        self.printer_ip_input = QLineEdit(self.settings.get("printer_IP", ""))
        self.printer_ip_input.setFont(QFont("Inter", 12))
        self.printer_ip_input.setPlaceholderText("Enter Printer IP Address")
        layout.addWidget(ip_label)
        layout.addWidget(self.printer_ip_input)

        # Admin Pin and Exit Code (Side by Side)
        pin_layout = QHBoxLayout()
        admin_pin_label = QLabel("Admin PIN:")
        admin_pin_label.setFont(QFont("Inter", 12))
        self.admin_pin_input = QLineEdit(self.settings.get("admin_pin", "123456"))
        self.admin_pin_input.setFont(QFont("Inter", 12))
        self.admin_pin_input.setFixedWidth(120)

        exit_code_label = QLabel("Exit Code:")
        exit_code_label.setFont(QFont("Inter", 12))
        self.exit_code_input = QLineEdit(self.settings.get("exit_code", "654321"))
        self.exit_code_input.setFont(QFont("Inter", 12))
        self.exit_code_input.setFixedWidth(120)

        pin_layout.addWidget(admin_pin_label)
        pin_layout.addWidget(self.admin_pin_input)
        pin_layout.addSpacing(40)  # Add some space between Admin PIN and Exit Code inputs
        pin_layout.addWidget(exit_code_label)
        pin_layout.addWidget(self.exit_code_input)
        layout.addLayout(pin_layout)

        # Test Connection Button
        test_button = QPushButton("Test Printer Connection")
        test_button.setFont(QFont("Inter", 12))
        test_button.clicked.connect(lambda: self.test_printer_connection(self.printer_ip_input.text().strip()))
        layout.addWidget(test_button)

        # Save Button
        save_button = QPushButton("Save Settings")
        save_button.setFont(QFont("Inter", 12))
        save_button.clicked.connect(self.save_settings_from_menu)
        layout.addWidget(save_button)

        settings_dialog.exec()

    def test_printer_connection(self, ip_address):
        """Test both ping and port 9100 connection to the printer (with UI feedback)."""
        success, message = self.test_printer_connection_silent(ip_address)
        
        if success:
            self.msg("Printer connection successful!", "info", "Success")
        else:
            self.msg(message, "warning", "Error")
            
        return success, message

    def test_printer_connection_silent(self, ip_address):
        """Test both ping and port 9100 connection to the printer (without UI feedback)."""
        if not ip_address.strip():
            return False, "IP address cannot be empty"
            
        if not self.ping_printer(ip_address):
            return False, "Printer is not responding to ping"
            
        try:
            # Try to connect to port 9100 (standard printer port)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)  # 2 second timeout
            result = sock.connect_ex((ip_address, 9100))
            sock.close()
            
            if result == 0:
                return True, "Printer connection successful"
            else:
                return False, "Printer port 9100 is not accessible"
                
        except Exception as e:
            logging.error(f"Error testing printer connection: {e}")
            return False, f"Connection error: {str(e)}"

    def save_settings_from_menu(self):
        """
        Save the settings from the settings menu with printer validation.
        """
        try:
            # Validate and save start and end days
            start_day = int(self.start_day_input.text())
            end_day = int(self.end_day_input.text())
            if not (1 <= start_day <= 31 and 1 <= end_day <= 31):
                raise ValueError("Days must be between 1 and 31.")

            # Validate Printer IP
            printer_ip = self.printer_ip_input.text().strip()
            if not printer_ip:
                raise ValueError("Printer IP cannot be empty.")

            # Validate Admin PIN and Exit Code
            admin_pin = self.admin_pin_input.text().strip()
            exit_code = self.exit_code_input.text().strip()
            
            if not admin_pin:
                raise ValueError("Admin PIN cannot be empty.")
            if not exit_code:
                raise ValueError("Exit Code cannot be empty.")
            if len(admin_pin) < 4:
                raise ValueError("Admin PIN must be at least 4 characters.")
            if len(exit_code) < 4:
                raise ValueError("Exit Code must be at least 4 characters.")
            if admin_pin == exit_code:
                raise ValueError("Admin PIN and Exit Code cannot be the same.")

            # Show testing message
            self.msg("Testing printer connection...", "info", "Testing")
            
            # Test printer connection
            success, message = self.test_printer_connection_silent(printer_ip)
            if not success:
                # Show dialog asking if user wants to save anyway
                reply = QMessageBox.question(
                    self,
                    "Printer Connection Failed",
                    f"Printer validation failed: {message}\n\nDo you want to save the settings anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.No:
                    return

            # Save all settings
            self.settings["start_day"] = start_day
            self.settings["end_day"] = end_day
            self.settings["printer_IP"] = printer_ip
            self.settings["admin_pin"] = admin_pin
            self.settings["exit_code"] = exit_code

            self.save_settings()
            
            if success:
                self.msg("Settings saved successfully. Printer connection verified.", "info", "Success")
            else:
                self.msg("Settings saved successfully. (Printer connection could not be verified)", "info", "Success")
            
        except ValueError as e:
            self.msg(f"Invalid settings: {e}", "warning", "Error")
        except Exception as e:
            self.msg(f"Error saving settings: {e}", "warning", "Error")
            logging.error(f"Error saving settings: {e}")

    def open_admin_tab(self):
        logging.info("Opening admin tab")
        self.admin_tab = QDialog(self)
        self.admin_tab.setWindowTitle('StaffClock Admin Panel')
        self.admin_tab.setFixedSize(1200, 800)
        self.admin_tab.setStyleSheet(f"""
            QDialog {{
                background: {self.COLORS['dark']};
                color: {self.COLORS['light']};
            }}
            QTabWidget {{
                background: {self.COLORS['dark']};
                border: none;
            }}
            QTabWidget::pane {{
                border: 2px solid {self.COLORS['gray']};
                border-radius: 8px;
                background: {self.COLORS['dark']};
            }}
            QTabBar::tab {{
                background: {self.COLORS['gray']};
                color: {self.COLORS['light']};
                padding: 12px 20px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-family: Inter;
                font-weight: bold;
            }}
            QTabBar::tab:selected {{
                background: {self.COLORS['primary']};
                color: white;
            }}
            QTabBar::tab:hover {{
                background: {self.COLORS['primary']}aa;
            }}
            QLabel {{
                color: {self.COLORS['light']};
                font-family: Inter;
            }}
            QLineEdit {{
                background-color: {self.COLORS['dark']};
                color: {self.COLORS['light']};
                border: 2px solid {self.COLORS['gray']};
                border-radius: 8px;
                padding: 8px;
                font-family: Inter;
            }}
            QLineEdit:focus {{
                border: 2px solid {self.COLORS['primary']};
            }}
            QTextEdit {{
                background-color: {self.COLORS['dark']};
                color: {self.COLORS['light']};
                border: 2px solid {self.COLORS['gray']};
                border-radius: 8px;
                padding: 8px;
                font-family: Consolas, monospace;
            }}
            QProgressBar {{
                border: 2px solid {self.COLORS['gray']};
                border-radius: 8px;
                background-color: {self.COLORS['dark']};
                text-align: center;
                font-weight: bold;
                color: {self.COLORS['light']};
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.COLORS['success']}, stop:1 {self.COLORS['primary']});
                border-radius: 6px;
            }}
            QListWidget {{
                background-color: {self.COLORS['dark']};
                color: {self.COLORS['light']};
                border: 2px solid {self.COLORS['gray']};
                border-radius: 8px;
                padding: 5px;
            }}
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {self.COLORS['gray']};
            }}
            QListWidget::item:selected {{
                background-color: {self.COLORS['primary']};
            }}
        """)

        # Store the admin tab state
        self.admin_was_open = False
        self.admin_tab.closeEvent = self.handle_admin_close

        # Create main layout
        main_layout = QVBoxLayout(self.admin_tab)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Create tab widget
        self.admin_tabs = QTabWidget()
        main_layout.addWidget(self.admin_tabs)

        # Create tabs
        self.create_staff_management_tab()
        self.create_timesheet_management_tab()
        self.create_system_management_tab()
        self.create_monitoring_tab()

        self.admin_tab.exec()

    def create_staff_management_tab(self):
        """Create the staff management tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Header
        header = QLabel("👥 Staff Management")
        header.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {self.COLORS['primary']}; margin-bottom: 10px;")
        layout.addWidget(header)

        # Staff input section
        input_section = QWidget()
        input_layout = QGridLayout(input_section)
        input_layout.setSpacing(15)

        # Name input
        name_label = QLabel("Staff Name:")
        name_label.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        self.name_entry = QLineEdit()
        self.name_entry.setFont(QFont("Inter", 14))
        self.name_entry.setPlaceholderText("Enter staff member name...")
        self.name_entry.textChanged.connect(self.update_pin_label)
        self.name_entry.editingFinished.connect(lambda: self.update_role_from_name(self.name_entry.text()))
        
        # Role input
        role_label = QLabel("Role:")
        role_label.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        self.role_entry = QLineEdit()
        self.role_entry.setFont(QFont("Inter", 14))
        self.role_entry.setPlaceholderText("Enter role...")

        # PIN display
        self.pin_label = QLabel("PIN: Not Found")
        self.pin_label.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        self.pin_label.setStyleSheet(f"color: {self.COLORS['warning']}; padding: 10px; border: 2px solid {self.COLORS['gray']}; border-radius: 8px;")

        # Add completers
        role_completer = QCompleter(self.fetch_unique_roles(), self)
        role_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        role_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.role_entry.setCompleter(role_completer)

        name_completer = QCompleter(self.fetch_staff_names_and_roles(), self)
        name_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        name_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.name_entry.setCompleter(name_completer)

        # Layout inputs
        input_layout.addWidget(name_label, 0, 0)
        input_layout.addWidget(self.name_entry, 0, 1, 1, 2)
        input_layout.addWidget(role_label, 1, 0)
        input_layout.addWidget(self.role_entry, 1, 1, 1, 2)
        input_layout.addWidget(QLabel("PIN:"), 2, 0)
        input_layout.addWidget(self.pin_label, 2, 1, 1, 2)

        layout.addWidget(input_section)

        # Action buttons
        button_layout = QGridLayout()
        button_layout.setSpacing(15)

        staff_buttons = [
            ("➕ Add Staff", self.COLORS['success'], self.add_staff, 0, 0),
            ("🗑️ Delete Staff", self.COLORS['danger'], self.remove_staff, 0, 1),
            ("📝 Add Comment", self.COLORS['purple'], self.add_comment, 1, 0),
            ("📋 View Records", self.COLORS['primary'], self.open_records_tab, 1, 1),
        ]

        for text, color, callback, row, col in staff_buttons:
            button = self.create_modern_button(text, color, callback)
            button_layout.addWidget(button, row, col)

        layout.addLayout(button_layout)
        
        # Add spacer
        layout.addStretch()

        self.admin_tabs.addTab(tab, "👥 Staff")

    def create_timesheet_management_tab(self):
        """Create the timesheet management tab with integrated progressive features."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        # Header
        header = QLabel("📊 Smart Timesheet Management")
        header.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {self.COLORS['primary']}; margin-bottom: 10px;")
        layout.addWidget(header)

        # Top section with status and progress
        top_section = QWidget()
        top_layout = QHBoxLayout(top_section)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # Status display
        self.status_display = QLabel("Loading status...")
        self.status_display.setFont(QFont("Inter", 12))
        self.status_display.setStyleSheet(f"background-color: {self.COLORS['gray']}; padding: 15px; border-radius: 8px;")
        top_layout.addWidget(self.status_display, 1) # Give it more stretch

        # Progress bar for generation
        self.generation_progress = QProgressBar()
        self.generation_progress.setVisible(False)
        self.generation_progress.setFixedHeight(35)
        top_layout.addWidget(self.generation_progress, 1)

        layout.addWidget(top_section)

        # Worker status lists
        worker_lists_layout = QHBoxLayout()
        worker_lists_layout.setSpacing(20)

        # Completed Workers List
        completed_widget = QWidget()
        completed_layout = QVBoxLayout(completed_widget)
        completed_label = QLabel("✅ Completed Workers")
        completed_label.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        completed_layout.addWidget(completed_label)
        self.completed_workers_list = QListWidget()
        completed_layout.addWidget(self.completed_workers_list)
        worker_lists_layout.addWidget(completed_widget)

        # Pending Workers List
        pending_widget = QWidget()
        pending_layout = QVBoxLayout(pending_widget)
        pending_label = QLabel("⏳ Pending Workers")
        pending_label.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        pending_layout.addWidget(pending_label)
        self.pending_workers_list = QListWidget()
        pending_layout.addWidget(self.pending_workers_list)
        worker_lists_layout.addWidget(pending_widget)
        
        layout.addLayout(worker_lists_layout)

        # Log area for detailed updates
        log_label = QLabel("📄 Generation Log")
        log_label.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        layout.addWidget(log_label)
        self.generation_log_area = QTextEdit()
        self.generation_log_area.setReadOnly(True)
        self.generation_log_area.setFixedHeight(150)
        layout.addWidget(self.generation_log_area)


        # Buttons section
        buttons_section = QGridLayout()
        buttons_section.setSpacing(15)

        # Progressive buttons
        prog_buttons = [
            ("🚀 Start Progressive Generation", self.COLORS['success'], self.start_integrated_progressive_generation, 0, 0),
            ("📊 Refresh Worker Status", self.COLORS['primary'], self.show_integrated_status, 0, 1),
            ("🔄 Check Monitor Status", self.COLORS['warning'], self.show_monitoring_status, 1, 0),
            ("🛑 Stop Monitoring", self.COLORS['danger'], self.stop_background_monitoring, 1, 1),
        ]
        for text, color, callback, row, col in prog_buttons:
            button = self.create_modern_button(text, color, callback)
            buttons_section.addWidget(button, row, col)

        # Traditional buttons
        trad_buttons = [
            ("📝 Generate Single Timesheet", self.COLORS['purple'], lambda: self.generate_one_timesheet(), 0, 2),
            ("🖨️ Print Timesheet", self.COLORS['primary'], lambda: self.preparePrint("timesheet"), 1, 2),
        ]
        for text, color, callback, row, col in trad_buttons:
            button = self.create_modern_button(text, color, callback)
            buttons_section.addWidget(button, row, col)

        layout.addLayout(buttons_section)

        # Auto-update status
        self.update_timesheet_status()

        self.admin_tabs.addTab(tab, "📊 Timesheets")

    def create_system_management_tab(self):
        """Create the system management tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Header
        header = QLabel("⚙️ System Management")
        header.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {self.COLORS['primary']}; margin-bottom: 10px;")
        layout.addWidget(header)

        # System controls
        button_layout = QGridLayout()
        button_layout.setSpacing(15)

        system_buttons = [
            ("⚙️ Settings", self.COLORS['gray'], self.open_settings_menu, 0, 0),
            ("👥 View Visitors", self.COLORS['brown'], self.open_visitors_tab, 0, 1),
            ("📦 Archive Management", self.COLORS['warning'], self.open_archive_management, 1, 0),
            ("🔐 Fingerprint Management", self.COLORS['success'], self.open_fingerprint_management, 1, 1),
            ("🛠️ Database Maintenance", self.COLORS['gray'], self.open_database_maintenance, 2, 0),
            ("❌ Close Admin Panel", self.COLORS['danger'], self.admin_tab.close, 2, 1),
        ]

        for text, color, callback, row, col in system_buttons:
            button = self.create_modern_button(text, color, callback)
            button_layout.addWidget(button, row, col)

        layout.addLayout(button_layout)
        
        # Add spacer
        layout.addStretch()

        self.admin_tabs.addTab(tab, "⚙️ System")

    def create_monitoring_tab(self):
        """Create the live monitoring tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Header
        header = QLabel("🔄 Live Monitoring")
        header.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {self.COLORS['primary']}; margin-bottom: 10px;")
        layout.addWidget(header)

        # Monitoring status
        self.monitoring_status_label = QLabel("🔍 Checking monitoring status...")
        self.monitoring_status_label.setFont(QFont("Inter", 12))
        self.monitoring_status_label.setStyleSheet(f"""
            background-color: {self.COLORS['gray']};
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid {self.COLORS['warning']};
        """)
        layout.addWidget(self.monitoring_status_label)

        # Active workers list
        workers_header = QLabel("👥 Active Workers")
        workers_header.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        workers_header.setStyleSheet(f"color: {self.COLORS['success']}; margin-top: 20px;")
        layout.addWidget(workers_header)

        self.active_workers_list = QListWidget()
        self.active_workers_list.setMaximumHeight(200)
        layout.addWidget(self.active_workers_list)

        # Monitoring controls
        control_layout = QHBoxLayout()
        refresh_btn = self.create_modern_button("🔄 Refresh", self.COLORS['primary'], self.refresh_monitoring_display)
        control_layout.addWidget(refresh_btn)
        control_layout.addStretch()

        layout.addLayout(control_layout)

        # Auto-update monitoring
        self.refresh_monitoring_display()

        self.admin_tabs.addTab(tab, "🔄 Monitor")

    def create_modern_button(self, text, color, callback):
        """Create a modern styled button."""
        button = QPushButton(text)
        button.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        button.setMinimumSize(200, 45)
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border-radius: 8px;
                border: none;
                padding: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {color}dd;
                transform: translateY(-1px);
            }}
            QPushButton:pressed {{
                background-color: {color}aa;
                transform: translateY(1px);
            }}
        """)
        button.clicked.connect(callback)
        return button

    def start_integrated_progressive_generation(self):
        """Starts the progressive generation thread and connects its signals to the UI."""
        try:
            from progressive_timesheet_generator import ProgressiveTimesheetGenerator, get_timesheet_date_range

            # Clear previous results
            self.completed_workers_list.clear()
            self.pending_workers_list.clear()
            self.generation_log_area.clear()
            self.generation_progress.setValue(0)
            self.generation_progress.setVisible(True)

            self.generation_log_area.append(f"[{datetime.now().strftime('%H:%M:%S')}] Starting progressive generation...")

            # Get date range
            start_date, end_date = get_timesheet_date_range(self.database_path)
            
            # Create and connect the generator thread
            self.progressive_generator_thread = ProgressiveTimesheetGenerator(self.database_path, start_date, end_date)

            self.progressive_generator_thread.worker_completed.connect(self.on_worker_completed_integrated)
            self.progressive_generator_thread.worker_pending.connect(self.on_worker_pending_integrated)
            self.progressive_generator_thread.generation_progress.connect(self.on_progress_update_integrated)
            self.progressive_generator_thread.all_completed.connect(self.on_all_completed_integrated)
            self.progressive_generator_thread.status_update.connect(self.on_status_update_integrated)

            self.progressive_generator_thread.start()
            self.on_status_update_integrated("🚀 Generation process started.")

        except Exception as e:
            self.on_status_update_integrated(f"❌ Error starting generation: {e}")
            logging.error(f"Failed to start integrated progressive generation: {e}")

    def on_worker_completed_integrated(self, name, status, details):
        item_text = f"{name} - {status}"
        if 'total_hours' in details:
            item_text += f" ({details.get('total_hours', 0):.1f}h)"
        
        item = QListWidgetItem(item_text)
        if "Generated" in status or "No Records" in status:
            item.setForeground(QColor(self.COLORS['success']))
        elif "Failed" in status:
            item.setForeground(QColor(self.COLORS['danger']))
        
        self.completed_workers_list.addItem(item)
        self.generation_log_area.append(f"[{datetime.now().strftime('%H:%M:%S')}] COMPLETED: {name} - {status}")

    def on_worker_pending_integrated(self, name, status, details):
        # Check if worker is already in the list
        for i in range(self.pending_workers_list.count()):
            item = self.pending_workers_list.item(i)
            if item.text().startswith(name):
                item.setText(f"{name} - {status}")
                return
        
        # If not, add a new item
        item = QListWidgetItem(f"{name} - {status}")
        item.setForeground(QColor(self.COLORS['warning']))
        self.pending_workers_list.addItem(item)
        self.generation_log_area.append(f"[{datetime.now().strftime('%H:%M:%S')}] PENDING: {name} - {status}")

    def on_progress_update_integrated(self, completed, total):
        if total > 0:
            self.generation_progress.setMaximum(total)
            self.generation_progress.setValue(completed)
            self.generation_progress.setFormat(f"{(completed/total)*100:.1f}%")

    def on_all_completed_integrated(self, stats):
        message = "🎊 All workers processed!"
        self.on_status_update_integrated(message)
        QMessageBox.information(self, "Generation Complete", message)
        self.generation_progress.setFormat("Complete!")

    def on_status_update_integrated(self, message):
        self.status_display.setText(message)
        self.generation_log_area.append(f"[{datetime.now().strftime('%H:%M:%S')}] STATUS: {message}")
        self.generation_log_area.ensureCursorVisible()

    def show_integrated_status(self):
        """Show worker status in the integrated display."""
        self.update_timesheet_status()

    def show_monitoring_status(self):
        """Show monitoring status in the integrated display."""
        self.refresh_monitoring_display()

    def update_timesheet_status(self):
        """Update the timesheet status display."""
        try:
            conn = sqlite3.connect(databasePath)
            c = conn.cursor()
            
            # Get worker counts
            c.execute('SELECT COUNT(*) FROM staff')
            total_workers = c.fetchone()[0]
            
            c.execute('SELECT COUNT(DISTINCT cr.staff_code) FROM clock_records cr WHERE cr.clock_out_time IS NULL')
            active_workers = c.fetchone()[0]
            
            completed_workers = total_workers - active_workers
            
            conn.close()
            
            # Update display
            status_text = f"""📊 WORKER STATUS OVERVIEW
            
👥 Total Workers: {total_workers}
✅ Completed Workers: {completed_workers} (ready for timesheets)
⏳ Active Workers: {active_workers} (need monitoring)

💡 Recommendation: {'Use Progressive Generation to handle all workers automatically!' if active_workers > 0 else 'All workers completed - safe to generate all timesheets!'}"""

            self.status_display.setText(status_text)
            
            if active_workers == 0:
                self.status_display.setStyleSheet(f"""
                    background-color: {self.COLORS['success']}33;
                    padding: 15px;
                    border-radius: 8px;
                    border-left: 4px solid {self.COLORS['success']};
                """)
            else:
                self.status_display.setStyleSheet(f"""
                    background-color: {self.COLORS['warning']}33;
                    padding: 15px;
                    border-radius: 8px;
                    border-left: 4px solid {self.COLORS['warning']};
                """)
                
        except Exception as e:
            self.status_display.setText(f"❌ Error loading status: {e}")

    def refresh_monitoring_display(self):
        """Refresh the monitoring display."""
        try:
            from background_timesheet_monitor import get_background_monitor
            
            monitor = get_background_monitor()
            
            if monitor and monitor.monitoring_active:
                status = monitor.get_monitoring_status()
                
                self.monitoring_status_label.setText(f"""🔄 BACKGROUND MONITORING ACTIVE
                
📊 Monitoring {status['pending_workers']} workers
⏱️ Check interval: {status['check_interval']} seconds  
📄 Timesheets generated: {status['total_generated']}""")
                
                self.monitoring_status_label.setStyleSheet(f"""
                    background-color: {self.COLORS['success']}33;
                    padding: 15px;
                    border-radius: 8px;
                    border-left: 4px solid {self.COLORS['success']};
                """)
                
                # Update active workers list
                self.active_workers_list.clear()
                
                if status['worker_list']:
                    conn = sqlite3.connect(databasePath)
                    c = conn.cursor()
                    for staff_code in status['worker_list']:
                        c.execute('SELECT name, role FROM staff WHERE code = ?', (staff_code,))
                        result = c.fetchone()
                        if result:
                            name, role = result
                            self.active_workers_list.addItem(f"👤 {name} ({staff_code}) - {role}")
                    conn.close()
                else:
                    self.active_workers_list.addItem("✅ No workers currently being monitored")
                    
            else:
                self.monitoring_status_label.setText("📭 No Background Monitoring Active")
                self.monitoring_status_label.setStyleSheet(f"""
                    background-color: {self.COLORS['gray']};
                    padding: 15px;
                    border-radius: 8px;
                    border-left: 4px solid {self.COLORS['gray']};
                """)
                
                # Show all active workers
                self.active_workers_list.clear()
                conn = sqlite3.connect(databasePath)
                c = conn.cursor()
                c.execute("""
                    SELECT DISTINCT cr.staff_code, s.name, s.role
                    FROM clock_records cr
                    JOIN staff s ON cr.staff_code = s.code
                    WHERE cr.clock_out_time IS NULL
                    ORDER BY s.name
                """)
                active_workers = c.fetchall()
                conn.close()
                
                if active_workers:
                    for staff_code, name, role in active_workers:
                        self.active_workers_list.addItem(f"⏳ {name} ({staff_code}) - {role}")
                else:
                    self.active_workers_list.addItem("✅ No active workers found")
                    
        except Exception as e:
            self.monitoring_status_label.setText(f"❌ Error: {e}")

    def show_timesheet_generation_status(self):
        '''Show current status of timesheet generation.'''
        try:
            # Check how many workers are currently active
            conn = sqlite3.connect(databasePath)
            c = conn.cursor()
            
            c.execute('''
                SELECT COUNT(DISTINCT cr.staff_code) 
                FROM clock_records cr 
                WHERE cr.clock_out_time IS NULL
            ''')
            active_workers = c.fetchone()[0]
            
            c.execute('SELECT COUNT(*) FROM staff')
            total_workers = c.fetchone()[0]
            
            conn.close()
            
            if active_workers == 0:
                status_msg = "✅ ALL WORKERS COMPLETED\n\n"
                status_msg += f"• Total workers: {total_workers}\n"
                status_msg += "• Currently active: 0\n"
                status_msg += "• Status: Safe to generate all timesheets"
                
                self.msg(status_msg, "info", "Timesheet Generation Status")
            else:
                status_msg = f"⏳ WORKERS STILL ACTIVE\n\n"
                status_msg += f"• Total workers: {total_workers}\n"
                status_msg += f"• Currently active: {active_workers}\n"
                status_msg += f"• Completed: {total_workers - active_workers}\n\n"
                status_msg += "Recommendation: Use Progressive Generation to\n"
                status_msg += "handle active workers automatically!"
                
                self.msg(status_msg, "warning", "Timesheet Generation Status")
                
        except Exception as e:
            self.msg(f"Error checking status: {e}", "warning", "Error")

    def handle_admin_close(self, event):
        """Handle the admin panel closing."""
        self.admin_was_open = False
        event.accept()

    def update_pin_label(self):
        """Update the PIN label dynamically based on the entered name and role."""
        staff_name = self.name_entry.text().strip()

        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            # Fetch the PIN based on the cleaned staff name
            cursor.execute("SELECT code FROM staff WHERE name = ?", (staff_name,))
            result = cursor.fetchone()
            conn.close()

            if result:
                staff_code = result[0]
                self.pin_label.setText(f"PIN: {staff_code}")
            else:
                self.pin_label.setText("PIN: Not Found")
        except sqlite3.Error as e:
            logging.error(f"Database error while fetching PIN: {e}")
            self.pin_label.setText("PIN: Error")

    def add_comment(self):
        staff_name = self.name_entry.text().strip()
        if not staff_name:
            self.msg("Please enter a staff name.", "warning", "Error")
            logging.error("No staff name entered.")
            return

        # Check if staff exists
        conn = sqlite3.connect(databasePath)
        c = conn.cursor()
        c.execute("SELECT code FROM staff WHERE name = ?", (staff_name,))
        staff = c.fetchone()
        if not staff:
            conn.close()
            self.msg("Staff not found.", "warning", "Error")
            logging.error(f"No staff found for name: {staff_name}")
            return
        staff_code = staff[0]
        conn.close()

        # Open the menu to choose where to add the comment
        comment_menu = QDialog(self)
        comment_menu.setWindowTitle('Add Comment')
        comment_menu.setFixedSize(400, 300)
        layout = QVBoxLayout(comment_menu)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        # Add the options
        staff_button = QPushButton("Add Comment to Staff")
        staff_button.setFont(QFont("Arial", 16))
        staff_button.clicked.connect(lambda: self.add_staff_comment(staff_name, comment_menu))
        layout.addWidget(staff_button)

        clock_record_button = QPushButton("Add Comment to Clock Record")
        clock_record_button.setFont(QFont("Arial", 16))
        clock_record_button.clicked.connect(lambda: self.add_clock_record_comment(staff_code, comment_menu))
        layout.addWidget(clock_record_button)

        comment_menu.exec()

    def calculate_pdf_dimensions(self, screen_width, screen_height):
    # A4 ratio (height/width)
        A4_RATIO = 1.414
    
    # Calculate maximum possible width and height while maintaining A4 ratio
    # Use 80% of screen dimensions to leave room for UI elements
        max_width = int(screen_width * 0.8)
        max_height = int(screen_height * 0.8)
    
    # Calculate dimensions based on screen constraints
        if max_height / max_width > A4_RATIO:
        # Screen is taller than A4 ratio, width is the constraint
            width = max_width
            height = int(width * A4_RATIO)
        else:
        # Screen is wider than A4 ratio, height is the constraint
            height = max_height
            width = int(height / A4_RATIO)
    
    # Ensure dimensions don't exceed screen size
        width = min(width, max_width)
        height = min(height, max_height)
    
        return width, height



    def add_staff_comment(self, staff_name, parent_menu):
        parent_menu.close()  # Close the parent menu

        # Open a dialog to add a comment
        comment_dialog = QDialog(self)
        comment_dialog.setWindowTitle("Add Comment to Staff")
        comment_dialog.setFixedSize(400, 200)
        layout = QVBoxLayout(comment_dialog)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        comment_label = QLabel("Enter Comment:")
        comment_label.setFont(QFont("Arial", 16))
        layout.addWidget(comment_label)

        comment_entry = QLineEdit()
        comment_entry.setFont(QFont("Arial", 16))
        layout.addWidget(comment_entry)

        save_button = QPushButton("Save Comment")
        save_button.setFont(QFont("Arial", 16))
        save_button.clicked.connect(lambda: self.save_staff_comment(staff_name, comment_entry.text(), comment_dialog))
        layout.addWidget(save_button)

        comment_dialog.exec()

    def save_staff_comment(self, staff_name, comment, dialog):
        if not comment.strip():
            self.msg("Please enter a comment.", "warning", "Error")
            return

        try:
            conn = sqlite3.connect(databasePath)
            c = conn.cursor()
            c.execute("UPDATE staff SET notes = ? WHERE name = ?", (comment, staff_name))
            conn.commit()
            conn.close()
            self.msg("Comment saved successfully.", "info", "Success")
            logging.info(f"Added comment to staff {staff_name}: {comment}")
            dialog.close()
        except sqlite3.Error as e:
            self.msg(f"Database error: {e}", "warning", "Error")
            logging.error(f"Database error: {e}")

    def add_clock_record_comment(self, staff_code, parent_menu):
        """Allow the user to select a clock record and add a comment."""
        parent_menu.close()

        # Fetch clock records
        records = self.fetch_clock_records(staff_code)
        if not records:
            self.msg("No records found for this staff member.", "warning", "Error")
            return

        # Show selection dialog
        record_id = self.show_record_selection_dialog()
        if record_id:
            self.add_comment_to_clock_record(record_id)

    def add_comment_to_record(self, record_id):
        """Open a dialog to add a comment to a specific clock record."""
        comment_dialog = QDialog(self)
        comment_dialog.setWindowTitle("Add Comment to Clock Record")
        comment_dialog.setFixedSize(400, 200)

        layout = QVBoxLayout(comment_dialog)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        comment_label = QLabel("Enter Comment:")
        comment_label.setFont(QFont("Arial", 14))
        layout.addWidget(comment_label)

        comment_entry = QLineEdit()
        comment_entry.setFont(QFont("Arial", 14))
        layout.addWidget(comment_entry)

        save_button = QPushButton("Save Comment")
        save_button.setFont(QFont("Arial", 14))
        save_button.clicked.connect(lambda: self.save_clock_reocrd_comment(record_id, comment_entry.text(), comment_dialog))
        layout.addWidget(save_button)

        comment_dialog.exec()

    def fetch_clock_records(self, staff_code):
        """Retrieve clock records for a specific staff member."""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, clock_in_time, clock_out_time FROM clock_records WHERE staff_code = ?",
                           (staff_code,))
            records = cursor.fetchall()
            conn.close()
            return records
        except sqlite3.Error as e:
            logging.error(f"Database error while fetching records: {e}")
            self.msg("Database error occurred.", "warning", "Error")
            return []

    def show_record_selection_dialog(self):
        """Display clock records as buttons for the selected staff member."""
        logging.debug("Starting open_records_tab function")
        staff_name = self.name_entry.text().strip()
        if not staff_name:
            self.msg("Please enter a valid staff name.", "warning", "Error")
            logging.error(f"Error: Invalid staff name '{staff_name}'")
            return

        try:
            conn = sqlite3.connect(databasePath)
            cursor = conn.cursor()
            cursor.execute('SELECT code FROM staff WHERE name = ?', (staff_name,))
            staff = cursor.fetchone()

            if not staff:
                self.msg("Staff member not found.", "warning", "Error")
                logging.error(f"Staff member '{staff_name}' not found.")
                return

            staff_code = staff[0]
            cursor.execute('SELECT id, clock_in_time, clock_out_time FROM clock_records WHERE staff_code = ?',
                           (staff_code,))
            records = cursor.fetchall()
            conn.close()

            if not records:
                self.msg("No records found for this staff member.", "info", "Info")
                logging.warning(f"No records found for staff '{staff_name}'.")
                return

        except sqlite3.Error as e:
            self.msg(f"Database error: {e}", "warning", "Error")
            logging.error(f"Database error occurred: {e}")
            return

        # Create the dialog
        records_dialog = QDialog(self)
        records_dialog.setWindowTitle(f"Clock Records for {staff_name}")
        records_dialog.setFixedSize(500, 900)

        # Position the dialog at the top of the screen
        screen_geometry = QApplication.primaryScreen().geometry()
        records_dialog.move(screen_geometry.x(), screen_geometry.y())

        layout = QVBoxLayout(records_dialog)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # Add a button for each record
        for record in records:
            record_id, clock_in, clock_out = record
            clock_in_time = (
                datetime.fromisoformat(clock_in).strftime('%H:%M %d/%m/%y') if clock_in else "N/A"
            )
            clock_out_time = (
                datetime.fromisoformat(clock_out).strftime('%H:%M %d/%m/%y') if clock_out else "N/A"
            )

            button_text = f"Clock In: {clock_in_time}, Clock Out: {clock_out_time}"
            record_button = QPushButton(button_text)
            record_button.setFont(QFont("Arial", 12))
            record_button.setMinimumSize(400, 40)
            record_button.clicked.connect(lambda _, rid=record_id: self.add_comment_to_record(rid))
            layout.addWidget(record_button)

        # Add a Close button
        close_button = QPushButton("Close")
        close_button.setFont(QFont("Arial", 14))
        close_button.clicked.connect(records_dialog.close)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignCenter)

        records_dialog.exec()

    def get_user_comment(self, title):
        """Display a dialog to collect a comment from the user."""
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setFixedSize(400, 200)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        label = QLabel("Enter Comment:")
        comment_entry = QLineEdit()

        save_button = QPushButton("Save")
        save_button.clicked.connect(dialog.accept)

        layout.addWidget(label)
        layout.addWidget(comment_entry)
        layout.addWidget(save_button)

        dialog.exec()
        return comment_entry.text().strip() if comment_entry.text().strip() else None

    def fetch_staff_names_and_roles(self):
        try:
            conn = sqlite3.connect(databasePath)
            cursor = conn.cursor()
            cursor.execute('SELECT name FROM staff')
            staff_data = cursor.fetchall()
            conn.close()
            return [name[0] for name in staff_data]
        except sqlite3.Error as e:
            logging.error(f"Database error when fetching staff data: {e}")
            return []

    def open_records_tab(self):
        """Opens a fixed-size tab to view clock records for a selected staff."""
        logging.debug("Starting open_records_tab function")
        staff_name = self.name_entry.text().strip()
        if not staff_name:
            self.msg("Please enter a valid staff name.", "warning", "Error")
            logging.error(f"Error: Invalid staff name '{staff_name}'")
            return

        try:
            conn = sqlite3.connect(databasePath)
            cursor = conn.cursor()
            cursor.execute('SELECT code FROM staff WHERE name = ?', (staff_name,))
            staff = cursor.fetchone()

            if not staff:
                self.msg("Staff member not found.", "warning", "Error")
                logging.error(f"Staff member '{staff_name}' not found.")
                return

            staff_code = staff[0]
            cursor.execute('SELECT id, clock_in_time, clock_out_time, notes FROM clock_records WHERE staff_code = ?',
                           (staff_code,))
            records = cursor.fetchall()
            conn.close()

            if not records:
                self.msg("No records found for this staff member.", "info", "Info")
                logging.warning(f"No records found for staff '{staff_name}'.")
                return

        except sqlite3.Error as e:
            self.msg(f"Database error: {e}", "warning", "Error")
            logging.error(f"Database error occurred: {e}")
            return

        # Create records dialog
        records_dialog = QDialog(self.admin_tab)
        records_dialog.setWindowTitle(f"Clock Records for {staff_name}")
        records_dialog.setFixedSize(800, 600)
        records_dialog.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)

        # Style the dialog
        records_dialog.setStyleSheet(f"""
            QDialog {{
                background: {self.COLORS['dark']};
                color: {self.COLORS['light']};
                border: 2px solid {self.COLORS['primary']};
                border-radius: 10px;
            }}
            QTableWidget {{
                background: {self.COLORS['dark']};
                color: {self.COLORS['light']};
                border: none;
                gridline-color: {self.COLORS['gray']};
            }}
            QTableWidget::item {{
                padding: 10px;
            }}
            QTableWidget::item:selected {{
                background: {self.COLORS['primary']};
            }}
            QHeaderView::section {{
                background: {self.COLORS['primary']};
                color: {self.COLORS['light']};
                padding: 10px;
                border: none;
            }}
            QPushButton {{
                background: {self.COLORS['primary']};
                color: {self.COLORS['light']};
                border: none;
                border-radius: 5px;
                padding: 10px;
                min-width: 100px;
            }}
            QPushButton:hover {{
                background: {self.COLORS['primary']}dd;
            }}
            QLineEdit {{
                background: {self.COLORS['dark']};
                color: {self.COLORS['light']};
                border: 1px solid {self.COLORS['gray']};
                border-radius: 5px;
                padding: 8px;
            }}
            QLineEdit:focus {{
                border: 1px solid {self.COLORS['primary']};
            }}
            QLabel {{
                color: {self.COLORS['light']};
            }}
        """)

        layout = QVBoxLayout(records_dialog)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # Add a title label
        title_label = QLabel(f"Clock Records for {staff_name}")
        title_label.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Add a search box
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        search_label.setFont(QFont("Inter", 12))
        search_entry = QLineEdit()
        search_entry.setFont(QFont("Inter", 12))
        search_layout.addWidget(search_label)
        search_layout.addWidget(search_entry)
        layout.addLayout(search_layout)

        # Create and setup table
        table = QTableWidget(len(records), 4)
        table.setHorizontalHeaderLabels(["Clock In", "Clock Out", "Notes", "Actions"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setFont(QFont("Inter", 11))

        # Populate the table
        for row, record in enumerate(records):
            clock_in_time = (
                datetime.fromisoformat(record[1]).strftime('%H:%M %d/%m/%y') if record[1] else "N/A"
            )
            clock_out_time = (
                datetime.fromisoformat(record[2]).strftime('%H:%M %d/%m/%y') if record[2] else "N/A"
            )

            table.setItem(row, 0, QTableWidgetItem(clock_in_time))
            table.setItem(row, 1, QTableWidgetItem(clock_out_time))
            table.setItem(row, 2, QTableWidgetItem(record[3] if record[3] else "N/A"))

            # Add an Edit button to each row
            edit_button = QPushButton("Edit")
            edit_button.setFont(QFont("Inter", 11))
            edit_button.clicked.connect(lambda checked, rid=record[0]: self.edit_clock_record(rid))
            table.setCellWidget(row, 3, edit_button)

        # Connect search functionality
        search_entry.textChanged.connect(lambda text: self.filter_records_table(text, table))

        layout.addWidget(table)

        # Add control buttons at the bottom
        button_layout = QHBoxLayout()
        
        refresh_button = QPushButton("Refresh")
        refresh_button.setFont(QFont("Inter", 12))
        refresh_button.clicked.connect(lambda: self.refresh_records_table(table, staff_code))
        
        close_button = QPushButton("Close")
        close_button.setFont(QFont("Inter", 12))
        close_button.clicked.connect(records_dialog.close)
        
        button_layout.addWidget(refresh_button)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)

        # Center the dialog on screen
        screen_geometry = QApplication.primaryScreen().geometry()
        x = (screen_geometry.width() - records_dialog.width()) // 2
        y = (screen_geometry.height() - records_dialog.height()) // 2
        records_dialog.move(x, y)

        records_dialog.exec()

    def start_drag(self, event, window):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def drag_window(self, event, window):
        if self.old_pos is not None:
            delta = event.globalPosition().toPoint() - self.old_pos
            window.move(window.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def stop_drag(self, event):
        self.old_pos = None

    def filter_records_table(self, search_text, table):
        """Filter the records table based on search text."""
        search_text = search_text.lower()
        for row in range(table.rowCount()):
            row_visible = False
            for col in range(table.columnCount() - 1):  # Exclude the Actions column
                item = table.item(row, col)
                if item and search_text in item.text().lower():
                    row_visible = True
                    break
            table.setRowHidden(row, not row_visible)

    def refresh_records_table(self, table, staff_code):
        """Refresh the records table with latest data."""
        try:
            conn = sqlite3.connect(databasePath)
            cursor = conn.cursor()
            cursor.execute('SELECT id, clock_in_time, clock_out_time, notes FROM clock_records WHERE staff_code = ?',
                           (staff_code,))
            records = cursor.fetchall()
            conn.close()

            table.setRowCount(len(records))
            for row, record in enumerate(records):
                clock_in_time = (
                    datetime.fromisoformat(record[1]).strftime('%H:%M %d/%m/%y') if record[1] else "N/A"
                )
                clock_out_time = (
                    datetime.fromisoformat(record[2]).strftime('%H:%M %d/%m/%y') if record[2] else "N/A"
                )

                table.setItem(row, 0, QTableWidgetItem(clock_in_time))
                table.setItem(row, 1, QTableWidgetItem(clock_out_time))
                table.setItem(row, 2, QTableWidgetItem(record[3] if record[3] else "N/A"))

                edit_button = QPushButton("Edit")
                edit_button.setFont(QFont("Inter", 11))
                edit_button.clicked.connect(lambda checked, rid=record[0]: self.edit_clock_record(rid))
                table.setCellWidget(row, 3, edit_button)

        except sqlite3.Error as e:
            self.msg(f"Database error: {e}", "warning", "Error")
            logging.error(f"Database error occurred while refreshing: {e}")

    def edit_clock_record(self, record_id):
        """Opens a dialog to edit a specific clock record."""
        logging.info(f"Editing clock record ID: {record_id}")

        # Fetch the record details
        conn = sqlite3.connect(databasePath)
        cursor = conn.cursor()
        cursor.execute("SELECT clock_in_time, clock_out_time, notes FROM clock_records WHERE id = ?", (record_id,))
        record = cursor.fetchone()
        conn.close()

        if not record:
            self.msg("Record not found.", "warning", "Error")
            return

        # Open a dialog to edit the record
        edit_dialog = QDialog(self)
        edit_dialog.setWindowTitle("Edit Clock Record")
        edit_dialog.setFixedSize(400, 300)

        layout = QVBoxLayout(edit_dialog)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        clock_in_label = QLabel("Clock In:")
        clock_in_entry = QLineEdit(record[0] if record[0] else "")
        layout.addWidget(clock_in_label)
        layout.addWidget(clock_in_entry)

        clock_out_label = QLabel("Clock Out:")
        clock_out_entry = QLineEdit(record[1] if record[1] else "")
        layout.addWidget(clock_out_label)
        layout.addWidget(clock_out_entry)

        notes_label = QLabel("Notes:")
        notes_entry = QLineEdit(record[2] if record[2] else "")
        layout.addWidget(notes_label)
        layout.addWidget(notes_entry)

        save_button = QPushButton("Save")
        save_button.clicked.connect(lambda: self.save_clock_record(record_id, clock_in_entry.text(),
                                                                   clock_out_entry.text(), notes_entry.text(),
                                                                   edit_dialog))
        layout.addWidget(save_button)

        edit_dialog.exec()

    def save_clock_record(self, record_id, clock_in, clock_out, notes, dialog):
        """Saves the edited clock record."""
        try:
            conn = sqlite3.connect(databasePath)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE clock_records
                SET clock_in_time = ?, clock_out_time = ?, notes = ?
                WHERE id = ?
            """, (clock_in, clock_out, notes, record_id))
            conn.commit()
            conn.close()

            self.msg("Record updated successfully.", "info", "Success")
            logging.info(
                f"Updated clock record ID {record_id}: Clock In: {clock_in}, Clock Out: {clock_out}, Notes: {notes}")
            dialog.close()
        except sqlite3.Error as e:
            self.msg(f"Database error occurred: {e}", "warning", "Error")
            logging.error(f"Database error occurred: {e}")

    def save_clock_reocrd_comment(self, record_id, comment, dialog):
        """Save the comment to the database."""
        if not comment.strip():
            self.msg("Please enter a comment.", "warning", "Error")
            return

        try:
            conn = sqlite3.connect(databasePath)
            cursor = conn.cursor()
            cursor.execute("UPDATE clock_records SET notes = ? WHERE id = ?", (comment.strip(), record_id))
            conn.commit()
            conn.close()
            self.msg("Comment saved successfully.", "info", "Success")
            dialog.close()
            logging.info(f"Added comment to record ID {record_id}: {comment}")
        except sqlite3.Error as e:
            self.msg(f"Database error occurred: {e}", "warning", "Error")
            logging.error(f"Database error: {e}")

    def toggle_window_mode(self):
        screen_geometry = QApplication.primaryScreen().geometry()

        if not self.isWindowed:
            # Switch to windowed mode
            self.setWindowFlags(Qt.WindowType.Window)
            self.showNormal()
            self.resize(800, 600)  # Default size for windowed mode
            self.move(200,200)
            self.windowed_button.setText("Enter Fullscreen Mode")
            logging.info("Switched to windowed mode.")
        else:
            # Switch to fullscreen mode
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
            self.setGeometry(screen_geometry)  # Ensure it fills the screen
            self.showFullScreen()
            self.windowed_button.setText("Enter Windowed Mode")
            logging.info("Switched to fullscreen mode.")

        self.isWindowed = not self.isWindowed

    def add_staff(self):
        staff_name = self.name_entry.text().strip()
        staff_role = self.role_entry.text().strip()

        if not staff_name:
            self.msg("Please enter a valid staff name.", "warning", "Error")
            logging.error("Missing staff name.")
            return

        max_retries = 1000
        retries = 0
        while retries < max_retries:
            staff_code = random.randint(1000, 9999)
            conn = sqlite3.connect(databasePath)
            c = conn.cursor()
            while c.execute('SELECT * FROM staff WHERE code = ?', (staff_code,)).fetchone():
                staff_code = random.randint(1000, 9999)

            try:
                c.execute('INSERT INTO staff (name, code, role) VALUES (?, ?, ?)', 
                         (staff_name, staff_code, staff_role))
                conn.commit()
                
                # Create real-time backup for staff record
                self.backup_staff_record(staff_code, staff_name, staff_role)
                
                self.msg(f"Staff member {staff_name} added with code {staff_code}.", "info", "Success")
                logging.info(f"Staff member {staff_name} added with code {staff_code} and role {staff_role}.")

                break
            except sqlite3.Error as e:
                self.msg(f"Database error occurred: {e}", "warning", "Error")
                logging.error(f"Database error occurred: {e}")
            finally:
                conn.close()
            retries += 1
        else:
            self.msg("Failed to add staff member. Please try again.", "warning", "Error")
            logging.error(f"Failed to add staff member {staff_name}.")

    def remove_staff(self):
        staff_name = self.name_entry.text().strip()
        if not staff_name:
            self.msg("Please enter a valid staff name.", "warning", "Error")
            logging.error("Staff name is empty.")
            return

        try:
            conn = sqlite3.connect(databasePath)
            c = conn.cursor()

            # Check if the staff member exists
            c.execute('SELECT code FROM staff WHERE name = ?', (staff_name,))
            staff = c.fetchone()
            if not staff:
                self.msg("Staff member not found.", "warning", "Error")
                logging.error(f"Staff member '{staff_name}' not found.")
                return
            staff_code = staff[0]

            # Fetch all clock records for the staff member
            c.execute('SELECT clock_in_time, clock_out_time, "" AS notes FROM clock_records WHERE staff_code = ?',
                      (staff_code,))
            clock_records = c.fetchall()

            # Archive records if any exist
            if clock_records:
                for record in clock_records:
                    c.execute(
                        'INSERT INTO archive_records (staff_name, staff_code, clock_in, clock_out, notes) VALUES (?, ?, ?, ?, ?)',
                        (staff_name, staff_code, *record)
                    )

            # If no records exist, still archive the staff's details
            if not clock_records:
                c.execute(
                    'INSERT INTO archive_records (staff_name, staff_code, clock_in, clock_out, notes) VALUES (?, ?, NULL, NULL, NULL)',
                    (staff_name, staff_code)
                )

            # Commit archive records
            conn.commit()

            # Delete clock records and staff record from main tables
            c.execute('DELETE FROM clock_records WHERE staff_code = ?', (staff_code,))
            c.execute('DELETE FROM staff WHERE code = ?', (staff_code,))
            conn.commit()

            self.msg(f"Staff member {staff_name} removed successfully.", "info", "Success")
            logging.info(f"Archived and removed staff member: {staff_name}")

        except sqlite3.Error as e:
            self.msg(f"Database error occurred: {e}", "warning", "Error")
            logging.error(f"Database error occurred: {e}")
        finally:
            conn.close()

    def generate_pdf(self, file_path, staff_name, records):
        """Generate a PDF for the given staff member and save it to file_path."""
        try:
            pdf = SimpleDocTemplate(file_path)
            styles = getSampleStyleSheet()

            elements = [Paragraph(f"Records for {staff_name}", styles['Title']), Spacer(1, 20)]
            table_data = [["Clock In Date", "Clock In Time", "Clock Out Date", "Clock Out Time"]]

            for record in records:
                clock_in = datetime.fromisoformat(record[0]) if record[0] else None
                clock_out = datetime.fromisoformat(record[1]) if record[1] else None
                table_data.append([
                    clock_in.strftime('%d-%m-%Y') if clock_in else '',
                    clock_in.strftime('%H:%M:%S') if clock_in else '',
                    clock_out.strftime('%d-%m-%Y') if clock_out else '',
                    clock_out.strftime('%H:%M:%S') if clock_out else '',
                ])

            table = Table(table_data, style=[
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ])
            elements.append(table)

            pdf.build(elements)
            logging.info(f"PDF created successfully at '{file_path}'.")
        except Exception as e:
            logging.error(f"Failed to create PDF: {e}")
            raise

    def viewItem(self, file_path):
        """Open the generated PDF using a web engine viewer widget."""
        try:
            # Ensure the file exists and get absolute path
            abs_path = os.path.abspath(file_path)
            if not os.path.exists(abs_path):
                raise FileNotFoundError(f"PDF file not found at: {abs_path}")

            # Get screen dimensions from settings
            screen_width = self.settings["width"]
            screen_height = self.settings["height"]
            
            # Calculate proportional dimensions
            pdf_width, pdf_height = self.calculate_pdf_dimensions(screen_width, screen_height)
            
            # Create PDF viewer dialog
            pdf_dialog = QDialog(self)
            pdf_dialog.setWindowTitle("PDF Viewer")
            pdf_dialog.setFixedSize(pdf_width, pdf_height)
            
            # Center the dialog on the screen
            screen = QApplication.primaryScreen().geometry()
            pdf_dialog.move(
                (screen.width() - pdf_width) // 2,
                (screen.height() - pdf_height) // 2
            )
            
            # Create web engine view for PDF
            web_view = QWebEngineView()
            settings = web_view.settings()
            settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, True)
            
            # Load the PDF file
            web_view.setUrl(QUrl.fromLocalFile(abs_path))
            
            # Remove margins and make it look more like Preview
            layout = QVBoxLayout(pdf_dialog)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

            
            # Add the web view to fill the entire dialog
            layout.addWidget(web_view)
            
            pdf_dialog.exec()
            logging.info(f"Opened PDF at '{abs_path}' in viewer widget")
            
        except Exception as e:
            logging.error(f"Failed to open PDF: {e}")
            raise

    def delete_pdf_after_delay(self, file_path, delay=10):
        """Delete the PDF file after a delay."""
        def delete_file():
            time.sleep(delay)
            try:
                os.remove(file_path)
                logging.info(f"Temporary PDF file '{file_path}' deleted after delay.")
            except Exception as e:
                logging.error(f"Failed to delete temporary file '{file_path}': {e}")

        Thread(target=delete_file, daemon=True).start()

    def get_printer_ip(self):
        """
        Display a dialog for the user to enter the printer's IP address.
        """
        # Create dialog
        printer_ip_dialog = QDialog(self)
        printer_ip_dialog.setWindowTitle("Enter Printer IP")
        printer_ip_dialog.setFixedSize(300, 150)

        # Set layout
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Create input field for IP address
        ip_input = QLineEdit(printer_ip_dialog)
        ip_input.setPlaceholderText("Enter Printer IP Address")
        ip_input.setStyleSheet("padding: 10px; border: 1px solid #ccc; border-radius: 5px;")
        layout.addWidget(ip_input)

        # Create "Submit" button
        submit_button = QPushButton("Submit", printer_ip_dialog)
        submit_button.setStyleSheet("background-color: #007BFF; color: white; padding: 10px; border-radius: 5px;")
        submit_button.clicked.connect(lambda: self.handle_printer_ip(ip_input.text(), printer_ip_dialog))
        layout.addWidget(submit_button)

        # Apply layout and show dialog
        printer_ip_dialog.setLayout(layout)
        printer_ip_dialog.exec()

    def handle_printer_ip(self, ip_address, dialog):
        """
        Handle the entered IP address and close the dialog.
        """
        if not ip_address.strip():
            self.msg("Please enter a valid IP address.", "warning", "Error")
            return

        # You can store or use the IP address here
        logging.info(f"Printer IP entered: {ip_address}")

        # Close the dialog
        dialog.close()

    def preparePrint(self, print_type="records"):
        """Generate a temporary PDF for the selected staff and send it to the printer."""
        staff_name = self.name_entry.text().strip()
        if not staff_name:
            self.msg("Please enter a valid staff name.", "warning", "Error")
            logging.error(f"Error: Invalid staff name '{staff_name}'")
            return

        try:
            # Fetch the staff details
            conn = sqlite3.connect(databasePath)
            cursor = conn.cursor()
            cursor.execute('SELECT code, role FROM staff WHERE name = ?', (staff_name,))
            staff = cursor.fetchone()

            if not staff:
                self.msg("Staff member not found.", "warning", "Error")
                logging.error(f"Staff member '{staff_name}' not found.")
                return

            staff_code = staff[0]
            staff_role = staff[1] if staff[1] else "Unknown"
            
            if print_type == "records":
                # Get all clock records
                cursor.execute('SELECT clock_in_time, clock_out_time FROM clock_records WHERE staff_code = ?',
                             (staff_code,))
                records = cursor.fetchall()
                
                if not records:
                    self.msg("No records found for this staff member.", "info", "Info")
                    logging.warning(f"No records found for staff '{staff_name}'.")
                    return

                # Generate temporary PDF for records
                file_path = os.path.abspath(os.path.join(tempPath, f"{staff_name}_records_temp.pdf"))
                self.generate_pdf(file_path, staff_name, records)
                
                # Print and clean up
                try:
                    self.print_via_jetdirect(file_path)
                    self.delete_pdf_after_delay(file_path, delay=10)
                except Exception as e:
                    self.msg(f"Error printing records: {e}", "warning", "Error")
                    logging.error(f"Failed to print records for {staff_name}: {e}")
                    
            else:  # timesheet
                # Get date range for timesheet
                start_day = self.settings["start_day"]
                now = datetime.now()
                prev_month = now.month - 1 if now.month > 1 else 12
                prev_year = now.year if now.month > 1 else now.year - 1
                last_day_of_prev_month = calendar.monthrange(prev_year, prev_month)[1]
                start_date_day = min(start_day, last_day_of_prev_month)
                start_date = datetime(prev_year, prev_month, start_date_day)
                end_date = datetime.now()

                # Get timesheet records
                cursor.execute("""
                    SELECT clock_in_time, clock_out_time
                    FROM clock_records
                    WHERE staff_code = ? AND DATE(clock_in_time) BETWEEN ? AND ?
                """, (staff_code, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
                records = cursor.fetchall()
                
                if not records:
                    self.msg(f"No records found for {staff_name} in the timesheet period.", "info", "Info")
                    return

                # Generate and save timesheet
                output_file = os.path.join(permanentPath, f"{staff_name}_timesheet.pdf")
                try:
                    self.generate_timesheet(staff_name, staff_role, start_date, end_date, records)
                    
                    # Ensure the file exists before trying to print
                    if os.path.exists(output_file):
                        self.print_via_jetdirect(output_file)
                    else:
                        raise FileNotFoundError("Timesheet file was not generated properly")
                        
                except Exception as e:
                    self.msg(f"Error printing timesheet: {e}", "warning", "Error")
                    logging.error(f"Failed to print timesheet for {staff_name}: {e}")

        except sqlite3.Error as e:
            self.msg(f"Database error: {e}", "warning", "Error")
            logging.error(f"Database error in preparePrint: {e}")
        finally:
            conn.close()

    def print_via_jetdirect(self, file_path):
        printerIP = self.settings["printer_IP"]
        printer_ip =printerIP
        printer_port = 9100
        try:
            with open(file_path, "rb") as pdf_file:
                pdf_data = pdf_file.read()
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as printer_socket:
                printer_socket.connect((printer_ip, printer_port))
                printer_socket.sendall(pdf_data)
            print("PDF sent to printer successfully!")
            logging.info(f'PDF sent to printer successfully')
        except Exception as e:
            print(f"Failed to print PDF: {e}")
            logging.error("failed to print")


    def get_date_range_for_timesheet(self, day_selected):
        today = datetime.now()
        if today.day < day_selected:
            end_date = today.replace(day=day_selected) - timedelta(days=30)
        else:
            end_date = today.replace(day=day_selected)

        start_date = end_date.replace(day=21) - timedelta(days=30)
        logging.info(f'Start date for timesheet {start_date.strftime("%d-%m-%Y")}, end date for timesheet {end_date.strftime("%d-%m-%Y")}')
        return start_date, end_date

    def fetch_timesheet_records(self, conn, start_date, end_date):
        c = conn.cursor()
        c.execute("""
            SELECT s.name, s.role, c.clock_in_time, c.clock_out_time
            FROM staff s
            LEFT JOIN clock_records c ON s.code = c.staff_code
            WHERE DATE(c.clock_in_time) BETWEEN ? AND ?
            ORDER BY s.role, s.name, c.clock_in_time
        """, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
        records = c.fetchall()
        logging.info(f"Fetched records for time sheet")
        return records

    def generate_all_timesheets(self, day_selected):
        '''Legacy method - now redirects to progressive generation.'''
        # Redirect to progressive system for better user experience
        self.start_progressive_timesheet_generation()
        
        # Show explanation to admin
        self.msg("🚀 Upgraded to Progressive Generation!\n\n"
                "The new system will:\n"
                "• Generate timesheets for completed workers immediately\n"
                "• Monitor active workers and generate when they finish\n"
                "• Show real-time progress with cool animations\n"
                "• Prevent any lost timesheet data\n\n"
                "Check the new Progressive Generation window!", 
                "info", "System Upgraded")

    def generate_one_timesheet(self):
        """Generates a single timesheet for a staff member selected via a dialog."""
        try:
            staff_names = self.fetch_staff_names_and_roles()
            if not staff_names:
                self.msg("No staff found in the database.", "warning", "Error")
                return

            staff_name, ok = QInputDialog.getItem(self, "Select Staff Member", 
                                                  "Select the staff member to generate a timesheet for:", 
                                                  staff_names, 0, False)

            if ok and staff_name:
                conn = sqlite3.connect(self.database_path)
                c = conn.cursor()
                c.execute("SELECT code FROM staff WHERE name = ?", (staff_name,))
                result = c.fetchone()
                conn.close()

                if result:
                    staff_code = result[0]
                    self.generate_single_worker_timesheet(staff_name, staff_code)
                else:
                    self.msg(f"Could not find staff code for {staff_name}.", "warning", "Error")

        except Exception as e:
            self.msg(f"An error occurred: {str(e)}", "warning", "Error")
            logging.error(f"Error in generate_one_timesheet: {e}")

    def generate_single_worker_timesheet(self, staff_name: str, staff_code: str):
        '''Generate timesheet for a single worker (existing logic).'''
        start_day = self.settings["start_day"]
        now = datetime.now()

        # Calculate the previous month and year
        prev_month = now.month - 1 if now.month > 1 else 12
        prev_year = now.year if now.month > 1 else now.year - 1

        # Validate the day and create the start_date
        last_day_of_prev_month = calendar.monthrange(prev_year, prev_month)[1]
        start_date_day = min(start_day, last_day_of_prev_month)  # Ensure start_day is valid
        start_date = datetime(prev_year, prev_month, start_date_day)

        end_date = datetime.now()

        # Fetch clock records for the staff member
        conn = sqlite3.connect(databasePath)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT clock_in_time, clock_out_time
            FROM clock_records
            WHERE staff_code = ? AND DATE(clock_in_time) BETWEEN ? AND ?
        """, (staff_code, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
        records = cursor.fetchall()
        conn.close()

        if not records:
            self.msg(f"No records found for {staff_name} between {start_date} and {end_date}.", "info", "Info")
            logging.info(f"No records found for {staff_name} between {start_date} and {end_date}.")
            return

        # Generate the timesheet
        self.generate_timesheet(staff_name, "Unknown", start_date, end_date, records)
        self.msg(f"Timesheet generated for {staff_name}.", "info", "Success")
        logging.info(f"Timesheet generated for {staff_name}.")



    def generate_timesheet(self, employee_name, role, start_date, end_date, records):
        # Create the PDF file path
        os.makedirs("Timesheets", exist_ok=True)
        output_file = os.path.join(permanentPath, f"{employee_name}_timesheet.pdf")

        # Create the PDF document
        doc = SimpleDocTemplate(output_file, pagesize=A4)
        elements = []

        # Header
        title = f"The Partnership in Care\nMONTHLY TIMESHEET"
        name_line = f"NAME: {employee_name}"
        role_line = f"ROLE: {role}"
        date_line = f"DATE: {start_date.strftime('%d %B')} to {end_date.strftime('%d %B')} {end_date.year}"
        signed_line = "SIGNED: ……………………………………………………….."

        elements.append(Spacer(1, 20))
        elements.append(Paragraph(title, getSampleStyleSheet()['Title']))
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(name_line, getSampleStyleSheet()['Normal']))
        elements.append(Paragraph(role_line, getSampleStyleSheet()['Normal']))
        elements.append(Paragraph(date_line, getSampleStyleSheet()['Normal']))
        elements.append(Spacer(1, 40))
        elements.append(Paragraph(signed_line, getSampleStyleSheet()['Normal']))
        elements.append(Spacer(1, 20))

        # Table header
        data = [
            ["Date", "Day", "Clock In", "Clock Out", "Hours Worked", "Notes"]
        ]

        # Add rows for each day
        for record in records:
            clock_in = datetime.fromisoformat(record[0]) if record[0] else None
            clock_out = datetime.fromisoformat(record[1]) if record[1] else None
            hours_worked = (
                (clock_out - clock_in).total_seconds() / 3600 if clock_in and clock_out else ""
            )
            data.append([
                clock_in.strftime('%d-%m-%Y') if clock_in else '',
                clock_in.strftime('%A') if clock_in else '',
                clock_in.strftime('%H:%M') if clock_in else '',
                clock_out.strftime('%H:%M') if clock_out else '',
                f"{hours_worked:.2f}" if hours_worked else '',
                ""
            ])

        # Add totals row
        data.append(["Totals"] + [""] * 5)

        # Create the table
        table = Table(data, colWidths=[70, 70, 70, 70, 70, 100])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)

        # Footer
        footer_lines = [
            "Checked by Administrator: ……………………………………………………….. Signed         ………………………………….. Date",
            "           ",
            "Checked by Manager:           ……………………………………………………….. Signed       ……………………………………. Date"
        ]
        elements.append(Spacer(1, 40))
        for line in footer_lines:
            elements.append(Paragraph(line, getSampleStyleSheet()['Normal']))

        # Build the PDF
        doc.build(elements)
        logging.info(f"Built Timesheet for {employee_name}")

    def update_screen_dimensions(self, rect):
        """Update the settings file with current screen dimensions."""
        try:
            with open(settingsFilePath, 'r') as file:
                settings = json.load(file)
            
            settings['width'] = rect.width()
            settings['height'] = rect.height()
            
            with open(settingsFilePath, 'w') as file:
                json.dump(settings, file, indent=4)
            
            logging.info(f"Updated screen dimensions in settings: {rect.width()}x{rect.height()}")
        except Exception as e:
            logging.error(f"Failed to update screen dimensions in settings: {e}")

    def fetch_unique_roles(self):
        try:
            conn = sqlite3.connect(databasePath)
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT role FROM staff WHERE role IS NOT NULL')
            roles = [role[0] for role in cursor.fetchall() if role[0]]
            conn.close()
            return roles
        except sqlite3.Error as e:
            logging.error(f"Database error when fetching roles: {e}")
            return []

    def update_role_from_name(self, name):
        if name:
            conn = sqlite3.connect(databasePath)
            c = conn.cursor()
            c.execute('SELECT role FROM staff WHERE name = ?', (name,))
            result = c.fetchone()
            conn.close()
            
            if result and result[0]:
                self.role_entry.setText(result[0])
            else:
                self.role_entry.setText("")

    def update_role_label(self):
        name = self.name_entry.text().strip()
        try:
            conn = sqlite3.connect(databasePath)
            c = conn.cursor()
            c.execute('SELECT role FROM staff WHERE name = ?', (name,))
            result = c.fetchone()
            conn.close()

            if result and result[0]:
                self.role_entry.setText(result[0])
            else:
                self.role_entry.setText("Unknown")
        except sqlite3.Error as e:
            logging.error(f"Database error when fetching role: {e}")
            self.role_entry.setText("Unknown")

    def open_visitor_form(self):
        """Opens a form for visitor check-in/check-out."""
        # Check if admin panel is open and store its state
        if hasattr(self, 'admin_tab') and self.admin_tab.isVisible():
            self.admin_was_open = True
            self.admin_tab.hide()

        visitor_dialog = QDialog(self)
        visitor_dialog.setWindowTitle("Visitor Check In/Out")
        visitor_dialog.setFixedSize(400, 400)
        visitor_dialog.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        
        # Handle visitor form closing
        visitor_dialog.finished.connect(self.handle_visitor_close)
        
        layout = QVBoxLayout(visitor_dialog)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # Style the visitor form
        visitor_dialog.setStyleSheet(f"""
            QDialog {{
                background: {self.COLORS['dark']};
                color: {self.COLORS['light']};
            }}
            QLabel {{
                color: {self.COLORS['light']};
                font-family: Inter;
            }}
            QLineEdit {{
                background-color: {self.COLORS['dark']};
                color: {self.COLORS['light']};
                border: 2px solid {self.COLORS['gray']};
                border-radius: 8px;
                padding: 8px;
                font-family: Inter;
            }}
            QLineEdit:focus {{
                border: 2px solid {self.COLORS['primary']};
            }}
            QPushButton {{
                background-color: {self.COLORS['primary']};
                color: {self.COLORS['light']};
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-family: Inter;
            }}
            QPushButton:hover {{
                background-color: {self.COLORS['primary']}dd;
            }}
        """)

        # Name input
        name_label = QLabel("Name:")
        name_label.setFont(QFont("Inter", 14))
        name_entry = QLineEdit()
        name_entry.setFont(QFont("Inter", 14))
        layout.addWidget(name_label)
        layout.addWidget(name_entry)

        # Car registration input
        car_reg_label = QLabel("Car Registration:")
        car_reg_label.setFont(QFont("Inter", 14))
        car_reg_entry = QLineEdit()
        car_reg_entry.setFont(QFont("Inter", 14))
        layout.addWidget(car_reg_label)
        layout.addWidget(car_reg_entry)

        # Purpose input
        purpose_label = QLabel("Purpose of Visit:")
        purpose_label.setFont(QFont("Inter", 14))
        purpose_entry = QLineEdit()
        purpose_entry.setFont(QFont("Inter", 14))
        layout.addWidget(purpose_label)
        layout.addWidget(purpose_entry)

        # Check In button
        check_in_button = QPushButton("Check In")
        check_in_button.setFont(QFont("Inter", 14))
        check_in_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.COLORS['success']};
                color: {self.COLORS['light']};
                border: none;
                border-radius: 8px;
                padding: 10px;
            }}
            QPushButton:hover {{
                background-color: {self.COLORS['success']}dd;
            }}
        """)
        check_in_button.clicked.connect(lambda: self.handle_visitor(name_entry.text(), car_reg_entry.text(), 
                                                               purpose_entry.text(), "in", visitor_dialog))
        layout.addWidget(check_in_button)

        # Check Out button
        check_out_button = QPushButton("Check Out")
        check_out_button.setFont(QFont("Inter", 14))
        check_out_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.COLORS['danger']};
                color: {self.COLORS['light']};
                border: none;
                border-radius: 8px;
                padding: 10px;
            }}
            QPushButton:hover {{
                background-color: {self.COLORS['danger']}dd;
            }}
        """)
        check_out_button.clicked.connect(lambda: self.handle_visitor(name_entry.text(), car_reg_entry.text(), 
                                                               purpose_entry.text(), "out", visitor_dialog))
        layout.addWidget(check_out_button)

        visitor_dialog.exec()

    def handle_visitor_close(self, result):
        """Handle the visitor form closing."""
        # If admin panel was open before, show it again
        if self.admin_was_open and hasattr(self, 'admin_tab'):
            self.admin_tab.show()
            self.admin_was_open = False

    def handle_visitor(self, name, car_reg, purpose, action, dialog):
        """Handle visitor check-in/check-out."""
        if not name or not car_reg:
            self.msg("Please enter both name and car registration.", "warning", "Error")
            return

        try:
            conn = sqlite3.connect(databasePath)
            c = conn.cursor()

            if action == "in":
                # Check if visitor is already checked in
                c.execute('''SELECT id FROM visitors 
                           WHERE name = ? AND car_reg = ? AND time_out IS NULL''', 
                           (name, car_reg))
                if c.fetchone():
                    self.msg("Visitor is already checked in.", "warning", "Error")
                    return

                # Record new visit
                time_in = datetime.now().isoformat()
                c.execute('''INSERT INTO visitors (name, car_reg, purpose, time_in) 
                           VALUES (?, ?, ?, ?)''', 
                           (name, car_reg, purpose, time_in))
                conn.commit()
                self.msg("Visitor checked in successfully.", "info", "Success")
                dialog.close()

            elif action == "out":
                # Find matching unchecked-out visit
                c.execute('''SELECT id FROM visitors 
                           WHERE name = ? AND car_reg = ? AND time_out IS NULL''', 
                           (name, car_reg))
                visit = c.fetchone()
                
                if not visit:
                    self.msg("No matching check-in found for this visitor.", "warning", "Error")
                    return

                # Record check-out time
                time_out = datetime.now().isoformat()
                c.execute('UPDATE visitors SET time_out = ? WHERE id = ?', 
                         (time_out, visit[0]))
                conn.commit()
                self.msg("Visitor checked out successfully.", "info", "Success")
                dialog.close()

        except sqlite3.Error as e:
            self.msg(f"Database error: {e}", "warning", "Error")
            logging.error(f"Database error in handle_visitor: {e}")
        finally:
            conn.close()

    def open_visitors_tab(self):
        """Opens a tab to view all visitor records."""
        try:
            conn = sqlite3.connect(databasePath)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT name, car_reg, purpose, time_in, time_out 
                FROM visitors 
                ORDER BY time_in DESC
            ''')
            records = cursor.fetchall()
            conn.close()

            if not records:
                self.msg("No visitor records found.", "info", "Info")
                return

            # Create dialog for visitor records
            visitors_dialog = QDialog(self)
            visitors_dialog.setWindowTitle("Visitor Records")
            visitors_dialog.setFixedSize(800, 600)
            visitors_dialog.setStyleSheet(f"""
                QDialog {{
                    background: {self.COLORS['dark']};
                    color: {self.COLORS['light']};
                }}
                QLabel {{
                    color: {self.COLORS['light']};
                    font-family: Inter;
                }}
                QTableWidget {{
                    background: {self.COLORS['dark']};
                    color: {self.COLORS['light']};
                    border: none;
                    gridline-color: {self.COLORS['gray']};
                }}
                QTableWidget::item {{
                    padding: 10px;
                }}
                QTableWidget::item:selected {{
                    background: {self.COLORS['primary']};
                }}
                QHeaderView::section {{
                    background: {self.COLORS['primary']};
                    color: {self.COLORS['light']};
                    padding: 10px;
                    border: none;
                }}
                QPushButton {{
                    background: {self.COLORS['primary']};
                    color: {self.COLORS['light']};
                    border: none;
                    border-radius: 5px;
                    padding: 10px;
                    min-width: 100px;
                }}
                QPushButton:hover {{
                    background: {self.COLORS['primary']}dd;
                }}
                QLineEdit {{
                    background: {self.COLORS['dark']};
                    color: {self.COLORS['light']};
                    border: 1px solid {self.COLORS['gray']};
                    border-radius: 5px;
                    padding: 8px;
                }}
            """)

            layout = QVBoxLayout(visitors_dialog)
            layout.setSpacing(10)
            layout.setContentsMargins(20, 20, 20, 20)

            # Add search functionality
            search_layout = QHBoxLayout()
            search_label = QLabel("Search:")
            search_label.setFont(QFont("Inter", 12))
            search_entry = QLineEdit()
            search_entry.setFont(QFont("Inter", 12))
            search_layout.addWidget(search_label)
            search_layout.addWidget(search_entry)
            layout.addLayout(search_layout)

            # Create table widget
            table = QTableWidget(len(records), 6)  # 6 columns including an Edit button
            table.setHorizontalHeaderLabels(["Name", "Car Reg", "Purpose", "Time In", "Time Out", "Actions"])
            table.horizontalHeader().setStretchLastSection(True)
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            table.setFont(QFont("Inter", 11))

            # Populate table
            for row, record in enumerate(records):
                name, car_reg, purpose = record[0], record[1], record[2]
                time_in = datetime.fromisoformat(record[3]).strftime('%H:%M %d/%m/%y') if record[3] else "N/A"
                time_out = datetime.fromisoformat(record[4]).strftime('%H:%M %d/%m/%y') if record[4] else "N/A"

                table.setItem(row, 0, QTableWidgetItem(name))
                table.setItem(row, 1, QTableWidgetItem(car_reg))
                table.setItem(row, 2, QTableWidgetItem(purpose))
                table.setItem(row, 3, QTableWidgetItem(time_in))
                table.setItem(row, 4, QTableWidgetItem(time_out))

                # Add Edit button
                edit_button = QPushButton("Edit")
                edit_button.setStyleSheet(f"background-color: {self.COLORS['primary']}; color: white;")
                edit_button.clicked.connect(lambda checked, r=row, data=record: self.edit_visitor_record(r, data))
                table.setCellWidget(row, 5, edit_button)

            # Connect search functionality
            search_entry.textChanged.connect(lambda text: self.filter_visitors_table(text, table))

            layout.addWidget(table)

            # Button layout at the bottom
            button_layout = QHBoxLayout()
            
            # Print button
            print_button = QPushButton("Print Visitor List")
            print_button.setFont(QFont("Inter", 12))
            print_button.setStyleSheet(f"""
                background-color: {self.COLORS['purple']};
                min-width: 150px;
            """)
            print_button.clicked.connect(lambda: self.print_visitor_list(records))
            
            # Close button
            close_button = QPushButton("Close")
            close_button.setFont(QFont("Inter", 12))
            close_button.setMinimumSize(120, 40)
            
            button_layout.addWidget(print_button)
            button_layout.addWidget(close_button)
            close_button.clicked.connect(visitors_dialog.close)
            
            layout.addLayout(button_layout)

            visitors_dialog.exec()

        except sqlite3.Error as e:
            self.msg(f"Database error: {e}", "warning", "Error")
            logging.error(f"Database error in open_visitors_tab: {e}")

    def filter_visitors_table(self, search_text, table):
        """Filter the visitors table based on search text."""
        search_text = search_text.lower()
        for row in range(table.rowCount()):
            row_visible = False
            for col in range(table.columnCount() - 1):  # Exclude the Actions column
                item = table.item(row, col)
                if item and search_text in item.text().lower():
                    row_visible = True
                    break
            table.setRowHidden(row, not row_visible)

    def edit_visitor_record(self, row, record_data):
        """Opens a dialog to edit a visitor record."""
        edit_dialog = QDialog(self)
        edit_dialog.setWindowTitle("Edit Visitor Record")
        edit_dialog.setFixedSize(400, 300)

        layout = QVBoxLayout(edit_dialog)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # Create input fields
        name_label = QLabel("Name:")
        name_entry = QLineEdit(record_data[0])
        car_reg_label = QLabel("Car Registration:")
        car_reg_entry = QLineEdit(record_data[1])
        purpose_label = QLabel("Purpose:")
        purpose_entry = QLineEdit(record_data[2])

        layout.addWidget(name_label)
        layout.addWidget(name_entry)
        layout.addWidget(car_reg_label)
        layout.addWidget(car_reg_entry)
        layout.addWidget(purpose_label)
        layout.addWidget(purpose_entry)

        # Add Save button
        save_button = QPushButton("Save Changes")
        save_button.setStyleSheet("background-color: #4CAF50; color: white;")
        save_button.clicked.connect(lambda: self.save_visitor_changes(
            name_entry.text(),
            car_reg_entry.text(),
            purpose_entry.text(),
            record_data,
            edit_dialog
        ))
        layout.addWidget(save_button)

        edit_dialog.exec()

    def save_visitor_changes(self, name, car_reg, purpose, old_record, dialog):
        """Save changes to a visitor record."""
        if not name or not car_reg:
            self.msg("Name and car registration are required.", "warning", "Error")
            return

        try:
            conn = sqlite3.connect(databasePath)
            cursor = conn.cursor()
            
            # Update the record
            cursor.execute('''
                UPDATE visitors 
                SET name = ?, car_reg = ?, purpose = ?
                WHERE name = ? AND car_reg = ? AND time_in = ?
            ''', (name, car_reg, purpose, old_record[0], old_record[1], old_record[3]))
            
            conn.commit()
            self.msg("Visitor record updated successfully.", "info", "Success")
            dialog.close()
            
            # Refresh the visitors view
            self.open_visitors_tab()
            
        except sqlite3.Error as e:
            self.msg(f"Database error: {e}", "warning", "Error")
            logging.error(f"Database error in save_visitor_changes: {e}")
        finally:
            conn.close()

    def ping_printer(self, ip_address):
        """Test if a printer is reachable at the given IP address."""
        try:
            # For Windows
            if platform.system().lower() == "windows":
                ping_cmd = ["ping", "-n", "1", "-w", "1000", ip_address]
            # For Unix/Linux/macOS
            else:
                ping_cmd = ["ping", "-c", "1", "-W", "1", ip_address]
            
            result = subprocess.run(ping_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return result.returncode == 0
            
        except Exception as e:
            logging.error(f"Error pinging printer at {ip_address}: {e}")
            return False

    def test_printer_connection(self, ip_address):
        """Test both ping and port 9100 connection to the printer."""
        if not self.ping_printer(ip_address):
            return False, "Printer is not responding to ping"
            
        try:
            # Try to connect to port 9100 (standard printer port)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)  # 2 second timeout
            result = sock.connect_ex((ip_address, 9100))
            sock.close()
            
            if result == 0:
                return True, "Printer connection successful"
            else:
                return False, "Printer port 9100 is not accessible"
                
        except Exception as e:
            logging.error(f"Error testing printer connection: {e}")
            return False, f"Connection error: {str(e)}"

    def generate_visitor_pdf(self, records, file_path):
        """Generate a PDF of visitor records."""
        try:
            doc = SimpleDocTemplate(file_path, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()

            # Add title
            title = Paragraph("Visitor Records", styles['Title'])
            elements.append(title)
            elements.append(Spacer(1, 20))

            # Create table data
            data = [["Name", "Car Registration", "Purpose", "Time In", "Time Out"]]  # Header row
            
            for record in records:
                name, car_reg, purpose = record[0], record[1], record[2]
                time_in = datetime.fromisoformat(record[3]).strftime('%H:%M %d/%m/%y') if record[3] else "N/A"
                time_out = datetime.fromisoformat(record[4]).strftime('%H:%M %d/%m/%y') if record[4] else "N/A"
                data.append([name, car_reg, purpose, time_in, time_out])

            # Create and style the table
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))

            elements.append(table)
            
            # Add timestamp
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
            footer = Paragraph(f"Generated on: {timestamp}", styles['Normal'])
            elements.append(Spacer(1, 20))
            elements.append(footer)

            doc.build(elements)
            return True
        except Exception as e:
            logging.error(f"Error generating visitor PDF: {e}")
            return False

    def print_visitor_list(self, records):
        """Print the visitor list."""
        try:
            # Generate temporary PDF
            temp_file = os.path.abspath(os.path.join(tempPath, "visitors_temp.pdf"))
            if self.generate_visitor_pdf(records, temp_file):
                # Print the PDF
                self.print_via_jetdirect(temp_file)
                # Schedule deletion of temporary file
                self.delete_pdf_after_delay(temp_file, delay=10)
                self.msg("Visitor list sent to printer.", "info", "Success")
            else:
                self.msg("Failed to generate visitor list.", "warning", "Error")
        except Exception as e:
            self.msg(f"Error printing visitor list: {e}", "warning", "Error")
            logging.error(f"Error printing visitor list: {e}")

    def open_archive_management(self):
        """Opens the archive management dialog to view and manage archived databases."""
        archive_dialog = QDialog(self)
        archive_dialog.setWindowTitle("Archive Management")
        archive_dialog.setFixedSize(800, 600)
        archive_dialog.setStyleSheet(f"""
            QDialog {{
                background: {self.COLORS['dark']};
                color: {self.COLORS['light']};
            }}
            QLabel {{
                color: {self.COLORS['light']};
                font-family: Inter;
            }}
            QTableWidget {{
                background: {self.COLORS['dark']};
                color: {self.COLORS['light']};
                border: none;
                gridline-color: {self.COLORS['gray']};
            }}
            QTableWidget::item {{
                padding: 10px;
            }}
            QTableWidget::item:selected {{
                background: {self.COLORS['primary']};
            }}
            QHeaderView::section {{
                background: {self.COLORS['primary']};
                color: {self.COLORS['light']};
                padding: 10px;
                border: none;
            }}
            QPushButton {{
                background: {self.COLORS['primary']};
                color: {self.COLORS['light']};
                border: none;
                border-radius: 5px;
                padding: 10px;
                min-width: 100px;
            }}
            QPushButton:hover {{
                background: {self.COLORS['primary']}dd;
            }}
        """)

        layout = QVBoxLayout(archive_dialog)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = QLabel("Database Archive Management")
        title_label.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Get archive databases
        archives = self.get_archive_databases()

        if not archives:
            no_archives_label = QLabel("No archived databases found.")
            no_archives_label.setFont(QFont("Inter", 14))
            no_archives_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_archives_label)
        else:
            # Create table for archives
            table = QTableWidget(len(archives), 5)
            table.setHorizontalHeaderLabels(["Archive Date", "Type", "Filename", "Size (KB)", "Actions"])
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            table.setFont(QFont("Inter", 11))

            # Populate table
            for row, archive in enumerate(archives):
                date_str = archive['date'].strftime('%Y-%m-%d %H:%M:%S')
                size_kb = archive['size'] / 1024
                archive_type = archive.get('type', 'Unknown')

                table.setItem(row, 0, QTableWidgetItem(date_str))
                table.setItem(row, 1, QTableWidgetItem(archive_type))
                table.setItem(row, 2, QTableWidgetItem(archive['filename']))
                table.setItem(row, 3, QTableWidgetItem(f"{size_kb:.1f}"))

                # Action buttons container
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(5, 0, 5, 0)

                # View button
                view_button = QPushButton("View")
                view_button.setStyleSheet(f"background-color: {self.COLORS['primary']}; min-width: 60px;")
                view_button.clicked.connect(lambda checked, path=archive['path']: self.view_archive_database(path))

                # Delete button
                delete_button = QPushButton("Delete")
                delete_button.setStyleSheet(f"background-color: {self.COLORS['danger']}; min-width: 60px;")
                delete_button.clicked.connect(lambda checked, path=archive['path'], name=archive['filename']: 
                                             self.delete_archive_database(path, name, archive_dialog))

                actions_layout.addWidget(view_button)
                actions_layout.addWidget(delete_button)
                table.setCellWidget(row, 4, actions_widget)

            layout.addWidget(table)

        # Control buttons
        button_layout = QHBoxLayout()
        
        # Manual archive button
        manual_archive_button = QPushButton("Create Manual Archive")
        manual_archive_button.setFont(QFont("Inter", 12))
        manual_archive_button.setStyleSheet(f"""
            background-color: {self.COLORS['warning']};
            min-width: 150px;
        """)
        manual_archive_button.clicked.connect(lambda: self.create_manual_archive(archive_dialog))
        
        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.setFont(QFont("Inter", 12))
        refresh_button.clicked.connect(lambda: self.refresh_archive_management(archive_dialog))
        
        # Close button
        close_button = QPushButton("Close")
        close_button.setFont(QFont("Inter", 12))
        close_button.clicked.connect(archive_dialog.close)
        
        button_layout.addWidget(manual_archive_button)
        button_layout.addWidget(refresh_button)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)

        archive_dialog.exec()

    def view_archive_database(self, archive_path):
        """View the contents of an archived database with detailed information."""
        try:
            # Create archive viewer dialog
            archive_viewer = QDialog(self)
            archive_viewer.setWindowTitle(f"Archive Database Viewer - {os.path.basename(archive_path)}")
            archive_viewer.setFixedSize(1000, 700)
            archive_viewer.setStyleSheet(f"""
                QDialog {{
                    background: {self.COLORS['dark']};
                    color: {self.COLORS['light']};
                }}
                QLabel {{
                    color: {self.COLORS['light']};
                    font-family: Inter;
                }}
                QTableWidget {{
                    background: {self.COLORS['dark']};
                    color: {self.COLORS['light']};
                    border: none;
                    gridline-color: {self.COLORS['gray']};
                }}
                QTableWidget::item {{
                    padding: 8px;
                }}
                QTableWidget::item:selected {{
                    background: {self.COLORS['primary']};
                }}
                QHeaderView::section {{
                    background: {self.COLORS['primary']};
                    color: {self.COLORS['light']};
                    padding: 8px;
                    border: none;
                }}
                QPushButton {{
                    background: {self.COLORS['primary']};
                    color: {self.COLORS['light']};
                    border: none;
                    border-radius: 5px;
                    padding: 10px;
                    min-width: 100px;
                }}
                QPushButton:hover {{
                    background: {self.COLORS['primary']}dd;
                }}
                QTabWidget::pane {{
                    border: 1px solid {self.COLORS['gray']};
                    background: {self.COLORS['dark']};
                }}
                QTabBar::tab {{
                    background: {self.COLORS['gray']};
                    color: {self.COLORS['light']};
                    padding: 8px 16px;
                    margin-right: 2px;
                }}
                QTabBar::tab:selected {{
                    background: {self.COLORS['primary']};
                }}
            """)

            layout = QVBoxLayout(archive_viewer)
            layout.setSpacing(10)
            layout.setContentsMargins(20, 20, 20, 20)

            # Title
            title_label = QLabel(f"Archive Database: {os.path.basename(archive_path)}")
            title_label.setFont(QFont("Inter", 16, QFont.Weight.Bold))
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(title_label)

            # Connect to archive database
            conn = sqlite3.connect(archive_path)
            cursor = conn.cursor()
            
            # Get summary information
            cursor.execute("SELECT COUNT(*) FROM staff")
            staff_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM clock_records")
            records_count = cursor.fetchone()[0]
            
            # Check if visitors table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='visitors'")
            visitors_table_exists = cursor.fetchone() is not None
            visitors_count = 0
            if visitors_table_exists:
                cursor.execute("SELECT COUNT(*) FROM visitors")
                visitors_count = cursor.fetchone()[0]

            # Summary section
            summary_text = f"Staff Members: {staff_count} | Clock Records: {records_count} | Visitor Records: {visitors_count}"
            summary_label = QLabel(summary_text)
            summary_label.setFont(QFont("Inter", 12))
            summary_label.setStyleSheet(f"color: {self.COLORS['light']}; padding: 10px; background: {self.COLORS['gray']}; border-radius: 5px;")
            summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(summary_label)

            # Create tab widget for different data views
            tab_widget = QTabWidget()
            
            # Staff tab
            staff_tab = QWidget()
            staff_layout = QVBoxLayout(staff_tab)
            
            if staff_count > 0:
                cursor.execute("SELECT code, name, role, notes FROM staff ORDER BY name")
                staff_data = cursor.fetchall()
                
                staff_table = QTableWidget(len(staff_data), 4)
                staff_table.setHorizontalHeaderLabels(["Code", "Name", "Role", "Notes"])
                staff_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
                staff_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
                
                for row, (code, name, role, notes) in enumerate(staff_data):
                    staff_table.setItem(row, 0, QTableWidgetItem(str(code)))
                    staff_table.setItem(row, 1, QTableWidgetItem(str(name)))
                    staff_table.setItem(row, 2, QTableWidgetItem(str(role) if role else ""))
                    staff_table.setItem(row, 3, QTableWidgetItem(str(notes) if notes else ""))
                
                staff_layout.addWidget(staff_table)
            else:
                no_staff_label = QLabel("No staff records found in this archive.")
                no_staff_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                staff_layout.addWidget(no_staff_label)
            
            tab_widget.addTab(staff_tab, "Staff")
            
            # Clock Records tab
            records_tab = QWidget()
            records_layout = QVBoxLayout(records_tab)
            
            if records_count > 0:
                cursor.execute("""
                    SELECT s.name, c.clock_in_time, c.clock_out_time, c.notes, c.break_time 
                    FROM clock_records c 
                    LEFT JOIN staff s ON c.staff_code = s.code 
                    ORDER BY c.clock_in_time DESC 
                    LIMIT 100
                """)
                records_data = cursor.fetchall()
                
                records_table = QTableWidget(len(records_data), 5)
                records_table.setHorizontalHeaderLabels(["Staff Name", "Clock In", "Clock Out", "Notes", "Break Time"])
                records_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
                records_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
                
                for row, (name, clock_in, clock_out, notes, break_time) in enumerate(records_data):
                    records_table.setItem(row, 0, QTableWidgetItem(str(name) if name else "Unknown"))
                    records_table.setItem(row, 1, QTableWidgetItem(str(clock_in) if clock_in else ""))
                    records_table.setItem(row, 2, QTableWidgetItem(str(clock_out) if clock_out else ""))
                    records_table.setItem(row, 3, QTableWidgetItem(str(notes) if notes else ""))
                    records_table.setItem(row, 4, QTableWidgetItem(str(break_time) if break_time else ""))
                
                records_layout.addWidget(records_table)
                
                if records_count > 100:
                    limit_label = QLabel(f"Showing first 100 records out of {records_count} total")
                    limit_label.setStyleSheet(f"color: {self.COLORS['warning']};")
                    records_layout.addWidget(limit_label)
            else:
                no_records_label = QLabel("No clock records found in this archive.")
                no_records_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                records_layout.addWidget(no_records_label)
            
            tab_widget.addTab(records_tab, "Clock Records")
            
            # Visitors tab (if table exists)
            if visitors_table_exists:
                visitors_tab = QWidget()
                visitors_layout = QVBoxLayout(visitors_tab)
                
                if visitors_count > 0:
                    cursor.execute("SELECT name, car_reg, purpose, time_in, time_out FROM visitors ORDER BY time_in DESC LIMIT 50")
                    visitors_data = cursor.fetchall()
                    
                    visitors_table = QTableWidget(len(visitors_data), 5)
                    visitors_table.setHorizontalHeaderLabels(["Name", "Car Reg", "Purpose", "Time In", "Time Out"])
                    visitors_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
                    visitors_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
                    
                    for row, (name, car_reg, purpose, time_in, time_out) in enumerate(visitors_data):
                        visitors_table.setItem(row, 0, QTableWidgetItem(str(name) if name else ""))
                        visitors_table.setItem(row, 1, QTableWidgetItem(str(car_reg) if car_reg else ""))
                        visitors_table.setItem(row, 2, QTableWidgetItem(str(purpose) if purpose else ""))
                        visitors_table.setItem(row, 3, QTableWidgetItem(str(time_in) if time_in else ""))
                        visitors_table.setItem(row, 4, QTableWidgetItem(str(time_out) if time_out else ""))
                    
                    visitors_layout.addWidget(visitors_table)
                    
                    if visitors_count > 50:
                        limit_label = QLabel(f"Showing first 50 records out of {visitors_count} total")
                        limit_label.setStyleSheet(f"color: {self.COLORS['warning']};")
                        visitors_layout.addWidget(limit_label)
                else:
                    no_visitors_label = QLabel("No visitor records found in this archive.")
                    no_visitors_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    visitors_layout.addWidget(no_visitors_label)
                
                tab_widget.addTab(visitors_tab, "Visitors")
            
            layout.addWidget(tab_widget)
            
            # Close button
            close_button = QPushButton("Close")
            close_button.setFont(QFont("Inter", 12))
            close_button.clicked.connect(archive_viewer.close)
            
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            button_layout.addWidget(close_button)
            layout.addLayout(button_layout)
            
            conn.close()
            archive_viewer.exec()
            
        except Exception as e:
            self.msg(f"Error reading archive database: {str(e)}", "warning", "Error")
            logging.error(f"Error reading archive database {archive_path}: {e}")

    def delete_archive_database(self, archive_path, filename, parent_dialog):
        """Delete an archived database after confirmation."""
        try:
            # Confirmation dialog
            reply = QMessageBox.question(
                parent_dialog, 
                "Confirm Deletion", 
                f"Are you sure you want to delete the archive '{filename}'?\n\nThis action cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                os.remove(archive_path)
                self.msg(f"Archive '{filename}' deleted successfully.", "info", "Archive Deleted")
                logging.info(f"Deleted archive database: {filename}")
                
                # Refresh the dialog
                parent_dialog.close()
                self.open_archive_management()
                
        except Exception as e:
            self.msg(f"Error deleting archive: {str(e)}", "warning", "Error")
            logging.error(f"Error deleting archive {archive_path}: {e}")

    def create_manual_archive(self, parent_dialog):
        """Create a manual archive of the current database."""
        try:
            reply = QMessageBox.question(
                parent_dialog,
                "Create Manual Archive",
                "This will create an archive of the current database.\n\nDo you want to proceed?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Create manual archive (but don't reset the database)
                archive_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                archive_filename = f"manual_archive_{archive_date}.db"
                archive_path = os.path.join(self.archive_folder, archive_filename)
                
                shutil.copy2(self.database_path, archive_path)
                self.msg(f"Manual archive created: {archive_filename}", "info", "Archive Created")
                logging.info(f"Manual archive created: {archive_filename}")
                
                # Refresh the dialog
                parent_dialog.close()
                self.open_archive_management()
                
        except Exception as e:
            self.msg(f"Error creating manual archive: {str(e)}", "warning", "Error")
            logging.error(f"Error creating manual archive: {e}")

    def refresh_archive_management(self, dialog):
        """Refresh the archive management dialog."""
        dialog.close()
        self.open_archive_management()

    def open_fingerprint_management(self):
        """Opens the fingerprint management dialog."""
        fingerprint_dialog = QDialog(self)
        fingerprint_dialog.setWindowTitle("Fingerprint Management")
        fingerprint_dialog.setFixedSize(800, 600)
        fingerprint_dialog.setStyleSheet(f"""
            QDialog {{
                background: {self.COLORS['dark']};
                color: {self.COLORS['light']};
            }}
            QLabel {{
                color: {self.COLORS['light']};
                font-family: Inter;
            }}
            QTableWidget {{
                background: {self.COLORS['dark']};
                color: {self.COLORS['light']};
                border: none;
                gridline-color: {self.COLORS['gray']};
            }}
            QTableWidget::item {{
                padding: 10px;
            }}
            QTableWidget::item:selected {{
                background: {self.COLORS['primary']};
            }}
            QHeaderView::section {{
                background: {self.COLORS['primary']};
                color: {self.COLORS['light']};
                padding: 10px;
                border: none;
            }}
            QPushButton {{
                background: {self.COLORS['primary']};
                color: {self.COLORS['light']};
                border: none;
                border-radius: 5px;
                padding: 10px;
                min-width: 100px;
            }}
            QPushButton:hover {{
                background: {self.COLORS['primary']}dd;
            }}
        """)

        layout = QVBoxLayout(fingerprint_dialog)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = QLabel("Fingerprint Management")
        title_label.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Device status
        device_status = "Connected" if self.fingerprint_device_available else "Not Connected"
        status_color = self.COLORS['success'] if self.fingerprint_device_available else self.COLORS['danger']
        status_label = QLabel(f"Device Status: {device_status}")
        status_label.setFont(QFont("Inter", 12))
        status_label.setStyleSheet(f"color: {status_color};")
        layout.addWidget(status_label)

        # Get all staff and their fingerprint status
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # First get all staff
            cursor.execute('SELECT code, name FROM staff ORDER BY name')
            staff_list = cursor.fetchall()
            conn.close()
            
            # Then check enrollment status in biometric profiles database
            staff_data = []
            for staff_code, staff_name in staff_list:
                try:
                    # Check if enrolled in biometric profiles database
                    bio_conn = sqlite3.connect("biometric_profiles.db")
                    bio_cursor = bio_conn.cursor()
                    bio_cursor.execute("SELECT COUNT(*) FROM biometric_profiles WHERE staff_code = ?", (staff_code,))
                    is_enrolled = bio_cursor.fetchone()[0] > 0
                    bio_conn.close()
                    
                    staff_data.append((staff_code, staff_name, 1 if is_enrolled else 0))
                except Exception as bio_e:
                    # If there's an error checking biometric DB, assume not enrolled
                    staff_data.append((staff_code, staff_name, 0))
                    
        except Exception as e:
            self.msg(f"Error loading staff data: {e}", "warning", "Error")
            staff_data = []

        if not staff_data:
            no_staff_label = QLabel("No staff members found.")
            no_staff_label.setFont(QFont("Inter", 14))
            no_staff_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_staff_label)
        else:
            # Create table for staff fingerprint status
            table = QTableWidget(len(staff_data), 4)
            table.setHorizontalHeaderLabels(["Staff Code", "Name", "Fingerprint Status", "Actions"])
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            table.setFont(QFont("Inter", 11))

            # Populate table
            for row, (staff_code, staff_name, is_enrolled) in enumerate(staff_data):
                status = "Enrolled" if is_enrolled else "Not Enrolled"
                status_color = self.COLORS['success'] if is_enrolled else self.COLORS['gray']

                table.setItem(row, 0, QTableWidgetItem(staff_code))
                table.setItem(row, 1, QTableWidgetItem(staff_name))
                
                status_item = QTableWidgetItem(status)
                status_item.setForeground(QColor(status_color))
                table.setItem(row, 2, status_item)

                # Action buttons container
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(5, 0, 5, 0)

                if is_enrolled:
                    # Remove fingerprint button
                    remove_button = QPushButton("Remove")
                    remove_button.setStyleSheet(f"background-color: {self.COLORS['danger']}; min-width: 60px;")
                    remove_button.clicked.connect(lambda checked, code=staff_code, name=staff_name: 
                                                 self.remove_staff_fingerprint(code, name, fingerprint_dialog))
                    actions_layout.addWidget(remove_button)
                else:
                    # Enroll fingerprint button
                    enroll_button = QPushButton("Enroll")
                    enroll_button.setStyleSheet(f"background-color: {self.COLORS['success']}; min-width: 60px;")
                    enroll_button.setEnabled(self.fingerprint_device_available)
                    enroll_button.clicked.connect(lambda checked, code=staff_code, name=staff_name: 
                                                 self.enroll_staff_fingerprint(code, name, fingerprint_dialog))
                    actions_layout.addWidget(enroll_button)

                table.setCellWidget(row, 3, actions_widget)

            layout.addWidget(table)

        # Control buttons
        button_layout = QHBoxLayout()
        
        # Test device button
        test_device_button = QPushButton("Test Device")
        test_device_button.setFont(QFont("Inter", 12))
        test_device_button.setStyleSheet(f"""
            background-color: {self.COLORS['primary']};
            min-width: 120px;
        """)
        test_device_button.clicked.connect(self.test_fingerprint_device)
        
        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.setFont(QFont("Inter", 12))
        refresh_button.clicked.connect(lambda: self.refresh_fingerprint_management(fingerprint_dialog))
        
        # Close button
        close_button = QPushButton("Close")
        close_button.setFont(QFont("Inter", 12))
        close_button.clicked.connect(fingerprint_dialog.close)
        
        button_layout.addWidget(test_device_button)
        button_layout.addWidget(refresh_button)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)

        fingerprint_dialog.exec()

    def enroll_staff_fingerprint(self, staff_code, staff_name, parent_dialog):
        """Enroll fingerprint for a staff member using built-in UI."""
        try:
            if not self.fingerprint_device_available:
                self.msg("Fingerprint device not available.", "warning", "Error")
                return

            # Show the built-in enrollment dialog
            dialog = FingerprintEnrollmentDialog(staff_code, staff_name, parent_dialog)
            result = dialog.exec()
            
            if result == QDialog.DialogCode.Accepted:
                self.msg(f"Fingerprint enrolled successfully for {staff_name}!", "info", "Success")
                logging.info(f"Fingerprint enrolled for {staff_name} ({staff_code})")
                
                # Refresh the dialog
                parent_dialog.close()
                self.open_fingerprint_management()
            else:
                # User cancelled or enrollment failed
                logging.info(f"Fingerprint enrollment cancelled for {staff_name} ({staff_code})")
                    
        except Exception as e:
            self.msg(f"Error enrolling fingerprint: {str(e)}", "warning", "Error")
            logging.error(f"Error enrolling fingerprint for {staff_code}: {e}")

    def remove_staff_fingerprint(self, staff_code, staff_name, parent_dialog):
        """Remove fingerprint for a staff member."""
        try:
            # Show confirmation dialog
            reply = QMessageBox.question(
                parent_dialog,
                "Remove Fingerprint",
                f"Are you sure you want to remove the fingerprint for {staff_name}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                success, message = self.fingerprint_manager.remove_employee_enrollment(staff_code)
                
                if success:
                    self.msg(f"Fingerprint removed for {staff_name}.", "info", "Success")
                    logging.info(f"Fingerprint removed for {staff_name} ({staff_code})")
                    
                    # Refresh the dialog
                    parent_dialog.close()
                    self.open_fingerprint_management()
                else:
                    self.msg(f"Error removing fingerprint: {message}", "warning", "Error")
                    
        except Exception as e:
            self.msg(f"Error removing fingerprint: {str(e)}", "warning", "Error")
            logging.error(f"Error removing fingerprint for {staff_code}: {e}")

    def test_fingerprint_device(self):
        """Test the fingerprint device connection."""
        try:
            detected, message = detect_digitalPersona_device()
            
            if detected:
                self.msg(f"Device test successful: {message}", "info", "Device Test")
            else:
                self.msg(f"Device test failed: {message}", "warning", "Device Test")
                
        except Exception as e:
            self.msg(f"Error testing device: {str(e)}", "warning", "Error")

    def refresh_fingerprint_management(self, dialog):
        """Refresh the fingerprint management dialog."""
        dialog.close()
        self.open_fingerprint_management()

    def open_database_maintenance(self):
        """Opens the database maintenance dialog for cleanup and optimization."""
        from utils.database_utils import DatabaseCleaner, DatabaseValidator
        
        maintenance_dialog = QDialog(self)
        maintenance_dialog.setWindowTitle("Database Maintenance")
        maintenance_dialog.setFixedSize(600, 500)
        maintenance_dialog.setStyleSheet(f"""
            QDialog {{
                background: {self.COLORS['dark']};
                color: {self.COLORS['light']};
            }}
            QLabel {{
                color: {self.COLORS['light']};
                font-family: Inter;
            }}
            QPushButton {{
                background: {self.COLORS['primary']};
                color: {self.COLORS['light']};
                border: none;
                border-radius: 5px;
                padding: 12px;
                min-width: 150px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {self.COLORS['primary']}dd;
            }}
            QPushButton[cleanup="true"] {{
                background: {self.COLORS['warning']};
            }}
            QPushButton[cleanup="true"]:hover {{
                background: {self.COLORS['warning']}dd;
            }}
            QPushButton[danger="true"] {{
                background: {self.COLORS['danger']};
            }}
            QPushButton[danger="true"]:hover {{
                background: {self.COLORS['danger']}dd;
            }}
            QTextEdit {{
                background: {self.COLORS['gray']};
                color: {self.COLORS['light']};
                border: 1px solid {self.COLORS['primary']};
                border-radius: 5px;
                padding: 10px;
            }}
        """)

        layout = QVBoxLayout(maintenance_dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = QLabel("Database Maintenance & Cleanup")
        title_label.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Description
        desc_label = QLabel("Maintain database integrity and optimize performance")
        desc_label.setFont(QFont("Inter", 12))
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet(f"color: {self.COLORS['gray']};")
        layout.addWidget(desc_label)

        # Results area
        results_area = QTextEdit()
        results_area.setMaximumHeight(150)
        results_area.setPlaceholderText("Maintenance results will appear here...")
        layout.addWidget(results_area)

        # Initialize utilities
        cleaner = DatabaseCleaner(self.database_path)
        validator = DatabaseValidator(self.database_path)

        # Maintenance buttons
        button_layout = QVBoxLayout()
        button_layout.setSpacing(10)

        # Validation buttons
        validate_structure_btn = QPushButton("Validate Database Structure")
        validate_structure_btn.clicked.connect(lambda: self.run_maintenance_task(
            validator.validate_tables, "Database Structure Validation", results_area
        ))

        validate_data_btn = QPushButton("Validate Data Consistency")
        validate_data_btn.clicked.connect(lambda: self.run_maintenance_task(
            validator.validate_data_consistency, "Data Consistency Validation", results_area
        ))

        # Optimization buttons
        vacuum_btn = QPushButton("Optimize Database (VACUUM)")
        vacuum_btn.setProperty("cleanup", "true")
        vacuum_btn.clicked.connect(lambda: self.run_maintenance_task(
            cleaner.vacuum_database, "Database Optimization", results_area
        ))

        integrity_btn = QPushButton("Check Database Integrity")
        integrity_btn.clicked.connect(lambda: self.run_maintenance_task(
            cleaner.check_database_integrity, "Database Integrity Check", results_area
        ))

        # Cleanup buttons
        reset_records_btn = QPushButton("Reset Clock Records (Keep Staff)")
        reset_records_btn.setProperty("danger", "true")
        reset_records_btn.clicked.connect(lambda: self.confirm_and_run_maintenance(
            lambda: cleaner.reset_database(keep_staff=True),
            "Reset Clock Records",
            "This will delete all clock records but keep staff data. Continue?",
            results_area,
            maintenance_dialog
        ))

        # Add buttons to layout
        button_layout.addWidget(validate_structure_btn)
        button_layout.addWidget(validate_data_btn)
        button_layout.addWidget(integrity_btn)
        button_layout.addWidget(vacuum_btn)
        button_layout.addWidget(reset_records_btn)

        layout.addLayout(button_layout)

        # Close button
        close_button_layout = QHBoxLayout()
        close_button = QPushButton("Close")
        close_button.clicked.connect(maintenance_dialog.close)
        close_button_layout.addStretch()
        close_button_layout.addWidget(close_button)
        layout.addLayout(close_button_layout)

        maintenance_dialog.exec()

    def run_maintenance_task(self, task_func, task_name, results_area):
        """Run a maintenance task and display results."""
        try:
            results_area.append(f"\n--- {task_name} ---")
            results_area.append("Running...")
            
            # Process events to update UI
            QApplication.processEvents()
            
            success, result = task_func()
            
            if success:
                if isinstance(result, list):
                    if result:  # Has validation issues
                        results_area.append("❌ Issues found:")
                        for issue in result:
                            results_area.append(f"  • {issue}")
                    else:  # No issues
                        results_area.append("✅ No issues found")
                else:
                    results_area.append(f"✅ {result}")
            else:
                if isinstance(result, list):
                    results_area.append("❌ Issues found:")
                    for issue in result:
                        results_area.append(f"  • {issue}")
                else:
                    results_area.append(f"❌ {result}")
                    
        except Exception as e:
            results_area.append(f"❌ Error: {str(e)}")
            logging.error(f"Maintenance task error: {e}")

    def confirm_and_run_maintenance(self, task_func, task_name, confirmation_msg, results_area, parent_dialog):
        """Confirm and run a potentially destructive maintenance task."""
        reply = QMessageBox.question(
            parent_dialog,
            f"Confirm {task_name}",
            confirmation_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.run_maintenance_task(task_func, task_name, results_area)

if __name__ == '__main__':
    get_os_specific_path()
    app = QApplication(sys.argv)
    window = StaffClockInOutSystem()
    window.show()
    logging.basicConfig(level=logging.DEBUG)
    sys.exit(app.exec())