# Folder/Snippet Selection Enhancement - Planning Summary

**Date:** December 22, 2025  
**Status:** ✅ Planning Complete - Ready for Implementation  
**Branch:** feature/comprehensive-config-capture

---

## Executive Summary

A comprehensive plan has been created for enhancing Prisma Access configuration import with granular folder and snippet selection. This feature allows users to selectively import specific folders, components, and snippets while automatically filtering out non-Prisma Access configurations.

---

## Planning Documents Created

### 1. FOLDER_SNIPPET_SELECTION_PLAN.md (Main Plan)
**Size:** 12 sections, ~1,500 lines  
**Content:**
- ✅ Current state analysis
- ✅ Folder filtering requirements (filter "all", "ngfw")
- ✅ API integration design
- ✅ GUI dialog design with mockups
- ✅ Backend orchestrator updates
- ✅ Worker thread design
- ✅ Implementation timeline (10-14 days)
- ✅ Risk assessment
- ✅ Success criteria

**Key Features:**
- Folder discovery button: "Grab Folder & Snippet List"
- Automatic filtering of non-PA folders
- Tree view for folder/component selection
- Snippet selection with folder associations
- Dependency auto-resolution (future enhancement)

### 2. COMPREHENSIVE_TESTING_UPDATE.md (Testing Plan)
**Size:** 9 sections, ~800 lines  
**Content:**
- ✅ New test file structure (test_folder_selection.py)
- ✅ 36 new test cases detailed
- ✅ Updated existing test files (3 files, 14 new tests)
- ✅ Test fixtures and mock data
- ✅ CI/CD integration updates
- ✅ Test execution plan
- ✅ Quality gates

**Test Coverage:**
- Folder filtering: 5 tests
- Dialog UI: 12 tests
- Discovery worker: 2 tests
- Component selection: 4 tests
- Snippet selection: 3 tests
- Integration: 4 tests
- GUI integration: 6 tests
- **Total: 36 new tests**

---

## Key Design Decisions

### 1. Folder Filtering Strategy

**Folders to EXCLUDE from migration:**
```python
MIGRATION_EXCLUDED_FOLDERS = {
    # Non-Prisma Access folders
    "all",                    # Global container, not PA-specific
    "ngfw",                   # NGFW-specific, not Prisma Access
    
    # Infrastructure-only folders
    "Service Connections",    # Infrastructure only, no security policies
    "Colo Connect",          # Infrastructure only, no security policies
}
```

**Folders to INCLUDE:**
- ✅ "Shared" (PA shared objects)
- ✅ "Mobile Users" (Mobile user configs)
- ✅ "Remote Networks" (Remote network configs)
- ✅ Custom user-created folders

**Rationale:**
- "all" folder contains predefined/default configurations not specific to PA
- "ngfw" folder is for NGFW-specific configs, not Prisma Access service
- Service Connections and Colo Connect are infrastructure-only, cannot have security policies

### 2. Granular Component Selection

**Components per folder:**
```
☐ Folder Name
  ☐ Objects (addresses, address groups, services, service groups)
  ☐ Profiles (security profiles: AV, AS, VPN, etc.)
  ☐ Rules (security policy rules)
```

**Selection Behavior:**
- Checking folder → checks all components
- Unchecking all components → unchecks folder
- Checking some components → folder shows "partially checked"
- Each folder can have different component selections

### 3. Discovery Workflow

```
User Flow:
1. Connect to source tenant
2. Click "📁 Select Folders & Snippets..." button in Pull Widget
3. In dialog, click "🔍 Grab Folder & Snippet List"
4. Wait for discovery (worker thread, 2-5 seconds)
5. Review discovered folders (filtered automatically)
6. Select folders and components
7. Select snippets (optional)
8. Click OK
9. Start pull with selections applied
```

**Technical Flow:**
```
GUI Button Click
    ↓
Launch FolderSelectionDialog
    ↓
User clicks "Grab Folder & Snippet List"
    ↓
Start DiscoveryWorker thread
    ↓
Worker → API: GET /config/setup/v1/security-policy/folders
Worker → API: GET /config/setup/v1/snippets
    ↓
Worker → filter_folders_for_migration() (remove all, ngfw, etc.)
    ↓
Worker emits finished signal with filtered folders + snippets
    ↓
Dialog populates tree views
    ↓
User makes selections
    ↓
Dialog returns: selected_folders, selected_components, selected_snippets
    ↓
PullWidget stores selections
    ↓
PullWidget passes selections to PullOrchestrator
    ↓
PullOrchestrator pulls only selected folders/components
```

