import os
import sqlite3
import random
import socket
import sys
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QDialog, QMessageBox, QDialogButtonBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

class StaffClockInOutSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Staff Digital Timesheet System")
        self.showMaximized()
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setup_ui()
        self.showFullScreen()

    def setup_ui(self):
        # Setting up the central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Main layout
        main_layout = QVBoxLayout()
        self.central_widget.setLayout(main_layout)

        # Logo Layout (Top-right alignment)
        logo_layout = QHBoxLayout()
        logo_label = QLabel()
        pixmap = QPixmap("ProgramData/Logo.png")
        logo_label.setPixmap(pixmap)
        logo_label.setFixedSize(150, 80)
        logo_label.setScaledContents(True)
        logo_layout.addStretch()
        logo_layout.addWidget(logo_label)
        main_layout.addLayout(logo_layout)

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

        button_layout.addLayout(clock_buttons_layout)

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

        # Set Background Style
        self.setStyleSheet(
            "background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #2b2b2b, stop:1 #444); color: white;"
        )

    def clock_action(self, action, staff_code):
        conn = sqlite3.connect('staff_hours.db')
        c = conn.cursor()

        # Check if the staff member exists
        c.execute('SELECT * FROM staff WHERE code = ?', (staff_code,))
        staff = c.fetchone()
        if not staff:
            conn.close()
            QMessageBox.critical(self, 'Error', 'Invalid staff code')
            return

        if action == 'in':
            clock_in_time = datetime.datetime.now().isoformat()
            c.execute('INSERT   clock_records (staff_code, clock_in_time) VALUES (?, ?)',
                      (staff_code, clock_in_time))
            conn.commit()
            conn.close()
            time_in = datetime.datetime.fromisoformat(clock_in_time).strftime('%H:%M')
            QMessageBox.information(self, 'Success', f'Clock-in recorded successfully at {time_in}')
            self.staff_code_entry.clear()
        elif action == 'out':
            clock_out_time = datetime.datetime.now().isoformat()
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
            time_out = datetime.datetime.fromisoformat(clock_out_time).strftime('%H:%M')
            QMessageBox.information(self, 'Success', f'Clock-out recorded successfully at {time_out}')
            self.staff_code_entry.clear()
        else:
            conn.close()
            QMessageBox.critical(self, 'Error', 'Invalid action')

    def on_staff_code_change(self):
        staff_code = self.staff_code_entry.text()
        if len(staff_code) == 4 and staff_code.isdigit():
            conn = sqlite3.connect('staff_hours.db')
            c = conn.cursor()
            c.execute('SELECT name FROM staff WHERE code = ?', (staff_code,))
            staff = c.fetchone()
            conn.close()
            if staff:
                self.greeting_label.setText(f'Hello, {staff[0]}!')
        elif staff_code == '123456':  # Admin code
            self.greeting_label.setText("Admin Mode Activated")
            self.admin_button.show()
        elif staff_code == '654321':  # Exit code
            self.greeting_label.setText("Exit Mode Activated")
            self.exit_button.show()
        elif staff_code == '111111':
            self.greeting_label.setText("Fire!")
            self.fire
        else:
            self.greeting_label.setText('')
            self.admin_button.hide()
            self.exit_button.hide()


    def fire(self):
        time_now = datetime.datetime.now().strftime('%Y-%m-%d')  # Today's date
        print(f"Today's date: {time_now}")  # Debugging: print the date being queried

        conn = sqlite3.connect('staff_hours.db')
        c = conn.cursor()

        # Test query to debug
        c.execute('SELECT clock_in_time FROM clock_records')
        all_records = c.fetchall()
        print("All clock_in_time values in the database:")
        for record in all_records:
            print(record)

        # Now attempt the original query
        c.execute('SELECT staff_code, clock_in_time FROM clock_records WHERE DATE(clock_in_time) = ?', (time_now,))
        records = c.fetchall()

        if not records:
            print("No records found for today's date.")
        else:
            print("Records for today:")
            for record in records:
                print(f"Staff Code: {record[0]}, Clock In Time: {record[1]}")

        conn.close()

    def open_admin_tab(self):
        admin_tab = QDialog(self)
        admin_tab.setWindowTitle('Admin Page')
        admin_tab.setFixedSize(500, 400)
        layout = QVBoxLayout(admin_tab)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        name_label = QLabel("Enter Name:")
        name_label.setFont(QFont("Arial", 16))
        self.name_entry = QLineEdit()
        self.name_entry.setFont(QFont("Arial", 16))
        layout.addWidget(name_label)
        layout.addWidget(self.name_entry)

        add_staff_button = QPushButton("Add Staff")
        add_staff_button.setFont(QFont("Arial", 16))
        add_staff_button.setMinimumSize(150, 50)
        add_staff_button.setStyleSheet("background-color: #4CAF50; color: white;")
        add_staff_button.clicked.connect(self.add_staff)
        layout.addWidget(add_staff_button)

        delete_staff_button = QPushButton("Delete Staff")
        delete_staff_button.setFont(QFont("Arial", 16))
        delete_staff_button.setMinimumSize(150, 50)
        delete_staff_button.setStyleSheet("background-color: #F44336; color: white;")
        delete_staff_button.clicked.connect(self.remove_staff)
        layout.addWidget(delete_staff_button)

        view_records_button = QPushButton("View Records")
        view_records_button.setFont(QFont("Arial", 16))
        view_records_button.setMinimumSize(150, 50)
        view_records_button.setStyleSheet("background-color: #2196F3; color: white;")
        view_records_button.clicked.connect(self.open_records_tab)
        layout.addWidget(view_records_button)

        print_records_button = QPushButton("Print Records")
        print_records_button.setFont(QFont("Arial", 16))
        print_records_button.setMinimumSize(150, 50)
        print_records_button.setStyleSheet("background-color: #967bb6; color: white;")
        print_records_button.clicked.connect(self.preparePrint)
        layout.addWidget(print_records_button)

        generate_timesheet_button = QPushButton("Generate Timesheet")
        generate_timesheet_button.setFont(QFont("Arial", 16))
        generate_timesheet_button.setMinimumSize(150, 50)
        generate_timesheet_button.setStyleSheet("background-color: #2196F3; color: white;")
        generate_timesheet_button.clicked.connect(lambda: self.generate_all_timesheets(20))
        layout.addWidget(generate_timesheet_button)

        admin_tab.exec()

    def add_staff(self):
        staff_name = self.name_entry.text().strip()
        if staff_name:
            staff_code = random.randint(1000, 9999)
            conn = sqlite3.connect('staff_hours.db')
            c = conn.cursor()
            while c.execute('SELECT * FROM staff WHERE code = ?', (staff_code,)).fetchone():
                staff_code = random.randint(1000, 9999)
            try:
                c.execute('INSERT INTO staff (name, code) VALUES (?, ?)', (staff_name, staff_code))
                conn.commit()
                QMessageBox.information(self, 'Success', f'Staff member {staff_name} added with code {staff_code}')
            except sqlite3.Error as e:
                QMessageBox.critical(self, 'Database Error', f'An error occurred: {e}')
            finally:
                conn.close()

    def remove_staff(self):
        staff_name = self.name_entry.text().strip()
        if staff_name:
            conn = sqlite3.connect('staff_hours.db')
            c = conn.cursor()
            if c.execute('SELECT * FROM staff WHERE name = ?', (staff_name,)).fetchone():
                c.execute('DELETE FROM staff WHERE name = ?', (staff_name,))
                conn.commit()
                QMessageBox.information(self, 'Success', f'Staff member {staff_name} deleted')
            conn.close()

    def open_records_tab(self):
        staff_name = self.name_entry.text().strip()
        if not staff_name:
            QMessageBox.critical(self, "Error", "Please enter a valid staff name.")
            return

        records = self.get_records(staff_name)
        if records:
            self.create_table_pdf(staff_name, records)
            self.show_pdf(staff_name)

    def get_records(self, staff_name):
        conn = sqlite3.connect('staff_hours.db')
        c = conn.cursor()
        c.execute('SELECT code FROM staff WHERE name = ?', (staff_name,))
        staff = c.fetchone()
        if not staff:
            conn.close()
            QMessageBox.critical(self, "Error", "Staff member not found")
            return None

        staff_code = staff[0]
        c.execute('SELECT clock_in_time, clock_out_time FROM clock_records WHERE staff_code = ?', (staff_code,))
        records = c.fetchall()
        conn.close()
        return records

    def create_table_pdf(self, staff_name, records):
        file_path = f"Timesheets/{staff_name}.pdf"
        table_data = [["Clock In Date", "Clock In Time", "Clock Out Date", "Clock Out Time"]]
        for record in records:
            clock_in = datetime.datetime.fromisoformat(record[0]) if record[0] else None
            clock_out = datetime.datetime.fromisoformat(record[1]) if record[1] else None
            table_data.append([
                clock_in.strftime('%d-%m-%Y') if clock_in else '',
                clock_in.strftime('%H:%M:%S') if clock_in else '',
                clock_out.strftime('%d-%m-%Y') if clock_out else '',
                clock_out.strftime('%H:%M:%S') if clock_out else '',
            ])

        pdf = SimpleDocTemplate(file_path, pagesize=letter)
        styles = getSampleStyleSheet()
        title_style = styles['Title']
        title_paragraph = Paragraph(f"Records for {staff_name}", title_style)
        spacer = Spacer(1, 20)
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        pdf.build([title_paragraph, spacer, table])

    def show_pdf(self, staff_name):
        file_path = f"Timesheets/{staff_name}_records.pdf"
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            QMessageBox.critical(self, "Error", "The file is empty or does not exist.")
            return

        document = QPdfDocument(self)
        if document.load(file_path) != QPdfDocument.Status.Ready:
            QMessageBox.critical(self, "Error", "Failed to load the PDF document.")
            return

        view_dialog = QDialog(self)
        view_dialog.setWindowTitle(f"{staff_name} - Records")
        view_dialog.setGeometry(100, 100, 600, 800)

        pdf_view = QPdfView(view_dialog)
        pdf_view.setPageMode(QPdfView.PageMode.MultiPage)
        pdf_view.setDocument(document)

        layout = QVBoxLayout(view_dialog)
        layout.addWidget(pdf_view)
        view_dialog.exec()

    def preparePrint(self):
        staff_name = self.name_entry.text().strip()
        if staff_name:
            file_path = f"Timesheets/{staff_name}_records.pdf"
            self.print_via_jetdirect(file_path)

    def print_via_jetdirect(self, file_path):
        printer_ip = "192.168.1.250"
        printer_port = 9100
        try:
            with open(file_path, "rb") as pdf_file:
                pdf_data = pdf_file.read()
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as printer_socket:
                printer_socket.connect((printer_ip, printer_port))
                printer_socket.sendall(pdf_data)
            print("PDF sent to printer successfully!")
        except Exception as e:
            print(f"Failed to print PDF: {e}")

    def get_date_range_for_timesheet(self, day_selected):
        today = datetime.now()
        if today.day < day_selected:
            end_date = today.replace(day=day_selected) - timedelta(days=30)
        else:
            end_date = today.replace(day=day_selected)

        start_date = end_date.replace(day=21) - timedelta(days=30)
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
        return records

    def generate_all_timesheets(self, day_selected):
        # Get date range
        start_date, end_date = self.get_date_range_for_timesheet(day_selected)

        # Fetch records
        conn = sqlite3.connect('staff_hours.db')
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

        QMessageBox.information(
            self,
            "Success",
            f"Timesheets generated for the period {start_date.strftime('%d-%m-%Y')} to {end_date.strftime('%d-%m-%Y')}"
        )

    def generate_timesheet(self, employee_name, role, start_date, end_date, records):
        # Create the PDF file path
        os.makedirs("Timesheets", exist_ok=True)
        output_file = f"Timesheets/{employee_name.replace(' ', '_')}_timesheet.pdf"

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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = StaffClockInOutSystem()
    window.show()
    sys.exit(app.exec())
