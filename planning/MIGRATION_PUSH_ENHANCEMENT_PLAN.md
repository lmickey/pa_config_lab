# Migration Push Enhancement Plan

## Overview
Complete the migration workflow with selective push capabilities and multi-tenant support.

---

## Current Problems

### 1. No Selective Push
- ❌ Can only push entire pulled config
- ❌ Can't select specific folders/components to push
- ❌ Can't combine parts from different configs
- ❌ Have to re-pull if want different selection

### 2. Single Tenant Connection
- ❌ Pull and Push use same tenant connection
- ❌ Can't migrate from Tenant A to Tenant B
- ❌ Have to disconnect/reconnect manually

### 3. Tenant Credential Management
- ❌ No saved tenant list
- ❌ Re-enter credentials every time
- ❌ No labels to identify tenants

---

## Solution Architecture

### Phase 1: Tenant Management System

#### 1.1 Tenant Storage
**Location:** `~/.pa_config_lab/tenants.json` (encrypted)

**Data Structure:**
```json
{
  "tenants": [
    {
      "id": "uuid-1234",
      "name": "Production Tenant",
      "tsg_id": "1234567890",
      "client_id": "sa-12345@...iam.panserviceaccount.com",
      "description": "Main production environment",
      "last_used": "2024-12-22T15:30:00Z",
      "created": "2024-12-01T10:00:00Z"
    },
    {
      "id": "uuid-5678",
      "name": "Dev Tenant",
      "tsg_id": "9876543210",
      "client_id": "sa-67890@...iam.panserviceaccount.com",
      "description": "Development and testing",
      "last_used": "2024-12-20T12:00:00Z",
      "created": "2024-12-01T10:05:00Z"
    }
  ],
  "version": "1.0"
}
```

**Security:**
- ✅ File encrypted with user password/key
- ✅ Client secrets NOT stored
- ✅ User enters secret on connect
- ✅ Secret cached in memory during session only

#### 1.2 Tenant Manager Class
**File:** `config/tenant_manager.py`

**Methods:**
```python
class TenantManager:
    def add_tenant(name, tsg_id, client_id, description="")
    def update_tenant(id, name=None, tsg_id=None, client_id=None, description=None)
    def delete_tenant(id)
    def get_tenant(id)
    def list_tenants()
    def search_tenants(query)
    def mark_used(id)  # Update last_used timestamp
```

#### 1.3 Tenant Management Dialog
**File:** `gui/dialogs/tenant_manager_dialog.py`

**Features:**
- List all saved tenants (name, TSG, last used)
- Add new tenant (name, TSG, client_id, description)
- Edit tenant details
- Delete tenant (with confirmation)
- Search/filter tenants
- Sort by name/last used

**UI Layout:**
```
┌────────────────────────────────────────────┐
│ Tenant Management                          │
├────────────────────────────────────────────┤
│ [Search: ____________] [Add New]           │
│                                            │
│ ┌────────────────────────────────────────┐ │
│ │ ☑ Production Tenant                    │ │
│ │   TSG: 1234567890                      │ │
│ │   Last used: 2 hours ago               │ │
│ │   [Edit] [Delete]                      │ │
│ │                                        │ │
│ │ ☐ Dev Tenant                           │ │
│ │   TSG: 9876543210                      │ │
│ │   Last used: 2 days ago                │ │
│ │   [Edit] [Delete]                      │ │
│ └────────────────────────────────────────┘ │
│                                            │
│                        [Close]             │
└────────────────────────────────────────────┘
```

---

### Phase 2: Multi-Tenant Connection

#### 2.1 Enhanced Connection Dialog
**File:** `gui/connection_dialog.py` (modify existing)

**Changes:**
- Add "Select from saved tenants" option
- Dropdown to choose saved tenant
- Auto-fill TSG and client_id when tenant selected
- Still prompt for client_secret (never stored)
- Option to save as new tenant after manual entry

