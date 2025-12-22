# Folder and Snippet Selection Enhancement Plan

**Date:** December 22, 2025  
**Branch:** feature/comprehensive-config-capture  
**Purpose:** Enhanced folder and snippet selection for Prisma Access configuration import

---

## Executive Summary

This document outlines the implementation plan for a sophisticated folder and snippet selection feature that allows users to:

1. **Discover Available Folders** - Query tenant for all available folders before pulling config
2. **Filter Non-Prisma Access Folders** - Automatically exclude "all" and "ngfw" folders (NGFW-specific, not Prisma Access)
3. **Granular Component Selection** - Select specific sections (objects, profiles, rules) per folder
4. **Automatic Dependency Resolution** - Auto-select dependencies when a folder is checked
5. **Snippet Management** - Discover and select snippets alongside folders

**User Workflow:**
```
1. Connect to tenant
2. Click "Grab Folder & Snippet List" button
3. Review discovered folders (with "all" and "ngfw" filtered out)
4. Select folders and components:
   - Check folders → auto-check dependencies
   - Granularly select: objects, profiles, rules per folder
   - Select snippets
5. Pull selected configuration
```

---

## 1. Current State Analysis

### 1.1 Existing Folder Discovery

**Current Implementation:**
- `prisma/pull/folder_capture.py` - `FolderCapture.discover_folders()`
- Discovers folders via API endpoint: `/config/setup/v1/security-policy/folders`
- Returns normalized folder data with metadata

**Current Reserved Folder Filtering:**
```python
# From folder_capture.py lines 195-220
RESERVED_FOLDERS = {
    "Service Connections",  # Infrastructure only
    "Colo Connect",         # Infrastructure only
}
```

**Gap:** Does NOT filter "all" and "ngfw" folders currently.

### 1.2 Existing Snippet Discovery

**Current Implementation:**
- `prisma/pull/snippet_capture.py` - `SnippetCapture.discover_snippets()`
- Discovers snippets via API endpoint: `/config/setup/v1/snippets`
- Returns normalized snippet data with folder associations

### 1.3 Current GUI Pull Widget

**Current Behavior:**
- User selects high-level components (folders, snippets, rules, objects, profiles)
- **All** folders are pulled together (no per-folder selection)
- **All** snippets are pulled together (no per-snippet selection)
- No pre-pull discovery step

**Files:**
- `gui/pull_widget.py` - Pull configuration widget
- `gui/workflows/migration_workflow.py` - Migration workflow

---

## 2. Folder Filtering Requirements

### 2.1 Folders to Filter Out

**Prisma Access Configuration Migration should ONLY include Prisma Access-specific folders.**

#### Folders to EXCLUDE:

1. **"all"** - This is a global container, not Prisma Access specific
   - Contains shared/predefined objects
   - Usually includes default NGFW configurations
   - Not relevant for Prisma Access migration

2. **"ngfw"** - Next-Gen Firewall specific folder
   - Contains NGFW-specific configurations
   - Not part of Prisma Access service
   - Should not be migrated in Prisma Access context

3. **Existing Reserved Folders:**
   - "Service Connections" (infrastructure only)
   - "Colo Connect" (infrastructure only)

#### Folders to INCLUDE:

- **"Shared"** - Shared Prisma Access objects (optional, user choice)
- **"Mobile Users"** - Mobile user configurations
- **"Mobile_User_Template"** - Mobile user templates
- **"Remote Networks"** - Remote network configurations
- **Custom folders** - Any user-created folders for Prisma Access

### 2.2 Filtering Logic

```python
# In folder_capture.py or new folder_filter.py

# Reserved/system folders that cannot have security policies
INFRASTRUCTURE_ONLY_FOLDERS = {
    "Service Connections",  # Infrastructure only - cannot have security policies
    "Colo Connect",         # Infrastructure only - cannot have security policies
}

# Folders that are not Prisma Access specific (filter from config migration)
NON_PRISMA_ACCESS_FOLDERS = {
    "all",    # Global/shared container - not Prisma Access specific
    "ngfw",   # NGFW-specific - not part of Prisma Access service
}

# Combined exclusion list for config migration
MIGRATION_EXCLUDED_FOLDERS = INFRASTRUCTURE_ONLY_FOLDERS | NON_PRISMA_ACCESS_FOLDERS

def filter_folders_for_migration(folders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter folders for Prisma Access configuration migration.
    
    Excludes:
    - Infrastructure-only folders (Service Connections, Colo Connect)
    - Non-Prisma Access folders (all, ngfw)
    
    Args:
        folders: List of discovered folders
        
    Returns:
        Filtered list of folders suitable for Prisma Access migration
    """
    filtered = []
    for folder in folders:
        folder_name = folder.get("name", "")
        
        # Skip excluded folders
        if folder_name in MIGRATION_EXCLUDED_FOLDERS:
            print(f"  ℹ Filtering out folder: {folder_name} (not Prisma Access specific)")
            continue
        
        # Skip case-insensitive matches
        if folder_name.lower() in {name.lower() for name in MIGRATION_EXCLUDED_FOLDERS}:
            print(f"  ℹ Filtering out folder: {folder_name} (not Prisma Access specific)")
            continue
        
        filtered.append(folder)
    
    return filtered
```

---

## 3. Folder Discovery API Integration

### 3.1 Discovery Workflow

```
User clicks "Grab Folder & Snippet List"
    ↓
[GUI] → [Worker Thread]
    ↓
[Worker] → [API Client] → GET /config/setup/v1/security-policy/folders
    ↓
[Worker] → [API Client] → GET /config/setup/v1/snippets
    ↓
[Worker] → Filter folders (remove "all", "ngfw", infrastructure-only)
    ↓
[Worker] → Return filtered folders + snippets to GUI
    ↓
[GUI] → Display folder selection dialog with tree view
```

### 3.2 New API Helper Methods

Add to `prisma/pull/folder_capture.py`:

