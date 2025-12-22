# API Endpoint Validator

Diagnostic tool to test all Prisma Access API endpoints and identify which ones need URL corrections.

## Usage

```bash
python3 validate_endpoints.py <tsg_id> <client_id>
```

You'll be prompted for the client secret securely.

## Example

```bash
python3 validate_endpoints.py 1234567890 myapp@12345.iam.panserviceaccount.com
```

## What It Tests

The validator tests **40+ API endpoints** across:

### Security Policies
- Security rules
- Security policy folders

### Objects
- Address objects & groups
- Service objects
- Applications

### Profiles
- Authentication profiles
- Security profiles (8 types)
- Decryption profiles

### Infrastructure
- Remote networks & connections
- IPsec tunnels, IKE gateways, crypto profiles
- Service connections & groups
- GlobalProtect (portals, gateways, settings)
- HIP objects & profiles
- Bandwidth allocations & locations
- Shared infrastructure settings

## Output

The script will:
1. ✅ Show which endpoints work correctly (200 OK)
2. ❌ Identify endpoints with incorrect URLs (404 Not Found)
3. ⚠️  Flag endpoints requiring additional permissions (403 Forbidden)
4. 📄 Save a detailed JSON report: `endpoint_validation_YYYYMMDD_HHMMSS.json`

## Reading Results

### ✅ Success (200)
Endpoint works correctly - no changes needed.

### ❌ Not Found (404)
**These need URL corrections!** The endpoint path in `api_client.py` or `api_endpoints.py` is incorrect.

### ⚠️ Forbidden (403)
Endpoint exists but your service account may need additional permissions.

### ❌ Other Errors (400, etc.)
May indicate parameter issues or API changes.

## Example Output

```
[1/40] Testing: Security Rules                      ✅ 200 - Returned 15 items
[2/40] Testing: IPsec Tunnels                       ❌ 404 - Endpoint not found
[3/40] Testing: HIP Objects                         ✅ 200 - Returned 3 items
```

## After Running

Review the **"ENDPOINTS NOT FOUND (404)"** section at the end. For each failed endpoint, you'll need to:

1. Find the correct API endpoint URL from Palo Alto documentation
2. Update the URL in `prisma/api_endpoints.py`
3. Re-run the validator to confirm the fix

## Report File

The JSON report includes:
- Timestamp and TSG ID
- Summary statistics
- Detailed results for each endpoint
- Error messages for failed endpoints

Share this report to get help with URL corrections.
