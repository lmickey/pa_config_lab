# Profile Endpoints Update

## Summary

Updated API endpoints for security and decryption profiles to match the master API endpoints list. Only endpoints marked "include in test" are now used in Test 5.

## Changes Made

### 1. Updated API Endpoints (`prisma/api_endpoints.py`)

**Before**: Used `/security-profiles/{type}` format
- `/security-profiles/antivirus`
- `/security-profiles/anti-spyware`
- etc.

**After**: Use individual endpoint format matching Master-API-Entpoint-List.txt
- `/anti-spyware-profiles`
- `/dns-security-profiles`
- `/file-blocking-profiles`
- `/http-header-profiles`
- `/profile-groups`
- `/url-access-profiles`
- `/vulnerability-protection-profiles`
- `/wildfire-anti-virus-profiles`
- `/decryption-profiles`

### 2. Added API Client Methods (`prisma/api_client.py`)

Added methods for all profile types marked "include in test":
- `get_anti_spyware_profiles()`
- `get_dns_security_profiles()`
- `get_file_blocking_profiles()`
- `get_http_header_profiles()`
- `get_profile_groups()`
- `get_url_access_profiles()`
- `get_vulnerability_protection_profiles()`
- `get_wildfire_anti_virus_profiles()`
- `get_decryption_profiles()`

All methods support:
- Folder parameter (with proper %20 encoding)
- Pagination (limit/offset)
- Proper error handling

### 3. Updated Profile Capture (`prisma/pull/profile_capture.py`)

- Updated `capture_security_profiles()` to use correct API client methods
- Updated `capture_all_security_profiles()` to only include profile types marked "include in test"
- Updated `capture_decryption_profiles()` to use single endpoint (not type-specific)
- Updated `capture_all_profiles()` to handle decryption profiles as a list

### 4. Updated Test 5 (`test_phase2.py`)

- Error message now shows all correct API URLs
- Only tests profile types marked "include in test"
- Error logging includes all relevant API URLs

## Profile Types Included in Test 5

Based on Master-API-Entpoint-List.txt (marked "include in test"):

1. **Anti-spyware profiles**: `/anti-spyware-profiles`
2. **DNS security profiles**: `/dns-security-profiles`
3. **File blocking profiles**: `/file-blocking-profiles`
4. **HTTP header profiles**: `/http-header-profiles`
5. **Profile groups**: `/profile-groups`
6. **URL access profiles**: `/url-access-profiles`
7. **Vulnerability protection profiles**: `/vulnerability-protection-profiles`
8. **WildFire antivirus profiles**: `/wildfire-anti-virus-profiles`
9. **Decryption profiles**: `/decryption-profiles`

## Error Message Format

When security profiles = 0, Test 5 shows:

```
✗ FAILED: No security profiles captured from folder 'Mobile Users'
  Expected: At least 1 security profile (default best practice profiles should exist)
  Actual: 0 security profiles

  Security profiles should be available at:
  - Anti-spyware: https://api.sase.paloaltonetworks.com/sse/config/v1/anti-spyware-profiles?folder=Mobile%20Users
  - DNS Security: https://api.sase.paloaltonetworks.com/sse/config/v1/dns-security-profiles?folder=Mobile%20Users
  - File Blocking: https://api.sase.paloaltonetworks.com/sse/config/v1/file-blocking-profiles?folder=Mobile%20Users
  - HTTP Header: https://api.sase.paloaltonetworks.com/sse/config/v1/http-header-profiles?folder=Mobile%20Users
  - Profile Groups: https://api.sase.paloaltonetworks.com/sse/config/v1/profile-groups?folder=Mobile%20Users
  - URL Access: https://api.sase.paloaltonetworks.com/sse/config/v1/url-access-profiles?folder=Mobile%20Users
  - Vulnerability Protection: https://api.sase.paloaltonetworks.com/sse/config/v1/vulnerability-protection-profiles?folder=Mobile%20Users
  - WildFire Anti-Virus: https://api.sase.paloaltonetworks.com/sse/config/v1/wildfire-anti-virus-profiles?folder=Mobile%20Users

  Decryption profiles:
  - Decryption: https://api.sase.paloaltonetworks.com/sse/config/v1/decryption-profiles?folder=Mobile%20Users
```

## Files Modified

1. **prisma/api_endpoints.py**: Updated endpoint definitions
2. **prisma/api_client.py**: Added API client methods for all profile types
3. **prisma/pull/profile_capture.py**: Updated to use correct endpoints and methods
4. **test_phase2.py**: Updated error messages and validation

## Verification

All endpoints verified to match Master-API-Entpoint-List.txt:
- ✅ All 9 profile endpoints correctly formatted
- ✅ All API client methods implemented
- ✅ Profile capture module updated
- ✅ Test 5 error messages show correct URLs