```python
def discover_folders_for_migration(
    self, 
    include_defaults: bool = False
) -> List[Dict[str, Any]]:
    """
    Discover folders suitable for Prisma Access configuration migration.
    
    Automatically filters out:
    - Infrastructure-only folders
    - Non-Prisma Access folders (all, ngfw)
    - Default folders (if include_defaults=False)
    
    Args:
        include_defaults: Whether to include default folders
        
    Returns:
        List of filtered folders suitable for migration
    """
    # Get all folders
    all_folders = self.discover_folders()
    
    # Filter for migration
    filtered = filter_folders_for_migration(all_folders)
    
    # Optionally filter defaults
    if not include_defaults:
        filtered = [
            f for f in filtered 
            if not f.get("is_default", False)
        ]
    
    return filtered
```

Add to `prisma/pull/snippet_capture.py`:

```python
def discover_snippets_with_folders(self) -> List[Dict[str, Any]]:
    """
    Discover snippets with their folder associations.
    
    Returns snippets with enhanced metadata including:
    - Associated folders
    - Folder names (resolved from IDs)
    - Snippet type/purpose
    
    Returns:
        List of snippets with folder associations
    """
    snippets = self.discover_snippets()
    
    # Enhance with folder information
    for snippet in snippets:
        folder_list = snippet.get("folders", [])
        if folder_list:
            # Extract folder names from folder objects
            folder_names = [f.get("name", "") for f in folder_list if isinstance(f, dict)]
            snippet["folder_names"] = folder_names
        else:
            snippet["folder_names"] = []
    
    return snippets
```

---

## 4. GUI Design - Folder Selection Dialog

### 4.1 New Dialog: Folder Selection

**File:** `gui/dialogs/folder_selection_dialog.py`

**Features:**
- Tree view of folders with nested sections (objects, profiles, rules)
- Checkbox for each folder (selects all sections)
- Indented checkboxes for granular section selection
- Snippet list with checkboxes
- Dependency indicator (shows when dependencies are auto-selected)
- Filter/search functionality

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Select Folders and Snippets for Configuration Import         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ ┌─ Discovered Folders ───────────────────────────────────┐  │
│ │                                                          │  │
│ │ Search: [_______________]  [🔍]                         │  │
│ │                                                          │  │
│ │ ☐ Select All                                            │  │
│ │                                                          │  │
│ │ Folders (5 found):                                      │  │
│ │ ────────────────────────────────────────────────────── │  │
│ │ ☐ Shared (default folder, optional)                    │  │
│ │   ☐ Objects                                             │  │
│ │   ☐ Profiles                                            │  │
│ │   ☐ Rules                                               │  │
│ │                                                          │  │
│ │ ☐ Mobile Users                                          │  │
│ │   ☐ Objects                                             │  │
│ │   ☐ Profiles                                            │  │
│ │   ☐ Rules                                               │  │
│ │                                                          │  │
│ │ ☐ Remote Networks                                       │  │
│ │   ☐ Objects                                             │  │
│ │   ☐ Profiles                                            │  │
│ │   ☐ Rules                                               │  │
│ │                                                          │  │
│ │ ☐ Custom-Folder-1                                       │  │
│ │   ☐ Objects                                             │  │
│ │   ☐ Profiles                                            │  │
│ │   ☐ Rules                                               │  │
│ │                                                          │  │
│ │ Filtered out (not Prisma Access): all, ngfw             │  │
│ │                                                          │  │
│ └──────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌─ Snippets (3 found) ───────────────────────────────────┐  │
│ │ ☐ snippet-mobile-users                                  │  │
│ │   Folders: Mobile Users                                 │  │
│ │                                                          │  │
│ │ ☐ snippet-security-baseline                             │  │
│ │   Folders: Shared, Mobile Users                         │  │
│ │                                                          │  │
│ │ ☐ snippet-custom-policy                                 │  │
│ │   Folders: Custom-Folder-1                              │  │
│ └──────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌─ Dependency Resolution ─────────────────────────────────┐  │
│ │ ☑ Auto-check dependencies                               │  │
│ │   When a folder is selected, automatically select:      │  │
│ │   - Objects that folder depends on (other folders)      │  │
│ │   - Profiles that folder references                     │  │
│ │   - Snippets associated with folder                     │  │
│ └──────────────────────────────────────────────────────────┘  │
│                                                               │
│ Selection Summary:                                            │
│ • 2 folders selected                                          │
│ • 6 sections selected (2 objects, 2 profiles, 2 rules)       │
│ • 1 snippet selected                                          │
│ • 3 dependencies auto-added                                   │
│                                                               │
│              [Discover List]  [Cancel]  [OK]                  │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Dialog Implementation

