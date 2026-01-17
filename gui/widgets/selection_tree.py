"""
Selection Tree Widget for Pull Configuration.

Reusable tree widget with checkboxes for selecting folders, snippets,
and their component types organized by section.
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
from PyQt6.QtGui import QFont

logger = logging.getLogger(__name__)


# Component types organized by section - matches config viewer organization
COMPONENT_SECTIONS: Dict[str, List[Tuple[str, str]]] = {
    'Addresses': [
        ('address_object', 'Address Objects'),
        ('address_group', 'Address Groups'),
        ('region', 'Address Regions'),
    ],
    'Services': [
        ('service_object', 'Service Objects'),
        ('service_group', 'Service Groups'),
    ],
    'Applications': [
        ('application_group', 'Application Groups'),
        ('application_filter', 'Application Filters'),
    ],
    'Tags & Schedules': [
        ('tag', 'Tags'),
        ('schedule', 'Schedules'),
    ],
    'External Lists': [
        ('external_dynamic_list', 'External Dynamic Lists'),
        ('custom_url_category', 'Custom URL Categories'),
    ],
    'Security Profiles': [
        ('anti_spyware_profile', 'Anti-Spyware Profiles'),
        ('vulnerability_profile', 'Vulnerability Profiles'),
        ('file_blocking_profile', 'File Blocking Profiles'),
        ('wildfire_profile', 'WildFire Profiles'),
        ('dns_security_profile', 'DNS Security Profiles'),
        ('decryption_profile', 'Decryption Profiles'),
        ('profile_group', 'Profile Groups'),
    ],
    'Other Profiles': [
        ('http_header_profile', 'HTTP Header Profiles'),
        ('certificate_profile', 'Certificate Profiles'),
        ('qos_profile', 'QoS Profiles'),
    ],
    'HIP': [
        ('hip_object', 'HIP Objects'),
        ('hip_profile', 'HIP Profiles'),
    ],
    'Authentication': [
        ('local_user', 'Local Users'),
        ('local_user_group', 'Local User Groups'),
    ],
    'Security Policy': [
        ('security_rule', 'Security Rules'),
        ('decryption_rule', 'Decryption Rules'),
    ],
    'Other Policies': [
        ('authentication_rule', 'Authentication Rules'),
        ('qos_policy_rule', 'QoS Policy Rules'),
    ],
}

# Flat list for backwards compatibility
COMPONENT_TYPES: List[Tuple[str, str]] = []
for section_items in COMPONENT_SECTIONS.values():
    COMPONENT_TYPES.extend(section_items)


class SelectionTreeWidget(QWidget):
    """
    Reusable tree widget with checkboxes for hierarchical selection.
    
    Used for folders, snippets, and infrastructure selection in the pull tab.
    Components are organized into sections matching the config viewer.
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
        self.tree.setColumnWidth(0, 220)
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
            add_components: Whether to add component type children (with sections)
            
        Returns:
            The created QTreeWidgetItem
        """
        item = QTreeWidgetItem([name, item_type])
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        
        if data is not None:
            item.setData(0, Qt.ItemDataRole.UserRole, data)
        
        # Add component sections and types if requested
        if add_components and self.show_components:
            self._add_component_sections(item, name, checked)
        
        self.tree.addTopLevelItem(item)
        
        # Update Select All checkbox state after adding item
        self._update_select_all_state()
        
        return item
    
    def _add_component_sections(self, parent_item: QTreeWidgetItem, parent_name: str, checked: bool):
        """
        Add component sections with their items.
        
        Args:
            parent_item: The parent tree item (folder/snippet)
            parent_name: Name of the parent for data storage
            checked: Initial checked state
        """
        for section_name, components in COMPONENT_SECTIONS.items():
            # Create section item (bold)
            section_item = QTreeWidgetItem([section_name, "section"])
            section_item.setFlags(section_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            section_item.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            section_item.setData(0, Qt.ItemDataRole.UserRole, {
                'type': 'section',
                'section': section_name,
                'parent': parent_name
            })
            
            # Make section name bold
            font = section_item.font(0)
            font.setBold(True)
            section_item.setFont(0, font)
            
            # Add component types under section
            for comp_type, comp_display in components:
                child = QTreeWidgetItem([comp_display, comp_type])
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
                child.setData(0, Qt.ItemDataRole.UserRole, {
                    'type': comp_type,
                    'section': section_name,
                    'parent': parent_name
                })
                section_item.addChild(child)
            
            parent_item.addChild(section_item)
    
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
            has_locked = False
            for i in range(self.tree.topLevelItemCount()):
                item = self.tree.topLevelItem(i)
                if not self._set_item_checked_recursive(item, checked):
                    has_locked = True
            
            # If there are locked items that stayed checked, we might be partially checked
            if has_locked and not checked:
                # Some items couldn't be unchecked - update parents
                for i in range(self.tree.topLevelItemCount()):
                    self._update_parent_check_state_from_root(self.tree.topLevelItem(i))
        finally:
            self._updating = False
        
        self.selection_changed.emit()
    
    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        """Handle item check state change."""
        if self._updating or column != 0:
            return
        
        self._updating = True
        try:
            # If item has children and was checked/unchecked, update all children
            if item.childCount() > 0:
                checked = item.checkState(0) == Qt.CheckState.Checked
                for i in range(item.childCount()):
                    self._set_item_checked_recursive(item.child(i), checked)
            
            # Update parent state based on children
            parent = item.parent()
            if parent:
                self._update_parent_check_state(parent)
            
            # Update Select All state
            self._update_select_all_state()
        finally:
            self._updating = False
        
        self.selection_changed.emit()
    
    def _set_item_checked_recursive(self, item: QTreeWidgetItem, checked: bool) -> bool:
        """
        Recursively set checked state for item and all children.
        
        Args:
            item: Tree item to update
            checked: Whether to check or uncheck
            
        Returns:
            True if the item was modified, False if locked
        """
        # Check if item is locked (not user-checkable)
        is_locked = not (item.flags() & Qt.ItemFlag.ItemIsUserCheckable)
        
        # Also check data for locked items (custom applications)
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if item_data and item_data.get('type') == 'custom_applications':
            is_locked = True
        
        if not is_locked:
            item.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        
        has_locked_children = is_locked
        for i in range(item.childCount()):
            if not self._set_item_checked_recursive(item.child(i), checked):
                has_locked_children = True
        
        return not has_locked_children
    
    def _update_parent_check_state(self, parent: QTreeWidgetItem):
        """Update parent check state based on children."""
        checked_count = 0
        unlocked_unchecked = 0
        locked_checked = 0
        total_count = parent.childCount()
        
        for i in range(total_count):
            child = parent.child(i)
            child_state = child.checkState(0)
            
            # Check if child is locked
            child_data = child.data(0, Qt.ItemDataRole.UserRole)
            is_locked = (child_data and child_data.get('type') == 'custom_applications') or \
                        not (child.flags() & Qt.ItemFlag.ItemIsUserCheckable)
            
            if child_state == Qt.CheckState.Checked:
                checked_count += 1
                if is_locked:
                    locked_checked += 1
            elif child_state == Qt.CheckState.PartiallyChecked:
                # If any child is partial, parent is partial
                parent.setCheckState(0, Qt.CheckState.PartiallyChecked)
                grandparent = parent.parent()
                if grandparent:
                    self._update_parent_check_state(grandparent)
                return
            elif not is_locked:
                # Only count unlocked unchecked items
                unlocked_unchecked += 1
        
        # If there are locked checked items but other items are unchecked, show partial
        if locked_checked > 0 and unlocked_unchecked > 0:
            parent.setCheckState(0, Qt.CheckState.PartiallyChecked)
        elif checked_count == 0 and unlocked_unchecked == total_count:
            parent.setCheckState(0, Qt.CheckState.Unchecked)
        elif checked_count == total_count:
            parent.setCheckState(0, Qt.CheckState.Checked)
        else:
            parent.setCheckState(0, Qt.CheckState.PartiallyChecked)
        
        # Recurse up
        grandparent = parent.parent()
        if grandparent:
            self._update_parent_check_state(grandparent)
    
    def _update_parent_check_state_from_root(self, item: QTreeWidgetItem):
        """
        Update check states from a root item down, then back up.
        Used after bulk operations to fix parent states when locked items exist.
        """
        # First update all children recursively
        for i in range(item.childCount()):
            child = item.child(i)
            if child.childCount() > 0:
                self._update_parent_check_state_from_root(child)
        
        # Then update this item's state based on children
        if item.childCount() > 0:
            self._update_parent_check_state_for_item(item)
    
    def _update_parent_check_state_for_item(self, item: QTreeWidgetItem):
        """Update a single item's check state based on its children."""
        checked_count = 0
        unlocked_unchecked = 0
        locked_checked = 0
        total_count = item.childCount()
        
        for i in range(total_count):
            child = item.child(i)
            child_state = child.checkState(0)
            
            # Check if child is locked
            child_data = child.data(0, Qt.ItemDataRole.UserRole)
            is_locked = (child_data and child_data.get('type') == 'custom_applications') or \
                        not (child.flags() & Qt.ItemFlag.ItemIsUserCheckable)
            
            if child_state == Qt.CheckState.Checked:
                checked_count += 1
                if is_locked:
                    locked_checked += 1
            elif child_state == Qt.CheckState.PartiallyChecked:
                item.setCheckState(0, Qt.CheckState.PartiallyChecked)
                return
            elif not is_locked:
                unlocked_unchecked += 1
        
        # If there are locked checked items but other items are unchecked, show partial
        if locked_checked > 0 and unlocked_unchecked > 0:
            item.setCheckState(0, Qt.CheckState.PartiallyChecked)
        elif checked_count == 0 and unlocked_unchecked == total_count:
            item.setCheckState(0, Qt.CheckState.Unchecked)
        elif checked_count == total_count:
            item.setCheckState(0, Qt.CheckState.Checked)
        else:
            item.setCheckState(0, Qt.CheckState.PartiallyChecked)
    
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
            List of dicts with 'name', 'data', and 'components' keys.
            Components are collected from all sections (flattened).
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
                
                # Collect selected components from sections
                self._collect_selected_components(item, entry['components'])
                
                selected.append(entry)
        
        return selected
    
    def _collect_selected_components(self, item: QTreeWidgetItem, components: List[str]):
        """
        Recursively collect selected component types from an item.
        
        Args:
            item: Tree item to collect from
            components: List to append component type strings to
        """
        # Pseudo-types that are handled separately (not real API item types)
        SKIP_TYPES = {'custom_applications', 'section', 'info'}
        
        for i in range(item.childCount()):
            child = item.child(i)
            child_data = child.data(0, Qt.ItemDataRole.UserRole)
            
            if child_data:
                item_type = child_data.get('type')
                
                # If it's a section, recurse into it
                if item_type == 'section':
                    self._collect_selected_components(child, components)
                # If it's a component type and checked, add it (skip pseudo-types)
                elif item_type and item_type not in SKIP_TYPES and child.checkState(0) == Qt.CheckState.Checked:
                    components.append(item_type)
            else:
                # Fallback: use type column text
                if child.checkState(0) == Qt.CheckState.Checked:
                    components.append(child.text(1))
    
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
