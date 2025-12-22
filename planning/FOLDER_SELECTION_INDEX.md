# Folder/Snippet Selection Enhancement - Document Index

**Date:** December 22, 2025  
**Status:** ✅ Planning Complete  
**Branch:** feature/comprehensive-config-capture

---

## Quick Navigation

### 📋 Planning Documents

| Document | Purpose | Size | Status |
|----------|---------|------|--------|
| [FOLDER_SNIPPET_SELECTION_PLAN.md](./FOLDER_SNIPPET_SELECTION_PLAN.md) | Main implementation plan | 1,500 lines | ✅ Complete |
| [COMPREHENSIVE_TESTING_UPDATE.md](./COMPREHENSIVE_TESTING_UPDATE.md) | Testing plan with 36+ test cases | 800 lines | ✅ Complete |
| [FOLDER_SELECTION_SUMMARY.md](./FOLDER_SELECTION_SUMMARY.md) | Executive summary | 400 lines | ✅ Complete |
| [FOLDER_SELECTION_INDEX.md](./FOLDER_SELECTION_INDEX.md) | This document | - | ✅ Complete |

**Total Planning:** ~2,700 lines of comprehensive documentation

---

## Feature Overview

### What's Being Built

A sophisticated folder and snippet selection system for Prisma Access configuration import that:

1. **Discovers Available Configuration**
   - Queries tenant for all folders and snippets
   - Filters out non-Prisma Access folders ("all", "ngfw")
   - Displays available options in tree view

2. **Enables Granular Selection**
   - Select specific folders (e.g., "Mobile Users", "Remote Networks")
   - Select specific components per folder (objects, profiles, rules)
   - Select specific snippets

3. **Automates Dependencies** (Future)
   - Detect cross-folder dependencies
   - Auto-select required objects and profiles
   - Prevent incomplete configurations

### User Benefits

- ✅ **Faster Migrations** - Pull only what you need
- ✅ **Cleaner Configs** - No unwanted NGFW or global configs
- ✅ **Better Control** - Choose exactly which components to import
- ✅ **Prisma Access Focus** - Automatically filters non-PA folders

---

## Implementation Plan Summary

### Timeline: 10-14 Days

```
Week 1: Core Functionality (Days 1-4)
├── Folder filtering logic
├── Snippet discovery enhancement
└── Discovery worker thread

Week 2: GUI Development (Days 5-8)
├── Folder selection dialog
└── Pull widget integration

Week 3: Backend & Testing (Days 9-14)
├── Pull orchestrator updates
├── Comprehensive testing
└── Documentation
```

### Key Components

```
Codebase Changes:
├── prisma/pull/
│   ├── folder_capture.py (+100 lines)
│   └── snippet_capture.py (+50 lines)
│
├── gui/
│   ├── dialogs/folder_selection_dialog.py (+600 lines, NEW)
│   ├── workers.py (+80 lines)
│   └── pull_widget.py (+160 lines)
│
└── tests/
    ├── test_folder_selection.py (+990 lines, NEW)
    ├── test_folder_capture.py (+150 lines)
    ├── test_integration_phase1.py (+120 lines)
    └── test_gui_infrastructure.py (+180 lines)
```

---

## Folder Filtering Logic

### Folders to EXCLUDE

```python
MIGRATION_EXCLUDED_FOLDERS = {
    # Non-Prisma Access
    "all",    # Global/shared - not PA-specific
    "ngfw",   # NGFW-specific - not Prisma Access
    
    # Infrastructure-only
    "Service Connections",
    "Colo Connect",
}
```

### Why Filter These?

| Folder | Type | Reason |
|--------|------|--------|
| **all** | Global | Contains predefined/default configs not specific to Prisma Access service |
| **ngfw** | NGFW | Next-Gen Firewall specific configs, not part of Prisma Access |
| **Service Connections** | Infrastructure | Infrastructure-only, cannot have security policies |
| **Colo Connect** | Infrastructure | Infrastructure-only, cannot have security policies |

### Folders to KEEP

- ✅ **Shared** - Shared Prisma Access objects
- ✅ **Mobile Users** - Mobile user configurations
- ✅ **Remote Networks** - Remote network configurations
- ✅ **Custom folders** - User-created PA folders

---

## Testing Plan Summary

### New Tests: 36+

| Category | Tests | Coverage |
|----------|-------|----------|
| Folder Filtering | 5 | 100% |
| Dialog UI | 12 | 95% |
| Discovery Worker | 2 | 100% |
| Component Selection | 4 | 100% |
| Snippet Selection | 3 | 100% |
| Integration | 4 | 90% |
| GUI Integration | 6 | 95% |
| **Total** | **36** | **96%** |

### Test Execution

