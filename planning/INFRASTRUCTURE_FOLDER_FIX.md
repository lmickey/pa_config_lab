# Infrastructure Capture - Folder Requirements Fix

**Date:** December 21, 2025  
**Issue:** IPsec tunnels failed with "Folder undefined doesn't exist"

---

## 🐛 **Problem:**

The GUI infrastructure capture was calling:
```python
capture_ipsec_tunnels(folder=None)
```

But IPsec tunnels **require** a folder parameter. When `folder=None`, the API interprets it as "undefined" and returns a 400 error.

---

## ✅ **Solution:**

### **1. IPsec Tunnels - Multi-Folder Capture**

IPsec tunnels can exist in multiple folders:
- "Service Connections" (for service connection tunnels)
- "Remote Networks" (for remote network tunnels)

**Updated method signature:**
```python
def capture_ipsec_tunnels(self, folders: Optional[List[str]] = None) -> Dict[str, Any]:
    # Defaults to checking both folders
    if folders is None:
        folders = ["Service Connections", "Remote Networks"]
```

**Now captures from both folders and combines results.**

---

### **2. HIP Objects/Profiles - Default to Mobile Users**

HIP objects and profiles are always in the "Mobile Users" folder.

**Updated call:**
```python
hip_data = self.capture_hip_objects_and_profiles(folder="Mobile Users")
```

---

### **3. Mobile User Infrastructure - Updated to New Endpoints**

Replaced deprecated GlobalProtect methods with new mobile agent methods:

**Before (deprecated):**
```python
result["gp_gateways"] = self.api_client.get_all_globalprotect_gateways()
result["gp_portals"] = self.api_client.get_all_globalprotect_portals()
```

**After (correct):**
```python
result["agent_profiles"] = self.api_client.get_mobile_agent_profiles(folder="Mobile Users")
result["agent_versions"] = self.api_client.get_mobile_agent_versions(folder="Mobile Users")
result["authentication_settings"] = self.api_client.get_mobile_agent_auth_settings(folder="Mobile Users")
result["enable"] = self.api_client.get_mobile_agent_enable(folder="Mobile Users")
result["global_settings"] = self.api_client.get_mobile_agent_global_settings(folder="Mobile Users")
result["infrastructure_settings"] = self.api_client.get_mobile_agent_infra_settings(folder="Mobile Users")
result["locations"] = self.api_client.get_mobile_agent_locations(folder="Mobile Users")
result["tunnel_profiles"] = self.api_client.get_mobile_agent_tunnel_profiles(folder="Mobile Users")
```

---

## 📋 **Folder Requirements Summary:**

| Component | Folders | Default Behavior |
|-----------|---------|------------------|
| **IPsec Tunnels** | Service Connections, Remote Networks | Checks both folders |
| **IKE Gateways** | Service Connections, Remote Networks | Checks both folders |
| **IKE Crypto Profiles** | Service Connections, Remote Networks | Checks both folders |
| **IPsec Crypto Profiles** | Service Connections, Remote Networks | Checks both folders |
| **HIP Objects** | Mobile Users | Fixed to Mobile Users |
| **HIP Profiles** | Mobile Users | Fixed to Mobile Users |
| **Mobile Agent (all)** | Mobile Users | Fixed to Mobile Users |
| **Remote Networks** | N/A | No folder required |
| **Service Connections** | N/A | No folder required |
| **Bandwidth/Locations** | N/A | No folder required |

---

## 🧪 **Testing:**

Run the GUI pull again with infrastructure options enabled:

```bash
./run_gui_wayland.sh
```

**Expected behavior:**
1. ✓ Captures IPsec tunnels from "Service Connections" folder
2. ✓ Captures IPsec tunnels from "Remote Networks" folder
3. ✓ Combines results from both folders
4. ✓ Captures HIP objects/profiles from "Mobile Users" folder
5. ✓ Captures all mobile agent settings from "Mobile Users" folder
6. ✓ No "Folder undefined" errors

---

## 🔍 **Error Handling:**

The updated code gracefully handles:
- Folders that don't exist (skips with info message)
- Folders that can't have tunnels (skips with info message)
- API errors (logs warning, continues to next folder)

**No more crashes from missing folders!**

---

**Status:** ✅ Fixed - Infrastructure capture now uses correct folders for all components
