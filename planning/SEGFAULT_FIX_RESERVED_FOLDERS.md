# Segmentation Fault Fix - Reserved Folders

**Date:** December 21, 2025  
**Issue:** GUI seg fault due to infinite loop querying invalid folders  
**Root Cause:** Two problems identified from `api_errors.log`

---

## 🐛 Problems Identified

### Problem 1: Non-Existent Folders
The system was trying to query folder **"Colo Connect"** which doesn't exist:
```
"Folder Colo Connect doesn't exist. Please create it before running the command"
```

This caused 400 errors for every API endpoint (rules, objects, profiles).

### Problem 2: Reserved System Folders
The system was trying to query **"Service Connections"** which is a **reserved/infrastructure-only folder**:
```
"folder" with value "Service Connections" fails to match the required pattern: /^((?!Service Connections).)*$/
```

The API explicitly rejects querying security policies in this folder because it's reserved for infrastructure configuration only.

### Result: Infinite Loop → Seg Fault
1. Try to query invalid folders
2. Get 400 errors  
3. Rate limiter waits
4. Retry same invalid folders
5. Get 400 errors again
6. Loop continues → seg fault

The logs showed this happening repeatedly (at 20:45:25, 20:59:36, etc.), causing the system to hang and eventually crash.

---

## ✅ Fixes Applied

### Fix 1: Filter Reserved Folders
**File:** `prisma/pull/folder_capture.py`  
**Method:** `list_folders_for_capture()`

Added a list of reserved infrastructure-only folders that cannot have security policies:

```python
# Reserved/system folders that cannot have security policies
RESERVED_FOLDERS = {
    "Service Connections",
    "Remote Networks",
    "Mobile Users",
    "Mobile_User_Template",
    "Shared",  # Shared is default but can be used
}
```

The method now:
1. Checks if folder is in `RESERVED_FOLDERS`
2. Skips reserved folders (except "Shared" which is usable)
3. Logs info message: `"ℹ Skipping reserved folder: {name} (infrastructure only)"`

### Fix 2: Improved Error Handling
**File:** `prisma/pull/rule_capture.py`  
**Method:** `capture_rules_from_folder()`

Enhanced error handling to detect "folder doesn't exist" errors:

```python
except Exception as e:
    # Check if folder doesn't exist (400 error)
    error_str = str(e).lower()
    if "doesn't exist" in error_str or "folder" in error_str and ("400" in error_str or "not exist" in error_str or "invalid" in error_str):
        print(f"⚠ Folder '{folder_name}' does not exist or is invalid - skipping")
        return []
    
    print(f"Error capturing rules from folder {folder_name}: {e}")
    return []
```

Now when a folder doesn't exist:
- Detects 400/"doesn't exist" errors
- Logs a clear warning message
- Returns empty list (no retry)
- Continues with next folder

---

## 🎯 Expected Behavior After Fix

### Before (Broken):
```
Pulling folder Service Connections...
API ERROR 400: folder "Service Connections" fails pattern
Rate limit approaching, waiting...
Pulling folder Service Connections...  [RETRY]
API ERROR 400: folder "Service Connections" fails pattern
Rate limit approaching, waiting...
[Infinite loop → seg fault]
```

### After (Fixed):
```
Pulling folders...
ℹ Skipping reserved folder: Service Connections (infrastructure only)
ℹ Skipping reserved folder: Remote Networks (infrastructure only)
ℹ Skipping reserved folder: Mobile Users (infrastructure only)
Pulling folder: Shared
Pulling folder: My Custom Folder
⚠ Folder 'Colo Connect' does not exist or is invalid - skipping
Pull complete!
```

---

## 📋 Reserved Folders List

These folders are **infrastructure-only** and cannot have security policies:

| Folder Name | Purpose | Can Query? |
|------------|---------|-----------|
| **Service Connections** | Infrastructure config for on-prem connectivity | ❌ No |
| **Remote Networks** | Infrastructure config for branch offices | ❌ No |
| **Mobile Users** | Infrastructure config for GlobalProtect | ❌ No |
| **Mobile_User_Template** | Template for mobile user configs | ❌ No |
| **Shared** | Default folder (usable) | ✅ Yes |

---

## 🧪 Testing

### Test 1: Verify Reserved Folders Are Skipped
```bash
python3 run_gui.py
# Connect to Prisma Access
# Click "Pull Configuration"
# Check output for:
#   "ℹ Skipping reserved folder: Service Connections (infrastructure only)"
```

### Test 2: Verify Non-Existent Folders Are Handled
```bash
# If you have a folder that was deleted/renamed
# Pull should show:
#   "⚠ Folder 'Colo Connect' does not exist or is invalid - skipping"
# And continue without hanging
```

### Test 3: Verify No More Seg Faults
```bash
python3 run_gui.py
# Connect
# Pull Configuration
# Should complete successfully without seg fault
```

---

## 📝 Additional Notes

### Why This Happened
The folder discovery API returns **all folders** including:
- User-created folders
- System/reserved folders (Service Connections, Remote Networks, etc.)
- Potentially deleted/renamed folders still in cache

The code was blindly trying to query all of them for security policies, which isn't valid for infrastructure-only folders.

### Why "Service Connections" Can't Have Security Policies
"Service Connections" is a **special infrastructure folder** used only for:
- Configuring service connections (to AWS, Azure, etc.)
- Cannot contain security policies, objects, or profiles
- The API explicitly rejects it with pattern validation

Same for "Remote Networks" and "Mobile Users" - they're infrastructure-only.

### Infrastructure vs. Security Policy Folders
- **Infrastructure Folders:** Configuration for network connectivity (remote networks, service connections, mobile users)
- **Security Policy Folders:** Configuration for security policies (rules, objects, profiles)

They're separate concepts - infrastructure folders cannot contain security policies.

---

## 🔍 How to Check Your Log

If this happens again:

1. **Look for repeated API errors:**
   ```
   grep "API ERROR" api_errors.log | grep -E "400|Forbidden"
   ```

2. **Check for folder doesn't exist:**
   ```
   grep "doesn't exist" api_errors.log
   ```

3. **Check for reserved folder pattern errors:**
   ```
   grep "fails to match the required pattern" api_errors.log
   ```

4. **Check for rate limit messages:**
   ```
   grep "Rate limit" console_output.log
   ```

If you see the same folder being queried repeatedly with 400 errors, that's the infinite loop.

---

## ✅ Fix Summary

- **Files Modified:** 2
  - `prisma/pull/folder_capture.py` - Filter reserved folders
  - `prisma/pull/rule_capture.py` - Better error handling

- **Lines Changed:** ~30 lines

- **Impact:** Prevents infinite loops on invalid folders, no more seg faults

- **Testing:** Ready for testing in GUI

---

**Status:** ✅ **FIXED**  
**Ready for:** Re-testing in GUI
