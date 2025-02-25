import os
import shutil
import winshell
from win32com.client import Dispatch

def create_shortcut():
    desktop = winshell.desktop()
    path = os.path.join(desktop, "Timesheet System.lnk")
    
    target = os.path.join(os.path.dirname(os.path.abspath(__file__)), "launch_timesheet.bat")
    
    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(path)
    shortcut.Targetpath = target
    shortcut.WorkingDirectory = os.path.dirname(target)
    shortcut.save()

def setup():
    # Create data directory structure
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "TimesheetData")
    
    # Create directories
    for dir_name in ["ProgramData", "TempData", "Timesheets", "QR_Codes", "Backups"]:
        os.makedirs(os.path.join(data_dir, dir_name), exist_ok=True)
    
    # Create desktop shortcut
    create_shortcut()

if __name__ == "__main__":
    setup() 