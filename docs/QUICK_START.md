# Quick Start Guide

**Prisma Access Configuration Capture Tool**

---

## Quick Install

```bash
# Clone repository
git clone https://github.com/lmickey/pa_config_lab.git
cd pa_config_lab

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run the GUI
python3 run_gui.py
```

## Running the GUI

### Linux/Mac
```bash
source venv/bin/activate
python3 run_gui.py
```

### Windows
```cmd
venv\Scripts\activate
python run_gui.py
```

---

## Common Issues

### "ModuleNotFoundError: No module named 'PyQt6'"
**Problem**: Dependencies not installed.

**Solution**:
```bash
source venv/bin/activate
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

### "No such file or directory" or "venv not found"
**Problem**: Virtual environment not set up.

**Solution**:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

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

## Quick Links

- **Full Setup Guide**: [docs/SETUP.md](SETUP.md)
- **GUI User Guide**: [docs/GUI_USER_GUIDE.md](GUI_USER_GUIDE.md)
- **Infrastructure Guide**: [docs/INFRASTRUCTURE_CAPTURE_GUIDE.md](INFRASTRUCTURE_CAPTURE_GUIDE.md)
- **API Reference**: [docs/API_REFERENCE.md](API_REFERENCE.md)
- **Troubleshooting**: [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md)
