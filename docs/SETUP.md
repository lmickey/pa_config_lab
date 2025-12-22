# Setup Guide for GUI Testing

## Prerequisites

### 1. Install tkinter (Required for GUI)

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install python3-tk
```

#### Linux (Fedora/RHEL/CentOS)
```bash
sudo dnf install python3-tkinter
# or
sudo yum install python3-tkinter
```

#### Mac
tkinter should be included with Python. If not:
```bash
brew install python-tk
```

#### Windows
tkinter is included with Python installations. If missing, reinstall Python and select "tcl/tk and IDLE" option.

### 2. Verify Python Version
```bash
python3 --version
```
Should be Python 3.7 or higher.

## Setup Steps

### Step 1: Create Virtual Environment (Already Done)
```bash
python3 -m venv venv
```

### Step 2: Activate Virtual Environment

**Linux/Mac:**
```bash
source venv/bin/activate
```

**Windows:**
```cmd
venv\Scripts\activate
```

### Step 3: Install Dependencies (Already Done)
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Verify Setup
```bash
python3 test_gui_import.py
```

This will check if all dependencies are available.

### Step 5: Run the GUI

**Option 1: Use the run script**
```bash
# Linux/Mac
./run_gui.sh

# Windows
run_gui.bat
```

**Option 2: Manual activation**
```bash
# Linux/Mac
source venv/bin/activate
python3 pa_config_gui.py

# Windows
venv\Scripts\activate
python pa_config_gui.py
```

## Troubleshooting

### tkinter Not Found
If you see `ModuleNotFoundError: No module named 'tkinter'`:

1. **Linux**: Install python3-tk package (see above)
2. **Mac**: May need to install via Homebrew or reinstall Python
3. **Windows**: Reinstall Python with tkinter option

### Import Errors for load_settings/get_settings
- Make sure you're running from the project directory
- Verify `load_settings.py` and `get_settings.py` are in the same directory as `pa_config_gui.py`

### Virtual Environment Issues
- Make sure venv is activated (you should see `(venv)` in your prompt)
- If activation fails, recreate: `rm -rf venv && python3 -m venv venv`

## Quick Test

After installing tkinter, run:
```bash
python3 test_gui_import.py
```

If all checks pass, you're ready to run the GUI!

## Next Steps

Once the GUI launches successfully:
1. Test basic functionality (see TESTING.md)
2. Try creating a new configuration
3. Test copy/paste functionality
4. Test loading/saving configurations
