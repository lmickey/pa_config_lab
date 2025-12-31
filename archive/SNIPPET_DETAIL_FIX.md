# Snippet Detail Access Fix

## Issue

Snippet detail retrieval was failing because:
1. API response format was not handled correctly (response is direct JSON object, not wrapped in 'data')
2. Insufficient error logging made it hard to debug
3. Code was trying to capture rules/objects/profiles from snippets, but snippets are high-level configuration parameters, not containers

## Root Cause

The snippet detail endpoint (`/snippets/:id`) returns the snippet object directly:
```json
{
  "id": "71bcabcb-ccb2-479a-8ec0-c02276295de7",
  "name": "predefined-snippet",
  "last_update": "...",
  "created_in": "...",
  "folders": [...],
  "shared_in": "local"
}
```

But the code was doing `response.get('data', {})` which returned `{}` because there's no `data` wrapper.

## Fixes Applied

### 1. Fixed API Response Handling (`prisma/api_client.py`)

**Before:**
```python
response = self._make_request('GET', url)
return response.get('data', {})  # Returns {} because no 'data' key
```

**After:**
```python
response = self._make_request('GET', url)
# Snippet detail endpoint returns the snippet object directly
if isinstance(response, dict):
    if 'data' in response:
        return response['data']
    else:
        return response  # Response IS the snippet object
```

### 2. Enhanced Error Logging (`prisma/pull/snippet_capture.py`)

Added detailed logging in `get_snippet_details()`:
- Shows API URL being called
- Checks response type and structure
- Shows response keys if unexpected format
- Logs full error details with traceback
- Logs to centralized error logger with API URL

### 3. Updated Snippet Normalization

Updated `_normalize_snippet()` to handle actual response format:
- Handles `folders` list (array of folder objects with id/name)
- Handles `shared_in` field
- Handles `last_update` and `created_in` timestamps
- Maps these to normalized format

### 4. Updated Snippet Configuration Capture

Removed attempts to capture rules/objects/profiles from snippets:
- **Snippets are high-level configuration parameters** (like folders)
- They don't contain rules, objects, or profiles
- They contain metadata: id, name, folders, shared_in, timestamps
- Rules, objects, and profiles are associated with folders, not snippets directly

## Expected Snippet Response Format

Based on `snippet-detail.txt`:
```json
{
  "id": "71bcabcb-ccb2-479a-8ec0-c02276295de7",
  "name": "predefined-snippet",
  "last_update": "Tue Jul 22 2025 16:15:51 GMT+0000 (Coordinated Universal Time)",
  "created_in": "Tue Jul 22 2025 16:15:51 GMT+0000 (Coordinated Universal Time)",
  "folders": [
    {
      "id": "06f604bd-9809-42e7-9f25-29ceeaf46b64",
      "name": "All"
    }
  ],
  "shared_in": "local"
}
```

## Files Modified

1. **prisma/api_client.py**: Fixed response handling for snippet detail endpoint
2. **prisma/pull/snippet_capture.py**: 
   - Enhanced error logging
   - Updated normalization for actual response format
   - Removed attempts to capture nested data (snippets don't contain rules/objects/profiles)

## Next Steps

When you run the test again, snippet details should be retrieved correctly, and you'll see detailed logging if there are any issues.
