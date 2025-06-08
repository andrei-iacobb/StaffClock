# Staff Digital Timesheet System

A comprehensive staff clock-in/clock-out system with fingerprint authentication, timesheet management, and visitor tracking.

## Features

- **Digital Clock In/Out**: Staff can clock in and out using staff codes or fingerprints (continuous scanning)
- **Fingerprint Authentication**: DigitalPersona U.are.U 4500 integration with user-friendly enrollment
- **Admin Panel**: Complete staff management, record editing, and system administration
- **Timesheet Generation**: Automated PDF timesheet generation with customizable scheduling
- **Visitor Management**: Track and manage visitor entries and exits
- **Archive System**: Database archiving and backup functionality
- **Real-time Backup**: Continuous data protection with automatic backups

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**:
   ```bash
   python main.py
   ```

3. **Initial Setup**:
   - Connect DigitalPersona fingerprint scanner (optional)
   - Access Admin Panel (default PIN: 1234)
   - Add staff members
   - Enroll fingerprints for enhanced security

## System Requirements

- Windows 10/11
- Python 3.13+
- DigitalPersona U.are.U 4500 fingerprint scanner (optional)
- PyQt6

## Key Components

- `main.py` - Main application with integrated enrollment UI
- `fingerprint_manager.py` - Fingerprint device management
- `digitalpersona_sdk_simple.py` - DigitalPersona SDK interface
- `biometric_enrollment.py` - Biometric profile management

## Database

The system uses SQLite databases:
- `staff_timesheet.db` - Main operational database
- `biometric_profiles.db` - Fingerprint templates and profiles
- Archive databases in `Archive_Databases/` folder

## License

Proprietary software for internal use. 