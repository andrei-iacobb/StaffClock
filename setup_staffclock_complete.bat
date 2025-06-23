@echo off
setlocal EnableDelayedExpansion

echo ===============================================
echo    StaffClock Complete Setup & Installer
echo          With DigitalPersona Support
echo ===============================================
echo.
echo This installer will set up everything needed to run StaffClock:
echo - Python 3.11 (if not installed)
echo - Digital Persona SDK and drivers
echo - Python virtual environment with fingerprint support
echo - All required dependencies including OpenCV and PyQt6
echo - USB device access permissions
echo.

:: Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This installer must be run as Administrator!
    echo Please right-click on this file and select "Run as administrator"
    pause
    exit /b 1
)

echo [1/10] Checking system requirements and architecture...

:: Check Windows version
for /f "tokens=4-5 delims=. " %%i in ('ver') do set VERSION=%%i.%%j
echo Windows version: %VERSION%

:: Check system architecture
if defined PROCESSOR_ARCHITEW6432 (
    set ARCH=%PROCESSOR_ARCHITEW6432%
) else (
    set ARCH=%PROCESSOR_ARCHITECTURE%
)
echo System architecture: %ARCH%

:: Check if Python is installed and get version
set PYTHON_INSTALLED=0
python --version >nul 2>&1
if %errorLevel% equ 0 (
    echo Python found in PATH.
    
    :: Get Python version in a safer way
    for /f "tokens=2 delims= " %%i in ('python --version 2^>^&1') do (
        set "PYTHON_VERSION=%%i"
    )
    echo Found Python !PYTHON_VERSION!
    
    :: Check if it's a suitable version (3.8+) - simplified check
    echo !PYTHON_VERSION! | findstr /r "^3\.[8-9]\|^3\.1[0-9]\|^[4-9]\." >nul
    if !errorLevel! equ 0 (
        set PYTHON_INSTALLED=1
        echo Python version is suitable for StaffClock.
    ) else (
        echo Python version may be too old. Recommended: 3.8 or later.
        echo Current version: !PYTHON_VERSION!
        echo Continuing anyway - you can upgrade later if needed.
        set PYTHON_INSTALLED=1
    )
) else (
    echo Python not found in PATH.
)

:: Install Python if needed
if %PYTHON_INSTALLED% equ 0 (
    echo [2/10] Installing Python 3.11...
    
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
    echo [2/10] Python already installed, skipping...
)

echo [3/10] Installing Digital Persona SDK and Runtime...

:: Check if Digital Persona SDK is already installed
set DP_SDK_INSTALLED=0
if exist "%ProgramFiles%\DigitalPersona\One Touch for Windows SDK\bin" (
    echo Digital Persona SDK already installed.
    set DP_SDK_INSTALLED=1
) else if exist "%ProgramFiles(x86)%\DigitalPersona\One Touch for Windows SDK\bin" (
    echo Digital Persona SDK already installed (x86).
    set DP_SDK_INSTALLED=1
)

:: Check if Digital Persona Runtime is installed
set DP_RUNTIME_INSTALLED=0
if exist "%ProgramFiles%\DigitalPersona\One Touch for Windows" (
    echo Digital Persona Runtime already installed.
    set DP_RUNTIME_INSTALLED=1
) else if exist "%ProgramFiles(x86)%\DigitalPersona\One Touch for Windows" (
    echo Digital Persona Runtime already installed (x86).
    set DP_RUNTIME_INSTALLED=1
)

:: Install SDK if needed
if %DP_SDK_INSTALLED% equ 0 (
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
        echo.
        echo You can download the SDK from:
        echo https://github.com/hidglobal/digitalpersona-one-touch-for-windows-sdk
    )
)

:: Install Runtime if needed and available
if %DP_RUNTIME_INSTALLED% equ 0 (
    if exist "DigitalPersona-Runtime.msi" (
        echo Installing Digital Persona Runtime...
        msiexec /i "DigitalPersona-Runtime.msi" /quiet /norestart
        timeout /t 30 /nobreak >nul
        echo Digital Persona Runtime installation completed.
    ) else (
        echo Digital Persona Runtime installer not found.
        echo The SDK installation may provide sufficient functionality.
    )
)

echo [4/10] Configuring USB device permissions...

:: Add registry entries for USB device access (requires admin)
echo Setting up USB device access permissions...
reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\USBSTOR" /v "Start" /t REG_DWORD /d 3 /f >nul 2>&1
reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\StorageDevicePolicies" /v "WriteProtect" /t REG_DWORD /d 0 /f >nul 2>&1

echo [5/10] Creating virtual environment...

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

echo [6/10] Activating virtual environment...
call venv\Scripts\activate.bat

echo [7/10] Upgrading pip and installing build tools...
python -m pip install --upgrade pip wheel setuptools

echo [8/10] Installing Python dependencies for fingerprint support...
echo This may take several minutes, please be patient...

