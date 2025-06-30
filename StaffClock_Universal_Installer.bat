@echo off
setlocal EnableDelayedExpansion

:: Set console colors and title
title StaffClock Universal Installer
color 0A

:MAIN_MENU
cls
echo.
echo ===============================================
echo        STAFFCLOCK UNIVERSAL INSTALLER
echo         Complete Setup and Management
echo ===============================================
echo.
echo Choose an option:
echo.
echo [1] Complete Installation (Recommended)
echo     - Python + DigitalPersona SDK + Full Dependencies
echo     - Fingerprint support and USB permissions
echo.
echo [2] Quick Installation (Basic)
echo     - Essential dependencies only
echo     - No fingerprint support
echo.
echo [3] Prerequisites via Windows Package Manager
echo     - Python, Visual C++, Git via winget
echo.
echo [4] Fix PyQt6 Installation Issues
echo     - Troubleshoot GUI framework problems
echo.
echo [5] Run StaffClock Application
echo     - Start the application
echo.
echo [6] System Information and Status
echo     - Check installation and hardware status
echo.
echo [7] Uninstall StaffClock
echo     - Remove application (preserve data option)
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
echo ===============================================

:: Check admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Administrator privileges required!
    echo Please right-click and select "Run as administrator"
    pause
    goto MAIN_MENU
)

echo [1/10] Checking system requirements...
for /f "tokens=4-5 delims=. " %%i in ('ver') do set VERSION=%%i.%%j
echo Windows version: %VERSION%

:: Check Python
set PYTHON_INSTALLED=0
python --version >nul 2>&1
if %errorLevel% equ 0 (
    for /f "tokens=2 delims= " %%i in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%i"
    echo Found Python !PYTHON_VERSION!
    echo !PYTHON_VERSION! | findstr /r "^3\.[8-9]\|^3\.1[0-9]\|^[4-9]\." >nul
    if !errorLevel! equ 0 set PYTHON_INSTALLED=1
)

:: Install Python if needed
if %PYTHON_INSTALLED% equ 0 (
    echo [2/10] Installing Python 3.11...
    if not exist "python-3.11.9-amd64.exe" (
        echo Downloading Python...
        powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile 'python-3.11.9-amd64.exe'}"
    )
    
    python-3.11.9-amd64.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    timeout /t 60 /nobreak >nul
    set PATH=%PATH%;C:\Program Files\Python311;C:\Program Files\Python311\Scripts
) else (
    echo [2/10] Python already installed...
)

echo [3/10] Installing Digital Persona SDK...
set DP_SDK_INSTALLED=0
if exist "%ProgramFiles%\DigitalPersona\One Touch for Windows SDK\bin" set DP_SDK_INSTALLED=1
if exist "%ProgramFiles(x86)%\DigitalPersona\One Touch for Windows SDK\bin" set DP_SDK_INSTALLED=1

if %DP_SDK_INSTALLED% equ 0 (
    if exist "Digital-Persona-SDK-master\SDK\Setup.exe" (
        "Digital-Persona-SDK-master\SDK\Setup.exe" /S
        timeout /t 45 /nobreak >nul
    ) else (
        echo WARNING: Digital Persona SDK files not found
        echo Download from: https://github.com/hidglobal/digitalpersona-one-touch-for-windows-sdk
    )
)

echo [4/10] Configuring USB permissions...
reg add "HKLM\SYSTEM\CurrentControlSet\Services\USBSTOR" /v "Start" /t REG_DWORD /d 3 /f >nul 2>&1

echo [5/10] Creating virtual environment...
if exist "venv" rmdir /s /q venv
python -m venv venv
call venv\Scripts\activate.bat

echo [6/10] Installing core dependencies...
python -m pip install --upgrade pip wheel setuptools
pip install PyQt6 PyQt6-Qt6 PyQt6-sip opencv-python pillow numpy

echo [7/10] Installing hardware support...
pip install pyusb libusb pywin32 wmi psutil