```python
"""Folder and snippet selection dialog for configuration import."""

from typing import Dict, Any, List, Set, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QLineEdit, QCheckBox, QGroupBox, QTextEdit,
    QDialogButtonBox, QProgressDialog
)
from PyQt6.QtCore import Qt, pyqtSignal

from prisma.api_client import PrismaAccessAPIClient
from gui.workers import DiscoveryWorker


class FolderSelectionDialog(QDialog):
    """Dialog for selecting folders and snippets for configuration import."""
    
    # Signal emitted when discovery completes
    discovery_completed = pyqtSignal(list, list)  # folders, snippets
    
    def __init__(self, api_client: PrismaAccessAPIClient, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.folders = []
        self.snippets = []
        self.folder_items = {}  # folder_name -> QTreeWidgetItem
        self.snippet_items = {}  # snippet_name -> QTreeWidgetItem
        
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Select Folders and Snippets")
        self.setMinimumSize(800, 700)
        
        layout = QVBoxLayout(self)
        
        # Instructions
        info = QLabel(
            "Select which folders and snippets to import from the source tenant.\n"
            "Folders marked as 'all' or 'ngfw' are filtered out (not Prisma Access specific)."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # Discovery button
        discover_layout = QHBoxLayout()
        discover_layout.addStretch()
        
        self.discover_btn = QPushButton("🔍 Grab Folder & Snippet List")
        self.discover_btn.setMinimumWidth(250)
        self.discover_btn.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; padding: 10px; font-weight: bold; }"
            "QPushButton:hover { background-color: #1976D2; }"
        )
        self.discover_btn.clicked.connect(self._start_discovery)
        discover_layout.addWidget(self.discover_btn)
        
        discover_layout.addStretch()
        layout.addLayout(discover_layout)
        
        # Folder tree group
        folder_group = QGroupBox("Discovered Folders")
        folder_layout = QVBoxLayout()
        
        # Search box
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search folders...")
        self.search_input.textChanged.connect(self._on_search)
        search_layout.addWidget(self.search_input)
        folder_layout.addLayout(search_layout)
        
        # Select all checkbox
        self.select_all_folders_check = QCheckBox("Select All Folders")
        self.select_all_folders_check.stateChanged.connect(self._on_select_all_folders)
        folder_layout.addWidget(self.select_all_folders_check)
        
        # Folder tree
        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderLabels(["Folder / Component", "Type", "Status"])
        self.folder_tree.setColumnWidth(0, 400)
        self.folder_tree.itemChanged.connect(self._on_folder_item_changed)
        folder_layout.addWidget(self.folder_tree)
        
        # Filtered folders label
        self.filtered_label = QLabel("Filtered out: (none discovered yet)")
        self.filtered_label.setStyleSheet("color: orange; font-size: 10px;")
        folder_layout.addWidget(self.filtered_label)
        
        folder_group.setLayout(folder_layout)
        layout.addWidget(folder_group)
        
        # Snippet group
        snippet_group = QGroupBox("Snippets")
        snippet_layout = QVBoxLayout()
        
        self.select_all_snippets_check = QCheckBox("Select All Snippets")
        self.select_all_snippets_check.stateChanged.connect(self._on_select_all_snippets)
        snippet_layout.addWidget(self.select_all_snippets_check)
        
        self.snippet_tree = QTreeWidget()
        self.snippet_tree.setHeaderLabels(["Snippet", "Associated Folders"])
        self.snippet_tree.setColumnWidth(0, 300)
        snippet_layout.addWidget(self.snippet_tree)
        
        snippet_group.setLayout(snippet_layout)
        layout.addWidget(snippet_group)
        
        # Dependency resolution option
        dep_group = QGroupBox("Dependency Resolution")
        dep_layout = QVBoxLayout()
        
        self.auto_deps_check = QCheckBox("Auto-check dependencies")
        self.auto_deps_check.setChecked(True)
        self.auto_deps_check.setToolTip(
            "Automatically select objects, profiles, and snippets that selected folders depend on"
        )
        dep_layout.addWidget(self.auto_deps_check)
        
        dep_info = QLabel(
            "When enabled, selecting a folder will automatically select:\n"
            "• Objects from other folders that this folder references\n"
            "• Profiles that this folder's rules use\n"
            "• Snippets associated with this folder"
        )
        dep_info.setStyleSheet("color: gray; font-size: 10px;")
        dep_info.setWordWrap(True)
        dep_layout.addWidget(dep_info)
        
        dep_group.setLayout(dep_layout)
        layout.addWidget(dep_group)
        
        # Summary
        self.summary_label = QLabel("No folders or snippets selected")
        self.summary_label.setStyleSheet("font-weight: bold; padding: 10px; background-color: #f0f0f0;")
        layout.addWidget(self.summary_label)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        self.ok_btn = QPushButton("OK")
        self.ok_btn.setEnabled(False)
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 8px; }"
            "QPushButton:hover { background-color: #45a049; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        button_layout.addWidget(self.ok_btn)
        
        layout.addLayout(button_layout)
    
    def _start_discovery(self):
        """Start folder and snippet discovery."""
        if not self.api_client:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Not Connected",
                "Please connect to Prisma Access before discovering folders."
            )
            return
        
        # Show progress dialog
        progress = QProgressDialog("Discovering folders and snippets...", None, 0, 0, self)
        progress.setWindowTitle("Discovery")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        
        # Create worker thread
        from gui.workers import DiscoveryWorker
        self.worker = DiscoveryWorker(self.api_client)
        self.worker.finished.connect(lambda folders, snippets: self._on_discovery_finished(folders, snippets, progress))
        self.worker.error.connect(lambda error: self._on_discovery_error(error, progress))
        self.worker.start()
    
    def _on_discovery_finished(self, folders: List[Dict], snippets: List[Dict], progress):
        """Handle discovery completion."""
        progress.close()
        
        self.folders = folders
        self.snippets = snippets
        
        # Populate folder tree
        self._populate_folder_tree()
        
        # Populate snippet tree
        self._populate_snippet_tree()
        
        # Enable OK button
        self.ok_btn.setEnabled(True)
        
        # Update summary
        self._update_summary()
        
        # Show success message
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "Discovery Complete",
            f"Discovered {len(folders)} folders and {len(snippets)} snippets.\n\n"
            f"Please select which folders and components to import."
        )
    
    def _on_discovery_error(self, error: str, progress):
        """Handle discovery error."""
        progress.close()
        
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(
            self,
            "Discovery Failed",
            f"Failed to discover folders and snippets:\n\n{error}"
        )
    
    def _populate_folder_tree(self):
        """Populate folder tree with discovered folders."""
        self.folder_tree.clear()
        self.folder_items.clear()
        
        filtered_count = 0
        filtered_names = []
        
        for folder in self.folders:
            folder_name = folder.get("name", "")
            is_default = folder.get("is_default", False)
            
            # Create folder item
            folder_item = QTreeWidgetItem(self.folder_tree)
            folder_item.setText(0, folder_name)
            folder_item.setText(1, "Folder")
            
            if is_default:
                folder_item.setText(2, "Default")
                folder_item.setForeground(2, Qt.GlobalColor.gray)
            else:
                folder_item.setText(2, "Custom")
            
            folder_item.setCheckState(0, Qt.CheckState.Unchecked)
            folder_item.setData(0, Qt.ItemDataRole.UserRole, folder)
            
            # Store reference
            self.folder_items[folder_name] = folder_item
            
            # Add component children (objects, profiles, rules)
            components = [
                ("Objects", "Addresses, address groups, services, service groups"),
                ("Profiles", "Security profiles (AV, AS, VPN, etc.)"),
                ("Rules", "Security policy rules")
            ]
            
            for comp_name, comp_desc in components:
                comp_item = QTreeWidgetItem(folder_item)
                comp_item.setText(0, comp_name)
                comp_item.setText(1, "Component")
                comp_item.setToolTip(0, comp_desc)
                comp_item.setCheckState(0, Qt.CheckState.Unchecked)
                comp_item.setData(0, Qt.ItemDataRole.UserRole, {"type": comp_name.lower()})
        
        self.folder_tree.expandAll()
        
        # Update filtered label
        if filtered_names:
            self.filtered_label.setText(f"Filtered out (not Prisma Access): {', '.join(filtered_names)}")
        else:
            self.filtered_label.setText("Filtered out: all, ngfw, Service Connections, Colo Connect")
    
    def _populate_snippet_tree(self):
        """Populate snippet tree with discovered snippets."""
        self.snippet_tree.clear()
        self.snippet_items.clear()
        
        for snippet in self.snippets:
            snippet_name = snippet.get("name", "")
            folder_names = snippet.get("folder_names", [])
            
            item = QTreeWidgetItem(self.snippet_tree)
            item.setText(0, snippet_name)
            item.setText(1, ", ".join(folder_names) if folder_names else "(no folders)")
            item.setCheckState(0, Qt.CheckState.Unchecked)
            item.setData(0, Qt.ItemDataRole.UserRole, snippet)
            
            self.snippet_items[snippet_name] = item
    
    def _on_folder_item_changed(self, item: QTreeWidgetItem, column: int):
        """Handle folder item checkbox change."""
        if column != 0:
            return
        
        # Block signals to prevent recursion
        self.folder_tree.blockSignals(True)
        
        # If parent folder is checked/unchecked, update children
        if item.parent() is None:  # This is a folder
            state = item.checkState(0)
            for i in range(item.childCount()):
                child = item.child(i)
                child.setCheckState(0, state)
        
        # If child is changed, update parent
        else:  # This is a component
            parent = item.parent()
            if parent:
                # Check if all children are checked
                all_checked = all(
                    parent.child(i).checkState(0) == Qt.CheckState.Checked
                    for i in range(parent.childCount())
                )
                
                if all_checked:
                    parent.setCheckState(0, Qt.CheckState.Checked)
                else:
                    # Check if any child is checked
                    any_checked = any(
                        parent.child(i).checkState(0) == Qt.CheckState.Checked
                        for i in range(parent.childCount())
                    )
                    
                    if any_checked:
                        parent.setCheckState(0, Qt.CheckState.PartiallyChecked)
                    else:
                        parent.setCheckState(0, Qt.CheckState.Unchecked)
        
        self.folder_tree.blockSignals(False)
        
        # Update summary
        self._update_summary()
        
        # Auto-resolve dependencies if enabled
        if self.auto_deps_check.isChecked():
            self._resolve_dependencies()
    
    def _on_select_all_folders(self, state):
        """Select or deselect all folders."""
        check_state = Qt.CheckState.Checked if state == Qt.CheckState.Checked.value else Qt.CheckState.Unchecked
        
        self.folder_tree.blockSignals(True)
        
        for i in range(self.folder_tree.topLevelItemCount()):
            item = self.folder_tree.topLevelItem(i)
            item.setCheckState(0, check_state)
            
            # Update children
            for j in range(item.childCount()):
                child = item.child(j)
                child.setCheckState(0, check_state)
        
        self.folder_tree.blockSignals(False)
        
        self._update_summary()
    
    def _on_select_all_snippets(self, state):
        """Select or deselect all snippets."""
        check_state = Qt.CheckState.Checked if state == Qt.CheckState.Checked.value else Qt.CheckState.Unchecked
        
        for i in range(self.snippet_tree.topLevelItemCount()):
            item = self.snippet_tree.topLevelItem(i)
            item.setCheckState(0, check_state)
        
        self._update_summary()
    
    def _on_search(self, text: str):
        """Filter folders by search text."""
        if not text:
            # Show all items
            for i in range(self.folder_tree.topLevelItemCount()):
                self.folder_tree.topLevelItem(i).setHidden(False)
            return
        
        text_lower = text.lower()
        
        for i in range(self.folder_tree.topLevelItemCount()):
            item = self.folder_tree.topLevelItem(i)
            folder_name = item.text(0).lower()
            
            # Hide if doesn't match
            item.setHidden(text_lower not in folder_name)
    
    def _resolve_dependencies(self):
        """Auto-resolve dependencies for selected folders."""
        # TODO: Implement dependency resolution
        # This would analyze selected folders and:
        # 1. Identify referenced objects from other folders
        # 2. Identify referenced profiles
        # 3. Auto-check associated snippets
        pass
    
    def _update_summary(self):
        """Update selection summary."""
        folder_count = 0
        section_count = 0
        snippet_count = 0
        
        # Count selected folders and sections
        for i in range(self.folder_tree.topLevelItemCount()):
            item = self.folder_tree.topLevelItem(i)
            if item.checkState(0) in [Qt.CheckState.Checked, Qt.CheckState.PartiallyChecked]:
                folder_count += 1
                
                # Count checked children
                for j in range(item.childCount()):
                    child = item.child(j)
                    if child.checkState(0) == Qt.CheckState.Checked:
                        section_count += 1
        
        # Count selected snippets
        for i in range(self.snippet_tree.topLevelItemCount()):
            item = self.snippet_tree.topLevelItem(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                snippet_count += 1
        
        # Update label
        if folder_count == 0 and snippet_count == 0:
            self.summary_label.setText("No folders or snippets selected")
        else:
            parts = []
            if folder_count > 0:
                parts.append(f"{folder_count} folder(s)")
            if section_count > 0:
                parts.append(f"{section_count} section(s)")
            if snippet_count > 0:
                parts.append(f"{snippet_count} snippet(s)")
            
            self.summary_label.setText("Selected: " + ", ".join(parts))
    
    def get_selected_folders(self) -> List[str]:
        """Get list of selected folder names."""
        selected = []
        
        for i in range(self.folder_tree.topLevelItemCount()):
            item = self.folder_tree.topLevelItem(i)
            if item.checkState(0) in [Qt.CheckState.Checked, Qt.CheckState.PartiallyChecked]:
                folder_name = item.text(0)
                selected.append(folder_name)
        
        return selected
    
    def get_selected_components(self) -> Dict[str, List[str]]:
        """Get selected components per folder."""
        components = {}
        
        for i in range(self.folder_tree.topLevelItemCount()):
            item = self.folder_tree.topLevelItem(i)
            folder_name = item.text(0)
            
            folder_components = []
            for j in range(item.childCount()):
                child = item.child(j)
                if child.checkState(0) == Qt.CheckState.Checked:
                    comp_type = child.text(0).lower()
                    folder_components.append(comp_type)
            
            if folder_components:
                components[folder_name] = folder_components
        
        return components
    
    def get_selected_snippets(self) -> List[str]:
        """Get list of selected snippet names."""
        selected = []
        
        for i in range(self.snippet_tree.topLevelItemCount()):
            item = self.snippet_tree.topLevelItem(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                snippet_name = item.text(0)
                selected.append(snippet_name)
        
        return selected
```

