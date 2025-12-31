# Component Selection Dialog - Sync with Config Viewer

## Issues to Fix

1. **Infrastructure incomplete:**
   - ✅ Shows: IPSec tunnels/gateways/crypto profiles/service connections
   - ❌ Missing: Mobile Users, Remote Networks, Regions

2. **HIP missing under folders:**
   - Should show HIP Objects and HIP Profiles per folder

3. **Snippets using `name` instead of `display_name`:**
   - Should use `display_name` if available, fall back to `name`
   - Should apply same filtering as config viewer

## Long-term Solution

Create a shared tree-building component that both config viewer and selection dialog use.

**Benefits:**
- Single source of truth
- Automatic sync
- Easier maintenance

**Implementation:**
- Extract tree-building logic to a shared class
- Add optional checkbox support
- Both dialogs use the same logic

## Short-term Fix

Copy the correct logic from config viewer to selection dialog:
1. Add Mobile Users, Remote Networks, Regions to infrastructure
2. Add HIP to folders
3. Fix snippet display_name usage
4. Apply snippet filtering

This will be done now, with refactoring to follow later.
