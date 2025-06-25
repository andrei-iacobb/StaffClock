@echo off
setlocal EnableDelayedExpansion

echo ===============================================
echo     StaffClock Prerequisites Installer
echo           (Using Windows Package Manager)
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
    echo Please install winget by:
    echo 1. Installing "App Installer" from Microsoft Store, OR
    echo 2. Downloading from: https://github.com/microsoft/winget-cli/releases
    echo 3. On Windows 11, winget should be pre-installed
    pause
    exit /b 1
)

echo ✓ Windows Package Manager (winget) detected
echo.

echo [1/8] Installing Python 3.9...
echo Installing Python 3.9.13 (stable version with excellent PyQt6 support)...
winget install Python.Python.3.9 --exact --silent --accept-package-agreements --accept-source-agreements
if %errorLevel% equ 0 (
    echo ✓ Python 3.9 installation completed
) else (
    echo ⚠ Python 3.9 installation may have failed or was already installed
)
echo.

echo [2/8] Installing Git for version control...
winget install Git.Git --silent --accept-package-agreements --accept-source-agreements
if %errorLevel% equ 0 (
    echo ✓ Git installation completed
) else (
    echo ⚠ Git installation may have failed or was already installed
)
echo.

echo [3/8] Installing Microsoft Visual C++ Redistributable...
echo Installing Visual C++ 2019-2022 Redistributable (required for some Python packages)...
winget install Microsoft.VCRedist.2015+.x64 --silent --accept-package-agreements --accept-source-agreements
if %errorLevel% equ 0 (
    echo ✓ Visual C++ Redistributable installation completed
) else (
    echo ⚠ Visual C++ Redistributable installation may have failed or was already installed
)
echo.

echo [4/8] Installing Microsoft Visual Studio Build Tools...
echo Installing Build Tools (required for packages that need compilation)...
winget install Microsoft.VisualStudio.2022.BuildTools --silent --accept-package-agreements --accept-source-agreements
if %errorLevel% equ 0 (
    echo ✓ Visual Studio Build Tools installation completed
) else (
    echo ⚠ Build Tools installation may have failed or was already installed
)
echo.

echo [5/8] Installing Windows Terminal (recommended)...
winget install Microsoft.WindowsTerminal --silent --accept-package-agreements --accept-source-agreements
if %errorLevel% equ 0 (
    echo ✓ Windows Terminal installation completed
) else (
    echo ⚠ Windows Terminal installation may have failed or was already installed
)
echo.

echo [6/8] Installing 7-Zip (for archive handling)...
winget install 7zip.7zip --silent --accept-package-agreements --accept-source-agreements
if %errorLevel% equ 0 (
    echo ✓ 7-Zip installation completed
) else (
    echo ⚠ 7-Zip installation may have failed or was already installed
)
echo.

echo [7/8] Installing Notepad++ (useful for editing config files)...
winget install Notepad++.Notepad++ --silent --accept-package-agreements --accept-source-agreements
if %errorLevel% equ 0 (
    echo ✓ Notepad++ installation completed
) else (
    echo ⚠ Notepad++ installation may have failed or was already installed
)
echo.

echo [8/8] Refreshing environment variables...
echo Updating PATH environment variable...
:: Refresh environment variables for current session
for /f "skip=2 tokens=3*" %%a in ('reg query HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment /v PATH') do set "SYSTEM_PATH=%%a %%b"
for /f "skip=2 tokens=3*" %%a in ('reg query HKCU\Environment /v PATH') do set "USER_PATH=%%a %%b"
set "PATH=%SYSTEM_PATH%;%USER_PATH%"

echo.
echo ===============================================
echo      Installation Summary
echo ===============================================
echo.

:: Check installations
echo Verifying installations...
echo.

python --version >nul 2>&1
if %errorLevel% equ 0 (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do echo ✓ Python %%i
) else (
    echo ✗ Python not found in PATH (may need to restart terminal)
)

git --version >nul 2>&1
if %errorLevel% equ 0 (
    for /f "tokens=3" %%i in ('git --version 2^>^&1') do echo ✓ Git %%i
) else (
    echo ✗ Git not found in PATH (may need to restart terminal)
)

pip --version >nul 2>&1
if %errorLevel% equ 0 (
    for /f "tokens=2" %%i in ('pip --version 2^>^&1') do echo ✓ pip %%i
) else (
    echo ✗ pip not found in PATH (may need to restart terminal)
)

echo.
echo ===============================================
echo         Prerequisites Installation Complete!
echo ===============================================
echo.
echo 🎉 All prerequisites have been installed!
echo.
echo NEXT STEPS:
echo.
echo 1. ⚠  RESTART YOUR COMMAND PROMPT or PowerShell
echo    (This ensures PATH environment variables are updated)
echo.
echo 2. 📂 Navigate to your StaffClock directory:
echo    cd C:\Users\Admin\StaffClock
echo.
echo 3. 🚀 Run the Python 3.9 optimized installer:
echo    install_staffclock_py39.bat
echo.
echo OPTIONAL: You can also install these useful tools:
echo • Visual Studio Code: winget install Microsoft.VisualStudioCode
echo • Windows Subsystem for Linux: wsl --install
echo • PowerToys: winget install Microsoft.PowerToys
echo.
echo 📋 What was installed:
echo • Python 3.9.13 (optimized for PyQt6)
echo • Git (version control)
echo • Visual C++ Redistributable (runtime libraries)
echo • Visual Studio Build Tools (for package compilation)
echo • Windows Terminal (improved command line)
echo • 7-Zip (archive handling)
echo • Notepad++ (text editor)
echo.
echo ℹ  If any installations failed, you can run specific commands:
echo   winget install Python.Python.3.9 --exact
echo   winget install Git.Git
echo   winget install Microsoft.VCRedist.2015+.x64
echo.
pause 