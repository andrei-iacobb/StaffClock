@echo off
setlocal EnableDelayedExpansion

echo ===============================================
echo    StaffClock Essential Prerequisites
echo         (Minimal winget installation)
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

:: Check if winget is available
winget --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Windows Package Manager (winget) is not available!
    echo.
    echo Install winget from Microsoft Store (search "App Installer")
    echo Or download from: https://github.com/microsoft/winget-cli/releases
    pause
    exit /b 1
)

echo ✓ Windows Package Manager detected
echo.

echo [1/3] Installing Python 3.9...
echo This is the core requirement for StaffClock
winget install Python.Python.3.9 --exact --silent --accept-package-agreements --accept-source-agreements
if %errorLevel% equ 0 (
    echo ✓ Python 3.9 installed successfully
) else (
    echo ⚠ Python 3.9 installation issue (may already be installed)
)
echo.

echo [2/3] Installing Visual C++ Redistributable...
echo Required for Python packages with native components
winget install Microsoft.VCRedist.2015+.x64 --silent --accept-package-agreements --accept-source-agreements
if %errorLevel% equ 0 (
    echo ✓ Visual C++ Redistributable installed
) else (
    echo ⚠ Visual C++ Redistributable installation issue (may already be installed)
)
echo.

echo [3/3] Installing Git...
echo Useful for downloading and updating StaffClock
winget install Git.Git --silent --accept-package-agreements --accept-source-agreements
if %errorLevel% equ 0 (
    echo ✓ Git installed successfully
) else (
    echo ⚠ Git installation issue (may already be installed)
)
echo.

echo Refreshing environment variables...
:: Refresh PATH for current session
for /f "skip=2 tokens=3*" %%a in ('reg query HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment /v PATH') do set "SYSTEM_PATH=%%a %%b"
for /f "skip=2 tokens=3*" %%a in ('reg query HKCU\Environment /v PATH') do set "USER_PATH=%%a %%b"
set "PATH=%SYSTEM_PATH%;%USER_PATH%"

echo.
echo ===============================================
echo        Essential Installation Complete!
echo ===============================================
echo.

:: Verify installations
python --version >nul 2>&1
if %errorLevel% equ 0 (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do echo ✓ Python %%i is ready
) else (
    echo ⚠ Python not found - you may need to restart your terminal
)

pip --version >nul 2>&1
if %errorLevel% equ 0 (
    echo ✓ pip is available
) else (
    echo ⚠ pip not found - you may need to restart your terminal
)

echo.
echo 🎯 READY FOR STAFFCLOCK INSTALLATION!
echo.
echo Next steps:
echo 1. Open a NEW Command Prompt (to refresh PATH)
echo 2. Navigate to StaffClock folder: cd C:\Users\Admin\StaffClock
echo 3. Run: install_staffclock_py39.bat
echo.
echo That's it! You now have everything needed for StaffClock.
echo.
pause 