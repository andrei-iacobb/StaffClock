import os
import logging
import json
import zipfile
from PyQt6.QtWidgets import QApplication

class PathManager:
    def __init__(self):
        self.temp_path = ""
        self.permanent_path = ""
        self.database_path = ""
        self.settings_file_path = ""
        self.log_file = ""
        self.logo_path = ""
        self.qr_code_folder_path = ""
        
    def initialize_paths(self):
        # Get base directory based on OS
        if os.name == 'nt':  # Windows
            base_path = os.path.dirname(os.path.abspath(__file__))
            data_root = os.path.join(os.path.dirname(base_path), "TimesheetData")
        else:  # macOS/Linux
            base_path = os.path.expanduser('~')
            data_root = os.path.join(base_path, "TimesheetData")
        
        # Define all data paths
        program_data_path = os.path.join(data_root, "ProgramData")
        self.temp_path = os.path.join(data_root, "TempData")
        self.permanent_path = os.path.join(data_root, "Timesheets")
        self.qr_code_folder_path = os.path.join(data_root, "QR_Codes")
        backup_folder = os.path.join(data_root, "Backups")

        # Create directories
        for folder in [program_data_path, self.temp_path, self.permanent_path, backup_folder, self.qr_code_folder_path]:
            os.makedirs(folder, exist_ok=True)

        # Set file paths
        self.settings_file_path = os.path.join(program_data_path, "settings.json")
        self.log_file = os.path.join(program_data_path, "staff_clock_system.log")
        self.logo_path = os.path.join(program_data_path, "Logo.png")
        self.database_path = os.path.join(program_data_path, "staff_hours.db")

        return backup_folder