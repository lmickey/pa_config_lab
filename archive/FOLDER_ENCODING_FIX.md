# Folder Parameter Encoding Fix

## Issue

The Prisma Access API expects folder names to be URL encoded with `%20` for spaces, but the `requests` library's `params` parameter uses `+` encoding by default. This was causing 400 Bad Request errors.

## Solution

Updated all API client methods to manually build query strings using `build_folder_query()` function instead of relying on `requests` library's automatic encoding.

### Before
```python
params = {'folder': folder}  # requests encodes as "Access+Agent"
response = requests.get(url, params=params)
```

### After
```python
url += build_folder_query(folder)  # Manually builds "?folder=Access%20Agent"
response = requests.get(url, params=other_params)
```

## Updated Methods

All methods that accept folder parameters now use manual query string building:

- `get_security_rules()` - Security rules
- `get_addresses()` - Address objects
- `get_address_groups()` - Address groups
- `get_services()` - Service objects
- `get_service_groups()` - Service groups
- `get_applications()` - Application objects
- `get_authentication_profiles()` - Authentication profiles
- `get_service_connections()` - Service connections
- `get_remote_networks()` - Remote networks

## Folder Query Encoding

The `build_folder_query()` function in `api_endpoints.py`:
- Uses `urllib.parse.quote()` to encode folder names
- Produces `%20` encoding for spaces (not `+`)
- Example: `"Access Agent"` → `"?folder=Access%20Agent"`

## Test Script Fixes

Also fixed `select_test_folder()` function to handle both:
- List of folder dictionaries (from `discover_folders()`)
- List of folder name strings (from `list_folders_for_capture()`)

## Expected Results

After these fixes:
- ✅ Folder parameters use `%20` encoding
- ✅ API calls should return 200 instead of 400
- ✅ Test script handles both folder formats correctly
- ✅ 404 on folders endpoint is handled gracefully (uses alternative discovery)

## Notes

- The 404 on `/folders` endpoint is expected and handled gracefully
- Alternative folder discovery methods are used when Strata API returns 404
- All folder-based API calls now use consistent `%20` encoding
