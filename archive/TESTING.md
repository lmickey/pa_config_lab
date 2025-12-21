# Testing the GUI Application

## Quick Start

### Linux/Mac
```bash
chmod +x run_gui.sh
./run_gui.sh
```

### Windows
```cmd
run_gui.bat
```

### Manual Activation

#### Linux/Mac
```bash
source venv/bin/activate
python3 pa_config_gui.py
deactivate
```

#### Windows
```cmd
venv\Scripts\activate
python pa_config_gui.py
deactivate
```

## Testing Checklist

### Basic Functionality
- [ ] GUI launches without errors
- [ ] All fields are visible
- [ ] Can type in all fields
- [ ] Copy button (📋) works for each field
- [ ] Right-click context menu appears
- [ ] Keyboard shortcuts work (Ctrl+C, Ctrl+V, etc.)

### Configuration Management
- [ ] "New Configuration" clears all fields
- [ ] "Load Configuration" opens file browser
- [ ] Can load an existing config file (if you have one)
- [ ] Fields populate correctly after loading
- [ ] "Save Configuration" saves to file
- [ ] "Print Settings" displays current values

### UI Features
- [ ] Window can be resized
- [ ] Scrollbar works when content exceeds window
- [ ] Menu bar is functional
- [ ] Status bar shows current operation
- [ ] Output log area displays messages

### Copy/Paste
- [ ] Copy button copies field value
- [ ] Right-click Copy works
- [ ] Right-click Paste works
- [ ] Ctrl+C copies selected text
- [ ] Ctrl+V pastes into focused field

### Password Fields
- [ ] Password fields show asterisks by default
- [ ] "Show/Hide Passwords" menu item works
- [ ] Password visibility toggles correctly

## Test Scenarios

### Scenario 1: Create New Configuration
1. Launch GUI
2. Click "File" → "New Configuration"
3. Enter a config name
4. Fill in some firewall fields
5. Fill in some Prisma Access fields
6. Click "File" → "Save Configuration"
7. Enter encryption password
8. Verify file is created

### Scenario 2: Load Existing Configuration
1. Launch GUI
2. Click "File" → "Load Configuration"
3. Select a `*-fwdata.bin` file
4. Enter encryption password
5. Verify all fields populate correctly
6. Modify some values
7. Save configuration

### Scenario 3: Copy/Paste
1. Enter a value in "Management URL" field
2. Click the 📋 button next to it
3. Click in "Untrust URL" field
4. Right-click → Paste
5. Verify value was pasted

### Scenario 4: Print Settings
1. Fill in some configuration values
2. Click "Tools" → "Print Settings"
3. Verify output appears in status area
4. Verify passwords are masked

## Known Issues to Watch For

1. **Load Config**: May need an existing config file to test fully
2. **Save Config**: May prompt for overwrite confirmation (this is expected)
3. **Password Toggle**: Should work but may need visual feedback improvement

## Troubleshooting

### GUI doesn't launch
- Check Python version: `python3 --version` (should be 3.x)
- Verify tkinter is available: `python3 -c "import tkinter; print('OK')"`
- Check virtual environment is activated

### Import errors
- Make sure `load_settings.py` and `get_settings.py` are in the same directory
- Verify virtual environment has all dependencies: `pip list`

### File not found errors
- Make sure you're running from the project directory
- Check that config files exist if trying to load

## Next Steps After Testing

Once basic testing is complete, we can proceed to:
- Phase 2: Enhanced configuration management
- Phase 3: Data integration and validation
- Phase 4: Operation integration
