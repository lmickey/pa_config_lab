# Phase 2 Test Script Updates

## Changes Made

### 1. File Output Logging ✅
- Test output is now automatically saved to a timestamped file
- Format: `Phase 2 Implementation Test-HH.MM.SS-MM.DD.YYYY.txt`
- Output is simultaneously written to console and file
- File path is displayed at the start and end of test run

### 2. Smart Folder Selection ✅
- Added `select_test_folder()` function that prioritizes folders with security policy content
- Priority order:
  1. **Access Agent** (preferred for security policy testing)
  2. **GlobalProtect**
  3. **Prisma Access**
  4. **Explicit Proxy**
  5. **Mobile User Container**
  6. Other folders (except Service Connections/Remote Networks)
  7. Service Connections (last resort - infrastructure only)

### 3. Tenant Information ✅
- Added note in credential prompt about test tenant (tsg: 1570970024)
- Tenant ID is NOT hardcoded - user must still enter it
- Guidance provided for which folder to use (Access Agent)

### 4. Updated All Test Functions ✅
All test functions now use `select_test_folder()` instead of just taking the first folder:
- `test_folder_capture()` - Shows selected test folder
- `test_rule_capture()` - Uses selected folder
- `test_object_capture()` - Uses selected folder
- `test_profile_capture()` - Uses selected folder
- `test_pull_orchestrator()` - Uses selected folder
- `test_config_pull()` - Uses selected folder

## Usage

### Running Tests

```bash
python3 test_phase2.py
```

### Expected Behavior

1. **Output File**: Automatically created with timestamp
   - Example: `Phase 2 Implementation Test-14.35.22-12.19.2025.txt`

2. **Folder Selection**: 
   - If "Access Agent" folder exists, it will be selected
   - Otherwise falls back to other preferred folders
   - Avoids Service Connections unless no other option

3. **Test Tenant**: 
   - Prompt suggests using tsg: 1570970024
   - User must enter credentials (not hardcoded)
   - Access Agent folder recommended for testing

### Example Output

```
============================================================
Phase 2 Implementation Tests
============================================================

Output will be saved to: Phase 2 Implementation Test-14.35.22-12.19.2025.txt

============================================================
Prisma Access Credentials
============================================================
Enter credentials to test against a real tenant.
Press Enter to skip and run structure tests only.

Note: For testing, use tenant tsg: 1570970024
      Use 'Access Agent' folder for security policy testing.

Test against real tenant? (y/n): y
Enter TSG ID: 1570970024
Enter API Client ID: cursor-dev@1570970024.iam.panserviceaccount.com
Enter API Client Secret: ********

Credentials provided. Testing against real tenant...

============================================================
Test 1: Folder Capture
============================================================
✓ Folder capture module structure correct

  Testing against real tenant...
  ✓ Discovered 6 folders
    - Service Connections (default: False)
    - Remote Networks (default: False)
    - Mobile User Container (default: False)
    - Access Agent (default: False)
    - GlobalProtect (default: False)
    - Explicit Proxy (default: False)

  Selected test folder: Access Agent
    (This folder will be used for subsequent tests)
```

## Benefits

1. **Better Test Coverage**: Tests now use folders with actual security policies
2. **Consistent Results**: Same folder used across all tests
3. **Debugging**: Full output saved to file for review
4. **Flexibility**: Works with any tenant, not hardcoded
5. **Guidance**: Clear instructions on which tenant/folder to use

## Notes

- Service Connections folder is avoided because it only contains VPN tunnel configuration
- Access Agent folder contains the actual security policies, rules, objects, and profiles
- Output file is created in the same directory as the test script
- All console output is also written to the file
