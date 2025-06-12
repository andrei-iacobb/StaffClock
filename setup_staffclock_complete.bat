@echo off
setlocal EnableDelayedExpansion

echo ===============================================
echo    StaffClock Complete Setup & Installer
echo ===============================================
echo.
echo This installer will set up everything needed to run StaffClock:
echo - Python 3.11 (if not installed)
echo - Digital Persona SDK
echo - Python virtual environment
echo - All required dependencies
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

:: Check Windows version
for /f "tokens=4-5 delims=. " %%i in ('ver') do set VERSION=%%i.%%j
echo Windows version: %VERSION%

:: Check if Python is installed and get version
set PYTHON_INSTALLED=0
python --version >nul 2>&1
if %errorLevel% equ 0 (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo Found Python %PYTHON_VERSION%
    
    :: Check if it's a suitable version (3.8+)
    for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
        set MAJOR=%%a
        set MINOR=%%b
    )
    if !MAJOR! GEQ 3 if !MINOR! GEQ 8 (
        set PYTHON_INSTALLED=1
        echo Python version is suitable.
    ) else (
        echo Python version is too old. Need 3.8 or later.
    )
) else (
    echo Python not found in PATH.
)

:: Install Python if needed
if %PYTHON_INSTALLED% equ 0 (
    echo [2/8] Installing Python 3.11...
    
    :: Check if installer exists
    if not exist "python-3.11.9-amd64.exe" (
        echo Downloading Python 3.11.9...
        echo This may take a few minutes depending on your internet connection...
        
        :: Try to download Python using PowerShell
        powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile 'python-3.11.9-amd64.exe'}"
        
        if not exist "python-3.11.9-amd64.exe" (
            echo ERROR: Failed to download Python installer.
            echo Please download Python 3.11 manually from https://python.org
            echo and place python-3.11.9-amd64.exe in this directory, then run this script again.
            pause
            exit /b 1
        )
    )
    
    echo Installing Python 3.11.9 (this may take a few minutes)...
    python-3.11.9-amd64.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    
    :: Wait for installation to complete
    echo Waiting for Python installation to complete...
    timeout /t 60 /nobreak >nul
    
    :: Refresh PATH
    set PATH=%PATH%;C:\Program Files\Python311;C:\Program Files\Python311\Scripts
    
    :: Verify installation
    python --version >nul 2>&1
    if %errorLevel% neq 0 (
        echo ERROR: Python installation may have failed.
        echo Please restart your command prompt and try again.
        pause
        exit /b 1
    )
    
    echo Python installation completed successfully.
) else (
    echo [2/8] Python already installed, skipping...
)

echo [3/8] Installing Digital Persona SDK...

:: Check if Digital Persona SDK is already installed
if exist "%ProgramFiles%\DigitalPersona\One Touch for Windows SDK\bin" (
    echo Digital Persona SDK already installed, skipping...
) else (
    if exist "Digital-Persona-SDK-master\SDK\Setup.exe" (
        echo Installing Digital Persona SDK from local files...
        "Digital-Persona-SDK-master\SDK\Setup.exe" /S
        
        echo Waiting for SDK installation to complete...
        timeout /t 45 /nobreak >nul
        
        :: Wait for installation process to finish
        :wait_sdk_complete
        tasklist /FI "IMAGENAME eq Setup.exe" 2>NUL | find /I /N "Setup.exe">NUL
        if "%ERRORLEVEL%"=="0" (
            timeout /t 5 /nobreak >nul
            goto wait_sdk_complete
        )
        
        echo Digital Persona SDK installation completed.
    ) else if exist "DigitalPersona-SDK.zip" (
        echo Extracting Digital Persona SDK from zip file...
        powershell -Command "Expand-Archive -Path 'DigitalPersona-SDK.zip' -DestinationPath '.' -Force"
        
        if exist "Digital-Persona-SDK-master\SDK\Setup.exe" (
            echo Installing Digital Persona SDK...
            "Digital-Persona-SDK-master\SDK\Setup.exe" /S
            timeout /t 45 /nobreak >nul
        ) else (
            echo WARNING: Could not find SDK setup file after extraction.
        )
    ) else (
        echo WARNING: Digital Persona SDK files not found.
        echo Please ensure either:
        echo 1. Digital-Persona-SDK-master folder is present, or
        echo 2. DigitalPersona-SDK.zip file is present
        echo You may need to install the SDK manually later.
    )
)

echo [4/8] Creating virtual environment...

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

echo [5/8] Activating virtual environment...
call venv\Scripts\activate.bat

echo [6/8] Upgrading pip and installing wheel...
python -m pip install --upgrade pip wheel setuptools

echo [7/8] Installing Python dependencies...
echo This may take several minutes, please be patient...

:: Install dependencies with error handling
pip install -r requirements.txt
if %errorLevel% neq 0 (
    echo.
    echo Some dependencies may have failed to install.
    echo Attempting to install critical packages individually...
    
    :: Install critical packages one by one
    echo Installing PyQt6...
    pip install PyQt6 PyQt6-Qt6 PyQt6-sip
    
    echo Installing computer vision packages...
    pip install opencv-python pillow numpy
    
    echo Installing scientific computing packages...
    pip install scikit-learn scipy matplotlib seaborn
    
    echo Installing additional utilities...
    pip install reportlab pyusb keyboard pyglet python-dateutil psutil requests
    
    echo Installing development tools...
    pip install pytest black
    
    :: Windows-specific packages
    echo Installing Windows-specific packages...
    pip install pywin32 wmi
)

echo [8/8] Setting up application directories and files...

:: Create required directories
for %%d in (ProgramData TempData Timesheets Backups biometric_samples QR_Codes) do (
    if not exist "%%d" (
        mkdir "%%d"
        echo Created directory: %%d
    )
)

:: Create desktop shortcut
echo Creating desktop shortcut...
set SCRIPT_DIR=%~dp0
set SHORTCUT_TARGET=%SCRIPT_DIR%run_staffclock.bat
set DESKTOP=%USERPROFILE%\Desktop

:: Create shortcut using PowerShell
powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%DESKTOP%\StaffClock.lnk');$s.TargetPath='%SHORTCUT_TARGET%';$s.WorkingDirectory='%SCRIPT_DIR%';$s.Description='StaffClock Biometric Time Management System';$s.Save()"

echo.
echo ===============================================
echo       Setup Completed Successfully!
echo ===============================================
echo.
echo Installation Summary:
echo - Python environment: Ready
echo - Digital Persona SDK: Installed
echo - Python dependencies: Installed  
echo - Application directories: Created
echo - Desktop shortcut: Created
echo.
echo Next steps:
echo 1. Connect your Digital Persona fingerprint reader
echo 2. Double-click the "StaffClock" shortcut on your desktop
echo    OR run "run_staffclock.bat" from this directory
echo 3. The application will initialize on first run
echo.
echo Troubleshooting:
echo - If fingerprint reader isn't detected, ensure drivers are installed
echo - Check Windows Device Manager for any device issues
echo - Restart your computer if you experience any issues
echo.
echo Press any key to exit...
pause 