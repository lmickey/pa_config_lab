# Test Folder Update

## Change Summary

Updated the test script to use **"Mobile Users"** as the preferred default test folder instead of "Access Agent".

## Why This Change?

Based on successful test results, "Mobile Users" folder:
- Contains actual security policy configurations
- Is a standard Prisma Access folder that exists in deployments
- Provides better test coverage for security policy operations

## Changes Made

### 1. Updated `select_test_folder()` Function

Changed the priority order to put "Mobile Users" first:

**Before:**
```python
preferred_folders = [
    'Access Agent',
    'GlobalProtect',
    'Prisma Access',
    ...
]
```

**After:**
```python
preferred_folders = [
    'Mobile Users',  # Preferred folder for testing (has actual security policies)
    'Access Agent',
    'GlobalProtect',
    'Prisma Access',
    ...
]
```

### 2. Updated Test Instructions

Changed the note in the test script:
- **Before:** "Use 'Access Agent' folder for security policy testing."
- **After:** "Use 'Mobile Users' folder for security policy testing."

### 3. Updated Comments

Updated all comments in test functions to reflect the new preference:
- Changed references from "prefer Access Agent/GlobalProtect" to "prefer Mobile Users"

## Verification

The `select_test_folder()` function now correctly prioritizes "Mobile Users":
```python
folders = ['Service Connections', 'Remote Networks', 'Mobile Users', 'Access Agent']
result = select_test_folder(folders)
# Returns: 'Mobile Users'
```

## Impact

- All future tests will use "Mobile Users" folder by default
- Better test coverage with actual security policy configurations
- More consistent test results across different Prisma Access deployments
