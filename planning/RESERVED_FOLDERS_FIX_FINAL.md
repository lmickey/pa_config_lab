# Reserved Folder Segfault Fix - Final Resolution

**Date:** December 21, 2025  
**Issue:** Segfaults caused by attempting to query reserved infrastructure folders for security policies/objects/profiles

---

## 🎯 Root Cause

The GUI was segfaulting because the system discovered **reserved infrastructure folders** like:
- "Service Connections" ❌ Cannot have security policies
- "Colo Connect" ❌ Cannot have security policies

And then attempted to query them for security policies, objects, and profiles. These folders:
1. **Cannot have security policies** - they're infrastructure-only
2. **Return API validation errors** - explicit pattern rejections like:
   ```
   "folder" with value "Service Connections" fails to match the required pattern: /^((?!Service Connections).)*$/
   ```
3. **Caused retry loops** - the system kept retrying, waiting for rate limits, and eventually segfaulted

---

## ✅ Complete Fix (Three Layers of Defense)

### **Layer 1: Folder Discovery Filtering**
**File:** `prisma/pull/folder_capture.py` (Line 196-214)

```python
RESERVED_FOLDERS = {
    "Service Connections",  # Infrastructure only - cannot have security policies
    "Colo Connect",         # Infrastructure only - cannot have security policies
    # "Remote Networks",    # CAN have security policies - commented out
    # "Mobile Users",       # CAN have security policies - commented out
}

# Skip reserved infrastructure-only folders
if folder_name in RESERVED_FOLDERS:
    print(f"  ℹ Skipping reserved folder: {folder_name} (infrastructure only, cannot have security policies)")
    continue
```

**Effect:** Prevents reserved folders from appearing in the list of folders to pull.

---

### **Layer 2: Profile Capture Defensive Check**
**File:** `prisma/pull/profile_capture.py` (Line 153+)

```python
def capture_all_profiles(self, folder: Optional[str] = None) -> Dict[str, Any]:
    # Reserved/infrastructure folders that cannot have security profiles
    RESERVED_FOLDERS = {
        "Service Connections",  # Infrastructure only - cannot have security policies
        "Colo Connect",         # Infrastructure only - cannot have security policies
        # "Remote Networks",    # CAN have security policies - commented out
        # "Mobile Users",       # CAN have security policies - commented out
    }
    
    # Return empty profiles if this is a reserved folder
    if folder and folder in RESERVED_FOLDERS:
        print(f"  ℹ Skipping reserved infrastructure folder: {folder} (cannot have security profiles)")
        return {
            "authentication_profiles": [],
            "security_profiles": {},
            "decryption_profiles": [],
        }
```

**Effect:** If a reserved folder somehow gets through Layer 1, return empty results instead of making API calls.

---

### **Layer 3: Object Capture Defensive Check**
**File:** `prisma/pull/object_capture.py` (Line 193+)

```python
def capture_all_objects(self, folder: Optional[str] = None, ...) -> Dict[str, List[Dict[str, Any]]]:
    # Reserved/infrastructure folders that cannot have security objects
    RESERVED_FOLDERS = {
        "Service Connections",  # Infrastructure only - cannot have security policies
        "Colo Connect",         # Infrastructure only - cannot have security policies
        # "Remote Networks",    # CAN have security policies - commented out
        # "Mobile Users",       # CAN have security policies - commented out
    }
    
    # Return empty objects if this is a reserved folder
    if folder and folder in RESERVED_FOLDERS:
        print(f"  ℹ Skipping reserved infrastructure folder: {folder} (cannot have security objects)")
        return {
            "address_objects": [],
            "address_groups": [],
            # ... etc
        }
```

**Effect:** Prevents any security object queries to reserved folders.

---

## 🛡️ Why Three Layers?

**Defense in Depth:** Even if:
1. The folder list somehow includes reserved folders, OR
2. The GUI or orchestrator passes a reserved folder name directly, OR
3. A future code change bypasses the folder list

The system will **never attempt API calls** to reserved folders for security policies/objects/profiles.

---

## 📋 Folder Classification

| Folder Name | Purpose | Can Have Security Policies? |
|-------------|---------|----------------------------|
| Service Connections | Infrastructure tunnels | ❌ No - Infrastructure only |
| Colo Connect | Colo connectivity | ❌ No - Infrastructure only |
| Remote Networks | Site-to-site VPN | ✅ **YES** - Can have policies |
| Mobile Users | Mobile user settings | ✅ **YES** - Can have policies |
| Mobile_User_Template | Mobile user template | ⚠️ Unknown (commented out) |
| Shared | Default shared folder | ✅ **YES** - Can have policies |

**Note:** Only "Service Connections" and "Colo Connect" are blocked. All others can have security policies.

---

## 🧪 Testing

### **Before Fix:**
```bash
./run_gui_wayland.sh
# → Segfault after trying "Service Connections"
```

### **After Fix:**
```bash
./run_gui_wayland.sh
# → Should show:
#   ℹ Skipping reserved folder: Service Connections (infrastructure only, cannot have security policies)
#   ℹ Skipping reserved folder: Colo Connect (infrastructure only, cannot have security policies)
#   ✓ Pulling folders: Remote Networks, Mobile Users, Shared, [others]
#   ✓ Pull completed successfully
```

---

## ✅ Expected Behavior

1. **Folder Discovery:** Only "Service Connections" and "Colo Connect" are filtered out
2. **Pull Process:** All other folders (including Remote Networks, Mobile Users) are queried
3. **No API Errors:** No more pattern validation errors from Service Connections/Colo Connect
4. **No Segfaults:** No retry loops that lead to crashes

---

## 🎯 Result

**GUI should now be stable** when pulling configurations, as it will:
- Skip only true infrastructure-only folders (Service Connections, Colo Connect)
- Process all security policy folders (including Remote Networks, Mobile Users)
- Never make invalid API calls
- Complete pulls without crashes

---

**Status:** ✅ Fixed in three layers (folder_capture.py, profile_capture.py, object_capture.py)

**Blocked Folders:** Service Connections, Colo Connect only

**Test Command:**
```bash
./run_gui_wayland.sh
# or
./run_gui_offscreen.sh
```
