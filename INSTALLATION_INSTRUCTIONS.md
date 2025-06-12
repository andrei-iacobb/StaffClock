# StaffClock Installation Instructions

## Quick Installation (Recommended)

### For Complete Setup (Includes Python Installation)
1. **Download** all required files to a folder on your Windows computer
2. **Right-click** on `setup_staffclock_complete.bat` and select **"Run as administrator"**
3. **Follow** the on-screen prompts
4. **Connect** your Digital Persona fingerprint reader
5. **Double-click** the StaffClock shortcut on your desktop to start the application

### For Basic Installation (Python Already Installed)
1. **Ensure** Python 3.8+ is installed on your system
2. **Right-click** on `install_staffclock.bat` and select **"Run as administrator"**
3. **Follow** the on-screen prompts
4. **Run** `run_staffclock.bat` to start the application

## System Requirements

- **Operating System**: Windows 10/11 (32-bit or 64-bit)
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 2GB free disk space
- **Hardware**: Digital Persona U.are.U 4000B or U.are.U 4500 fingerprint reader
- **Network**: Internet connection required for initial setup

## Installation Files

### Installer Scripts
- `setup_staffclock_complete.bat` - Complete installer with Python download
- `install_staffclock.bat` - Basic installer (requires Python pre-installed)
- `run_staffclock.bat` - Application launcher

### Required Files/Folders
- `requirements.txt` - Python dependencies
- `main.py` - Main application file
- `Digital-Persona-SDK-master/` - Digital Persona SDK files
- OR `DigitalPersona-SDK.zip` - SDK in zip format

## Installation Process

### Step 1: Prepare Installation Files
1. Download or copy all StaffClock files to a dedicated folder
2. Ensure the Digital Persona SDK files are present:
   - Either `Digital-Persona-SDK-master` folder
   - Or `DigitalPersona-SDK.zip` file

### Step 2: Run Installer
1. **IMPORTANT**: Right-click the installer and select "Run as administrator"
2. The installer will:
   - Check system requirements
   - Install Python 3.11 (if needed)
   - Install Digital Persona SDK
   - Create Python virtual environment
   - Install all required dependencies
   - Set up application directories
   - Create desktop shortcut

### Step 3: Connect Hardware
1. Connect your Digital Persona fingerprint reader to a USB port
2. Windows should automatically detect and install drivers
3. Verify in Device Manager that the device appears without errors

### Step 4: First Run
1. Double-click the "StaffClock" desktop shortcut
2. The application will create initial database and configuration files
3. Follow the on-screen setup wizard

## Troubleshooting

### Common Issues

#### Python Installation Problems
- **Error**: "Python is not installed or not in PATH"
- **Solution**: Run `setup_staffclock_complete.bat` which will install Python automatically

#### Digital Persona SDK Issues
- **Error**: "Digital Persona SDK files not found"
- **Solution**: Ensure either `Digital-Persona-SDK-master` folder or `DigitalPersona-SDK.zip` is present

#### Fingerprint Reader Not Detected
- **Error**: Device not recognized
- **Solutions**:
  1. Check USB connection
  2. Install latest Digital Persona drivers
  3. Check Windows Device Manager for errors
  4. Try a different USB port
  5. Restart computer after SDK installation

#### Permission Errors
- **Error**: "Access denied" or "Permission denied"
- **Solution**: Always run installers as Administrator

#### Dependency Installation Failures
- **Error**: Failed to install Python packages
- **Solutions**:
  1. Check internet connection
  2. Temporarily disable antivirus
  3. Run installer again
  4. Manual installation: Open Command Prompt as Admin and run:
     ```
     cd path\to\staffclock\folder
     venv\Scripts\activate
     pip install -r requirements.txt
     ```

### Advanced Troubleshooting

#### Manual Python Installation
If automatic Python installation fails:
1. Download Python 3.11 from https://python.org
2. Install with "Add Python to PATH" checked
3. Restart Command Prompt
4. Run `install_staffclock.bat`

#### Manual SDK Installation
If SDK installation fails:
1. Navigate to `Digital-Persona-SDK-master\SDK\`
2. Run `Setup.exe` manually as Administrator
3. Follow installation wizard
4. Run StaffClock installer again

#### Virtual Environment Issues
If virtual environment creation fails:
1. Delete existing `venv` folder
2. Open Command Prompt as Administrator
3. Navigate to StaffClock folder
4. Run: `python -m venv venv`
5. Run: `venv\Scripts\activate`
6. Run: `pip install -r requirements.txt`

## Post-Installation

### Initial Setup
1. **Admin Access**: Set up admin PIN when prompted
2. **Staff Setup**: Add staff members and enroll fingerprints
3. **Settings**: Configure printer settings and other preferences
4. **Backup**: The system automatically creates backups

### Regular Maintenance
- The application automatically backs up data daily
- Check for Windows updates regularly
- Keep fingerprint reader clean
- Monitor log files for any issues

### Updates
To update the application:
1. Download new version files
2. Run installer again (it will update existing installation)
3. Your data and settings will be preserved

## Support

### Log Files
Application logs are stored in: `ProgramData\staff_clock_system.log`

### Database Files
- Main database: `ProgramData\staff_hours.db`
- Biometric data: `biometric_profiles.db`
- Backups: `Backups\` folder

### Getting Help
If you encounter issues:
1. Check the log files for error messages
2. Verify all hardware connections
3. Ensure Windows is up to date
4. Try running as Administrator
5. Restart the computer if issues persist

## File Structure After Installation

```
StaffClock/
├── venv/                           # Python virtual environment
├── ProgramData/                    # Application data
│   ├── settings.json
│   ├── staff_hours.db
│   └── staff_clock_system.log
├── Backups/                        # Automatic backups
├── Timesheets/                     # Generated timesheets
├── biometric_samples/              # Fingerprint samples
├── main.py                         # Application entry point
├── requirements.txt                # Python dependencies
├── run_staffclock.bat             # Application launcher
└── Desktop Shortcut: StaffClock   # Desktop shortcut
```

---

**Note**: Always run batch files as Administrator to ensure proper installation and operation. 