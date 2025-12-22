# Snippet Verification Script

## Overview

The `verify_snippets.py` script retrieves all configuration snippets from your Prisma Access tenant and saves the raw API response data to a JSON file for review.

## Purpose

This script helps you:
- Verify what snippets are actually available in your tenant
- Compare the API response with what's shown in the SCM management screen
- Debug any discrepancies in snippet discovery
- Review raw API data including folder associations

## Usage

### Option 1: Use Saved Credentials (Recommended)

```bash
python3 verify_snippets.py --use-saved
```

This will use the credentials stored in `config.json` (from the GUI or `setup_credentials.py`).

### Option 2: Provide Credentials Manually

```bash
python3 verify_snippets.py <tsg_id> <client_id>
```

You'll be prompted to enter the client secret securely.

## Output

The script generates a timestamped JSON file: `snippet_verification_YYYYMMDD_HHMMSS.json`

### Output File Structure

```json
{
  "timestamp": "2024-12-22T...",
  "tsg_id": "1234567890",
  "snippet_count": 5,
  "snippets": [
    {
      "index": 1,
      "raw_data": { ... },  // Complete raw API response
      "parsed": {
        "name": "snippet-name",
        "id": "12345678-1234-1234-1234-123456789abc",
        "description": "...",
        "folders": [...],
        "folder_names": ["Mobile Users", "Remote Networks"],
        "shared_in": "...",
        "created_in": "...",
        "last_update": "..."
      }
    }
  ],
  "errors": [],
  "raw_api_response": [...]  // Complete unprocessed API response
}
```

## What to Look For

### 1. Snippet Count
Compare the `snippet_count` in the output with what you see in the SCM management screen.

### 2. Folder Associations
Check the `folder_names` field for each snippet to see which folders it's associated with.

### 3. Default vs Custom
The script shows all snippets. To determine if a snippet is default or custom, you can:
- Check the name (defaults often have "default" or "predefined" in the name)
- Review the `created_in` and `last_update` timestamps
- Compare against known default snippet names

### 4. Raw API Response
The `raw_api_response` field contains the complete, unprocessed response from the API. This is useful for:
- Seeing exactly what the API returns
- Identifying any fields we might not be parsing
- Debugging API response format issues

## Example Output (Console)

```
======================================================================
Prisma Access Snippet Verifier
======================================================================

🔐 Authenticating...
   TSG ID: 1234567890
   Client ID: sa-12345@...iam.panserviceaccount.com
   Client Secret: **************************************** (40 chars)
✅ Authentication successful!

📋 Retrieving snippets from tenant...

   Calling get_security_policy_snippets()...
   ✅ Retrieved 5 snippet(s)

   1. best-practice-snippet
      ID: 12345678-1234-1234-1234-123456789abc
      Folders: Mobile Users, Remote Networks

   2. custom-security-snippet
      ID: 87654321-4321-4321-4321-cba987654321
      Folders: (none)

💾 Results saved to: snippet_verification_20241222_153045.json
   File size: 12,345 bytes

======================================================================
SUMMARY
======================================================================
Total snippets found: 5
Errors encountered: 0

✅ Verification complete!
📄 Review the full output in: snippet_verification_20241222_153045.json

The file contains:
   - Raw API response data
   - Parsed snippet information
   - Folder associations
   - Any errors encountered
======================================================================
```

## Troubleshooting

### No Snippets Found

If `snippet_count` is 0:
1. Verify you have snippets configured in your tenant
2. Check that the service account has permissions to read snippets
3. Review the `errors` array in the output file

### Discrepancy with SCM Screen

If you see more snippets in the API than in the SCM screen:
1. Check if some snippets are "hidden" or system-managed
2. Review the `shared_in` field - some snippets might be shared from parent folders
3. Look for default/predefined snippets that might not show in the UI

### Authentication Errors

If authentication fails:
1. Verify credentials in `config.json` are correct
2. Check that the service account hasn't been revoked
3. Ensure the TSG ID is correct
4. Try running `setup_credentials.py` to re-enter credentials

## Related Files

- `validate_endpoints.py` - Similar script for validating API endpoints
- `config.json` - Stores credentials (encrypted)
- `setup_credentials.py` - Sets up credentials for the first time

## Notes

- The script only reads data; it doesn't modify anything in your tenant
- All sensitive data (client secret) is masked in console output
- The output JSON file may contain sensitive information - handle appropriately
- Default detection is based on patterns in `config/defaults/default_configs.py`
