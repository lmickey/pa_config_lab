# Troubleshooting GUI Issues

## Issue: GUI Doesn't Open / No Window Appears

### On Linux (Headless/SSH)

If you're running on a Linux system without a display (like SSH), tkinter needs a display server:

1. **Check if DISPLAY is set:**
   ```bash
   echo $DISPLAY
   ```

2. **If not set and you have X11 forwarding:**
   ```bash
   export DISPLAY=:0
   # or for X11 forwarding:
   export DISPLAY=localhost:10.0
   ```

3. **For remote SSH with X11 forwarding:**
   ```bash
   ssh -X user@host
   # Then run:
   python3 pa_config_gui.py
   ```

4. **If you don't have a display, you can't run GUI applications.**
   - Use the CLI scripts instead (`get_settings.py`, etc.)
   - Or use VNC/X11 forwarding
   - Or run on a system with a desktop environment

### Check if tkinter works:

```bash
python3 -c "import tkinter as tk; root = tk.Tk(); root.title('Test'); root.geometry('200x100'); tk.Label(root, text='Test').pack(); root.mainloop()"
```

If this doesn't show a window, tkinter can't access a display.

## Issue: Import Errors

### "ModuleNotFoundError: No module named 'tkinter'"

**Linux:**
```bash
sudo apt-get install python3-tk
# or
sudo dnf install python3-tkinter
```

**Mac:**
```bash
brew install python-tk
```

**Windows:** Reinstall Python with tkinter option selected.

### "ModuleNotFoundError: No module named 'load_settings'"

- Make sure you're in the project directory
- Verify `load_settings.py` exists in the same directory as `pa_config_gui.py`

## Issue: get_settings.py Still Runs CLI When Imported

This was fixed! The CLI code is now wrapped in `if __name__ == "__main__":` so it only runs when executed directly, not when imported.

Verify with:
```bash
python3 -c "import get_settings; print('OK')"
```

If you see prompts, the fix didn't work. Check that `get_settings.py` has the `if __name__ == "__main__":` guard.

## Testing Without Display

If you can't test the GUI visually, you can at least verify:

1. **Imports work:**
   ```bash
   python3 test_gui_import.py
   ```

2. **No syntax errors:**
   ```bash
   python3 -m py_compile pa_config_gui.py
   ```

3. **GUI class can be instantiated (but won't show window):**
   ```bash
   python3 -c "import pa_config_gui; import tkinter as tk; root = tk.Tk(); app = pa_config_gui.PAConfigGUI(root); print('GUI created successfully'); root.destroy()"
   ```

## Common Solutions

1. **Install tkinter** (see above)
2. **Set DISPLAY variable** (Linux with X11)
3. **Use X11 forwarding** for SSH
4. **Run on a system with desktop environment**
5. **Use VNC** if you have remote access

## Still Having Issues?

Check:
- Python version: `python3 --version` (should be 3.7+)
- Virtual environment activated: `which python3` should show venv path
- Dependencies installed: `pip list | grep pan-os-python`
- File permissions: `ls -la pa_config_gui.py`
