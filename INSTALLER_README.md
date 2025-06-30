# StaffClock Universal Installer

## 🎯 **Overview**
The **StaffClock Universal Installer** is a comprehensive, menu-driven batch script that combines all installation, setup, troubleshooting, and management functionality for the StaffClock application into one convenient tool.

## 🚀 **Quick Start**
1. **Download** the StaffClock application files
2. **Right-click** on `StaffClock_Universal_Installer.bat`
3. **Select** "Run as administrator"
4. **Choose option 1** for complete installation
5. **Follow** the on-screen prompts

## 📋 **Menu Options**

### **[1] Complete Installation (Recommended)**
**What it does:**
- ✅ Downloads and installs Python 3.11 (if needed)
- ✅ Installs DigitalPersona SDK for fingerprint support
- ✅ Sets up USB device permissions
- ✅ Creates Python virtual environment
- ✅ Installs all dependencies (PyQt6, OpenCV, USB libraries, etc.)
- ✅ Creates application directories
- ✅ Sets up desktop shortcut
- ✅ Tests fingerprint device detection

**Use when:** You want full StaffClock functionality including fingerprint support

### **[2] Quick Installation (Basic)**
**What it does:**
- ✅ Creates Python virtual environment (requires Python pre-installed)
- ✅ Installs essential dependencies only
- ✅ Creates basic application directories
- ❌ No fingerprint support
- ❌ No DigitalPersona SDK

**Use when:** You only need basic time tracking without fingerprint features

### **[3] Prerequisites via Windows Package Manager**
**What it does:**
- ✅ Uses `winget` to install Python 3.9
- ✅ Installs Visual C++ Redistributable
- ✅ Installs Git for development
- ⚠️ Requires Windows Package Manager (winget)

**Use when:** You prefer using Windows Package Manager for system-level installations

### **[4] Fix PyQt6 Installation Issues**
**What it does:**
- 🔧 Upgrades pip and build tools
- 🔧 Clears pip cache
- 🔧 Tries multiple PyQt6 versions
- 🔧 Falls back to PySide6 if needed
- 🔧 Tests GUI framework imports

**Use when:** You're experiencing GUI-related installation problems

### **[5] Run StaffClock Application**
**What it does:**
- ▶️ Activates virtual environment
- ▶️ Checks dependencies
- ▶️ Tests fingerprint device detection
- ▶️ Starts the StaffClock application
- 📊 Shows error diagnostics if startup fails

**Use when:** You want to start the application (replaces `run_staffclock.bat`)

### **[6] System Information and Status**
**What it does:**
- 📋 Shows Windows version and architecture
- 📋 Reports Python installation status
- 📋 Shows virtual environment status
- 📋 Lists installed packages
- 📋 Shows DigitalPersona SDK status
- 📋 Tests USB device detection

**Use when:** You need to diagnose installation or hardware issues

### **[7] Uninstall StaffClock**
**What it does:**
- 🗑️ Removes virtual environment
- 🗑️ Deletes temporary directories
- 🗑️ Removes desktop shortcuts
- 🗑️ Cleans up installer files
- ⚠️ **Optional:** Remove all data files (databases, backups, etc.)

**Use when:** You want to remove StaffClock (preserves data by default)

### **[8] Help and Troubleshooting**
**What it shows:**
- 💡 Common installation issues and solutions
- 💡 Fingerprint reader troubleshooting steps
- 💡 Python and dependency problem fixes
- 💡 Permission and security issue guidance

**Use when:** You're experiencing problems and need guidance

## 🔧 **Replaced Scripts**
This universal installer replaces all these individual batch files:

| **Old Script** | **Functionality Now In** |
|---|---|
| `setup_staffclock_complete.bat` | Option 1: Complete Installation |
| `install_staffclock.bat` | Option 1: Complete Installation |
| `install_essentials_winget.bat` | Option 3: Prerequisites via winget |
| `fix_pyqt6_windows.bat` | Option 4: Fix PyQt6 Issues |
| `run_staffclock.bat` | Option 5: Run Application |
| `uninstall_staffclock.bat` | Option 7: Uninstall |

## ⚡ **Key Improvements**

### **User Experience**
- 🎨 **Menu-driven interface** - No need to remember script names
- 🔄 **Persistent menu** - Returns to main menu after each action
- 📱 **Clear status messages** - Real-time feedback during installation
- 🎯 **Targeted options** - Choose exactly what you need

### **Error Handling**
- ✅ **Admin privilege checks** - Automatic detection and prompts
- ✅ **Dependency validation** - Verifies each step before proceeding
- ✅ **Graceful failures** - Clear error messages with solutions
- ✅ **Recovery options** - Built-in troubleshooting tools

### **Installation Flexibility**
- 🔧 **Multiple installation methods** - Complete, quick, or prerequisites-only
- 🔧 **Automatic Python download** - No manual Python installation needed
- 🔧 **Fallback strategies** - Alternative approaches when primary methods fail
- 🔧 **Modular components** - Install only what you need

### **Maintenance & Management**
- 📊 **System diagnostics** - Comprehensive status reporting
- 🔍 **Device detection** - Automatic fingerprint reader testing
- 🧹 **Clean uninstall** - Removes components while preserving data
- 📚 **Built-in help** - Troubleshooting guide always available

## 🛠️ **Technical Requirements**

### **System Requirements**
- **OS:** Windows 10/11 (64-bit recommended)
- **RAM:** 4GB minimum, 8GB recommended
- **Storage:** 2GB free space
- **Permissions:** Administrator access required

### **Optional Hardware**
- **Fingerprint Reader:** DigitalPersona U.are.U series (4500, 5160, etc.)
- **Network:** Internet connection for downloading dependencies

## 🚨 **Important Notes**

### **Administrator Rights**
⚠️ **Always run as Administrator** - Right-click the installer and select "Run as administrator"

### **Antivirus Software**
⚠️ **Temporary exclusion may be needed** - Some antivirus software may interfere with installation

### **Internet Connection**
⚠️ **Required for first-time setup** - Downloading Python and dependencies requires internet

### **Existing Installations**
✅ **Safe to re-run** - The installer detects existing components and skips unnecessary steps

## 📞 **Support**

### **Before Seeking Help**
1. Run **Option 6** (System Information) to gather diagnostic info
2. Try **Option 8** (Help and Troubleshooting) for common solutions
3. For PyQt6 issues, try **Option 4** (Fix PyQt6 Issues)

### **Common Solutions**
- **Python not found:** Use Option 3 or manually install Python with PATH option
- **Permission errors:** Always run as Administrator
- **PyQt6 fails:** Run Option 4 for automated troubleshooting
- **Fingerprint issues:** Check USB connection and Device Manager

## 🎉 **Success Indicators**
After successful installation, you should see:
- ✅ Desktop shortcut created
- ✅ Virtual environment in `venv` folder
- ✅ All directories created (`ProgramData`, `Backups`, etc.)
- ✅ Dependencies installed and tested
- ✅ Application starts without errors

---

**Enjoy using StaffClock with enhanced logging and security features!** 🎯 