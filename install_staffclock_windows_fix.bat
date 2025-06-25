@echo off
setlocal EnableDelayedExpansion

echo ===============================================
echo       StaffClock Application Installer
echo         (Windows PyQt6 Fix Version)
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

echo [1/8] Checking system requirements...

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

echo [2/8] Installing Digital Persona SDK...

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

echo [3/8] Creating virtual environment...

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

echo [4/8] Activating virtual environment...
call venv\Scripts\activate.bat

echo [5/8] Upgrading pip and installing build tools...
python -m pip install --upgrade pip
python -m pip install --upgrade setuptools wheel

echo [6/8] Installing Python dependencies with PyQt6 fallback strategies...
echo This may take several minutes...

:: Try the Windows-specific requirements first
echo Attempting installation with Windows-specific requirements...
pip install -r requirements-windows.txt
if %errorLevel% equ 0 (
    echo SUCCESS: Dependencies installed with Windows-specific requirements
    goto :create_dirs
)

echo.
echo First attempt failed. Trying PyQt6 with pre-compiled wheels only...
pip install --only-binary=all PyQt6==6.5.3 PyQt6-Qt6==6.5.3 PyQt6-sip==13.6.0
if %errorLevel% equ 0 (
    echo SUCCESS: PyQt6 installed with pre-compiled wheels
    echo Installing remaining dependencies...
    pip install opencv-python pillow numpy scikit-learn scipy matplotlib seaborn pyusb keyboard pyglet python-dateutil psutil requests pytest black pywin32 wmi reportlab libusb pandas
    if %errorLevel% equ 0 (
        echo SUCCESS: All dependencies installed
        goto :create_dirs
    )
)

echo.
echo PyQt6 installation failed. Trying PySide6 as alternative...
pip install PySide6>=6.4.0
if %errorLevel% equ 0 (
    echo SUCCESS: PySide6 installed as PyQt6 alternative
    echo NOTE: You may need to update import statements in the code from PyQt6 to PySide6
    echo Installing remaining dependencies...
    pip install opencv-python pillow numpy scikit-learn scipy matplotlib seaborn pyusb keyboard pyglet python-dateutil psutil requests pytest black pywin32 wmi reportlab libusb pandas
    if %errorLevel% equ 0 (
        echo SUCCESS: All dependencies installed with PySide6
        goto :create_dirs
    )
)

echo.
echo ERROR: All PyQt6/PySide6 installation methods failed.
echo.
echo TROUBLESHOOTING SUGGESTIONS:
echo 1. Update Python to a newer version (3.9, 3.10, or 3.11)
echo 2. Install Microsoft Visual C++ 14.0 or greater
echo 3. Try installing Qt6 development tools manually
echo 4. Use a different Python distribution like Anaconda
echo.
echo For immediate resolution, you can:
echo 1. Install Anaconda Python from https://anaconda.org
echo 2. Use: conda install pyqt6
echo.
pause
exit /b 1

:create_dirs
echo [7/8] Creating additional required directories...
if not exist "ProgramData" mkdir ProgramData
if not exist "TempData" mkdir TempData
if not exist "Timesheets" mkdir Timesheets
if not exist "Backups" mkdir Backups
if not exist "biometric_samples" mkdir biometric_samples
if not exist "QR_Codes" mkdir QR_Codes

echo [8/8] Installation validation...
echo Testing PyQt6/PySide6 installation...
python -c "try: import PyQt6; print('PyQt6 import: SUCCESS')" 2>nul || (
    python -c "try: import PySide6; print('PySide6 import: SUCCESS')" 2>nul || (
        echo WARNING: Neither PyQt6 nor PySide6 could be imported
        echo The installation may not work correctly
    )
)

echo.
echo ===============================================
echo        Installation Completed!
echo ===============================================
echo.
echo Next steps:
echo 1. Connect your Digital Persona fingerprint reader
echo 2. Run "run_staffclock.bat" to start the application
echo 3. The application will create default database and settings on first run
echo.
echo Note: If you used PySide6 instead of PyQt6, you may need to update
echo the application code to use PySide6 imports instead of PyQt6.
echo.
echo If you encounter any fingerprint reader issues,
echo make sure the Digital Persona drivers are properly installed.
echo.
pause 