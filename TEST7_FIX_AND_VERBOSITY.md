# Test 7 Fix and Verbosity Reduction

## Issue

Test 7 was using `pull_folders_only()` which explicitly excludes objects and profiles (`include_objects=False`, `include_profiles=False`), resulting in 0 objects and 0 profiles. The test was expecting full configuration data.

## Fix Applied

### Test 7 Updated (`test_phase2.py`)

**Before:**
- Used `pull_folders_only()` which only captures rules
- Expected objects and profiles but got 0 for both

**After:**
- Changed to use `pull_configuration()` which captures everything (rules, objects, profiles, snippets)
- Validates counts match expected values from earlier tests:
  - Rules: 22 (from Test 3)
  - Objects: 211 (from Test 4)
  - Profiles: 32 (from Test 5)
  - Snippets: 27 (from Test 2)
- Extracts folder configuration from the full config structure
- Provides clear validation messages if counts don't match

## Verbosity Reduction

Reduced verbose output from capture modules to only show:
- Errors and warnings (always shown)
- Brief success summaries (e.g., "✓ Captured 211 objects")
- No individual item details during successful captures

### Files Modified

1. **`prisma/pull/object_capture.py`**:
   - Removed "Capturing objects from folder..." message
   - Removed detailed breakdown of object types
   - Only prints brief summary: "✓ Captured {total} objects"

2. **`prisma/pull/profile_capture.py`**:
   - Removed "Capturing profiles from folder..." message
   - Removed individual profile type capture messages ("Capturing {type} profiles...")
   - Removed detailed breakdown (Authentication: X, Security: Y, Decryption: Z)
   - Only prints brief summary: "✓ Captured {total} profiles"

3. **`prisma/pull/rule_capture.py`**:
   - Removed "Capturing rules from folder..." per folder
   - Removed "Captured {count} rules" per folder
   - Only prints brief summary: "✓ Captured {total} rules"

4. **`prisma/pull/snippet_capture.py`**:
   - Removed "Capturing snippet: {name} (ID: {id})" message
   - Removed "✓ Retrieved snippet details..." success message
   - Removed detailed snippet information display (name, ID, shared_in, folders)
   - Only prints errors if snippet retrieval fails

5. **`prisma/pull/pull_orchestrator.py`**:
   - Progress callbacks still work (showing [1/3], [2/3], etc.)
   - Individual capture modules are now quieter

## Result

- Test 7 now properly validates full configuration pull
- Output is much cleaner and easier to read
- Errors and warnings are still clearly visible
- Success summaries provide quick verification without overwhelming detail
