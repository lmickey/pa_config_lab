# Quick Testing Guide - Phases 9.5, 10, 11

**Run this to test the new features!**

---

## Launch GUI

```bash
cd /home/lindsay/Code/pa_config_lab
python3 gui/main_window.py
```

---

## Test 1: Log Level Settings ✅

1. Click **Tools** → **Settings**
2. Go to **Advanced** tab
3. Find **Log Level** dropdown - should show 5 levels:
   - Error - Fewest entries
   - Warning - Recoverable issues
   - **Normal - Summary operations** (default)
   - Info - Detailed steps
   - Debug - Everything (troubleshooting)
4. Try changing to **INFO** or **DEBUG**
5. Click **Save**
6. Check logs widget - should show more detail

**Expected:** Log level changes immediately, settings persist

---

## Test 2: Configuration Save/Load ✅

### Pull and Save:
1. Do a configuration pull (however you normally do it)
2. Click **File** → **Save Configuration** (Ctrl+S)
3. Choose location, name it `test_config.json`
4. Click Save
5. Verify file created in chosen location

### Load Configuration:
1. Click **File** → **Load Configuration** (Ctrl+O)
2. Select the `test_config.json` file
3. Should show success message with item counts

**Expected:** Configuration saves/loads without errors

---

## Test 3: Configuration Info ✅

1. After loading or pulling a configuration
2. Click **File** → **Configuration Info** (Ctrl+I)
3. Should display:
   - Source TSG
   - Created/Modified dates
   - Total items count
   - Folders/Snippets/Infrastructure counts
   - Top item types

**Expected:** All metadata displays correctly

---

## Test 4: Compression ✅

1. Pull or load a configuration
2. Click **File** → **Save Configuration**
3. Name it `test_config.json.gz` (add .gz extension)
4. Save
5. Check file size - should be 5-20x smaller than .json

**Expected:** Compressed file much smaller, loads correctly

---

## Test 5: Log Rotation ✅

1. Check for `logs/activity.log` file
2. Restart the application
3. Check for `logs/activity-1.log` (previous run)
4. Verify `logs/activity.log` is new

**Expected:** Logs rotate on each startup

---

## Test 6: Keyboard Shortcuts ✅

Try these shortcuts:
- **Ctrl+O** - Load Configuration
- **Ctrl+S** - Save Configuration
- **Ctrl+Shift+S** - Save As
- **Ctrl+I** - Configuration Info
- **Ctrl+T** - Manage Tenants
- **F1** - Documentation
- **Ctrl+Q** - Exit

**Expected:** All shortcuts work

---

## What to Look For

### ✅ Good Signs:
- Settings dialog shows 5 log levels
- File menu has Load/Save/Info actions
- Configuration saves as .json or .json.gz
- Metadata displays in Info dialog
- Logs show appropriate detail per level
- activity.log rotates on restart

### ❌ Issues to Report:
- Errors when saving/loading
- Missing menu items
- Keyboard shortcuts not working
- Settings not persisting
- Log files not rotating

---

## Quick Commands

### Check Logs:
```bash
# View current log
tail -f /home/lindsay/Code/pa_config_lab/logs/activity.log

# View rotated logs
ls -lh /home/lindsay/Code/pa_config_lab/logs/activity*.log
```

### Check Saved Configs:
```bash
# List saved configurations
ls -lh test_config.*

# View config file
cat test_config.json | head -50

# Check compressed size
ls -lh test_config.json*
```

### Test Log Levels (CLI):
```bash
# Test with different log levels
cd /home/lindsay/Code/pa_config_lab
export PYTHONPATH=/home/lindsay/Code/pa_config_lab:$PYTHONPATH

# Run with INFO level
python3 -c "
from config.logging_config import setup_logging, NORMAL
import logging
setup_logging(level=logging.INFO)
logging.getLogger().info('INFO level test')
logging.getLogger().debug('DEBUG level test - should not appear')
"
```

---

## Expected Results

### Settings Dialog:
- 5-level dropdown visible
- Default: NORMAL
- Rotation: 7 files
- Age: 30 days

### File Menu:
- 4 new items: Load, Save, Save As, Info
- All have shortcuts
- All work correctly

### Configuration Operations:
- Save creates valid JSON
- Load recreates Configuration object
- Compression works (5-20x)
- Metadata preserved

### Logging:
- NORMAL: Clean summaries
- INFO: Detailed steps
- DEBUG: Everything including raw data
- Rotation: activity.log → activity-1.log → ...

---

## Success Criteria

### All Features Working:
- ✅ Can change log level in GUI
- ✅ Can save configuration to file
- ✅ Can load configuration from file
- ✅ Can view configuration metadata
- ✅ Compression works
- ✅ Settings persist
- ✅ Logs rotate
- ✅ Keyboard shortcuts work

**If all ✅ above, session is a complete success!** 🎉

---

## Report Issues

If you encounter any issues, please note:
1. What you were doing
2. Error message (if any)
3. Expected behavior
4. Log level setting
5. File being saved/loaded

---

**Ready to test! Launch the GUI and try all the new features!** 🚀

```bash
cd /home/lindsay/Code/pa_config_lab && python3 gui/main_window.py
```
