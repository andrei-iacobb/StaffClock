from PyQt6.QtCore import QThread, pyqtSignal
from datetime import datetime, timedelta
import os
import json

class TimesheetCheckerThread(QThread):
    timesheet_generated = pyqtSignal(str)

    def __init__(self, settings_file_path):
        super().__init__()
        self.settings_file_path = settings_file_path
        self.running = True

    def run(self):
        while self.running:
            today = datetime.now()
            settings = self.load_settings()

            # Check if today is within the settings range
            if settings["start_day"] <= today.day <= settings["end_day"]:
                self.timesheet_generated.emit(f"Timesheet generated for {today.strftime('%Y-%m-%d')}")

            # Sleep until the next day
            next_midnight = datetime.combine(today.date() + timedelta(days=1), datetime.min.time())
            seconds_until_midnight = (next_midnight - today).total_seconds()
            self.sleep(int(seconds_until_midnight))

    def load_settings(self):
        """Load settings from the settings.json file."""
        if os.path.exists(self.settings_file_path):
            with open(self.settings_file_path, "r") as file:
                return json.load(file)
        else:
            return {"start_day": 21, "end_day": 20}  # Default range if settings are missing

    #stop the method
    def stop(self):
        self.running = False