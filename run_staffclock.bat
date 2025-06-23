@echo off
setlocal

echo ===============================================
echo         Starting StaffClock Application
echo          With DigitalPersona Support
echo ===============================================
echo.

:: Check if virtual environment exists
if not exist "venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found!
    echo Please run "setup_staffclock_complete.bat" first to set up the application.
    pause
    exit /b 1
)

:: Check if main application file exists
if not exist "staffclock\main.py" (
    echo ERROR: staffclock\main.py not found!
    echo Please ensure you're running this from the StaffClock application directory.
    pause
    exit /b 1
)

:: Check if staffclock package structure is correct
if not exist "staffclock\__init__.py" (
    echo Creating __init__.py file for package structure...
    echo. > "staffclock\__init__.py"
)

echo Activating virtual environment...
call venv\Scripts\activate

echo Checking system and dependencies...
:: Brief pause to let user see the message
timeout /t 1 /nobreak >nul

:: Test if critical packages are available
echo Testing Python dependencies...
python -c "import PyQt6" 2>nul || (
    echo ERROR: PyQt6 not found. Please run the installer again.
    pause
    exit /b 1
)

python -c "import cv2" 2>nul || (
    echo WARNING: OpenCV not found. Some features may not work.
)

python -c "import usb.core" 2>nul || (
    echo WARNING: PyUSB not found. Fingerprint functionality may not work.
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
        print('  Connect your fingerprint reader and try again')
except ImportError:
    print('⚠ USB library not available')
except Exception as e:
    print('⚠ Device detection error: %s' % e)
" 2>nul

echo.
echo Starting StaffClock Application...
echo.
echo ===============================================
echo  Application is starting - please wait...
echo ===============================================
echo.

:: Run the application with the correct module structure
python -m staffclock.main

:: Check if the application exited with an error
if %errorLevel% neq 0 (
    echo.
    echo ===============================================
    echo        Application exited with an error
    echo ===============================================
    echo.
    echo Error Code: %errorLevel%
    echo.
    echo Common solutions:
    echo 1. Make sure your fingerprint reader is connected via USB
    echo 2. Check Device Manager for DigitalPersona or U.are.U devices
    echo 3. Ensure all dependencies were installed correctly
    echo 4. Try running as Administrator
    echo 5. Verify the Digital Persona SDK is properly installed
    echo 6. Restart your computer and try again
    echo.
    echo If the error persists:
    echo - Check that Python modules can import correctly
    echo - Verify the staffclock package structure is intact
    echo - Run the complete installer again: setup_staffclock_complete.bat
    echo.
    pause
) else (
    echo.
    echo Application closed normally.
)

echo.
echo Press any key to exit...
pause >nul 