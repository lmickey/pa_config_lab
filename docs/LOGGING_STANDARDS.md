# Logging Standards

**Version:** 2.0 (Updated for NORMAL level)  
**Date:** January 2, 2026

This document defines logging standards for the Prisma Access Configuration Lab project.

---

## Table of Contents

1. [Log Levels](#log-levels)
2. [When to Use Each Level](#when-to-use-each-level)
3. [Message Formats](#message-formats)
4. [Module-Specific Patterns](#module-specific-patterns)
5. [Debug Mode](#debug-mode)
6. [Performance Considerations](#performance-considerations)
7. [Testing](#testing)

---

## Log Levels

The project uses **5 log levels** in order of severity:

| Level | Value | Visibility | Purpose |
|-------|-------|------------|---------|
| **ERROR** | 40 | Always | Operation failures that prevent completion |
| **WARNING** | 30 | Always | Recoverable issues, items skipped |
| **NORMAL** | 25 | Production | Summary operations, key milestones (custom level) |
| **INFO** | 20 | Detailed | Normal operations, every step confirmed |
| **DEBUG** | 10 | Debug only | Diagnostic details, internal state |

### Level Hierarchy

```
ERROR (40)     ████████████████████████████████████████
WARNING (30)   ██████████████████████████████
NORMAL (25)    █████████████████████████
INFO (20)      ████████████████████
DEBUG (10)     ██████████
```

**Note:** NORMAL is a custom log level between WARNING and INFO.

---

## When to Use Each Level

### 🔴 ERROR (40) - Operation Failures

**Use when:** An operation cannot complete and user action is required.

**Examples:**
- API calls that fail completely
- Missing required data (ID, endpoint, credentials)
- Validation failures that block the workflow
- Cannot proceed with the current operation

**Code Pattern:**
```python
try:
    result = api_client.create_item(item)
except Exception as e:
    logger.error(f"Failed to create {item.item_type} '{item.name}': {e}", exc_info=True)
    raise
```

**Example Messages:**
```
2026-01-02 19:30:45 - ERROR - Cannot delete 'web-server': no ID set
2026-01-02 19:30:46 - ERROR - API request failed (status 400): Name conflict
2026-01-02 19:30:47 - ERROR - Authentication failed: Invalid credentials
```

**User Impact:** Operation stops, user must fix the issue to proceed.

---

### ⚠️ WARNING (30) - Recoverable Issues

**Use when:** Something unexpected happened, but the operation can continue.

**Examples:**
- Item skipped (already exists, conflicts)
- Optional validation warnings
- Default/system items excluded
- Deprecated API usage
- Missing optional fields

**Code Pattern:**
```python
if item_exists:
    logger.warning(f"Skipping {item.item_type} '{item.name}': already exists")
    result.items_skipped += 1
    continue
```

**Example Messages:**
```
2026-01-02 19:30:45 - WARNING - Skipping 'Allow-Web': already exists
2026-01-02 19:30:46 - WARNING - Could not overwrite 'db-group': still referenced
2026-01-02 19:30:47 - WARNING - Response validation warning: missing optional field 'description'
```

**User Impact:** Operation continues, user should be aware of the issue.

---

### 📊 NORMAL (25) - Summary Operations *(Custom Level)*

**Use when:** Logging major operation summaries and key milestones.

**Purpose:** Provide clean, high-level view of operations without overwhelming detail.

**Examples:**
- Workflow start/complete banners
- Summary counts (items processed, created, failed)
- Major phase transitions
- High-level progress updates

**Code Pattern:**
```python
logger.normal("=" * 80)
logger.normal("STARTING PULL OPERATION")
logger.normal("=" * 80)

# ... operations ...

logger.normal(f"PULL COMPLETE: {total} items processed in {duration}s")
```

**Example Messages:**
```
2026-01-02 19:30:45 - NORMAL - ================================================================================
2026-01-02 19:30:45 - NORMAL - STARTING PUSH OPERATION
2026-01-02 19:30:45 - NORMAL - ================================================================================
2026-01-02 19:31:30 - NORMAL - [1/3] Processing folder: Mobile Users
2026-01-02 19:32:15 - NORMAL - PUSH COMPLETE: 150 created, 5 skipped, 0 failed
```

**User Impact:** Clear understanding of major operations without excessive detail.

---

### ℹ️ INFO (20) - Normal Operations

**Use when:** Confirming every step of normal operations.

**Examples:**
- Successful create/update/delete
- Every workflow step
- Loading/saving configurations
- Object instantiation
- Progress through iterations
- API calls (summary, not full request/response)

**Code Pattern:**
```python
logger.info(f"Creating {item.item_type} '{item.name}' in {location}")
logger.info(f"Fetching {len(items)} {item_type} items from API")
logger.info(f"Validation passed: {count} items")
```

**Example Messages:**
```
2026-01-02 19:30:45 - INFO - Authenticating with Prisma Access API (TSG: 1570970024)
2026-01-02 19:30:46 - INFO - Authentication successful (token expires in 900s)
2026-01-02 19:30:47 - INFO - Creating address_object 'web-server' in Mobile Users
2026-01-02 19:30:48 - INFO - Created address_object 'web-server' (ID: abc-123)
2026-01-02 19:30:49 - INFO - Pulled 45 address_object items
```

**User Impact:** Detailed confirmation of every operation for troubleshooting.

---

### 🔍 DEBUG (10) - Diagnostic Details

**Use when:** Debug mode is enabled, providing internal diagnostic information.

**Examples:**
- Raw API request/response bodies
- Cache hit/miss operations
- Dependency resolution details
- Validation step-by-step
- Internal state changes
- Reference updates
- Data transformations
- Decision-making rationale

**Code Pattern:**
```python
logger.debug(f"API Request: {method} {url}")
logger.debug(f"Request body: {json.dumps(data, indent=2)}")
logger.debug(f"Cache HIT for {cache_key[:100]}")
logger.debug(f"Computing dependencies for '{item.name}'")
logger.debug(f"Updated reference: {old_name} → {new_name}")
```

**Example Messages:**
```
2026-01-02 19:30:45 - DEBUG - [api_client.py:185] Auth URL: https://auth.apps.paloaltonetworks.com/oauth2/access_token
2026-01-02 19:30:45 - DEBUG - [api_client.py:195] Request body: {
  "grant_type": "client_credentials",
  "scope": "tsg_id:1570970024"
}
2026-01-02 19:30:46 - DEBUG - [api_client.py:230] Response status: 200
2026-01-02 19:30:46 - DEBUG - [api_client.py:245] Token: eyJhbGciOiJSUzI1NiIsIn...
2026-01-02 19:30:47 - DEBUG - [api_client.py:195] Cache MISS for GET:https://api.sase...
2026-01-02 19:30:48 - DEBUG - [pull_orchestrator.py:395] Computing dependencies for 'web-servers'
```

**User Impact:** Troubleshooting only, not visible in normal or production modes.

---

## Message Formats

### Standard Format

```
YYYY-MM-DD HH:MM:SS - LEVEL - message
```

Example:
```
2026-01-02 19:30:45 - INFO - Created address_object 'web-server'
```

### Debug Format

Includes file and line number:

```
YYYY-MM-DD HH:MM:SS - LEVEL - [filename:lineno] - message
```

Example:
```
2026-01-02 19:30:45 - DEBUG - [api_client.py:245] - Token: eyJhbGci...
```

### Banner Format

For NORMAL level, use banners for major operations:

```python
logger.normal("=" * 80)
logger.normal("OPERATION NAME")
logger.normal("=" * 80)
```

---

## Module-Specific Patterns

### API Client (`prisma/api_client.py`)

**INFO:**
- Authentication start/success
- API request summary (method, URL, status)
- Response item counts

**DEBUG:**
- Request headers, body
- Response headers, body, detailed fields
- Cache operations (hit/miss)
- Token details

```python
# INFO
logger.info(f"API {method} request to {url}")
logger.info(f"API response: {status_code} in {duration:.2f}s")

# DEBUG
logger.debug(f"Request params: {params}")
logger.debug(f"Request body: {json.dumps(data, indent=2)}")
logger.debug(f"Response body: {response.text[:500]}")
logger.debug(f"Cache HIT for {cache_key[:100]}")
```

### Pull Orchestrator (`prisma/pull/pull_orchestrator.py`)

**NORMAL:**
- Workflow start/complete banners
- Folder/snippet processing progress
- Summary counts

**INFO:**
- Each step description
- Items retrieved per type
- Filtering decisions

**DEBUG:**
- API endpoint details
- Item-by-item processing
- Filter/default checks

```python
# NORMAL
logger.normal("=" * 80)
logger.normal("STARTING PULL OPERATION")
logger.normal(f"[{idx}/{total}] Processing folder: {folder}")

# INFO
logger.info(f"Pulling folder-based items from {len(folders)} folders")
logger.info(f"  {item_type}: {len(items)} items retrieved")

# DEBUG
logger.debug(f"Item types to pull: {self.FOLDER_TYPES}")
logger.debug(f"    [{idx}/{total}] Creating {item_type} '{name}'")
```

### Push Orchestrator (`prisma/push/push_orchestrator_v2.py`)

**NORMAL:**
- Workflow start/complete banners
- Phase transitions
- Summary results

**INFO:**
- Each step description
- Items created/updated/skipped
- Conflict resolutions

**DEBUG:**
- Dependency resolution details
- Existence checks
- Name mappings

```python
# NORMAL
logger.normal("=" * 80)
logger.normal("STARTING PUSH OPERATION")
logger.normal(f"PUSH COMPLETE: {created} created, {skipped} skipped")

# INFO
logger.info(f"Step 1: Checking for existing items")
logger.info(f"Creating {item.item_type} '{item.name}'")

# DEBUG
logger.debug(f"Workflow ID: {self.state.workflow_id}")
logger.debug(f"Execution order: {len(items)} items")
```

### ConfigItem Classes (`config/models/`)

**INFO:**
- Object creation
- Validation success
- State changes (rename, delete marking)

**DEBUG:**
- Field-by-field validation
- Dependency computation
- Internal transformations

```python
# INFO (in base.py __init__)
logger.info(f"Creating {self.item_type} '{self.name}'")
logger.info(f"Validation passed for '{self.name}'")

# DEBUG
logger.debug(f"Setting field '{field}': {value}")
logger.debug(f"Computing dependencies for '{self.name}'")
```

### Factory (`config/models/factory.py`)

**INFO:**
- Successful item creation

**DEBUG:**
- Type registration
- Model class lookup
- Endpoint mapping

```python
# INFO
logger.info(f"Created {item_type} '{item.name}' from API data")

# DEBUG
logger.debug(f"Registered endpoint '{endpoint}' → '{item_type}'")
logger.debug(f"Model class: {model_class.__name__}")
```

---

## Debug Mode

### Enabling Debug Mode

```python
from config.logging_config import enable_debug_mode, disable_debug_mode

# Enable
enable_debug_mode()  # Sets level to DEBUG, enables debug filter

# Disable
disable_debug_mode()  # Resets to default level
```

### Debug Mode Behavior

**Normal Mode:**
- ERROR, WARNING, NORMAL, INFO messages visible
- ~85% of all log statements
- 10-20 messages per operation
- 1-2% performance overhead

**Debug Mode (+DEBUG):**
- All messages visible including DEBUG
- ~100% of all log statements (+15%)
- 12-25 messages per operation (+20%)
- 5-10% performance overhead
- Includes:
  - Raw API request/response bodies
  - Cache operations (hit/miss)
  - Step-by-step validation
  - Internal state changes
  - Decision-making rationale

### Conditional Debug Logging

For expensive operations (e.g., large data serialization):

```python
if logger.isEnabledFor(logging.DEBUG):
    logger.debug(f"Full data: {expensive_serialization(data)}")
```

---

## Performance Considerations

### Overhead by Level

| Mode | Messages/Op | Overhead |
|------|-------------|----------|
| ERROR only | 2-5 | <1% |
| WARNING | 5-10 | 1% |
| NORMAL | 8-15 | 1-2% |
| INFO | 10-20 | 2-3% |
| DEBUG | 12-25 | 5-10% |

### Best Practices

1. **Use appropriate levels** - Don't log everything as INFO
2. **Avoid logging in tight loops** - Use summary counts instead
3. **Defer expensive operations** - Use `isEnabledFor()` for DEBUG
4. **Keep messages concise** - Truncate large data structures
5. **Use structured logging** - Include context (type, name, location)

### Anti-Patterns

**❌ Don't do this:**
```python
# Logging in tight loop
for item in items:  # 1000+ items
    logger.info(f"Processing {item}")

# Expensive DEBUG without check
logger.debug(f"Full config: {json.dumps(huge_config, indent=2)}")

# Vague message
logger.error("Error occurred")
```

**✅ Do this instead:**
```python
# Summary logging
logger.info(f"Processing {len(items)} items")
for idx, item in enumerate(items):
    if idx % 100 == 0:
        logger.info(f"Progress: {idx}/{len(items)} items")

# Conditional expensive operation
if logger.isEnabledFor(logging.DEBUG):
    logger.debug(f"Full config: {json.dumps(huge_config, indent=2)}")

# Clear, actionable message
logger.error(f"Failed to create {item_type} '{name}': {error}")
```

---

## Testing

### Logging Tests

Tests should verify:
1. Correct log level usage
2. Message format consistency
3. Debug mode toggle
4. Performance overhead acceptable

### Example Test

```python
def test_logging_levels():
    """Verify correct log level usage."""
    with LogCapture() as logs:
        # Should log INFO
        item.create()
        assert any("Created" in msg and level == "INFO" for level, msg in logs)
        
        # Should log ERROR on failure
        with pytest.raises(Exception):
            item.delete()  # No ID set
        assert any("Cannot delete" in msg and level == "ERROR" for level, msg in logs)
```

### Log Rotation Tests

```python
def test_log_rotation():
    """Verify log files rotate correctly."""
    log_file = Path("test.log")
    
    # Create initial log
    setup_logging(log_file=log_file)
    logger.info("Initial")
    
    # Rotate
    setup_logging(log_file=log_file, rotate=True)
    
    # Verify rotation
    assert (log_file.parent / "test-1.log").exists()
```

---

## Quick Reference

### Log Level Decision Tree

```
Can the operation continue?
├─ No → ERROR
└─ Yes
    ├─ Is it a summary/banner? → NORMAL
    ├─ Is it unexpected? → WARNING
    ├─ Is it a normal operation? → INFO
    └─ Is it diagnostic detail? → DEBUG
```

### Common Scenarios

| Scenario | Level | Example |
|----------|-------|---------|
| Workflow start | NORMAL | `"STARTING PULL OPERATION"` |
| API authentication | INFO | `"Authenticating with API"` |
| API auth success | INFO | `"Authentication successful"` |
| API auth failure | ERROR | `"Authentication failed: {error}"` |
| Item created | INFO | `"Created address_object 'web-server'"` |
| Item skipped | WARNING | `"Skipping 'web-server': already exists"` |
| Item creation failed | ERROR | `"Failed to create 'web-server': {error}"` |
| Processing folder | NORMAL | `"[1/3] Processing folder: Mobile Users"` |
| Items fetched | INFO | `"Fetched 45 address_object items"` |
| API request | INFO | `"API GET request to {url}"` |
| API request body | DEBUG | `"Request body: {json}"` |
| Cache hit | DEBUG | `"Cache HIT for {key}"` |
| Dependency resolution | DEBUG | `"Computing dependencies for '{name}'"` |
| Workflow complete | NORMAL | `"PULL COMPLETE: 150 items processed"` |

---

## Summary

**5 Log Levels:**
1. **ERROR** (40) - Cannot continue
2. **WARNING** (30) - Can continue, user aware
3. **NORMAL** (25) - Summary operations
4. **INFO** (20) - Every step confirmed
5. **DEBUG** (10) - Diagnostic details

**Best Practices:**
- Use the right level for the situation
- Include context (type, name, location)
- Keep messages concise and actionable
- Avoid logging in tight loops
- Use conditional debug for expensive operations

**Normal vs Debug:**
- Normal: 85% of logs, summaries + operations
- Debug: +15% logs, raw data + internals

**Current Status:**
- ✅ 400+ log statements across codebase
- ✅ Well-distributed across modules
- ✅ Minimal performance impact
- ✅ Comprehensive debug mode

---

*Last updated: January 2, 2026 (Phase 9.5: Enhanced Logging)*
