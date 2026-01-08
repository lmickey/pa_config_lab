"""
Folder and snippet selection dialog for configuration import.

This module provides a dialog for selecting specific folders, components,
and snippets for Prisma Access configuration migration.
"""

from typing import Dict, Any, List, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QLineEdit, QCheckBox, QGroupBox,
    QDialogButtonBox, QProgressDialog, QMessageBox, QScrollArea, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal

from prisma.api_client import PrismaAccessAPIClient


class FolderSelectionDialog(QDialog):
    """Dialog for selecting folders and snippets for configuration import."""
    
    # Signal emitted when discovery completes
    discovery_completed = pyqtSignal(list, list)  # folders, snippets
    
    def __init__(self, api_client: PrismaAccessAPIClient, parent=None):
        """
        Initialize folder selection dialog.
        
        Args:
            api_client: Authenticated API client
            parent: Parent widget
        """
        super().__init__(parent)
        self.api_client = api_client
        self.folders = []
        self.snippets = []
        self.folder_items = {}  # folder_name -> QTreeWidgetItem
        self.snippet_items = {}  # snippet_name -> QTreeWidgetItem
        
        self._init_ui()
        
        # Auto-start discovery when dialog opens
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self._start_discovery)  # Start after UI is fully initialized
        
    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Select Folders and Snippets")
        self.setMinimumSize(800, 700)
        self.setMaximumSize(1200, 900)  # Constrain dialog size
        
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Scroll area for all content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Content widget inside scroll area
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        
        # Instructions
        info = QLabel(
            "Select which folders and snippets to import from the source tenant.\n"
            "Folders marked as 'all' or 'ngfw-shared' are filtered out (not Prisma Access specific)."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(info)
        
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
        
        # Select all checkbox and Collapse/Expand buttons
        controls_layout = QHBoxLayout()
        
        self.select_all_folders_check = QCheckBox("Select All Folders")
        self.select_all_folders_check.stateChanged.connect(self._on_select_all_folders)
        controls_layout.addWidget(self.select_all_folders_check)
        
        controls_layout.addStretch()
        
        # Collapse/Expand buttons
        self.collapse_all_btn = QPushButton("Collapse All")
        self.collapse_all_btn.setMaximumWidth(100)
        self.collapse_all_btn.clicked.connect(self._on_collapse_all)
        controls_layout.addWidget(self.collapse_all_btn)
        
        self.expand_all_btn = QPushButton("Expand All")
        self.expand_all_btn.setMaximumWidth(100)
        self.expand_all_btn.clicked.connect(self._on_expand_all)
        controls_layout.addWidget(self.expand_all_btn)
        
        folder_layout.addLayout(controls_layout)
        
        # Folder tree (doubled size - was implicitly sized, now explicitly larger)
        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderLabels(["Folder / Component", "Type", "Status"])
        self.folder_tree.setColumnWidth(0, 400)
        self.folder_tree.setMinimumHeight(300)
        self.folder_tree.setMaximumHeight(400)
        self.folder_tree.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.folder_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.folder_tree.itemChanged.connect(self._on_folder_item_changed)
        folder_layout.addWidget(self.folder_tree)
        
        folder_group.setLayout(folder_layout)
        layout.addWidget(folder_group)
        
        # Snippet group
        snippet_group = QGroupBox("Snippets")
        snippet_layout = QVBoxLayout()
        
        self.select_all_snippets_check = QCheckBox("Select All Snippets")
        self.select_all_snippets_check.stateChanged.connect(self._on_select_all_snippets)
        snippet_layout.addWidget(self.select_all_snippets_check)
        
        self.snippet_tree = QTreeWidget()
        self.snippet_tree.setHeaderLabels(["Snippet", "Type", "Associated Folders"])
        self.snippet_tree.setColumnWidth(0, 300)
        self.snippet_tree.setColumnWidth(1, 100)
        self.snippet_tree.setMinimumHeight(200)
        self.snippet_tree.setMaximumHeight(300)
        self.snippet_tree.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.snippet_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.snippet_tree.itemChanged.connect(self._update_summary)
        snippet_layout.addWidget(self.snippet_tree)
        
        snippet_group.setLayout(snippet_layout)
        layout.addWidget(snippet_group)
        
        # Dependency resolution option (compact)
        dep_layout = QHBoxLayout()
        
        self.auto_deps_check = QCheckBox("Auto-check dependencies (future feature)")
        self.auto_deps_check.setChecked(False)
        self.auto_deps_check.setEnabled(False)  # Disabled for MVP
        self.auto_deps_check.setToolTip(
            "Automatically select objects, profiles, and snippets that selected folders depend on (coming soon)"
        )
        self.auto_deps_check.setStyleSheet("color: gray;")
        dep_layout.addWidget(self.auto_deps_check)
        dep_layout.addStretch()
        
        layout.addLayout(dep_layout)
        
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
            "QPushButton { "
            "  background-color: #4CAF50; color: white; padding: 8px; "
            "  border-radius: 5px; border: 1px solid #388E3C; border-bottom: 3px solid #2E7D32; "
            "}"
            "QPushButton:hover { background-color: #45a049; border-bottom: 3px solid #1B5E20; }"
            "QPushButton:pressed { background-color: #388E3C; border-bottom: 1px solid #2E7D32; }"
            "QPushButton:disabled { background-color: #BDBDBD; border: 1px solid #9E9E9E; border-bottom: 3px solid #757575; }"
        )
        button_layout.addWidget(self.ok_btn)
        
        layout.addLayout(button_layout)
        
        # Set the content widget in the scroll area
        scroll_area.setWidget(content_widget)
        
        # Add scroll area to main layout
        main_layout.addWidget(scroll_area)
    
    def _start_discovery(self):
        """Start folder and snippet discovery."""
        if not self.api_client:
            QMessageBox.warning(
                self,
                "Not Connected",
                "Please connect to Prisma Access before discovering folders."
            )
            return
        
        # Show progress dialog
        progress = QProgressDialog("Discovering folders and snippets...", None, 0, 100, self)
        progress.setWindowTitle("Discovery")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setValue(0)
        progress.show()
        
        # Create worker thread
        from gui.workers import DiscoveryWorker
        self.worker = DiscoveryWorker(self.api_client)
        self.worker.progress.connect(lambda msg, pct: progress.setValue(pct), Qt.ConnectionType.QueuedConnection)
        self.worker.finished.connect(lambda folders, snippets: self._on_discovery_finished(folders, snippets, progress), Qt.ConnectionType.QueuedConnection)
        self.worker.error.connect(lambda error: self._on_discovery_error(error, progress), Qt.ConnectionType.QueuedConnection)
        self.worker.start()
    
    def _on_discovery_finished(self, folders: List[Dict], snippets: List[Dict], progress):
        """Handle discovery completion."""
        progress.close()
        
        self.folders = folders
        self.snippets = snippets
        
        # Extract debug info if available
        debug_info = None
        if snippets and "_discovery_debug" in snippets[0]:
            debug_info = snippets[0]["_discovery_debug"]
        
        # Populate folder tree
        self._populate_folder_tree()
        
        # Populate snippet tree
        self._populate_snippet_tree()
        
        # Enable OK button
        self.ok_btn.setEnabled(True)
        
        # Update summary
        self._update_summary()
        
        # No success dialog - user can see the populated trees
    
    def _on_discovery_error(self, error: str, progress):
        """Handle discovery error."""
        progress.close()
        
        QMessageBox.critical(
            self,
            "Discovery Failed",
            f"Failed to discover folders and snippets:\n\n{error}"
        )
    
    def _populate_folder_tree(self):
        """Populate folder tree with discovered folders."""
        self.folder_tree.clear()
        self.folder_items.clear()
        
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
    
    def _populate_snippet_tree(self):
        """Populate snippet tree with discovered snippets."""
        self.snippet_tree.clear()
        self.snippet_items.clear()
        
        for snippet in self.snippets:
            # Use display_name if available, fallback to name
            snippet_display = snippet.get("display_name", snippet.get("name", ""))
            snippet_name = snippet.get("name", "")
            folder_names = snippet.get("folder_names", [])
            is_default = snippet.get("is_default", False)
            
            item = QTreeWidgetItem(self.snippet_tree)
            item.setText(0, snippet_display)
            
            # Column 1: Type (Predefined/Custom based on type field)
            snippet_type = snippet.get("type", "")
            if snippet_type in ["predefined", "readonly"]:
                item.setText(1, "Predefined")
                item.setForeground(1, Qt.GlobalColor.gray)
            else:
                item.setText(1, "Custom")
            
            # Column 2: Associated Folders
            item.setText(2, ", ".join(folder_names) if folder_names else "(no folders)")
            
            item.setCheckState(0, Qt.CheckState.Unchecked)
            item.setData(0, Qt.ItemDataRole.UserRole, snippet)
            
            # Store by name (not display_name) for lookups
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
    
    def _on_collapse_all(self):
        """Collapse all folders in the tree."""
        self.folder_tree.collapseAll()
    
    def _on_expand_all(self):
        """Expand all folders in the tree."""
        self.folder_tree.expandAll()
    
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
    
    def get_selected_snippets(self) -> List[Dict[str, str]]:
        """
        Get list of selected snippets with their IDs.
        
        Returns:
            List of dicts with 'id' and 'name' keys
        """
        selected = []
        
        for i in range(self.snippet_tree.topLevelItemCount()):
            item = self.snippet_tree.topLevelItem(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                snippet_data = item.data(0, Qt.ItemDataRole.UserRole)
                if snippet_data:
                    selected.append({
                        'id': snippet_data.get('id', ''),
                        'name': snippet_data.get('name', '')
                    })
        
        return selected
