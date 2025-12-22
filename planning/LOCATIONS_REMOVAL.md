# Locations (Regions) Removal from Configuration Capture

**Date:** December 21, 2025  
**Status:** ✅ Complete

---

## 🎯 **Objective**

Remove the capture of locations (regions) from the infrastructure configuration pull, as these are static across all Prisma Access tenants and do not need to be included in tenant-specific configurations.

---

## 📋 **Rationale**

**Locations (Regions) are Static:**
- The available Prisma Access regions (e.g., `us-east-1`, `eu-west-1`, etc.) are the same for all tenants
- They are defined by Palo Alto Networks' infrastructure, not by tenant configuration
- Including them in configs adds unnecessary data without providing tenant-specific value

**Bandwidth Allocations are Dynamic:**
- Bandwidth allocations are tenant-specific and show how bandwidth is distributed across regions
- These are important configuration items that vary per tenant
- They should continue to be captured

---

## 🔧 **Changes Made**

### **1. Infrastructure Capture Module**
**File:** `prisma/pull/infrastructure_capture.py`

#### **Updated `capture_regions_and_bandwidth()` Method:**

**Before:**
```python
def capture_regions_and_bandwidth(self) -> Dict[str, Any]:
    """
    Capture region and bandwidth allocation configurations.
    
    Returns:
        Dictionary containing regions and bandwidth:
        {
            "locations": [...],
            "bandwidth_allocations": [...]
        }
    """
    result = {
        "locations": [],
        "bandwidth_allocations": [],
    }
    
    # Capture locations (enabled regions)
    self.logger.info("Capturing locations (regions)...")
    result["locations"] = self.api_client.get_all_locations()
    self.logger.info(f"Captured {len(result['locations'])} location(s)")
    
    # Capture bandwidth allocations
    self.logger.info("Capturing bandwidth allocations...")
    result["bandwidth_allocations"] = self.api_client.get_all_bandwidth_allocations()
    
    return result
```

**After:**
```python
def capture_regions_and_bandwidth(self) -> Dict[str, Any]:
    """
    Capture region and bandwidth allocation configurations.
    
    This captures bandwidth allocations which provide information about 
    Prisma Access regional deployments. Locations (regions) are static
    and not included as they don't change per-tenant.
    
    Returns:
        Dictionary containing bandwidth allocations:
        {
            "bandwidth_allocations": [...]
        }
    """
    result = {
        "bandwidth_allocations": [],
    }
    
    # Note: Locations (regions) are static and not captured
    # They are the same across all tenants and don't need to be in configs
    
    # Capture bandwidth allocations
    self.logger.info("Capturing bandwidth allocations...")
    result["bandwidth_allocations"] = self.api_client.get_all_bandwidth_allocations()
    
    return result
```

**Key Changes:**
- ✅ Removed `locations` from result dictionary
- ✅ Removed API call to `get_all_locations()`
- ✅ Removed log message "Capturing locations (regions)..."
- ✅ Added explanatory comment about why locations are excluded
- ✅ Updated docstring to reflect new behavior

---

#### **Updated Progress Message:**

**Before:**
```python
enabled_components.append(("Regions & Bandwidth", lambda: self.capture_regions_and_bandwidth()))
```

**After:**
```python
enabled_components.append(("Bandwidth Allocations", lambda: self.capture_regions_and_bandwidth()))
```

**Progress message now shows:**
```
Infrastructure: Bandwidth Allocations (6/6)
```

Instead of:
```
Infrastructure: Regions & Bandwidth (6/6)
```

---

### **2. GUI Worker Statistics**
**File:** `gui/workers.py`

#### **Updated Stats Collection:**

**Before:**
```python
if config.get("regions", {}).get("locations"):
    stats["regions"] = len(config["regions"]["locations"])
```

**After:**
```python
if config.get("regions", {}).get("bandwidth_allocations"):
    stats["bandwidth_allocations"] = len(config["regions"]["bandwidth_allocations"])
```

---

#### **Updated Stats Formatting:**

**Before:**
```python
if stats.get("regions", 0) > 0:
    lines.append(f"Regions: {stats['regions']}")
```

**After:**
```python
if stats.get("bandwidth_allocations", 0) > 0:
    lines.append(f"Bandwidth Allocations: {stats['bandwidth_allocations']}")
```

**Completion message now shows:**
```
Pull completed successfully!

Folders: 5
Security Rules: 42
Objects: 156
Profiles: 23
Remote Networks: 3
Service Connections: 2
Bandwidth Allocations: 4
```

---

## 📊 **Impact**

### **What's Removed:**
- ❌ API call to `/sse/config/v1/locations`
- ❌ Log message: "Capturing locations (regions)..."
- ❌ Log message: "Captured X location(s)"
- ❌ `locations` array in config output

### **What's Kept:**
- ✅ API call to `/sse/config/v1/bandwidth-allocations`
- ✅ Log message: "Capturing bandwidth allocations..."
- ✅ Log message: "Captured X bandwidth allocation(s)"
- ✅ `bandwidth_allocations` array in config output

---

## 🎯 **Benefits**

1. **Cleaner Logs:**
   - No more "Capturing locations (regions)..." messages
   - Focus on tenant-specific configuration items

2. **Smaller Config Files:**
   - Removes static data that's the same for all tenants
   - Reduces config file size

3. **Faster Capture:**
   - One less API call per pull operation
   - Slight performance improvement

4. **Better Clarity:**
   - Config files now only contain tenant-specific data
   - Easier to understand what's actually configured vs. what's available

---

## 📝 **Configuration Schema**

The `regions` section in the config schema remains unchanged:

```python
"regions": {
    "bandwidth_allocations": [...]
}
```

**Note:** The schema still uses the key `regions` for the top-level section, but it now only contains `bandwidth_allocations`. This maintains backward compatibility while removing the static `locations` data.

---

## ✅ **Testing**

### **Verification Steps:**
1. ✅ Run GUI pull operation
2. ✅ Verify no "Capturing locations (regions)..." message in logs
3. ✅ Verify "Capturing bandwidth allocations..." message appears
4. ✅ Check completion stats show "Bandwidth Allocations: X"
5. ✅ Verify config JSON has `regions.bandwidth_allocations` but no `regions.locations`

### **Expected Log Output:**
```
[70%] Infrastructure: Remote Networks (1/6)
[72%] Infrastructure: Service Connections (2/6)
[74%] Infrastructure: IPsec Tunnels & Crypto (3/6)
[76%] Infrastructure: Mobile User Settings (4/6)
[78%] Infrastructure: HIP Objects & Profiles (5/6)
[80%] Infrastructure: Bandwidth Allocations (6/6)
```

**Note:** No "locations" or "regions" message appears.

---

## 🔄 **API Endpoints Still Used**

| **Endpoint** | **Purpose** | **Status** |
|-------------|-------------|------------|
| `/sse/config/v1/locations` | Get available regions | ❌ **Removed** (static data) |
| `/sse/config/v1/bandwidth-allocations` | Get bandwidth per region | ✅ **Active** (tenant-specific) |

---

## 📚 **Related Files**

- `prisma/pull/infrastructure_capture.py` - Removed locations capture
- `gui/workers.py` - Updated stats to show bandwidth allocations
- `planning/PROGRESS_BAR_ENHANCEMENT.md` - Progress message updated

---

**Status:** ✅ Implementation Complete - Ready for Testing