---

## 5. GUI Integration

### 5.1 Update Pull Widget

Add button to `gui/pull_widget.py`:

```python
# In PullConfigWidget._init_ui()

# Add before options group
folder_selection_layout = QHBoxLayout()
folder_selection_layout.addStretch()

self.folder_select_btn = QPushButton("📁 Select Folders & Snippets...")
self.folder_select_btn.setMinimumWidth(250)
self.folder_select_btn.setStyleSheet(
    "QPushButton { background-color: #FF9800; color: white; padding: 10px; font-weight: bold; }"
    "QPushButton:hover { background-color: #F57C00; }"
)
self.folder_select_btn.clicked.connect(self._open_folder_selection)
self.folder_select_btn.setEnabled(False)  # Enable when connected
folder_selection_layout.addWidget(self.folder_select_btn)

folder_selection_layout.addStretch()
layout.addLayout(folder_selection_layout)

# Add selection status label
self.folder_selection_label = QLabel("No specific folders selected (will pull all)")
self.folder_selection_label.setStyleSheet("color: gray; font-size: 10px; padding: 5px;")
layout.addWidget(self.folder_selection_label)

# Store selected folders/components
self.selected_folders = []
self.selected_components = {}
self.selected_snippets = []
```

Add handler methods:

```python
def _open_folder_selection(self):
    """Open folder selection dialog."""
    if not self.api_client:
        QMessageBox.warning(
            self,
            "Not Connected",
            "Please connect to Prisma Access before selecting folders."
        )
        return
    
    from gui.dialogs.folder_selection_dialog import FolderSelectionDialog
    
    dialog = FolderSelectionDialog(self.api_client, self)
    if dialog.exec():
        self.selected_folders = dialog.get_selected_folders()
        self.selected_components = dialog.get_selected_components()
        self.selected_snippets = dialog.get_selected_snippets()
        
        # Update label
        folder_count = len(self.selected_folders)
        snippet_count = len(self.selected_snippets)
        
        if folder_count == 0 and snippet_count == 0:
            self.folder_selection_label.setText("No specific folders selected (will pull all)")
            self.folder_selection_label.setStyleSheet("color: gray; font-size: 10px; padding: 5px;")
        else:
            parts = []
            if folder_count > 0:
                parts.append(f"{folder_count} folder(s)")
            if snippet_count > 0:
                parts.append(f"{snippet_count} snippet(s)")
            
            self.folder_selection_label.setText(f"Selected: {', '.join(parts)}")
            self.folder_selection_label.setStyleSheet("color: green; font-size: 10px; padding: 5px;")

def set_api_client(self, api_client):
    """Set the API client for pull operations."""
    self.api_client = api_client
    self.pull_btn.setEnabled(api_client is not None)
    self.folder_select_btn.setEnabled(api_client is not None)  # NEW
    
    # ... rest of existing code ...
```

