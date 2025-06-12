@echo off
setlocal EnableDelayedExpansion

echo ===============================================
echo       StaffClock Application Installer
echo ===============================================
echo.

:: Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This installer must be run as Administrator!
    echo Please right-click on this file and select "Run as administrator"
    pause
    exit /b 1
)

echo [1/7] Checking system requirements...

:: Check if Python is installed
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or later from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

:: Get Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Found Python %PYTHON_VERSION%

:: Check Python version (require 3.8+)
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set MAJOR=%%a
    set MINOR=%%b
)
if %MAJOR% LSS 3 (
    echo ERROR: Python 3.8 or later is required. Found Python %PYTHON_VERSION%
    pause
    exit /b 1
)
if %MAJOR% EQU 3 if %MINOR% LSS 8 (
    echo ERROR: Python 3.8 or later is required. Found Python %PYTHON_VERSION%
    pause
    exit /b 1
)

echo [2/7] Installing Digital Persona SDK...

:: Check if Digital Persona SDK is already installed
if exist "%ProgramFiles%\DigitalPersona\One Touch for Windows SDK\bin" (
    echo Digital Persona SDK already installed, skipping...
) else (
    if exist "Digital-Persona-SDK-master\SDK\Setup.exe" (
        echo Installing Digital Persona SDK from local files...
        "Digital-Persona-SDK-master\SDK\Setup.exe" /S
        timeout /t 30 /nobreak >nul
        
        :: Wait for installation to complete
        :wait_sdk
        tasklist /FI "IMAGENAME eq Setup.exe" 2>NUL | find /I /N "Setup.exe">NUL
        if "%ERRORLEVEL%"=="0" (
            timeout /t 2 /nobreak >nul
            goto wait_sdk
        )
        
        echo Digital Persona SDK installation completed.
    ) else (
        echo WARNING: Digital Persona SDK files not found in expected location.
        echo Please ensure the Digital-Persona-SDK-master folder is present.
        echo You may need to install the SDK manually later.
    )
)

echo [3/7] Creating virtual environment...

:: Remove existing venv if present
if exist "venv" (
    echo Removing existing virtual environment...
    rmdir /s /q venv
)

:: Create new virtual environment
echo Creating Python virtual environment...
python -m venv venv
if %errorLevel% neq 0 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

echo [4/7] Activating virtual environment...
call venv\Scripts\activate.bat

echo [5/7] Upgrading pip...
python -m pip install --upgrade pip

echo [6/7] Installing Python dependencies...
echo This may take several minutes...
pip install -r requirements.txt
if %errorLevel% neq 0 (
    echo ERROR: Failed to install some dependencies
    echo Please check the error messages above
    pause
    exit /b 1
)

echo [7/7] Creating additional required directories...
if not exist "ProgramData" mkdir ProgramData
if not exist "TempData" mkdir TempData
if not exist "Timesheets" mkdir Timesheets
if not exist "Backups" mkdir Backups
if not exist "biometric_samples" mkdir biometric_samples
if not exist "QR_Codes" mkdir QR_Codes

echo.
echo ===============================================
echo        Installation Completed Successfully!
echo ===============================================
echo.
echo Next steps:
echo 1. Connect your Digital Persona fingerprint reader
echo 2. Run "run_staffclock.bat" to start the application
echo 3. The application will create default database and settings on first run
echo.
echo Note: If you encounter any fingerprint reader issues,
echo make sure the Digital Persona drivers are properly installed.
echo.
pause 