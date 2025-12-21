# Authentication Method Update

## Issue

The SCM (Strata Cloud Manager) Authentication Service requires a specific authentication format:
- Form data must be in the request body (not query parameters)
- Content-Type header must be `application/x-www-form-urlencoded`
- Basic auth uses Client ID as username and Client Secret as password

## Changes Made

### 1. Updated API Client Authentication ✅

**File**: `prisma/api_client.py`

**Before**:
```python
params = {'grant_type': 'client_credentials', 'scope': scope}
response = requests.post(AUTH_URL, auth=(user, secret), params=params)
```

**After**:
```python
data = {'grant_type': 'client_credentials', 'scope': scope}
headers = {'Content-Type': 'application/x-www-form-urlencoded'}
response = requests.post(AUTH_URL, auth=(user, secret), data=data, headers=headers)
```

### 2. Updated Legacy Authentication Functions ✅

**Files**: `load_settings.py`, `get_settings.py`

Updated `prisma_access_auth()` function in both files to use:
- Form data in request body (`data` parameter)
- Proper Content-Type header
- Basic auth with Client ID/Secret

## Authentication Flow

1. **Endpoint**: `https://auth.apps.paloaltonetworks.com/oauth2/access_token`
2. **Method**: POST
3. **Authentication**: Basic Auth
   - Username: Client ID
   - Password: Client Secret
4. **Headers**: 
   - `Content-Type: application/x-www-form-urlencoded`
5. **Body** (form data):
   - `grant_type=client_credentials`
   - `scope=tsg_id:<tsg_id>`
6. **Response**: JSON with `access_token` and `expires_in` (15 minutes)

## Example cURL Command

```bash
curl -d "grant_type=client_credentials&scope=tsg_id:<tsg_id>" \
  -u <client_id>:<client_secret> \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -X POST https://auth.apps.paloaltonetworks.com/oauth2/access_token
```

## Python Implementation

```python
import requests

auth_url = "https://auth.apps.paloaltonetworks.com/oauth2/access_token"
data = {
    'grant_type': 'client_credentials',
    'scope': f'tsg_id:{tsg_id}'
}
headers = {
    'Content-Type': 'application/x-www-form-urlencoded'
}

response = requests.post(
    auth_url,
    auth=(client_id, client_secret),  # Basic auth
    data=data,  # Form data in body
    headers=headers
)

if response.status_code == 200:
    access_token = response.json()['access_token']
```

## Key Differences

| Aspect | Before | After |
|--------|--------|-------|
| Data Location | Query parameters (`params`) | Request body (`data`) |
| Content-Type | Not specified | `application/x-www-form-urlencoded` |
| Auth Method | Basic auth (correct) | Basic auth (correct) |
| Scope Format | `tsg_id:<tsg_id>` (correct) | `tsg_id:<tsg_id>` (correct) |

## Impact

- ✅ Authentication now matches SCM API requirements
- ✅ Form data sent in request body instead of query string
- ✅ Proper Content-Type header set
- ✅ All authentication functions updated consistently
- ✅ Token expiration handling remains the same (15 minutes)

## Testing

The authentication method now correctly:
1. Uses basic auth with Client ID/Secret
2. Sends form data in request body
3. Sets proper Content-Type header
4. Handles 15-minute token expiration
5. Works with both Strata and SASE APIs (same token)
