# Config Save Dialog Improvement

**Date:** December 22, 2025  
**Status:** ✅ COMPLETE

## Summary

Improved the configuration save dialog UX by combining name and password fields into a single dialog, using tenant name as default instead of TSG, and adding status messages with auto-close on success.

## Changes Made

### 1. Combined Save Dialog (`gui/saved_configs_sidebar.py`)

**Before:**
- Two separate dialogs: one for name, one for password
- Success shown in separate popup dialog
- Used simple `QInputDialog.getText()` for name

**After:**
- Single dialog with all fields:
  - Configuration Name (pre-filled with tenant name)
  - Password (if encrypting)
  - Confirm Password (if encrypting)
- Status header (green for success, red for error)
- Auto-closes after 1 second on success
- Stays open on error for user to correct

### 2. Default Name Logic (`gui/workflows/migration_workflow.py`)

**Before:**
```python
default_name = config.get("metadata", {}).get("source_tenant", "")  # TSG ID
```

**After:**
```python
# Use connection name (tenant name like "Production") instead of TSG
default_name = getattr(self, 'connection_name', None)
if not default_name or default_name == "Manual":
    # Fall back to TSG or timestamp
    default_name = config.get("metadata", {}).get("source_tenant", "")
```

### 3. Connection Name Storage

Added `self.connection_name` to `MigrationWorkflowWidget` to track the tenant name for use in save dialogs.

## UI/UX Improvements

### Status Messages
- **Success (Green):** `✓ Configuration saved as 'Production'`
  - Background: `#e8f5e9` (light green)
  - Text: `#2e7d32` (dark green)
  - Auto-closes after 1 second

- **Error (Red):** `✗ Error message here`
  - Background: `#ffebee` (light red)
  - Text: `#c62828` (dark red)
  - Stays open for user action

### Validation
- Name required
- Password required (if encrypting)
- Password confirmation must match
- All validation errors shown in red status header

### Overwrite Handling
- If config name exists, shows confirmation dialog
- On overwrite success, shows green status and auto-closes
- On overwrite failure, shows red status and stays open

## Files Modified

1. `gui/saved_configs_sidebar.py`
   - Replaced `save_current_config()` with combined dialog
   - Removed separate password dialog call
   - Added status label with color-coded messages
   - Added QTimer for auto-close on success

2. `gui/workflows/migration_workflow.py`
   - Added `self.connection_name` storage in `set_api_client()`
   - Updated `_save_current_config()` to use connection name
   - Updated `_auto_save_pulled_config()` to use connection name
   - Removed success popup (handled by save dialog)

## User Experience Flow

### Successful Save
1. User clicks "Save Configuration"
2. Dialog opens with tenant name pre-filled (e.g., "Production")
3. User enters password and confirms
4. User clicks "Save"
5. Green status appears: "✓ Configuration saved as 'Production'"
6. Dialog auto-closes after 1 second
7. Config appears in saved configs list

### Error Handling
1. User clicks "Save Configuration"
2. Dialog opens with tenant name pre-filled
3. User makes an error (e.g., passwords don't match)
4. Red status appears: "⚠ Passwords do not match"
5. Dialog stays open for correction
6. User fixes error and saves successfully

### Overwrite Scenario
1. User tries to save with existing name
2. Confirmation dialog: "Configuration 'Production' already exists. Overwrite it?"
3. User confirms
4. Green status appears: "✓ Configuration saved as 'Production'"
5. Dialog auto-closes after 1 second

## Benefits

1. **Fewer Clicks** - One dialog instead of two
2. **Better Context** - All fields visible at once
3. **Clear Feedback** - Color-coded status messages
4. **Faster Workflow** - Auto-close on success
5. **Better Defaults** - Uses friendly tenant name instead of TSG ID
6. **Consistent UX** - Matches connection dialog pattern

## Testing Checklist

- [ ] Save new config with tenant name default
- [ ] Save with manual connection (falls back to TSG)
- [ ] Password validation (empty, mismatch)
- [ ] Name validation (empty)
- [ ] Overwrite existing config
- [ ] Success auto-close after 1 second
- [ ] Error stays open for correction
- [ ] Config appears in saved configs list
