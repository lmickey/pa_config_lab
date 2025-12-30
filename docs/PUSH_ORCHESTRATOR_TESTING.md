# Push Orchestrator Testing Guide

**Date:** 2024-12-30  
**Status:** ✅ Ready for Testing

---

## Overview

The SelectivePushOrchestrator is now integrated and ready to test! While the API calls are placeholders, you can test the complete flow and see how everything works.

---

## What You'll See

### ✅ Working Features:
1. **Progress tracking** - Real-time updates as items are processed
2. **Result tracking** - Detailed per-item results
3. **Conflict resolution** - Logic for SKIP/OVERWRITE/RENAME
4. **Summary statistics** - Total, created, updated, skipped, failed counts
5. **Full UI flow** - From selection to results

### ⚪ Placeholder Features:
1. **API calls** - All show "Created (placeholder - API not implemented)"
2. **Actual push** - No real changes made to destination tenant

---

## Test Steps

### 1. Load Configuration
1. Open the app
2. Go to **"Push Configuration"** tab
3. Click **"Load from File"** dropdown
4. Select a saved configuration file
5. Enter password if encrypted
6. ✅ Config info should display

### 2. Select Components
1. Click **"Select Components..."** button
2. Component selection dialog opens
3. Select some items:
   - Check a folder (e.g., "Mobile Users")
   - Expand and select specific objects (e.g., 2 address objects)
   - Select a security rule
   - Select infrastructure items
4. Click **OK**
5. ✅ Selection summary should update

### 3. Choose Destination
1. Go to **"Select Destination"** section
2. Choose a destination tenant
3. ✅ Status should show ready to push

### 4. Set Conflict Resolution
1. Choose conflict resolution strategy:
   - **SKIP** - Don't push if exists
   - **OVERWRITE** - Update if exists
   - **RENAME** - Create with new name if exists

### 5. Start Push
1. Go to **"Push to Target"** tab
2. ✅ Should see ready message with item counts
3. Click **"Push Config"** button

