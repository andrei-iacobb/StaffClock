import os
import platform
import sqlite3
import datetime
import random
import socket
import keyboard
import pyglet
import logging
from threading import Thread
import json
import time
import sys
from datetime import datetime, timedelta
from os import mkdir, write
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QDialog, QMessageBox, QDialogButtonBox, QTableWidget, QHeaderView, QAbstractItemView,
    QTableWidgetItem
)
from PyQt6.QtCore import Qt, QTimer, QTime, QEvent
from PyQt6.QtGui import QFont, QPixmap
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
    global tempPath, permanentPath, databasePath, settingsFilePath, log_file, logoPath

    # Get the base directory where main.py resides
    base_path = os.path.dirname(os.path.abspath(__file__))

    if not os.path.exists(base_path):
        raise FileNotFoundError("Base directory does not exist.")

    # OS-dependent paths
    if platform.system() == "Darwin":
        # macOS paths
        program_data_path = os.path.join(base_path, "ProgramData")
        tempPath = os.path.join(base_path, "TempData")
        permanentPath = os.path.join(base_path, "Timesheets")
    elif platform.system() == "Windows":
        # Windows paths
        program_data_path = os.path.join(base_path, "ProgramData")
        tempPath = os.path.join(base_path, "TempData")
        permanentPath = os.path.join(base_path, "Timesheets")
    else:
        raise OSError("Unsupported Operating System")

    # Ensure directories exist
    os.makedirs(program_data_path, exist_ok=True)
    os.makedirs(tempPath, exist_ok=True)
    os.makedirs(permanentPath, exist_ok=True)

    # Paths for specific files
    settingsFilePath = os.path.join(program_data_path, "settings.json")
    log_file = os.path.join(program_data_path, "staff_clock_system.log")
    logoPath = os.path.join(program_data_path, "Logo.png")
    databasePath = os.path.join(program_data_path, "staff_hours.db")

    # Ensure files exist or create defaults
    if not os.path.exists(settingsFilePath):
        default_settings = {"start_day": 21, "end_day": 20}
        with open(settingsFilePath, "w") as file:
            json.dump(default_settings, file)

    if not os.path.exists(log_file):
        open(log_file, "a").close()

    if not os.path.exists(logoPath):
        raise FileNotFoundError(f"Logo file not found at {logoPath}.")
    if not os.path.exists(databasePath):
        raise FileNotFoundError(f"Database file not found at {databasePath}.")

    configure_logging()

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
        self.setWindowTitle("Staff Digital Timesheet System")
        self.showMaximized()
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        logging.info("UI setup complete.")

        # Install event filter globally on the application
        QApplication.instance().installEventFilter(self)
        #self.standby_stage = 0  # 0: Not in standby, 1: Dimmed, 2: Fully Dimmed
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

        # Initialize Inactivity Timer
        #self.inactivity_timer = QTimer(self)
        #self.inactivity_timer.setInterval(5000)  # 5 minutes
        #self.inactivity_timer.timeout.connect(self.enter_standby_mode)
        #self.inactivity_timer.start()

        # Monitor user interactions
        #self.installEventFilter(self)

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

        # Check for timesheet generation
        #logging.info("Performing initial timesheet generation check...")
        #self.check_timesheet_generation()

    def handle_timesheet_generated(self, message):
        logging.info(message)
        self.generate_all_timesheets(self.settings["end_day"])
        #QMessageBox.information(self, "Timesheet Generated", message)

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
        default_settings = {"start_day": 21, "end_day": 20}

        if os.path.exists(settings_file):
            with open(settings_file, "r") as file:
                return json.load(file)
        else:
            with open(settings_file, "w") as file:
                json.dump(default_settings, file)
            return default_settings

    def save_settings(self):
        with open("settings.json", "w") as file:
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

        # Set Background Style
        self.setStyleSheet(
            "background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #2b2b2b, stop:1 #444); color: white;"
        )

    def clock_action(self, action, staff_code):
        conn = sqlite3.connect(databasePath)
        c = conn.cursor()

        # Check if the staff member exists
        c.execute('SELECT * FROM staff WHERE code = ?', (staff_code,))
        staff = c.fetchone()
        if not staff:
            conn.close()
            QMessageBox.critical(self, 'Error', 'Invalid staff code')
            return

        if action == 'in':
            clock_in_time = datetime.now().isoformat()
            c.execute('INSERT INTO clock_records (staff_code, clock_in_time) VALUES (?, ?)', (staff_code, clock_in_time))
            conn.commit()
            conn.close()
            time_in = datetime.fromisoformat(clock_in_time).strftime('%H:%M')
            QMessageBox.information(self, 'Success', f'Clock-in recorded successfully at {time_in}')
            logging.info(f"Clock-in successful for staff code {staff_code} at {time_in}")
            self.staff_code_entry.clear()
        elif action == 'out':
            clock_out_time = datetime.now().isoformat()
            c.execute('SELECT id FROM clock_records WHERE staff_code = ? AND clock_out_time IS NULL',
                      (staff_code,))
            clock_record = c.fetchone()
            if not clock_record:
                conn.close()
                QMessageBox.critical(self, 'Error', 'No clock-in record found')
                return
            c.execute('UPDATE clock_records SET clock_out_time = ? WHERE id = ?', (clock_out_time, clock_record[0]))
            conn.commit()
            conn.close()
            time_out = datetime.fromisoformat(clock_out_time).strftime('%H:%M')
            QMessageBox.information(self, 'Success', f'Clock-out recorded successfully at {time_out}')
            logging.info(f"Clock-out successful for staff code {staff_code} at {time_out}")
            self.staff_code_entry.clear()
        else:
            conn.close()
            QMessageBox.critical(self, 'Error', 'Invalid action')

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
        elif staff_code == '123456':  # Admin code
            self.greeting_label.setText("Admin Mode Activated")
            self.admin_button.show()
            self.admin_button.click()
        elif staff_code == '654321':  # Exit code
            self.greeting_label.setText("Exit Mode Activated")
            self.closeEvent()
            self.exit_button.show()
            self.exit_button.click()
        elif staff_code == '111111':
            self.greeting_label.setText("Fire!")
            self.fire()
        else:
            self.greeting_label.setText('')
            self.admin_button.hide()
            self.exit_button.hide()


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

    def open_settings_menu(self):
        settings_dialog = QDialog(self)
        settings_dialog.setWindowTitle("Settings")
        settings_dialog.setFixedSize(300, 200)

        layout = QVBoxLayout(settings_dialog)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        start_label = QLabel("Start Day:")
        self.start_day_input = QLineEdit(str(self.settings["start_day"]))
        layout.addWidget(start_label)
        layout.addWidget(self.start_day_input)

        end_label = QLabel("End Day:")
        self.end_day_input = QLineEdit(str(self.settings["end_day"]))
        layout.addWidget(end_label)
        layout.addWidget(self.end_day_input)

        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self.save_settings_from_menu)
        layout.addWidget(save_button)

        settings_dialog.exec()

    def save_settings_from_menu(self):
        try:
            start_day = int(self.start_day_input.text())
            end_day = int(self.end_day_input.text())

            if not (1 <= start_day <= 31 and 1 <= end_day <= 31):
                raise ValueError("Days must be between 1 and 31.")

            self.settings["start_day"] = start_day
            self.settings["end_day"] = end_day
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
        generate_timesheet_button.clicked.connect(lambda: self.generate_all_timesheets(20))
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

    def enter_standby_mode(self):
        """Enter standby mode in two stages."""
        if self.standby_stage == 0:
            logging.info("Entering first stage of standby mode...")
            self.standby_stage = 1

            # Dim screen slightly and add standby text
            self.standby_label = QLabel("Standby Mode\nMove your mouse or press a key to wake.", self.central_widget)
            self.standby_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
            self.standby_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.standby_label.setStyleSheet("background-color: rgba(0, 0, 0, 0.5); color: white;")
            self.standby_label.setGeometry(self.central_widget.rect())
            self.standby_label.show()
            return

        if self.standby_stage == 1:
            logging.info("Entering second stage of standby mode...")
            self.standby_stage = 2

            # Fully dim the screen
            self.standby_label.setStyleSheet("background-color: rgba(0, 0, 0, 0.8); color: white;")

    def exit_standby_mode(self):
        """Exit standby mode and restore normal operations."""
        if self.standby_stage == 0:
            logging.info("Not in standby mode. No action needed.")
            return

        logging.info("Exiting standby mode...")
        self.standby_stage = 0  # Reset standby stage

        # Remove standby overlay
        if hasattr(self, 'standby_label'):
            self.standby_label.deleteLater()
            del self.standby_label

        # Restart UI updates
        self.clock_timer.start()

        # Restore central widget visibility
        if hasattr(self, 'central_widget') and self.central_widget.isVisible():
            self.central_widget.show()

    def eventFilter(self, source, event):
        """Monitor interactions to exit standby mode."""
        if event.type() in {QEvent.Type.MouseMove, QEvent.Type.KeyPress}:
            logging.info(f"User interaction detected. Standby stage: {self.standby_stage}")

            # Exit standby mode directly
            if self.standby_stage > 0:
                self.exit_standby_mode()
                self.inactivity_timer.start()  # Reset inactivity timer
            return True  # Event handled

        return super().eventFilter(source, event)

    def delete_central_widget(self):
        logging.debug("Deleting central widget.")
        self.central_widget.deleteLater()
        self.central_widget = None

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
        parent_menu.close()  # Close the parent menu

        # Fetch clock records for the staff
        conn = sqlite3.connect(databasePath)
        c = conn.cursor()
        c.execute("SELECT id, clock_in_time, clock_out_time FROM clock_records WHERE staff_code = ?", (staff_code,))
        records = c.fetchall()
        conn.close()

        if not records:
            QMessageBox.information(self, "Info", "No clock records found for this staff member.")
            return

        # Open a dialog to list clock records and add a comment
        record_dialog = QDialog(self)
        record_dialog.setWindowTitle("Add Comment to Clock Record")
        record_dialog.setFixedSize(500, 400)
        layout = QVBoxLayout(record_dialog)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        record_label = QLabel("Select a Clock Record:")
        record_label.setFont(QFont("Arial", 16))
        layout.addWidget(record_label)

        # Create buttons for each record
        for record in records:
            record_id, clock_in, clock_out = record
            button_text = f"Clock In: {clock_in}, Clock Out: {clock_out or 'N/A'}"
            record_button = QPushButton(button_text)
            record_button.setFont(QFont("Arial", 12))
            record_button.clicked.connect(lambda _, rid=record_id: self.open_records_tab)
            layout.addWidget(record_button)

        record_dialog.exec()

    def open_records_tab(self):
        """Opens a dynamic tab to view clock records for a selected staff."""
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
        records_dialog.setMinimumWidth(600)

        layout = QVBoxLayout(records_dialog)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # Add a QTableWidget for displaying records
        table = QTableWidget(len(records), 4)
        table.setHorizontalHeaderLabels(["Clock In", "Clock Out", "Notes", "Edit"])
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Make non-editable by default

        # Populate the table with records
        for row, record in enumerate(records):
            clock_in_item = QTableWidgetItem(record[1] if record[1] else "N/A")
            clock_out_item = QTableWidgetItem(record[2] if record[2] else "N/A")
            notes_item = QTableWidgetItem(record[3] if record[3] else "N/A")

            table.setItem(row, 0, clock_in_item)
            table.setItem(row, 1, clock_out_item)
            table.setItem(row, 2, notes_item)

            # Add an "Edit" button to each row
            edit_button = QPushButton("Edit")
            edit_button.clicked.connect(lambda _, rid=record[0]: self.edit_clock_record(rid))
            table.setCellWidget(row, 3, edit_button)

        layout.addWidget(table)

        # Adjust dialog height dynamically
        rows_height = table.verticalHeader().length()
        records_dialog.setFixedHeight(200 + rows_height)

        close_button = QPushButton("Close")
        close_button.clicked.connect(records_dialog.close)
        layout.addWidget(close_button)

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

    def save_clock_record_comment(self, record_id, comment, dialog):
        if not comment.strip():
            QMessageBox.warning(self, "Warning", "Comment cannot be empty.")
            return

        try:
            conn = sqlite3.connect(databasePath)
            c = conn.cursor()
            c.execute("UPDATE clock_records SET notes = ? WHERE id = ?", (comment, record_id))
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Success", "Comment added to clock record.")
            logging.info(f"Added comment to clock record {record_id}: {comment}")
            dialog.close()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Error", f"Database error: {e}")
            logging.error(f"Database error: {e}")


    def toggle_window_mode(self):
        if not self.isWindowed:
            # Switch to windowed mode
            self.showNormal()
            self.setFixedSize(800, 600)
            self.setWindowFlags(Qt.WindowType.Window)
            self.show()
            self.windowed_button.setText("Enter Fullscreen Mode")
            logging.info("Switched to windowed mode.")
        else:
            # Switch to fullscreen mode
            self.showMaximized()
            self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
            self.windowed_button.setText("Enter Windowed Mode")
            logging.info("Switched to fullscreen mode.")

        # Toggle the state
        self.isWindowed = not self.isWindowed


    def add_staff(self):
        staff_name = self.name_entry.text().strip()
        max_retries = 1000
        retries = 0
        while retries < max_retries:
            if staff_name:
                staff_code = random.randint(1000, 9999)
                conn = sqlite3.connect(databasePath)
                c = conn.cursor()
                while c.execute('SELECT * FROM staff WHERE code = ?', (staff_code,)).fetchone():
                    staff_code = random.randint(1000, 9999)
                try:
                    c.execute('INSERT INTO staff (name, code) VALUES (?, ?)', (staff_name, staff_code))
                    conn.commit()
                    QMessageBox.information(self, 'Success', f'Staff member {staff_name} added with code {staff_code}')
                    logging.info(f'Staff member {staff_name} added with code {staff_code}')
                    break
                except sqlite3.Error as e:
                    QMessageBox.critical(self, 'Database Error', f'An error occurred: {e}')
                    logging.error(f'Database error occurred: {e}')
                finally:
                    conn.close()
        else:
            QMessageBox.warning(self, "Warning", "Could not add staff.")
            logging.info(f"Could not add staff.{staff_name}")


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

            # Insert staff details into archive_records
            for record in clock_records:
                c.execute(
                    'INSERT INTO archive_records (staff_name, staff_code, clock_in, clock_out, notes) VALUES (?, ?, ?, ?, ?)',
                    (staff_name, staff_code, *record))

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
            os.startfile(file_path)  # Windows-specific method
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


    def preparePrint(self):
        staff_name = self.name_entry.text().strip()
        if staff_name:
            file_path = f"Timesheets/{staff_name}_timesheet.pdf"
            self.print_via_jetdirect(file_path)
            logging.info(f'Prepared to print {staff_name}')

    def print_via_jetdirect(self, file_path):
        printer_ip = "10.60.1.146"
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