# Utility Scripts

This directory contains utility scripts for various maintenance and conversion tasks.

## Available Scripts

### capture_production_examples.py
Captures real-world configuration examples from a Prisma Access tenant for testing and validation.

**Purpose:**
- Validate model implementations against real configurations
- Discover missing properties in models
- Create comprehensive test cases
- Document real-world usage patterns

**Usage:**
```bash
# Interactive tenant selection
python scripts/capture_production_examples.py

# Use specific saved tenant
python scripts/capture_production_examples.py --tenant "Lab Tenant"

# Capture with custom limit per type
python scripts/capture_production_examples.py --max 20

# Capture from specific folder only
python scripts/capture_production_examples.py --folder "Mobile Users"
```

**Output:**
- Raw JSON files: `tests/examples/production/raw/<type>/*.json`
- Detailed report: `tests/examples/production/capture_report.json`

**Expected Errors:**
Many errors are NORMAL and expected:
- `404 Not Found` - Type doesn't exist in this folder (normal)
- `No items found` - Empty folder/snippet (normal)
- API errors may indicate permissions or unsupported types

All errors are logged to `capture_report.json` for review. Don't worry about seeing many errors during capture - they're filtered and logged automatically.

**Excluded Items:**
For security/sensitivity reasons, the following are excluded:
- Folders: "Colo Connect", "Service Connections"
- Types: service_connection

### convert_legacy_to_json.py
Converts legacy pickle format configuration files to JSON format.

**Usage:**
```bash
python scripts/convert_legacy_to_json.py
```

### generate_pov_code.py
Generates POV (Proof of Value) workflow code and configurations.

**Usage:**
```bash
python scripts/generate_pov_code.py
```

### reorganize_pov_workflow.py
Reorganizes and restructures POV workflow components.

**Usage:**
```bash
python scripts/reorganize_pov_workflow.py
```

## Notes

These are utility scripts for specific tasks and are not part of the main application. They are kept here to avoid cluttering the project root.

For main application scripts, see the project root:
- `run_gui.py` - Launch the GUI
- `get_settings.py` - Interactive configuration setup
- `load_settings.py` - Load configuration
- `print_settings.py` - Display configuration
