@echo off
setlocal

echo ===============================================
echo       StaffClock Application Uninstaller
echo ===============================================
echo.
echo WARNING: This will remove the StaffClock application and all its components.
echo Your data files (databases, timesheets, backups) will be preserved.
echo.

:: Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This uninstaller must be run as Administrator!
    echo Please right-click on this file and select "Run as administrator"
    pause
    exit /b 1
)

:: Confirm uninstallation
set /p CONFIRM="Are you sure you want to uninstall StaffClock? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo Uninstallation cancelled.
    pause
    exit /b 0
)

echo.
echo [1/5] Stopping any running StaffClock processes...

:: Kill any running Python processes that might be StaffClock
taskkill /f /im python.exe 2>nul

echo [2/5] Removing Python virtual environment...

if exist "venv" (
    echo Removing virtual environment...
    rmdir /s /q venv
    echo Virtual environment removed.
) else (
    echo No virtual environment found.
)

echo [3/5] Removing temporary directories...

:: Remove temporary directories but preserve data
for %%d in (TempData) do (
    if exist "%%d" (
        rmdir /s /q "%%d"
        echo Removed: %%d
    )
)

echo [4/5] Removing desktop shortcuts...

:: Remove desktop shortcut
set DESKTOP=%USERPROFILE%\Desktop
if exist "%DESKTOP%\StaffClock.lnk" (
    del "%DESKTOP%\StaffClock.lnk"
    echo Removed desktop shortcut.
)

:: Remove start menu shortcuts if they exist
set STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs
if exist "%STARTMENU%\StaffClock.lnk" (
    del "%STARTMENU%\StaffClock.lnk"
    echo Removed start menu shortcut.
)

echo [5/5] Cleaning up installer files...

:: Remove installer downloaded files
if exist "python-3.11.9-amd64.exe" (
    del "python-3.11.9-amd64.exe"
    echo Removed Python installer.
)

echo.
echo ===============================================
echo      StaffClock Application Components Removed
echo ===============================================
echo.
echo What was removed:
echo - Python virtual environment (venv folder)
echo - Temporary data directories
echo - Desktop and start menu shortcuts
echo - Downloaded installer files
echo.
echo What was preserved:
echo - ProgramData folder (settings, databases, logs)
echo - Backups folder (your backup files)
echo - Timesheets folder (generated PDFs)
echo - biometric_samples folder
echo - QR_Codes folder
echo - Main application files (main.py, etc.)
echo.
echo Note: Digital Persona SDK was NOT removed as it may be used by other applications.
echo If you want to completely remove it, go to Control Panel ^> Programs and Features
echo and uninstall "DigitalPersona One Touch for Windows SDK".
echo.
echo Note: Python was NOT removed as it may be used by other applications.
echo If you want to remove Python, go to Control Panel ^> Programs and Features.
echo.

:: Ask if user wants to remove data files too
echo.
set /p REMOVE_DATA="Do you also want to remove all data files (databases, backups, etc.)? (Y/N): "
if /i "%REMOVE_DATA%"=="Y" (
    echo.
    echo WARNING: This will permanently delete all your StaffClock data!
    set /p FINAL_CONFIRM="Are you absolutely sure? This cannot be undone! (Y/N): "
    if /i "!FINAL_CONFIRM!"=="Y" (
        echo Removing all data files...
        
        for %%d in (ProgramData Backups Timesheets biometric_samples QR_Codes) do (
            if exist "%%d" (
                rmdir /s /q "%%d"
                echo Removed: %%d
            )
        )
        
        :: Remove database files in root
        if exist "staff_timesheet.db" del "staff_timesheet.db"
        if exist "biometric_profiles.db" del "biometric_profiles.db"
        if exist "biometric_profiles.db-x-biometric_profiles-5-minutiae_data.bin" del "biometric_profiles.db-x-biometric_profiles-5-minutiae_data.bin"
        
        echo.
        echo All StaffClock data has been permanently removed.
    ) else (
        echo Data files preserved.
    )
) else (
    echo Data files preserved.
)

echo.
echo Uninstallation completed.
echo.
echo If you want to reinstall StaffClock later, simply run the installer again.
echo Your preserved data files will be automatically detected and used.
echo.
pause 