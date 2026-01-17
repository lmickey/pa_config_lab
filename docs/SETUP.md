# Setup Guide

## Prerequisites

### Python Version
```bash
python3 --version
```
Python 3.9 or higher is required.

### System Dependencies (Linux)

PyQt6 requires certain system libraries. On Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install -y libxcb-xinerama0 libxkbcommon0 libgl1
```

On Fedora/RHEL:
```bash
sudo dnf install libxkbcommon mesa-libGL
```

## Installation Steps

### Step 1: Clone the Repository
```bash
git clone https://github.com/lmickey/pa_config_lab.git
cd pa_config_lab
```

### Step 2: Create Virtual Environment
```bash
python3 -m venv venv
```

### Step 3: Activate Virtual Environment

**Linux/Mac:**
```bash
source venv/bin/activate
```

**Windows:**
```cmd
venv\Scripts\activate
```

### Step 4: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 5: Run the GUI
```bash
python3 run_gui.py
```

## Troubleshooting

### PyQt6 Import Errors
If you see errors about PyQt6 or Qt libraries:

1. **Linux**: Install system Qt dependencies:
   ```bash
   sudo apt-get install -y libxcb-xinerama0 libxkbcommon0 libgl1
   ```

2. **Try reinstalling PyQt6**:
   ```bash
   pip uninstall PyQt6 PyQt6-Qt6 PyQt6-sip
   pip install PyQt6
   ```

### "No module named 'gui'" Error
Make sure you're running from the project root directory:
```bash
cd /path/to/pa_config_lab
python3 run_gui.py
```

### Virtual Environment Issues
If activation fails, recreate the environment:
```bash
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Display Issues (Headless/SSH)
For remote sessions, use X11 forwarding:
```bash
ssh -X user@host
export DISPLAY=:0
python3 run_gui.py
```

## Verifying Installation

Run a quick test to verify the API client works:
```bash
python3 -c "from prisma.api_client import PrismaAccessAPIClient; print('OK')"
```

## Next Steps

Once the GUI launches:
1. Configure tenant credentials in Settings
2. Test Pull functionality to capture configuration
3. Review captured data in the Results panel
