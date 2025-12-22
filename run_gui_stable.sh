#!/bin/bash
# Stable GUI Launcher for Linux with Qt Environment Variables
# This uses the most likely stable Qt configuration

echo "Starting Prisma Access Configuration GUI (Linux Stable Mode)..."
echo ""

# Apply stable Qt environment variables
export QT_QPA_PLATFORM=xcb                    # Use X11 backend (most stable)
export QT_XCB_NO_THREADED_RENDERING=1         # Disable threaded rendering
export QT_LOGGING_RULES="*.debug=false"       # Reduce log noise

# Optional: Uncomment if still having issues
# export QT_XCB_GL_INTEGRATION=none           # Disable GPU acceleration
# export LIBGL_ALWAYS_SOFTWARE=1              # Force software rendering
# export QT_QUICK_BACKEND=software            # Software backend

echo "Qt Platform: XCB (X11)"
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
