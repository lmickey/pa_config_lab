#!/bin/bash
# Stable GUI Launcher for Linux - Wayland Fallback
# Uses Wayland platform (second most stable option)

echo "Starting Prisma Access Configuration GUI (Linux Wayland Mode)..."
echo ""

# Apply Wayland Qt environment variables
export QT_QPA_PLATFORM=wayland              # Use Wayland backend
export QT_WAYLAND_DISABLE_WINDOWDECORATION=0
export QT_LOGGING_RULES="*.debug=false"

# Disable threaded rendering for safety
export QT_XCB_NO_THREADED_RENDERING=1

echo "Qt Platform: Wayland"
echo "Threaded Rendering: Disabled"
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the GUI
python3 run_gui.py

echo ""
echo "GUI closed."
