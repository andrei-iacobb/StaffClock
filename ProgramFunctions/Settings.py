from PyQt6.QtWidgets import QDialog, QMessageBox, QVBoxLayout, QLabel, QLineEdit, QPushButton
import json
from datetime import datetime
import os

class Settings:
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


    def load_settings(self):
        settings_file = "ProgramData/settings.json"
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