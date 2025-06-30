# Multi-stage Dockerfile for StaffClock Application
# Supports GUI display via X11 forwarding and VNC

FROM python:3.9-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:99 \
    QT_X11_NO_MITSHM=1 \
    _X11_NO_MITSHM=1 \
    _MITSHM=0

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Core system packages
    wget \
    curl \
    git \
    sudo \
    # X11 and GUI support
    xvfb \
    x11vnc \
    fluxbox \
    xterm \
    # Qt6 dependencies
    libqt6core6 \
    libqt6gui6 \
    libqt6widgets6 \
    libqt6pdf6 \
    libqt6pdfwidgets6 \
    qt6-base-dev \
    # Graphics and display
    libgl1-mesa-glx \
    libglib2.0-0 \
    libxrender1 \
    libxrandr2 \
    libxext6 \
    libxi6 \
    libxtst6 \
    libxkbcommon-x11-0 \
    # Audio (for sound alerts)
    alsa-utils \
    pulseaudio \
    # Network tools
    netcat-openbsd \
    # Build tools for Python packages
    build-essential \
    pkg-config \
    # Clean up
    && rm -rf /var/lib/apt/lists/*

# Create application user
RUN useradd -m -s /bin/bash staffclock && \
    echo "staffclock ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements-py39.txt requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-py39.txt

# Copy application code
COPY staffclock/ ./staffclock/
COPY *.bat *.sh ./
COPY README.md ./

# Create necessary directories
RUN mkdir -p \
    /app/ProgramData \
    /app/TempData \
    /app/Timesheets \
    /app/Backups \
    /app/biometric_samples \
    /app/QR_Codes \
    && chown -R staffclock:staffclock /app

# Switch to application user
USER staffclock

# Create startup scripts
COPY --chown=staffclock:staffclock docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Expose VNC port
EXPOSE 5900

# Default command
CMD ["/app/docker-entrypoint.sh"]

# --- Development Stage ---
FROM base as development

USER root

# Install additional development tools
RUN apt-get update && apt-get install -y \
    vim \
    nano \
    htop \
    tree \
    && rm -rf /var/lib/apt/lists/*

# Install noVNC for web-based VNC access
RUN git clone https://github.com/novnc/noVNC.git /opt/novnc && \
    git clone https://github.com/novnc/websockify /opt/novnc/utils/websockify && \
    ln -s /opt/novnc/vnc.html /opt/novnc/index.html

USER staffclock

# Expose noVNC port
EXPOSE 6080

# --- Production Stage ---
FROM base as production

# Copy only necessary files for production
USER root

# Remove development packages to reduce size
RUN apt-get update && apt-get remove -y \
    build-essential \
    pkg-config \
    wget \
    curl \
    git \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

USER staffclock

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep -f "python.*main.py" || exit 1 