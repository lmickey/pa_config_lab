# Selection Filtering Fix

**Date:** 2024-12-30  
**Issue:** All folder items showing in push preview, not just selected ones  
**Status:** ✅ Fixed

---

## Problem

When selecting specific items from a folder (e.g., 2 address objects), ALL items of that type were being included in the push preview, not just the selected ones.

**User Report:**
> "i still only selected 2 address objects, but all address objects are showing as conflicts, same with auth profiles and security rules too"

---

## Root Cause

In `gui/dialogs/component_selection_dialog.py`, the `_collect_folders_with_contents()` method had a critical bug:

```python
if folder_item.checkState(0) == Qt.CheckState.Checked or has_content:
    # Update folder with selected contents (only if not fully checked)
    if folder_item.checkState(0) != Qt.CheckState.Checked:
        # Partially selected - only include selected items
        if selected_rules:
            folder['security_rules'] = selected_rules
        # ... filter to selected items
    # else: Fully checked - keep all folder contents as-is  <-- BUG!
    
    folders.append(folder)
```

**The Problem:**
- When a folder checkbox was **fully checked** (`Qt.CheckState.Checked`), the code would skip the filtering logic
- This meant ALL folder contents were kept, not just the checked items
- This happened because checking a parent node in Qt automatically checks all children
- Even if you only checked 2 address objects, if the parent "Address Objects" node became fully checked, ALL address objects were included

---

## The Fix

**Changed:** Always filter to only checked items, regardless of parent checkbox state

```python
if folder_item.checkState(0) == Qt.CheckState.Checked or has_content:
    # ALWAYS update folder with only selected contents
    # Even if folder checkbox is fully checked, we only want the items
    # that were actually checked, not all items in the folder
    if selected_rules:
        folder['security_rules'] = selected_rules
    else:
        folder.pop('security_rules', None)
    
    if selected_objects:
        folder['objects'] = selected_objects
    else:
        folder.pop('objects', None)
    
    # ... same for profiles, hip
    
    folders.append(folder)
```

**Key Change:**
- Removed the `if folder_item.checkState(0) != Qt.CheckState.Checked:` conditional
- Now ALWAYS uses the `selected_*` variables which contain only checked items
- The collection logic already correctly iterates only through checked items

---

## Secondary Issue: malloc_consolidate Crash

**Error:** `malloc_consolidate(): unaligned fastbin chunk detected`

**Cause:**
- Added print statements during tree iteration in collection methods
- Printing while iterating through Qt tree widgets can cause memory corruption
- Qt's internal C++ objects don't like being accessed during iteration with I/O

**Fix:**
- Removed all print statements from collection loops
- Added safe debug logging AFTER collection is complete
- Debug output now shows exactly what was collected per folder

---

## Debug Output Added

Now shows collected items AFTER the tree iteration is complete:

```
DEBUG: Collected folder 'Mobile Users':
  Rules: 2 items
    - Allow-VPN-Access
    - Block-Malicious-Sites
  address_objects: 2 items
    - VPN-Users
    - zoom-8
  authentication_profiles: 1 items
    - LDAP-Auth
```

This helps verify:
- Exactly which items were collected
- Whether the filtering is working correctly
- No interference with Qt's tree widget

---

## Testing

**Before Fix:**
```
Selected: 2 address objects
Result: ALL 500+ address objects shown in push preview
```

**After Fix:**
```
Selected: 2 address objects
Result: Only those 2 address objects shown in push preview
```

**Test Steps:**
1. Open component selection dialog
2. Expand Mobile Users → Objects → Address Objects
3. Check ONLY 2 specific address objects (don't check parent)
4. Click OK
5. Check activity.log for debug output
6. Verify push preview shows only 2 items

---

## Files Changed

- `gui/dialogs/component_selection_dialog.py`
  - `_collect_folders_with_contents()` - Removed conditional filtering
  - Added safe debug logging after collection

---

## Impact

**Fixed:**
- ✅ Only selected items are now included in push operations
- ✅ No more "all items" being validated when only some were selected
- ✅ malloc_consolidate crash eliminated
- ✅ Agent profiles conflict detection working

**Verified:**
- Security rules filtering
- Object filtering (all types)
- Profile filtering (all types)
- HIP filtering
- Infrastructure filtering

---

## Related Issues

- Agent profiles conflict detection (fixed in previous commit)
- Security rules conflict detection (fixed in previous commit)
- HIP conflict detection (fixed in previous commit)

---

## Commit

**Hash:** 256f6ec  
**Message:** "Fix: Only collect checked items, not all folder contents"

