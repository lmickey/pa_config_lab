# Logging Level Audit Report

## Overview

This document analyzes all logging statements in the codebase and recommends appropriate log levels based on the 6-level system:

| Level | Value | Purpose |
|-------|-------|---------|
| ERROR | 40 | Failures that stop the operation |
| WARNING | 30 | Issues that don't stop operation but need attention |
| NORMAL | 25 | High-level tasks and responses (operation summaries, milestones) |
| INFO | 20 | Lower-level tasks/responses (per-item processing) |
| DETAIL | 15 | Verbose info: API URLs, specific keys/values, item counts |
| DEBUG | 10 | Developer-level debugging (stack traces, internal state) |

---

## Pull Operation Hierarchy

### 1. Top-Level Operation (NORMAL)
These are operation summaries that should always be visible at default logging:

| Current | File | Line | Message Pattern | Recommended |
|---------|------|------|-----------------|-------------|
| ✅ NORMAL | pull_orchestrator.py | 372-374 | `"=" * 80, "STARTING PULL OPERATION"` | NORMAL ✓ |
| ✅ NORMAL | pull_orchestrator.py | 624-626 | `"=" * 80, "PULL COMPLETE: X items"` | NORMAL ✓ |
| ✅ NORMAL | pull_orchestrator.py | 829 | `"[1/3] Processing folder: X"` | NORMAL ✓ |
| ✅ NORMAL | pull_orchestrator.py | 1003 | `"[1/27] Processing snippet: X"` | NORMAL ✓ |
| ⚠️ INFO | pull_orchestrator.py | 160 | `"Initializing Pull Orchestrator"` | **Detail** |
| ⚠️ INFO | pull_orchestrator.py | 341 | `"Pull Orchestrator initialized"` | **Detail** |

### 2. Folder/Snippet Processing Summary (INFO)
Per-folder or per-snippet summaries:

| Current | File | Line | Message Pattern | Recommended |
|---------|------|------|-----------------|-------------|
| ⚠️ INFO | pull_orchestrator.py | 398 | `"Using user-selected folders: [...]"` | INFO ✓ |
| ⚠️ INFO | pull_orchestrator.py | 402-403 | `"Using bottom-level folders..."` | INFO ✓ |
| ⚠️ INFO | pull_orchestrator.py | 409 | `"Found X folders"` | INFO ✓ |
| ⚠️ INFO | pull_orchestrator.py | 425 | `"Found X snippets"` | INFO ✓ |
| ⚠️ INFO | pull_orchestrator.py | 456 | `"Pulling folder-based items from X folders..."` | **NORMAL** |
| ⚠️ INFO | pull_orchestrator.py | 459 | `"Pulled X folder-based items"` | **INFO** |
| ⚠️ INFO | pull_orchestrator.py | 464 | `"Pulling snippet-based items from X snippets..."` | **NORMAL** |
| ⚠️ INFO | pull_orchestrator.py | 467 | `"Pulled X snippet-based items"` | **INFO** |
| ⚠️ INFO | pull_orchestrator.py | 472 | `"Pulling infrastructure items..."` | **NORMAL** |
| ⚠️ INFO | pull_orchestrator.py | 475 | `"Pulled X infrastructure items"` | **INFO** |
| ⚠️ INFO | pull_orchestrator.py | 479 | `"Building Configuration object..."` | INFO ✓ |
| ⚠️ INFO | pull_orchestrator.py | 617 | `"Configuration object created with X total items"` | **NORMAL** |

### 3. Per-Item Type Processing (INFO)
Individual item type processing within a folder:

| Current | File | Line | Message Pattern | Recommended |
|---------|------|------|-----------------|-------------|
| ⚠️ INFO | pull_orchestrator.py | 841 | `"Filtering to selected components: [...]"` | INFO ✓ |
| ⚠️ INFO | pull_orchestrator.py | 908 | `"X: Y items retrieved"` (per type) | INFO ✓ |
| ⚠️ INFO | pull_orchestrator.py | 1043 | `"X: Y items"` (snippet items) | INFO ✓ |
| ⚠️ INFO | pull_orchestrator.py | 1135-1144 | Infrastructure fetch per folder | INFO ✓ |
| ⚠️ INFO | pull_orchestrator.py | 1153-1156 | Infrastructure fetch global | INFO ✓ |
| ⚠️ INFO | pull_orchestrator.py | 566 | `"Folder items: X stored, Y filtered..."` | **NORMAL** |

### 4. Detailed Processing (DETAIL)
API URLs, response details, specific keys/values:

