# Centralized Error Logging System

## Overview

A centralized error logging system has been implemented to automatically log all API errors and capture operation errors to a file (`api_errors.log`) with clear delimiters between test runs.

## Features

### 1. Automatic Error Logging

- **API Errors**: Automatically logged when API requests fail (via `handle_api_response()`)
- **Capture Errors**: Logged when capture operations fail (via error logger calls)
- **Test Errors**: Logged when test operations fail

### 2. Error Log File

- **Location**: `api_errors.log` (in project root)
- **Format**: Clear delimiters between test runs
- **Overwrite**: Log file is cleared at the start of each test run
- **Content**: Full request/response details, headers, parameters, tracebacks

### 3. Security Features

- **Token Masking**: Authorization tokens are partially masked (first 20 + last 10 chars)
- **Password Masking**: Passwords and secrets in request bodies are redacted

## Usage

### Automatic Logging

Error logging happens automatically - no code changes needed in most cases:

1. **API Errors**: Automatically logged by `handle_api_response()` in `prisma/api_utils.py`
2. **Capture Errors**: Logged via `error_logger.log_capture_error()` calls
3. **Test Errors**: Logged in test functions when exceptions occur

### Manual Logging

If you need to manually log an error:

```python
from prisma.error_logger import error_logger

error_logger.log_capture_error(
    operation="capture_addresses",
    context="Mobile Users",
    error=exception_object,
    additional_info={"folder": "Mobile Users", "count": 0}
)
```

### Reading the Log

The test script automatically reads and displays the error log at the end of each run if errors occurred. You can also read it manually:

```python
from prisma.error_logger import error_logger

log_content = error_logger.read_log()
print(log_content)
```

## Error Log Format

```
====================================================================================================
API ERROR LOG - Test Run Started
Test: Phase 2 Implementation Tests
Timestamp: 2025-12-19 17:31:59
====================================================================================================

----------------------------------------------------------------------------------------------------
API ERROR - 2025-12-19 17:32:01
----------------------------------------------------------------------------------------------------

Method: GET
URL: https://api.sase.paloaltonetworks.com/sse/config/v1/addresses?folder=Mobile%20Users
Status Code: 400
Status Text: Bad Request

Headers:
  Content-Type: application/json
  Authorization: Bearer eyJhbGciOiJSUzI1NiIs...xyz1234567

Query Parameters:
  limit: 100
  offset: 0

Response Body:
{
  "_errors": [
    {
      "code": "API_I00013",
      "message": "..."
    }
  ]
}

Exception Details:
  Type: HTTPError
  Message: 400 Client Error: Bad Request

Traceback:
...

----------------------------------------------------------------------------------------------------

====================================================================================================
Test Run Ended
Timestamp: 2025-12-19 17:32:05
Duration: 6.23 seconds
Summary: Tests: 2/3 passed
====================================================================================================
```

## Integration Points

### 1. API Client (`prisma/api_utils.py`)

- `handle_api_response()` automatically logs API errors
- Logs full request details, response, and traceback

### 2. Capture Modules

- `object_capture.py`: Logs errors for address, service, application capture
- Other capture modules can be updated similarly

### 3. Test Script (`test_phase2.py`)

- Initializes error logger at start of test run
- Ends error logging session at end of test run
- Automatically displays error log summary if errors occurred

## Benefits

1. **Centralized Logging**: All errors in one place
2. **Detailed Information**: Full request/response details for debugging
3. **Clear Delimiters**: Easy to find errors from specific test runs
4. **Automatic**: No need to manually paste filenames
5. **Security**: Sensitive data is masked
6. **Persistent**: Errors are saved even if test script crashes

## Files Modified

1. **Created**: `prisma/error_logger.py` - Centralized error logging module
2. **Updated**: `prisma/api_utils.py` - Integrated error logging into API response handler
3. **Updated**: `test_phase2.py` - Integrated error logger into test script
4. **Updated**: `prisma/pull/object_capture.py` - Added error logging to capture methods

## Next Steps

- Update other capture modules (`rule_capture.py`, `profile_capture.py`, etc.) to use error logger
- Consider adding log rotation if log files get too large
- Add option to append vs overwrite log file
