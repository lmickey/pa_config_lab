#!/usr/bin/env python3
"""
Debug wrapper for GUI - catches crashes and provides detailed error info.

Usage:
    python3 run_gui_debug.py
    
This wrapper:
- Enables all Python warnings
- Catches segfaults with faulthandler
- Logs all exceptions
- Provides stack traces
"""

import sys
import os
import faulthandler
import warnings
import traceback
import signal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Enable fault handler to catch segfaults
faulthandler.enable(file=sys.stderr, all_threads=True)

# Enable all warnings
warnings.filterwarnings('default')

# Set up crash log
crash_log = open('logs/gui_crashes.log', 'a')
crash_log.write('\n' + '='*80 + '\n')
crash_log.write(f'GUI Debug Session Started\n')
crash_log.write('='*80 + '\n')

def signal_handler(signum, frame):
    """Handle termination signals."""
    crash_log.write(f'\nReceived signal {signum}\n')
    crash_log.write('Stack trace:\n')
    traceback.print_stack(frame, file=crash_log)
    crash_log.flush()
    sys.exit(1)

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
if hasattr(signal, 'SIGQUIT'):
    signal.signal(signal.SIGQUIT, signal_handler)

# Enable faulthandler to file
faulthandler.enable(file=crash_log, all_threads=True)

print("="*80)
print("GUI Debug Mode Enabled")
print("="*80)
print("• Fault handler active (catches segfaults)")
print("• All warnings enabled")
print("• Crash log: logs/gui_crashes.log")
print("• Activity log: logs/activity.log")
print("="*80)
print()

try:
    # Import and run GUI
    from gui.main_window import main
    
    print("Starting GUI...")
    exit_code = main()
    sys.exit(exit_code if exit_code else 0)
    
except Exception as e:
    print("\n" + "="*80)
    print("UNCAUGHT EXCEPTION")
    print("="*80)
    traceback.print_exc()
    
    # Log to crash file
    crash_log.write('\n\nUncaught Exception:\n')
    crash_log.write(traceback.format_exc())
    crash_log.flush()
    
    sys.exit(1)
    
finally:
    crash_log.close()
