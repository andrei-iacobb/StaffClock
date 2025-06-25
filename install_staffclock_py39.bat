@echo off
setlocal EnableDelayedExpansion

echo ===============================================
echo       StaffClock Application Installer
echo           (Python 3.9 Optimized)
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

echo [1/8] Checking Python 3.9 requirements...

:: Check if Python is installed
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo RECOMMENDED: Install Python 3.9.x from https://python.org
    echo - Download Python 3.9.18 (latest 3.9 version)
    echo - Make sure to check "Add Python to PATH" during installation
    echo - Choose "Install for all users" if prompted
    pause
    exit /b 1
)

:: Get Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Found Python %PYTHON_VERSION%

:: Check for Python 3.9 specifically (recommended)
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set MAJOR=%%a
    set MINOR=%%b
)

if %MAJOR% LSS 3 (
    echo ERROR: Python 3.9 is required for optimal compatibility. Found Python %PYTHON_VERSION%
    echo Please install Python 3.9.x from https://python.org
    pause
    exit /b 1
)

if %MAJOR% EQU 3 if %MINOR% LSS 9 (
    echo WARNING: Python 3.9+ is recommended for best PyQt6 compatibility. Found Python %PYTHON_VERSION%
    echo You may encounter installation issues with older Python versions.
    echo Consider upgrading to Python 3.9.x
    echo.
    set /p CONTINUE="Continue anyway? (y/n): "
    if /i not "!CONTINUE!"=="y" (
        echo Installation cancelled. Please upgrade to Python 3.9.x
        pause
        exit /b 1
    )
)

if %MAJOR% EQU 3 if %MINOR% EQU 9 (
    echo EXCELLENT: Python 3.9 detected - optimal for PyQt6 compatibility!
)

if %MAJOR% EQU 3 if %MINOR% GTR 9 (
    echo GOOD: Python 3.%MINOR% detected - should work well with PyQt6
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

echo [5/8] Upgrading pip and build tools...
python -m pip install --upgrade pip>=23.0
python -m pip install --upgrade setuptools>=65.0 wheel>=0.38

echo [6/8] Installing Python dependencies (Python 3.9 optimized)...
echo This may take several minutes...

:: Try Python 3.9 optimized PyQt6 first
echo Attempting PyQt6 installation optimized for Python 3.9...
pip install --only-binary=all PyQt6==6.6.0 PyQt6-Qt6==6.6.0 PyQt6-sip==13.6.0
if %errorLevel% equ 0 (
    echo SUCCESS: PyQt6 6.6.0 installed successfully!
    goto :install_remaining
)

:: Fallback to slightly older version
echo First attempt failed. Trying PyQt6 6.5.3...
pip install --only-binary=all PyQt6==6.5.3 PyQt6-Qt6==6.5.3 PyQt6-sip==13.6.0
if %errorLevel% equ 0 (
    echo SUCCESS: PyQt6 6.5.3 installed successfully!
    goto :install_remaining
)

:: Fallback to even older but very stable version
echo Trying PyQt6 6.4.2 (very stable version)...
pip install --only-binary=all PyQt6==6.4.2 PyQt6-Qt6==6.4.2 PyQt6-sip==13.5.2
if %errorLevel% equ 0 (
    echo SUCCESS: PyQt6 6.4.2 installed successfully!
    goto :install_remaining
)

:: Last resort: PySide6
echo PyQt6 installation failed. Installing PySide6 as alternative...
pip install PySide6==6.6.0
if %errorLevel% equ 0 (
    echo SUCCESS: PySide6 installed as PyQt6 alternative!
    echo NOTE: The application may need minor code changes to use PySide6
    goto :install_remaining
)

echo ERROR: All GUI framework installation attempts failed.
echo.
echo TROUBLESHOOTING:
echo 1. Ensure you have a stable internet connection
echo 2. Try running: pip cache purge
echo 3. Check if antivirus is blocking the installation
echo 4. Consider using Anaconda Python with: conda install pyqt6
echo.
pause
exit /b 1

:install_remaining
echo Installing remaining dependencies...

:: Install packages in groups for better error handling
echo Installing computer vision packages...
pip install opencv-python==4.8.1.78 pillow==10.1.0 numpy==1.24.4

echo Installing scientific computing packages...
pip install scikit-learn==1.3.2 scipy==1.11.4

echo Installing visualization packages...
pip install matplotlib==3.8.2 seaborn==0.13.0

echo Installing system integration packages...
pip install pyusb==1.2.1 keyboard==0.13.5 pyglet==2.0.10

echo Installing utility packages...
pip install python-dateutil==2.8.2 psutil==5.9.6 requests==2.31.0

echo Installing development packages...
pip install pytest==7.4.3 black==23.11.0

echo Installing Windows-specific packages...
pip install pywin32==306 wmi==1.5.1

echo Installing report generation...
pip install reportlab==4.0.7

echo Installing USB support...
pip install libusb==1.0.26

echo Installing data handling...
pip install pandas==2.1.4

echo [7/8] Creating additional required directories...
if not exist "ProgramData" mkdir ProgramData
if not exist "TempData" mkdir TempData
if not exist "Timesheets" mkdir Timesheets
if not exist "Backups" mkdir Backups
if not exist "biometric_samples" mkdir biometric_samples
if not exist "QR_Codes" mkdir QR_Codes

echo [8/8] Installation validation...
echo Testing GUI framework installation...
python -c "try: import PyQt6.QtWidgets; print('✓ PyQt6 import: SUCCESS')" 2>nul || (
    python -c "try: import PySide6.QtWidgets; print('✓ PySide6 import: SUCCESS')" 2>nul || (
        echo ✗ WARNING: GUI framework import failed
        echo The application may not start correctly
    )
)

echo Testing computer vision...
python -c "try: import cv2; print('✓ OpenCV import: SUCCESS')" 2>nul || echo ✗ OpenCV import failed

echo Testing other key dependencies...
python -c "try: import numpy, pandas, matplotlib; print('✓ Core dependencies: SUCCESS')" 2>nul || echo ✗ Some core dependencies failed

echo.
echo ===============================================
echo        Installation Completed Successfully!
echo ===============================================
echo.
echo Python Version: %PYTHON_VERSION%
echo Virtual Environment: Created and configured
echo GUI Framework: PyQt6 or PySide6 installed
echo.
echo Next steps:
echo 1. Connect your Digital Persona fingerprint reader
echo 2. Run "run_staffclock.bat" to start the application
echo 3. The application will create default database and settings on first run
echo.
echo If you used PySide6 instead of PyQt6, you may need to update
echo import statements in the code from PyQt6 to PySide6.
echo.
echo For fingerprint reader issues, ensure Digital Persona drivers
echo are properly installed from the manufacturer.
echo.
pause 