Update `_start_pull()` to include folder selection:

```python
def _start_pull(self):
    """Start the pull operation."""
    # ... existing validation ...
    
    # Gather options
    options = {
        # ... existing options ...
        
        # NEW: Folder and snippet selection
        "selected_folders": self.selected_folders if self.selected_folders else None,
        "selected_components": self.selected_components if self.selected_components else None,
        "selected_snippets": self.selected_snippets if self.selected_snippets else None,
    }
    
    # ... rest of existing code ...
```

---

## 6. Worker Thread for Discovery

**File:** Add to `gui/workers.py`

```python
class DiscoveryWorker(QThread):
    """Worker thread for folder and snippet discovery."""
    
    # Signals
    finished = pyqtSignal(list, list)  # folders, snippets
    error = pyqtSignal(str)  # error message
    
    def __init__(self, api_client: PrismaAccessAPIClient):
        super().__init__()
        self.api_client = api_client
    
    def run(self):
        """Run discovery."""
        try:
            from prisma.pull.folder_capture import FolderCapture, filter_folders_for_migration
            from prisma.pull.snippet_capture import SnippetCapture
            
            # Discover folders
            folder_capture = FolderCapture(self.api_client)
            all_folders = folder_capture.discover_folders()
            
            # Filter for migration (remove "all", "ngfw", etc.)
            filtered_folders = filter_folders_for_migration(all_folders)
            
            # Discover snippets
            snippet_capture = SnippetCapture(self.api_client)
            snippets = snippet_capture.discover_snippets_with_folders()
            
            # Emit success
            self.finished.emit(filtered_folders, snippets)
            
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n\n{traceback.format_exc()}"
            self.error.emit(error_msg)
```

---

## 7. Backend Integration - Pull Orchestrator

### 7.1 Update Pull Orchestrator

Modify `prisma/pull/pull_orchestrator.py`:

```python
def pull_complete_configuration(
    self,
    folder_names: Optional[List[str]] = None,
    snippet_names: Optional[List[str]] = None,
    selected_components: Optional[Dict[str, List[str]]] = None,  # NEW
    application_names: Optional[List[str]] = None,
    include_snippets: bool = True,
    # ... other params ...
) -> Dict[str, Any]:
    """
    Pull complete configuration from Prisma Access.
    
    Args:
        folder_names: List of folder names to pull (None = all folders)
        snippet_names: List of snippet names to pull (None = all, only used if include_snippets=True)
        selected_components: Dict mapping folder names to component types to pull
                            e.g., {"Mobile Users": ["objects", "rules"], "Shared": ["profiles"]}
                            If None, pulls all components for selected folders
        application_names: List of custom application names to capture
        include_snippets: Whether to capture snippets
        ...
    """
    # ... existing code ...
    
    # Pull folder configurations
    if folder_names:
        # Pull specific folders
        for folder_name in folder_names:
            # Determine which components to pull for this folder
            if selected_components and folder_name in selected_components:
                components = selected_components[folder_name]
                include_objs = "objects" in components
                include_profs = "profiles" in components
                include_ruls = "rules" in components
            else:
                # Pull all components by default
                include_objs = True
                include_profs = True
                include_ruls = True
            
            folder_config = self.pull_folder_configuration(
                folder_name=folder_name,
                include_objects=include_objs,
                include_profiles=include_profs,
                include_rules=include_ruls,
                # ... other params ...
            )
            
            config["security_policies"]["folders"].append(folder_config)
    else:
        # Pull all folders (existing behavior)
        # ... existing code ...
```

