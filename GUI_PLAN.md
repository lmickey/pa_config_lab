# GUI Implementation Plan for Palo Alto Configuration Lab

## Overview
This document outlines the plan to add a cross-platform GUI (Mac/Windows) to the Palo Alto Networks Configuration Lab tool. The GUI will consolidate all functionality into a single Python application with optional separate include files.

## Technology Stack

### GUI Framework: **tkinter**
- **Rationale**: Built into Python, works on Mac/Windows/Linux without additional dependencies
- **Alternative considered**: PyQt5/PySide2 (requires separate installation, larger footprint)
- **Pros**: Zero dependencies, native look, sufficient for this use case
- **Cons**: Less modern than Qt, but adequate for configuration tools

### Architecture: Single-file with optional modules
- **Main file**: `pa_config_gui.py` - Main GUI application
- **Optional modules**: 
  - `gui_config_manager.py` - Configuration file management (encryption/decryption)
  - `gui_firewall_ops.py` - Firewall operations wrapper
  - `gui_prisma_ops.py` - Prisma Access operations wrapper

## GUI Structure & Layout

### Main Window Components

```
┌─────────────────────────────────────────────────────────────┐
│  Palo Alto Configuration Lab                    [Min][Max][X]│
├─────────────────────────────────────────────────────────────┤
│  File Menu: [New Config] [Load Config] [Save Config] [Exit] │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────┐  ┌──────────────────────────────┐ │
│  │  Configuration Name   │  │  Encryption Password: [****] │ │
│  │  [_____________]     │  │  [Change Password]          │ │
│  └──────────────────────┘  └──────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Firewall Configuration                                  │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │  Management URL:     [https://fw.example.com      ] [📋]│ │
│  │  Management User:    [admin                      ] [📋]│ │
│  │  Management Password: [****************          ] [📋]│ │
│  │  Untrust URL:        [fw-untrust.example.com     ] [📋]│ │
│  │  Untrust Address:    [10.32.0.4/24              ] [📋]│ │
│  │  Untrust Subnet:     [10.32.0.0/24              ] [📋]│ │
│  │  Untrust Interface:  [ethernet1/1              ] [📋]│ │
│  │  Untrust Default GW: [10.32.0.1                 ] [📋]│ │
│  │  Trust Address:      [10.32.1.4/24              ] [📋]│ │
│  │  Trust Subnet:       [10.32.1.0/24              ] [📋]│ │
│  │  Trust Interface:    [ethernet1/2              ] [📋]│ │
│  │  Tunnel Interface:   [tunnel.1                 ] [📋]│ │
│  │  Tunnel Address:     [192.168.1.1/32           ] [📋]│ │
│  │  Panorama Address:   [10.32.1.5                 ] [📋]│ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Prisma Access Configuration                            │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │  Managed By:         [SCM ▼]                            │ │
│  │  TSG ID:             [1234567890                    ] [📋]│ │
│  │  API User:           [client-id                      ] [📋]│ │
│  │  API Secret:         [****************              ] [📋]│ │
│  │  Infrastructure Subnet: [192.168.254.0/24          ] [📋]│ │
│  │  Mobile User Subnet:   [100.64.0.0/16              ] [📋]│ │
│  │  Portal Hostname:      [portal.gpcloudservice.com  ] [📋]│ │
│  │  SC Endpoint:          [sc-endpoint.example.com    ] [📋]│ │
│  │  SC Name:              [SC-Datacenter              ] [📋]│ │
│  │  SC Location:          [US East                    ] [📋]│ │
│  │  SC PSK:               [****************          ] [📋]│ │
│  │  [Load from SCM] [Load from SPOV File...]                │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Operations                                              │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │  [Configure Initial Config] [Configure Firewall]          │ │
│  │  [Configure Service Connection] [Get FW Version]        │ │
│  │  [Print Settings]                                         │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Status/Output                                           │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │  [Output log area with scrollbar]                       │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. Configuration Management
- **New Configuration**: Create new encrypted config file
- **Load Configuration**: Browse and select existing `.bin` config file
- **Save Configuration**: Save current settings to encrypted file
- **Password Management**: Change encryption password
- **Copy/Paste Support**: 
  - Copy button (📋) next to each field
  - Right-click context menu for copy/paste
  - Keyboard shortcuts (Ctrl+C/Cmd+C, Ctrl+V/Cmd+V)

### 2. File Selection
- **SPOV Questionnaire**: File browser dialog for JSON files
- **Terraform Config**: Paste area or file selection
- **Config File Loading**: File browser with filter for `*-fwdata.bin`

### 3. Data Entry & Validation
- **All fields visible**: No hidden tabs, scrollable main window
- **Input validation**: 
  - IP address format checking
  - Subnet CIDR validation
  - URL format validation
  - Required field highlighting
- **Auto-calculation**: 
  - Subnet calculation from IP address
  - Default gateway suggestion
- **Password masking**: Show/hide toggle for password fields

### 4. Integration with Existing Scripts
- **Wrapper functions**: Call existing script functions without modification
- **Progress indication**: Show progress bars for long operations
- **Error handling**: Display errors in status area
- **Output redirection**: Capture stdout/stderr to GUI log area

### 5. Prisma Access Integration
- **Load from SCM**: Authenticate and fetch config from Prisma Access
- **Load from SPOV**: File browser to select JSON questionnaire
- **Auto-populate**: Fill fields from loaded data

## File Structure

### Option A: Single File (Recommended for simplicity)
```
pa_config_lab/
├── pa_config_gui.py          # Main GUI application (all-in-one)
├── [existing scripts...]      # Keep for reference/backward compatibility
└── requirements.txt           # Same dependencies
```

### Option B: Modular (Better organization)
```
pa_config_lab/
├── pa_config_gui.py          # Main GUI application
├── gui_modules/
│   ├── __init__.py
│   ├── config_manager.py     # Config file encryption/decryption
│   ├── firewall_ops.py       # Firewall operation wrappers
│   ├── prisma_ops.py         # Prisma Access operation wrappers
│   └── gui_widgets.py        # Custom GUI widgets
├── [existing scripts...]
└── requirements.txt
```

## Implementation Details

### GUI Components Breakdown

#### 1. Main Window Class
```python
class PAConfigGUI:
    def __init__(self, root):
        self.root = root
        self.current_config = None
        self.config_cipher = None
        self.setup_ui()
        self.setup_menu()
        
    def setup_ui(self):
        # Create all UI components
        # Organize into sections with frames
        
    def setup_menu(self):
        # File menu: New, Load, Save, Exit
        # Edit menu: Copy, Paste, Select All
        # Tools menu: All operations
        # Help menu: About, Documentation
