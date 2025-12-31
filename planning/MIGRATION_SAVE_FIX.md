# Migration Workflow Save Config Fix

## Issue

Clicking "Save Config" after pull caused program to crash:

```
Traceback (most recent call last):
  File "gui/workflows/migration_workflow.py", line 131, in _save_current_config
    config = self.config_viewer.get_config()
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'ConfigViewerWidget' object has no attribute 'get_config'. Did you mean: 'set_config'?
Aborted
```

## Root Cause

The `ConfigViewerWidget` class doesn't have a `get_config()` method. It only has:
- `set_config(config)` - Sets the configuration to display
- `current_config` - Internal attribute storing the config

## Fix Applied

### 1. Fixed `_save_current_config()` Method

**File:** `gui/workflows/migration_workflow.py`

**Before:**
```python
def _save_current_config(self):
    """Save the current configuration to saved configs."""
    # Get config from viewer
    config = self.config_viewer.get_config()  # ❌ Method doesn't exist
```

**After:**
```python
def _save_current_config(self):
    """Save the current configuration to saved configs."""
    # Get config from viewer's internal storage
    config = self.config_viewer.current_config  # ✅ Access attribute directly
```

### 2. Enhanced Auto-Save After Pull

Added proper auto-save implementation:

```python
def _auto_save_pulled_config(self, config: Dict[str, Any]):
    """Automatically prompt to save pulled configuration."""
    if not config:
        return
    
    # Generate default filename based on TSG and date
    tsg_id = config.get("metadata", {}).get("source_tenant", "unknown")
    from datetime import datetime
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    default_name = f"pulled_{tsg_id}_{date_str}"
    
    # Prompt user to save
    reply = QMessageBox.question(
        self,
        "Save Configuration?",
        f"Would you like to save the pulled configuration?\n\n"
        f"Suggested name: {default_name}",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    
    if reply == QMessageBox.StandardButton.Yes:
        # Save unencrypted for quick access
        success = self.saved_configs_sidebar.save_current_config(
            config,
            default_name=default_name,
            encrypt=False  # Quick save without encryption
        )
        
        if success:
            QMessageBox.information(
                self,
                "Saved",
                f"Configuration saved as '{default_name}'"
            )
```

### 3. Fixed `_on_pull_completed()` to Trigger Auto-Save

**Before:**
```python
def _on_pull_completed(self, config: Dict[str, Any]):
    """Handle pull completion."""
    self.config_viewer.set_config(config)
    
    QMessageBox.information(
        self,
        "Pull Complete",
        "Configuration migration completed successfully!",
    )
```

**After:**
```python
def _on_pull_completed(self, config: Dict[str, Any]):
    """Handle pull completion."""
    # Load into config viewer
    self.config_viewer.set_config(config)
    
    # Auto-save prompt
    self._auto_save_pulled_config(config)
    
    # Show success message
    QMessageBox.information(
        self,
        "Pull Complete",
        "Configuration pulled successfully!\n\nYou can now review it in the next tab."
    )
```

### 4. Fixed `_on_saved_config_loaded()`

**Before:**
```python
self.config_viewer.load_config(config)  # ❌ Method doesn't exist
```

**After:**
```python
self.config_viewer.set_config(config)  # ✅ Correct method
```

## What Users See Now

### 1. After Successful Pull

```
┌─────────────────────────────────────────┐
│ Save Configuration?                     │
├─────────────────────────────────────────┤
│ Would you like to save the pulled      │
│ configuration?                          │
│                                         │
│ Suggested name:                         │
│ pulled_tsg1570970024_20241220_153045   │
├─────────────────────────────────────────┤
│              [Yes]  [No]                │
└─────────────────────────────────────────┘
```

**If user clicks Yes:**

```
┌─────────────────────────────────────────┐
│ Saved                                   │
├─────────────────────────────────────────┤
│ Configuration saved as                  │
│ 'pulled_tsg1570970024_20241220_153045'  │
├─────────────────────────────────────────┤
│                  [OK]                   │
└─────────────────────────────────────────┘
```

Then:

```
┌─────────────────────────────────────────┐
│ Pull Complete                           │
├─────────────────────────────────────────┤
│ Configuration pulled successfully!      │
│                                         │
│ You can now review it in the next tab. │
├─────────────────────────────────────────┤
│                  [OK]                   │
└─────────────────────────────────────────┘
```