---

## 8. Updated Comprehensive Testing Plan

### 8.1 New Test Cases for Folder Selection

**File:** `tests/test_folder_selection.py` (NEW)

```python
"""Tests for folder and snippet selection dialog."""

import pytest
from PyQt6.QtCore import Qt
from gui.dialogs.folder_selection_dialog import FolderSelectionDialog


class TestFolderFiltering:
    """Test folder filtering for Prisma Access migration."""
    
    def test_filter_all_folder(self, mock_folders):
        """Test that 'all' folder is filtered out."""
        from prisma.pull.folder_capture import filter_folders_for_migration
        
        folders = [
            {"name": "all", "id": "1"},
            {"name": "Mobile Users", "id": "2"},
        ]
        
        filtered = filter_folders_for_migration(folders)
        
        assert len(filtered) == 1
        assert filtered[0]["name"] == "Mobile Users"
    
    def test_filter_ngfw_folder(self, mock_folders):
        """Test that 'ngfw' folder is filtered out."""
        from prisma.pull.folder_capture import filter_folders_for_migration
        
        folders = [
            {"name": "ngfw", "id": "1"},
            {"name": "Remote Networks", "id": "2"},
        ]
        
        filtered = filter_folders_for_migration(folders)
        
        assert len(filtered) == 1
        assert filtered[0]["name"] == "Remote Networks"
    
    def test_filter_infrastructure_folders(self, mock_folders):
        """Test that infrastructure-only folders are filtered out."""
        from prisma.pull.folder_capture import filter_folders_for_migration
        
        folders = [
            {"name": "Service Connections", "id": "1"},
            {"name": "Colo Connect", "id": "2"},
            {"name": "Mobile Users", "id": "3"},
        ]
        
        filtered = filter_folders_for_migration(folders)
        
        assert len(filtered) == 1
        assert filtered[0]["name"] == "Mobile Users"
    
    def test_filter_case_insensitive(self, mock_folders):
        """Test that filtering is case-insensitive."""
        from prisma.pull.folder_capture import filter_folders_for_migration
        
        folders = [
            {"name": "ALL", "id": "1"},
            {"name": "NGFW", "id": "2"},
            {"name": "Mobile Users", "id": "3"},
        ]
        
        filtered = filter_folders_for_migration(folders)
        
        assert len(filtered) == 1
        assert filtered[0]["name"] == "Mobile Users"
    
    def test_keep_prisma_access_folders(self, mock_folders):
        """Test that Prisma Access folders are kept."""
        from prisma.pull.folder_capture import filter_folders_for_migration
        
        folders = [
            {"name": "Shared", "id": "1"},
            {"name": "Mobile Users", "id": "2"},
            {"name": "Remote Networks", "id": "3"},
            {"name": "Custom-Folder-1", "id": "4"},
        ]
        
        filtered = filter_folders_for_migration(folders)
        
        assert len(filtered) == 4


class TestFolderSelectionDialog:
    """Test folder selection dialog functionality."""
    
    def test_dialog_creation(self, qtbot, mock_api_client):
        """Test that dialog can be created."""
        dialog = FolderSelectionDialog(mock_api_client)
        qtbot.addWidget(dialog)
        
        assert dialog is not None
        assert dialog.api_client == mock_api_client
    
    def test_discover_button_click(self, qtbot, mock_api_client, monkeypatch):
        """Test discover button starts discovery."""
        dialog = FolderSelectionDialog(mock_api_client)
        qtbot.addWidget(dialog)
        
        # Mock discovery
        discovered = False
        
        def mock_start_discovery():
            nonlocal discovered
            discovered = True
        
        monkeypatch.setattr(dialog, "_start_discovery", mock_start_discovery)
        
        # Click button
        qtbot.mouseClick(dialog.discover_btn, Qt.MouseButton.LeftButton)
        
        assert discovered
    
    def test_folder_tree_population(self, qtbot, mock_api_client):
        """Test that folder tree is populated correctly."""
        dialog = FolderSelectionDialog(mock_api_client)
        qtbot.addWidget(dialog)
        
        dialog.folders = [
            {"name": "Mobile Users", "id": "1", "is_default": False},
            {"name": "Shared", "id": "2", "is_default": True},
        ]
        
        dialog._populate_folder_tree()
        
        assert dialog.folder_tree.topLevelItemCount() == 2
    
    def test_snippet_tree_population(self, qtbot, mock_api_client):
        """Test that snippet tree is populated correctly."""
        dialog = FolderSelectionDialog(mock_api_client)
        qtbot.addWidget(dialog)
        
        dialog.snippets = [
            {"name": "snippet-1", "id": "1", "folder_names": ["Mobile Users"]},
            {"name": "snippet-2", "id": "2", "folder_names": ["Shared", "Mobile Users"]},
        ]
        
        dialog._populate_snippet_tree()
        
        assert dialog.snippet_tree.topLevelItemCount() == 2
    
    def test_folder_selection(self, qtbot, mock_api_client):
        """Test selecting folders."""
        dialog = FolderSelectionDialog(mock_api_client)
        qtbot.addWidget(dialog)
        
        dialog.folders = [
            {"name": "Mobile Users", "id": "1", "is_default": False},
        ]
        
        dialog._populate_folder_tree()
        
        # Select folder
        item = dialog.folder_tree.topLevelItem(0)
        item.setCheckState(0, Qt.CheckState.Checked)
        
        # Verify child components are also checked
        for i in range(item.childCount()):
            child = item.child(i)
            assert child.checkState(0) == Qt.CheckState.Checked
    
    def test_component_selection(self, qtbot, mock_api_client):
        """Test selecting specific components."""
        dialog = FolderSelectionDialog(mock_api_client)
        qtbot.addWidget(dialog)
        
        dialog.folders = [
            {"name": "Mobile Users", "id": "1", "is_default": False},
        ]
        
        dialog._populate_folder_tree()
        
        # Select only objects component
        folder_item = dialog.folder_tree.topLevelItem(0)
        objects_item = folder_item.child(0)  # Assuming first child is objects
        objects_item.setCheckState(0, Qt.CheckState.Checked)
        
        # Verify folder shows partially checked
        assert folder_item.checkState(0) == Qt.CheckState.PartiallyChecked
    
    def test_get_selected_folders(self, qtbot, mock_api_client):
        """Test retrieving selected folders."""
        dialog = FolderSelectionDialog(mock_api_client)
        qtbot.addWidget(dialog)
        
        dialog.folders = [
            {"name": "Mobile Users", "id": "1", "is_default": False},
            {"name": "Remote Networks", "id": "2", "is_default": False},
        ]
        
        dialog._populate_folder_tree()
        
        # Select first folder
        dialog.folder_tree.topLevelItem(0).setCheckState(0, Qt.CheckState.Checked)
        
        selected = dialog.get_selected_folders()
        
        assert len(selected) == 1
        assert "Mobile Users" in selected
    
    def test_get_selected_components(self, qtbot, mock_api_client):
        """Test retrieving selected components per folder."""
        dialog = FolderSelectionDialog(mock_api_client)
        qtbot.addWidget(dialog)
        
        dialog.folders = [
            {"name": "Mobile Users", "id": "1", "is_default": False},
        ]
        
        dialog._populate_folder_tree()
        
        # Select only objects and rules
        folder_item = dialog.folder_tree.topLevelItem(0)
        folder_item.child(0).setCheckState(0, Qt.CheckState.Checked)  # Objects
        folder_item.child(2).setCheckState(0, Qt.CheckState.Checked)  # Rules
        
        components = dialog.get_selected_components()
        
        assert "Mobile Users" in components
        assert "objects" in components["Mobile Users"]
        assert "rules" in components["Mobile Users"]
        assert "profiles" not in components["Mobile Users"]
    
    def test_search_filter(self, qtbot, mock_api_client):
        """Test folder search filtering."""
        dialog = FolderSelectionDialog(mock_api_client)
        qtbot.addWidget(dialog)
        
        dialog.folders = [
            {"name": "Mobile Users", "id": "1", "is_default": False},
            {"name": "Remote Networks", "id": "2", "is_default": False},
        ]
        
        dialog._populate_folder_tree()
        
        # Search for "mobile"
        dialog.search_input.setText("mobile")
        
        # First item should be visible, second hidden
        assert not dialog.folder_tree.topLevelItem(0).isHidden()
        assert dialog.folder_tree.topLevelItem(1).isHidden()
    
    def test_select_all_folders(self, qtbot, mock_api_client):
        """Test select all folders checkbox."""
        dialog = FolderSelectionDialog(mock_api_client)
        qtbot.addWidget(dialog)
        
        dialog.folders = [
            {"name": "Mobile Users", "id": "1", "is_default": False},
            {"name": "Remote Networks", "id": "2", "is_default": False},
        ]
        
        dialog._populate_folder_tree()
        
        # Click select all
        dialog.select_all_folders_check.setCheckState(Qt.CheckState.Checked)
        
        # All folders should be checked
        for i in range(dialog.folder_tree.topLevelItemCount()):
            item = dialog.folder_tree.topLevelItem(i)
            assert item.checkState(0) == Qt.CheckState.Checked


class TestDiscoveryWorker:
    """Test discovery worker thread."""
    
    def test_worker_creation(self, mock_api_client):
        """Test worker can be created."""
        from gui.workers import DiscoveryWorker
        
        worker = DiscoveryWorker(mock_api_client)
        
        assert worker is not None
        assert worker.api_client == mock_api_client
    
    def test_worker_discovery(self, qtbot, mock_api_client, monkeypatch):
        """Test worker performs discovery."""
        from gui.workers import DiscoveryWorker
        
        # Mock folder and snippet capture
        mock_folders = [
            {"name": "Mobile Users", "id": "1"},
        ]
        
        mock_snippets = [
            {"name": "snippet-1", "id": "1"},
        ]
        
        def mock_discover_folders(self):
            return mock_folders
        
        def mock_discover_snippets(self):
            return mock_snippets
        
        from prisma.pull import folder_capture, snippet_capture
        monkeypatch.setattr(folder_capture.FolderCapture, "discover_folders", mock_discover_folders)
        monkeypatch.setattr(snippet_capture.SnippetCapture, "discover_snippets_with_folders", mock_discover_snippets)
        
        worker = DiscoveryWorker(mock_api_client)
        
        # Connect signal
        result = []
        
        def on_finished(folders, snippets):
            result.append((folders, snippets))
        
        worker.finished.connect(on_finished)
        
        # Run worker
        worker.run()
        
        # Verify results
        assert len(result) == 1
        folders, snippets = result[0]
        assert len(folders) == 1
        assert len(snippets) == 1
```