```bash
# Quick unit tests (2-3 min)
pytest tests/test_folder_selection.py -v

# GUI tests (3-5 min)
pytest tests/test_folder_selection.py::TestFolderSelectionDialog -v

# Integration tests (5-10 min, requires live tenant)
pytest tests/test_integration_phase1.py::TestFolderSelectionIntegration -v --integration

# Full regression (15-20 min)
pytest tests/ -v --cov=prisma --cov=gui --cov=config
```

---

## GUI Design Preview

### Folder Selection Dialog

```
┌─────────────────────────────────────────────────────────┐
│ Select Folders and Snippets for Configuration Import     │
├─────────────────────────────────────────────────────────┤
│                                                           │
│ [🔍 Grab Folder & Snippet List]                         │
│                                                           │
│ ┌─ Discovered Folders ─────────────────────────────┐    │
│ │ Search: [_______________]  [🔍]                  │    │
│ │                                                   │    │
│ │ ☐ Select All                                     │    │
│ │                                                   │    │
│ │ ☐ Shared (default folder)                        │    │
│ │   ☐ Objects                                      │    │
│ │   ☐ Profiles                                     │    │
│ │   ☐ Rules                                        │    │
│ │                                                   │    │
│ │ ☐ Mobile Users                                   │    │
│ │   ☐ Objects                                      │    │
│ │   ☐ Profiles                                     │    │
│ │   ☐ Rules                                        │    │
│ │                                                   │    │
│ │ Filtered out: all, ngfw, Service Connections     │    │
│ └───────────────────────────────────────────────────┘    │
│                                                           │
│ ┌─ Snippets ────────────────────────────────────────┐    │
│ │ ☐ snippet-mobile-users                            │    │
│ │   Folders: Mobile Users                           │    │
│ └───────────────────────────────────────────────────┘    │
│                                                           │
│ Selected: 2 folders, 6 sections, 1 snippet               │
│                                                           │
│              [Discover List]  [Cancel]  [OK]              │
└─────────────────────────────────────────────────────────┘
```

### Pull Widget Integration

```
┌─────────────────────────────────────────────────────────┐
│ Pull Configuration                                        │
├─────────────────────────────────────────────────────────┤
│                                                           │
│         [📁 Select Folders & Snippets...]                │
│         Selected: 2 folders, 1 snippet                    │
│                                                           │
│ ┌─ Configuration Components ───────────────────────┐     │
│ │ ☑ Security Policy Folders                        │     │
│ │ ☑ Configuration Snippets                         │     │
│ │ ☑ Security Rules                                 │     │
│ │ ... (other options)                              │     │
│ └──────────────────────────────────────────────────┘     │
│                                                           │
│              [Select All]  [Pull Configuration]           │
└─────────────────────────────────────────────────────────┘
```

---

## Code Examples

### Folder Filtering

```python
from prisma.pull.folder_capture import FolderCapture, filter_folders_for_migration

# Discover all folders
capture = FolderCapture(api_client)
all_folders = capture.discover_folders()

# Filter for Prisma Access migration
pa_folders = filter_folders_for_migration(all_folders)

# pa_folders will NOT include: all, ngfw, Service Connections, Colo Connect
# pa_folders WILL include: Shared, Mobile Users, Remote Networks, custom folders
```

### Using the Selection Dialog

```python
from gui.dialogs.folder_selection_dialog import FolderSelectionDialog

# Open dialog
dialog = FolderSelectionDialog(api_client, parent=self)
if dialog.exec():
    # Get selections
    folders = dialog.get_selected_folders()
    components = dialog.get_selected_components()
    snippets = dialog.get_selected_snippets()
    
    # Example results:
    # folders = ["Mobile Users", "Remote Networks"]
    # components = {
    #     "Mobile Users": ["objects", "rules"],
    #     "Remote Networks": ["objects", "profiles"]
    # }
    # snippets = ["snippet-mobile-users"]
```

### Pulling with Selections

```python
from prisma.pull.pull_orchestrator import PullOrchestrator

orchestrator = PullOrchestrator(api_client)

# Pull only selected folders/components
config = orchestrator.pull_complete_configuration(
    folder_names=["Mobile Users", "Remote Networks"],
    selected_components={
        "Mobile Users": ["objects", "rules"],
        "Remote Networks": ["objects", "profiles"]
    },
    snippet_names=["snippet-mobile-users"],
    include_snippets=True,
)

# Result: Only specified folders, components, and snippets are pulled
```

---

## API Endpoints Used

### Folder Discovery
```
GET /config/setup/v1/security-policy/folders

Response:
[
    {
        "id": "folder-id",
        "name": "Mobile Users",
        "path": "/config/security-policy/folders/Mobile Users",
        "description": "...",
        ...
    },
    ...
]
```

### Snippet Discovery
```
GET /config/setup/v1/snippets

Response:
[
    {
        "id": "snippet-id",
        "name": "snippet-mobile-users",
        "folders": [
            {"id": "folder-id", "name": "Mobile Users"}
        ],
        ...
    },
    ...
]
```

