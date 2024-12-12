from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QLineEdit
)
from PyQt6.QtGui import QFont

class Admin_tab():
    def open_admin_tab(self):
        admin_tab = QDialog(self)
        admin_tab.setWindowTitle('Admin Page')
        admin_tab.setFixedSize(500, 500)
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

        settings_button = QPushButton("Settings")
        settings_button.setFont(QFont("Arial", 16))
        settings_button.setMinimumSize(150, 50)
        settings_button.setStyleSheet("background-color: #2196F3; color: white;")
        settings_button.clicked.connect(self.open_settings_menu)
        layout.addWidget(settings_button)

        admin_tab.exec()
