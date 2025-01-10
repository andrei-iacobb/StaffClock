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

import time
import sys
from datetime import datetime, timedelta
from os import mkdir, write
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QDialog, QMessageBox, QDialogButtonBox, QTableWidget, QHeaderView, QAbstractItemView,
    QTableWidgetItem, QCompleter
)
from PyQt6.QtCore import Qt, QTimer, QTime, QEvent
from PyQt6.QtGui import QFont, QPixmap, QImage
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from timesheetDailyCheck import TimesheetCheckerThread
from dailyBackUp import DailyBackUp


tempPath = ""
permanentPath = ""
databasePath = ""
settingsFilePath = ""
log_file = ""
logoPath = ""


def get_os_specific_path():
    global tempPath, permanentPath, databasePath, settingsFilePath, log_file, logoPath, qr_code_folder_path

    # Get the base directory where main.py resides
    base_path = os.path.dirname(os.path.abspath(__file__))

    if not os.path.exists(base_path):
        raise FileNotFoundError("Base directory does not exist.")

    # OS-dependent paths
    program_data_path = os.path.join(base_path, "ProgramData")
    tempPath = os.path.join(base_path, "TempData")
    permanentPath = os.path.join(base_path, "Timesheets")
    qr_code_folder_path = os.path.join(base_path, "QR_Codes")  # Path for QR codes

    backup_folder = os.path.join(base_path, "Backups")

    # Ensure directories exist
    os.makedirs(program_data_path, exist_ok=True)
    os.makedirs(tempPath, exist_ok=True)
    os.makedirs(permanentPath, exist_ok=True)
    os.makedirs(backup_folder, exist_ok=True)

    # Paths for specific files
    settingsFilePath = os.path.join(program_data_path, "settings.json")
    log_file = os.path.join(program_data_path, "staff_clock_system.log")
    logoPath = os.path.join(program_data_path, "Logo.png")
    databasePath = os.path.join(program_data_path, "staff_hours.db")

    configure_logging()

    # Ensure files and folders exist or restore them from backups
    check_and_restore_file(databasePath, backup_folder, generate_default_database)
    check_and_restore_file(settingsFilePath, backup_folder, generate_default_settings)
    check_and_restore_folder(qr_code_folder_path, backup_folder)

def check_and_restore_folder(folder_path, backup_folder):
    """Ensure a folder exists or restore it from backup if available."""
    if os.path.exists(folder_path):
        logging.info(f"Folder found: {folder_path}")
        return

    # Search for zipped backups containing the folder
    zip_files = [
        os.path.join(backup_folder, f) for f in os.listdir(backup_folder) if f.endswith('.zip')
    ]
    zip_files.sort(key=os.path.getmtime, reverse=True)  # Sort by modification time (newest first)

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

    # If no backup exists, create the folder
    logging.warning(f"No backup found for folder '{folder_path}'. Creating new folder.")
    os.makedirs(folder_path, exist_ok=True)

def check_and_restore_file(primary_path, backup_folder, generate_default=None):
    if os.path.exists(primary_path):
        logging.info(f"File found: {primary_path}")
        return

    # Look for zipped backups
    zip_files = [
        os.path.join(backup_folder, f) for f in os.listdir(backup_folder) if f.endswith('.zip')
    ]
    zip_files.sort(key=os.path.getmtime, reverse=True)  # Sort backups by modification time (newest first)

    for zip_file in zip_files:
        try:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                # Check if the file exists in the zip archive
                if os.path.basename(primary_path) in zip_ref.namelist():
                    zip_ref.extract(os.path.basename(primary_path), os.path.dirname(primary_path))
                    logging.info(f"Restored {primary_path} from backup {zip_file}")
                    return
        except zipfile.BadZipFile:
            logging.error(f"Corrupted zip file: {zip_file}")

    # If no backup exists for files like the logo, raise an error
    if primary_path == logoPath:
        logging.error(f"Critical: Logo file not found in either {primary_path} or backups.")
        raise FileNotFoundError(f"Logo file missing and no backups available in {backup_folder}.")

    # For other files, generate default if a function is provided
    if generate_default:
        logging.warning(f"No backup found for {primary_path}. Generating default.")
        generate_default(primary_path)

def generate_default_database(path):
    conn = sqlite3.connect(path)
    c = conn.cursor()

    # Create the staff table
    c.execute('''
        CREATE TABLE IF NOT EXISTS staff (
            name TEXT NOT NULL,
            code TEXT UNIQUE PRIMARY KEY,
            fingerprint TEXT,
            role TEXT,
            notes TEXT
        )
    ''')

    # Create the clock_records table
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

    # Create the archive_records table
    c.execute('''
        CREATE TABLE IF NOT EXISTS archive_records (
            staff_name TEXT,
            staff_code TEXT,
            clock_in TEXT,
            clock_out TEXT,
            notes TEXT
        )
    ''')

    conn.commit()
    conn.close()
    logging.info(f"Default database created at {path}")

