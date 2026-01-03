# Pull Progress Reporting System

## Overview

The pull orchestrator now provides detailed, real-time progress updates throughout the entire configuration pull process, giving users clear visibility into what's happening at every step.

## Problem Solved

**Before:**
- Pull operation would sit at 10% for several minutes
- No indication of what was happening
- Users thought the application had frozen
- ~300+ API calls happening silently

**After:**
- Detailed progress for every API call
- Shows current folder/snippet being processed
- Shows current configuration type being fetched
- Users can track progress in real-time

## Progress Breakdown

### Phase 1: Initialization (5-15%)
- `5%` - Starting pull operation
- `10%` - Identifying folders to query
- `12%` - Fetching snippets list from API
- `15%` - Ready to pull configurations

### Phase 2: Folder Configurations (15-55%)
For each of 3 folders (Mobile Users, Remote Networks, Explicit Proxy):
- Progress updates for each folder: `[1/3]`, `[2/3]`, `[3/3]`
- Progress updates for each type within folder: `(1/24)`, `(2/24)`, etc.
- ~72 API calls total (3 folders × 24 types)

Example messages:
```
[16%] [1/3] Pulling from folder: Mobile Users...
[17%] [1/3] Mobile Users: Address Object (1/24)...
[18%] [1/3] Mobile Users: Address Group (2/24)...
...
[35%] [2/3] Pulling from folder: Remote Networks...
```

### Phase 3: Snippet Configurations (55-85%)
For each of 27 snippets:
- Progress updates for each snippet: `[1/27]`, `[2/27]`, etc.
- Progress updates for each type within snippet: `(1/9)`, `(2/9)`, etc.
- ~243 API calls total (27 snippets × 9 types)

Example messages:
```
[56%] [1/27] Pulling from snippet: predefined-snippet...
[57%] [1/27] predefined-snippet: Address Object (1/9)...
[58%] [1/27] predefined-snippet: Address Group (2/9)...
...
[70%] [15/27] Pulling from snippet: office365...
```

### Phase 4: Infrastructure (85-90%)
- `85%` - Pulling infrastructure configs
- Infrastructure items (remote networks, regions, etc.)

### Phase 5: Finalization (90-100%)
- `90%` - Building Configuration object
- `95%` - Finalizing configuration
- `100%` - Pull operation complete!

## Technical Implementation

### 1. Progress Callback System

The `PullOrchestrator` supports a progress callback:

```python
orchestrator = PullOrchestrator(api_client, config=workflow_config)
orchestrator.set_progress_callback(lambda msg, pct: self.progress.emit(msg, pct))
```

### 2. Helper Methods

**`_emit_progress(message: str, percentage: int)`**
- Safely emits progress updates
- Only calls callback if set
- Handles errors gracefully

**`_calculate_progress(base_pct, current, total, range_pct)`**
- Calculates percentage within a range
- Example: For folder 2 of 3 in 15-55% range:
  - `base_pct=15`, `current=1`, `total=3`, `range_pct=40`
  - Returns: `15 + (1/3 * 40) = 28%`

### 3. Progress Points

Progress is emitted at these key locations:

**In `pull_all()` method:**
1. Start (5%)
2. Identifying folders (10%)
3. Fetching snippets (12%)
4. Before folder pull (15%)
5. Before snippet pull (55%)
6. Before infrastructure pull (85%)
7. Building configuration (90%)

**In `_pull_folder_items()` method:**
- For each folder being processed
- For each type within each folder

**In `_pull_snippet_items()` method:**
- For each snippet being processed
- For each type within each snippet

## Message Format

Messages follow consistent patterns for easy parsing:

### Folder Messages
```
[folder_num/total_folders] Pulling from folder: {folder_name}...
[folder_num/total_folders] {folder_name}: {Type Display} (type_num/total_types)...
```

Example:
```
[2/3] Pulling from folder: Remote Networks...
[2/3] Remote Networks: Security Rule (15/24)...
```

### Snippet Messages
```
[snippet_num/total_snippets] Pulling from snippet: {snippet_name}...
[snippet_num/total_snippets] {snippet_name}: {Type Display} (type_num/total_types)...
```

Example:
```
[5/27] Pulling from snippet: office365...
[5/27] office365: Address Group (3/9)...
```

## User Benefits

1. **Transparency**: Always know what's happening
2. **Progress Tracking**: See how much is complete
3. **Performance Monitoring**: Identify slow API calls
4. **Confidence**: No more wondering if app is frozen
5. **Time Estimation**: Percentage gives ETA sense

## Performance Impact

- **Minimal overhead**: Progress calculations are simple math
- **No extra API calls**: Only reporting what's already happening
- **Thread-safe**: Uses Qt signals for cross-thread communication
- **Non-blocking**: Progress emissions don't slow down pull

## Logging Correlation

Progress messages correlate with `activity.log` entries:

**GUI shows:**
```
[55%] [1/27] Pulling from snippet: predefined-snippet...
```

**Log shows:**
```
2026-01-02 21:15:30 - prisma.pull.pull_orchestrator - NORMAL - [1/27] Processing snippet: predefined-snippet
```

This allows debugging by comparing GUI progress with log timestamps.

## Future Enhancements

Potential improvements:
1. Add infrastructure type-level progress
2. Show item counts as they're fetched
3. Add elapsed/remaining time estimates
4. Configurable progress detail level
5. Progress history/replay for diagnostics

## Testing

To test progress system:

```bash
python3 run_gui_debug.py
# Start a config pull
# Watch progress updates in real-time
# Check logs/activity.log for correlation
```

Expected behavior:
- Progress should update every 1-2 seconds
- Should never hang at one percentage
- Should show clear current operation
- Should reach 100% on successful completion

---

**Implementation Date:** 2026-01-02
**Files Modified:** 
- `prisma/pull/pull_orchestrator.py`
- `gui/workers.py`
