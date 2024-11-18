import os

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QHBoxLayout, QDialog, QMessageBox, QTableWidget, QTableWidgetItem, QMainWindow, QDialogButtonBox, QGridLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap, QIcon
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import sqlite3
import datetime
import socket
import random
import sys


class StaffClockInOutSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Staff Clock In/Out System")
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
        pixmap = QPixmap("Logo.png")
        logo_label.setPixmap(pixmap)
        logo_label.setFixedSize(150, 80)  # Adjusted size
        logo_label.setScaledContents(True)
        logo_layout.addStretch()
        logo_layout.addWidget(logo_label)
        main_layout.addLayout(logo_layout)

        # Spacer
        main_layout.addSpacing(30)

        # Staff Code Input Section
        staff_code_layout = QVBoxLayout()
        staff_code_label = QLabel("Enter Staff Code:")
        staff_code_label.setFont(QFont("Segoe UI", 38, QFont.Weight.Bold))
        staff_code_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.staff_code_entry = QLineEdit()
        self.staff_code_entry.setFont(QFont("Segoe UI", 26))
        self.staff_code_entry.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.staff_code_entry.setPlaceholderText("Enter your 4-digit code")
        self.staff_code_entry.setStyleSheet(
            "background-color: #444; color: white; border: 1px solid #555; padding: 8px; border-radius: 5px;"
        )
        self.staff_code_entry.textChanged.connect(self.on_staff_code_change)

        self.greeting_label = QLabel("")
        self.greeting_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
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

        # Define buttons as class attributes
        self.clock_in_button = QPushButton("Clock In")
        self.clock_in_button.setFont(QFont("Segoe UI", 18))
        self.clock_in_button.setMinimumSize(250, 60)
        self.clock_in_button.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 8px;")
        self.clock_in_button.clicked.connect(lambda: self.clock_action('in', self.staff_code_entry.text()))
        button_layout.addWidget(self.clock_in_button)

        self.clock_out_button = QPushButton("Clock Out")
        self.clock_out_button.setFont(QFont("Segoe UI", 18))
        self.clock_out_button.setMinimumSize(250, 60)
        self.clock_out_button.setStyleSheet("background-color: #F44336; color: white; border-radius: 8px;")
        self.clock_out_button.clicked.connect(lambda: self.clock_action('out', self.staff_code_entry.text()))
        button_layout.addWidget(self.clock_out_button)

        self.admin_button = QPushButton("Admin")
        self.admin_button.setFont(QFont("Segoe UI", 18))
        self.admin_button.setMinimumSize(250, 60)
        self.admin_button.setStyleSheet("background-color: #2196F3; color: white; border-radius: 8px;")
        self.admin_button.clicked.connect(self.open_admin_tab)
        button_layout.addWidget(self.admin_button)

        self.exit_button = QPushButton("Exit")
        self.exit_button.setFont(QFont("Segoe UI", 18))
        self.exit_button.setMinimumSize(250, 60)
        self.exit_button.setStyleSheet("background-color: #555555; color: white; border-radius: 8px;")
        self.exit_button.clicked.connect(self.close)
        button_layout.addWidget(self.exit_button)

        main_layout.addLayout(button_layout)

        # Set Background Style
        self.setStyleSheet(
            "background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #2b2b2b, stop:1 #444); color: white;")

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
            c.execute('INSERT INTO clock_records (staff_code, clock_in_time) VALUES (?, ?)',
                      (staff_code, clock_in_time))
            conn.commit()
            conn.close()
            time_in = datetime.datetime.fromisoformat(clock_in_time).strftime('%H:%M')
            QMessageBox.information(self, 'Success', f'Clock-in recorded successfully at {time_in}')
            self.staff_code_entry.clear()
        elif action == 'out':
            clock_out_time = datetime.datetime.now().isoformat()
            c.execute('SELECT id, clock_in_time FROM clock_records WHERE staff_code = ? AND clock_out_time IS NULL',
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
            QMessageBox.information(self, 'Success', f'Clock-out recorded successfully at {time_out}.\n'
                                                     f'Today you have worked {self.get_hours(staff_code)}')
            self.staff_code_entry.clear()

        else:
            conn.close()
            QMessageBox.critical(self, 'Error', 'Invalid action')

    def get_hours(self, staff_code):
        conn = sqlite3.connect('staff_hours.db')
        c = conn.cursor()
        c.execute('SELECT * FROM staff WHERE code = ?', (staff_code,))
        staff = c.fetchone()
        if not staff:
            conn.close()
            QMessageBox.critical(self, 'Error', 'Invalid staff code')
            return

        c.execute('SELECT clock_in_time, clock_out_time FROM clock_records WHERE staff_code = ?', (staff_code,))
        records = c.fetchall()
        total_hours = 0.0
        for record in records:
            if record[1]:
                clock_in = datetime.datetime.fromisoformat(record[0])
                clock_out = datetime.datetime.fromisoformat(record[1])
                total_hours += (clock_out - clock_in).total_seconds() / 3600

        conn.close()
        return f'{total_hours:.2f} hours'

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
        elif staff_code == '123456':
            self.greeting_label.setText("Admin")
            self.admin_button.show()
        elif staff_code == '654321':
            self.greeting_label.setText("Exit")
            self.exit_button.show()
        else:
            self.greeting_label.setText('')

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

    def open_admin_tab(self):
        admin_tab = QDialog(self)
        admin_tab.setWindowTitle('Admin Page')
        admin_tab.setFixedSize(500,400)

        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)

        layout = QVBoxLayout(admin_tab)
        layout.setSpacing(20)  # Space between widgets in the dialog
        layout.setContentsMargins(30, 30, 30, 30)  # Padding around the layout

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
        delete_staff_button.clicked.connect(self.delete_staff)
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

        admin_tab.exec()

    def add_staff(self):
        # Create a dialog
        dlg = QDialog(self)
        dlg.setWindowTitle('Add Staff Confirmation')

        # Create a layout
        layout = QVBoxLayout(dlg)

        # Add message to the layout
        message = QLabel("Are you sure you would like to add this user?")
        layout.addWidget(message)

        # Add dialog buttons (Yes and No)
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No)
        layout.addWidget(button_box)

        # Connect signals for Yes and No buttons
        button_box.accepted.connect(lambda: self.confirm_add_staff(dlg))  # Call confirm method
        button_box.rejected.connect(lambda: self.reject_add_staff(dlg), )  # Close the dialog

        dlg.setLayout(layout)
        dlg.exec()

    def confirm_add_staff(self, dlg):
        # Fetch staff name from the input field
        staff_name = self.name_entry.text().strip()
        if staff_name:
            # Generate a random unique staff code
            staff_code = random.randint(1000, 9999)
            conn = sqlite3.connect('staff_hours.db')
            c = conn.cursor()

            # Ensure unique staff code
            while c.execute('SELECT * FROM staff WHERE code = ?', (staff_code,)).fetchone():
                staff_code = random.randint(1000, 9999)

            try:
                # Add the new staff member to the database
                c.execute('INSERT INTO staff (name, code) VALUES (?, ?)', (staff_name, staff_code))
                conn.commit()
                QMessageBox.information(self, 'Success', f'Staff member {staff_name} added with code {staff_code}')
            except sqlite3.Error as e:
                QMessageBox.critical(self, 'Database Error', f'An error occurred: {e}')
            finally:
                conn.close()
            dlg.accept()  # Close the dialog after successful addition
        else:
            QMessageBox.critical(self, 'Invalid Input', 'Please enter a valid staff name')

    def reject_add_staff(self, dlg):
        QMessageBox.critical(self, 'Rejected entry', 'Staff was not added to the list')
        self.name_entry.clear()
        dlg.close()

    def delete_staff(self):
        staff_name = self.name_entry.text().strip()
        if staff_name:
            conn = sqlite3.connect('staff_hours.db')
            c = conn.cursor()
            if c.execute('SELECT * FROM staff WHERE name = ?', (staff_name,)).fetchone():
                c.execute('DELETE FROM staff WHERE name = ?', (staff_name,))
                conn.commit()
                QMessageBox.information(self, 'Success', f'Staff member {staff_name} deleted')
            conn.close()

    def show_record(self):
        staff_name = self.name_entry.text().strip()
        if staff_name:
            conn = sqlite3.connect('staff_hours.db')
            c = conn.cursor()
            c.execute('SELECT code FROM staff WHERE name = ?', (staff_name,))
            staff = c.fetchone()
            if not staff:
                conn.close()
                QMessageBox.critical(self, "Error", "Staff member not found")
                return
            staff_code = staff[0]

            c.execute('SELECT clock_in_time, clock_out_time FROM clock_records WHERE staff_code = ?', (staff_code,))
            records = c.fetchall()
            conn.close()
            self.createTable(records, staff_name)



    def createTable(self, records, staff_name):
            # Prepare data for the PDF table
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

            # Generate and print the PDF
            title = f"Records for {staff_name}"
            self.generate_pdf_table(f"{staff_name}_records.pdf", table_data, title)
            #QMessageBox.information(self, "Success", f"Records for {staff_name} have been saved as a PDF.")

    def open_records_tab(self, staff_name):
        self.show_record()
        # Create a dialog for viewing records
        view_records = QDialog(self)
        view_records.setWindowTitle('View Records')
        view_records.setGeometry(100, 100, 400, 500)
        # Load the PDF document
        file_path = os.path.join(os.path.dirname(__file__), f'/Users/andreiiacob/PycharmProjects/staffClock/{staff_name}_records.pdf')
        document = QPdfDocument(view_records)
        if not document.load(file_path):
            print(f"Failed to load PDF file: {file_path}")
            return

        # Create and set up the PDF viewer
        pdf_view = QPdfView(view_records)
        pdf_view.setPageMode(QPdfView.PageMode.MultiPage)
        pdf_view.setDocument(document)
        print(document)
        print(document.status())

        # Add the viewer to the dialog
        layout = QVBoxLayout(view_records)
        layout.addWidget(pdf_view)

        view_records.exec()

    def preparePrint(self):
        name = self.name_entry.text().strip()
        self.show_record()  # Generates the PDF
        pdfName = f"{name}_records.pdf"
        self.print_via_jetdirect(pdfName)

    def generate_pdf_table(self, file_path, table_data, title):
        """
        Generate a PDF with a title and a table.
        """
        try:
            # Create the PDF document
            pdf = SimpleDocTemplate(file_path, pagesize=letter)

            # Create a title
            styles = getSampleStyleSheet()
            title_style = styles['Title']
            title_paragraph = Paragraph(title, title_style)

            # Spacer between title and table
            spacer = Spacer(1, 20)

            # Create the table
            table = Table(table_data)

            # Add table styles
            style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ])
            table.setStyle(style)

            # Build the PDF
            pdf.build([title_paragraph, spacer, table])
            print(f"PDF saved at {file_path}")

            self.name_entry.clear()
            QMessageBox.information(self, 'Success', f'Sent to printer!')
        except Exception as e:
            self.name_entry.clear()
            print(f"Failed to generate PDF: {e}")




if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = StaffClockInOutSystem()
    window.show()
    sys.exit(app.exec())
