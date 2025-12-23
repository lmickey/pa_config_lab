# Phase 3 - Selective Push Implementation Plan

**Date:** December 23, 2025  
**Status:** 🚀 PLANNING

## Overview

Phase 3 focuses on implementing **selective push** functionality, allowing users to:
1. Load a saved configuration
2. Select specific components to push
3. Choose destination tenant
4. Push only selected items with conflict detection

---

## 🎯 Goals

### Primary Objectives:
1. ✅ Load saved configurations in Push tab
2. ✅ Select specific folders/snippets/components to push
3. ✅ Validate selections before push
4. ✅ Show what will be pushed (preview)
5. ✅ Push only selected items to destination

### Secondary Objectives:
1. ⚠️ Dependency resolution (show what else is needed)
2. ⚠️ Conflict detection (warn if exists in destination)
3. ⚠️ Dry-run mode (validate without pushing)
4. ⚠️ Push progress tracking
5. ⚠️ Push result summary

---

## 📋 Current State

### What We Have:
- ✅ Pull widget with folder/snippet selection
- ✅ Config viewer showing all components
- ✅ Push widget with destination tenant selection
- ✅ Saved configs manager
- ✅ Multi-tenant support

### What's Missing:
- ❌ Load config into Push tab
- ❌ Selection UI for push
- ❌ Preview what will be pushed
- ❌ Selective push orchestrator
- ❌ Push validation
- ❌ Push progress tracking

---

## 🏗️ Architecture

### Component Flow:

