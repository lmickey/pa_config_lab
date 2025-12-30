# Dependency Validation Fix

## Issue
When selecting a single object or infrastructure item in the component selection dialog, the dependency validation would show a dialog saying "Dependencies Required" but the list would be blank/empty.

## Root Cause
The `find_required_dependencies()` method returns a dictionary with the following structure:
```python
{
    'folders': [],
    'snippets': [],
    'objects': {},
    'profiles': [],
    'infrastructure': {}
}
```

Even when no dependencies are found, this dictionary is returned with empty collections. The code was checking `if required_deps:` which evaluates to `True` for a non-empty dictionary, even if all the values are empty collections.

## Solution
Added a proper check to determine if there are actually any dependencies before showing the confirmation dialog:

```python
# Check if there are actually any dependencies (not just empty collections)
has_deps = False
if required_deps:
    has_deps = (
        len(required_deps.get('folders', [])) > 0 or
        len(required_deps.get('snippets', [])) > 0 or
        sum(len(v) for v in required_deps.get('objects', {}).values() if isinstance(v, list)) > 0 or
        len(required_deps.get('profiles', [])) > 0 or
        sum(len(v) if isinstance(v, list) else 1 for v in required_deps.get('infrastructure', {}).values()) > 0
    )

if has_deps:
    # Show dependency confirmation dialog
    ...
else:
    print("\nDEBUG: No dependencies found - proceeding with original selection")
```

## Testing
The fix properly handles:
1. ✅ Empty dependencies (no dialog shown)
2. ✅ Folder dependencies (dialog shown)
3. ✅ Infrastructure dependencies (dialog shown)
4. ✅ Object dependencies (dialog shown)
5. ✅ Empty object/infrastructure lists (no dialog shown)

## Files Modified
- `gui/dialogs/component_selection_dialog.py` - Added proper empty dependency check

## Impact
Users will no longer see a blank dependency dialog when selecting standalone items that have no dependencies.
