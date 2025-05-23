import os
import shutil
import sqlite3
import datetime
import random
import socket
import keyboard
import calendar
import pyglet
from functools import partial
import logging
from threading import Thread
import json
import subprocess
import platform
import zipfile
import qrcode
import cv2
import subprocess
import time
import sys
from datetime import datetime, timedelta
from os import mkdir, write
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QDialog, QMessageBox, QDialogButtonBox, QTableWidget, QHeaderView, QAbstractItemView,
    QTableWidgetItem, QCompleter, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer, QTime, QEvent, QUrl
from PyQt6.QtGui import QFont, QPixmap, QImage, QScreen
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from timesheetDailyCheck import TimesheetCheckerThread
from dailyBackUp import DailyBackUp
from utils.logging_manager import LoggingManager

# Application version
APP_VERSION = "1.0.0"

# Global Paths
tempPath = permanentPath = databasePath = settingsFilePath = log_file = logoPath = qr_code_folder_path = ""

# Initialize logging manager
logger = None

def get_os_specific_path():
    global tempPath, permanentPath, databasePath, settingsFilePath, log_file, logoPath, qr_code_folder_path, logger

    # Get the base directory where the script is located
    base_path = os.path.dirname(os.path.abspath(__file__))

    if not os.path.exists(base_path):
        raise FileNotFoundError("Base directory does not exist.")

    program_data_path = os.path.join(base_path, "ProgramData")
    tempPath = os.path.join(base_path, "TempData")
    permanentPath = os.path.join(base_path, "Timesheets")
    qr_code_folder_path = os.path.join(base_path, "QR_Codes")
    backup_folder = os.path.join(base_path, "Backups")

    for folder in [program_data_path, tempPath, permanentPath, backup_folder, qr_code_folder_path]:
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
    check_and_restore_folder(qr_code_folder_path, backup_folder)

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