```
┌─────────────────────────────────────────────────────────┐
│                    Migration Workflow                    │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────┐      ┌─────────┐      ┌──────────┐        │
│  │  Pull   │ ───> │  View   │ ───> │   Push   │        │
│  │ Widget  │      │ Widget  │      │  Widget  │        │
│  └─────────┘      └─────────┘      └──────────┘        │
│       │                │                  │              │
│       │                │                  │              │
│       v                v                  v              │
│  Pull Config    View/Select        Push Selected        │
│  from Source    Components         to Destination       │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### New Components Needed:

1. **ConfigSelectionDialog** - Select what to push
2. **PushPreviewDialog** - Preview before push
3. **SelectivePushOrchestrator** - Push only selected items
4. **PushValidator** - Validate before push
5. **PushProgressDialog** - Track push progress

---

## 🎨 UI Design

### Push Widget Layout:

```
┌────────────────────────────────────────────────────────┐
│ Push Configuration                                      │
├────────────────────────────────────────────────────────┤
│                                                          │
│ Source Configuration:                                   │
│ ┌──────────────────────────────────────────────────┐  │
│ │ [Load from File ▼]  [Select Components...]       │  │
│ │                                                    │  │
│ │ Loaded: pulled_Production_20251223.json           │  │
│ │ Selected: 3 folders, 2 snippets, 45 objects       │  │
│ └──────────────────────────────────────────────────┘  │
│                                                          │
│ Destination Tenant:                                     │
│ ┌──────────────────────────────────────────────────┐  │
│ │ [Staging ▼]  [Connect to Different Tenant...]    │  │
│ │                                                    │  │
│ │ Status: ✓ Connected to Staging (TSG: xyz-456)    │  │
│ └──────────────────────────────────────────────────┘  │
│                                                          │
│ Push Options:                                           │
│ ┌──────────────────────────────────────────────────┐  │
│ │ □ Dry run (validate without pushing)              │  │
│ │ □ Skip existing (don't overwrite)                 │  │
│ │ □ Force overwrite (replace existing)              │  │
│ │ □ Check dependencies (warn if missing)            │  │
│ └──────────────────────────────────────────────────┘  │
│                                                          │
│ ┌──────────────────────────────────────────────────┐  │
│ │ [Preview Push...]  [Start Push]                   │  │
│ └──────────────────────────────────────────────────┘  │
│                                                          │
│ Push Log:                                               │
│ ┌──────────────────────────────────────────────────┐  │
│ │ Ready to push configuration...                    │  │
│ │                                                    │  │
│ └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

---

## 🔧 Implementation Steps

### Step 1: Load Configuration in Push Widget
**Goal:** Allow loading saved configs into push widget

**Tasks:**
- [ ] Add "Load from File" dropdown to push widget
- [ ] Populate with saved configs from saved_configs_manager
- [ ] Load selected config into memory
- [ ] Display loaded config info (name, date, source)
- [ ] Enable "Select Components" button when loaded

**Files to Modify:**
- `gui/push_widget.py`
- `gui/saved_configs_manager.py`

**Estimated Time:** 2-3 hours

---

### Step 2: Component Selection Dialog
**Goal:** Let users select what to push

**Tasks:**
- [ ] Create `ConfigSelectionDialog` class
- [ ] Show tree view of loaded config (similar to folder selection)
- [ ] Allow selection of:
  - Folders (with rules, objects, profiles)
  - Snippets
  - Individual objects/profiles
  - Infrastructure components
- [ ] Show selection summary (X folders, Y snippets, Z objects)
- [ ] Return selected items as structured data

**Files to Create:**
- `gui/dialogs/config_selection_dialog.py`

**Estimated Time:** 4-5 hours

---

### Step 3: Push Preview Dialog
**Goal:** Show what will be pushed before pushing

**Tasks:**
- [ ] Create `PushPreviewDialog` class
- [ ] Display selected items in tree view
- [ ] Show counts (folders, snippets, objects, etc.)
- [ ] Highlight potential conflicts (if exists in destination)
- [ ] Show missing dependencies (if any)
- [ ] Allow final confirmation

**Files to Create:**
- `gui/dialogs/push_preview_dialog.py`

**Estimated Time:** 3-4 hours

---

### Step 4: Selective Push Orchestrator
**Goal:** Push only selected items

**Tasks:**
- [ ] Create `SelectivePushOrchestrator` class
- [ ] Accept selected items as input
- [ ] Push folders (with selected components)
- [ ] Push snippets
- [ ] Push individual objects/profiles
- [ ] Handle errors gracefully
- [ ] Return push results

**Files to Create:**
- `prisma/push/selective_push_orchestrator.py`

**Estimated Time:** 5-6 hours

---

### Step 5: Push Validation
**Goal:** Validate before pushing

**Tasks:**
- [ ] Create `PushValidator` class
- [ ] Check if items already exist in destination
- [ ] Check for naming conflicts
- [ ] Validate object references
- [ ] Check for missing dependencies
- [ ] Return validation report

**Files to Create:**
- `prisma/push/push_validator.py`

**Estimated Time:** 4-5 hours

---

### Step 6: Push Progress Tracking
**Goal:** Show progress during push

**Tasks:**
- [ ] Create `PushProgressDialog` class
- [ ] Show progress bar
- [ ] Display current operation
- [ ] Show success/error counts
- [ ] Allow cancellation
- [ ] Show final summary

**Files to Create:**
- `gui/dialogs/push_progress_dialog.py`

**Estimated Time:** 3-4 hours

---

### Step 7: Integration & Testing
**Goal:** Wire everything together

**Tasks:**
- [ ] Integrate all components into push widget
- [ ] Add error handling
- [ ] Add logging
- [ ] Test with various selections
- [ ] Test with different destination tenants
- [ ] Test error scenarios

**Estimated Time:** 4-5 hours

---

## 📊 Data Structures

### Selected Items Format:

```python
selected_items = {
    "folders": [
        {
            "name": "Mobile Users",
            "components": {
                "rules": True,      # All rules
                "objects": True,    # All objects
                "profiles": True    # All profiles
            }
        }
    ],
    "snippets": [
        {
            "id": "abc-123",
            "name": "custom-snippet-1"
        }
    ],
    "objects": {
        "addresses": ["addr-1", "addr-2"],
        "address_groups": ["group-1"],
        "services": []
    },
    "profiles": {
        "security_profiles": ["profile-1"],
        "decryption_profiles": []
    },
    "infrastructure": {
        "remote_networks": ["rn-1", "rn-2"],
        "service_connections": []
    }
}
```

### Push Result Format:

```python
push_result = {
    "success": True,
    "summary": {
        "folders_pushed": 3,
        "snippets_pushed": 2,
        "objects_pushed": 45,
        "profiles_pushed": 12,
        "errors": 0
    },
    "details": [
        {"type": "folder", "name": "Mobile Users", "status": "success"},
        {"type": "snippet", "name": "custom-snippet-1", "status": "success"},
        {"type": "address", "name": "addr-1", "status": "error", "message": "Already exists"}
    ]
}
```

---

## 🎯 Success Criteria

### Must Have:
- [ ] Load saved config in push widget
- [ ] Select specific folders/snippets to push
- [ ] Preview selection before push
- [ ] Push only selected items
- [ ] Show push progress
- [ ] Display push results

### Nice to Have:
- [ ] Dependency resolution
- [ ] Conflict detection
- [ ] Dry-run mode
- [ ] Skip existing option
- [ ] Force overwrite option

---

## 🚧 Potential Challenges

### 1. **Dependency Resolution**
- **Challenge:** Objects reference other objects (address groups → addresses)
- **Solution:** Build dependency graph, auto-include dependencies or warn user

### 2. **Conflict Detection**
- **Challenge:** Items may already exist in destination
- **Solution:** Check before push, offer skip/overwrite options

### 3. **Partial Push Failures**
- **Challenge:** Some items push successfully, others fail
- **Solution:** Track each item individually, show detailed results

### 4. **API Rate Limits**
- **Challenge:** Pushing many items may hit rate limits
- **Solution:** Add delays between pushes, retry on 429 errors

### 5. **Large Selections**
- **Challenge:** Pushing 100+ items takes time
- **Solution:** Show progress, allow cancellation, batch where possible

---

## 📝 Testing Plan

### Unit Tests:
- [ ] Test config loading
- [ ] Test selection parsing
- [ ] Test push orchestrator
- [ ] Test validation logic

### Integration Tests:
- [ ] Test full push workflow
- [ ] Test with various selections
- [ ] Test error handling
- [ ] Test cancellation

### Manual Tests:
- [ ] Load config and select items
- [ ] Preview selection
- [ ] Push to test tenant
- [ ] Verify items in destination
- [ ] Test with conflicts
- [ ] Test with missing dependencies

---

## 📅 Timeline

### Week 1 (Steps 1-3):
- Load config in push widget
- Component selection dialog
- Push preview dialog

### Week 2 (Steps 4-5):
- Selective push orchestrator
- Push validation

### Week 3 (Steps 6-7):
- Push progress tracking
- Integration & testing

**Total Estimated Time:** 25-34 hours

---

## 🔄 Workflow Example

### User Story:
*"As a user, I want to push only the Mobile Users folder and 2 custom snippets from Production to Staging."*

**Steps:**
1. User goes to Push tab
2. User selects "Load from File" → "pulled_Production_20251223.json"
3. User clicks "Select Components"
4. Selection dialog opens showing all folders/snippets
5. User checks "Mobile Users" folder
6. User checks 2 custom snippets
7. User clicks "OK"
8. Push widget shows "Selected: 1 folder, 2 snippets, 35 objects"
9. User selects destination tenant: "Staging"
10. User clicks "Preview Push"
11. Preview dialog shows what will be pushed
12. User clicks "Confirm"
13. Push progress dialog appears
14. Items are pushed one by one
15. Success toast appears: "✓ Pushed 1 folder, 2 snippets, 35 objects"
16. Push log shows detailed results

---

## 🎨 UI Mockups

### Selection Dialog:
```
┌─────────────────────────────────────────────────────┐
│ Select Components to Push                           │
├─────────────────────────────────────────────────────┤
│                                                       │
│ ☑ Folders                                           │
│   ☑ Mobile Users                                    │
│     ☑ Rules (12)                                    │
│     ☑ Objects (35)                                  │
│     ☑ Profiles (8)                                  │
│   ☐ Remote Networks                                 │
│                                                       │
│ ☑ Snippets                                          │
│   ☑ custom-snippet-1 (Custom)                       │
│   ☑ custom-snippet-2 (Custom)                       │
│   ☐ predefined-snippet-1 (Predefined)              │
│                                                       │
│ ☐ Infrastructure                                    │
│   ☐ Remote Networks (5)                             │
│   ☐ Service Connections (2)                         │
│                                                       │
│ Selected: 1 folder, 2 snippets, 55 total items     │
│                                                       │
│ [Cancel]  [Select All]  [Clear All]  [OK]          │
└─────────────────────────────────────────────────────┘
```

### Preview Dialog:
```
┌─────────────────────────────────────────────────────┐
│ Push Preview                                         │
├─────────────────────────────────────────────────────┤
│                                                       │
│ The following items will be pushed to Staging:      │
│                                                       │
│ Folders (1):                                         │
│   • Mobile Users (12 rules, 35 objects, 8 profiles) │
│                                                       │
│ Snippets (2):                                        │
│   • custom-snippet-1                                 │
│   • custom-snippet-2                                 │
│                                                       │
│ ⚠ Warnings:                                          │
│   • Address "addr-1" already exists (will skip)     │
│   • Snippet "custom-snippet-1" already exists       │
│                                                       │
│ ℹ Dependencies:                                      │
│   • Address group "group-1" requires "addr-2"       │
│     (will be included automatically)                 │
│                                                       │
│ Total: 57 items (55 selected + 2 dependencies)      │
│                                                       │
│ [Cancel]  [Back]  [Push]                            │
└─────────────────────────────────────────────────────┘
```

---

## 🚀 Phase 3 Kickoff

**Status:** Ready to begin implementation  
**First Step:** Implement config loading in push widget  
**Next Review:** After Step 1 completion  

Let's start with Step 1! 🎯
