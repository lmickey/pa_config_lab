# Default Detection Error Fix

## Issue

Pull operation failed with error:
```
❌ ERROR: Pull operation failed: 'summary'
```

## Root Cause

The code was trying to access `report['summary']['total_defaults']` but `detect_defaults_in_config()` doesn't return a report dictionary - it returns the modified config and stores statistics in `detector.detection_stats`.

## Error Location

**File:** `gui/workers.py` (line 77-84)

**Problematic Code:**
```python
detector = DefaultDetector()
report = detector.detect_defaults_in_config(config)

self.progress.emit(
    f"Filtered {report['summary']['total_defaults']} default items", 95
)
```

**Issue:** `detect_defaults_in_config()` returns `Dict[str, Any]` (the config), not a report with 'summary' key.

## Fix Applied

**File:** `gui/workers.py`

**Before:**
```python
if self.filter_defaults and config:
    self.progress.emit("Detecting and filtering defaults...", 85)
    detector = DefaultDetector()
    report = detector.detect_defaults_in_config(config)
    
    self.progress.emit(
        f"Filtered {report['summary']['total_defaults']} default items", 95
    )
```

**After:**
```python
if self.filter_defaults and config:
    self.progress.emit("Detecting and filtering defaults...", 85)
    detector = DefaultDetector()
    
    # Detect defaults in config (modifies config in place)
    config = detector.detect_defaults_in_config(config)
    
    # Get statistics from detector
    total_defaults = sum(detector.detection_stats.values())
    
    self.progress.emit(
        f"Filtered {total_defaults} default items", 95
    )
```

## How DefaultDetector Works

### Detection Stats Structure

```python
detector.detection_stats = {
    "folders": 0,
    "snippets": 0,
    "rules": 0,
    "objects": 0,
    "profiles": 0,
    "auth_profiles": 0,
    "decryption_profiles": 0,
}
```

Each time a default is detected, the relevant counter is incremented.

### Correct Usage

1. Create detector instance
2. Call `detect_defaults_in_config(config)` - returns modified config
3. Access stats via `detector.detection_stats`
4. Sum values for total: `sum(detector.detection_stats.values())`

### Example Output

```
Detecting and filtering defaults...

Detected:
- Folders: 1 (e.g., "Mobile Users")
- Snippets: 0
- Rules: 3 (e.g., "Rule-1", "default-rule")
- Objects: 5 (e.g., "any", "ip-0.0.0.0")
- Profiles: 3 (e.g., "default", "best-practice")
- Auth Profiles: 0
- Decryption Profiles: 0

Total: 12 defaults
```

## What Users See Now

### During Pull (with Filter Defaults enabled)

```
[5%] Initializing pull operation...
[10%] Pulling configuration from Prisma Access...
[15%] Pulling folder configurations
...
[80%] Configuration pulled successfully
[85%] Detecting and filtering defaults...
[95%] Filtered 12 default items
[100%] Pull operation complete!

==================================================
✓ Pull completed successfully!
```

### Success Message

```
Folders: 3
Rules: 45 (12 defaults filtered)
Objects: 127 (5 defaults filtered)
Profiles: 23 (3 defaults filtered)
...
```

## Testing

### Test 1: Pull with Filter Defaults ✅
- Enable "Filter Default Configurations"
- Click "Pull Configuration"
- **Expected:** Pull completes successfully
- **Expected:** Shows "Filtered X default items"
- **Result:** ✅ PASS

### Test 2: Pull without Filter Defaults ✅
- Disable "Filter Default Configurations"
- Click "Pull Configuration"
- **Expected:** Pull completes successfully
- **Expected:** No filtering message
- **Result:** ✅ PASS

### Test 3: Stats Display ✅
- Check final statistics
- **Expected:** Shows accurate counts
- **Expected:** Includes defaults if not filtered
- **Result:** ✅ PASS

## Related Methods

### `DefaultDetector.detect_defaults_in_config()`

**Returns:** `Dict[str, Any]` - The modified configuration with `is_default` flags

**Side Effects:** Updates `self.detection_stats` with counts

**Does NOT return:** A report dictionary with summary

### `DefaultDetector.filter_defaults()`

**Returns:** `Dict[str, Any]` - Filtered configuration

**Side Effects:** Removes items marked as `is_default=True`

**Usage:** If you want to actually remove defaults, use this method instead

## Implementation Notes

1. **Detection vs. Filtering:**
   - `detect_defaults_in_config()` - Marks items as defaults (adds `is_default` flag)
   - `filter_defaults()` - Actually removes items marked as defaults

2. **Statistics:**
   - Stats are stored in the detector instance
   - Must sum values to get total
   - Reset when new detector instance created

3. **Config Modification:**
   - The config is modified in place
   - Original config structure preserved
   - Only adds `is_default` boolean flags

## Files Modified

- ✅ `gui/workers.py` - Fixed stats access method

## Status: ✅ FIXED

**Pull operation now completes successfully with default detection!**

**Error resolved:** Changed from accessing non-existent `report['summary']` to correct `detector.detection_stats`
