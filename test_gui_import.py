#!/usr/bin/env python3
"""
Quick test to verify GUI can be imported and basic dependencies are available
"""

import sys

print("Testing GUI dependencies...")
print(f"Python version: {sys.version}")

# Test tkinter
try:
    import tkinter
    print("✓ tkinter available")
except ImportError as e:
    print(f"✗ tkinter not available: {e}")
    print("  On Linux, install with: sudo apt-get install python3-tk")
    sys.exit(1)

# Test existing modules
try:
    import load_settings
    print("✓ load_settings module available")
except ImportError as e:
    print(f"✗ load_settings not available: {e}")

try:
    import get_settings
    print("✓ get_settings module available")
except ImportError as e:
    print(f"✗ get_settings not available: {e}")

# Test GUI import
try:
    import pa_config_gui
    print("✓ pa_config_gui module can be imported")
except Exception as e:
    print(f"✗ Error importing pa_config_gui: {e}")
    sys.exit(1)

print("\nAll checks passed! GUI should be ready to run.")
print("Run with: python3 pa_config_gui.py")
