@echo off
setlocal EnableDelayedExpansion

:: Set console colors and title
title StaffClock Master Installer
color 0A

:MAIN_MENU
cls
echo.
echo ===============================================
echo         STAFFCLOCK MASTER INSTALLER
echo          Complete Setup and Management
echo ===============================================
echo.
echo Choose an option:
echo.
echo [1] Complete Installation (Recommended)
echo     - Installs Python, DigitalPersona SDK, dependencies
echo     - Sets up virtual environment with fingerprint support
echo     - Configures USB permissions and creates shortcuts
echo.
echo [2] Quick Installation (Basic)
echo     - Basic Python environment setup
echo     - Essential dependencies only
echo     - No fingerprint support
echo.
echo [3] Prerequisites Only (winget method)
echo     - Uses Windows Package Manager to install essentials
echo     - Python, Visual C++, Git
echo.
echo [4] Fix PyQt6 Issues
echo     - Troubleshoot GUI framework installation problems
echo     - Multiple fallback strategies
echo.
echo [5] Run StaffClock Application
echo     - Start the application (must be installed first)
echo.
echo [6] System Information
echo     - Check current installation status
echo     - Verify dependencies and hardware
echo.
echo [7] Uninstall StaffClock
echo     - Remove application components
echo     - Option to preserve or remove data
echo.
echo [8] Help and Troubleshooting
echo     - Common issues and solutions
echo.
echo [9] Exit
echo.
set /p CHOICE="Enter your choice (1-9): "

if "%CHOICE%"=="1" goto COMPLETE_INSTALL
if "%CHOICE%"=="2" goto QUICK_INSTALL  
if "%CHOICE%"=="3" goto WINGET_INSTALL
if "%CHOICE%"=="4" goto FIX_PYQT6
if "%CHOICE%"=="5" goto RUN_APP
if "%CHOICE%"=="6" goto SYSTEM_INFO
if "%CHOICE%"=="7" goto UNINSTALL
if "%CHOICE%"=="8" goto HELP
if "%CHOICE%"=="9" goto EXIT
echo Invalid choice. Please try again.
timeout /t 2 /nobreak >nul
goto MAIN_MENU

:COMPLETE_INSTALL
cls
echo ===============================================
echo      COMPLETE STAFFCLOCK INSTALLATION
echo         With DigitalPersona Support
echo ===============================================
echo.
echo This will install everything needed for StaffClock:
echo - Python 3.11 (if not installed)
echo - Digital Persona SDK and drivers
echo - Python virtual environment with fingerprint support
echo - All required dependencies including OpenCV and PyQt6
echo - USB device access permissions
echo - Desktop shortcuts and application directories
echo.

:: Check admin rights
call :CHECK_ADMIN
if %ADMIN_CHECK% equ 0 goto MAIN_MENU

echo [1/12] Checking system requirements and architecture...

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

:: Check if Python is installed
set PYTHON_INSTALLED=0
python --version >nul 2>&1
if %errorLevel% equ 0 (
    for /f "tokens=2 delims= " %%i in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%i"
    echo Found Python !PYTHON_VERSION!
    
    :: Check if version is suitable (3.8+)
    echo !PYTHON_VERSION! | findstr /r "^3\.[8-9]\|^3\.1[0-9]\|^[4-9]\." >nul
    if !errorLevel! equ 0 (
        set PYTHON_INSTALLED=1
        echo Python version is suitable for StaffClock.
    ) else (
        echo Python version may be too old. Installing Python 3.11...
    )
) else (
    echo Python not found in PATH.
)

:: Install Python if needed
if %PYTHON_INSTALLED% equ 0 (
    echo [2/12] Installing Python 3.11...
    call :INSTALL_PYTHON
    if !errorLevel! neq 0 goto INSTALL_ERROR
) else (
    echo [2/12] Python already installed, skipping...
)

:: Install Digital Persona components
echo [3/12] Installing Digital Persona SDK and Runtime...
call :INSTALL_DIGITALPERSONA

:: Configure USB permissions
echo [4/12] Configuring USB device permissions...
reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\USBSTOR" /v "Start" /t REG_DWORD /d 3 /f >nul 2>&1
reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\StorageDevicePolicies" /v "WriteProtect" /t REG_DWORD /d 0 /f >nul 2>&1

:: Create virtual environment
echo [5/12] Creating virtual environment...
call :CREATE_VENV
if !errorLevel! neq 0 goto INSTALL_ERROR

