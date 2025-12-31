# Phase 2 Test Script Usage

## Overview

The Phase 2 test script (`test_phase2.py`) tests all security policy capture components against a real Prisma Access tenant.

## Running the Tests

### Basic Usage

```bash
python3 test_phase2.py
```

### Credential Prompts

When you run the script, it will prompt for:

1. **Test against real tenant? (y/n)**
   - Enter `y` to test against a real tenant
   - Enter `n` to run structure tests only (no API calls)

2. **TSG ID**
   - Your Prisma Access Tenant Service Group ID
   - Example: `tsg-1234567890`

3. **API Client ID**
   - Your Prisma Access API client ID
   - This is the username for API authentication

4. **API Client Secret**
   - Your Prisma Access API client secret
   - Input is hidden for security

## Expected Results

### Successful Test Output

When testing against a real tenant, you should see:

```
✓ Folder capture module structure correct
  Testing against real tenant...
  ✓ Discovered 5 folders
    - Service Connections (default: True)
    - Remote Networks (default: True)
    - Mobile User Container (default: True)
    - Access Agent (default: True)
    - GlobalProtect (default: True)
  ✓ Built folder hierarchy (5 folders)
  ✓ Listed 0 non-default folders for capture
```

### Error Handling

The script now properly reports failures:

- **✗ FAILED**: Test failed and returned False
- **⚠ WARNING**: Test completed but with warnings
- **✓**: Test passed successfully

### Common Issues

1. **403 Forbidden on security-policy/folders**
   - The script will try alternative folder discovery methods
   - Default folders (Service Connections, Remote Networks, Mobile User Container) will be discovered via object endpoints

2. **No folders discovered**
   - Check API credentials
   - Verify TSG ID is correct
   - Check API client permissions

3. **Authentication failures**
   - Verify API Client ID and Secret are correct
   - Check that the API client has proper permissions

## Test Coverage

The script tests:

1. **Folder Capture** - Discovers folders and builds hierarchy
2. **Rule Capture** - Captures security rules from folders
3. **Object Capture** - Captures address objects, groups, services
4. **Profile Capture** - Captures authentication and security profiles
5. **Snippet Capture** - Discovers snippets
6. **Pull Orchestrator** - Tests complete pull workflow
7. **Config Pull** - Tests main pull interface
8. **Integration** - Tests module integration

## Exit Codes

- **0**: All tests passed
- **1**: One or more tests failed

## Notes

- The script will continue testing even if individual tests fail
- All errors are reported in the summary
- Real tenant tests require valid API credentials
- Structure tests run even without credentials
