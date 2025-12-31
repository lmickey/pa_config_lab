# Skip Validation Feature

**Date:** 2024-12-30  
**Feature:** Prevent push when all items will be skipped  
**Status:** ✅ Implemented

---

## Feature Request

> "if validation is set to 'skip' and all selected items are skipped and there's no new configuration to create, then the push button should stay disabled and warning message banner should be presented on the window to say 'all identified configuration to be skipped, update selection or update conflict method to continue' or something similar."

---

## Problem

When conflict resolution is set to **SKIP** and all selected items already exist in the destination tenant:
- The push operation would do nothing (all items skipped)
- But the Push button was still enabled
- User could click Push and waste time on a no-op operation
- No clear feedback about why nothing would happen

**Example Scenario:**
1. User selects 5 address objects
2. All 5 already exist in destination
3. Conflict resolution is SKIP
4. Push preview shows "5 conflicts, 0 new items"
5. **Problem:** Push button is enabled, but clicking it would skip all 5 items = nothing pushed!

---

## Solution

Added validation logic in `_analyze_and_populate()` to detect this scenario:

```python
# Check if all items will be skipped
if conflicts and not new_items and self.conflict_resolution == 'SKIP':
    # All items are conflicts and will be skipped - nothing to push
    self.action_label.setText(
        f"⚠️ All selected items already exist and will be skipped. "
        f"Update your selection or change conflict resolution to continue."
    )
    self.action_label.setStyleSheet(
        "padding: 10px; background-color: #FFEBEE; border: 2px solid #F44336; "
        "border-radius: 5px; font-weight: bold; color: #C62828;"
    )
    # Disable the push button
    self.ok_button.setEnabled(False)
else:
    # Normal case - show summary and enable push
    self.action_label.setText(
        f"📊 Ready to push: {conflict_text}, {new_text} ({total} total items)"
    )
    # Enable push button
    self.ok_button.setEnabled(True)
```

---

## Validation Logic

**Condition:** All three must be true:
1. `conflicts` list is not empty (items exist in destination)
2. `new_items` list is empty (no new items to create)
3. `conflict_resolution == 'SKIP'` (conflicts will be skipped)

**Result:** Nothing would be pushed!

**Action:**
- Disable Push button (`ok_button.setEnabled(False)`)
- Show red warning banner
- Provide clear guidance

---

## UI Changes

### Warning State (All Skipped)

**Banner:**
- Background: Red (#FFEBEE)
- Border: 2px solid red (#F44336)
- Text: Bold, dark red (#C62828)
- Icon: ⚠️

**Message:**
```
⚠️ All selected items already exist and will be skipped.
Update your selection or change conflict resolution to continue.
```

**Push Button:** Disabled

### Normal State (Items to Push)

**Banner:**
- Background: Orange (#FFF3E0)
- Text: Bold, black
- Icon: 📊

**Message:**
```
📊 Ready to push: 5 conflicts, 3 new items (8 total items)
```

**Push Button:** Enabled

---

## User Guidance

The warning message tells users they have two options:

### Option 1: Update Selection
- Go back to component selection
- Select different items (that don't all exist)
- Or select additional new items

### Option 2: Change Conflict Resolution
- Change from SKIP to OVERWRITE or RENAME
- This allows the conflicting items to be pushed

---

## Testing

### Test Case 1: All Items Skipped

**Setup:**
1. Select 5 address objects that all exist in destination
2. Set conflict resolution to SKIP
3. Open push preview

**Expected Result:**
- ⚠️ Red warning banner appears
- Message: "All selected items already exist and will be skipped..."
- Push button is **disabled**
- Conflicts tab shows 5 conflicts
- New Items tab shows "No new items"

### Test Case 2: Some New Items

**Setup:**
1. Select 3 existing + 2 new address objects
2. Set conflict resolution to SKIP
3. Open push preview

**Expected Result:**
- 📊 Normal orange banner appears
- Message: "Ready to push: 3 conflicts, 2 new items (5 total)"
- Push button is **enabled**
- 3 conflicts will be skipped, 2 new items will be created

### Test Case 3: Change Resolution

**Setup:**
1. Start with Test Case 1 (all skipped, button disabled)
2. Close dialog
3. Change conflict resolution to OVERWRITE
4. Reopen push preview

**Expected Result:**
- 📊 Normal orange banner appears
- Message: "Ready to push: 5 conflicts, 0 new items (5 total)"
- Push button is **enabled**
- All 5 items will be overwritten

### Test Case 4: No Conflicts

**Setup:**
1. Select 5 new items (don't exist in destination)
2. Any conflict resolution
3. Open push preview

**Expected Result:**
- 📊 Normal orange banner appears
- Message: "Ready to push: no conflicts, 5 new items (5 total)"
- Push button is **enabled**
- All 5 items will be created

---

## Edge Cases

### All Items Are New
- `conflicts = []`, `new_items = [...]`
- Condition fails (conflicts is empty)
- Push button enabled ✓

### Mix of Conflicts and New Items
- `conflicts = [...]`, `new_items = [...]`
- Condition fails (new_items not empty)
- Push button enabled ✓

### Conflicts with OVERWRITE
- `conflicts = [...]`, `new_items = []`, `resolution = 'OVERWRITE'`
- Condition fails (resolution not SKIP)
- Push button enabled ✓

### Conflicts with RENAME
- `conflicts = [...]`, `new_items = []`, `resolution = 'RENAME'`
- Condition fails (resolution not SKIP)
- Push button enabled ✓

---

## Files Changed

- `gui/dialogs/push_preview_dialog.py`
  - `_analyze_and_populate()` - Added validation logic
  - Conditional styling for action_label
  - Conditional enabling/disabling of ok_button

---

## Benefits

**User Experience:**
- ✅ Prevents wasted time on no-op push operations
- ✅ Clear visual feedback (red warning)
- ✅ Actionable guidance (what to do next)
- ✅ Prevents confusion ("Why didn't anything push?")

**Workflow:**
- ✅ Forces user to make a conscious decision
- ✅ Encourages proper conflict resolution strategy
- ✅ Reduces support requests

---

## Commit

**Hash:** f8161f4  
**Message:** "Add validation to prevent push when all items will be skipped"

