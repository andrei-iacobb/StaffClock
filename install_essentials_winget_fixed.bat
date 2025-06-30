@echo off
setlocal

echo ===============================================
echo    StaffClock Essential Prerequisites
echo         (Fixed winget installation)
echo ===============================================
echo.

:: Check if running as administrator
net session >nul 2>&1
if not %errorLevel% == 0 (
    echo ERROR: This installer must be run as Administrator!
    echo Please right-click on this file and select "Run as administrator"
    pause
    exit /b 1
)

:: Check if winget is available
winget --version >nul 2>&1
if not %errorLevel% == 0 (
    echo ERROR: Windows Package Manager (winget) is not available!
    echo.
    echo Install winget from Microsoft Store - search "App Installer"
    echo Or download from: https://github.com/microsoft/winget-cli/releases
    pause
    exit /b 1
)

echo Verified: Windows Package Manager is available
echo.

echo [1/3] Installing Python 3.9...
echo This is the core requirement for StaffClock
winget install Python.Python.3.9 --exact --silent --accept-package-agreements --accept-source-agreements
if %errorLevel% == 0 (
    echo SUCCESS: Python 3.9 installed
) else (
    echo WARNING: Python 3.9 installation had issues - may already be installed
)
echo.

echo [2/3] Installing Visual C++ Redistributable...
echo Required for Python packages with native components
winget install Microsoft.VCRedist.2015+.x64 --silent --accept-package-agreements --accept-source-agreements
if %errorLevel% == 0 (
    echo SUCCESS: Visual C++ Redistributable installed
) else (
    echo WARNING: Visual C++ Redistributable had issues - may already be installed
)
echo.

echo [3/3] Installing Git...
echo Useful for downloading and updating StaffClock
winget install Git.Git --silent --accept-package-agreements --accept-source-agreements
if %errorLevel% == 0 (
    echo SUCCESS: Git installed
) else (
    echo WARNING: Git installation had issues - may already be installed
)
echo.

echo ===============================================
echo        Installation Complete!
echo ===============================================
echo.

echo Verifying installations...
echo.

python --version >nul 2>&1
if %errorLevel% == 0 (
    echo VERIFIED: Python is available
    python --version
) else (
    echo WARNING: Python not found - restart your terminal
)

pip --version >nul 2>&1
if %errorLevel% == 0 (
    echo VERIFIED: pip is available
) else (
    echo WARNING: pip not found - restart your terminal
)

git --version >nul 2>&1
if %errorLevel% == 0 (
    echo VERIFIED: Git is available
) else (
    echo WARNING: Git not found - restart your terminal
)

echo.
echo READY FOR STAFFCLOCK INSTALLATION!
echo.
echo Next steps:
echo 1. Close this window and open a NEW Command Prompt
echo 2. Navigate to StaffClock: cd C:\Users\Admin\StaffClock
echo 3. Run: install_staffclock_py39.bat
echo.
pause 