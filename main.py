from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QHBoxLayout, QDialog, QMessageBox, QTableWidget, QTableWidgetItem, QMainWindow
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import sqlite3
import datetime
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
        main_layout.setContentsMargins(50, 50, 50, 50)  # Add padding around the main layout
        self.central_widget.setLayout(main_layout)

        # Staff Code Label and Entry
        staff_code_layout = QHBoxLayout()
        staff_code_label = QLabel("Enter Staff Code:")
        staff_code_label.setFont(QFont("Arial", 18))  # Set larger font for readability
        self.staff_code_entry = QLineEdit()
        self.staff_code_entry.setFont(QFont("Arial", 16))  # Increase font size in input
        self.staff_code_entry.textChanged.connect(self.on_staff_code_change)

        staff_code_layout.addWidget(staff_code_label)
        staff_code_layout.addWidget(self.staff_code_entry)
        main_layout.addLayout(staff_code_layout)

        # Greeting Label
        self.greeting_label = QLabel("")
        self.greeting_label.setFont(QFont("Arial", 20))
        self.greeting_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.greeting_label)

        # Clock In/Out Buttons with custom size and style
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)  # Space between buttons

        self.clock_in_button = QPushButton("Clock In")
        self.clock_in_button.setFont(QFont("Arial", 18))
        self.clock_in_button.setMinimumSize(200, 60)
        self.clock_in_button.setStyleSheet("background-color: #4CAF50; color: white;")
        self.clock_in_button.clicked.connect(lambda: self.clock_action('in', self.staff_code_entry.text()))
        button_layout.addWidget(self.clock_in_button)

        self.clock_out_button = QPushButton("Clock Out")
        self.clock_out_button.setFont(QFont("Arial", 18))
        self.clock_out_button.setMinimumSize(200, 60)
        self.clock_out_button.setStyleSheet("background-color: #F44336; color: white;")
        self.clock_out_button.clicked.connect(lambda: self.clock_action('out', self.staff_code_entry.text()))
        button_layout.addWidget(self.clock_out_button)

        main_layout.addLayout(button_layout)

        # Admin and Exit Buttons with larger size
        self.admin_button = QPushButton("Admin")
        self.admin_button.setFont(QFont("Arial", 18))
        self.admin_button.setMinimumSize(200, 60)
        self.admin_button.setStyleSheet("background-color: #2196F3; color: white;")
        self.admin_button.clicked.connect(self.open_admin_tab)
        main_layout.addWidget(self.admin_button)

        self.exit_button = QPushButton("Exit")
        self.exit_button.setFont(QFont("Arial", 18))
        self.exit_button.setMinimumSize(200, 60)
        self.exit_button.setStyleSheet("background-color: #555555; color: white;")
        self.exit_button.clicked.connect(self.close)
        main_layout.addWidget(self.exit_button)


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

    def open_admin_tab(self):
        admin_tab = QDialog(self)
        admin_tab.setWindowTitle('Admin Page')
        admin_tab.setGeometry(100, 100, 500, 400)

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
        view_records_button.clicked.connect(self.show_record)
        layout.addWidget(view_records_button)

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
        else:
            QMessageBox.critical(self, 'Invalid Input', 'Please enter a valid staff name')

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

            record_dialog = QDialog(self)
            record_dialog.setWindowTitle("Staff Clock Records")
            record_dialog.setGeometry(100, 100, 800, 600)
            layout = QVBoxLayout(record_dialog)
            table = QTableWidget()
            table.setRowCount(len(records))
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(["Clock In Date", "Clock In Time", "Clock Out Date", "Clock Out Time"])

            for i, record in enumerate(records):
                clock_in = datetime.datetime.fromisoformat(record[0]) if record[0] else None
                clock_out = datetime.datetime.fromisoformat(record[1]) if record[1] else None
                table.setItem(i, 0, QTableWidgetItem(clock_in.strftime('%Y-%m-%d') if clock_in else ''))
                table.setItem(i, 1, QTableWidgetItem(clock_in.strftime('%H:%M:%S') if clock_in else ''))
                table.setItem(i, 2, QTableWidgetItem(clock_out.strftime('%Y-%m-%d') if clock_out else ''))
                table.setItem(i, 3, QTableWidgetItem(clock_out.strftime('%H:%M:%S') if clock_out else ''))

            layout.addWidget(table)
            record_dialog.exec()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = StaffClockInOutSystem()
    window.show()
    sys.exit(app.exec())
