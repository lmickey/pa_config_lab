# Quick Start Guide

**Prisma Access Configuration Capture Tool v2.0**

---

## What's New in v2.0

✅ **Infrastructure Capture** - Remote Networks, Service Connections, IPsec/IKE, Mobile Users, HIP, Regions  
✅ **Custom Applications** - Option to capture custom/user-created applications  
✅ **Enhanced GUI** - 6 new infrastructure options + application selector  
✅ **Rate Limiting** - 45 req/min (90% of API limit) for safe operation  
✅ **Comprehensive Testing** - 300+ test cases for reliability

---

## Running the GUI

### Linux/Mac
```bash
# Make sure script is executable
chmod +x run_gui.sh

# Run the GUI
./run_gui.sh
```

**OR** run directly with bash:
```bash
bash run_gui.sh
```

### Windows
```cmd
run_gui.bat
```

### Manual Method (if scripts don't work)

**Linux/Mac:**
```bash
source venv/bin/activate
python3 pa_config_gui.py
```

**Windows:**
```cmd
venv\Scripts\activate
python pa_config_gui.py
```

## Common Issues

### "SyntaxError" when running run_gui.sh
**Problem**: You're running the script with Python instead of bash.

**Solution**: Use one of these methods:
```bash
# Method 1: Make executable and run directly
chmod +x run_gui.sh
./run_gui.sh

# Method 2: Run with bash explicitly
bash run_gui.sh

# Method 3: Use sh
sh run_gui.sh
```

**DO NOT** run it like this:
```bash
python3 run_gui.sh  # ❌ WRONG - This is a bash script, not Python!
```

### "No such file or directory" or "venv/bin/activate: No such file"
**Problem**: Virtual environment not set up.

**Solution**: 
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### "ModuleNotFoundError: No module named 'tkinter'"
**Problem**: tkinter not installed.

**Solution**: Install python3-tk package:
```bash
# Linux (Ubuntu/Debian)
sudo apt-get install python3-tk

# Linux (Fedora/RHEL)
sudo dnf install python3-tkinter
```

### GUI doesn't open / No window appears
**Problem**: No display available (common on SSH/headless systems).

**Solution**: 
- Set DISPLAY variable: `export DISPLAY=:0`
- Use X11 forwarding: `ssh -X user@host`
- Or use CLI scripts instead

## Testing the Setup

Run this to verify everything is set up:
```bash
python3 test_gui_import.py
```

If all checks pass, you're ready to run the GUI!

---

## New Features Guide

### Infrastructure Capture

The GUI now includes 6 infrastructure component options:

1. **Remote Networks** - Branch offices and data centers
2. **Service Connections** - On-premises connectivity  
3. **IPsec Tunnels & Crypto** - VPN infrastructure
4. **Mobile User Infrastructure** - GlobalProtect gateways/portals
5. **HIP Objects & Profiles** - Endpoint compliance checks
6. **Regions & Bandwidth** - Deployment locations

**To use:**
1. Go to "Pull" tab
2. Scroll to "Infrastructure Components" section
3. All are checked by default
4. Uncheck any you don't need

### Custom Applications

**NEW:** Option to capture custom/user-created applications.

**To use:**
1. Check "Custom Applications" in Pull tab
2. Click "Select Applications..." button
3. Enter app names (comma-separated): `App1, App2, App3`

**Note:** Only needed for custom apps. Predefined applications are automatically included.

---

## Quick Links

- **📖 Full Documentation:** See [docs/README.md](docs/README.md)
- **🏗️ Infrastructure Guide:** See [docs/INFRASTRUCTURE_CAPTURE_GUIDE.md](docs/INFRASTRUCTURE_CAPTURE_GUIDE.md)
- **🔧 API Reference:** See [docs/API_REFERENCE_INFRASTRUCTURE.md](docs/API_REFERENCE_INFRASTRUCTURE.md)
- **❓ Troubleshooting:** See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
