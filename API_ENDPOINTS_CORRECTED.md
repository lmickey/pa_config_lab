# API Endpoints Correction Summary

## Issue Identified

The API endpoints were not correctly aligned with Prisma Access API structure:
- Folders endpoint was using wrong base URL
- Security rules endpoint path was incorrect
- Folder parameter encoding needed adjustment

## Corrections Made

### 1. Separated Strata and SASE API Base URLs ✅

**Strata API** (`https://api.strata.paloaltonetworks.com/config/v1`):
- Used for: **Folders** endpoint only
- Endpoint: `/folders`

**SASE API** (`https://api.sase.paloaltonetworks.com/sse/config/v1`):
- Used for: Security rules, objects, profiles, infrastructure
- Endpoints: `/security-rules`, `/addresses`, `/services`, `/applications`, etc.

### 2. Updated Folder Endpoint ✅

**Before**: `https://api.sase.paloaltonetworks.com/sse/config/v1/security-policy/folders`  
**After**: `https://api.strata.paloaltonetworks.com/config/v1/folders`

### 3. Updated Security Rules Endpoint ✅

**Before**: `https://api.sase.paloaltonetworks.com/sse/config/v1/security-policy/security-rules`  
**After**: `https://api.sase.paloaltonetworks.com/sse/config/v1/security-rules`

**Note**: Folder is specified as query parameter: `?folder=Mobile%20Users`

### 4. Fixed Folder Parameter Encoding ✅

Updated `build_folder_query()` to use `%20` encoding for spaces:
- Input: `"Mobile Users"`
- Output: `"?folder=Mobile%20Users"`

## Correct API Usage Examples

### Get Folders (Strata API)
```
GET https://api.strata.paloaltonetworks.com/config/v1/folders
```

### Get Security Rules (SASE API)
```
GET https://api.sase.paloaltonetworks.com/sse/config/v1/security-rules?folder=Mobile%20Users
```

### Get Addresses (SASE API)
```
GET https://api.sase.paloaltonetworks.com/sse/config/v1/addresses?folder=Access%20Agent
```

## Updated Code

### api_endpoints.py
- Added `STRATA_BASE_URL` and `SASE_BASE_URL` constants
- Updated all endpoints to use correct base URLs
- Fixed `build_folder_query()` to use `%20` encoding

### api_client.py
- Uses Strata API for `get_security_policy_folders()`
- Uses SASE API for `get_security_rules()` with folder parameter
- All other endpoints use SASE API

## Testing

All endpoints now correctly use:
- ✅ Strata API for folders
- ✅ SASE API for security rules with properly encoded folder names
- ✅ SASE API for all objects and profiles

## Impact

- Folder discovery now uses correct Strata API endpoint
- Security rules retrieval uses correct SASE API endpoint with folder parameter
- Folder names are properly URL encoded (`%20` for spaces)
- All other endpoints correctly use SASE API