| Current | File | Line | Message Pattern | Recommended |
|---------|------|------|-----------------|-------------|
| ⚠️ DEBUG | pull_orchestrator.py | 892 | `"Fetching from: {url}"` | **DETAIL** |
| ⚠️ DEBUG | pull_orchestrator.py | 900-905 | `"Response contains 'data' with X items"` | **DETAIL** |
| ⚠️ DEBUG | pull_orchestrator.py | 909 | `"First item keys: [...]"` | **DETAIL** |
| ⚠️ INFO | pull_orchestrator.py | 503 | `"Folder filter active: allowed folders = ..."` | **DETAIL** |
| ⚠️ INFO | pull_orchestrator.py | 523 | `"Folder filter active: allowed components = ..."` | **DETAIL** |
| ⚠️ DEBUG | pull_orchestrator.py | 410 | `"Folders: [...]"` | **DETAIL** |
| ⚠️ DEBUG | pull_orchestrator.py | 426 | `"Snippets: [...]"` | **DETAIL** |

### 5. Individual Item Creation (DEBUG)
Creating/processing individual items:

| Current | File | Line | Message Pattern | Recommended |
|---------|------|------|-----------------|-------------|
| ⚠️ DEBUG | pull_orchestrator.py | 918 | `"Creating X 'Y'"` (per item) | DEBUG ✓ |
| ⚠️ DEBUG | pull_orchestrator.py | 925 | `"Skipping 'X' (default item)"` | DEBUG ✓ |
| ⚠️ DEBUG | pull_orchestrator.py | 931 | `"Created X 'Y'"` | DEBUG ✓ |
| ⚠️ DEBUG | pull_orchestrator.py | 935 | `"Skipping 'X' (filtered by config)"` | DEBUG ✓ |
| ⚠️ DEBUG | pull_orchestrator.py | 942 | `"Added X 'Y' to results"` | DEBUG ✓ |

---

## API Client Logging Hierarchy

### 1. API Operation Summary (NORMAL → INFO)

| Current | File | Line | Message Pattern | Recommended |
|---------|------|------|-----------------|-------------|
| ⚠️ INFO | api_client.py | 112 | `"Authenticating with Prisma Access API (TSG: X)"` | **NORMAL** |
| ⚠️ INFO | api_client.py | 151 | `"Authentication successful (token expires in Xs)"` | **NORMAL** |
| ⚠️ INFO | api_client.py | 212 | `"API GET request to {url}"` | **DETAIL** |
| ⚠️ INFO | api_client.py | 250 | `"API response: {status} in {duration}s"` | INFO ✓ |
| ⚠️ INFO | api_client.py | 289 | `"Response contains X data items"` | **DETAIL** |

### 2. CRUD Operations (INFO)

| Current | File | Line | Message Pattern | Recommended |
|---------|------|------|-----------------|-------------|
| ⚠️ INFO | api_client.py | 344 | `"Creating X 'Y'"` | INFO ✓ |
| ⚠️ INFO | api_client.py | 387-390 | `"Created X 'Y' (ID: Z)"` | INFO ✓ |
| ⚠️ INFO | api_client.py | 414 | `"Updating X 'Y'"` | INFO ✓ |
| ⚠️ INFO | api_client.py | 442 | `"Updated X 'Y'"` | INFO ✓ |
| ⚠️ INFO | api_client.py | 464 | `"Deleting X 'Y'"` | INFO ✓ |
| ⚠️ INFO | api_client.py | 488 | `"Deleted X 'Y'"` | INFO ✓ |

### 3. Request Details (DETAIL)

| Current | File | Line | Message Pattern | Recommended |
|---------|------|------|-----------------|-------------|
| ⚠️ DEBUG | api_client.py | 113-114 | `"Auth URL: ...", "API User: ..."` | **DETAIL** |
| ⚠️ DEBUG | api_client.py | 213 | `"Request params: {...}"` | DEBUG ✓ |
| ⚠️ DEBUG | api_client.py | 216 | `"Request body: {...}"` | DEBUG ✓|
| ⚠️ DEBUG | api_client.py | 223-226 | Cache HIT/MISS | **DETAIL** |
| ⚠️ DEBUG | api_client.py | 251 | `"Response headers: {...}"` | DEBUG ✓ |
| ⚠️ DEBUG | api_client.py | 290 | `"First data item keys: [...]"` | **DETAIL** |

---

## GUI Components Logging Hierarchy

### PullWidget (gui/pull_widget.py)

