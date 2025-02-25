import os
import shutil
import zipfile
import logging
from datetime import datetime, timedelta
from PyQt6.QtCore import QThread, pyqtSignal

class EnhancedBackupSystem(QThread):
    backup_complete = pyqtSignal(str)

    def __init__(self, paths_config):
        super().__init__()
        self.paths = paths_config
        self.running = True
        
        # Get OS-specific backup locations
        self.backup_locations = self._get_backup_locations()
        self._create_backup_directories()

    def _get_backup_locations(self):
        base_backup = os.path.join(os.path.dirname(self.paths['database']), "Backups")
        
        # Windows-specific AppData location
        if os.name == 'nt':  # Windows
            appdata_backup = os.path.join(os.environ['APPDATA'], "TimesheetBackups")
            return [base_backup, appdata_backup]
        else:  # Linux/Mac
            home_backup = os.path.join(os.path.expanduser('~'), ".timesheet_backups")
            return [base_backup, home_backup]

    def _create_backup_directories(self):
        for backup_location in self.backup_locations:
            os.makedirs(backup_location, exist_ok=True)

    def run(self):
        while self.running:
            current_time = datetime.now()
            # Backup at 8:30 AM and 4:30 PM
            if current_time.strftime("%H:%M") in ["08:30", "16:30"]:
                self.perform_backup()
                self.sleep(60)  # Sleep for a minute to avoid multiple backups
            self.sleep(30)  # Check every 30 seconds

    def perform_backup(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_successful = False

        for backup_location in self.backup_locations:
            try:
                backup_path = os.path.join(backup_location, f"backup_{timestamp}.zip")
                temp_backup_path = f"{backup_path}.tmp"

                with zipfile.ZipFile(temp_backup_path, 'w', zipfile.ZIP_DEFLATED) as backup_zip:
                    # Add core files with verification
                    for file_key in ['database', 'logs', 'settings', 'logo']:
                        file_path = self.paths.get(file_key)
                        if file_path and os.path.exists(file_path):
                            backup_zip.write(file_path, os.path.basename(file_path))
                            if os.path.basename(file_path) not in backup_zip.namelist():
                                raise Exception(f"File verification failed: {file_path}")

                    # Add folders
                    for folder in ["ProgramData", "QR_Codes", "Timesheets"]:
                        folder_path = os.path.join(os.path.dirname(self.paths['database']), folder)
                        if os.path.exists(folder_path):
                            for root, _, files in os.walk(folder_path):
                                for file in files:
                                    full_path = os.path.join(root, file)
                                    rel_path = os.path.relpath(full_path, os.path.dirname(folder_path))
                                    backup_zip.write(full_path, rel_path)

                # Verify backup integrity
                with zipfile.ZipFile(temp_backup_path, 'r') as verify_zip:
                    if verify_zip.testzip() is not None:
                        raise Exception("Backup integrity check failed")

                # Only rename if verification passed
                os.rename(temp_backup_path, backup_path)
                backup_successful = True
                
                # Clean up old backups (keep last 7 days)
                self._cleanup_old_backups(backup_location)
                
                msg = f"Backup successful at {backup_path}"
                logging.info(msg)
                self.backup_complete.emit(msg)

            except Exception as e:
                logging.error(f"Backup failed at {backup_location}: {str(e)}")
                if os.path.exists(temp_backup_path):
                    os.remove(temp_backup_path)

        return backup_successful

    def _cleanup_old_backups(self, backup_location):
        try:
            # Keep backups from the last 7 days
            cutoff_date = datetime.now() - timedelta(days=7)
            
            for filename in os.listdir(backup_location):
                if filename.startswith("backup_") and filename.endswith(".zip"):
                    file_path = os.path.join(backup_location, filename)
                    file_date = datetime.strptime(filename[7:15], '%Y%m%d')
                    
                    if file_date < cutoff_date:
                        os.remove(file_path)
                        logging.info(f"Removed old backup: {file_path}")
        
        except Exception as e:
            logging.error(f"Error cleaning up old backups: {str(e)}")

    def stop(self):
        self.running = False 