**UI Flow:**
```
┌────────────────────────────────────────┐
│ Connect to Prisma Access              │
├────────────────────────────────────────┤
│ ⦿ Saved Tenant                         │
│   [▼ Production Tenant              ]  │
│                                        │
│ ○ Manual Entry                         │
│   TSG ID: [____________________]       │
│   Client ID: [_________________]       │
│                                        │
│ Client Secret: [___________________]   │
│ ☑ Save as new tenant                   │
│                                        │
│              [Connect] [Cancel]        │
└────────────────────────────────────────┘
```

#### 2.2 Connection Context
**Update:** Track which tenant is connected for pull vs push

```python
class MigrationWorkflow:
    self.source_tenant = None  # Tenant connected for pull
    self.source_api_client = None
    
    self.destination_tenant = None  # Tenant connected for push
    self.destination_api_client = None
```

#### 2.3 Dual Connection UI
**Migration Workflow Tabs:**
```
┌─────────────────────────────────────────────────┐
│ [Pull] [Review] [Push] [Saved Configs]         │
├─────────────────────────────────────────────────┤
│ Source: Connected to "Production Tenant"       │
│ Destination: Not connected [Connect]           │
└─────────────────────────────────────────────────┘
```

---

### Phase 3: Selective Push

#### 3.1 Push Selection Dialog
**File:** `gui/dialogs/push_selection_dialog.py`

**Features:**
- Show loaded config structure
- Tree view with checkboxes
- Select folders to push
- Select components per folder (Objects, Profiles, Rules)
- Select snippets to push
- Summary of selections

**UI Layout:**
```
┌──────────────────────────────────────────────┐
│ Select Configuration to Push                 │
├──────────────────────────────────────────────┤
│ Config: customer_migration_v1                │
│ Source: Pull - 1234567890                    │
│                                              │
│ ┌──────────────────────────────────────────┐ │
│ │ ☑ Folders                                │ │
│ │   ☑ Mobile Users                         │ │
│ │     ☑ Objects                            │ │
│ │     ☑ Profiles                           │ │
│ │     ☑ Rules (45)                         │ │
│ │   ☑ Remote Networks                      │ │
│ │     ☑ Objects                            │ │
│ │     ☐ Profiles                           │ │
│ │     ☑ Rules (12)                         │ │
│ │   ☐ Branch Offices                       │ │
│ │                                          │ │
│ │ ☑ Snippets (2 selected)                  │ │
│ │   ☑ custom-security-snippet              │ │
│ │   ☐ best-practice-snippet                │ │
│ └──────────────────────────────────────────┘ │
│                                              │
│ Summary: 2 folders, 57 rules, 1 snippet     │
│                                              │
│                      [OK] [Cancel]           │
└──────────────────────────────────────────────┘
```

#### 3.2 Push Widget Enhancement
**File:** `gui/push_widget.py`

**Changes:**
- Add "Select Items to Push" button
- Show selection summary
- Button opens PushSelectionDialog
- Store selections: `selected_folders`, `selected_components`, `selected_snippets`

**Updated Layout:**
```
┌─────────────────────────────────────────┐
│ Push Configuration                      │
├─────────────────────────────────────────┤
│ Destination: ✓ Connected to Dev Tenant │
│              [Disconnect] [Change]      │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ Configuration Selection             │ │
│ │ [📋 Select Items to Push]           │ │
│ │                                     │ │
│ │ Current: 2 folders, 57 rules,       │ │
│ │          1 snippet selected          │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ Push Options                        │ │
│ │ ☑ Test mode (validate only)        │ │
│ │ ☑ Create dependencies               │ │
│ │ ☐ Skip existing objects             │ │
│ │                                     │ │
│ │ Conflict Resolution:                │ │
│ │ ⦿ Ask for each conflict             │ │
│ │ ○ Overwrite all                     │ │
│ │ ○ Skip all conflicts                │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ [Push Configuration]                    │
└─────────────────────────────────────────┘
```

---

### Phase 4: Push Orchestration

#### 4.1 Update Push Orchestrator
**File:** `prisma/push/push_orchestrator.py`

**New Parameters:**
```python
def push_configuration(
    config: Dict[str, Any],
    selected_folders: Optional[List[str]] = None,
    selected_components: Optional[Dict[str, List[str]]] = None,
    selected_snippets: Optional[List[str]] = None,
    test_mode: bool = False,
    conflict_resolution: str = "ask",
    create_dependencies: bool = True,
    skip_existing: bool = False
):
```

