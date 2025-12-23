# Mobile Users & HIP Configuration Fix

## Issues

### Issue 1: Mobile Users Data Not Parsing Correctly

**Problem:**
- Mobile Users endpoints return paginated responses: `{"data": [...], "offset": 0, "limit": 200}`
- We're storing the entire response object instead of extracting the `data` array
- Config viewer shows "data, offset, limit" fields instead of actual items

**Example:**
```json
// What API returns
{
  "agent_profiles": {
    "data": [
      {"name": "Profile-1", ...},
      {"name": "Profile-2", ...}
    ],
    "offset": 0,
    "limit": 200
  }
}

// What we should store
{
  "agent_profiles": [
    {"name": "Profile-1", ...},
    {"name": "Profile-2", ...}
  ]
}
```

### Issue 2: HIP Missing / Wrong Location

**Problem:**
- HIP (Host Information Profile) is captured at infrastructure level with `folder="Mobile Users"`
- But HIP is actually **folder-level configuration**, not infrastructure
- Should be captured per-folder (like objects and profiles)
- Should NOT be in "Remote Networks" folder

**Current:**
```
Infrastructure
  └─ HIP
      ├─ hip_objects
      └─ hip_profiles
```

**Should be:**
```
Folders
  ├─ Mobile Users
  │   ├─ Security Rules
  │   ├─ Objects
  │   ├─ Profiles
  │   └─ HIP  ← Per-folder
  │       ├─ HIP Objects
  │       └─ HIP Profiles
  └─ Shared
      └─ HIP  ← Per-folder
```

---

## Solution

### Fix 1: Extract `data` from Mobile Users Responses

**File:** `prisma/pull/infrastructure_capture.py`

Update `capture_mobile_user_infrastructure` to extract `data` arrays:

```python
# Before
result["agent_profiles"] = self.api_client.get_mobile_agent_profiles(folder=folder)

# After
response = self.api_client.get_mobile_agent_profiles(folder=folder)
# Extract 'data' if it's a paginated response, otherwise use as-is
if isinstance(response, dict) and "data" in response:
    result["agent_profiles"] = response["data"]
else:
    result["agent_profiles"] = response
```

Apply to all mobile user endpoints:
- agent_profiles
- agent_versions
- authentication_settings
- global_settings
- infrastructure_settings
- locations
- tunnel_profiles

### Fix 2: Move HIP to Folder-Level Capture

**File:** `prisma/pull/folder_capture.py` or `prisma/pull/pull_orchestrator.py`

1. **Remove HIP from infrastructure capture**
   - Remove from `capture_all_infrastructure`
   - Remove from infrastructure workers

2. **Add HIP to folder capture**
   - Capture HIP objects/profiles per folder
   - Skip for "Remote Networks" folder
   - Store under `folder["hip"]`

3. **Update config schema**
   - HIP should be under each folder, not infrastructure

---

## Implementation Steps

1. ✅ Fix mobile users data extraction
2. ✅ Move HIP capture to folder level
3. ✅ Update config viewer to display HIP under folders
4. ✅ Remove HIP from infrastructure display
5. ✅ Test with real data

---

## Testing

1. **Mobile Users:**
   - Pull config with Mobile Users enabled
   - Expand Mobile Users → agent_profiles
   - Should see list of profiles, not "data, offset, limit"

2. **HIP:**
   - Pull config with HIP enabled
   - Expand Folders → Mobile Users → HIP
   - Should see HIP Objects and HIP Profiles
   - Should NOT see HIP under Infrastructure
