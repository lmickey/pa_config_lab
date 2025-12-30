# Same Tenant Warning Feature

**Date:** 2024-12-30  
**Feature:** Warning when pushing to the same tenant  
**Status:** ✅ Implemented

---

## Feature Request

> "if the destination tenant and source tenant are the same, can we use this same yellow banner on the 'Push to Target' tab for the ready to push message? And instead of green and 'Ready to push <x> items to <tenant name>' have something like 'Warning: Pushing <x> items to the Same Tenant' and also make the 'Push Config' button also be yellow"

---

## Problem

When a user selects the same tenant as both source and destination:
- The UI showed a green "Ready to push" message
- No visual indication that they're pushing to the same tenant
- Could cause confusion or unintended overwrites
- User might not realize they're modifying the source tenant

**Example Scenario:**
1. User pulls config from "Production Tenant"
2. Selects "Use Source Tenant" as destination
3. Makes some selections
4. Sees green "Ready to push" message
5. **Problem:** No warning that they're about to modify Production!

---

## Solution

Added tenant comparison logic that detects when source and destination are the same, then shows a yellow warning banner with matching button styling.

### Detection Logic

```python
# Check if source and destination are the same tenant
is_same_tenant = (self.api_client and self.destination_client and 
                self.api_client.tsg_id == self.destination_client.tsg_id)
```

**Comparison:** Uses `tsg_id` (Tenant Service Group ID) which uniquely identifies each tenant.

---

## UI Changes

### ⚠️ Warning State (Same Tenant)

**Banner:**
- Background: Light yellow (#FFF9C4)
- Border: 2px solid gold (#FBC02D)
- Text: Dark amber (#F57F17), bold
- Icon: ⚠️

**Message:**
```
⚠️ Warning: Pushing 15 items to the Same Tenant (5 snippets, 10 objects)
```

**Push Config Button:**
- Background: Gold (#FBC02D)
- Border: 2px solid darker gold (#F9A825)
- Text: Black, bold
- Hover: Darker yellow (#F9A825)
- Pressed: Amber (#F57F17)

**Progress Label:**
```
Warning: Same tenant
```
- Color: Dark amber (#F57F17), bold

---

### ✓ Normal State (Different Tenant)

**Banner:**
- Background: Light green (#e8f5e9)
- Border: 1px solid green (#4CAF50)
- Text: Dark green (#2e7d32)
- Icon: ✓

**Message:**
```
✓ Ready to push 15 items to Staging Tenant (5 snippets, 10 objects)
```

**Push Config Button:**
- Default blue styling (no custom style)
- Standard Qt button appearance

**Progress Label:**
```
Ready to push
```
- Color: Green

---

## Color Consistency

This feature uses the **same yellow color scheme** as the skip validation warning:

| Element | Color | Hex |
|---------|-------|-----|
| Background | Light yellow | #FFF9C4 |
| Border | Gold | #FBC02D |
| Text | Dark amber | #F57F17 |
| Button | Gold | #FBC02D |
| Button hover | Darker gold | #F9A825 |
| Button pressed | Amber | #F57F17 |

---

## When Warning Appears

**Same Tenant Scenarios:**
1. User selects "Use Source Tenant" as destination
2. User selects a different tenant connection that happens to be the same TSG ID
3. User switches between connections that resolve to the same tenant

**Different Tenant (No Warning):**
1. User selects a different tenant from saved configs
2. User selects a different tenant from connections
3. User manually enters different tenant credentials

---

## Benefits

**User Safety:**
- ✅ Clear visual warning before modifying source tenant
- ✅ Prevents accidental overwrites
- ✅ Makes user think twice before proceeding

**User Experience:**
- ✅ Consistent yellow warning theme
- ✅ Obvious visual difference from normal state
- ✅ Yellow button reinforces the warning

**Workflow:**
- ✅ Doesn't prevent the operation (button still enabled)
- ✅ Just provides clear warning
- ✅ User can proceed if intentional

---

## Testing

### Test Case 1: Same Tenant Warning

**Setup:**
1. Connect to "Production Tenant"
2. Pull configuration
3. Select items to push
4. Select "Use Source Tenant" as destination
5. Go to "Push to Target" tab

**Expected Result:**
- ⚠️ Yellow warning banner
- Message: "Warning: Pushing X items to the Same Tenant"
- Yellow "Push Config" button
- Progress label: "Warning: Same tenant" (amber)

### Test Case 2: Different Tenant (Normal)

**Setup:**
1. Connect to "Production Tenant"
2. Pull configuration
3. Select items to push
4. Select "Staging Tenant" as destination
5. Go to "Push to Target" tab

**Expected Result:**
- ✓ Green ready banner
- Message: "Ready to push X items to Staging Tenant"
- Blue "Push Config" button (default)
- Progress label: "Ready to push" (green)

### Test Case 3: Switch Between Same/Different

**Setup:**
1. Start with same tenant (yellow warning)
2. Change to different tenant
3. Change back to same tenant

**Expected Result:**
- UI updates dynamically
- Yellow → Green → Yellow
- Button style updates accordingly

---

## Code Location

**File:** `gui/push_widget.py`

**Method:** `_update_status()` (around line 445)

**Key Changes:**
1. Added `is_same_tenant` check comparing TSG IDs
2. Conditional styling based on check result
3. Custom button styling for same-tenant case
4. Progress label updates

---

## Edge Cases

### No API Client
- If `self.api_client` is None, comparison fails safely
- Defaults to normal state (green)

### No Destination Client
- If `self.destination_client` is None, comparison fails safely
- Defaults to normal state (green)

### TSG ID Not Available
- If either client doesn't have `tsg_id` attribute
- Comparison fails safely
- Defaults to normal state (green)

---

## Future Enhancements

Potential additions:
1. Add confirmation dialog when pushing to same tenant
2. Show diff preview before pushing to same tenant
3. Add option to disable same-tenant pushes entirely
4. Log same-tenant pushes for audit purposes

---

## Related Features

- **Skip Validation** (`docs/SKIP_VALIDATION.md`)
  - Uses same yellow color scheme
  - Similar warning banner style
  - Consistent user experience

- **Push Preview Dialog** (`gui/dialogs/push_preview_dialog.py`)
  - Shows conflicts before push
  - Works with same-tenant pushes
  - Provides additional safety layer

---

## Commit

**Hash:** 6f59bf0  
**Message:** "Add same-tenant warning on Push to Target tab"

