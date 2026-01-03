# Plan: Improved Default Configuration Filtering

## Current State Analysis

Based on analysis of `SCM-Lab-FULL.json`:

| Category | Count | Description |
|----------|-------|-------------|
| **Default Items** | 97 | Should be filtered when "Ignore Defaults" is enabled |
| **Custom Items** | 124 | User-created configuration |
| **Total** | 221 | |

### Default Items Breakdown

| Item Type | Count | Snippet Value |
|-----------|-------|---------------|
| IKE Crypto Profiles | 22 | `default` |
| IPSec Crypto Profiles | 24 | `default` |
| HIP Objects | 27 | `default` (1) + `hip-default` (26) |
| HIP Profiles | 19 | `hip-default` |
| Tags | 3 | `default` (2) + `optional-default` (1) |
| Address Objects | 1 | `default` (Palo Alto Networks Sinkhole) |
| Certificate Profiles | 1 | `default` (EDL-Hosting-Service-Profile) |

---

## Key Finding: The `snippet` Field

The **`snippet` field** in the API response is the primary indicator for default vs custom items:

### Default Snippet Values
```
default          → General system defaults (crypto profiles, tags, etc.)
hip-default      → HIP-specific defaults (HIP objects/profiles)
optional-default → Optional pre-built defaults
```

### Custom Snippet Values (Examples)
```
NO_SNIPPET / null → User-created items not in any snippet
Basic Internet Access → Custom snippet
Web-Security-Default → Custom snippet (user-created, despite name)
office365 → Custom snippet
predefined-snippet → Custom snippet (confusing name, but user-created)
proxy → Custom snippet
```

---

## Implementation Plan

### Phase 1: Update Default Filtering Logic

**File:** `prisma/pull/pull_orchestrator.py`

```python
# Define default snippet values
DEFAULT_SNIPPETS = {
    'default',           # General system defaults
    'hip-default',       # HIP-specific defaults
    'optional-default',  # Optional pre-built defaults
}

def _is_default_item(self, item_data: dict) -> bool:
    """
    Determine if an item is a system default.
    
    Primary indicator: snippet field value
    """
    snippet = item_data.get('snippet', '')
    
    # Check if snippet indicates default
    if snippet in DEFAULT_SNIPPETS:
        return True
    
    # Check for snippet names ending in -default (catch future patterns)
    if snippet and snippet.endswith('-default'):
        return True
    
    return False
```

### Phase 2: Apply Filtering During Pull

Update `_get_folder_items()` and `_get_snippet_items()` methods:

```python
def _get_folder_items(self, folder: str, item_type: str, ...):
    items = self._fetch_items(...)
    
    if self.config.include_defaults:
        return items
    else:
        return [item for item in items if not self._is_default_item(item)]
```

### Phase 3: Update Infrastructure Filtering

Infrastructure items (IKE/IPSec crypto profiles) also have `snippet` field:

```python
def _pull_infrastructure_items(self, ...):
    # For ike_crypto_profile, ipsec_crypto_profile
    items = self._fetch_items(...)
    
    if not self.config.include_defaults:
        items = [item for item in items if not self._is_default_item(item)]
    
    return items
```

### Phase 4: Add UI Indicator for Default Items

In the config tree viewer, show which items are defaults:

```python
# In config_tree_builder.py
def _get_item_type_indicator(self, item_dict):
    snippet = item_dict.get('snippet', '')
    if snippet in DEFAULT_SNIPPETS or snippet.endswith('-default'):
        return "default"  # Shows as badge/icon
    return "custom"
```

---

## Expected Results After Implementation

### With "Ignore Defaults" ENABLED:

| Item Type | Before | After |
|-----------|--------|-------|
| HIP Objects | 27 | 0 |
| HIP Profiles | 19 | 0 |
| IKE Crypto Profiles | 22 | 0 |
| IPSec Crypto Profiles | 24 | 0 |
| Tags | 7 | 4 |
| Address Objects | 2 | 1 |
| Certificate Profiles | 1 | 0 |
| **Total** | **221** | **~124** |

### With "Ignore Defaults" DISABLED:
All 221 items pulled (current behavior preserved)

---

## Files to Modify

1. **`prisma/pull/pull_orchestrator.py`**
   - Add `DEFAULT_SNIPPETS` constant
   - Add `_is_default_item()` method
   - Update `_get_folder_items()` to filter by snippet
   - Update `_get_snippet_items()` to filter by snippet
   - Update `_pull_infrastructure_items()` to filter by snippet

2. **`gui/config_tree_builder.py`** (optional enhancement)
   - Add visual indicator for default vs custom items

3. **`config/workflows/default_manager.py`** (if exists)
   - Update default detection logic

---

## Testing

1. Pull with "Ignore Defaults" OFF → Should get all 221 items
2. Pull with "Ignore Defaults" ON → Should get ~124 items (no HIP objects/profiles, no default crypto profiles)
3. Verify custom items with snippet values are NOT filtered
4. Verify items with no snippet (null/empty) are NOT filtered

---

## Snippet Reference

### Known Default Snippets (Filter These)
| Snippet | Description |
|---------|-------------|
| `default` | System defaults |
| `hip-default` | HIP defaults |
| `optional-default` | Optional defaults |
| `*-default` | Any ending in -default |

### Known Custom Snippets (Keep These)
| Snippet | Description |
|---------|-------------|
| (empty/null) | User items not in snippet |
| `Web-Security-Default` | Despite name, this is custom |
| `predefined-snippet` | Despite name, this is custom |
| `Basic Internet Access` | Custom snippet |
| `office365` | Custom snippet |
| `proxy` | Custom snippet |

---

## Notes

- The `is_default` field in our model is NOT reliable (always `false`)
- The `snippet` field from the API is the authoritative source
- Some custom snippets have confusing names (e.g., "predefined-snippet") - these are user-created
- The `type` field for snippets (`predefined` vs `custom`) is different from item defaults