def check_and_restore_file(primary_path, backup_folder, generate_default=None):
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

    if primary_path == logoPath:
        logging.error(f"Critical: Logo file not found in {primary_path} or backups.")
        raise FileNotFoundError(f"Logo file missing and no backups available in {backup_folder}.")

    if generate_default:
        logging.warning(f"No backup found for {primary_path}. Generating default.")
        generate_default(primary_path)

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
        "height": rect.height() if rect else 1080  # Default fallback height
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

        self.scanner_active = False  # Track if the scanner is active
        self.cap = None  # Store camera object

        self.isWindowed = False
        # Paths
        self.backup_folder = os.path.join(os.path.dirname(__file__), "Backups")
        self.database_path = databasePath
        self.log_file_path = log_file
        self.settings_path = settingsFilePath

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

    def closeEvent(self, event):
        # Log shutdown
        logger.log_shutdown()
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
        default_settings = {"start_day": 21, "end_day": 20, "printer_IP": "10.60.1.146"}

        if os.path.exists(settings_file):
            with open(settings_file, "r") as file:
                return json.load(file)
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
            self.generate_all_timesheets(end_day)

    def setup_ui(self):
        # Ensure central widget is persistently defined
        if not hasattr(self, "central_widget") or self.central_widget is None:
            self.central_widget = QWidget()
            self.setCentralWidget(self.central_widget)

        # Define color scheme
        self.COLORS = {
            'primary': '#1a73e8',      # Blue
            'success': '#34a853',      # Green
            'danger': '#ea4335',       # Red
            'warning': '#fbbc05',      # Yellow
            'dark': '#202124',         # Dark gray
            'light': '#ffffff',        # White
            'gray': '#5f6368',         # Medium gray
            'purple': '#9334e8',       # Purple for visitor
            'brown': '#795548',        # Brown for admin
        }

        # Main layout with proper margins
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(40, 20, 40, 20)
        self.central_widget.setLayout(main_layout)

        # Top layout for clock and logo
        top_layout = QHBoxLayout()
        top_layout.setSpacing(20)

        # Clock Label with modern font
        self.clock_label = QLabel()
        self.clock_label.setFont(QFont("Arial", 64, QFont.Weight.Medium))
        self.clock_label.setStyleSheet(f"color: {self.COLORS['light']}; margin-bottom: 10px;")
        self.clock_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.update_time()

        # Add the clock widget to the top-left
        top_layout.addWidget(self.clock_label, alignment=Qt.AlignmentFlag.AlignLeft)

        # Logo Layout (Top-right alignment)
        logo_label = QLabel()
        pixmap = QPixmap(logoPath)
        scaled_pixmap = pixmap.scaled(150, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        logo_label.setPixmap(scaled_pixmap)
        logo_label.setFixedSize(150, 80)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_layout.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignRight)

        main_layout.addLayout(top_layout)

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

        # QR Scan Button
        self.qr_scan_button = self.create_styled_button(
            "Scan QR Code",
            self.COLORS['primary'],
            lambda: self.scan_qr_code()
        )
        button_layout.addWidget(self.qr_scan_button)

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
        button_layout.addLayout(clock_buttons_layout)

        self.central_widget.installEventFilter(self)

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


    def generate_qr_code(self, staff_code):
        """Generate a QR code for the given staff code and save it, then show a dialog."""
        qr_folder = os.path.join(os.path.dirname(__file__), "QR_Codes")
        os.makedirs(qr_folder, exist_ok=True)
        qr_code_file = os.path.join(qr_folder, f"{staff_code}.png")

        # Generate QR Code
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(staff_code)
        qr.make(fit=True)
        img = qr.make_image(fill="black", back_color="white")
        img.save(qr_code_file)

        logging.info(f"Generated QR code for staff code {staff_code} at {qr_code_file}")

        # Show QR Code dialog
        self.show_qr_code_dialog(qr_code_file)

    def show_qr_code_dialog(self, qr_code_file):
        """Show a dialog with the QR code image."""
        dialog = QDialog(self)
        dialog.setWindowTitle("QR Code")
        dialog.setFixedSize(400, 400)

        layout = QVBoxLayout(dialog)

        qr_label = QLabel(dialog)
        pixmap = QPixmap(qr_code_file)
        qr_label.setPixmap(pixmap)
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        close_button = QPushButton("Close", dialog)
        close_button.clicked.connect(dialog.close)

        layout.addWidget(qr_label)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignCenter)

        dialog.setLayout(layout)
        dialog.exec()

    def scan_qr_code(self):
        """Start/stop QR code scanning based on the button state."""
        if self.scanner_active:
            self.stop_scanner()  # Stop scanning if already active
            self.qr_scan_button.setText("Scan QR Code")
            return

        self.qr_scan_button.setText("Stop Scan")
        self.scanner_active = True
        self.cap = cv2.VideoCapture(0)  # Open the default camera

        detector = cv2.QRCodeDetector()

        logging.info("Camera started for QR scanning...")

        # Create or show the QLabel for the camera preview
        if not hasattr(self, "camera_preview"):
            self.camera_preview = QLabel(self)
            self.camera_preview.setFixedSize(300, 300)  # Set preview box size
            self.camera_preview.setStyleSheet("border: 2px solid white; background-color: black;")
            self.camera_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.central_widget.layout().addWidget(self.camera_preview)

        self.camera_preview.setScaledContents(False)  # Preserve aspect ratio
        self.camera_preview.show()  # Show the preview box

        def run_scanner():
            while self.cap.isOpened() and self.scanner_active:
                ret, frame = self.cap.read()
                if not ret:
                    break

                # Get QLabel's size and calculate the resized frame dimensions
                label_width = self.camera_preview.width()
                label_height = self.camera_preview.height()
                frame_height, frame_width = frame.shape[:2]
                aspect_ratio = frame_width / frame_height

                # Calculate new dimensions while preserving aspect ratio
                if label_width / label_height > aspect_ratio:
                    new_height = label_height
                    new_width = int(aspect_ratio * label_height)
                else:
                    new_width = label_width
                    new_height = int(label_width / aspect_ratio)

                resized_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

                # Convert to RGB and display the frame
                rgb_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
                q_img = QImage(rgb_frame.data, new_width, new_height, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(q_img)

                self.camera_preview.setPixmap(pixmap)

                # Detect and decode QR Code
                data, _, _ = detector.detectAndDecode(frame)
                if data:
                    logging.info(f"QR Code detected: {data}")
                    self.staff_code_entry.setText(data)  # Automatically fill the staff code entry
                    break

            self.stop_scanner()

        Thread(target=run_scanner, daemon=True).start()

    def stop_scanner(self):
        """Stop the QR scanner and hide the camera preview."""
        if self.cap:
            self.cap.release()
        self.scanner_active = False
        if hasattr(self, "camera_preview"):
            self.camera_preview.clear()  # Clear the video feed
            self.camera_preview.hide()  # Hide the QLabel
        self.qr_scan_button.setText("Scan QR Code")
        logging.info("Camera stopped for QR scanning.")

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
        elif staff_code == '123456':  # Admin code
            self.greeting_label.setText("Admin Mode Activated")
            self.admin_button.show()
            self.admin_button.click()
            self.admin_button.setVisible(True)  # Show the admin button
        elif staff_code == '654321':  # Exit code
            self.greeting_label.setText("Exit Mode Activated")
            self.closeEvent()
        elif staff_code =='111111':
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
        settings_dialog.setFixedSize(400, 300)
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

            # Show testing message
            self.msg("Testing printer connection...", "info", "Testing")
            
            # Test printer connection
            success, message = self.test_printer_connection(printer_ip)
            if not success:
                self.msg(f"Printer validation failed: {message}", "warning", "Error")
                return

            # If we get here, the printer connection was successful
            # Save all settings
            self.settings["start_day"] = start_day
            self.settings["end_day"] = end_day
            self.settings["printer_IP"] = printer_ip

            self.save_settings()
            self.msg("Settings saved successfully. Printer connection verified.", "info", "Success")
            
        except ValueError as e:
            self.msg(f"Invalid settings: {e}", "warning", "Error")
        except Exception as e:
            self.msg(f"Error saving settings: {e}", "warning", "Error")
            logging.error(f"Error saving settings: {e}")

    def open_admin_tab(self):
        logging.info("Opening admin tab")
        self.admin_tab = QDialog(self)
        self.admin_tab.setWindowTitle('Admin Panel')
        self.admin_tab.setFixedSize(600, 800)
        self.admin_tab.setStyleSheet(f"""
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
        """)

        # Store the admin tab state
        self.admin_was_open = False
        self.admin_tab.closeEvent = self.handle_admin_close

        layout = QVBoxLayout(self.admin_tab)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        # Name input with modern styling
        name_label = QLabel("Enter Name:")
        name_label.setFont(QFont("Inter", 16))
        self.name_entry = QLineEdit()
        self.name_entry.setFont(QFont("Inter", 16))
        self.name_entry.textChanged.connect(self.update_pin_label)
        self.name_entry.editingFinished.connect(lambda: self.update_role_from_name(self.name_entry.text()))
        
        layout.addWidget(name_label)
        layout.addWidget(self.name_entry)

        # Role Field
        role_label = QLabel("Enter Role:")
        role_label.setFont(QFont("Inter", 16))
        self.role_entry = QLineEdit()
        self.role_entry.setFont(QFont("Inter", 16))
        layout.addWidget(role_label)
        layout.addWidget(self.role_entry)

        # Add role completer
        role_completer = QCompleter(self.fetch_unique_roles(), self)
        role_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        role_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.role_entry.setCompleter(role_completer)

        # Add name completer
        completer = QCompleter(self.fetch_staff_names_and_roles(), self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.name_entry.setCompleter(completer)

        # PIN Label
        self.pin_label = QLabel("PIN")
        self.pin_label.setFont(QFont("Inter", 16))
        layout.addWidget(self.pin_label)

        # Create a grid layout for buttons
        button_grid = QGridLayout()
        button_grid.setSpacing(15)

        # Define button configurations - reorganized as requested
        buttons = [
            ("Add Staff", self.COLORS['success'], self.add_staff, 0, 0),
            ("Delete Staff", self.COLORS['danger'], self.remove_staff, 0, 1),
            ("View Records", self.COLORS['primary'], self.open_records_tab, 1, 0),
            ("Print Records", self.COLORS['purple'], lambda: self.preparePrint("records"), 1, 1),
            ("Generate Timesheet", self.COLORS['warning'], lambda: self.generate_one_timesheet(), 2, 0),
            ("Print Timesheet", self.COLORS['primary'], lambda: self.preparePrint("timesheet"), 2, 1),
            ("Settings", self.COLORS['gray'], self.open_settings_menu, 3, 0),
            ("View Visitors", self.COLORS['brown'], self.open_visitors_tab, 3, 1),
            ("Add Comment", self.COLORS['purple'], self.add_comment, 4, 0),
            ("Exit", self.COLORS['danger'], self.admin_tab.close, 4, 1)
        ]

        # Create and add buttons to grid
        for text, color, callback, row, col in buttons:
            button = QPushButton(text)
            button.setFont(QFont("Inter", 14))
            button.setMinimumSize(200, 50)
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: {self.COLORS['light']};
                    border-radius: 8px;
                    border: none;
                    padding: 10px;
                }}
                QPushButton:hover {{
                    background-color: {color}dd;
                }}
            """)
            button.clicked.connect(callback)
            button_grid.addWidget(button, row, col)

        layout.addLayout(button_grid)

        self.admin_tab.exec()

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

    def update_pin_label(self):
        """Update the PIN label dynamically based on the entered name."""
        staff_name = self.name_entry.text().strip()
        if not staff_name:
            self.pin_label.setText("PIN: ")
            return

        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            cursor.execute("SELECT code FROM staff WHERE name LIKE ?", (f"%{staff_name}%",))
            result = cursor.fetchone()
            conn.close()

            if result:
                self.pin_label.setText(f"PIN: {result[0]}")
            else:
                self.pin_label.setText("PIN: Not Found")
        except sqlite3.Error as e:
            logging.error(f"Database error while fetching PIN: {e}")
            self.pin_label.setText("PIN: Error")

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
                self.msg(f"Staff member {staff_name} added with code {staff_code}.", "info", "Success")
                logging.info(f"Staff member {staff_name} added with code {staff_code} and role {staff_role}.")
                self.generate_qr_code(staff_code)
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
                timesheet_path = os.path.join(permanentPath, f"{staff_name}_timesheet.pdf")
                try:
                    self.generate_timesheet(staff_name, staff_role, start_date, end_date, records)
                    
                    # Ensure the file exists before trying to print
                    if os.path.exists(timesheet_path):
                        self.print_via_jetdirect(timesheet_path)
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
        # Get date range
        start_date, end_date = self.get_date_range_for_timesheet(day_selected)

        # Fetch records
        conn = sqlite3.connect(databasePath)
        records = self.fetch_timesheet_records(conn, start_date, end_date)
        conn.close()

        if not records:
            self.msg("No records found for the selected period.", "info", "Info")
            return

        # Organize records by staff
        staff_data = {}
        for name, role, clock_in, clock_out in records:
            if name not in staff_data:
                staff_data[name] = {"role": role, "records": []}
            staff_data[name]["records"].append((clock_in, clock_out))

        # Generate timesheets for all staff
        for staff_name, details in staff_data.items():
            self.generate_timesheet(staff_name, details["role"], start_date, end_date, details["records"])

        logging.info(f"Timesheets generated for the period {start_date.strftime('%d-%m-%Y')} to {end_date.strftime('%d-%m-%Y')}")

    def generate_one_timesheet(self):
        """
        Generate a timesheet for the currently selected staff member from the admin tab.
        """
        staff_name = self.name_entry.text().strip()
        if not staff_name:
            self.msg("Please enter a valid staff name.", "warning", "Error")
            logging.error("No staff name provided for timesheet generation.")
            return

        # Fetch staff details
        conn = sqlite3.connect(databasePath)
        cursor = conn.cursor()
        cursor.execute("SELECT code FROM staff WHERE name = ?", (staff_name,))
        staff = cursor.fetchone()
        conn.close()

        if not staff:
            self.msg("Staff member not found.", "warning", "Error")
            logging.error(f"Staff member '{staff_name}' not found.")
            return

        staff_code = staff[0]

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
        output_file = f"{permanentPath}/{employee_name}_timesheet.pdf"

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

if __name__ == '__main__':
    get_os_specific_path()
    app = QApplication(sys.argv)
    window = StaffClockInOutSystem()
    window.show()
    logging.basicConfig(level=logging.DEBUG)
    sys.exit(app.exec())