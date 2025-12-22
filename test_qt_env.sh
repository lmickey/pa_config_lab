#!/bin/bash
# Qt Environment Variable Test Script for Linux PyQt6 Stability
# Tests different Qt configurations to find stable settings

echo "=================================================="
echo "Qt Environment Variable Test for PyQt6 Stability"
echo "=================================================="
echo ""
echo "This script will test different Qt configurations."
echo "After each test, note if the GUI:"
echo "  ✅ Works without crashes"
echo "  ⚠️ Works but slower"
echo "  ❌ Still crashes"
echo ""
echo "Press Ctrl+C to stop any test that hangs."
echo ""

# Function to run test
run_test() {
    local test_name=$1
    shift
    local env_vars="$@"
    
    echo "=================================================="
    echo "TEST: $test_name"
    echo "=================================================="
    echo "Environment variables:"
    echo "$env_vars"
    echo ""
    echo "Starting GUI... (Press Ctrl+C to stop)"
    echo ""
    
    # Export the variables and run
    eval "$env_vars python3 run_gui.py"
    
    echo ""
    echo "Test ended. Did it work? (Enter to continue)"
    read
    echo ""
}

# Test 1: Baseline (Current - likely crashes)
echo "TEST 0: Baseline (No environment variables)"
echo "This will probably crash. Just verify it crashes so we have a baseline."
echo "Press Enter to start..."
read
python3 run_gui.py
echo ""
echo "Baseline test complete. Did it crash? (Enter to continue)"
read
echo ""

# Test 1: Force XCB Platform
run_test "Force XCB Platform (Most Likely Fix)" \
    "QT_QPA_PLATFORM=xcb"

# Test 2: Disable GPU Acceleration
run_test "Disable GPU Acceleration" \
    "QT_XCB_GL_INTEGRATION=none QT_QUICK_BACKEND=software"

# Test 3: Force Software OpenGL
run_test "Force Software OpenGL" \
    "LIBGL_ALWAYS_SOFTWARE=1 QT_XCB_GL_INTEGRATION=none"

# Test 4: Disable Threaded Rendering
run_test "Disable Threaded Rendering" \
    "QT_XCB_NO_THREADED_RENDERING=1"

# Test 5: XCB + No Threaded Rendering
run_test "XCB + No Threaded Rendering" \
    "QT_QPA_PLATFORM=xcb QT_XCB_NO_THREADED_RENDERING=1"

# Test 6: Nuclear Option (All combined)
run_test "Nuclear Option (All Combined - Slowest but Most Stable)" \
    "QT_QPA_PLATFORM=xcb QT_XCB_GL_INTEGRATION=none LIBGL_ALWAYS_SOFTWARE=1 QT_QUICK_BACKEND=software QT_XCB_NO_THREADED_RENDERING=1"

echo "=================================================="
echo "All tests complete!"
echo "=================================================="
echo ""
echo "Which test worked best?"
echo "1. If any test worked, note the environment variables"
echo "2. Add those to run_gui.sh permanently"
echo "3. Or create a wrapper script"
echo ""
echo "Recommended: If Test 1 (XCB) worked, use that."
echo "It's the fastest while being stable."
echo ""