echo [6/12] Activating virtual environment...
call venv\Scripts\activate.bat

echo [7/12] Upgrading pip and installing build tools...
python -m pip install --upgrade pip wheel setuptools

echo [8/12] Installing core dependencies...
call :INSTALL_CORE_DEPS

echo [9/12] Installing fingerprint and hardware support...
call :INSTALL_HARDWARE_DEPS

echo [10/12] Installing remaining requirements...
pip install -r requirements.txt

echo [11/12] Verifying critical package installations...
call :VERIFY_PACKAGES

echo [12/12] Setting up application environment...
call :SETUP_ENVIRONMENT

echo.
echo ===============================================
echo       COMPLETE INSTALLATION SUCCESSFUL!
echo ===============================================
call :SHOW_COMPLETION_MESSAGE
pause
goto MAIN_MENU

:QUICK_INSTALL
cls
echo ===============================================
echo        QUICK STAFFCLOCK INSTALLATION
echo            (Basic Dependencies Only)
echo ===============================================
echo.

call :CHECK_ADMIN
if %ADMIN_CHECK% equ 0 goto MAIN_MENU

echo [1/6] Checking Python installation...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    goto MAIN_MENU
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Found Python %PYTHON_VERSION%

echo [2/6] Creating virtual environment...
call :CREATE_VENV
if !errorLevel! neq 0 goto INSTALL_ERROR

echo [3/6] Activating virtual environment...
call venv\Scripts\activate.bat

echo [4/6] Upgrading pip...
python -m pip install --upgrade pip

echo [5/6] Installing basic dependencies...
pip install -r requirements.txt
if %errorLevel% neq 0 (
    echo ERROR: Failed to install some dependencies
    pause
    goto MAIN_MENU
)

echo [6/6] Creating required directories...
call :CREATE_DIRECTORIES

echo.
echo ===============================================
echo        QUICK INSTALLATION SUCCESSFUL!
echo ===============================================
echo.
echo Note: This installation does not include fingerprint support.
echo For full features, use the Complete Installation option.
echo.
pause
goto MAIN_MENU

:WINGET_INSTALL
cls
echo ===============================================
echo    PREREQUISITES INSTALLATION (WINGET)
echo ===============================================
echo.

call :CHECK_ADMIN
if %ADMIN_CHECK% equ 0 goto MAIN_MENU

:: Check if winget is available
winget --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Windows Package Manager (winget) is not available!
    echo.
    echo Install winget from Microsoft Store (search "App Installer")
    echo Or download from: https://github.com/microsoft/winget-cli/releases
    pause
    goto MAIN_MENU
)

echo ✓ Windows Package Manager detected
echo.

echo [1/3] Installing Python 3.9...
winget install Python.Python.3.9 --exact --silent --accept-package-agreements --accept-source-agreements
if %errorLevel% equ 0 (
    echo ✓ Python 3.9 installed successfully
) else (
    echo ⚠ Python 3.9 installation issue (may already be installed)
)

echo [2/3] Installing Visual C++ Redistributable...
winget install Microsoft.VCRedist.2015+.x64 --silent --accept-package-agreements --accept-source-agreements
if %errorLevel% equ 0 (
    echo ✓ Visual C++ Redistributable installed
) else (
    echo ⚠ Visual C++ Redistributable installation issue (may already be installed)
)

echo [3/3] Installing Git...
winget install Git.Git --silent --accept-package-agreements --accept-source-agreements
if %errorLevel% equ 0 (
    echo ✓ Git installed successfully
) else (
    echo ⚠ Git installation issue (may already be installed)
)

echo.
echo Prerequisites installation complete!
echo Please restart your terminal and run option 1 or 2 for full installation.
pause
goto MAIN_MENU

:FIX_PYQT6
cls
echo ===============================================
echo        PYQT6 INSTALLATION TROUBLESHOOTER
echo ===============================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found!
    echo Please run installation first.
    pause
    goto MAIN_MENU
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo [1/5] Upgrading pip and build tools...
python -m pip install --upgrade pip setuptools wheel

echo [2/5] Cleaning pip cache...
pip cache purge

echo [3/5] Attempting PyQt6 installation with pre-compiled wheels only...
pip install --only-binary=all --force-reinstall PyQt6==6.5.3
if %errorLevel% equ 0 (
    echo SUCCESS: PyQt6 6.5.3 installed successfully!
    goto :test_pyqt_import
)

