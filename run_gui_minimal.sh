#!/bin/bash
# Stable GUI Launcher for Linux - Minimal Platform
# Uses minimal platform (basic rendering, very stable)

echo "Starting Prisma Access Configuration GUI (Linux Minimal Mode)..."
echo ""

# Apply minimal Qt environment variables
export QT_QPA_PLATFORM=minimal              # Minimal platform (basic but stable)
export QT_LOGGING_RULES="*.debug=false"

echo "Qt Platform: Minimal (Basic Rendering)"
echo "Note: Limited visual features but very stable"
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the GUI
python3 run_gui.py

echo ""
echo "GUI closed."