### 6. Preview Dialog
1. Push preview dialog opens
2. ✅ Shows conflicts (items that exist)
3. ✅ Shows new items (items that don't exist)
4. ✅ Shows appropriate warnings
5. Click **OK** to proceed

### 7. Confirmation Dialog
1. Warning dialog appears
2. ⚠️ "Push configuration to [tenant]?"
3. Shows conflict resolution strategy
4. Click **Yes** to confirm

### 8. Watch Progress
1. ✅ Progress bar appears
2. ✅ Messages update in real-time:
   - "Processing folder: Mobile Users"
   - "Pushing address_objects: VPN-Users"
   - "Pushing security rule: Allow-VPN"
   - etc.
3. ✅ Progress bar fills as items are processed

### 9. View Results
1. ✅ Success dialog appears
2. Shows summary:
   ```
   Push completed!
   
   Total: 15
   Created: 15
   Updated: 0
   Skipped: 0
   Failed: 0
   ```
3. ✅ Results text area shows details

---

## Expected Messages

### Progress Messages:
```
Starting push operation
Processing folder: Mobile Users
Pushing address_objects: VPN-Users
Pushing address_objects: zoom-8
Pushing security_rule: Allow-VPN-Access
Pushing ipsec_tunnels: Azure_DC_FW01
Push operation complete
```

### Result Messages:
```
Push completed!

Total: 15
Created: 15
Updated: 0
Skipped: 0
Failed: 0
```

### Details (in results text area):
```
✓ address_objects: VPN-Users - Created (placeholder - API not implemented)
✓ address_objects: zoom-8 - Created (placeholder - API not implemented)
✓ security_rule: Allow-VPN-Access - Created (placeholder - API not implemented)
...
```

---

## Test Scenarios

### Scenario 1: All New Items
**Setup:**
- Select items that don't exist in destination
- Conflict resolution: Any

**Expected:**
- All items show as "new items" in preview
- All items created
- Summary: Created = Total

### Scenario 2: All Conflicts (SKIP)
**Setup:**
- Select items that all exist in destination
- Conflict resolution: SKIP

**Expected:**
- All items show as "conflicts" in preview
- Yellow warning: "All items will be skipped"
- Push button disabled
- Cannot proceed

### Scenario 3: All Conflicts (OVERWRITE)
**Setup:**
- Select items that all exist in destination
- Conflict resolution: OVERWRITE

**Expected:**
- All items show as "conflicts" in preview
- Can proceed
- All items updated
- Summary: Updated = Total

### Scenario 4: Mix of New and Conflicts
**Setup:**
- Select mix of existing and new items
- Conflict resolution: SKIP

**Expected:**
- Preview shows both conflicts and new items
- Conflicts skipped
- New items created
- Summary: Created + Skipped = Total

### Scenario 5: Same Tenant Warning
**Setup:**
- Load config from Tenant A
- Select Tenant A as destination

**Expected:**
- Yellow warning banner
- "Warning: Pushing X items to the Same Tenant"
- Yellow push button
- Can still proceed (just warned)

---

## What to Check

### ✅ UI Updates:
- [ ] Progress bar moves smoothly
- [ ] Messages update in real-time
- [ ] UI is disabled during push
- [ ] UI re-enables after push
- [ ] Results display correctly

### ✅ Progress Tracking:
- [ ] Each item shows progress message
- [ ] Current/total counts are accurate
- [ ] Progress bar percentage is correct
- [ ] Final message shows "complete"

### ✅ Result Tracking:
- [ ] Summary counts are accurate
- [ ] Details list all items
- [ ] Each item shows correct action (created/skipped/etc.)
- [ ] Placeholder message is clear

### ✅ Error Handling:
- [ ] No crashes during push
- [ ] Errors are caught gracefully
- [ ] Error messages are clear
- [ ] UI recovers from errors

---

## Known Limitations (Placeholders)

1. **No actual API calls** - All items show as "placeholder"
2. **No real updates** - Destination tenant not modified
3. **No folder creation** - Folders not actually created
4. **No conflict detection from API** - Uses preview dialog's detection
5. **No rename logic** - Renamed items not actually created with new name

---

## Debug Output

Check the console for detailed debug output:
```
[0/15] Starting push operation
[1/15] Processing folder: Mobile Users
[2/15] Pushing address_objects: VPN-Users
[3/15] Pushing address_objects: zoom-8
...
[15/15] Push operation complete
```

---

## Next Steps After Testing

Once you've verified the flow works:

1. **Implement API methods** in `api_client.py`:
   - `create_address(data, folder)`
   - `update_address(id, data)`
   - `create_security_rule(data, folder)`
   - etc.

2. **Replace placeholders** in `selective_push_orchestrator.py`:
   - Remove "placeholder" messages
   - Add real API calls
   - Add error handling for API failures

3. **Test with real API**:
   - Use test tenant
   - Verify items are actually created
   - Verify conflict resolution works
   - Verify errors are handled

---

## Troubleshooting

### Progress bar doesn't move
- Check console for errors
- Verify worker thread started
- Check if signals are connected

### No results displayed
- Check if worker finished signal fired
- Check console for exceptions
- Verify results text area is visible

### UI doesn't re-enable
- Check if finished signal fired
- Check _set_ui_enabled method
- Look for uncaught exceptions

### Crashes or freezes
- Check for print statements in threads
- Verify no blocking operations in main thread
- Check for Qt signal/slot issues

---

## Success Criteria

✅ **Test is successful if:**
1. Progress bar moves from 0% to 100%
2. All selected items are processed
3. Summary shows correct counts
4. No crashes or errors
5. UI remains responsive
6. Results are displayed clearly

---

**Status:** Ready to test!  
**Commit:** d1898b5

Start testing and report any issues! 🧪