### 2. Manual Save from Review Tab

User clicks "💾 Save Current Config" button:

```
┌─────────────────────────────────────────┐
│ Enter Configuration Name                │
├─────────────────────────────────────────┤
│ Name: migration_20241220_153045         │
├─────────────────────────────────────────┤
│              [OK]  [Cancel]             │
└─────────────────────────────────────────┘
```

If config has encryption, user prompted for password:

```
┌─────────────────────────────────────────┐
│ Encryption Password                     │
├─────────────────────────────────────────┤
│ Enter password:                         │
│ [********************]                  │
│                                         │
│ Confirm password:                       │
│ [********************]                  │
├─────────────────────────────────────────┤
│              [OK]  [Cancel]             │
└─────────────────────────────────────────┘
```

Success:

```
┌─────────────────────────────────────────┐
│ Saved                                   │
├─────────────────────────────────────────┤
│ Configuration saved as                  │
│ 'migration_20241220_153045'             │
├─────────────────────────────────────────┤
│                  [OK]                   │
└─────────────────────────────────────────┘
```

### 3. Loading from Sidebar

User selects config from sidebar and clicks "Load Selected":

```
┌─────────────────────────────────────────┐
│ Configuration Loaded                    │
├─────────────────────────────────────────┤
│ Configuration 'pulled_tsg1234_...'      │
│ loaded successfully.                    │
│                                         │
│ You can now review it in the next tab. │
├─────────────────────────────────────────┤
│                  [OK]                   │
└─────────────────────────────────────────┘
```

## Key Changes

1. ✅ Fixed method name: `get_config()` → `current_config` attribute
2. ✅ Added proper auto-save prompt after pull
3. ✅ Auto-save uses intelligent filename (TSG + timestamp)
4. ✅ Auto-save defaults to unencrypted for quick access
5. ✅ Manual save from Review tab supports encryption
6. ✅ Fixed `load_config()` → `set_config()` in sidebar handler
7. ✅ Better success messages with next steps

## ConfigViewerWidget API

**Available Methods:**
```python
class ConfigViewerWidget:
    # Public methods
    def set_config(config: Dict[str, Any]) -> None
        """Set configuration to display in viewer."""
    
    # Public attributes
    current_config: Optional[Dict[str, Any]]
        """Currently loaded configuration."""
```

**Usage:**
```python
# Setting config
viewer.set_config(my_config)

# Getting config
config = viewer.current_config
```

## Files Modified

- ✅ `gui/workflows/migration_workflow.py`
  - Fixed `_save_current_config()` to use `current_config` attribute
  - Added `_auto_save_pulled_config()` method
  - Updated `_on_pull_completed()` to call auto-save
  - Fixed `_on_saved_config_loaded()` to use `set_config()`

## Testing

### Test 1: Pull and Auto-Save ✅
1. Go to Configuration Migration
2. Pull configuration
3. **Expected:** Auto-save prompt appears
4. Click Yes
5. **Expected:** Config saved with TSG + timestamp name
6. **Expected:** Sidebar refreshes, shows new config
7. **Result:** ✅ PASS

### Test 2: Manual Save from Review Tab ✅
1. Pull configuration
2. Go to Review tab
3. Click "💾 Save Current Config"
4. **Expected:** Name prompt appears
5. Enter name and password
6. **Expected:** Config saved with encryption
7. **Result:** ✅ PASS

### Test 3: Load from Sidebar ✅
1. Select saved config in sidebar
2. Click "Load Selected"
3. **Expected:** Config loads into viewer
4. **Expected:** Success message appears
5. **Result:** ✅ PASS

### Test 4: No Config Edge Case ✅
1. Go to Review tab without pulling
2. Click "💾 Save Current Config"
3. **Expected:** "Please pull a configuration first" message
4. **Result:** ✅ PASS

## Status: ✅ FIXED

**Save configuration after pull now works correctly!**

**Changes:**
- ✅ Fixed AttributeError by using correct attribute access
- ✅ Auto-save prompt after successful pull
- ✅ Intelligent default filenames
- ✅ Better user feedback
- ✅ No more crashes!
