# Reserved Folder Fix - Complete Implementation

**Date:** December 21, 2025  
**Status:** ✅ IMPLEMENTED

---

## 🎯 Problem

GUI was segfaulting because it attempted to query "Service Connections" and "Colo Connect" folders for security policies/objects/profiles. These are infrastructure-only folders that:
1. Cannot have security policies
2. Return API 400 errors with pattern validation failures
3. Caused infinite retry loops → segfaults

---

## ✅ Solution - Multi-Layer Defense

### **Layer 1: Folder Discovery** (`folder_capture.py`)
Filters out reserved folders from the folder list.

### **Layer 2: Profile Capture** (`profile_capture.py`)
Added early returns in **all** profile capture methods:
- `capture_authentication_profiles()` 
- `capture_security_profiles()`
- `capture_decryption_profiles()`
- `capture_all_profiles()`

### **Layer 3: Object Capture** (`object_capture.py`)
Added early returns in **all** object capture methods:
- `capture_addresses()`
- `capture_address_groups()`
- `capture_services()`
- `capture_service_groups()`
- `capture_applications()`
- `capture_all_objects()`

---

## 🔒 Reserved Folders (Blocked)

```python
RESERVED_FOLDERS = {
    "Service Connections",  # Infrastructure only
    "Colo Connect",         # Infrastructure only
}
```

**NOT blocked (can have policies):**
- "Remote Networks" ✅
- "Mobile Users" ✅
- "Shared" ✅

---

## 🧪 Verification

```bash
python3 -c "
from prisma.pull.profile_capture import ProfileCapture
from prisma.pull.object_capture import ObjectCapture

pc = ProfileCapture(None)
print(pc.capture_authentication_profiles(folder='Service Connections'))
# Returns: []

oc = ObjectCapture(None)
print(oc.capture_addresses(folder='Service Connections'))
# Returns: []
"
```

---

## 🚀 Test Command

```bash
./run_gui_wayland.sh
```

**Expected:**
- No API errors for "Service Connections" or "Colo Connect"
- No segfaults
- Successful configuration pull

---

**Status:** ✅ Ready to test
