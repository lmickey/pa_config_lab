# Test Updates Summary

## Changes Made

### 1. Fixed Snippets Endpoint ✅
- **Before**: `https://api.sase.paloaltonetworks.com/sse/config/v1/security-policy/snippets`
- **After**: `https://api.strata.paloaltonetworks.com/config/setup/v1/snippets`
- **Reason**: Snippets endpoint uses Strata API with `/setup/v1/` path, same as folders endpoint

### 2. Added Security Profile Validation ✅
- **Test 5 (Profile Capture)** now fails if no security profiles are found
- **Expected**: At least 1 security profile (default best practice profiles should exist)
- **Error Message**: Shows the API URL that should be used to retrieve security profiles
- **URL Format**: `{SASE_BASE_URL}/security-profiles/{type}?folder={folder_name}`
- **Profile Types**: antivirus, anti_spyware, vulnerability, url_filtering, file_blocking, wildfire, data_filtering

### 3. Moved Snippet Test to Position 2 ✅
- **Before**: Test 5 (after profile capture)
- **After**: Test 2 (after folder capture, before rule capture)
- **Reason**: Snippets and folders are equivalent containers - both can contain all types of profiles and objects

### 4. Updated Test Numbering ✅
- **Test 1**: Folder Capture (unchanged)
- **Test 2**: Snippet Capture (moved from Test 5)
- **Test 3**: Rule Capture (was Test 2)
- **Test 4**: Object Capture (was Test 3)
- **Test 5**: Profile Capture (was Test 4)
- **Test 6**: Pull Orchestrator (unchanged)
- **Test 7**: Config Pull (unchanged)
- **Test 8**: Module Integration (unchanged)

## Test 5 Validation Details

When security profiles = 0, the test will:
1. **Fail** with clear error message
2. **Show expected vs actual**: Expected at least 1, Actual 0
3. **Display API URL**: Shows the URL format that should be used
4. **List profile types**: Shows all available security profile types
5. **Log error**: Logs to centralized error logger with URL information
6. **Explain possible causes**: Lists possible reasons for failure

## Error Message Format

```
✗ FAILED: No security profiles captured from folder 'Mobile Users'
  Expected: At least 1 security profile (default best practice profiles should exist)
  Actual: 0 security profiles

  Security profiles should be available at:
  URL: https://api.sase.paloaltonetworks.com/sse/config/v1/security-profiles/{type}?folder=Mobile%20Users
  Profile types: antivirus, anti_spyware, vulnerability, url_filtering, file_blocking, wildfire, data_filtering

  This indicates:
  - Security profile capture may not be implemented correctly
  - API endpoint may be incorrect
  - Folder may not have security profiles configured
```

## Files Modified

1. **prisma/api_endpoints.py**: Fixed snippets endpoint to use Strata API
2. **test_phase2.py**: 
   - Added security profile validation to Test 5
   - Moved snippet test to Test 2 position
   - Updated test numbering

## Next Steps

- Security profile capture needs to be implemented in `prisma/api_client.py` and `prisma/pull/profile_capture.py`
- Currently returning empty list as placeholder
- Once implemented, Test 5 should pass if security profiles exist
