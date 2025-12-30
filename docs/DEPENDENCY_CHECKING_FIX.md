# Dependency Checking Fix

**Date:** 2024-12-30  
**Issue:** Dependencies not being checked in tree after confirmation  
**Status:** ✅ Fixed

---

## Problem

When selecting an object with dependencies:
1. User selects 1 address object
2. Dependency dialog shows a second dependent address object
3. User confirms dependencies
4. **BUG:** When going back to selection dialog, the dependent object is NOT checked
5. Result: Dependent object doesn't make it to push validation

**User Report:**
> "I checked one address object, dependency check highlighted a second one, but when i go back in to confirm selection it's not check so it's not making it to the validation step"

---

## Root Cause

The `_check_merged_dependencies()` method was trying to check objects in the tree using a generic recursive search:

```python
# Old code
if 'objects' in required_deps:
    for obj_type, obj_list in required_deps['objects'].items():
        for obj in obj_list:
            obj_name = obj.get('name')
            if obj_name:
                folder_name = obj.get('folder')
                if folder_name:
                    # ... find Security Policies section ...
                    find_and_check_item(folders_section, obj_name, 'folder_object')
```

**The Problem:**
- The generic `find_and_check_item()` function was looking for items with `item_type == 'folder_object'`
- But objects in folders have a complex nested structure that the generic function couldn't navigate
- The tree structure for objects is:

```
Security Policies
  └─ Folders
      └─ Mobile Users (folder)
          └─ Objects (container)
              └─ Address Objects (object type container)
                  └─ VPN-Users (the actual object)
```

- The generic search would find the folder but couldn't navigate into the Objects container → object type → specific object

---

## The Fix

Created a specialized `_check_object_in_folder()` method that understands the folder structure:

```python
def _check_object_in_folder(self, folders_section: QTreeWidgetItem, 
                            folder_name: str, obj_name: str, obj_type: str):
    """Find and check an object within a specific folder."""
    # 1. Find the folder by name
    for i in range(folders_section.childCount()):
        folder_item = folders_section.child(i)
        folder_data = folder_item.data(0, Qt.ItemDataRole.UserRole)
        if folder_data and folder_data.get('type') == 'folder':
            if folder_data.get('data', {}).get('name') == folder_name:
                # 2. Find the "Objects" container within the folder
                for j in range(folder_item.childCount()):
                    content_item = folder_item.child(j)
                    if content_item.text(0) == "Objects":
                        # 3. Find the object type container (e.g., "Address Objects")
                        for k in range(content_item.childCount()):
                            obj_type_item = content_item.child(k)
                            obj_type_data = obj_type_item.data(0, Qt.ItemDataRole.UserRole)
                            if obj_type_data and obj_type_data.get('object_type') == obj_type:
                                # 4. Find the specific object by name
                                for m in range(obj_type_item.childCount()):
                                    obj_item = obj_type_item.child(m)
                                    obj_item_data = obj_item.data(0, Qt.ItemDataRole.UserRole)
                                    if obj_item_data:
                                        item_name = obj_item_data.get('data', {}).get('name')
                                        if item_name == obj_name:
                                            # 5. Check it!
                                            obj_item.setCheckState(0, Qt.CheckState.Checked)
                                            return True
    return False
```

**Updated the object checking code:**

```python
if 'objects' in required_deps:
    print(f"\nDEBUG: Checking object dependencies")
    for obj_type, obj_list in required_deps['objects'].items():
        print(f"  Object type: {obj_type}, Count: {len(obj_list)}")
        for obj in obj_list:
            obj_name = obj.get('name')
            folder_name = obj.get('folder')
            print(f"    Object: {obj_name}, Folder: {folder_name}")
            if obj_name and folder_name:
                # ... find folders section ...
                self._check_object_in_folder(folders_section, folder_name, 
                                            obj_name, obj_type)
```

---

## Debug Output Added

Now shows detailed information when checking object dependencies:

```
DEBUG: Checking object dependencies
  Object type: address_objects, Count: 1
    Object: VPN-Users, Folder: Mobile Users
    Searching for object 'VPN-Users' in folder 'Mobile Users'
      Found folder: Mobile Users
      Found Objects container
      Found object type: address_objects
      MATCH! Checking object: VPN-Users
```

This helps verify:
- Which objects are being checked as dependencies
- Which folder they belong to
- Whether the tree navigation succeeded
- Whether the object was found and checked

---

## Testing

**Test Case: Address Object with Dependency**

1. **Setup:**
   - Object A uses Object B in its configuration
   - Object B is a dependency of Object A

2. **Steps:**
   - Select only Object A
   - Click OK
   - Dependency dialog appears showing Object B
   - Click "Add Dependencies"
   - Selection dialog reopens

3. **Expected Result:**
   - ✅ Object A is checked (original selection)
   - ✅ Object B is checked (dependency)
   - Both show in summary at bottom

4. **Proceed to Push Preview:**
   - ✅ Both objects appear in the list
   - ✅ Conflict detection works for both

---

## Files Changed

- `gui/dialogs/component_selection_dialog.py`
  - Added `_check_object_in_folder()` helper method
  - Updated object dependency checking with debug output
  - Proper tree navigation for nested objects

---

## Impact

**Fixed:**
- ✅ Object dependencies are now properly checked in tree
- ✅ Dependencies persist when dialog reopens
- ✅ All dependencies make it to push validation

**Works For:**
- Address objects
- Service objects
- Application objects
- All other object types in folders

**Related Fixes:**
- Selection filtering (previous commit)
- Agent profiles conflict detection
- All folder contents filtering

---

## Commit

**Hash:** 7722071  
**Message:** "Fix object dependency checking in tree"