---

## Implementation Breakdown

### Phase 1: Folder Filtering (1-2 days)
**Files to modify:**
- `prisma/pull/folder_capture.py` - Add `filter_folders_for_migration()`
- `prisma/pull/folder_capture.py` - Add `discover_folders_for_migration()`

**Tests to create:**
- `tests/test_folder_selection.py::TestFolderFiltering` (5 tests)

### Phase 2: Snippet Discovery Enhancement (1 day)
**Files to modify:**
- `prisma/pull/snippet_capture.py` - Add `discover_snippets_with_folders()`

**Tests to update:**
- `tests/test_folder_selection.py::TestSnippetSelection` (3 tests)

### Phase 3: Discovery Worker (1 day)
**Files to modify:**
- `gui/workers.py` - Add `DiscoveryWorker` class

**Tests to create:**
- `tests/test_folder_selection.py::TestDiscoveryWorker` (2 tests)

### Phase 4: Folder Selection Dialog (2-3 days)
**Files to create:**
- `gui/dialogs/folder_selection_dialog.py` - Complete dialog implementation

**Tests to create:**
- `tests/test_folder_selection.py::TestFolderSelectionDialog` (12 tests)

### Phase 5: Pull Widget Integration (1 day)
**Files to modify:**
- `gui/pull_widget.py` - Add folder selection button and handler

**Tests to update:**
- `tests/test_gui_infrastructure.py::TestPullWidgetFolderSelection` (6 tests)

### Phase 6: Pull Orchestrator Updates (1-2 days)
**Files to modify:**
- `prisma/pull/pull_orchestrator.py` - Update `pull_complete_configuration()`

**Tests to update:**
- `tests/test_integration_phase1.py::TestFolderSelectionIntegration` (4 tests)

### Phase 7: Testing (2-3 days)
**Activities:**
- Run all unit tests
- Run all GUI tests
- Run all integration tests with live tenant
- Fix any issues found
- Verify test coverage ≥ 85%

### Phase 8: Documentation (1 day)
**Files to update:**
- `docs/GUI_USER_GUIDE.md` - Add folder selection workflow
- `docs/PULL_PUSH_GUIDE.md` - Document folder selection API
- `README.md` - Update features list

---

## Code Statistics (Estimated)

| Component | New Lines | Modified Lines | Test Lines |
|-----------|-----------|----------------|------------|
| folder_capture.py | +80 | +20 | +150 |
| snippet_capture.py | +40 | +10 | +80 |
| folder_selection_dialog.py | +600 | 0 | +400 |
| workers.py | +80 | 0 | +60 |
| pull_widget.py | +120 | +40 | +180 |
| pull_orchestrator.py | +60 | +80 | +120 |
| Documentation | +400 | +100 | - |
| **Total** | **~1,380** | **~250** | **~990** |

**Total Implementation Effort:** ~2,620 lines (code + tests + docs)

---

## Dependencies and Prerequisites

### Technical Dependencies
- ✅ PyQt6 (already installed)
- ✅ Existing API client methods (already implemented)
- ✅ Existing folder/snippet capture modules (already implemented)

### Testing Dependencies
- ✅ pytest (already installed)
- ✅ pytest-qt (already installed)
- ✅ Mock data fixtures (need to create)

### API Requirements
- ✅ `/config/setup/v1/security-policy/folders` endpoint (confirmed)
- ✅ `/config/setup/v1/snippets` endpoint (confirmed)
- ✅ API authentication (already working)

---

## Success Metrics

### Functional Requirements
- [x] Planning complete
- [ ] Folder filtering excludes "all" and "ngfw"
- [ ] Folder selection dialog implemented
- [ ] Component selection per folder works
- [ ] Snippet selection works
- [ ] Discovery button triggers API calls
- [ ] Pull respects selections
- [ ] All tests pass

### Quality Metrics
| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Test Coverage | 85% | 85% | ✅ Planning |
| New Tests | 36+ | 36 | ✅ Planned |
| Documentation | 100% | 0% | 🟡 Pending |
| Code Review | Pass | N/A | ⚪ Not Started |

