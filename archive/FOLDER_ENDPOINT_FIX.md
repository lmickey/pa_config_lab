# Folder Endpoint Fix

## Issue

The folders endpoint was returning 404 errors because the URL path was incorrect.

## Root Cause

The correct endpoint for listing folders is:
```
https://api.strata.paloaltonetworks.com/config/setup/v1/folders
```

But we were using:
```
https://api.strata.paloaltonetworks.com/config/v1/folders
```

The difference is `/setup/v1/` vs `/v1/`.

## Fix Applied

### 1. Updated `prisma/api_endpoints.py`

Added a new base URL constant for the setup API:
```python
STRATA_SETUP_BASE_URL = "https://api.strata.paloaltonetworks.com/config/setup/v1"
```

Updated the folders endpoint to use the correct base URL:
```python
SECURITY_POLICY_FOLDERS = f"{STRATA_SETUP_BASE_URL}/folders"
```

### 2. Updated `test_phase2.py`

Commented out all tests except `test_folder_capture` to focus on fixing the folder listing endpoint first.

## Example Request (from curl)

```bash
curl -L 'https://api.strata.paloaltonetworks.com/config/setup/v1/folders' \
-H 'Accept: application/json' \
-H 'Authorization: Bearer <token>'
```

## Expected Response

The API should return a JSON response with folder data:
```json
{
  "data": [
    {
      "id": "...",
      "name": "Mobile Users",
      "parent": "Mobile Users Container",
      "type": "cloud"
    },
    ...
  ],
  "limit": 200,
  "offset": 0,
  "total": 9
}
```

## Testing

Run the test script to verify the folder endpoint now works:
```bash
python3 test_phase2.py
```

Only the folder capture test will run, allowing us to verify the endpoint fix before proceeding with other tests.