| Current | File | Line | Message Pattern | Recommended |
|---------|------|------|-----------------|-------------|
| ⚠️ INFO | pull_widget.py | 322 | `"Added X custom applications to selection"` | INFO ✓ |
| ⚠️ INFO | pull_widget.py | 461 | `"User requested to update selection"` | INFO ✓ |
| ⚠️ INFO | pull_widget.py | 474 | `"User requested pull cancellation"` | INFO ✓ |
| ⚠️ INFO | pull_widget.py | 495 | `"Tenant changed from 'X' to 'Y'"` | INFO ✓ |
| ⚠️ INFO | pull_widget.py | 567 | `"Discovered X custom snippets"` | INFO ✓ |
| ⚠️ INFO | pull_widget.py | 624 | `"Discovered X agent profiles"` | INFO ✓ |
| ⚠️ INFO | pull_widget.py | 688 | `"Starting pull with options: ..."` | **NORMAL** |
| ⚠️ INFO | pull_widget.py | 756 | `"Retrieved configuration from worker: X bytes"` | **DETAIL** |
| ⚠️ INFO | pull_widget.py | 785 | `"Emitting pull_completed signal with config"` | **DETAIL** |

### Workers (gui/workers.py)

| Current | File | Line | Message Pattern | Recommended |
|---------|------|------|-----------------|-------------|
| ⚠️ INFO | workers.py | 126 | `"Folder filter being sent to orchestrator: {...}"` | **DETAIL** |
| ⚠️ INFO | workers.py | 127 | `"Has real components to pull: X"` | **DETAIL** |
| ⚠️ INFO | workers.py | 128 | `"Include infrastructure: X"` | **DETAIL** |
| ⚠️ INFO | workers.py | 133-136 | Custom apps debugging | **DETAIL** |
| ⚠️ INFO | workers.py | 141 | `"Only custom applications selected - skipping API pull"` | INFO ✓ |
| ⚠️ INFO | workers.py | 168-205 | Various DEBUG prefixed messages | **DEBUG** |
| ⚠️ INFO | workers.py | 221 | `"Folders to query (with real components): [...]"` | **DETAIL** |
| ⚠️ INFO | workers.py | 277 | `"Added X custom applications to configuration"` | INFO ✓ |

### ConfigViewer (gui/config_viewer.py)

| Current | File | Line | Message Pattern | Recommended |
|---------|------|------|-----------------|-------------|
| ⚠️ INFO | config_viewer.py | 207-215 | All refresh_view logging | **DETAIL** |

### ConfigTreeBuilder (gui/config_tree_builder.py)

| Current | File | Line | Message Pattern | Recommended |
|---------|------|------|-----------------|-------------|
| ⚠️ INFO | config_tree_builder.py | 68-71 | `"build_tree called"`, config info | **DETAIL** |
| ⚠️ INFO | config_tree_builder.py | 81-90 | Section building calls | **DETAIL** |
| ⚠️ INFO | config_tree_builder.py | 120-138 | Smart expand decisions | **DETAIL** |
| ⚠️ INFO | config_tree_builder.py | 209-230 | Security policies section | **DETAIL** |
| ⚠️ INFO | config_tree_builder.py | 672 | Infrastructure section keys | **DETAIL** |
| ⚠️ INFO | config_tree_builder.py | 860-968 | Folder section building | **DETAIL** |

### TenantSelector (gui/widgets/tenant_selector.py)

| Current | File | Line | Message Pattern | Recommended |
|---------|------|------|-----------------|-------------|
| ⚠️ INFO | tenant_selector.py | 119 | `"Populated tenant selector with X tenant(s)"` | **DETAIL** |
| ⚠️ INFO | tenant_selector.py | 133 | `"Tenant selected from dropdown: X"` | INFO ✓ |
| ⚠️ INFO | tenant_selector.py | 155 | `"Attempting to connect to saved tenant: X"` | INFO ✓ |
| ⚠️ INFO | tenant_selector.py | 182 | `"Tenant loaded: X"` | **DETAIL** |
| ⚠️ INFO | tenant_selector.py | 198 | `"Creating API client for: X"` | INFO ✓ |
| ⚠️ INFO | tenant_selector.py | 219 | `"✓ Successfully connected to: X"` | **NORMAL** |
| ⚠️ INFO | tenant_selector.py | 258 | `"Opening manual connection dialog"` | **DETAIL** |
| ⚠️ INFO | tenant_selector.py | 269 | `"✓ Manual connection successful: X"` | **NORMAL** |
| ⚠️ INFO | tenant_selector.py | 291 | `"Manual connection cancelled or failed"` | **WARNING** |
| ⚠️ INFO | tenant_selector.py | 318 | `"Connection set: X"` | **DETAIL** |
| ⚠️ INFO | tenant_selector.py | 323 | `"Connection cleared"` | **DETAIL** |

---

## Summary of Required Changes

### Changes to NORMAL (High-Level Summaries)

These should be promoted from INFO to NORMAL:

