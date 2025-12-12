#!/bin/bash
# Run the GUI application with virtual environment

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "Error: Virtual environment not found. Please run: python3 -m venv venv"
    exit 1
fi

# Run the GUI
python3 pa_config_gui.py

# Deactivate virtual environment when done
deactivate
