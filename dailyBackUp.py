import logging

from PyQt6.QtCore import QThread, pyqtSignal
from datetime import datetime
import os
import zipfile

class DailyBackUp(QThread):
    daily_back_up = pyqtSignal(str)  # Signal to notify backup completion

    def __init__(self, backup_folder, database_path, log_file_path, settings_path, logo_path, parent=None):
        super().__init__(parent)
        self.backup_folder = backup_folder
        self.database_path = database_path
        self.log_file_path = log_file_path
        self.settings_path = settings_path
        self.logo_path = logo_path  # Add logo_path here
        self.running = True

        # Ensure the backup directory exists or create it
        self.create_backup_directory()

    def create_backup_directory(self):
        """Create the backup directory if it doesn't exist."""
        if not os.path.exists(self.backup_folder):
            os.makedirs(self.backup_folder)

    def run(self):
        while self.running:
            today = datetime.now()
            backup_time = today.strftime("%H:%M:%S")
            if backup_time == "11:05:40":  # Trigger backup at 12:59
                self.perform_backup()
                self.sleep(1)  # Avoid triggering multiple times during the same second
            elif backup_time == "9:30:00":
                self.perform_backup()
                self.sleep(1)
            else:
                self.sleep(1)

    def perform_backup(self):
        try:
            # Create a timestamped backup file
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            backup_path = os.path.join(self.backup_folder, backup_name)

            with zipfile.ZipFile(backup_path, 'w') as backup_zip:
                # Add database
                self.add_file_to_zip(backup_zip, self.database_path)

                # Add log file
                self.add_file_to_zip(backup_zip, self.log_file_path)

                # Add settings file
                self.add_file_to_zip(backup_zip, self.settings_path)

                # Add logo file
                self.add_file_to_zip(backup_zip, self.logo_path)

                # Add ProgramData folder
                self.add_folder_to_zip(backup_zip, "ProgramData")

                

                # Add Timesheets folder
                self.add_folder_to_zip(backup_zip, "Timesheets")

            self.daily_back_up.emit(f"Backup completed: {backup_path}")
            print(f"Backup completed: {backup_path}")
        except Exception as e:
            self.daily_back_up.emit(f"Backup failed: {str(e)}")
            print(f"Backup failed: {e}")

    def add_file_to_zip(self, backup_zip, file_path):
        """Helper method to add a file to the zip if it exists."""
        if os.path.exists(file_path):
            backup_zip.write(file_path, os.path.basename(file_path))

    def add_folder_to_zip(self, backup_zip, folder_name):
        """Helper method to add all contents of a folder to the zip."""
        folder_path = os.path.join(os.path.dirname(self.database_path), folder_name)
        if os.path.exists(folder_path):
            for root, _, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Preserve folder structure within the zip
                    arcname = os.path.relpath(file_path, os.path.dirname(self.database_path))
                    backup_zip.write(file_path, arcname)

    def stop(self):
        self.running = False
