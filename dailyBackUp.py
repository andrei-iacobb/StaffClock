from PyQt6.QtCore import QThread, pyqtSignal
from datetime import datetime, timedelta
import os
import shutil
import zipfile

class DailyBackUp(QThread):
    daily_back_up = pyqtSignal(str)  # Signal to notify backup completion

    def __init__(self, backup_folder, database_path, log_file_path, settings_path, logo_path, parent=None):
        super().__init__(parent)
        self.backup_folder = backup_folder
        self.database_path = database_path
        self.log_file_path = log_file_path
        self.settings_path = settings_path
        self.logo_path = logo_path
        self.running = True

        # Ensure the backup directory exists or create it
        self.create_backup_directory()

    def create_backup_directory(self):
        """Create the backup directory if it doesn't exist."""
        try:
            if not os.path.exists(self.backup_folder):
                os.makedirs(self.backup_folder)
                print(f"Backup directory created: {self.backup_folder}")
            else:
                print(f"Backup directory already exists: {self.backup_folder}")
        except Exception as e:
            print(f"Failed to create backup directory: {e}")
            self.daily_back_up.emit(f"Failed to create backup directory: {e}")

    def run(self):
        while self.running:
            today = datetime.now()
            backup_time = today.strftime("%H:%M:%S")
            if backup_time == "13:45:30":  # Trigger backup at midnight
                self.perform_backup()
                self.sleep(1)  # Avoid triggering multiple times during the same second
            else:
                self.sleep(1)

    def perform_backup(self):
        try:
            # Create a timestamped backup file
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            backup_path = os.path.join(self.backup_folder, backup_name)

            with zipfile.ZipFile(backup_path, 'w') as backup_zip:
                # Add database
                backup_zip.write(self.database_path, os.path.basename(self.database_path))

                # Add log file
                if os.path.exists(self.log_file_path):
                    backup_zip.write(self.log_file_path, os.path.basename(self.log_file_path))

                # Add settings
                if os.path.exists(self.settings_path):
                    backup_zip.write(self.settings_path, os.path.basename(self.settings_path))

            self.daily_back_up.emit(f"Backup completed: {backup_path}")
            print(f"Backup completed: {backup_path}")  # Debugging output
        except Exception as e:
            self.daily_back_up.emit(f"Backup failed: {str(e)}")
            print(f"Backup failed: {e}")  # Debugging output

    def stop(self):
        self.running = False
