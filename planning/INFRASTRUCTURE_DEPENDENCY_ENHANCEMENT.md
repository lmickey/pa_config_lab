# Infrastructure Dependency Enhancement - Complete

**Date**: December 23, 2025  
**Status**: ✅ **COMPLETE**

## Overview

Enhanced the `DependencyResolver` to analyze infrastructure component dependencies, enabling automatic detection and inclusion of required infrastructure items (IKE Gateways, Crypto Profiles, IPSec Tunnels, etc.) when selecting service connections or remote networks.

---

## Changes Made

### 1. **Added Infrastructure Dependency Processing**

**File**: `prisma/dependencies/dependency_resolver.py`

**New Method**: `_process_infrastructure_dependencies()`

Processes infrastructure components and their dependencies:

#### **IKE Crypto Profiles** (No dependencies)
- Added as nodes in dependency graph
- Type: `ike_crypto_profile`

#### **IPSec Crypto Profiles** (No dependencies)
- Added as nodes in dependency graph
- Type: `ipsec_crypto_profile`

#### **IKE Gateways** → IKE Crypto Profile
- Depends on IKE Crypto Profile (from `protocol.ikev1.ike_crypto_profile` or `protocol.ikev2.ike_crypto_profile`)
- Type: `ike_gateway`
- Dependency: `ike_gateway` → `ike_crypto_profile`

#### **IPSec Tunnels** → IKE Gateway + IPSec Crypto Profile
- Depends on IKE Gateway (from `auto_key.ike_gateway`)
- Depends on IPSec Crypto Profile (from `auto_key.ipsec_crypto_profile`)
- Type: `ipsec_tunnel`
- Dependencies:
  - `ipsec_tunnel` → `ike_gateway`
  - `ipsec_tunnel` → `ipsec_crypto_profile`

#### **Service Connections** → IPSec Tunnel
- Depends on IPSec Tunnel (from `ipsec_tunnel` field)
- Type: `service_connection`
- Dependency: `service_connection` → `ipsec_tunnel`

#### **Remote Networks** → IPSec Tunnel
- Depends on IPSec Tunnel (from `ipsec_tunnel` field)
- Type: `remote_network`
- Dependency: `remote_network` → `ipsec_tunnel`

---

### 2. **Integrated Infrastructure into Dependency Graph**

Updated `build_dependency_graph()` to process infrastructure:

```python
# Process infrastructure
if "infrastructure" in config:
    self._process_infrastructure_dependencies(config["infrastructure"])
```

---

### 3. **Enhanced Dependency Search**

Updated `find_required_dependencies()` to search for infrastructure items in full config:

```python
# Search in infrastructure
elif dep_type in ['ike_crypto_profile', 'ipsec_crypto_profile', 'ike_gateway', 
                 'ipsec_tunnel', 'service_connection', 'remote_network']:
    infrastructure = full_config.get('infrastructure', {})
    
    # Map dependency types to infrastructure keys
    type_map = {
        'ike_crypto_profile': 'ike_crypto_profiles',
        'ipsec_crypto_profile': 'ipsec_crypto_profiles',
        'ike_gateway': 'ike_gateways',
        'ipsec_tunnel': 'ipsec_tunnels',
        'service_connection': 'service_connections',
        'remote_network': 'remote_networks'
    }
    
    # Find and add to required dependencies
```

---

## Dependency Chains

### **Service Connection Dependency Chain**

```
Service Connection
    └─→ IPSec Tunnel
            ├─→ IKE Gateway
            │       └─→ IKE Crypto Profile
            └─→ IPSec Crypto Profile
```

**Example**:
1. User selects: `Service Connection: "AWS-Connection"`
2. System detects dependencies:
   - IPSec Tunnel: `AWS-Tunnel`
   - IKE Gateway: `AWS-Gateway`
   - IKE Crypto Profile: `default-ikev2`
   - IPSec Crypto Profile: `default-ipsec`
3. Dependency dialog shows all 4 required items
4. User confirms, all 5 items are included in push

### **Remote Network Dependency Chain**

```
Remote Network
    └─→ IPSec Tunnel
            ├─→ IKE Gateway
            │       └─→ IKE Crypto Profile
            └─→ IPSec Crypto Profile
```

