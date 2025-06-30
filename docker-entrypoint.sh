#!/bin/bash
set -e

echo "==============================================="
echo "      StaffClock Docker Container Starting"
echo "==============================================="

# Function to cleanup on exit
cleanup() {
    echo "Shutting down services..."
    pkill -f x11vnc || true
    pkill -f Xvfb || true
    pkill -f fluxbox || true
    exit 0
}

# Set trap for cleanup
trap cleanup SIGTERM SIGINT

# Create necessary directories
mkdir -p /app/ProgramData /app/TempData /app/Timesheets /app/Backups /app/biometric_samples /app/QR_Codes

# Set up X11 display
echo "Setting up virtual display..."
export DISPLAY=:99
Xvfb :99 -screen 0 1920x1080x24 &
XVFB_PID=$!

# Wait for X server to start
sleep 2

# Start window manager
echo "Starting window manager..."
fluxbox &
FLUXBOX_PID=$!

# Start VNC server
echo "Starting VNC server..."
x11vnc -display :99 -forever -usepw -create -rfbport 5900 &
VNC_PID=$!

# Set VNC password if provided
if [ ! -z "$VNC_PASSWORD" ]; then
    echo "Setting VNC password..."
    mkdir -p ~/.vnc
    echo "$VNC_PASSWORD" | vncpasswd -f > ~/.vnc/passwd
    chmod 600 ~/.vnc/passwd
    x11vnc -display :99 -forever -usepw -rfbport 5900 &
else
    echo "No VNC password set. Use VNC_PASSWORD environment variable to set one."
    x11vnc -display :99 -forever -nopw -rfbport 5900 &
fi

# Start noVNC if in development mode
if [ -d "/opt/novnc" ]; then
    echo "Starting noVNC web interface..."
    /opt/novnc/utils/websockify/run --web /opt/novnc 6080 localhost:5900 &
    NOVNC_PID=$!
    echo "noVNC available at http://localhost:6080"
fi

# Wait for display to be ready
sleep 3

# Set environment for GUI applications
export QT_X11_NO_MITSHM=1
export _X11_NO_MITSHM=1
export _MITSHM=0

# Handle fingerprint device (if available)
if [ -e "/dev/bus/usb" ]; then
    echo "USB devices detected, fingerprint reader may be available"
else
    echo "No USB devices detected, running in mock fingerprint mode"
fi

# Check for command line arguments
if [ "$1" = "bash" ] || [ "$1" = "shell" ]; then
    echo "Starting interactive shell..."
    exec bash
elif [ "$1" = "test" ]; then
    echo "Running application tests..."
    cd /app
    python -c "
import sys
sys.path.append('/app')
from staffclock.main import get_app_directory
print('App directory:', get_app_directory())
print('Testing PyQt6 import...')
from PyQt6.QtWidgets import QApplication
print('✓ PyQt6 import successful')
print('✓ Container setup complete')
"
else
    # Start the main application
    echo "Starting StaffClock application..."
    cd /app
    
    # Create a desktop environment for better GUI support
    echo "Starting desktop environment..."
    
    # Launch the application
    echo "Launching StaffClock..."
    python staffclock/main.py &
    APP_PID=$!
    
    echo "==============================================="
    echo "    StaffClock Started Successfully!"
    echo "==============================================="
    echo ""
    echo "Access the application via:"
    echo "• VNC: localhost:5900 (or your-server-ip:5900)"
    if [ -d "/opt/novnc" ]; then
        echo "• Web VNC: http://localhost:6080"
    fi
    echo ""
    echo "Container logs will appear below..."
    echo "Press Ctrl+C to stop the container"
    echo ""
    
    # Monitor the application
    while kill -0 $APP_PID 2>/dev/null; do
        sleep 5
    done
    
    echo "Application stopped"
fi

# Keep container running and handle signals
wait 