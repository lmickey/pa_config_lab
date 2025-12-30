"""
Component selection dialog for choosing what to push.

This dialog allows users to select specific folders, snippets, objects,
and infrastructure components from a loaded configuration.
"""

from typing import Dict, Any, Optional, List
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
    QLabel,
    QCheckBox,
    QDialogButtonBox,
    QTabWidget,
    QWidget,
    QSplitter,
)
from PyQt6.QtCore import Qt

from gui.config_tree_builder import ConfigTreeBuilder


class ComponentSelectionDialog(QDialog):
    """Dialog for selecting components to push."""
    
    def __init__(self, config: Dict[str, Any], full_config: Optional[Dict[str, Any]] = None, 
                 previous_selection: Optional[Dict[str, Any]] = None, parent=None):
        """Initialize the component selection dialog.
        
        Args:
            config: The configuration dictionary to select from
            full_config: The full configuration (for dependency resolution). If None, uses config.
            previous_selection: Previously selected items to restore
            parent: Parent widget
        """
        super().__init__(parent)
        self.config = config
        self.full_config = full_config if full_config is not None else config
        self.previous_selection = previous_selection
        self.selected_items = {
            'folders': [],
            'snippets': [],
            'objects': {},
            'infrastructure': {}
        }
        
        self.setWindowTitle("Select Components to Push")
        self.resize(900, 700)
        
        self._init_ui()
        self._populate_tree()
        
        # Restore previous selections if provided
        if self.previous_selection:
            self._restore_selections()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("<h2>Select Components to Push</h2>")
        layout.addWidget(header)
        
        info = QLabel(
            "Check the components you want to push to the destination tenant. "
            "Use 'Select All' to quickly select everything."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # Selection controls
        controls_layout = QHBoxLayout()
        
        self.select_all_check = QCheckBox("Select All")
        self.select_all_check.stateChanged.connect(self._on_select_all)
        controls_layout.addWidget(self.select_all_check)
        
        controls_layout.addStretch()
        
        expand_btn = QPushButton("Expand All")
        expand_btn.clicked.connect(self._expand_all)
        controls_layout.addWidget(expand_btn)
        
        collapse_btn = QPushButton("Collapse All")
        collapse_btn.clicked.connect(self._collapse_all)
        controls_layout.addWidget(collapse_btn)
        
        layout.addLayout(controls_layout)
        
        # Main tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Component", "Type", "Count"])
        self.tree.setColumnWidth(0, 400)
        self.tree.setColumnWidth(1, 150)
        self.tree.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.tree)
        
        # Selection summary
        self.summary_label = QLabel("Nothing selected")
        self.summary_label.setStyleSheet(
            "color: gray; padding: 10px; background-color: #f5f5f5; border-radius: 5px;"
        )
        layout.addWidget(self.summary_label)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _populate_tree(self):
        """Populate the tree with configuration components."""
        self.tree.blockSignals(True)
        
        # Use shared tree builder with checkboxes enabled and simplified structure
        builder = ConfigTreeBuilder(enable_checkboxes=True, simplified=True)
        builder.build_tree(self.tree, self.config)
        
        # Auto-expand top level and all folders
        self.tree.expandToDepth(0)
        for i in range(self.tree.topLevelItemCount()):
            top_item = self.tree.topLevelItem(i)
            # If this is "Security Policies", expand it
            if top_item.text(0) == "Security Policies":
                top_item.setExpanded(True)
                # Find and expand "Folders" within it
                for j in range(top_item.childCount()):
                    child = top_item.child(j)
                    if child.text(0) == "Folders":
                        child.setExpanded(True)
                        # Expand each individual folder
                        for k in range(child.childCount()):
                            child.child(k).setExpanded(True)
        
        # Check for CIE dependencies
        self._check_cie_dependencies()
        
        self.tree.blockSignals(False)
    
    def _on_select_all(self, state):
        """Handle select all checkbox."""
        self.tree.blockSignals(True)
        
        check_state = Qt.CheckState.Checked if state == Qt.CheckState.Checked.value else Qt.CheckState.Unchecked
        
        # Set all top-level items
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            self._set_item_check_state_recursive(item, check_state)
        
        self.tree.blockSignals(False)
        self._update_summary()
    
    def _set_item_check_state_recursive(self, item: QTreeWidgetItem, state: Qt.CheckState):
        """Recursively set check state for item and all children."""
        item.setCheckState(0, state)
        for i in range(item.childCount()):
            self._set_item_check_state_recursive(item.child(i), state)
    
    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        """Handle item check state change."""
        if column != 0:
            return
        
        self.tree.blockSignals(True)
        
        # Update children
        check_state = item.checkState(0)
        for i in range(item.childCount()):
            self._set_item_check_state_recursive(item.child(i), check_state)
        
        # Update parent
        parent = item.parent()
        if parent:
            self._update_parent_check_state(parent)
        
        self.tree.blockSignals(False)
        self._update_summary()
    
    def _update_parent_check_state(self, parent: QTreeWidgetItem):
        """Update parent check state based on children."""
        checked_count = 0
        partial_count = 0
        total_count = parent.childCount()
        
        for i in range(total_count):
            child_state = parent.child(i).checkState(0)
            if child_state == Qt.CheckState.Checked:
                checked_count += 1
            elif child_state == Qt.CheckState.PartiallyChecked:
                partial_count += 1
        
        if checked_count == 0 and partial_count == 0:
            parent.setCheckState(0, Qt.CheckState.Unchecked)
        elif checked_count == total_count:
            parent.setCheckState(0, Qt.CheckState.Checked)
        else:
            parent.setCheckState(0, Qt.CheckState.PartiallyChecked)
        
        # Recursively update grandparent
        grandparent = parent.parent()
        if grandparent:
            self._update_parent_check_state(grandparent)
    
    def _check_cie_dependencies(self):
        """Check for Cloud Identity Engine dependencies and grey out items."""
        # Recursively check all items in tree
        for i in range(self.tree.topLevelItemCount()):
            self._check_item_for_cie(self.tree.topLevelItem(i))
    
    def _check_item_for_cie(self, item: QTreeWidgetItem):
        """Recursively check item and children for CIE dependencies."""
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if item_data:
            data = item_data.get('data', {})
            item_type = item_data.get('type', '')
            
            # Check authentication profiles for CIE
            if item_type == 'folder_profile' and item_data.get('profile_type') == 'authentication_profiles':
                # Check if profile uses CIE - use the profile data directly
                if self._uses_cie(data):
                    # Grey out and disable
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                    item.setForeground(0, Qt.GlobalColor.gray)
                    item.setToolTip(0, "⚠️ Cannot push: Profile depends on Cloud Identity Engine (CIE)")
                    item.setText(2, "CIE Dependency")
            
            # Check security rules for authentication profiles
            elif item_type == 'security_rule':
                # Check if rule uses authentication profile
                auth_profile_name = data.get('authentication_profile')
                if auth_profile_name:
                    # Look up the profile and check it directly
                    profile_data = self._find_auth_profile(auth_profile_name)
                    if profile_data and self._uses_cie(profile_data):
                        # Grey out and disable
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                        item.setForeground(0, Qt.GlobalColor.gray)
                        item.setToolTip(0, f"⚠️ Cannot push: Rule uses authentication profile '{auth_profile_name}' which depends on CIE")
                        item.setText(2, "CIE Dependency")
        
        # Check children
        for i in range(item.childCount()):
            self._check_item_for_cie(item.child(i))
    
    def _uses_cie(self, profile: Dict) -> bool:
        """Check if authentication profile uses Cloud Identity Engine."""
        # Check for CIE-specific fields
        if profile.get('type') == 'cloud':
            return True
        if profile.get('cloud_authentication'):
            return True
        
        # Check method field for cloud authentication
        method = profile.get('method', {})
        if isinstance(method, dict):
            # Check if method contains 'cloud' key
            if 'cloud' in method:
                return True
            # Also check for cloud_authentication within method
            if method.get('cloud_authentication'):
                return True
        
        # Check for CIE keywords in the profile
        if 'cloud_identity_engine' in str(profile).lower():
            return True
        if 'cie' in str(profile.get('name', '')).lower():
            return True
        
        return False
    
    def _find_auth_profile(self, profile_name: str) -> Optional[Dict]:
        """Find an authentication profile by name across all folders.
        
        Args:
            profile_name: Name of the authentication profile
            
        Returns:
            Profile data dict if found, None otherwise
        """
        # Search through full_config (which has all folders) for this profile
        sec_policies = self.full_config.get('security_policies', {})
        folders = sec_policies.get('folders', [])
        
        for folder in folders:
            profiles = folder.get('profiles', {})
            auth_profiles = profiles.get('authentication_profiles', [])
            
            for profile in auth_profiles:
                if profile.get('name') == profile_name:
                    return profile
        
        return None
    
    def _expand_all(self):
        """Expand all tree items."""
        self.tree.expandAll()
    
    def _collapse_all(self):
        """Collapse all tree items."""
        self.tree.collapseAll()
    
    def _update_summary(self):
        """Update the selection summary label."""
        folders_count = 0
        snippets_count = 0
        objects_count = 0
        infra_count = 0
        
        # Count selected items
        for i in range(self.tree.topLevelItemCount()):
            top_item = self.tree.topLevelItem(i)
            item_data = top_item.data(0, Qt.ItemDataRole.UserRole)
            
            if item_data:
                item_type = item_data.get('type')
                
                if item_type == 'folders_parent':
                    folders_count = self._count_checked_children(top_item)
                elif item_type == 'snippets_parent':
                    snippets_count = self._count_checked_children(top_item)
                elif item_type == 'objects_parent':
                    objects_count = self._count_checked_children_recursive(top_item)
                elif item_type == 'infrastructure_parent':
                    infra_count = self._count_checked_children_recursive(top_item)
        
        total = folders_count + snippets_count + objects_count + infra_count
        
        if total == 0:
            self.summary_label.setText("Nothing selected")
            self.summary_label.setStyleSheet(
                "color: gray; padding: 10px; background-color: #f5f5f5; border-radius: 5px;"
            )
        else:
            summary = f"✅ <b>Selected:</b> {total} items<br>"
            if folders_count > 0:
                summary += f"• {folders_count} folders<br>"
            if snippets_count > 0:
                summary += f"• {snippets_count} snippets<br>"
            if objects_count > 0:
                summary += f"• {objects_count} objects<br>"
            if infra_count > 0:
                summary += f"• {infra_count} infrastructure components"
            
            self.summary_label.setText(summary)
            self.summary_label.setStyleSheet(
                "color: #2e7d32; padding: 10px; background-color: #e8f5e9; border-radius: 5px; border: 2px solid #4CAF50;"
            )
    
    def _count_checked_children(self, parent: QTreeWidgetItem) -> int:
        """Count directly checked children (not recursive)."""
        count = 0
        for i in range(parent.childCount()):
            if parent.child(i).checkState(0) == Qt.CheckState.Checked:
                count += 1
        return count
    
    def _count_checked_children_recursive(self, parent: QTreeWidgetItem) -> int:
        """Count all checked leaf items recursively."""
        count = 0
        for i in range(parent.childCount()):
            child = parent.child(i)
            if child.childCount() > 0:
                # Has children, recurse
                count += self._count_checked_children_recursive(child)
            else:
                # Leaf node
                if child.checkState(0) == Qt.CheckState.Checked:
                    count += 1
        return count
    
    def get_selected_items(self) -> Dict[str, Any]:
        """Get the selected items.
        
        Returns:
            Dictionary with selected folders, snippets, objects, and infrastructure
        """
        selected = {
            'folders': [],
            'snippets': [],
            'objects': {},
            'infrastructure': {}
        }
        
        # Iterate through tree and collect checked items
        # The tree structure is now: Top-level sections (Security Policies, Objects, Infrastructure)
        # We need to navigate into these sections to find the actual items
        for i in range(self.tree.topLevelItemCount()):
            top_item = self.tree.topLevelItem(i)
            section_name = top_item.text(0)
            
            if section_name == "Security Policies":
                # Navigate into Security Policies to find Folders and Snippets
                for j in range(top_item.childCount()):
                    child = top_item.child(j)
                    child_name = child.text(0)
                    
                    if child_name == "Folders":
                        selected['folders'] = self._collect_folders_with_contents(child)
                    elif child_name == "Snippets":
                        # Snippets are direct children, each with their data
                        for k in range(child.childCount()):
                            snippet_item = child.child(k)
                            if snippet_item.checkState(0) == Qt.CheckState.Checked:
                                snippet_data = snippet_item.data(0, Qt.ItemDataRole.UserRole)
                                if snippet_data:
                                    selected['snippets'].append(snippet_data)
            
            elif section_name == "Objects":
                selected['objects'] = self._collect_objects(top_item)
            
            elif section_name == "Infrastructure":
                selected['infrastructure'] = self._collect_infrastructure(top_item)
        
        return selected
    
    def _collect_folders_with_contents(self, parent: QTreeWidgetItem) -> List[Dict]:
        """Collect checked folders with their selected contents."""
        folders = []
        
        for i in range(parent.childCount()):
            folder_item = parent.child(i)
            folder_data = folder_item.data(0, Qt.ItemDataRole.UserRole)
            
            if folder_data and folder_data.get('type') == 'folder':
                folder = folder_data.get('data', {}).copy()
                
                # Collect selected items within this folder
                selected_rules = []
                selected_objects = {}
                selected_profiles = {}
                selected_hip = {}
                
                for j in range(folder_item.childCount()):
                    content_item = folder_item.child(j)
                    content_name = content_item.text(0)
                    content_data = content_item.data(0, Qt.ItemDataRole.UserRole)
                    content_type = content_data.get('type') if content_data else None
                    
                    # Collect rules
                    if content_type == 'rules_parent':
                        for k in range(content_item.childCount()):
                            rule_item = content_item.child(k)
                            if rule_item.checkState(0) == Qt.CheckState.Checked:
                                rule_data = rule_item.data(0, Qt.ItemDataRole.UserRole)
                                if rule_data:
                                    selected_rules.append(rule_data.get('data'))
                    
                    # Collect objects - check for Objects container
                    elif content_name == "Objects":
                        # This is the Objects container, check its children (object types)
                        for k in range(content_item.childCount()):
                            obj_type_item = content_item.child(k)
                            obj_type_data = obj_type_item.data(0, Qt.ItemDataRole.UserRole)
                            if obj_type_data and obj_type_data.get('type') == 'folder_object_type':
                                obj_type = obj_type_data.get('object_type')
                                # Collect individual objects
                                for m in range(obj_type_item.childCount()):
                                    obj_item = obj_type_item.child(m)
                                    if obj_item.checkState(0) == Qt.CheckState.Checked:
                                        obj_data = obj_item.data(0, Qt.ItemDataRole.UserRole)
                                        if obj_data:
                                            if obj_type not in selected_objects:
                                                selected_objects[obj_type] = []
                                            selected_objects[obj_type].append(obj_data.get('data'))
                    
                    # Collect profiles - check for Profiles container
                    elif content_name == "Profiles":
                        # This is the Profiles container, check its children (profile types)
                        for k in range(content_item.childCount()):
                            prof_type_item = content_item.child(k)
                            prof_type_data = prof_type_item.data(0, Qt.ItemDataRole.UserRole)
                            if prof_type_data and prof_type_data.get('type') == 'folder_profile_type':
                                profile_type = prof_type_data.get('profile_type')
                                # Collect individual profiles
                                for m in range(prof_type_item.childCount()):
                                    profile_item = prof_type_item.child(m)
                                    if profile_item.checkState(0) == Qt.CheckState.Checked:
                                        profile_data = profile_item.data(0, Qt.ItemDataRole.UserRole)
                                        if profile_data:
                                            if profile_type not in selected_profiles:
                                                selected_profiles[profile_type] = []
                                            selected_profiles[profile_type].append(profile_data.get('data'))
                    
                    # Collect HIP - check for HIP container
                    elif content_name == "HIP":
                        # This is the HIP container, check its children
                        for k in range(content_item.childCount()):
                            hip_type_item = content_item.child(k)
                            hip_type_name = hip_type_item.text(0)
                            
                            # Collect HIP Objects or HIP Profiles
                            for m in range(hip_type_item.childCount()):
                                hip_item = hip_type_item.child(m)
                                if hip_item.checkState(0) == Qt.CheckState.Checked:
                                    hip_data = hip_item.data(0, Qt.ItemDataRole.UserRole)
                                    if hip_data:
                                        if "HIP Objects" in hip_type_name:
                                            if 'hip_objects' not in selected_hip:
                                                selected_hip['hip_objects'] = []
                                            selected_hip['hip_objects'].append(hip_data)
                                        elif "HIP Profiles" in hip_type_name:
                                            if 'hip_profiles' not in selected_hip:
                                                selected_hip['hip_profiles'] = []
                                            selected_hip['hip_profiles'].append(hip_data)
                
                # Only include folder if it's checked OR has selected contents
                # Check explicitly for non-empty collections
                has_content = (
                    len(selected_rules) > 0 or
                    len(selected_objects) > 0 or
                    len(selected_profiles) > 0 or
                    len(selected_hip) > 0
                )
                
                if folder_item.checkState(0) == Qt.CheckState.Checked or has_content:
                    # Update folder with selected contents (only if not fully checked)
                    if folder_item.checkState(0) != Qt.CheckState.Checked:
                        # Partially selected - only include selected items
                        if selected_rules:
                            folder['security_rules'] = selected_rules
                        else:
                            folder.pop('security_rules', None)
                        
                        if selected_objects:
                            folder['objects'] = selected_objects
                        else:
                            folder.pop('objects', None)
                        
                        if selected_profiles:
                            folder['profiles'] = selected_profiles
                        else:
                            folder.pop('profiles', None)
                        
                        if selected_hip:
                            folder['hip'] = selected_hip
                        else:
                            folder.pop('hip', None)
                    # else: Fully checked - keep all folder contents as-is
                    
                    folders.append(folder)
        
        return folders
    
    def _collect_checked_items(self, parent: QTreeWidgetItem, target_type: str) -> List[Dict]:
        """Collect checked items of a specific type."""
        items = []
        for i in range(parent.childCount()):
            child = parent.child(i)
            if child.checkState(0) == Qt.CheckState.Checked:
                child_data = child.data(0, Qt.ItemDataRole.UserRole)
                if child_data and child_data.get('type') == target_type:
                    items.append(child_data.get('data'))
        return items
    
    def _collect_objects(self, parent: QTreeWidgetItem) -> Dict[str, List]:
        """Collect checked objects organized by type."""
        objects = {}
        
        for i in range(parent.childCount()):
            type_item = parent.child(i)
            type_data = type_item.data(0, Qt.ItemDataRole.UserRole)
            
            if type_data and type_data.get('type') == 'object_type':
                obj_type = type_data.get('object_type')
                objects[obj_type] = []
                
                for j in range(type_item.childCount()):
                    obj_item = type_item.child(j)
                    if obj_item.checkState(0) == Qt.CheckState.Checked:
                        obj_data = obj_item.data(0, Qt.ItemDataRole.UserRole)
                        if obj_data:
                            objects[obj_type].append(obj_data.get('data'))
        
        # Remove empty object types
        objects = {k: v for k, v in objects.items() if v}
        return objects
    
    def _collect_infrastructure(self, parent: QTreeWidgetItem) -> Dict[str, Any]:
        """Collect checked infrastructure items organized by type."""
        infrastructure = {}
        
        def collect_recursive(item, depth=0):
            """Recursively collect checked infrastructure items."""
            item_data = item.data(0, Qt.ItemDataRole.UserRole)
            indent = "  " * depth
            
            # Debug: Print item info
            item_text = item.text(0)
            check_state = item.checkState(0)
            print(f"{indent}Checking item: '{item_text}', CheckState: {check_state}")
            
            if item_data and item_data.get('type') == 'infrastructure':
                # This is an infrastructure item
                print(f"{indent}  -> Is infrastructure item")
                if item.checkState(0) == Qt.CheckState.Checked:
                    print(f"{indent}  -> Is CHECKED")
                    infra_type = item_data.get('infra_type')
                    data = item_data.get('data')
                    
                    print(f"{indent}  -> infra_type={infra_type}, has_data={data is not None}")
                    
                    if infra_type and data:
                        # Initialize list if needed
                        if infra_type not in infrastructure:
                            infrastructure[infra_type] = []
                        
                        # For lists, extend the list
                        if isinstance(data, list):
                            infrastructure[infra_type].extend(data)
                            print(f"{indent}  -> Extended list with {len(data)} items")
                        # For single items (dict), append to list
                        elif isinstance(data, dict):
                            infrastructure[infra_type].append(data)
                            print(f"{indent}  -> Appended dict item")
                        # For other types, store directly (e.g., Mobile Users settings)
                        else:
                            infrastructure[infra_type] = data
                            print(f"{indent}  -> Stored directly")
                else:
                    print(f"{indent}  -> NOT checked")
            
            # Check children
            for i in range(item.childCount()):
                collect_recursive(item.child(i), depth + 1)
        
        print(f"\nDEBUG: Starting _collect_infrastructure")
        # Start recursive collection from parent's children
        for i in range(parent.childCount()):
            collect_recursive(parent.child(i))
        
        print(f"DEBUG: _collect_infrastructure found {len(infrastructure)} types: {list(infrastructure.keys())}")
        return infrastructure
    
    def accept(self):
        """Override accept to add dependency analysis."""
        print("\n=== DEPENDENCY VALIDATION STARTING ===")
        
        # Get initially selected items
        selected = self.get_selected_items()
        
        print(f"Selected items summary:")
        print(f"  Folders: {len(selected.get('folders', []))}")
        print(f"  Snippets: {len(selected.get('snippets', []))}")
        print(f"  Objects: {sum(len(v) for v in selected.get('objects', {}).values() if isinstance(v, list))}")
        print(f"  Infrastructure: {sum(len(v) if isinstance(v, list) else 1 for v in selected.get('infrastructure', {}).values())}")
        
        # Check if anything is selected
        total = (len(selected.get('folders', [])) + 
                len(selected.get('snippets', [])) +
                sum(len(v) for v in selected.get('objects', {}).values() if isinstance(v, list)) +
                sum(len(v) if isinstance(v, list) else 1 for v in selected.get('infrastructure', {}).values()))
        
        if total == 0:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No Selection", "Please select at least one component.")
            return
        
        # Run dependency analysis
        try:
            from prisma.dependencies.dependency_resolver import DependencyResolver
            from gui.dialogs.dependency_confirmation_dialog import DependencyConfirmationDialog
            
            resolver = DependencyResolver()
            
            # Build config from selection for dependency analysis
            selected_config = {
                'security_policies': {
                    'folders': selected.get('folders', []),
                    'snippets': selected.get('snippets', [])
                },
                'objects': selected.get('objects', {}),
                'infrastructure': selected.get('infrastructure', {})
            }
            
            # Debug: Show what we're analyzing
            print(f"\nDEBUG: Selected config structure:")
            print(f"  Infrastructure types: {list(selected_config.get('infrastructure', {}).keys())}")
            for infra_type, items in selected_config.get('infrastructure', {}).items():
                if isinstance(items, list):
                    print(f"    {infra_type}: {len(items)} items")
                    for item in items:
                        print(f"      - {item.get('name', 'Unknown')}")
                else:
                    print(f"    {infra_type}: 1 item (dict)")
            
            # Find required dependencies
            required_deps = resolver.find_required_dependencies(selected_config, self.full_config)
            
            # Debug output
            print(f"\nDEBUG: Required dependencies found: {list(required_deps.keys())}")
            for key, value in required_deps.items():
                if isinstance(value, dict):
                    print(f"  {key}: {sum(len(v) for v in value.values() if isinstance(v, list))} items")
                    for subkey, subvalue in value.items():
                        if isinstance(subvalue, list):
                            print(f"    {subkey}: {len(subvalue)} items")
                elif isinstance(value, list):
                    print(f"  {key}: {len(value)} items")
            
            # Check if there are actually any dependencies (not just empty collections)
            has_deps = False
            if required_deps:
                has_deps = (
                    len(required_deps.get('folders', [])) > 0 or
                    len(required_deps.get('snippets', [])) > 0 or
                    sum(len(v) for v in required_deps.get('objects', {}).values() if isinstance(v, list)) > 0 or
                    len(required_deps.get('profiles', [])) > 0 or
                    sum(len(v) if isinstance(v, list) else 1 for v in required_deps.get('infrastructure', {}).values()) > 0
                )
            
            if has_deps:
                # Show dependency confirmation dialog
                dep_dialog = DependencyConfirmationDialog(required_deps, self)
                if not dep_dialog.exec():
                    # User cancelled
                    return
                
                # Add dependencies to selection
                selected = self._merge_dependencies(selected, required_deps)
                
                # Check the newly added dependencies in the tree
                self._check_merged_dependencies(required_deps)
                
                # Re-collect from tree to ensure checked items are included
                # (This ensures the GUI state matches the internal state)
                print("\nDEBUG: Re-collecting items from tree after checking dependencies")
                tree_selected = self.get_selected_items()
                print(f"  Tree has {len(tree_selected.get('infrastructure', {}))} infrastructure types after checking")
                
                # Merge tree selection with our already-merged selection
                # (This ensures we don't lose anything)
                selected = self._merge_dependencies(selected, tree_selected)
            else:
                print("\nDEBUG: No dependencies found - proceeding with original selection")
            
            # Store final selection
            self.selected_items = selected
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Dependency Analysis Error",
                f"Error analyzing dependencies:\n{str(e)}\n\nProceeding without dependency validation."
            )
            self.selected_items = selected
        
        # Call parent accept
        super().accept()
    
    def _merge_dependencies(self, selected: Dict[str, Any], required_deps: Dict[str, Any]) -> Dict[str, Any]:
        """Merge required dependencies into selection."""
        # Merge folders
        if 'folders' in required_deps:
            existing_names = {f.get('name') for f in selected.get('folders', [])}
            for folder in required_deps['folders']:
                if folder.get('name') not in existing_names:
                    selected.setdefault('folders', []).append(folder)
        
        # Merge snippets
        if 'snippets' in required_deps:
            existing_names = {s.get('name') for s in selected.get('snippets', [])}
            for snippet in required_deps['snippets']:
                if snippet.get('name') not in existing_names:
                    selected.setdefault('snippets', []).append(snippet)
        
        # Merge objects
        if 'objects' in required_deps:
            for obj_type, obj_list in required_deps['objects'].items():
                if obj_type not in selected.get('objects', {}):
                    selected.setdefault('objects', {})[obj_type] = []
                
                existing_names = {o.get('name') for o in selected['objects'][obj_type]}
                for obj in obj_list:
                    if obj.get('name') not in existing_names:
                        selected['objects'][obj_type].append(obj)
        
        # Merge profiles (add to folders if needed)
        if 'profiles' in required_deps:
            # For now, just add to a profiles list
            # In reality, profiles belong to folders
            selected['profiles'] = required_deps['profiles']
        
        # Merge infrastructure
        if 'infrastructure' in required_deps:
            for infra_type, infra_list in required_deps['infrastructure'].items():
                if infra_type not in selected.get('infrastructure', {}):
                    selected.setdefault('infrastructure', {})[infra_type] = []
                
                existing_names = {i.get('name', i.get('id')) for i in selected['infrastructure'][infra_type]}
                for item in infra_list:
                    item_name = item.get('name', item.get('id'))
                    if item_name not in existing_names:
                        selected['infrastructure'][infra_type].append(item)
        
        return selected
    
    def _check_merged_dependencies(self, required_deps: Dict[str, Any]):
        """Check items in the tree that were added as dependencies."""
        self.tree.blockSignals(True)
        
        try:
            # Helper to recursively find and check items by name and type
            def find_and_check_item(parent: QTreeWidgetItem, name: str, check_type: str) -> bool:
                """Recursively find and check an item."""
                for i in range(parent.childCount()):
                    item = parent.child(i)
                    item_data = item.data(0, Qt.ItemDataRole.UserRole)
                    
                    if item_data:
                        data = item_data.get('data', {})
                        item_type = item_data.get('type')
                        infra_type = item_data.get('infra_type')
                        item_name = data.get('name') if isinstance(data, dict) else None
                        
                        # Debug: Print what we're comparing
                        if check_type == 'infrastructure':
                            print(f"    Comparing: '{name}' with item_name='{item_name}', infra_type='{infra_type}', item_type='{item_type}'")
                        
                        # Check if this is the item we're looking for
                        if check_type == 'infrastructure' and item_type == 'infrastructure':
                            if data.get('name') == name:
                                print(f"    MATCH! Checking item: {name}")
                                item.setCheckState(0, Qt.CheckState.Checked)
                                # DON'T call _update_parent_check_state - it will uncheck the item!
                                # Parent state updates will happen naturally when user interacts
                                return True
                        elif item_type == check_type and data.get('name') == name:
                            item.setCheckState(0, Qt.CheckState.Checked)
                            # DON'T call _update_parent_check_state
                            return True
                    
                    # Recurse into children
                    if find_and_check_item(item, name, check_type):
                        return True
                
                return False
            
            # Check infrastructure dependencies
            if 'infrastructure' in required_deps:
                print(f"\nDEBUG: Checking infrastructure dependencies")
                for infra_type, items in required_deps['infrastructure'].items():
                    print(f"  Type: {infra_type}, Items type: {type(items)}, Count: {len(items) if isinstance(items, list) else 'N/A'}")
                    
                    if not isinstance(items, list):
                        print(f"  WARNING: {infra_type} is not a list, skipping")
                        continue
                    
                    for idx, item in enumerate(items):
                        if not isinstance(item, dict):
                            print(f"  WARNING: Item {idx} is not a dict: {type(item)} = {item}")
                            continue
                            
                        item_name = item.get('name', item.get('id'))
                        print(f"  Checking item: {item_name}")
                        if item_name:
                            # Find Infrastructure section
                            root = self.tree.invisibleRootItem()
                            for i in range(root.childCount()):
                                section = root.child(i)
                                if section.text(0) == "Infrastructure":
                                    find_and_check_item(section, item_name, 'infrastructure')
                                    break
            
            # Check snippet dependencies
            if 'snippets' in required_deps:
                for snippet in required_deps['snippets']:
                    snippet_name = snippet.get('name')
                    if snippet_name:
                        root = self.tree.invisibleRootItem()
                        for i in range(root.childCount()):
                            section = root.child(i)
                            if section.text(0) == "Security Policies":
                                find_and_check_item(section, snippet_name, 'snippet')
                                break
            
            # Check folder dependencies
            if 'folders' in required_deps:
                for folder in required_deps['folders']:
                    folder_name = folder.get('name')
                    if folder_name:
                        root = self.tree.invisibleRootItem()
                        for i in range(root.childCount()):
                            section = root.child(i)
                            if section.text(0) == "Security Policies":
                                find_and_check_item(section, folder_name, 'folder')
                                break
            
            # Check object dependencies
            if 'objects' in required_deps:
                for obj_type, obj_list in required_deps['objects'].items():
                    for obj in obj_list:
                        obj_name = obj.get('name')
                        if obj_name:
                            # Objects are under folders, need to find the right folder
                            folder_name = obj.get('folder')
                            if folder_name:
                                root = self.tree.invisibleRootItem()
                                for i in range(root.childCount()):
                                    section = root.child(i)
                                    if section.text(0) == "Security Policies":
                                        # Find the folder
                                        for j in range(section.childCount()):
                                            folders_section = section.child(j)
                                            if folders_section.text(0) == "Folders":
                                                find_and_check_item(folders_section, obj_name, 'folder_object')
                                                break
                                        break
        
        finally:
            self.tree.blockSignals(False)
    
    def _restore_selections(self):
        """Restore previously selected items in the tree."""
        print(f"DEBUG _restore_selections: Called!")
        print(f"  previous_selection is None? {self.previous_selection is None}")
        if self.previous_selection:
            print(f"  previous_selection keys: {list(self.previous_selection.keys())}")
        
        if not self.previous_selection:
            print(f"  Returning early - no previous selection")
            return
        
        self.tree.blockSignals(True)
        
        # Build sets of selected item names for quick lookup
        selected_folder_names = {f.get('name') for f in self.previous_selection.get('folders', [])}
        selected_snippet_names = {s.get('name') for s in self.previous_selection.get('snippets', [])}
        
        # For infrastructure, build a dict of {infra_type: set of item names}
        print(f"DEBUG _restore_selections: Starting infrastructure restoration")
        print(f"DEBUG: previous_selection.infrastructure keys: {list(self.previous_selection.get('infrastructure', {}).keys())}")
        selected_infra_items = {}
        try:
            for infra_type, items in self.previous_selection.get('infrastructure', {}).items():
                print(f"DEBUG: Processing infra_type={infra_type}, items type={type(items)}, count={len(items) if isinstance(items, (list, dict)) else '?'}")
                selected_infra_items[infra_type] = set()
                if isinstance(items, list):
                    for idx, item in enumerate(items):
                        print(f"  DEBUG: Item {idx}: type={type(item)}")
                        if isinstance(item, dict):
                            item_name = item.get('name') or item.get('id')
                            if item_name:
                                print(f"    Adding to selected_infra_items[{infra_type}]: {item_name}")
                                selected_infra_items[infra_type].add(item_name)
                        else:
                            print(f"    WARNING: Item is not a dict, it's {type(item)}")
                elif isinstance(items, dict):
                    # Single item (not a list)
                    print(f"  DEBUG: Single dict item")
                    item_name = items.get('name') or items.get('id')
                    if item_name:
                        print(f"    Adding to selected_infra_items[{infra_type}]: {item_name}")
                        selected_infra_items[infra_type].add(item_name)
                else:
                    print(f"  WARNING: items is neither list nor dict, it's {type(items)}")
            print(f"DEBUG: Built selected_infra_items: {selected_infra_items}")
        except Exception as e:
            print(f"ERROR building selected_infra_items: {e}")
            import traceback
            traceback.print_exc()
            selected_infra_items = {}
        
        # Recursively check items
        def restore_item(item: QTreeWidgetItem):
            try:
                print(f"DEBUG restore_item: Processing item '{item.text(0)}'")
                item_data = item.data(0, Qt.ItemDataRole.UserRole)
                print(f"  item_data: {type(item_data)}")
                
                if item_data:
                    item_type = item_data.get('type')
                    data = item_data.get('data', {})
                    print(f"  item_type: {item_type}, has data: {bool(data)}")
                    
                    # Check folders
                    if item_type == 'folder':
                        if data.get('name') in selected_folder_names:
                            # Check if this folder was fully selected or partially
                            prev_folder = next((f for f in self.previous_selection.get('folders', []) 
                                              if f.get('name') == data.get('name')), None)
                            if prev_folder:
                                # Check if it has selective contents or was fully selected
                                has_rules = 'security_rules' in prev_folder
                                has_objects = 'objects' in prev_folder
                                has_profiles = 'profiles' in prev_folder
                                has_hip = 'hip' in prev_folder
                                
                                if not (has_rules or has_objects or has_profiles or has_hip):
                                    # Fully selected - check the folder
                                    item.setCheckState(0, Qt.CheckState.Checked)
                                # If partial, we'll handle children below
                    
                    # Check security rules
                    elif item_type == 'security_rule':
                        folder_name = item_data.get('folder')
                        rule_name = data.get('name')
                        # Check if this rule was in the previous selection
                        for folder in self.previous_selection.get('folders', []):
                            if folder.get('name') == folder_name:
                                rules = folder.get('security_rules', [])
                                if any(r.get('name') == rule_name for r in rules):
                                    item.setCheckState(0, Qt.CheckState.Checked)
                    
                    # Check folder objects
                    elif item_type == 'folder_object':
                        folder_name = item_data.get('folder')
                        obj_type = item_data.get('object_type')
                        obj_name = data.get('name')
                        # Check if this object was in the previous selection
                        for folder in self.previous_selection.get('folders', []):
                            if folder.get('name') == folder_name:
                                objects = folder.get('objects', {}).get(obj_type, [])
                                if any(o.get('name') == obj_name for o in objects):
                                    item.setCheckState(0, Qt.CheckState.Checked)
                    
                    # Check folder profiles
                    elif item_type == 'folder_profile':
                        folder_name = item_data.get('folder')
                        prof_type = item_data.get('profile_type')
                        prof_name = data.get('name')
                        # Check if this profile was in the previous selection
                        for folder in self.previous_selection.get('folders', []):
                            if folder.get('name') == folder_name:
                                profiles = folder.get('profiles', {}).get(prof_type, [])
                                if any(p.get('name') == prof_name for p in profiles):
                                    item.setCheckState(0, Qt.CheckState.Checked)
                    
                    # Check snippets (item_data is the snippet itself, not wrapped)
                    elif not item_type and isinstance(item_data, dict) and item_data.get('name') in selected_snippet_names:
                        print(f"  SNIPPET CHECK MATCHED")
                        item.setCheckState(0, Qt.CheckState.Checked)
                    
                    # Check infrastructure
                    elif item_type == 'infrastructure':
                        print(f"DEBUG: ENTERED infrastructure elif block!")
                        infra_type = item_data.get('infra_type')
                        item_name = data.get('name', data.get('id'))
                        print(f"DEBUG restore_item: Checking infrastructure item '{item_name}' (infra_type={infra_type})")
                        
                        # Skip if item_name is None (container items like Mobile Users, Regions, etc.)
                        if item_name is None:
                            print(f"  Skipping - item_name is None (likely a container)")
                        elif infra_type in selected_infra_items:
                            print(f"  infra_type in selected_infra_items? True")
                            print(f"  item_name in selected_infra_items[{infra_type}]? {item_name in selected_infra_items[infra_type]}")
                            # Check if this specific infrastructure item is in the selection
                            if item_name in selected_infra_items[infra_type]:
                                print(f"  RESTORING: Checking item '{item_name}'")
                                item.setCheckState(0, Qt.CheckState.Checked)
                        else:
                            print(f"  infra_type NOT in selected_infra_items")
                    else:
                        print(f"  No matching elif for item_type='{item_type}'")
                    
                    # Check HIP items (stored directly in item_data)
                    # HIP items don't have a 'type' field, so check by parent structure
                    # This check runs independently after the main type-based checks
                    parent_item = item.parent()
                    if parent_item:
                        parent_text = parent_item.text(0)
                        grandparent = parent_item.parent()
                        if grandparent and grandparent.text(0) == "HIP":
                            # This is a HIP object or profile
                            # Find the folder this belongs to
                            folder_item = grandparent.parent()
                            if folder_item:
                                folder_name = folder_item.text(0)
                                item_name = item.text(0)
                                
                                # Check if this HIP item was in the previous selection
                                for folder in self.previous_selection.get('folders', []):
                                    if folder.get('name') == folder_name:
                                        hip_data = folder.get('hip', {})
                                        if "HIP Objects" in parent_text:
                                            hip_objects = hip_data.get('hip_objects', [])
                                            if any(obj.get('name') == item_name for obj in hip_objects):
                                                item.setCheckState(0, Qt.CheckState.Checked)
                                        elif "HIP Profiles" in parent_text:
                                            hip_profiles = hip_data.get('hip_profiles', [])
                                            if any(prof.get('name') == item_name for prof in hip_profiles):
                                                item.setCheckState(0, Qt.CheckState.Checked)
                
                # Recurse to children
                for i in range(item.childCount()):
                    restore_item(item.child(i))
            except Exception as e:
                print(f"ERROR in restore_item for '{item.text(0)}': {e}")
                import traceback
                traceback.print_exc()
        
        # Start restoration from top level
        print(f"DEBUG: Starting tree restoration loop")
        print(f"  Tree has {self.tree.topLevelItemCount()} top-level items")
        for i in range(self.tree.topLevelItemCount()):
            top_item = self.tree.topLevelItem(i)
            print(f"  Restoring top-level item {i}: {top_item.text(0)}")
            restore_item(top_item)
        
        # Update parent check states
        for i in range(self.tree.topLevelItemCount()):
            self._update_parent_states_recursive(self.tree.topLevelItem(i))
        
        self.tree.blockSignals(False)
        self._update_summary()
    
    def _update_parent_states_recursive(self, item: QTreeWidgetItem):
        """Recursively update parent check states from bottom up."""
        # First, update all children
        for i in range(item.childCount()):
            self._update_parent_states_recursive(item.child(i))
        
        # Then update this item if it has children
        if item.childCount() > 0:
            checked_count = 0
            partial_count = 0
            total_count = item.childCount()
            
            for i in range(total_count):
                child_state = item.child(i).checkState(0)
                if child_state == Qt.CheckState.Checked:
                    checked_count += 1
                elif child_state == Qt.CheckState.PartiallyChecked:
                    partial_count += 1
            
            if checked_count == 0 and partial_count == 0:
                item.setCheckState(0, Qt.CheckState.Unchecked)
            elif checked_count == total_count:
                item.setCheckState(0, Qt.CheckState.Checked)
            else:
                item.setCheckState(0, Qt.CheckState.PartiallyChecked)