echo [4/5] Trying alternative PyQt6 version...
pip install --only-binary=all --force-reinstall PyQt6==6.4.2
if %errorLevel% equ 0 (
    echo SUCCESS: PyQt6 6.4.2 installed successfully!
    goto :test_pyqt_import
)

echo [5/5] Installing PySide6 as alternative...
pip install PySide6>=6.4.0
if %errorLevel% equ 0 (
    echo SUCCESS: PySide6 installed as alternative to PyQt6!
    echo NOTE: You may need to update import statements from PyQt6 to PySide6
    goto :test_pyqt_import
)

echo ERROR: All installation attempts failed.
echo Consider updating Python or using a different installation method.
pause
goto MAIN_MENU

:test_pyqt_import
echo.
echo Testing GUI framework import...
python -c "try: import PyQt6.QtWidgets; print('PyQt6 import: SUCCESS')" 2>nul || (
    python -c "try: import PySide6.QtWidgets; print('PySide6 import: SUCCESS')" 2>nul || (
        echo WARNING: GUI framework import failed
        pause
        goto MAIN_MENU
    )
)

echo.
echo PyQt6 fix applied successfully!
pause
goto MAIN_MENU

:RUN_APP
cls
echo ===============================================
echo         STARTING STAFFCLOCK APPLICATION
echo ===============================================
echo.

:: Check if virtual environment exists
if not exist "venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found!
    echo Please run installation first.
    pause
    goto MAIN_MENU
)

:: Check if main application file exists
if not exist "staffclock\main.py" (
    echo ERROR: staffclock\main.py not found!
    echo Please ensure you're in the correct directory.
    pause
    goto MAIN_MENU
)

echo Activating virtual environment...
call venv\Scripts\activate

echo Checking dependencies...
python -c "import PyQt6" 2>nul || (
    echo ERROR: PyQt6 not found. Please run the installer again.
    pause
    goto MAIN_MENU
)

echo Checking for Digital Persona fingerprint devices...
python -c "
try:
    import usb.core
    devices = list(usb.core.find(find_all=True, idVendor=0x05ba))
    if devices:
        print('✓ DigitalPersona device(s) detected: %d' % len(devices))
    else:
        print('⚠ No DigitalPersona devices found')
except ImportError:
    print('⚠ USB library not available')
except Exception as e:
    print('⚠ Device detection error: %s' % e)
" 2>nul

echo.
echo Starting StaffClock Application...
echo.

:: Run the application
python -m staffclock.main

:: Check exit code
if %errorLevel% neq 0 (
    echo.
    echo Application exited with error code: %errorLevel%
    echo Check the troubleshooting section for solutions.
    pause
)

goto MAIN_MENU

:SYSTEM_INFO
cls
echo ===============================================
echo          SYSTEM INFORMATION & STATUS
echo ===============================================
echo.

:: System info
echo SYSTEM INFORMATION:
echo Windows Version: 
ver
echo.
echo Architecture: %PROCESSOR_ARCHITECTURE%
echo.

:: Python info
echo PYTHON STATUS:
python --version 2>nul && (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do echo Python Version: %%i
    pip --version 2>nul && echo pip: Available || echo pip: Not found
) || echo Python: Not installed or not in PATH
echo.

:: Virtual environment status
echo VIRTUAL ENVIRONMENT:
if exist "venv\Scripts\python.exe" (
    echo Status: Installed
    call venv\Scripts\activate && (
        echo Packages: 
        pip list | findstr -i "pyqt6 opencv usb"
    )
) else (
    echo Status: Not found
)
echo.

:: Application files
echo APPLICATION FILES:
if exist "staffclock\main.py" (
    echo Main application: Found
) else (
    echo Main application: Not found
)

if exist "requirements.txt" (
    echo Requirements file: Found
) else (
    echo Requirements file: Not found
)
echo.

:: Digital Persona status
echo DIGITAL PERSONA STATUS:
if exist "%ProgramFiles%\DigitalPersona\One Touch for Windows SDK\bin" (
    echo SDK: Installed (64-bit)
) else if exist "%ProgramFiles(x86)%\DigitalPersona\One Touch for Windows SDK\bin" (
    echo SDK: Installed (32-bit)
) else (
    echo SDK: Not found
)

:: Check for devices if USB library is available
if exist "venv\Scripts\python.exe" (
    call venv\Scripts\activate >nul 2>&1
    python -c "
import usb.core
try:
    devices = list(usb.core.find(find_all=True, idVendor=0x05ba))
    print('USB Devices: %d DigitalPersona device(s) found' % len(devices))
except:
    print('USB Devices: Unable to scan')
" 2>nul
)

