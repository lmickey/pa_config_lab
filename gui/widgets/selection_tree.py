"""
Selection Tree Widget for Pull Configuration.

Reusable tree widget with checkboxes for selecting folders, snippets,
and their component types.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QCheckBox,
    QLabel,
    QHeaderView,
)
from PyQt6.QtCore import Qt, pyqtSignal

logger = logging.getLogger(__name__)


# Shared component types for folders and snippets
COMPONENT_TYPES: List[Tuple[str, str]] = [
    ('address_object', 'Address Objects'),
    ('address_group', 'Address Groups'),
    ('service_object', 'Service Objects'),
    ('service_group', 'Service Groups'),
    ('tag', 'Tags'),
    ('application_group', 'Application Groups'),
    ('application_filter', 'Application Filters'),
    ('schedule', 'Schedules'),
    ('hip_object', 'HIP Objects'),
    ('hip_profile', 'HIP Profiles'),
    ('anti_spyware_profile', 'Anti-Spyware Profiles'),
    ('vulnerability_profile', 'Vulnerability Profiles'),
    ('file_blocking_profile', 'File Blocking Profiles'),
    ('wildfire_profile', 'WildFire Profiles'),
    ('dns_security_profile', 'DNS Security Profiles'),
    ('decryption_profile', 'Decryption Profiles'),
    ('http_header_profile', 'HTTP Header Profiles'),
    ('certificate_profile', 'Certificate Profiles'),
    ('security_rule', 'Security Rules'),
    ('decryption_rule', 'Decryption Rules'),
    ('authentication_rule', 'Authentication Rules'),
    ('qos_policy_rule', 'QoS Policy Rules'),
]


class SelectionTreeWidget(QWidget):
    """
    Reusable tree widget with checkboxes for hierarchical selection.
    
    Used for folders, snippets, and infrastructure selection in the pull tab.
    """
    
    # Signal emitted when selection changes
    selection_changed = pyqtSignal()
    
    def __init__(
        self,
        title: str,
        parent: Optional[QWidget] = None,
        show_components: bool = True,
    ):
        """
        Initialize the selection tree widget.
        
        Args:
            title: Title to display above the tree
            parent: Parent widget
            show_components: Whether to show component type children
        """
        super().__init__(parent)
        
        self.title_text = title
        self.show_components = show_components
        self._updating = False  # Prevent recursive updates
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title_label = QLabel(f"<b>{self.title_text}</b>")
        layout.addWidget(title_label)
        
        # Select All checkbox
        self.select_all_check = QCheckBox("Select All")
        self.select_all_check.stateChanged.connect(self._on_select_all_changed)
        layout.addWidget(self.select_all_check)
        
        # Tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Type"])
        self.tree.setColumnWidth(0, 200)
        self.tree.header().setStretchLastSection(True)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tree.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.tree)
    
    def add_top_level_item(
        self,
        name: str,
        item_type: str = "",
        data: Any = None,
        checked: bool = True,
        add_components: bool = True,
    ) -> QTreeWidgetItem:
        """
        Add a top-level item to the tree.
        
        Args:
            name: Display name
            item_type: Type label (e.g., "folder", "snippet")
            data: Custom data to store with the item
            checked: Initial checked state
            add_components: Whether to add component type children
            
        Returns:
            The created QTreeWidgetItem
        """
        item = QTreeWidgetItem([name, item_type])
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        
        if data is not None:
            item.setData(0, Qt.ItemDataRole.UserRole, data)
        
        # Add component type children if requested
        if add_components and self.show_components:
            for comp_type, comp_display in COMPONENT_TYPES:
                child = QTreeWidgetItem([comp_display, comp_type])
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
                child.setData(0, Qt.ItemDataRole.UserRole, {'type': comp_type, 'parent': name})
                item.addChild(child)
        
        self.tree.addTopLevelItem(item)
        return item
    
    def add_child_item(
        self,
        parent: QTreeWidgetItem,
        name: str,
        item_type: str = "",
        data: Any = None,
        checked: bool = True,
    ) -> QTreeWidgetItem:
        """
        Add a child item to an existing item.
        
        Args:
            parent: Parent item
            name: Display name
            item_type: Type label
            data: Custom data to store
            checked: Initial checked state
            
        Returns:
            The created QTreeWidgetItem
        """
        child = QTreeWidgetItem([name, item_type])
        child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        child.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        
        if data is not None:
            child.setData(0, Qt.ItemDataRole.UserRole, data)
        
        parent.addChild(child)
        return child
    
    def clear(self):
        """Clear all items from the tree."""
        self.tree.clear()
        self.select_all_check.setChecked(False)
    
    def _on_select_all_changed(self, state: int):
        """Handle Select All checkbox change."""
        if self._updating:
            return
        
        self._updating = True
        try:
            checked = state == Qt.CheckState.Checked.value
            for i in range(self.tree.topLevelItemCount()):
                item = self.tree.topLevelItem(i)
                self._set_item_checked_recursive(item, checked)
        finally:
            self._updating = False
        
        self.selection_changed.emit()
    
    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        """Handle item check state change."""
        if self._updating or column != 0:
            return
        
        self._updating = True
        try:
            # If parent item changed, update all children
            if item.childCount() > 0:
                checked = item.checkState(0) == Qt.CheckState.Checked
                for i in range(item.childCount()):
                    child = item.child(i)
                    child.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
                    # Recurse for nested children
                    self._set_item_checked_recursive(child, checked)
            
            # Update parent state based on children
            parent = item.parent()
            if parent:
                self._update_parent_check_state(parent)
            
            # Update Select All state
            self._update_select_all_state()
        finally:
            self._updating = False
        
        self.selection_changed.emit()
    
    def _set_item_checked_recursive(self, item: QTreeWidgetItem, checked: bool):
        """Recursively set checked state for item and all children."""
        item.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        for i in range(item.childCount()):
            self._set_item_checked_recursive(item.child(i), checked)
    
    def _update_parent_check_state(self, parent: QTreeWidgetItem):
        """Update parent check state based on children."""
        checked_count = 0
        total_count = parent.childCount()
        
        for i in range(total_count):
            if parent.child(i).checkState(0) == Qt.CheckState.Checked:
                checked_count += 1
        
        if checked_count == 0:
            parent.setCheckState(0, Qt.CheckState.Unchecked)
        elif checked_count == total_count:
            parent.setCheckState(0, Qt.CheckState.Checked)
        else:
            parent.setCheckState(0, Qt.CheckState.PartiallyChecked)
        
        # Recurse up
        grandparent = parent.parent()
        if grandparent:
            self._update_parent_check_state(grandparent)
    
    def _update_select_all_state(self):
        """Update Select All checkbox based on tree state."""
        checked_count = 0
        total_count = self.tree.topLevelItemCount()
        
        for i in range(total_count):
            item = self.tree.topLevelItem(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                checked_count += 1
        
        self._updating = True
        try:
            if total_count == 0:
                self.select_all_check.setChecked(False)
            elif checked_count == total_count:
                self.select_all_check.setChecked(True)
            else:
                self.select_all_check.setChecked(False)
        finally:
            self._updating = False
    
    def get_selected_items(self) -> List[Dict[str, Any]]:
        """
        Get list of selected top-level items with their selected components.
        
        Returns:
            List of dicts with 'name', 'data', and 'components' keys
        """
        selected = []
        
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.checkState(0) != Qt.CheckState.Unchecked:
                entry = {
                    'name': item.text(0),
                    'data': item.data(0, Qt.ItemDataRole.UserRole),
                    'components': [],
                }
                
                # Collect selected components
                for j in range(item.childCount()):
                    child = item.child(j)
                    if child.checkState(0) == Qt.CheckState.Checked:
                        child_data = child.data(0, Qt.ItemDataRole.UserRole)
                        if child_data and 'type' in child_data:
                            entry['components'].append(child_data['type'])
                        else:
                            entry['components'].append(child.text(1))  # Use type column
                
                selected.append(entry)
        
        return selected
    
    def expand_all(self):
        """Expand all items in the tree."""
        self.tree.expandAll()
    
    def collapse_all(self):
        """Collapse all items in the tree."""
        self.tree.collapseAll()
    
    def set_enabled(self, enabled: bool):
        """Enable or disable the widget."""
        self.select_all_check.setEnabled(enabled)
        self.tree.setEnabled(enabled)
