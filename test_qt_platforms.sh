#!/bin/bash
# GUI Platform Test - Quick Sequential Test
# Tests Wayland, Offscreen, and Minimal platforms

echo "=========================================="
echo "Qt Platform Quick Test"
echo "=========================================="
echo ""

# Test 1: Wayland
echo "TEST 1: Wayland Platform"
echo "=========================================="
export QT_QPA_PLATFORM=wayland
export QT_LOGGING_RULES="*.debug=false"
echo "Running with Wayland..."
timeout 5s python3 -c "
from PyQt6.QtWidgets import QApplication
import sys
app = QApplication(sys.argv)
print('✅ Wayland: Qt initialized successfully')
app.quit()
" 2>&1
WAYLAND_RESULT=$?
echo ""

# Test 2: Offscreen
echo "TEST 2: Offscreen Platform"
echo "=========================================="
export QT_QPA_PLATFORM=offscreen
echo "Running with Offscreen..."
timeout 5s python3 -c "
from PyQt6.QtWidgets import QApplication
import sys
app = QApplication(sys.argv)
print('✅ Offscreen: Qt initialized successfully')
app.quit()
" 2>&1
OFFSCREEN_RESULT=$?
echo ""

# Test 3: Minimal
echo "TEST 3: Minimal Platform"
echo "=========================================="
export QT_QPA_PLATFORM=minimal
echo "Running with Minimal..."
timeout 5s python3 -c "
from PyQt6.QtWidgets import QApplication
import sys
app = QApplication(sys.argv)
print('✅ Minimal: Qt initialized successfully')
app.quit()
" 2>&1
MINIMAL_RESULT=$?
echo ""

# Summary
echo "=========================================="
echo "RESULTS SUMMARY"
echo "=========================================="
[ $WAYLAND_RESULT -eq 0 ] && echo "✅ Wayland: WORKS" || echo "❌ Wayland: FAILED"
[ $OFFSCREEN_RESULT -eq 0 ] && echo "✅ Offscreen: WORKS" || echo "❌ Offscreen: FAILED"
[ $MINIMAL_RESULT -eq 0 ] && echo "✅ Minimal: WORKS" || echo "❌ Minimal: FAILED"
echo ""

# Recommendation
if [ $WAYLAND_RESULT -eq 0 ]; then
    echo "✅ RECOMMENDATION: Use Wayland"
    echo "   Run: ./run_gui_wayland.sh"
elif [ $OFFSCREEN_RESULT -eq 0 ]; then
    echo "✅ RECOMMENDATION: Use Offscreen"
    echo "   Run: ./run_gui_offscreen.sh"
elif [ $MINIMAL_RESULT -eq 0 ]; then
    echo "✅ RECOMMENDATION: Use Minimal"
    echo "   Run: ./run_gui_minimal.sh"
else
    echo "❌ NO WORKING PLATFORM FOUND"
    echo "   Recommendation: Use CLI instead"
    echo "   Run: python3 -m cli.pull_cli --help"
fi