1. **pull_orchestrator.py**:
   - Line 160: `"Initializing Pull Orchestrator"` → NORMAL
   - Line 341: `"Pull Orchestrator initialized"` → NORMAL
   - Line 456: `"Pulling folder-based items from X folders..."` → NORMAL
   - Line 459: `"Pulled X folder-based items"` → NORMAL
   - Line 464: `"Pulling snippet-based items from X snippets..."` → NORMAL
   - Line 467: `"Pulled X snippet-based items"` → NORMAL
   - Line 472: `"Pulling infrastructure items..."` → NORMAL
   - Line 475: `"Pulled X infrastructure items"` → NORMAL
   - Line 566: `"Folder items: X stored, Y filtered..."` → NORMAL
   - Line 617: `"Configuration object created with X total items"` → NORMAL

2. **api_client.py**:
   - Line 112: `"Authenticating with Prisma Access API"` → NORMAL
   - Line 151: `"Authentication successful"` → NORMAL

3. **pull_widget.py**:
   - Line 688: `"Starting pull with options..."` → NORMAL

4. **tenant_selector.py**:
   - Line 219: `"✓ Successfully connected to: X"` → NORMAL
   - Line 269: `"✓ Manual connection successful: X"` → NORMAL

### Changes to DETAIL (Verbose Details)

These should be demoted from INFO or promoted from DEBUG to DETAIL:

1. **pull_orchestrator.py** (INFO → DETAIL):
   - Lines 503, 523: Folder filter details
   - Line 892: `"Fetching from: {url}"` (currently DEBUG → DETAIL)
   - Lines 900-909: Response structure details (currently DEBUG → DETAIL)
   - Lines 410, 426: Lists of folders/snippets

2. **api_client.py** (INFO → DETAIL):
   - Line 212: `"API GET request to {url}"`
   - Line 289: `"Response contains X data items"`
   - Lines 113-114, 213, 216, 223-226, 251, 290: Request/response details (currently DEBUG → DETAIL)

3. **workers.py** (INFO → DETAIL):
   - Lines 126-136: Folder filter and debug info
   - Line 221: Folders to query list

4. **gui/config_viewer.py** (INFO → DETAIL):
   - Lines 207-215: All refresh_view logging

5. **gui/config_tree_builder.py** (INFO → DETAIL):
   - All INFO statements (lines 68-968): These are tree building internals

6. **tenant_selector.py** (INFO → DETAIL):
   - Lines 119, 182, 258, 291, 318, 323: Connection state details

### Keep as DEBUG

Messages prefixed with "DEBUG:" in workers.py (lines 144-209) should remain at DEBUG level.

---

## Estimated Line Counts After Changes

| Level | Current Count | After Changes |
|-------|---------------|---------------|
| ERROR | ~45 | ~45 (no change) |
| WARNING | ~35 | ~35 (no change) |
| NORMAL | ~20 | ~40 (+20) |
| INFO | ~180 | ~100 (-80) |
| DETAIL | 0 | ~80 (+80) |
| DEBUG | ~280 | ~260 (-20) |

---

## Production Log Output Examples

### NORMAL Level (Default)
```
NORMAL - ================================================================================
NORMAL - STARTING PULL OPERATION
NORMAL - ================================================================================
NORMAL - Initializing Pull Orchestrator
NORMAL - [1/3] Processing folder: Mobile Users
NORMAL - [2/3] Processing folder: Remote Networks
NORMAL - [3/3] Processing folder: Mobile Users Explicit Proxy
NORMAL - Pulling folder-based items from 3 folders...
NORMAL - Pulled 150 folder-based items
NORMAL - Configuration object created with 150 total items
NORMAL - ================================================================================
NORMAL - PULL COMPLETE: 150 items processed
NORMAL - ================================================================================
```

### INFO Level
```
(All NORMAL messages plus...)
INFO - Using user-selected folders: ['Mobile Users', 'Remote Networks']
INFO - Found 27 snippets
INFO - address_object: 45 items retrieved
INFO - security_rule: 12 items retrieved
INFO - Building Configuration object...
INFO - Created address_object 'web-server-01'
```

### DETAIL Level
```
(All NORMAL + INFO messages plus...)
DETAIL - Folder filter active: allowed folders = {'Mobile Users', 'Remote Networks'}
DETAIL - API GET request to https://api.sase.paloaltonetworks.com/sse/config/v1/addresses?folder=Mobile%20Users
DETAIL - Response contains 45 data items
DETAIL - First item keys: ['id', 'name', 'folder', 'ip_netmask']
DETAIL - ConfigTreeBuilder.build_tree called
DETAIL - folders keys: ['Mobile Users', 'Remote Networks']
```
