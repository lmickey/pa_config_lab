# API Endpoints Update

## Changes Made

### 1. Separated Strata and SASE API Base URLs ✅

**Previous**: Single BASE_URL for all endpoints  
**Updated**: Two separate base URLs:

- **Strata API**: `https://api.strata.paloaltonetworks.com/config/v1`
  - Used for: Folders endpoint
  
- **SASE API**: `https://api.sase.paloaltonetworks.com/sse/config/v1`
  - Used for: Security rules, objects, profiles, infrastructure, etc.

### 2. Updated Endpoint Mappings ✅

#### Strata API Endpoints
- `/folders` - List and get folders

#### SASE API Endpoints
- `/security-rules` - Security rules (with folder query parameter)
- `/addresses` - Address objects
- `/address-groups` - Address groups
- `/services` - Service objects
- `/service-groups` - Service groups
- `/applications` - Application objects
- `/application-groups` - Application groups
- `/application-filters` - Application filters
- `/url-categories` - URL categories
- `/external-dynamic-lists` - External dynamic lists
- `/fqdn` - FQDN objects
- `/authentication-profiles` - Authentication profiles
- `/security-profiles/{type}` - Security profiles
- `/decryption-profiles/{type}` - Decryption profiles
- `/ike-crypto-profiles` - IKE crypto profiles
- `/ipsec-crypto-profiles` - IPSec crypto profiles
- `/ike-gateways` - IKE gateways
- `/ipsec-tunnels` - IPSec tunnels
- `/service-connections` - Service connections
- `/remote-networks` - Remote networks
- `/shared-infrastructure-settings` - Infrastructure settings
- `/mobile-agent/infrastructure-settings` - Mobile agent settings

### 3. Folder Query Parameter Encoding ✅

Updated `build_folder_query()` function to properly URL encode folder names:
- Input: `"Mobile Users"`
- Output: `"?folder=Mobile%20Users"`

This ensures folder names with spaces are properly encoded in API requests.

## Example Usage

### Security Rules Endpoint
```
GET https://api.sase.paloaltonetworks.com/sse/config/v1/security-rules?folder=Mobile%20Users
```

### Folders Endpoint
```
GET https://api.strata.paloaltonetworks.com/config/v1/folders
```

## Impact

All API client methods now use the correct base URLs:
- `get_security_policy_folders()` → Strata API
- `get_security_rules(folder="Mobile Users")` → SASE API with encoded folder
- All object/profile endpoints → SASE API

## Testing

The test script will now:
1. Use Strata API to discover folders
2. Use SASE API with properly encoded folder names for security rules
3. Use SASE API for all objects and profiles

## Notes

- Folder names are automatically URL encoded when building query strings
- The API client handles both Strata and SASE API calls seamlessly
- All endpoints are properly categorized by API type
