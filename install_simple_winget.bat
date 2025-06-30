@echo off

echo ===============================================
echo    Simple StaffClock Prerequisites Installer
echo ===============================================
echo.

echo Checking administrator privileges...
net session >nul 2>&1
if errorlevel 1 goto :not_admin

echo Checking winget availability...
winget --version >nul 2>&1
if errorlevel 1 goto :no_winget

echo Installing Python 3.9...
winget install Python.Python.3.9 --exact --silent --accept-package-agreements --accept-source-agreements

echo Installing Visual C++ Redistributable...
winget install Microsoft.VCRedist.2015+.x64 --silent --accept-package-agreements --accept-source-agreements

echo Installing Git...
winget install Git.Git --silent --accept-package-agreements --accept-source-agreements

echo.
echo Installation completed!
echo.
echo IMPORTANT: Close this window and open a NEW Command Prompt
echo Then run: install_staffclock_py39.bat
echo.
pause
goto :end

:not_admin
echo ERROR: Must run as Administrator!
echo Right-click this file and select "Run as administrator"
pause
goto :end

:no_winget
echo ERROR: winget not found!
echo Install "App Installer" from Microsoft Store
pause
goto :end

:end 