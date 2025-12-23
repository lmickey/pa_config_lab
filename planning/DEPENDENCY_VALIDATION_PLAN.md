# Dependency Validation Integration Plan

## Current Status

### ✅ What We Have:
- `DependencyResolver` class in `prisma/dependencies/dependency_resolver.py`
- `DependencyGraph` for mapping relationships
- Methods to build dependency graphs from configs
- Methods to resolve dependencies

### ❌ What's Missing:
- **No integration in component selection dialog**
- **No automatic dependency inclusion**
- **No validation before push**

---

## Problem Statement

**Current Behavior:**
1. User selects "Service Connection" in component selection dialog
2. Service Connection has dependencies (crypto profiles, IKE gateways, etc.)
3. Dependencies are NOT automatically selected
4. Push will fail or be incomplete

**Desired Behavior:**
1. User selects "Service Connection"
2. System analyzes dependencies
3. System automatically selects required dependencies
4. User sees what was auto-selected
5. Push includes everything needed

---

## Integration Points

### 1. Component Selection Dialog
**File:** `gui/dialogs/component_selection_dialog.py`

**Changes Needed:**
- Add "Analyze Dependencies" button
- When user clicks "OK", run dependency analysis
- Show dialog with auto-selected dependencies
- Allow user to review and proceed

**Flow:**
```
1. User selects items in tree
2. User clicks "OK"
3. System runs DependencyResolver
4. System finds missing dependencies
5. Show dialog: "The following dependencies will be added: ..."
6. User clicks "OK" or "Cancel"
7. Return complete selection with dependencies
```

### 2. Push Preview Dialog
**File:** `gui/dialogs/push_preview_dialog.py`

**Changes Needed:**
- Run dependency validation during fetch
- Show "Missing Dependencies" tab if any found
- Warn user before proceeding

**Flow:**
```
1. Preview dialog opens
2. Fetches destination configs
3. Runs dependency analysis on selected items
4. Shows:
   - Conflicts tab
   - New Items tab
   - Missing Dependencies tab (if any)
5. User reviews and proceeds
```

---

## Implementation Plan

### Phase 1: Component Selection Integration

**Step 1.1: Add Dependency Analysis to Selection Dialog**
```python
# In component_selection_dialog.py

def get_selected_items(self) -> Dict[str, Any]:
    """Get selected items with dependencies."""
    selected = self._collect_selected_items()
    
    # Run dependency analysis
    from prisma.dependencies.dependency_resolver import DependencyResolver
    resolver = DependencyResolver()
    
    # Build graph from selected items
    # (Need to construct a config dict from selected items)
    temp_config = self._build_config_from_selection(selected)
    graph = resolver.build_dependency_graph(temp_config)
    
    # Find missing dependencies
    missing = resolver.find_missing_dependencies(graph)
    
    if missing:
        # Show dialog with missing deps
        reply = self._show_dependency_dialog(missing)
        if reply:
            # Add missing deps to selection
            selected = self._add_dependencies(selected, missing)
    
    return selected
```

**Step 1.2: Create Dependency Confirmation Dialog**
```python
class DependencyConfirmationDialog(QDialog):
    """Dialog to show auto-selected dependencies."""
    
    def __init__(self, missing_deps, parent=None):
        # Show tree of missing dependencies
        # Group by type
        # Allow user to review
        # Buttons: "Add Dependencies" / "Cancel"
```

### Phase 2: Push Preview Integration

**Step 2.1: Add Dependency Validation Tab**
```python
# In push_preview_dialog.py

def _analyze_and_populate(self):
    # ... existing conflict analysis ...
    
    # Add dependency validation
    self._validate_dependencies()

def _validate_dependencies(self):
    """Validate that all dependencies are included."""
    from prisma.dependencies.dependency_resolver import DependencyResolver
    
    resolver = DependencyResolver()
    temp_config = self._build_config_from_selection(self.selected_items)
    graph = resolver.build_dependency_graph(temp_config)
    
    missing = resolver.find_missing_dependencies(graph)
    
    if missing:
        # Add "Missing Dependencies" tab
        # Show warning
        # Optionally disable proceed button
```

### Phase 3: Helper Methods

**Step 3.1: Build Config from Selection**
```python
def _build_config_from_selection(self, selected_items: Dict) -> Dict:
    """Convert selected items dict to config dict for dependency analysis."""
    config = {
        'security_policies': {
            'folders': selected_items.get('folders', []),
            'snippets': selected_items.get('snippets', [])
        },
        'objects': selected_items.get('objects', {}),
        'infrastructure': selected_items.get('infrastructure', {})
    }
    return config
```

