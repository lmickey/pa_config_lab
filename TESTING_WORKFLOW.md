# GUI Testing Workflow

## Quick Test Procedure

### Option 1: Debug Mode (Recommended for Testing)
```bash
cd /home/lindsay/Code/pa_config_lab
python3 run_gui_debug.py
```

**Benefits:**
- Catches segfaults with stack traces
- Logs crashes to `logs/gui_crashes.log`
- Shows all warnings
- Better error messages

### Option 2: Normal Mode
```bash
cd /home/lindsay/Code/pa_config_lab
./run_gui.py
```

## Test Scenario: Config Pull

1. **Start GUI** (using debug mode)
   ```bash
   python3 run_gui_debug.py
   ```

2. **Connect to Tenant**
   - Click tenant dropdown
   - Select "SCM Lab"
   - Wait for connection confirmation

3. **Open Pull Configuration**
   - Go to "Configuration Migration" tab
   - Click "Pull Configuration" button

4. **Configure Pull Options**
   - ✅ Check "Ignore default configurations"
   - ✅ Select all component types
   - Click "Start Pull"

5. **Monitor Progress**
   - Watch progress bar
   - Check for errors in results panel
   - Wait for completion message

6. **Check Logs if Crash Occurs**
   ```bash
   # Check activity log (normal operations)
   tail -100 logs/activity.log
   
   # Check crash log (segfaults/exceptions)
   tail -100 logs/gui_crashes.log
   
   # Check for core dumps
   ls -la core* 2>/dev/null
   ```

## Common Issues & Quick Checks

### Issue: Segfault During Pull

**Quick Check:**
```bash
# Last 50 lines of activity log
tail -50 logs/activity.log

# Crash log
cat logs/gui_crashes.log
```

**What to look for:**
- Last API call before crash
- Memory allocation patterns
- Thread activity

### Issue: GUI Won't Start

**Quick Check:**
```bash
# Try importing in Python
python3 -c "from gui.main_window import main; print('Import OK')"

# Check for syntax errors
python3 -m py_compile gui/main_window.py
```

### Issue: Pull Hangs

**Quick Check:**
```bash
# Check if process is alive
ps aux | grep run_gui

# Check thread activity
cat logs/activity.log | grep -i "thread\|worker\|pull"
```

## Log Analysis Commands

### Find Last Error
```bash
grep -i "error\|exception\|traceback" logs/activity.log | tail -20
```

### Find Memory Issues
```bash
grep -i "free\|corruption\|malloc\|memory" logs/gui_crashes.log
```

### Find Threading Issues
```bash
grep -i "thread\|timer\|signal" logs/activity.log | tail -30
```

### Count API Calls
```bash
grep "API GET request" logs/activity.log | wc -l
```

### Show Pull Progress
```bash
grep "Processing folder\|Processing snippet" logs/activity.log
```

## Automated Testing Script

Create `test_pull.sh`:
```bash
#!/bin/bash

echo "Starting automated pull test..."

# Clean logs
rm -f logs/gui_crashes.log
echo "Cleaned crash log"

# Start GUI in background (you'll need to interact with it)
python3 run_gui_debug.py &
GUI_PID=$!
echo "GUI started (PID: $GUI_PID)"

# Wait for user to perform test
echo ""
echo "Perform your test in the GUI window, then close it."
echo "Logs will be analyzed automatically."
echo ""

# Wait for GUI to exit
wait $GUI_PID
EXIT_CODE=$?

echo ""
echo "GUI exited with code: $EXIT_CODE"
echo ""

# Analyze logs
echo "=== Log Analysis ==="
echo ""

if [ -f logs/gui_crashes.log ]; then
    echo "CRASH LOG FOUND:"
    tail -50 logs/gui_crashes.log
else
    echo "No crash log (good sign)"
fi

echo ""
echo "Last 20 activity log entries:"
tail -20 logs/activity.log

echo ""
echo "Errors in activity log:"
grep -i "error" logs/activity.log | tail -10 || echo "No errors found"

echo ""
echo "=== Test Complete ==="
```

## Current Status After Fixes

### ✅ Fixed Issues
1. Deep copy causing double-free
2. QTimer cross-thread access
3. Print statements in workers
4. Worker cleanup
5. Memory management

### 🧪 Test These Scenarios

1. **Small Pull** (should work)
   - Uncheck all except "Security Rules"
   - Pull from 1 folder only

2. **Medium Pull** (test stability)
   - Check "Ignore defaults"
   - Pull all types from 1 folder

3. **Full Pull** (stress test)
   - Check "Ignore defaults"
   - Pull everything

## If You Still Get a Crash

**Provide these 3 things:**

1. **Last 50 lines of activity.log:**
   ```bash
   tail -50 logs/activity.log
   ```

2. **Crash log:**
   ```bash
   cat logs/gui_crashes.log
   ```

3. **What you were doing:**
   - Clicked "Pull Configuration"
   - Selected tenant "X"
   - Checked options: [list]
   - Crash happened at: [describe]

## Quick Recovery

If GUI crashes and won't restart:
```bash
# Kill any stuck processes
pkill -9 -f run_gui

# Clean Qt cache
rm -rf ~/.cache/QtProject

# Remove lock files
rm -f /tmp/prisma-access-*.lock

# Restart
python3 run_gui_debug.py
```

## Success Indicators

✅ Pull completes without crash
✅ Activity log shows all API calls
✅ No entries in gui_crashes.log
✅ Configuration loads in viewer
✅ Memory usage stays reasonable (<500MB)

---

**Remember:** Run `python3 run_gui_debug.py` for better crash diagnostics!
