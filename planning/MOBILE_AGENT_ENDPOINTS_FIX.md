# Mobile Agent API Endpoints - Correction

**Date:** December 21, 2025  
**Issue:** GlobalProtect Portals and Gateways endpoints returned 404

---

## ❌ **Old (Incorrect) Endpoints:**

```python
GLOBALPROTECT_PORTALS = "/sse/config/v1/mobile-agent/portals"   # 404
GLOBALPROTECT_GATEWAYS = "/sse/config/v1/mobile-agent/gateways" # 404
```

These endpoints don't exist. GlobalProtect configuration is split across **8 separate mobile-agent endpoints**.

---

## ✅ **New (Correct) Endpoints:**

GlobalProtect/Mobile User configuration is now split into:

| Endpoint | Purpose | Documentation |
|----------|---------|---------------|
| `/sse/config/v1/mobile-agent/agent-profiles` | Agent profile settings | [Docs](https://pan.dev/access/api/prisma-access-config/get-sse-config-v-1-mobile-agent-agent-profiles/) |
| `/sse/config/v1/mobile-agent/agent-versions` | Agent version management | [Docs](https://pan.dev/access/api/prisma-access-config/get-sse-config-v-1-mobile-agent-agent-versions/) |
| `/sse/config/v1/mobile-agent/authentication-settings` | Authentication config | [Docs](https://pan.dev/access/api/prisma-access-config/get-sse-config-v-1-mobile-agent-authentication-settings/) |
| `/sse/config/v1/mobile-agent/enable` | Enable/disable mobile agent | [Docs](https://pan.dev/access/api/prisma-access-config/get-sse-config-v-1-mobile-agent-enable/) |
| `/sse/config/v1/mobile-agent/global-settings` | Global settings | [Docs](https://pan.dev/access/api/prisma-access-config/get-sse-config-v-1-mobile-agent-global-settings/) |
| `/sse/config/v1/mobile-agent/infrastructure-settings` | Infrastructure config | [Docs](https://pan.dev/access/api/prisma-access-config/get-sse-config-v-1-mobile-agent-infrastructure-settings/) |
| `/sse/config/v1/mobile-agent/locations` | Location settings | [Docs](https://pan.dev/access/api/prisma-access-config/get-sse-config-v-1-mobile-agent-locations/) |
| `/sse/config/v1/mobile-agent/tunnel-profiles` | Tunnel profile config | [Docs](https://pan.dev/access/api/prisma-access-config/get-sse-config-v-1-mobile-agent-tunnel-profiles/) |

---

## 📝 **Changes Made:**

### **1. `prisma/api_endpoints.py`**
Replaced:
```python
GLOBALPROTECT_GATEWAYS = f"{SASE_BASE_URL}/mobile-agent/gateways"
GLOBALPROTECT_PORTALS = f"{SASE_BASE_URL}/mobile-agent/portals"
```

With:
```python
MOBILE_AGENT_PROFILES = f"{SASE_BASE_URL}/mobile-agent/agent-profiles"
MOBILE_AGENT_VERSIONS = f"{SASE_BASE_URL}/mobile-agent/agent-versions"
MOBILE_AGENT_AUTH_SETTINGS = f"{SASE_BASE_URL}/mobile-agent/authentication-settings"
MOBILE_AGENT_ENABLE = f"{SASE_BASE_URL}/mobile-agent/enable"
MOBILE_AGENT_GLOBAL_SETTINGS = f"{SASE_BASE_URL}/mobile-agent/global-settings"
MOBILE_AGENT_INFRA_SETTINGS = f"{SASE_BASE_URL}/mobile-agent/infrastructure-settings"
MOBILE_AGENT_LOCATIONS = f"{SASE_BASE_URL}/mobile-agent/locations"
MOBILE_AGENT_TUNNEL_PROFILES = f"{SASE_BASE_URL}/mobile-agent/tunnel-profiles"
```

### **2. `prisma/api_client.py`**
Added 8 new methods:
- `get_mobile_agent_profiles()`
- `get_mobile_agent_versions()`
- `get_mobile_agent_auth_settings()`
- `get_mobile_agent_enable()`
- `get_mobile_agent_global_settings()`
- `get_mobile_agent_infra_settings()`
- `get_mobile_agent_locations()`
- `get_mobile_agent_tunnel_profiles()`

Deprecated old methods:
- `get_all_globalprotect_portals()` - marked as DEPRECATED
- `get_all_globalprotect_gateways()` - marked as DEPRECATED

### **3. `validate_endpoints.py`**
Updated test endpoints to use new mobile agent methods.

---

## 🧪 **Testing:**

Run the validator to confirm all endpoints work:

```bash
python3 validate_endpoints.py 1570970024 cursor-dev@1570970024.iam.panserviceaccount.com
```

Expected results:
- ✅ Mobile Agent Profiles - 200 OK
- ✅ Mobile Agent Versions - 200 OK
- ✅ Mobile Agent Auth Settings - 200 OK
- ✅ Mobile Agent Enable - 200 OK
- ✅ Mobile Agent Global Settings - 200 OK
- ✅ Mobile Agent Infra Settings - 200 OK
- ✅ Mobile Agent Locations - 200 OK
- ✅ Mobile Agent Tunnel Profiles - 200 OK

---

## 📋 **Next Steps:**

1. Run validator to identify any remaining 404 endpoints
2. Update `infrastructure_capture.py` to use new mobile agent methods
3. Update schema to match new mobile agent response structures

---

**Status:** ✅ Endpoints corrected, ready for testing