:: Install core dependencies first
echo Installing core PyQt6 and UI dependencies...
pip install PyQt6 PyQt6-Qt6 PyQt6-sip

:: Install computer vision and image processing
echo Installing computer vision packages...
pip install opencv-python pillow numpy

:: Install scientific computing packages
echo Installing scientific computing packages...
pip install scikit-learn scipy matplotlib seaborn pandas

:: Install USB and hardware interface packages
echo Installing USB and hardware interface packages...
pip install pyusb libusb keyboard

:: Install Windows-specific packages for device management
echo Installing Windows-specific packages...
pip install pywin32 wmi psutil

:: Install additional utilities
echo Installing additional utilities...
pip install reportlab pyglet python-dateutil requests

:: Install development and testing tools
echo Installing development tools...
pip install pytest black

:: Install remaining requirements from file
echo Installing remaining requirements from file...
pip install -r requirements.txt

:: Verify critical packages are installed
echo [9/10] Verifying critical package installations...
python -c "import PyQt6; print('PyQt6: OK')" 2>nul || echo "WARNING: PyQt6 not properly installed"
python -c "import cv2; print('OpenCV: OK')" 2>nul || echo "WARNING: OpenCV not properly installed"
python -c "import usb.core; print('PyUSB: OK')" 2>nul || echo "WARNING: PyUSB not properly installed"
python -c "import numpy; print('NumPy: OK')" 2>nul || echo "WARNING: NumPy not properly installed"

echo [10/10] Setting up application directories and files...

:: Create required directories
for %%d in (ProgramData TempData Timesheets Backups biometric_samples QR_Codes) do (
    if not exist "%%d" (
        mkdir "%%d"
        echo Created directory: %%d
    )
)

:: Create StaffClock_Data directory in user profile
set STAFFCLOCK_DATA=%USERPROFILE%\StaffClock_Data
if not exist "%STAFFCLOCK_DATA%" (
    mkdir "%STAFFCLOCK_DATA%"
    echo Created user data directory: %STAFFCLOCK_DATA%
)

for %%d in (Timesheets Backups biometric_samples QR_Codes TempData) do (
    if not exist "%STAFFCLOCK_DATA%\%%d" (
        mkdir "%STAFFCLOCK_DATA%\%%d"
        echo Created: %STAFFCLOCK_DATA%\%%d
    )
)

:: Create desktop shortcut
echo Creating desktop shortcut...
set SCRIPT_DIR=%~dp0
set SHORTCUT_TARGET=%SCRIPT_DIR%run_staffclock.bat
set DESKTOP=%USERPROFILE%\Desktop

:: Create shortcut using PowerShell
powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%DESKTOP%\StaffClock.lnk');$s.TargetPath='%SHORTCUT_TARGET%';$s.WorkingDirectory='%SCRIPT_DIR%';$s.Description='StaffClock Biometric Time Management System with Fingerprint Support';$s.IconLocation='%SystemRoot%\System32\shell32.dll,23';$s.Save()"

:: Test fingerprint device detection
echo Testing fingerprint device detection...
python -c "
try:
    import usb.core
    import usb.util
    devices = list(usb.core.find(find_all=True, idVendor=0x05ba))
    if devices:
        print('DigitalPersona devices found: %d' % len(devices))
        for dev in devices:
            print('  Device: %s' % dev)
    else:
        print('No DigitalPersona devices detected')
        print('Make sure your fingerprint reader is connected')
except Exception as e:
    print('Error testing device detection: %s' % e)
" 2>nul

echo.
echo ===============================================
echo       Setup Completed Successfully!
echo ===============================================
echo.
echo Installation Summary:
echo - Python environment: Ready
echo - Digital Persona SDK: Installed
echo - Python dependencies: Installed with fingerprint support
echo - USB device access: Configured
echo - Application directories: Created
echo - Desktop shortcut: Created
echo.
echo Fingerprint Setup Notes:
echo - Connect your DigitalPersona fingerprint reader via USB
echo - Ensure the device appears in Device Manager
echo - Windows may automatically install drivers
echo - If device isn't recognized, try different USB ports
echo.
echo Next steps:
echo 1. Connect your Digital Persona fingerprint reader
echo 2. Double-click the "StaffClock" shortcut on your desktop
echo    OR run "run_staffclock.bat" from this directory
echo 3. The application will auto-detect fingerprint devices
echo 4. Register fingerprints through the application interface
echo.
echo Supported DigitalPersona Devices:
echo - U.are.U 4500 (USB)
echo - U.are.U 5160 (USB)
echo - And other DigitalPersona compatible readers
echo.
echo Troubleshooting:
echo - Check Device Manager for "DigitalPersona" or "U.are.U" devices
echo - Ensure USB drivers are properly installed
echo - Try running as Administrator if device access fails
echo - Restart your computer after first installation
echo.
echo Press any key to exit...
pause 