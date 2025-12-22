# IPsec Tunnels & IKE Gateways - Folder Requirement

**Date:** December 21, 2025  
**Issue:** IPsec Tunnels and IKE Gateways returned 400 Bad Request without folder parameter

---

## ❌ **Problem:**

```
📍 IPsec Tunnels
   Method: get_all_ipsec_tunnels
   Status: 400
   Error: 400 Client Error: Bad Request for url: 
         https://api.sase.paloaltonetworks.com/sse/config/v1/ipsec-tunnels
```

The API requires a `folder` query parameter for these endpoints.

---

## ✅ **Solution:**

These endpoints **require** a folder parameter:
- IPsec Tunnels → "Service Connections"
- IKE Gateways → "Service Connections"
- IKE Crypto Profiles → "Service Connections"
- IPsec Crypto Profiles → "Service Connections"
- HIP Objects → "Mobile Users"
- HIP Profiles → "Mobile Users"

---

## 📝 **Updated Validator:**

Changed from:
```python
("IPsec Tunnels", "get_all_ipsec_tunnels", {}),
("IKE Gateways", "get_all_ike_gateways", {}),
```

To:
```python
("IPsec Tunnels", "get_all_ipsec_tunnels", {"folder": "Service Connections"}),
("IKE Gateways", "get_all_ike_gateways", {"folder": "Service Connections"}),
("IKE Crypto Profiles", "get_all_ike_crypto_profiles", {"folder": "Service Connections"}),
("IPsec Crypto Profiles", "get_all_ipsec_crypto_profiles", {"folder": "Service Connections"}),
```

---

## 💡 **Why "Service Connections"?**

- Service Connections folder is where IPsec tunnels and IKE gateways are typically configured
- More likely to have existing tunnels/gateways than other folders
- Better test coverage for validation

---

## 🧪 **Testing:**

```bash
python3 validate_endpoints.py 1570970024 cursor-dev@1570970024.iam.panserviceaccount.com
```

Expected results:
- ✅ IPsec Tunnels (folder=Service Connections) - 200 OK
- ✅ IKE Gateways (folder=Service Connections) - 200 OK
- ✅ IKE Crypto Profiles (folder=Service Connections) - 200 OK
- ✅ IPsec Crypto Profiles (folder=Service Connections) - 200 OK

---

## 📋 **API Methods:**

The existing methods already support the folder parameter:

```python
def get_all_ipsec_tunnels(self, folder: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all IPsec tunnels with automatic pagination."""
    def api_func(offset=0, limit=100):
        return self.get_ipsec_tunnels(folder=folder, limit=limit, offset=offset)
    return paginate_api_request(api_func)
```

No code changes needed - just need to pass the folder parameter when calling.

---

**Status:** ✅ Validator updated with folder parameter
