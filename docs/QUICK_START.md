# Quick Start Guide

**Prisma Access Configuration Capture Tool**

---

## Installation

### Step 1: Create a Project Directory

Choose a location for the project and create a directory:

```bash
# Linux/Mac
mkdir -p ~/Projects
cd ~/Projects

# Windows (Command Prompt)
mkdir C:\Projects
cd C:\Projects

# Windows (PowerShell)
New-Item -ItemType Directory -Path C:\Projects -Force
Set-Location C:\Projects
```

### Step 2: Clone the Repository

```bash
git clone https://github.com/lmickey/pa_config_lab.git
cd pa_config_lab
```

### Step 3: Create Virtual Environment

```bash
python3 -m venv venv
```

### Step 4: Activate Virtual Environment

**Linux/Mac:**
```bash
source venv/bin/activate
```

**Windows (Command Prompt):**
```cmd
venv\Scripts\activate
```

**Windows (PowerShell):**
```powershell
venv\Scripts\Activate.ps1
```

### Step 5: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 6: Run the GUI

```bash
python3 run_gui.py
```

---

## Quick Install (All-in-One)

### Linux/Mac
```bash
mkdir -p ~/Projects && cd ~/Projects
git clone https://github.com/lmickey/pa_config_lab.git
cd pa_config_lab
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python3 run_gui.py
```

### Windows (Command Prompt)
```cmd
mkdir C:\Projects
cd C:\Projects
git clone https://github.com/lmickey/pa_config_lab.git
cd pa_config_lab
python -m venv venv
venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
python run_gui.py
```

---

## Running the GUI (After Installation)

Each time you want to run the application:

### Linux/Mac
```bash
cd ~/Projects/pa_config_lab
source venv/bin/activate
python3 run_gui.py
```

### Windows
```cmd
cd C:\Projects\pa_config_lab
venv\Scripts\activate
python run_gui.py
```

---

## Common Issues

### "ModuleNotFoundError: No module named 'PyQt6'"
**Problem**: Dependencies not installed or virtual environment not activated.

**Solution**:
```bash
source venv/bin/activate  # Make sure venv is active
pip install -r requirements.txt
```

### PyQt6 crashes or won't start (Linux)
**Problem**: Missing system Qt libraries.

**Solution**: Install required system packages:
```bash
# Ubuntu/Debian
sudo apt-get install -y libxcb-xinerama0 libxkbcommon0 libgl1

# Fedora/RHEL
sudo dnf install libxkbcommon mesa-libGL
```

### "git: command not found"
**Problem**: Git is not installed.

**Solution**:
```bash
# Ubuntu/Debian
sudo apt-get install git

# Fedora/RHEL
sudo dnf install git

# Mac (using Homebrew)
brew install git

# Windows: Download from https://git-scm.com/download/win
```

### "python3: command not found"
**Problem**: Python is not installed or not in PATH.

**Solution**:
- **Linux**: `sudo apt-get install python3 python3-venv`
- **Mac**: `brew install python3` or download from python.org
- **Windows**: Download from https://www.python.org/downloads/

### GUI doesn't open / No window appears
**Problem**: No display available (common on SSH/headless systems).

**Solution**:
- Use X11 forwarding: `ssh -X user@host`
- Set DISPLAY variable: `export DISPLAY=:0`

---

## Features

### Pull (Capture Configuration)
- Capture security policies, objects, and profiles from Prisma Access
- Support for multiple folders and snippets
- Infrastructure capture (Remote Networks, Service Connections, etc.)

### Push (Deploy Configuration)
- Push captured configuration to same or different tenant
- Pre-push validation with dependency checking
- Conflict resolution (skip, overwrite, rename)

### Multi-Tenant Support
- Configure multiple tenant credentials
- Easy switching between tenants
- Cross-tenant migration support

---

## First Time Setup in GUI

1. **Configure Credentials**: Go to Settings tab and add your Prisma Access tenant credentials (TSG ID, Client ID, Client Secret)
2. **Test Connection**: Click "Test Connection" to verify credentials work
3. **Pull Configuration**: Go to Pull tab, select folders/snippets, and click Pull
4. **Review Results**: Check the Results panel for captured configuration

---

## Quick Links

- **Full Setup Guide**: [docs/SETUP.md](SETUP.md)
- **GUI User Guide**: [docs/GUI_USER_GUIDE.md](GUI_USER_GUIDE.md)
- **Infrastructure Guide**: [docs/INFRASTRUCTURE_CAPTURE_GUIDE.md](INFRASTRUCTURE_CAPTURE_GUIDE.md)
- **API Reference**: [docs/API_REFERENCE.md](API_REFERENCE.md)
- **Troubleshooting**: [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md)
