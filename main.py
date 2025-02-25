import sys
from PyQt6.QtWidgets import QApplication
from path_manager import PathManager
from database_manager import DatabaseManager
from timesheet_generator import TimesheetGenerator
from staff_system import StaffClockInOutSystem

def main():
    path_manager = PathManager()
    backup_folder = path_manager.initialize_paths()
    
    database_manager = DatabaseManager(path_manager.database_path)
    timesheet_generator = TimesheetGenerator(path_manager.permanent_path)
    
    app = QApplication(sys.argv)
    window = StaffClockInOutSystem(path_manager, database_manager, timesheet_generator)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