---

## Testing Scenarios

### **Test 1: Service Connection with Dependencies**

**Setup**:
- Service Connection: `SC-1` → IPSec Tunnel: `Tunnel-1`
- IPSec Tunnel: `Tunnel-1` → IKE Gateway: `Gateway-1`, IPSec Crypto: `Crypto-1`
- IKE Gateway: `Gateway-1` → IKE Crypto: `IKE-Crypto-1`

**Test**:
1. Select only `SC-1`
2. Click OK

**Expected**:
- Dependency dialog shows:
  - IPSec Tunnel: `Tunnel-1`
  - IKE Gateway: `Gateway-1`
  - IKE Crypto Profile: `IKE-Crypto-1`
  - IPSec Crypto Profile: `Crypto-1`
- User confirms
- All 5 items included in selection

### **Test 2: IPSec Tunnel with Dependencies**

**Setup**:
- IPSec Tunnel: `Tunnel-2` → IKE Gateway: `Gateway-2`, IPSec Crypto: `Crypto-2`
- IKE Gateway: `Gateway-2` → IKE Crypto: `IKE-Crypto-2`

**Test**:
1. Select only `Tunnel-2`
2. Click OK

**Expected**:
- Dependency dialog shows:
  - IKE Gateway: `Gateway-2`
  - IKE Crypto Profile: `IKE-Crypto-2`
  - IPSec Crypto Profile: `Crypto-2`
- User confirms
- All 4 items included in selection

### **Test 3: IKE Gateway with Dependencies**

**Setup**:
- IKE Gateway: `Gateway-3` → IKE Crypto: `IKE-Crypto-3`

**Test**:
1. Select only `Gateway-3`
2. Click OK

**Expected**:
- Dependency dialog shows:
  - IKE Crypto Profile: `IKE-Crypto-3`
- User confirms
- Both items included in selection

### **Test 4: Crypto Profiles (No Dependencies)**

**Test**:
1. Select IKE Crypto Profile: `Custom-IKE`
2. Click OK

**Expected**:
- No dependency dialog (crypto profiles have no dependencies)
- Proceeds directly to push

---

## Limitations & Future Enhancements

### **Current Limitations**:

1. **BGP Peer Dependencies**: Not yet analyzed
   - Service Connections may have BGP peer configurations
   - BGP peer dependencies are complex and require further analysis

2. **Mobile Users Dependencies**: Not yet analyzed
   - Agent profiles, authentication settings, etc.
   - May have dependencies on authentication profiles, certificates, etc.

3. **Snippet Dependencies**: Minimal analysis
   - Snippets are treated as standalone items
   - May reference other configuration elements

### **Future Enhancements**:

1. **BGP Peer Analysis**
   - Analyze BGP peer configurations in service connections
   - Detect dependencies on routing configurations

2. **Mobile Users Analysis**
   - Analyze mobile user agent profiles
   - Detect dependencies on authentication profiles
   - Detect dependencies on certificates

3. **Snippet Enhancement**
   - Analyze snippet contents for references
   - Detect dependencies on other snippets or configuration items

4. **Circular Dependency Detection**
   - Enhanced detection of circular dependencies
   - Better error messages for circular dependency scenarios

---

## Files Modified

1. **`prisma/dependencies/dependency_resolver.py`**
   - Added `_process_infrastructure_dependencies()` method
   - Updated `build_dependency_graph()` to process infrastructure
   - Updated `find_required_dependencies()` to search infrastructure

---

## Result

✅ **Infrastructure dependencies now fully analyzed!**

- Service Connections → IPSec Tunnels → IKE Gateways → Crypto Profiles
- Remote Networks → IPSec Tunnels → IKE Gateways → Crypto Profiles
- Automatic detection and inclusion of all required items
- User confirmation via dependency dialog
- Prevents incomplete pushes that would fail due to missing dependencies

---

## Next Steps

1. **Test infrastructure dependency detection** with real configurations
2. **Verify dependency dialog** shows all required items correctly
3. **Test push workflow** with auto-included dependencies
4. **Consider BGP peer analysis** if needed for your use case
5. **Document any edge cases** discovered during testing