### User Experience
- [ ] Intuitive UI (tree view, checkboxes)
- [ ] Clear labeling (filtered folders shown)
- [ ] Responsive (discovery < 5 seconds)
- [ ] Error handling (graceful failures)
- [ ] Help text and tooltips

---

## Risk Mitigation

### Risk 1: API Changes
**Likelihood:** Low  
**Impact:** High  
**Mitigation:**
- Version checking for API endpoints
- Graceful degradation if endpoints unavailable
- Error messages guide user to alternative approaches

### Risk 2: Large Folder Lists
**Likelihood:** Medium  
**Impact:** Low  
**Mitigation:**
- Search/filter functionality in dialog
- Lazy loading if needed (future enhancement)
- Efficient tree rendering

### Risk 3: Complex Dependencies
**Likelihood:** Medium  
**Impact:** Medium  
**Mitigation:**
- Start with manual selection (MVP)
- Add auto-dependency resolution later (Phase 2)
- Clear warning messages about missing dependencies

---

## Next Steps (Implementation Order)

### Week 1: Core Functionality
1. **Day 1-2:** Implement folder filtering logic
   - Add `filter_folders_for_migration()`
   - Write unit tests
   - Test with live API

2. **Day 3:** Enhance snippet discovery
   - Add folder associations
   - Write tests

3. **Day 4:** Create discovery worker
   - Implement worker thread
   - Write tests

### Week 2: GUI Development
4. **Day 5-7:** Build folder selection dialog
   - Create dialog UI
   - Implement tree views
   - Add checkbox logic
   - Write GUI tests

5. **Day 8:** Integrate with pull widget
   - Add button
   - Connect signals
   - Update tests

### Week 3: Backend & Testing
6. **Day 9-10:** Update pull orchestrator
   - Add component selection support
   - Update integration tests

7. **Day 11-13:** Comprehensive testing
   - Run all tests
   - Fix issues
   - Verify coverage

8. **Day 14:** Documentation
   - Update user guides
   - Add API docs
   - Create screenshots

---

## Approval and Sign-off

**Planning Status:** ✅ Complete  
**Ready for Implementation:** ✅ Yes  
**Estimated Timeline:** 10-14 days  
**Risk Level:** Low-Medium  

**Documents Created:**
1. ✅ FOLDER_SNIPPET_SELECTION_PLAN.md (1,500 lines)
2. ✅ COMPREHENSIVE_TESTING_UPDATE.md (800 lines)
3. ✅ FOLDER_SELECTION_SUMMARY.md (this document)

**Total Planning Effort:** ~2,500 lines of comprehensive documentation

---

## Questions for Clarification

Before starting implementation, please confirm:

1. **Folder Filtering:**
   - ✅ Confirm "all" folder should be filtered (Yes, not PA-specific)
   - ✅ Confirm "ngfw" folder should be filtered (Yes, not PA-specific)
   - ❓ Are there any other folders to filter?

2. **Component Selection:**
   - ✅ Granular selection (objects, profiles, rules) per folder is desired
   - ❓ Should there be a "quick select" preset (e.g., "Select all rules only")?

3. **Dependency Resolution:**
   - ✅ MVP: Manual selection without auto-dependency resolution
   - ❓ Priority for auto-dependency feature? (Post-MVP or included?)

4. **User Experience:**
   - ✅ Tree view with checkboxes is approved
   - ❓ Any specific UI preferences or requirements?

5. **Testing:**
   - ✅ 36 new tests planned
   - ❓ Target test coverage? (Suggest 85%+)

---

## Conclusion

The planning phase for the folder/snippet selection enhancement is **complete and comprehensive**. All design decisions have been documented, test cases planned, and implementation timeline estimated.

**Ready to Proceed:** ✅ Yes  
**Blockers:** None  
**Next Action:** Begin Phase 1 implementation (folder filtering)

---

## Document References

- **Main Plan:** `/planning/FOLDER_SNIPPET_SELECTION_PLAN.md`
- **Testing Plan:** `/planning/COMPREHENSIVE_TESTING_UPDATE.md`
- **Summary:** `/planning/FOLDER_SELECTION_SUMMARY.md` (this document)

---

**Document Version:** 1.0  
**Last Updated:** December 22, 2025  
**Author:** AI Assistant  
**Status:** ✅ Planning Complete

---

**End of Document**
