#!/bin/bash
# Stable GUI Launcher for Linux - Offscreen Mode
# Uses offscreen rendering (no display acceleration - most stable)

echo "Starting Prisma Access Configuration GUI (Linux Offscreen Mode)..."
echo ""

# Apply offscreen Qt environment variables
export QT_QPA_PLATFORM=offscreen            # Offscreen rendering (CPU only)
export QT_LOGGING_RULES="*.debug=false"

echo "Qt Platform: Offscreen (Software Rendering)"
echo "Note: This mode is slower but extremely stable"
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the GUI
python3 run_gui.py

echo ""
echo "GUI closed."
