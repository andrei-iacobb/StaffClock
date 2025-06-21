@echo off
setlocal

echo ===============================================
echo         Starting StaffClock Application
echo ===============================================
echo.

:: Check if virtual environment exists
if not exist "venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found!
    echo Please run "install_staffclock.bat" first to set up the application.
    pause
    exit /b 1
)

:: Check if main application file exists
if not exist "main.py" (
    echo ERROR: main.py not found!
    echo Please ensure you're running this from the StaffClock application directory.
    pause
    exit /b 1
)

echo Activating virtual environment...
call venv\\Scripts\\activate

echo Checking for Digital Persona fingerprint reader...
:: Brief pause to let user see the message
timeout /t 2 /nobreak >nul

echo Starting StaffClock Application...
echo.
echo ===============================================
echo  Application is starting - please wait...
echo ===============================================
echo.

:: Run the application
python staffclock\\main.py

:: Check if the application exited with an error
if %errorLevel% neq 0 (
    echo.
    echo ===============================================
    echo        Application exited with an error
    echo ===============================================
    echo.
    echo If you're experiencing issues:
    echo 1. Make sure your fingerprint reader is connected
    echo 2. Check that all dependencies were installed correctly
    echo 3. Verify the Digital Persona SDK is properly installed
    echo 4. Run the installer again if needed
    echo.
    pause
) else (
    echo.
    echo Application closed normally.
)

echo.
echo Press any key to exit...
pause >nul 