from PyQt6.QtCore import QThread, pyqtSignal
from datetime import datetime

class TimesheetCheckerThread(QThread):
    timesheet_generated = pyqtSignal(str)

    def __init__(self, start_day, end_day, parent=None):
        super().__init__(parent)
        self.start_day = start_day
        self.end_day = end_day
        self.running = True

    def run(self):
        while self.running:
            today = datetime.now()
            if today.day == self.end_day:
                self.timesheet_generated.emit(f"Timesheet generated for {today.strftime('%Y-%m-%d')}")
                self.sleep(86400)
            else:
                self.sleep(3600)

    def stop(self):
        self.running = False