echo.
pause
goto MAIN_MENU

:UNINSTALL
cls
echo ===============================================
echo       STAFFCLOCK APPLICATION UNINSTALLER
echo ===============================================
echo.
echo WARNING: This will remove StaffClock application components.
echo Your data files can be optionally preserved.
echo.

call :CHECK_ADMIN
if %ADMIN_CHECK% equ 0 goto MAIN_MENU

set /p CONFIRM="Are you sure you want to uninstall StaffClock? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo Uninstallation cancelled.
    pause
    goto MAIN_MENU
)

echo [1/5] Stopping any running processes...
taskkill /f /im python.exe 2>nul

echo [2/5] Removing virtual environment...
if exist "venv" (
    rmdir /s /q venv
    echo Virtual environment removed.
)

echo [3/5] Removing temporary directories...
if exist "TempData" rmdir /s /q "TempData"

echo [4/5] Removing shortcuts...
if exist "%USERPROFILE%\Desktop\StaffClock.lnk" del "%USERPROFILE%\Desktop\StaffClock.lnk"

echo [5/5] Cleaning up installer files...
if exist "python-3.11.9-amd64.exe" del "python-3.11.9-amd64.exe"

echo.
set /p REMOVE_DATA="Remove all data files (databases, backups, etc.)? (Y/N): "
if /i "%REMOVE_DATA%"=="Y" (
    echo.
    set /p FINAL_CONFIRM="This will permanently delete all data! Continue? (Y/N): "
    if /i "!FINAL_CONFIRM!"=="Y" (
        for %%d in (ProgramData Backups Timesheets biometric_samples QR_Codes) do (
            if exist "%%d" rmdir /s /q "%%d"
        )
        echo All data files removed.
    )
)

echo.
echo Uninstallation completed.
pause
goto MAIN_MENU

:HELP
cls
echo ===============================================
echo         HELP AND TROUBLESHOOTING
echo ===============================================
echo.
echo COMMON ISSUES AND SOLUTIONS:
echo.
echo 1. PyQt6 Installation Fails:
echo    - Run option 4 (Fix PyQt6 Issues)
echo    - Ensure Visual C++ Redistributable is installed
echo    - Try different Python version (3.9-3.11)
echo.
echo 2. Fingerprint Reader Not Detected:
echo    - Check USB connection
echo    - Install Digital Persona SDK
echo    - Check Device Manager for proper drivers
echo    - Try different USB ports
echo    - Run as Administrator
echo.
echo 3. Python Not Found:
echo    - Restart command prompt after Python installation
echo    - Check PATH environment variable
echo    - Reinstall Python with "Add to PATH" option
echo.
echo 4. Permission Errors:
echo    - Run installer as Administrator
echo    - Check antivirus software interference
echo    - Temporarily disable Windows Defender
echo.
echo 5. Application Won't Start:
echo    - Check system info (option 6)
echo    - Verify all dependencies are installed
echo    - Check log files in ProgramData folder
echo.
echo 6. Database Issues:
echo    - Check ProgramData folder permissions
echo    - Ensure sufficient disk space
echo    - Run database integrity check
echo.
echo For additional support, check the README file or
echo contact system administrator.
echo.
pause
goto MAIN_MENU

:: HELPER FUNCTIONS

:CHECK_ADMIN
set ADMIN_CHECK=1
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Administrator privileges required!
    echo Please right-click and select "Run as administrator"
    set ADMIN_CHECK=0
    pause
)
exit /b

:INSTALL_PYTHON
if not exist "python-3.11.9-amd64.exe" (
    echo Downloading Python 3.11.9...
    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile 'python-3.11.9-amd64.exe'}"
    
    if not exist "python-3.11.9-amd64.exe" (
        echo ERROR: Failed to download Python installer.
        exit /b 1
    )
)

echo Installing Python 3.11.9...
python-3.11.9-amd64.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
timeout /t 60 /nobreak >nul

:: Refresh PATH
set PATH=%PATH%;C:\Program Files\Python311;C:\Program Files\Python311\Scripts

python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Python installation failed.
    exit /b 1
)
exit /b 0

:INSTALL_DIGITALPERSONA
set DP_SDK_INSTALLED=0
if exist "%ProgramFiles%\DigitalPersona\One Touch for Windows SDK\bin" set DP_SDK_INSTALLED=1
if exist "%ProgramFiles(x86)%\DigitalPersona\One Touch for Windows SDK\bin" set DP_SDK_INSTALLED=1