def generate_default_settings(path):
    default_settings = {"start_day": 21, "end_day": 20, "printer_IP": "10.60.1.146"}
    with open(path, "w") as file:
        json.dump(default_settings, file)
    logging.info(f"Default settings file created at {path}")

def configure_logging():
    logging.basicConfig(
        filename=log_file,
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logging.info("Logging initialized.")

class StaffClockInOutSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        self.role_entry = QLineEdit()
        self.setWindowTitle("Staff Digital Timesheet System")
        self.showMaximized()
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        logging.info("UI setup complete.")

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

    def handle_timesheet_generated(self, message):
        logging.info(message)
        self.generate_all_timesheets(self.settings["end_day"])

    def closeEvent(self, event):
        # Ensure the thread stops when the app closes
        self.daily_backup_thread.stop()
        self.daily_backup_thread.wait()
        super().closeEvent(event)

    def handle_backup_complete(self, message):
        logging.info(message)
        QMessageBox.information(self, "Backup", message)

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

        # Main layout
        main_layout = QVBoxLayout()
        self.central_widget.setLayout(main_layout)

        # Top layout for clock and logo
        top_layout = QHBoxLayout()
        top_layout.setSpacing(0)

        # Clock Label
        self.clock_label = QLabel()
        self.clock_label.setFont(QFont("Arial", 64, QFont.Weight.Bold))
        self.clock_label.setStyleSheet("color: white;")
        self.clock_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.update_time()  # Initialize the clock with the current time

        # Add the clock widget to the top-left
        top_layout.addWidget(self.clock_label, alignment=Qt.AlignmentFlag.AlignLeft)

        # Logo Layout (Top-right alignment)
        logo_label = QLabel()
        pixmap = QPixmap(logoPath)
        logo_label.setPixmap(pixmap)
        logo_label.setFixedSize(150, 80)
        logo_label.setScaledContents(True)
        top_layout.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignRight)

        # Add top layout to the main layout
        main_layout.addLayout(top_layout)

        # Spacer
        main_layout.addSpacing(30)

        # Staff Code Input Section
        staff_code_layout = QVBoxLayout()
        staff_code_label = QLabel("Enter Staff Code:")
        staff_code_label.setFont(QFont("Arial", 38, QFont.Weight.Bold))
        staff_code_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.staff_code_entry = QLineEdit()
        self.staff_code_entry.setFont(QFont("Arial", 26))
        self.staff_code_entry.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.staff_code_entry.setPlaceholderText("Enter your 4-digit code")
        self.staff_code_entry.setStyleSheet(
            "background-color: #444; color: white; border: 1px solid #555; padding: 8px; border-radius: 5px;"
        )
        self.staff_code_entry.textChanged.connect(self.on_staff_code_change)

        self.greeting_label = QLabel("")
        self.greeting_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        self.greeting_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        staff_code_layout.addWidget(staff_code_label)
        staff_code_layout.addWidget(self.staff_code_entry)
        staff_code_layout.addWidget(self.greeting_label)
        main_layout.addLayout(staff_code_layout)

        # Spacer
        main_layout.addSpacing(50)

        # Buttons Layout
        button_layout = QVBoxLayout()
        button_layout.setSpacing(20)

        # Clock In and Clock Out Buttons
        clock_buttons_layout = QHBoxLayout()
        clock_buttons_layout.setSpacing(20)

        self.qr_scan_button = QPushButton("Scan QR Code")
        self.qr_scan_button.setFont(QFont("Arial", 18))
        self.qr_scan_button.setMinimumSize(250, 60)
        self.qr_scan_button.setStyleSheet("background-color: #17a2b8; color: white; border-radius: 8px;")
        self.qr_scan_button.clicked.connect(self.scan_qr_code)
        button_layout.addWidget(self.qr_scan_button)

        self.clock_in_button = QPushButton("Enter Building")
        self.clock_in_button.setFont(QFont("Arial", 18))
        self.clock_in_button.setMinimumSize(250, 60)
        self.clock_in_button.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 8px;")
        self.clock_in_button.clicked.connect(lambda: self.clock_action('in', self.staff_code_entry.text()))
        clock_buttons_layout.addWidget(self.clock_in_button)

        self.clock_out_button = QPushButton("Exit Building")
        self.clock_out_button.setFont(QFont("Arial", 18))
        self.clock_out_button.setMinimumSize(250, 60)
        self.clock_out_button.setStyleSheet("background-color: #F44336; color: white; border-radius: 8px;")
        self.clock_out_button.clicked.connect(lambda: self.clock_action('out', self.staff_code_entry.text()))
        clock_buttons_layout.addWidget(self.clock_out_button)

        # Admin and Exit Buttons
        self.admin_button = QPushButton("Admin")
        self.admin_button.setFont(QFont("Arial", 18))
        self.admin_button.setMinimumSize(250, 60)
        self.admin_button.setStyleSheet("background-color: #2196F3; color: white; border-radius: 8px;")
        self.admin_button.clicked.connect(self.open_admin_tab)
        self.admin_button.hide()
        button_layout.addWidget(self.admin_button)

        self.exit_button = QPushButton("Exit")
        self.exit_button.setFont(QFont("Arial", 18))
        self.exit_button.setMinimumSize(250, 60)
        self.exit_button.setStyleSheet("background-color: #555555; color: white; border-radius: 8px;")
        self.exit_button.clicked.connect(self.close)
        self.exit_button.hide()
        button_layout.addWidget(self.exit_button)

        main_layout.addLayout(button_layout)
        button_layout.addLayout(clock_buttons_layout)

        self.central_widget.installEventFilter(self)

        main_layout.addWidget(self.create_footer())

        # Set Background Style
        self.setStyleSheet(
            "background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #2b2b2b, stop:1 #444); color: white;"
        )

    def create_footer(self):
        """Create a smaller footer with fixed size."""
        footer = QLabel("© 2025 Andrei Iacob. All rights reserved.")
        footer.setFont(QFont("Arial", 10))  # Set smaller font size
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setFixedHeight(30)  # Set fixed height for the footer
        footer.setStyleSheet("color: gray; margin: 0; padding: 0;")  # Minimal styling
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
        conn = sqlite3.connect(databasePath)
        c = conn.cursor()

        # Check if the staff exists
        c.execute('SELECT * FROM staff WHERE code = ?', (staff_code,))
        staff = c.fetchone()
        if not staff:
            conn.close()
            QMessageBox.critical(self, 'Error', 'Invalid staff code')
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
                    QMessageBox.information(self, 'Break Started', 'Your break has started.')
                    logging.info(f"Break started for staff code {staff_code} at {self.break_start_time}")
                else:
                    QMessageBox.warning(self, 'Error', 'You are already on a break.')
            else:
                # Regular Clock-In
                clock_in_time = datetime.now().isoformat()
                c.execute('INSERT INTO clock_records (staff_code, clock_in_time) VALUES (?, ?)',
                          (staff_code, clock_in_time))
                conn.commit()
                time_in = datetime.fromisoformat(clock_in_time).strftime('%H:%M')
                QMessageBox.information(self, 'Success', f'Clock-in recorded successfully at {time_in}')
                logging.info(f"Clock-in successful for staff code {staff_code} at {time_in}")
            self.staff_code_entry.clear()

        elif action == 'out':
            # Check if on break
            if self.on_break:
                # End Break
                break_end_time = datetime.now()
                break_duration = (break_end_time - self.break_start_time).total_seconds() / 60  # Duration in minutes
                c.execute('UPDATE clock_records SET break_time = ? WHERE staff_code = ? AND clock_out_time IS NULL',
                          (str(break_duration), staff_code))
                conn.commit()
                self.on_break = False
                self.break_start_time = None
                QMessageBox.information(self, 'Break Ended', f'Your break lasted {break_duration:.2f} minutes.')
                logging.info(f"Break ended for staff code {staff_code}. Duration: {break_duration:.2f} minutes.")
            else:
                # Regular Clock-Out
                clock_out_time = datetime.now().isoformat()
                c.execute('SELECT id FROM clock_records WHERE staff_code = ? AND clock_out_time IS NULL', (staff_code,))
                clock_record = c.fetchone()
                if not clock_record:
                    conn.close()
                    QMessageBox.critical(self, 'Error', 'No clock-in record found')
                    return
                c.execute('UPDATE clock_records SET clock_out_time = ? WHERE id = ?', (clock_out_time, clock_record[0]))
                conn.commit()
                time_out = datetime.fromisoformat(clock_out_time).strftime('%H:%M')
                QMessageBox.information(self, 'Success', f'Clock-out recorded successfully at {time_out}')
                logging.info(f"Clock-out successful for staff code {staff_code} at {time_out}")
            self.staff_code_entry.clear()

        else:
            conn.close()
            QMessageBox.critical(self, 'Error', 'Invalid action')
        self.clock_in_button.setText("Enter Building")
        self.clock_out_button.setText("Exit Building")

    def process_clock_action(self, user_id, action="in"):
        """Process clock-in or clock-out based on user ID or staff code."""
        conn = sqlite3.connect(databasePath)
        c = conn.cursor()

        # Check if the staff exists
        c.execute('SELECT * FROM staff WHERE code = ?', (user_id,))
        staff = c.fetchone()
        if not staff:
            conn.close()
            QMessageBox.critical(self, "Error", "Invalid user ID or staff code.")
            return

        if action == "in":
            self.clock_action("in", user_id)
        elif action == "out":
            self.clock_action("out", user_id)
        else:
            QMessageBox.warning(self, "Action Error", f"Unknown action: {action}")
        conn.close()

    def on_staff_code_change(self):
        staff_code = self.staff_code_entry.text()
        if len(staff_code) == 4 and staff_code.isdigit():
            conn = sqlite3.connect(databasePath)
            c = conn.cursor()
            c.execute('SELECT name FROM staff WHERE code = ?', (staff_code,))
            staff = c.fetchone()
            conn.close()
            if staff:
                self.greeting_label.setText(f'Hello, {staff[0]}!')

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
                self.greeting_label.setText('')
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
        logging.info("Fire system triggerd!")
        logging.info("Gathering time right now.")
        time_now = datetime.now().strftime('%Y-%m-%d')  # Today's date
        print(f"Today's date: {time_now}")  # Debugging: print the date being queried

        logging.info("Connecting to database")
        conn = sqlite3.connect(databasePath)
        c = conn.cursor()

        logging.info("Executing SQL command!")
        c.execute('''
            SELECT s.name, c.clock_in_time
            FROM clock_records c
            JOIN staff s ON c.staff_code = s.code
            WHERE DATE(c.clock_in_time) = ?
        ''', (time_now,))
        records = c.fetchall()

        # Remove duplicates and keep only the first occurrence of each name
        unique_records = {}
        for record in records:
            name = record[0]
            clock_in_time = record[1]
            if name not in unique_records:
                unique_records[name] = clock_in_time

        if not records:
            print("No records found for today's date.")
        else:
            # Generate the PDF
            doc = SimpleDocTemplate('fire.pdf')
            elements = []
            styles = getSampleStyleSheet()

            elements.append(Paragraph("Fire Records", styles['Title']))
            elements.append(Spacer(1, 12))

            # Format and add unique records to the PDF
            for name, clock_in_time in unique_records.items():
                # Convert ISO format to "HH:MM DD/MM/YYYY"
                readable_time = datetime.fromisoformat(clock_in_time).strftime('%H:%M %d/%m/%Y')
                elements.append(Paragraph(f"Name: {name}, Clock In Time: {readable_time}", styles['Normal']))
                elements.append(Spacer(1, 6))

            logging.info("Building document!")
            doc.build(elements)

            logging.info("Exiting Database")
            conn.close()

            self.print_via_jetdirect('fire.pdf')

    def open_settings_menu(self):
        """
        Open the settings dialog, including start day, end day, and printer IP settings.
        """
        settings_dialog = QDialog(self)
        settings_dialog.setWindowTitle("Settings")
        settings_dialog.setFixedSize(400, 250)

        layout = QVBoxLayout(settings_dialog)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # Start Day and End Day (Side by Side)
        day_layout = QHBoxLayout()
        start_label = QLabel("Start Day:")
        self.start_day_input = QLineEdit(str(self.settings["start_day"]))
        self.start_day_input.setFixedWidth(80)

        end_label = QLabel("End Day:")
        self.end_day_input = QLineEdit(str(self.settings["end_day"]))
        self.end_day_input.setFixedWidth(80)

        day_layout.addWidget(start_label)
        day_layout.addWidget(self.start_day_input)
        day_layout.addSpacing(40)  # Add some space between Start and End inputs
        day_layout.addWidget(end_label)
        day_layout.addWidget(self.end_day_input)
        layout.addLayout(day_layout)

        # Printer IP Address Input
        ip_label = QLabel("Printer IP:")
        self.printer_ip_input = QLineEdit(self.settings.get("printer_IP", ""))
        self.printer_ip_input.setPlaceholderText("Enter Printer IP Address")
        layout.addWidget(ip_label)
        layout.addWidget(self.printer_ip_input)

        # Save Button
        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self.save_settings_from_menu)
        layout.addWidget(save_button)

        settings_dialog.exec()

    def save_settings_from_menu(self):
        """
        Save the settings from the settings menu.
        """
        try:
            # Validate and save start and end days
            start_day = int(self.start_day_input.text())
            end_day = int(self.end_day_input.text())
            if not (1 <= start_day <= 31 and 1 <= end_day <= 31):
                raise ValueError("Days must be between 1 and 31.")
            self.settings["start_day"] = start_day
            self.settings["end_day"] = end_day

            # Save Printer IP
            printer_ip = self.printer_ip_input.text().strip()
            if not printer_ip:
                raise ValueError("Printer IP cannot be empty.")
            self.settings["printer_IP"] = printer_ip

            self.save_settings()

            QMessageBox.information(self, "Success", "Settings saved successfully.")
        except ValueError as e:
            QMessageBox.critical(self, "Error", f"Invalid input: {e}")

    def open_admin_tab(self):
        logging.info("Opening admin tab")
        admin_tab = QDialog(self)
        admin_tab.setWindowTitle('Admin Page')
        admin_tab.setFixedSize(500, 700)
        layout = QVBoxLayout(admin_tab)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        name_label = QLabel("Enter Name:")
        name_label.setFont(QFont("Arial", 16))
        self.name_entry = QLineEdit()
        self.name_entry.setFont(QFont("Arial", 16))
        self.name_entry.textChanged.connect(self.update_pin_label)
        layout.addWidget(name_label)
        layout.addWidget(self.name_entry)

        completer = QCompleter(self.fetch_staff_names_and_roles(), self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.name_entry.setCompleter(completer)

        self.pin_label = QLabel("PIN")
        self.pin_label.setFont(QFont("Arial", 16))
        layout.addWidget(self.pin_label)

        layout.addWidget(name_label)
        layout.addWidget(self.name_entry)

        add_staff_button = QPushButton("Add Staff")
        add_staff_button.setFont(QFont("Arial", 16))
        add_staff_button.setMinimumSize(150, 50)
        add_staff_button.setStyleSheet("background-color: #28a745; color: white;")  # Green shade
        add_staff_button.clicked.connect(self.add_staff)
        layout.addWidget(add_staff_button)

        delete_staff_button = QPushButton("Delete Staff")
        delete_staff_button.setFont(QFont("Arial", 16))
        delete_staff_button.setMinimumSize(150, 50)
        delete_staff_button.setStyleSheet("background-color: #dc3545; color: white;")  # Red shade
        delete_staff_button.clicked.connect(self.remove_staff)
        layout.addWidget(delete_staff_button)

        view_records_button = QPushButton("View Records")
        view_records_button.setFont(QFont("Arial", 16))
        view_records_button.setMinimumSize(150, 50)
        view_records_button.setStyleSheet("background-color: #007bff; color: white;")  # Blue shade
        view_records_button.clicked.connect(self.open_records_tab)
        layout.addWidget(view_records_button)

        print_records_button = QPushButton("Print Records")
        print_records_button.setFont(QFont("Arial", 16))
        print_records_button.setMinimumSize(150, 50)
        print_records_button.setStyleSheet("background-color: #6f42c1; color: white;")  # Purple shade
        print_records_button.clicked.connect(self.preparePrint)
        layout.addWidget(print_records_button)

        generate_timesheet_button = QPushButton("Generate Timesheet")
        generate_timesheet_button.setFont(QFont("Arial", 16))
        generate_timesheet_button.setMinimumSize(150, 50)
        generate_timesheet_button.setStyleSheet("background-color: #17a2b8; color: white;")  # Teal shade
        generate_timesheet_button.clicked.connect(lambda: self.generate_one_timesheet())
        layout.addWidget(generate_timesheet_button)

        settings_button = QPushButton("Settings")
        settings_button.setFont(QFont("Arial", 16))
        settings_button.setMinimumSize(150, 50)
        settings_button.setStyleSheet("background-color: #ffc107; color: black;")  # Yellow shade with black text
        settings_button.clicked.connect(self.open_settings_menu)
        layout.addWidget(settings_button)

        # Add this in setup_ui where you define the windowed_button
        self.windowed_button = QPushButton("Enter Windowed Mode")
        self.windowed_button.setFont(QFont("Arial", 16))
        self.windowed_button.setMinimumSize(150, 50)
        self.windowed_button.setStyleSheet("background-color: #20c997; color: white;")  # Cyan shade
        self.windowed_button.clicked.connect(self.toggle_window_mode)
        layout.addWidget(self.windowed_button)

        self.add_comment_button = QPushButton("Add Comment")
        self.add_comment_button.setFont(QFont("Arial", 16))
        self.add_comment_button.setMinimumSize(150, 50)
        self.add_comment_button.setStyleSheet("background-color: #e83e8c; color: white;")  # Pink shade
        self.add_comment_button.clicked.connect(self.add_comment)
        layout.addWidget(self.add_comment_button)
        admin_tab.exec()

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
            QMessageBox.warning(self, "Warning", "Please enter a Name")
            logging.error("No staff name entered.")
            return

        # Check if staff exists
        conn = sqlite3.connect(databasePath)
        c = conn.cursor()
        c.execute("SELECT code FROM staff WHERE name = ?", (staff_name,))
        staff = c.fetchone()
        if not staff:
            conn.close()
            QMessageBox.warning(self, "Warning", "No staff found")
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
            QMessageBox.warning(self, "Warning", "Comment cannot be empty.")
            return

        try:
            conn = sqlite3.connect(databasePath)
            c = conn.cursor()
            c.execute("UPDATE staff SET notes = ? WHERE name = ?", (comment, staff_name))
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Success", "Comment added to staff record.")
            logging.info(f"Added comment to staff {staff_name}: {comment}")
            dialog.close()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Error", f"Database error: {e}")
            logging.error(f"Database error: {e}")

    def add_clock_record_comment(self, staff_code, parent_menu):
        """Allow the user to select a clock record and add a comment."""
        parent_menu.close()

        # Fetch clock records
        records = self.fetch_clock_records(staff_code)
        if not records:
            QMessageBox.information(self, "Info", "No clock records found for this staff member.")
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
            QMessageBox.critical(self, "Error", f"Unable to fetch records: {e}")
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
            QMessageBox.critical(self, "Error", "Please enter a valid staff name.")
            logging.error(f"Error: Invalid staff name '{staff_name}'")
            return

        try:
            conn = sqlite3.connect(databasePath)
            cursor = conn.cursor()
            cursor.execute('SELECT code FROM staff WHERE name = ?', (staff_name,))
            staff = cursor.fetchone()

            if not staff:
                QMessageBox.critical(self, "Error", "Staff member not found.")
                logging.error(f"Staff member '{staff_name}' not found.")
                return

            staff_code = staff[0]
            cursor.execute('SELECT id, clock_in_time, clock_out_time FROM clock_records WHERE staff_code = ?',
                           (staff_code,))
            records = cursor.fetchall()
            conn.close()

            if not records:
                QMessageBox.information(self, "Info", "No records found for this staff member.")
                logging.warning(f"No records found for staff '{staff_name}'.")
                return

        except sqlite3.Error as e:
            QMessageBox.critical(self, "Error", f"Database error: {e}")
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
        """Fetch all staff names and roles from the database."""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM staff")
            names_and_roles = [f"{row[0]}" for row in cursor.fetchall()]
            conn.close()
            return names_and_roles
        except sqlite3.Error as e:
            logging.error(f"Error fetching staff names and roles: {e}")
            return []

    def open_records_tab(self):
        """Opens a fixed-size tab to view clock records for a selected staff."""
        logging.debug("Starting open_records_tab function")
        staff_name = self.name_entry.text().strip()
        if not staff_name:
            QMessageBox.critical(self, "Error", "Please enter a valid staff name.")
            logging.error(f"Error: Invalid staff name '{staff_name}'")
            return

        try:
            conn = sqlite3.connect(databasePath)
            cursor = conn.cursor()
            cursor.execute('SELECT code FROM staff WHERE name = ?', (staff_name,))
            staff = cursor.fetchone()

            if not staff:
                QMessageBox.critical(self, "Error", "Staff member not found.")
                logging.error(f"Staff member '{staff_name}' not found.")
                return

            staff_code = staff[0]
            cursor.execute('SELECT id, clock_in_time, clock_out_time, notes FROM clock_records WHERE staff_code = ?',
                           (staff_code,))
            records = cursor.fetchall()
            conn.close()

            if not records:
                QMessageBox.information(self, "Info", "No records found for this staff member.")
                logging.warning(f"No records found for staff '{staff_name}'.")
                return

        except sqlite3.Error as e:
            QMessageBox.critical(self, "Error", f"Database error: {e}")
            logging.error(f"Database error occurred: {e}")
            return

        # Create a dialog for displaying records
        records_dialog = QDialog(self)
        records_dialog.setWindowTitle(f"Clock Records for {staff_name}")
        records_dialog.setFixedSize(500, 1000)

        # Position the dialog at the top of the screen
        screen_geometry = QApplication.primaryScreen().geometry()
        records_dialog.move(screen_geometry.x(), screen_geometry.y())

        layout = QVBoxLayout(records_dialog)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # Add a QTableWidget for displaying records
        table = QTableWidget(len(records), 4)
        table.setHorizontalHeaderLabels(["Clock In", "Clock Out", "Notes", "Edit"])
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Make non-editable by default

        # Populate the table with records
        for row, record in enumerate(records):
            clock_in_time = (
                datetime.fromisoformat(record[1]).strftime('%H:%M %d/%m/%y') if record[1] else "N/A"
            )
            clock_out_time = (
                datetime.fromisoformat(record[2]).strftime('%H:%M %d/%m/%y') if record[2] else "N/A"
            )

            clock_in_item = QTableWidgetItem(clock_in_time)
            clock_out_item = QTableWidgetItem(clock_out_time)
            notes_item = QTableWidgetItem(record[3] if record[3] else "N/A")

            table.setItem(row, 0, clock_in_item)
            table.setItem(row, 1, clock_out_item)
            table.setItem(row, 2, notes_item)

            # Add an "Edit" button to each row
            edit_button = QPushButton("Edit")
            edit_button.setFont(QFont("Arial", 12))  # Smaller font for better visibility
            edit_button.setMinimumSize(80, 30)  # Smaller button size
            edit_button.clicked.connect(lambda _, rid=record[0]: self.edit_clock_record(rid))
            table.setCellWidget(row, 3, edit_button)

        layout.addWidget(table)

        # Add a Close button at the bottom
        close_button = QPushButton("Close")
        close_button.setFont(QFont("Arial", 14))
        close_button.setMinimumSize(120, 40)
        close_button.clicked.connect(records_dialog.close)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignCenter)

        records_dialog.exec()

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
            QMessageBox.warning(self, "Warning", "Record not found.")
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

            QMessageBox.information(self, "Success", "Record updated successfully.")
            logging.info(
                f"Updated clock record ID {record_id}: Clock In: {clock_in}, Clock Out: {clock_out}, Notes: {notes}")
            dialog.close()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Error", f"Database error: {e}")
            logging.error(f"Database error occurred: {e}")

    def save_clock_reocrd_comment(self, record_id, comment, dialog):
        """Save the comment to the database."""
        if not comment.strip():
            QMessageBox.warning(self, "Warning", "Comment cannot be empty.")
            return

        try:
            conn = sqlite3.connect(databasePath)
            cursor = conn.cursor()
            cursor.execute("UPDATE clock_records SET notes = ? WHERE id = ?", (comment.strip(), record_id))
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Success", "Comment added to clock record.")
            dialog.close()
            logging.info(f"Added comment to record ID {record_id}: {comment}")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Error", f"Database error: {e}")
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

        if not staff_name:
            QMessageBox.warning(self, "Warning", "Please enter a valid name.")
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
                c.execute('INSERT INTO staff (name, code) VALUES (?, ?)', (staff_name, staff_code))
                conn.commit()
                QMessageBox.information(
                    self, 'Success', f'Staff member {staff_name} with code {staff_code}.'
                )
                logging.info(f"Staff member {staff_name} added with code {staff_code}.")
                self.generate_qr_code(staff_code)
                break
            except sqlite3.Error as e:
                QMessageBox.critical(self, 'Database Error', f'An error occurred: {e}')
                logging.error(f"Database error occurred: {e}")
            finally:
                conn.close()
            retries += 1
        else:
            QMessageBox.warning(self, "Warning", "Could not add staff after multiple retries.")
            logging.error(f"Failed to add staff member {staff_name}.")

    def remove_staff(self):
        staff_name = self.name_entry.text().strip()
        if not staff_name:
            QMessageBox.critical(self, "Error", "Please enter a valid staff name.")
            logging.error("Staff name is empty.")
            return

        try:
            conn = sqlite3.connect(databasePath)
            c = conn.cursor()

            # Check if the staff member exists
            c.execute('SELECT code FROM staff WHERE name = ?', (staff_name,))
            staff = c.fetchone()
            if not staff:
                QMessageBox.critical(self, "Error", "Staff member not found.")
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

            QMessageBox.information(self, "Success", f"Staff member {staff_name} archived and deleted successfully.")
            logging.info(f"Archived and removed staff member: {staff_name}")

        except sqlite3.Error as e:
            QMessageBox.critical(self, "Error", f"Database error: {e}")
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

    def open_pdf(self, file_path):
        """Open the generated PDF using the default system viewer."""
        try:
            if platform.system() == "Windows":
                os.startfile(file_path)  # Windows-specific
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", file_path], check=True)
            else:  # Linux/Other
                subprocess.run(["xdg-open", file_path], check=True)
            logging.info(f"Opened PDF at '{file_path}' using the default viewer.")
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

    def open_records_tab(self):
        """Main function to handle PDF generation, opening, and deletion."""
        logging.debug("Starting open_records_tab function")
        staff_name = self.name_entry.text().strip()
        if not staff_name:
            QMessageBox.critical(self, "Error", "Please enter a valid staff name.")
            logging.error(f"Error: Invalid staff name '{staff_name}'")
            return

        try:
            conn = sqlite3.connect(databasePath)
            cursor = conn.cursor()
            cursor.execute('SELECT code FROM staff WHERE name = ?', (staff_name,))
            staff = cursor.fetchone()

            if not staff:
                QMessageBox.critical(self, "Error", "Staff member not found.")
                logging.error(f"Staff member '{staff_name}' not found.")
                return

            staff_code = staff[0]
            cursor.execute('SELECT clock_in_time, clock_out_time FROM clock_records WHERE staff_code = ?',
                           (staff_code,))
            records = cursor.fetchall()

        finally:
            conn.close()

        if not records:
            QMessageBox.information(self, "Info", "No records found for this staff member.")
            logging.warning(f"No records found for staff '{staff_name}'.")
            return

        # Path for the temporary PDF
        file_path = os.path.abspath(os.path.join(tempPath, f"{staff_name}.pdf"))

        try:
            # Generate, open, and schedule deletion of the PDF
            self.generate_pdf(file_path, staff_name, records)
            self.open_pdf(file_path)
            self.delete_pdf_after_delay(file_path, delay=10)  # Delete after 60 seconds
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")

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
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid IP address.")
            return

        # You can store or use the IP address here
        logging.info(f"Printer IP entered: {ip_address}")

        # Close the dialog
        dialog.close()

    def preparePrint(self):
        """Generate a temporary PDF for the selected staff and send it to the printer."""
        staff_name = self.name_entry.text().strip()
        if not staff_name:
            QMessageBox.warning(self, "Warning", "Please enter a valid staff name.")
            logging.error(f"Error: Invalid staff name '{staff_name}'")
            return

        try:
            # Fetch the records
            conn = sqlite3.connect(databasePath)
            cursor = conn.cursor()
            cursor.execute('SELECT code FROM staff WHERE name = ?', (staff_name,))
            staff = cursor.fetchone()

            if not staff:
                QMessageBox.critical(self, "Error", "Staff member not found.")
                logging.error(f"Staff member '{staff_name}' not found.")
                return

            staff_code = staff[0]
            cursor.execute('SELECT clock_in_time, clock_out_time FROM clock_records WHERE staff_code = ?',
                           (staff_code,))
            records = cursor.fetchall()

        finally:
            conn.close()

        if not records:
            QMessageBox.information(self, "Info", "No records found for this staff member.")
            logging.warning(f"No records found for staff '{staff_name}'.")
            return

        # Path for the temporary PDF
        file_path = os.path.abspath(os.path.join(tempPath, f"{staff_name}_temp.pdf"))

        try:
            # Generate the PDF
            self.generate_pdf(file_path, staff_name, records)

            # Print the PDF
            self.print_via_jetdirect(file_path)

            # Schedule the deletion of the temporary file
            self.delete_pdf_after_delay(file_path, delay=10)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")
            logging.error(f"Failed to prepare print for {staff_name}: {e}")

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
            QMessageBox.information(self, "Info", "No records found for the selected period.")
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
            QMessageBox.critical(self, "Error", "Please enter a valid staff name.")
            logging.error("No staff name provided for timesheet generation.")
            return

        # Fetch staff details
        conn = sqlite3.connect(databasePath)
        cursor = conn.cursor()
        cursor.execute("SELECT code FROM staff WHERE name = ?", (staff_name,))
        staff = cursor.fetchone()
        conn.close()

        if not staff:
            QMessageBox.critical(self, "Error", "Staff member not found.")
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
            QMessageBox.information(self, "Info", f"No records found for {staff_name} in the selected period.")
            logging.info(f"No records found for {staff_name} between {start_date} and {end_date}.")
            return

        # Generate the timesheet
        self.generate_timesheet(staff_name, "Unknown", start_date, end_date, records)
        QMessageBox.information(self, "Success", f"Timesheet generated for {staff_name}.")
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
            "Checked by Manager:           ……………………………………………………….. Signed       ……………………………………. Date"
        ]
        elements.append(Spacer(1, 40))
        for line in footer_lines:
            elements.append(Paragraph(line, getSampleStyleSheet()['Normal']))

        # Build the PDF
        doc.build(elements)
        logging.info(f"Built Timesheet for {employee_name}")

if __name__ == '__main__':
    get_os_specific_path()
    app = QApplication(sys.argv)
    window = StaffClockInOutSystem()
    window.show()
    logging.basicConfig(level=logging.DEBUG)
    sys.exit(app.exec())