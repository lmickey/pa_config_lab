# Enhanced Error Logging

## Overview

Enhanced API error logging to provide comprehensive debugging information when API requests fail.

## Changes Made

### 1. Enhanced `handle_api_response()` Function

Updated `prisma/api_utils.py` to print detailed debugging information when API errors occur:

- **Request Details:**
  - HTTP Method (GET, POST, etc.)
  - Full URL (base URL + query parameters)
  - Headers (with token masking for security)
  - Query Parameters (separate from URL)
  - Request Body (form-data or JSON)

- **Response Details:**
  - Status Code
  - Status Text
  - Final Request URL (after redirects and parameter merging by requests library)
  - Response Body (JSON or text, truncated to 1000 chars if too long)

### 2. Updated `_make_request()` Method

Modified `prisma/api_client.py` to capture request details and pass them to `handle_api_response()`:

- Captures method, URL, headers, params, and body before making request
- Passes request details to error handler for comprehensive logging

### 3. Security Features

- **Token Masking:** Authorization tokens are partially masked in logs
  - Shows first 20 characters and last 10 characters
  - Example: `Bearer eyJhbGciOiJSUzI1NiIs...xyz1234567`
  
- **Password Masking:** Passwords and secrets in request bodies are redacted
  - Shows `***REDACTED***` instead of actual values

## Example Error Output

When an API error occurs, you'll now see output like:

```
================================================================================
API ERROR - Request Details:
================================================================================
Method: GET
URL: https://api.sase.paloaltonetworks.com/sse/config/v1/security-rules?folder=Access%20Agent

Headers:
  Content-Type: application/json
  Authorization: Bearer eyJhbGciOiJSUzI1NiIs...xyz1234567

Query Parameters:
  limit: 100
  offset: 0

--------------------------------------------------------------------------------
Response Details:
--------------------------------------------------------------------------------
Status Code: 400
Status Text: Bad Request
Final Request URL (after redirects/merging): https://api.sase.paloaltonetworks.com/sse/config/v1/security-rules?folder=Access%20Agent&limit=100&offset=0

Response Body (JSON):
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Invalid folder parameter",
    "details": "..."
  }
}
================================================================================
```

## Benefits

1. **Easier Debugging:** See exactly what was sent to the API
2. **URL Verification:** Compare base URL vs final URL to catch encoding issues
3. **Header Inspection:** Verify authentication and content-type headers
4. **Parameter Validation:** See all query parameters and request body data
5. **Response Analysis:** Full error messages from API help identify root cause

## Usage

Error logging is automatic - no code changes needed in capture modules. When an API call fails, detailed debugging information is automatically printed before the exception is raised.

## Notes

- Error details are printed to stdout/stderr
- Token masking ensures sensitive credentials aren't fully exposed
- Response bodies are truncated to 1000 characters to prevent log flooding
- All error information is available before exceptions are caught by capture modules