echo [8/10] Installing additional packages...
pip install scikit-learn scipy matplotlib reportlab python-dateutil requests

echo [9/10] Installing from requirements file...
if exist "requirements.txt" pip install -r requirements.txt

echo [10/10] Setting up directories and shortcuts...
for %%d in (ProgramData TempData Timesheets Backups biometric_samples QR_Codes) do (
    if not exist "%%d" mkdir "%%d"
)

set SCRIPT_DIR=%~dp0
powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%USERPROFILE%\Desktop\StaffClock.lnk');$s.TargetPath='%SCRIPT_DIR%StaffClock_Universal_Installer.bat';$s.Arguments='5';$s.WorkingDirectory='%SCRIPT_DIR%';$s.Description='StaffClock Application';$s.Save()" 2>nul

echo.
echo ===============================================
echo       INSTALLATION COMPLETED SUCCESSFULLY!
echo ===============================================
pause
goto MAIN_MENU

:QUICK_INSTALL
cls
echo ===============================================
echo        QUICK INSTALLATION (BASIC)
echo ===============================================

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Administrator privileges required!
    pause
    goto MAIN_MENU
)

python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Python not found! Please install Python first.
    pause
    goto MAIN_MENU
)

echo Creating virtual environment...
if exist "venv" rmdir /s /q venv
python -m venv venv
call venv\Scripts\activate.bat

echo Installing basic dependencies...
python -m pip install --upgrade pip
if exist "requirements.txt" (
    pip install -r requirements.txt
) else (
    pip install PyQt6 opencv-python pillow numpy reportlab
)

echo Creating directories...
for %%d in (ProgramData TempData Timesheets Backups) do (
    if not exist "%%d" mkdir "%%d"
)

echo Quick installation complete!
pause
goto MAIN_MENU

:WINGET_INSTALL
cls
echo ===============================================
echo     PREREQUISITES VIA WINDOWS PACKAGE MANAGER
echo ===============================================

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Administrator privileges required!
    pause
    goto MAIN_MENU
)

winget --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Windows Package Manager not available!
    echo Install from Microsoft Store (search "App Installer")
    pause
    goto MAIN_MENU
)

echo Installing Python 3.9...
winget install Python.Python.3.9 --exact --silent --accept-package-agreements --accept-source-agreements

echo Installing Visual C++ Redistributable...
winget install Microsoft.VCRedist.2015+.x64 --silent --accept-package-agreements --accept-source-agreements

echo Installing Git...
winget install Git.Git --silent --accept-package-agreements --accept-source-agreements

echo Prerequisites installed! Please restart terminal and run full installation.
pause
goto MAIN_MENU

:FIX_PYQT6
cls
echo ===============================================
echo        PYQT6 TROUBLESHOOTER
echo ===============================================

if not exist "venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found!
    pause
    goto MAIN_MENU
)

call venv\Scripts\activate.bat

echo Upgrading build tools...
python -m pip install --upgrade pip setuptools wheel
pip cache purge

echo Attempting PyQt6 installation...
pip install --only-binary=all --force-reinstall PyQt6==6.5.3
if %errorLevel% equ 0 (
    echo PyQt6 installed successfully!
    goto :test_pyqt
)

echo Trying alternative version...
pip install --only-binary=all --force-reinstall PyQt6==6.4.2
if %errorLevel% equ 0 (
    echo PyQt6 alternative version installed!
    goto :test_pyqt
)

echo Installing PySide6 as fallback...
pip install PySide6>=6.4.0

:test_pyqt
python -c "try: import PyQt6.QtWidgets; print('PyQt6: SUCCESS')" 2>nul || (
    python -c "try: import PySide6.QtWidgets; print('PySide6: SUCCESS')" 2>nul || (
        echo GUI framework test failed
    )
)
pause
goto MAIN_MENU

:RUN_APP
cls
echo ===============================================
echo         STARTING STAFFCLOCK
echo ===============================================

if not exist "venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found! Run installation first.
    pause
    goto MAIN_MENU
)