```

#### 2. Configuration Sections
- **FirewallConfigFrame**: All firewall-related fields
- **PrismaConfigFrame**: All Prisma Access fields
- **OperationsFrame**: Buttons for all operations
- **StatusFrame**: Output log area

#### 3. Field Widget Factory
```python
def create_field_row(parent, label, default_value, field_type='text', 
                     protected=False, copy_button=True):
    # Creates: Label | Entry/Password Entry | Copy Button
    # Returns: (entry_widget, value_getter_function)
```

#### 4. Operations Integration
```python
def run_configure_firewall(self):
    # Collect values from GUI fields
    # Call configure_firewall.py functions
    # Show progress
    # Display results in status area
```

### Data Flow

1. **Load Config**:
   - User clicks "Load Config" → File browser opens
   - User selects `.bin` file → Password prompt
   - Decrypt config → Populate all GUI fields

2. **Edit Config**:
   - User edits fields in GUI
   - Changes stored in memory (not auto-saved)
   - "Save Config" button commits changes

3. **Run Operation**:
   - User clicks operation button (e.g., "Configure Firewall")
   - GUI collects current field values
   - Creates temporary config dict
   - Calls existing script functions
   - Displays output in status area

### Cross-Platform Considerations

#### Mac-specific
- Use `tkinter.filedialog` for native file dialogs
- Handle menu bar (appears at top of screen)
- Use Cmd key for shortcuts

#### Windows-specific
- Use `tkinter.filedialog` for native file dialogs
- Handle menu bar (in window)
- Use Ctrl key for shortcuts

#### Both Platforms
- Use `os.path` for file paths (handles separators)
- Test font rendering (tkinter fonts may differ)
- Handle window sizing/resizing gracefully

## Implementation Phases

### Phase 1: Basic GUI Structure (Week 1)
- [ ] Create main window with menu bar
- [ ] Create configuration sections (Firewall, Prisma)
- [ ] Implement field widgets with labels
- [ ] Add copy/paste functionality
- [ ] Basic layout and styling

### Phase 2: Configuration Management (Week 1-2)
- [ ] Integrate `load_settings.py` functionality
- [ ] Implement config file loading
- [ ] Implement config file saving
- [ ] Password management
- [ ] File browser dialogs

### Phase 3: Data Integration (Week 2)
- [ ] Connect GUI fields to config data
- [ ] Implement field validation
- [ ] Auto-calculation features
- [ ] Load from SCM integration
- [ ] Load from SPOV file integration

### Phase 4: Operations Integration (Week 2-3)
- [ ] Wrap `configure_initial_config.py`
- [ ] Wrap `configure_firewall.py`
- [ ] Wrap `configure_service_connection.py`
- [ ] Wrap `get_fw_version.py`
- [ ] Wrap `print_settings.py`
- [ ] Progress indicators
- [ ] Output redirection to status area

### Phase 5: Polish & Testing (Week 3)
- [ ] Error handling and user feedback
- [ ] Keyboard shortcuts
- [ ] Tooltips/help text
- [ ] Testing on Mac
- [ ] Testing on Windows
- [ ] Documentation

## Code Organization Strategy

### Single File Approach
- Use classes to organize code
- Group related functions together
- Use comments to separate sections
- Keep it under ~2000 lines if possible

### Modular Approach
- Main file: GUI layout and event handling
- Modules: Business logic separated from UI
- Easier to maintain and test

## User Experience Enhancements

1. **Tooltips**: Hover over fields for descriptions
2. **Validation Feedback**: Red borders on invalid fields
3. **Auto-save**: Optional auto-save on field change
4. **Recent Files**: Menu showing recently opened configs
5. **Keyboard Navigation**: Tab through fields
6. **Status Bar**: Show current operation status
7. **Progress Dialogs**: For long-running operations
8. **Confirmation Dialogs**: Before destructive operations

## Security Considerations

1. **Password Handling**: 
   - Never store passwords in plain text
   - Clear password fields from memory when possible
   - Use secure password entry widgets

2. **Config File Security**:
   - Maintain existing encryption
   - Secure file permissions
   - Warn before overwriting

3. **API Credentials**:
   - Mask in UI
   - Secure storage
   - Clear after use if possible

## Testing Strategy

1. **Unit Tests**: Test config loading/saving independently
2. **Integration Tests**: Test GUI → script integration
3. **Platform Tests**: Test on Mac and Windows
4. **User Testing**: Get feedback on usability

## Migration Path

1. **Keep existing scripts**: Don't break existing workflows
2. **Gradual adoption**: GUI can call existing scripts
3. **Documentation**: Update README with GUI instructions
4. **Backward compatibility**: GUI saves same format as CLI

## Future Enhancements (Post-MVP)

1. **Dark Mode**: Theme support
2. **Config Templates**: Pre-filled templates for common scenarios
3. **Export/Import**: JSON/CSV export for sharing
4. **History**: Undo/redo for config changes
5. **Multi-config**: Open multiple configs in tabs
6. **Validation Rules**: Custom validation per field type
7. **Wizard Mode**: Step-by-step guided configuration

## Estimated Timeline

- **Phase 1**: 3-5 days
- **Phase 2**: 3-5 days  
- **Phase 3**: 3-5 days
- **Phase 4**: 5-7 days
- **Phase 5**: 3-5 days

**Total**: ~3-4 weeks for full implementation

## Dependencies

No new dependencies required! tkinter is built into Python.

Optional enhancements:
- `ttkthemes` - Better looking themes (optional)
- `pillow` - Better image support if adding icons (optional)

## Next Steps

1. Review and approve this plan
2. Choose single-file vs modular approach
3. Create initial GUI skeleton
4. Begin Phase 1 implementation
5. Iterate based on feedback