**Logic:**
1. Filter config based on selections
2. Validate all selected items exist in config
3. Build dependency graph
4. Push in correct order
5. Handle conflicts per user preference
6. Report results

#### 4.2 Selective Push Logic
```python
def _filter_config_for_push(config, selected_folders, selected_components, selected_snippets):
    """Filter config to only include selected items."""
    filtered = {
        "metadata": config["metadata"],
        "security_policies": {
            "folders": [],
            "snippets": []
        }
    }
    
    # Filter folders and components
    for folder in config["security_policies"]["folders"]:
        folder_name = folder["name"]
        if folder_name not in selected_folders:
            continue
        
        # Check component selections
        folder_components = selected_components.get(folder_name, [])
        
        filtered_folder = {
            "name": folder_name,
            "objects": folder["objects"] if "objects" in folder_components else {},
            "profiles": folder["profiles"] if "profiles" in folder_components else {},
            "security_rules": folder["security_rules"] if "rules" in folder_components else []
        }
        
        filtered["security_policies"]["folders"].append(filtered_folder)
    
    # Filter snippets
    for snippet in config["security_policies"]["snippets"]:
        if snippet["name"] in selected_snippets:
            filtered["security_policies"]["snippets"].append(snippet)
    
    return filtered
```

---

## Implementation Plan

### Week 1: Tenant Management (Days 1-3)

#### Day 1: Backend
- [ ] Create `config/tenant_manager.py`
- [ ] Implement TenantManager class
- [ ] Add encryption for tenant storage
- [ ] Write unit tests

**Files:**
- `config/tenant_manager.py` (new)
- `tests/test_tenant_manager.py` (new)

#### Day 2: UI
- [ ] Create tenant management dialog
- [ ] Add/Edit/Delete tenant UI
- [ ] Search and filter functionality
- [ ] Integration with main menu

**Files:**
- `gui/dialogs/tenant_manager_dialog.py` (new)
- `gui/main_window.py` (add menu item)

#### Day 3: Connection Integration
- [ ] Update connection dialog
- [ ] Add tenant dropdown
- [ ] Auto-fill from saved tenant
- [ ] Save new tenant option

**Files:**
- `gui/connection_dialog.py` (modify)

---

### Week 2: Multi-Tenant Connection (Days 4-5)

#### Day 4: Dual Connection
- [ ] Add destination tenant connection to migration workflow
- [ ] Update UI to show source/destination
- [ ] Connect/disconnect for each independently
- [ ] Status indicators for both

**Files:**
- `gui/workflows/migration_workflow.py` (modify)

#### Day 5: Connection Flow
- [ ] Pull uses source tenant
- [ ] Push prompts for destination if not connected
- [ ] Can change destination without affecting source
- [ ] Session persistence

**Files:**
- `gui/pull_widget.py` (use source_api_client)
- `gui/push_widget.py` (use destination_api_client)

---

### Week 3: Selective Push (Days 6-8)

#### Day 6: Push Selection Dialog
- [ ] Create push selection dialog
- [ ] Tree view with loaded config
- [ ] Checkbox selection for folders/components/snippets
- [ ] Summary display

**Files:**
- `gui/dialogs/push_selection_dialog.py` (new)

#### Day 7: Push Widget Integration
- [ ] Add "Select Items to Push" button
- [ ] Display selection summary
- [ ] Pass selections to push worker
- [ ] Validate selections before push

**Files:**
- `gui/push_widget.py` (modify)

#### Day 8: Push Orchestration
- [ ] Update push orchestrator with selective push
- [ ] Filter config based on selections
- [ ] Dependency resolution for filtered config
- [ ] Maintain all conflict resolution features

**Files:**
- `prisma/push/push_orchestrator.py` (modify)

---

### Week 4: Testing & Polish (Days 9-10)

#### Day 9: Integration Testing
- [ ] Test tenant management (add/edit/delete)
- [ ] Test dual connection (source + destination)
- [ ] Test selective push (various combinations)
- [ ] Test conflict resolution with selective push