if not exist "staffclock\main.py" (
    echo ERROR: Application files not found!
    pause
    goto MAIN_MENU
)

call venv\Scripts\activate

echo Checking dependencies...
python -c "import PyQt6" 2>nul || (
    echo ERROR: PyQt6 not found!
    pause
    goto MAIN_MENU
)

echo Checking fingerprint devices...
python -c "
try:
    import usb.core
    devices = list(usb.core.find(find_all=True, idVendor=0x05ba))
    print('DigitalPersona devices: %d found' % len(devices))
except:
    print('Device detection unavailable')
" 2>nul

echo Starting application...
python -m staffclock.main

if %errorLevel% neq 0 (
    echo Application exited with error code: %errorLevel%
    pause
)
goto MAIN_MENU

:SYSTEM_INFO
cls
echo ===============================================
echo          SYSTEM INFORMATION
echo ===============================================

echo SYSTEM:
ver
echo Architecture: %PROCESSOR_ARCHITECTURE%
echo.

echo PYTHON:
python --version 2>nul || echo Python: Not installed
pip --version 2>nul || echo pip: Not available
echo.

echo VIRTUAL ENVIRONMENT:
if exist "venv\Scripts\python.exe" (
    echo Status: Installed
) else (
    echo Status: Not found
)
echo.

echo APPLICATION:
if exist "staffclock\main.py" (
    echo Main application: Found
) else (
    echo Main application: Missing
)
echo.

echo DIGITAL PERSONA SDK:
if exist "%ProgramFiles%\DigitalPersona\One Touch for Windows SDK\bin" (
    echo SDK: Installed (64-bit)
) else if exist "%ProgramFiles(x86)%\DigitalPersona\One Touch for Windows SDK\bin" (
    echo SDK: Installed (32-bit)
) else (
    echo SDK: Not found
)
echo.

pause
goto MAIN_MENU

:UNINSTALL
cls
echo ===============================================
echo         UNINSTALL STAFFCLOCK
echo ===============================================

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Administrator privileges required!
    pause
    goto MAIN_MENU
)

set /p CONFIRM="Remove StaffClock? (Y/N): "
if /i not "%CONFIRM%"=="Y" goto MAIN_MENU

echo Stopping processes...
taskkill /f /im python.exe 2>nul

echo Removing virtual environment...
if exist "venv" rmdir /s /q venv

echo Removing shortcuts...
if exist "%USERPROFILE%\Desktop\StaffClock.lnk" del "%USERPROFILE%\Desktop\StaffClock.lnk"

echo Cleaning up...
if exist "TempData" rmdir /s /q "TempData"
if exist "python-3.11.9-amd64.exe" del "python-3.11.9-amd64.exe"

set /p REMOVE_DATA="Remove data files? (Y/N): "
if /i "%REMOVE_DATA%"=="Y" (
    for %%d in (ProgramData Backups Timesheets biometric_samples QR_Codes) do (
        if exist "%%d" rmdir /s /q "%%d"
    )
)

echo Uninstall complete!
pause
goto MAIN_MENU

:HELP
cls
echo ===============================================
echo          TROUBLESHOOTING GUIDE
echo ===============================================
echo.
echo COMMON ISSUES:
echo.
echo 1. PyQt6 installation fails:
echo    - Run option 4 (Fix PyQt6)
echo    - Install Visual C++ Redistributable
echo    - Try different Python version
echo.
echo 2. Fingerprint reader not detected:
echo    - Check USB connection
echo    - Install Digital Persona SDK
echo    - Check Device Manager
echo    - Run as Administrator
echo.
echo 3. Python not found:
echo    - Restart command prompt
echo    - Reinstall Python with PATH option
echo.
echo 4. Permission errors:
echo    - Run as Administrator
echo    - Check antivirus interference
echo.
echo 5. Application won't start:
echo    - Check system info (option 6)
echo    - Verify dependencies
echo    - Check log files
echo.
pause
goto MAIN_MENU

:EXIT
echo.
echo Thank you for using StaffClock Universal Installer!
exit /b 0 