---

## Success Criteria

### Must Have (MVP)
- [x] Planning complete
- [ ] Folder filtering works (excludes all, ngfw)
- [ ] Discovery button in GUI
- [ ] Folder selection dialog functional
- [ ] Component selection per folder
- [ ] Snippet selection
- [ ] Pull respects selections
- [ ] 36+ tests passing
- [ ] Documentation complete

### Nice to Have (Post-MVP)
- [ ] Auto-dependency resolution
- [ ] Folder hierarchy visualization
- [ ] Smart recommendations
- [ ] Save/load selection profiles

---

## Documentation References

### Planning Documents
1. **Main Plan** - [FOLDER_SNIPPET_SELECTION_PLAN.md](./FOLDER_SNIPPET_SELECTION_PLAN.md)
   - Complete implementation details
   - API integration
   - GUI design with mockups
   - Timeline and phases

2. **Testing Plan** - [COMPREHENSIVE_TESTING_UPDATE.md](./COMPREHENSIVE_TESTING_UPDATE.md)
   - 36 new test cases
   - Test fixtures
   - CI/CD integration
   - Quality gates

3. **Summary** - [FOLDER_SELECTION_SUMMARY.md](./FOLDER_SELECTION_SUMMARY.md)
   - Executive overview
   - Key decisions
   - Implementation breakdown
   - Risk assessment

### Existing Documentation (to be updated)
- `docs/GUI_USER_GUIDE.md` - Add folder selection workflow
- `docs/PULL_PUSH_GUIDE.md` - Document folder selection API
- `docs/API_REFERENCE.md` - Update with new methods
- `README.md` - Add feature to feature list

---

## Quick Start for Developers

### 1. Read the Planning Documents
```bash
# Main implementation plan
cat planning/FOLDER_SNIPPET_SELECTION_PLAN.md

# Testing plan
cat planning/COMPREHENSIVE_TESTING_UPDATE.md

# Summary
cat planning/FOLDER_SELECTION_SUMMARY.md
```

### 2. Review Current Code
```bash
# Existing folder capture
cat prisma/pull/folder_capture.py

# Existing snippet capture
cat prisma/pull/snippet_capture.py

# Existing pull widget
cat gui/pull_widget.py
```

### 3. Start Implementation (Recommended Order)
1. Phase 1: Folder filtering (`folder_capture.py`)
2. Phase 2: Snippet discovery (`snippet_capture.py`)
3. Phase 3: Discovery worker (`gui/workers.py`)
4. Phase 4: Selection dialog (`gui/dialogs/folder_selection_dialog.py`)
5. Phase 5: Pull widget integration (`gui/pull_widget.py`)
6. Phase 6: Orchestrator updates (`prisma/pull/pull_orchestrator.py`)
7. Phase 7: Testing
8. Phase 8: Documentation

### 4. Run Tests After Each Phase
```bash
# After each phase, run relevant tests
pytest tests/test_folder_selection.py::TestFolderFiltering -v
pytest tests/test_folder_selection.py::TestFolderSelectionDialog -v
# ... etc
```

---

## Project Stats

### Planning Effort
- **Documents:** 4 (plan, testing, summary, index)
- **Total Lines:** ~2,700
- **Time Investment:** ~8 hours of comprehensive planning
- **Coverage:** Architecture, GUI, backend, testing, documentation

### Implementation Estimate
- **New Code:** ~1,380 lines
- **Modified Code:** ~250 lines
- **Test Code:** ~990 lines
- **Documentation:** ~500 lines
- **Total Effort:** ~3,120 lines

### Test Coverage
- **New Tests:** 36
- **Updated Tests:** 14
- **Total Tests (project):** 159 (from 123)
- **Coverage Target:** 85%+

---

## Contact and Questions

For questions about this feature or the planning documents:

1. Review the detailed planning documents (links above)
2. Check the code examples in this index
3. Review existing similar implementations in the codebase
4. Refer to the comprehensive testing plan for expected behavior

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2025-12-22 | 1.0 | Initial planning documents created |
| 2025-12-22 | 1.0 | Index document created |

---

## Status Dashboard

### Planning Phase ✅
- [x] Requirements analysis
- [x] Architecture design
- [x] GUI mockups
- [x] API integration design
- [x] Testing plan
- [x] Documentation plan

### Implementation Phase ⚪ (Not Started)
- [ ] Folder filtering
- [ ] Snippet discovery
- [ ] Discovery worker
- [ ] Selection dialog
- [ ] Pull widget integration
- [ ] Orchestrator updates
- [ ] Testing
- [ ] Documentation

### Ready to Begin ✅
**Status:** All planning complete  
**Next Step:** Begin Phase 1 (Folder filtering)  
**Blocker:** None  

---

**Document Index Version:** 1.0  
**Last Updated:** December 22, 2025  
**Maintained By:** Development Team  

---

**End of Index**