**Step 3.2: Add Dependencies to Selection**
```python
def _add_dependencies(self, selected_items: Dict, missing_deps: List) -> Dict:
    """Add missing dependencies to selection."""
    # Parse missing_deps and add to appropriate categories
    # Return updated selected_items
```

---

## Dependency Types to Handle

### Objects:
- Address Groups → Addresses
- Service Groups → Services
- Application Groups → Applications
- URL Categories → URL Filters

### Security Policies:
- Rules → Profiles (Security, URL Filtering, File Blocking, etc.)
- Rules → Objects (Addresses, Services, Applications)
- Rules → Zones

### Infrastructure:
- Service Connections → IKE Gateways
- Service Connections → IPSec Crypto Profiles
- Service Connections → IKE Crypto Profiles
- Remote Networks → IPSec Tunnels
- Remote Networks → IKE Gateways

### Profiles:
- Security Profiles → Threat Signatures
- Security Profiles → Custom Signatures
- URL Filtering Profiles → URL Categories

---

## UI/UX Considerations

### Component Selection Dialog:
1. **Option 1: Automatic (Recommended)**
   - Automatically analyze on "OK"
   - Show confirmation dialog if dependencies found
   - User can review and proceed

2. **Option 2: Manual**
   - Add "Analyze Dependencies" button
   - User must click to analyze
   - More control, but extra step

### Push Preview Dialog:
1. **Add "Dependencies" tab**
   - Show all dependencies
   - Mark which are included vs missing
   - Color code: Green = included, Red = missing

2. **Warning if missing**
   - Show warning banner at top
   - "⚠️ Missing dependencies detected. Push may fail."
   - Option to go back and add them

---

## Testing Strategy

### Test Cases:
1. **Address Group with Addresses**
   - Select address group
   - Verify addresses are auto-selected

2. **Service Connection**
   - Select service connection
   - Verify crypto profiles, IKE gateways are auto-selected

3. **Security Rule**
   - Select security rule
   - Verify profiles, objects are auto-selected

4. **Nested Dependencies**
   - Select address group that references another address group
   - Verify entire chain is selected

5. **Missing Dependencies**
   - Select item with missing dependencies
   - Verify warning is shown
   - Verify push is blocked or warned

---

## Implementation Priority

### High Priority (Must Have):
1. ✅ Fix built-in folder filtering
2. ✅ Fix progress bar visibility
3. 🔲 Add dependency analysis to component selection
4. 🔲 Show dependency confirmation dialog

### Medium Priority (Should Have):
1. 🔲 Add dependencies tab to push preview
2. 🔲 Validate dependencies before push
3. 🔲 Show missing dependencies warning

### Low Priority (Nice to Have):
1. 🔲 Manual "Analyze Dependencies" button
2. 🔲 Dependency graph visualization
3. 🔲 Circular dependency detection

---

## Next Steps

### Immediate (Complete GUI Steps First):
1. ✅ Fix progress bar display issue
2. ✅ Filter built-in folders
3. ✅ Add visual feedback for config load
4. Continue with Step 4 (Selective Push Orchestrator)

### After GUI Complete:
1. Implement dependency analysis in component selection
2. Add dependency confirmation dialog
3. Integrate into push preview
4. Test thoroughly

---

## Questions to Resolve

1. **Should dependency analysis be automatic or manual?**
   - Recommendation: Automatic with confirmation

2. **Should missing dependencies block push?**
   - Recommendation: Show warning, allow user to decide

3. **How to handle circular dependencies?**
   - Recommendation: Detect and show error

4. **Should we show dependency graph visually?**
   - Recommendation: Nice to have, not critical

---

## Estimated Effort

- **Component Selection Integration:** 2-3 hours
- **Dependency Confirmation Dialog:** 1-2 hours
- **Push Preview Integration:** 1-2 hours
- **Testing:** 2-3 hours
- **Total:** 6-10 hours

---

## Files to Modify

1. `gui/dialogs/component_selection_dialog.py` - Add dependency analysis
2. `gui/dialogs/push_preview_dialog.py` - Add validation tab
3. `gui/dialogs/dependency_confirmation_dialog.py` - NEW file
4. `prisma/dependencies/dependency_resolver.py` - Add helper methods if needed

---

## Success Criteria

✅ User selects component with dependencies
✅ System automatically detects dependencies
✅ User is shown what will be added
✅ User can review and proceed
✅ Push includes all required dependencies
✅ No missing dependency errors during push