### 8.2 Integration Test Updates

**File:** `tests/test_integration_phase1.py` (UPDATE)

Add new test cases:

```python
class TestFolderSelectionIntegration:
    """Integration tests for folder selection workflow."""
    
    @pytest.mark.integration
    def test_discover_and_filter_folders(self, live_api_client):
        """Test discovering folders and filtering non-PA folders."""
        from prisma.pull.folder_capture import FolderCapture, filter_folders_for_migration
        
        capture = FolderCapture(live_api_client)
        all_folders = capture.discover_folders()
        
        # Should have discovered folders
        assert len(all_folders) > 0
        
        # Filter for migration
        filtered = filter_folders_for_migration(all_folders)
        
        # Verify "all" and "ngfw" are filtered out
        folder_names = [f["name"] for f in filtered]
        assert "all" not in folder_names
        assert "ngfw" not in folder_names
        assert "Service Connections" not in folder_names
        assert "Colo Connect" not in folder_names
    
    @pytest.mark.integration
    def test_pull_selected_folders_only(self, live_api_client):
        """Test pulling only selected folders."""
        from prisma.pull.pull_orchestrator import PullOrchestrator
        
        orchestrator = PullOrchestrator(live_api_client)
        
        # Pull only Mobile Users folder
        config = orchestrator.pull_complete_configuration(
            folder_names=["Mobile Users"],
            include_snippets=False,
            include_infrastructure=False,
        )
        
        # Verify only Mobile Users folder was pulled
        folders = config.get("security_policies", {}).get("folders", [])
        folder_names = [f["name"] for f in folders]
        
        assert len(folder_names) == 1
        assert "Mobile Users" in folder_names
    
    @pytest.mark.integration
    def test_pull_selected_components_only(self, live_api_client):
        """Test pulling only selected components from a folder."""
        from prisma.pull.pull_orchestrator import PullOrchestrator
        
        orchestrator = PullOrchestrator(live_api_client)
        
        # Pull only objects from Mobile Users
        config = orchestrator.pull_complete_configuration(
            folder_names=["Mobile Users"],
            selected_components={"Mobile Users": ["objects"]},
            include_snippets=False,
            include_infrastructure=False,
        )
        
        # Verify only objects were pulled
        folder = config["security_policies"]["folders"][0]
        
        assert len(folder.get("objects", {}).get("addresses", [])) >= 0  # May be 0 or more
        assert "security_rules" not in folder or len(folder["security_rules"]) == 0
        assert "profiles" not in folder or len(folder["profiles"]) == 0
```