#### Day 10: Documentation & Cleanup
- [ ] Update README with tenant management
- [ ] Add screenshots for new dialogs
- [ ] Update workflow documentation
- [ ] Clean up and commit

---

## File Structure

### New Files
```
config/
  tenant_manager.py           # Tenant CRUD operations

gui/dialogs/
  tenant_manager_dialog.py    # Tenant management UI
  push_selection_dialog.py    # Push selection UI

tests/
  test_tenant_manager.py      # Unit tests

docs/
  TENANT_MANAGEMENT.md        # Tenant docs
  SELECTIVE_PUSH.md           # Push workflow docs
```

### Modified Files
```
gui/
  connection_dialog.py        # Add tenant dropdown
  main_window.py              # Add tenant menu
  push_widget.py              # Add selection button
  workflows/migration_workflow.py  # Dual connection

prisma/push/
  push_orchestrator.py        # Selective push logic
```

---

## Security Considerations

### What We Store
✅ TSG ID
✅ Client ID
✅ Tenant name/label
✅ Description
✅ Timestamps

### What We DON'T Store
❌ Client Secret
❌ Access Tokens
❌ API Keys

### Encryption
- Tenant file encrypted with user-specific key
- Key derived from system + user info
- No secrets in memory when not connected
- Clear sensitive data on disconnect

---

## Future Enhancements (Not in Scope)

### Phase 5: Advanced Features
- [ ] Tenant groups/categories
- [ ] Import/export tenant lists
- [ ] Tenant health checks
- [ ] Connection history/logs
- [ ] Multi-config merge (combine parts from multiple configs)
- [ ] Template-based push (define push patterns)

### POV Workflow Integration
- [ ] Use tenant list in POV workflow
- [ ] Switch between tenants easily
- [ ] Compare configs across tenants
- [ ] Clone tenant configurations

---

## Success Criteria

### Tenant Management
✅ Can add/edit/delete tenants
✅ Can search and filter tenant list
✅ Tenant data persists between sessions
✅ No client secrets stored

### Multi-Tenant Connection
✅ Can connect to source tenant for pull
✅ Can connect to different destination tenant for push
✅ Both connections independent
✅ Clear status indicators for both

### Selective Push
✅ Can load config and select folders to push
✅ Can select components per folder
✅ Can select snippets to push
✅ Summary shows what will be pushed
✅ Can change selections and push again

### Migration Workflow
✅ Pull from Tenant A
✅ Review and select items
✅ Push to Tenant B
✅ All conflict resolution works
✅ Test mode validates without changing

---

## Testing Checklist

### Tenant Management
- [ ] Add new tenant
- [ ] Edit existing tenant
- [ ] Delete tenant
- [ ] Search tenants
- [ ] File encryption works
- [ ] Data persists after restart

### Connection
- [ ] Connect to saved tenant
- [ ] Connect manually
- [ ] Save new tenant after manual connect
- [ ] Client secret not stored
- [ ] Disconnect and reconnect

### Dual Connection
- [ ] Connect source tenant
- [ ] Pull configuration
- [ ] Connect different destination tenant
- [ ] Source still connected
- [ ] Push to destination

### Selective Push
- [ ] Select specific folders
- [ ] Select components per folder
- [ ] Select snippets
- [ ] Deselect and reselect
- [ ] Push only selected items
- [ ] Verify only selected items pushed

### End-to-End
- [ ] Pull from Production
- [ ] Select 2 of 5 folders
- [ ] Select specific components
- [ ] Push to Dev tenant
- [ ] Verify correct items pushed
- [ ] Load different config
- [ ] Select different items
- [ ] Push to same tenant
- [ ] Verify additive push works

---

## Timeline Summary

- **Week 1:** Tenant management backend and UI
- **Week 2:** Multi-tenant connection support
- **Week 3:** Selective push implementation
- **Week 4:** Testing and documentation

**Total Effort:** ~10 development days

**Dependencies:** None (all additive changes)

**Risks:** Low (no breaking changes to existing workflows)
