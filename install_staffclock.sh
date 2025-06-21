#!/bin/bash

# Check for python3
if ! command -v python3 &> /dev/null
then
    echo "python3 could not be found, please install it."
    exit
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment and install dependencies
echo "Installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt

echo "Installation complete. You can now run the application using run_staffclock.sh" 