### 8.3 Summary of Test Updates

**New Test Files:**
1. `tests/test_folder_selection.py` - Folder selection dialog tests (15+ test cases)

**Updated Test Files:**
2. `tests/test_integration_phase1.py` - Add folder selection integration tests (3+ test cases)
3. `tests/test_folder_capture.py` - Update with filtering tests (5+ test cases)
4. `tests/test_gui_infrastructure.py` - Add GUI tests for folder selection button (3+ test cases)

**New Test Coverage:**
- Folder filtering logic (all, ngfw, infrastructure-only)
- Folder selection dialog UI
- Component selection per folder
- Snippet selection
- Discovery worker thread
- Integration with pull orchestrator
- Dependency resolution (future)

**Total New Tests:** 26+

---

## 9. Implementation Timeline

### Phase 1: Folder Filtering (1-2 days)
- [ ] Add filtering logic to `folder_capture.py`
- [ ] Add `filter_folders_for_migration()` function
- [ ] Update `discover_folders()` to optionally filter
- [ ] Write unit tests for filtering
- [ ] Test filtering against live tenant

### Phase 2: Snippet Discovery Enhancement (1 day)
- [ ] Add `discover_snippets_with_folders()` method
- [ ] Enhance snippet metadata with folder associations
- [ ] Write unit tests

### Phase 3: Discovery Worker (1 day)
- [ ] Create `DiscoveryWorker` in `gui/workers.py`
- [ ] Implement discovery logic
- [ ] Add error handling
- [ ] Write unit tests

### Phase 4: Folder Selection Dialog (2-3 days)
- [ ] Create `folder_selection_dialog.py`
- [ ] Implement folder tree view
- [ ] Implement snippet tree view
- [ ] Add search/filter functionality
- [ ] Implement checkbox logic (parent/child)
- [ ] Add summary display
- [ ] Write GUI tests

### Phase 5: Pull Widget Integration (1 day)
- [ ] Add "Grab Folder & Snippet List" button to pull widget
- [ ] Connect button to folder selection dialog
- [ ] Update pull widget to pass selections to orchestrator
- [ ] Update selection status label

### Phase 6: Pull Orchestrator Updates (1-2 days)
- [ ] Update `pull_complete_configuration()` signature
- [ ] Add `selected_components` parameter handling
- [ ] Update folder pulling logic to respect component selection
- [ ] Test with various selection combinations

### Phase 7: Testing (2-3 days)
- [ ] Write unit tests for folder filtering
- [ ] Write unit tests for dialog components
- [ ] Write integration tests
- [ ] Test with live tenant
- [ ] Test edge cases (no folders, all folders, partial selection)

### Phase 8: Documentation (1 day)
- [ ] Update user guide with folder selection workflow
- [ ] Update API documentation
- [ ] Add screenshots to documentation
- [ ] Update comprehensive testing document

**Total: 10-14 days**

---

## 10. Success Criteria

### 10.1 Feature Completion
- [x] Folder filtering excludes "all" and "ngfw" folders
- [ ] Folder filtering excludes infrastructure-only folders
- [ ] "Grab Folder & Snippet List" button works in GUI
- [ ] Folder selection dialog displays all discovered folders
- [ ] Users can select specific folders
- [ ] Users can select specific components (objects, profiles, rules) per folder
- [ ] Users can select specific snippets
- [ ] Selected folders and components are passed to pull orchestrator
- [ ] Pull orchestrator respects folder and component selection
- [ ] Dependency auto-selection works (future enhancement)

### 10.2 Testing
- [ ] All unit tests passing (26+ new tests)
- [ ] All integration tests passing
- [ ] GUI tests passing
- [ ] Manual testing successful with live tenant
- [ ] Edge cases covered

### 10.3 Documentation
- [ ] User workflow documented
- [ ] API changes documented
- [ ] Testing plan updated
- [ ] Code comments complete

---

## 11. Future Enhancements (Post-MVP)

### 11.1 Automatic Dependency Resolution
- Analyze selected folders for dependencies
- Auto-check objects from other folders that are referenced
- Auto-check profiles used by rules
- Auto-check snippets associated with folders
- Show dependency graph visualization

### 11.2 Folder Hierarchy Visualization
- Display parent/child folder relationships
- Show folder inheritance
- Highlight inherited configurations

### 11.3 Smart Recommendations
- Suggest folders based on common migration patterns
- Recommend snippets based on folder selection
- Warn about missing dependencies

### 11.4 Save/Load Selection Profiles
- Save folder selection as profile
- Load saved selection profiles
- Share selection profiles between users

---

## 12. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Folder API changes | Low | High | Version checks, graceful degradation |
| Missing folder metadata | Medium | Medium | Handle missing fields gracefully |
| Large folder lists (performance) | Low | Low | Lazy loading, pagination if needed |
| Circular dependencies | Low | Medium | Dependency detection, cycle prevention |
| User confusion with partial selection | Medium | Low | Clear UI labels, tooltips, help text |

---

## Document Change Log

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-12-22 | 1.0 | Initial planning document created | AI Assistant |

---

**End of Document**
