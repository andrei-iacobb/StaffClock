import os
import logging
import json
from typing import Dict

class PathManager:
    def __init__(self):
        self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.temp_path = ""
        self.permanent_path = ""
        self.database_path = ""
        self.settings_file_path = ""
        self.log_file = ""
        self.logo_path = ""
        self.qr_code_folder_path = ""
        self.initialize_paths()

    def initialize_paths(self):
        """Initialize all required paths and create directories if needed."""
        program_data_path = os.path.join(self.base_path, "ProgramData")
        self.temp_path = os.path.join(self.base_path, "TempData")
        self.permanent_path = os.path.join(self.base_path, "Timesheets")
        self.qr_code_folder_path = os.path.join(self.base_path, "QR_Codes")
        backup_folder = os.path.join(self.base_path, "Backups")

        # Create required directories
        for folder in [program_data_path, self.temp_path, self.permanent_path, backup_folder, self.qr_code_folder_path]:
            os.makedirs(folder, exist_ok=True)

        # Set file paths
        self.settings_file_path = os.path.join(program_data_path, "settings.json")
        self.log_file = os.path.join(program_data_path, "staff_clock_system.log")
        self.logo_path = os.path.join(program_data_path, "Logo.png")
        self.database_path = os.path.join(program_data_path, "staff_hours.db")

    def get_paths(self) -> Dict[str, str]:
        """Return all paths as a dictionary."""
        return {
            "temp_path": self.temp_path,
            "permanent_path": self.permanent_path,
            "database_path": self.database_path,
            "settings_file_path": self.settings_file_path,
            "log_file": self.log_file,
            "logo_path": self.logo_path,
            "qr_code_folder_path": self.qr_code_folder_path
        }

    def check_and_restore_folder(self, folder_path: str, backup_folder: str):
        """Check if a folder exists and restore from backup if needed."""
        if os.path.exists(folder_path):
            logging.info(f"Folder found: {folder_path}")
            return

        # Look for backups
        backup_files = [f for f in os.listdir(backup_folder) if f.endswith('.zip')]
        if not backup_files:
            os.makedirs(folder_path, exist_ok=True)
            logging.warning(f"No backup found for folder '{folder_path}'. Creating new folder.")
            return

        # Restore from most recent backup
        # Implementation of restore logic here...
        pass

    def check_and_restore_file(self, file_path: str, backup_folder: str, generate_default=None):
        """Check if a file exists and restore from backup if needed."""
        if os.path.exists(file_path):
            logging.info(f"File found: {file_path}")
            return

        # Look for backups
        backup_files = [f for f in os.listdir(backup_folder) if f.endswith('.zip')]
        if not backup_files and generate_default:
            logging.warning(f"No backup found for {file_path}. Generating default.")
            generate_default(file_path)
            return

        # Handle logo file specially
        if file_path == self.logo_path and not backup_files:
            raise FileNotFoundError(f"Logo file missing and no backups available in {backup_folder}.")

        # Restore from backup logic here...
        pass 