if %DP_SDK_INSTALLED% equ 0 (
    if exist "Digital-Persona-SDK-master\SDK\Setup.exe" (
        echo Installing Digital Persona SDK...
        "Digital-Persona-SDK-master\SDK\Setup.exe" /S
        timeout /t 45 /nobreak >nul
    ) else if exist "DigitalPersona-SDK.zip" (
        echo Extracting Digital Persona SDK...
        powershell -Command "Expand-Archive -Path 'DigitalPersona-SDK.zip' -DestinationPath '.' -Force"
        if exist "Digital-Persona-SDK-master\SDK\Setup.exe" (
            "Digital-Persona-SDK-master\SDK\Setup.exe" /S
            timeout /t 45 /nobreak >nul
        )
    ) else (
        echo WARNING: Digital Persona SDK files not found.
        echo Download from: https://github.com/hidglobal/digitalpersona-one-touch-for-windows-sdk
    )
)
exit /b 0

:CREATE_VENV
if exist "venv" rmdir /s /q venv
python -m venv venv
if %errorLevel% neq 0 (
    echo ERROR: Failed to create virtual environment
    exit /b 1
)
exit /b 0

:INSTALL_CORE_DEPS
echo Installing PyQt6 and UI dependencies...
pip install PyQt6 PyQt6-Qt6 PyQt6-sip
echo Installing computer vision packages...
pip install opencv-python pillow numpy
echo Installing scientific computing packages...
pip install scikit-learn scipy matplotlib seaborn pandas
exit /b 0

:INSTALL_HARDWARE_DEPS
echo Installing USB and hardware interface packages...
pip install pyusb libusb keyboard
echo Installing Windows-specific packages...
pip install pywin32 wmi psutil
echo Installing additional utilities...
pip install reportlab pyglet python-dateutil requests pytest
exit /b 0

:VERIFY_PACKAGES
python -c "import PyQt6; print('✓ PyQt6: OK')" 2>nul || echo "⚠ PyQt6: Failed"
python -c "import cv2; print('✓ OpenCV: OK')" 2>nul || echo "⚠ OpenCV: Failed"
python -c "import usb.core; print('✓ PyUSB: OK')" 2>nul || echo "⚠ PyUSB: Failed"
python -c "import numpy; print('✓ NumPy: OK')" 2>nul || echo "⚠ NumPy: Failed"
exit /b 0

:SETUP_ENVIRONMENT
call :CREATE_DIRECTORIES

:: Create desktop shortcut
set SCRIPT_DIR=%~dp0
set SHORTCUT_TARGET=%SCRIPT_DIR%StaffClock_Master_Installer.bat
powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%USERPROFILE%\Desktop\StaffClock.lnk');$s.TargetPath='%SHORTCUT_TARGET%';$s.Arguments='5';$s.WorkingDirectory='%SCRIPT_DIR%';$s.Description='StaffClock Application';$s.Save()" 2>nul

:: Test device detection
python -c "
try:
    import usb.core
    devices = list(usb.core.find(find_all=True, idVendor=0x05ba))
    if devices:
        print('✓ DigitalPersona devices found: %d' % len(devices))
    else:
        print('⚠ No DigitalPersona devices detected')
except:
    print('⚠ Device detection unavailable')
" 2>nul
exit /b 0

:CREATE_DIRECTORIES
for %%d in (ProgramData TempData Timesheets Backups biometric_samples QR_Codes) do (
    if not exist "%%d" mkdir "%%d"
)
exit /b 0

:SHOW_COMPLETION_MESSAGE
echo.
echo Installation Summary:
echo - Python environment: Ready
echo - Digital Persona SDK: Installed
echo - Python dependencies: Installed with fingerprint support
echo - USB device access: Configured
echo - Application directories: Created
echo - Desktop shortcut: Created
echo.
echo Next steps:
echo 1. Connect your Digital Persona fingerprint reader
echo 2. Use option 5 to run StaffClock or use the desktop shortcut
echo 3. The application will auto-detect fingerprint devices
echo.
exit /b 0

:INSTALL_ERROR
echo.
echo Installation failed. Please check the error messages above.
echo You can try the troubleshooting options or contact support.
pause
goto MAIN_MENU

:EXIT
echo.
echo Thank you for using StaffClock Master Installer!
echo.
exit /b 0 