@echo off
echo ===============================================
echo      PyQt6 Windows Installation Fix
echo ===============================================
echo.
echo This script will attempt to fix the PyQt6 installation issue
echo by trying multiple installation strategies.
echo.

:: Activate the virtual environment
call venv\Scripts\activate.bat

echo [1/5] Upgrading pip and build tools...
python -m pip install --upgrade pip setuptools wheel

echo [2/5] Cleaning pip cache...
pip cache purge

echo [3/5] Attempting PyQt6 installation with pre-compiled wheels only...
pip install --only-binary=all --force-reinstall PyQt6==6.5.3
if %errorLevel% equ 0 (
    echo SUCCESS: PyQt6 6.5.3 installed successfully!
    goto :test_import
)

echo [4/5] Trying alternative PyQt6 version...
pip install --only-binary=all --force-reinstall PyQt6==6.4.2
if %errorLevel% equ 0 (
    echo SUCCESS: PyQt6 6.4.2 installed successfully!
    goto :test_import
)

echo [5/5] Installing PySide6 as alternative...
pip install PySide6>=6.4.0
if %errorLevel% equ 0 (
    echo SUCCESS: PySide6 installed as alternative to PyQt6!
    echo NOTE: You may need to update import statements from PyQt6 to PySide6
    goto :test_import
)

echo ERROR: All installation attempts failed.
echo.
echo NEXT STEPS:
echo 1. Try updating Python to 3.9, 3.10, or 3.11
echo 2. Install Visual Studio Build Tools
echo 3. Consider using Anaconda Python instead
echo.
pause
exit /b 1

:test_import
echo.
echo Testing GUI framework import...
python -c "try: import PyQt6.QtWidgets; print('PyQt6 import: SUCCESS')" 2>nul || (
    python -c "try: import PySide6.QtWidgets; print('PySide6 import: SUCCESS')" 2>nul || (
        echo WARNING: GUI framework import failed
        pause
        exit /b 1
    )
)

echo.
echo ===============================================
echo           Fix Applied Successfully!
echo ===============================================
echo.
echo You can now run the main installation script or
echo try running the application directly.
echo.
pause 