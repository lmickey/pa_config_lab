"""
Selection widget for choosing components to push.

This module provides the UI for selecting specific components 
(folders, snippets, objects) from the currently loaded configuration.
The selection UI is displayed directly on the page (not in a popup).
"""

import logging
from typing import Optional, Dict, Any, List
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QPushButton,
    QLabel,
    QMessageBox,
    QTreeWidget,
    QTreeWidgetItem,
    QCheckBox,
    QSplitter,
    QFrame,
)
from PyQt6.QtCore import pyqtSignal, Qt

from gui.config_tree_builder import ConfigTreeBuilder

logger = logging.getLogger(__name__)


class SelectionWidget(QWidget):
    """Widget for selecting components from loaded config to push."""
    
    # Signal emitted when selection is ready
    selection_ready = pyqtSignal(object)  # (selected_items)
    
    def __init__(self, parent=None):
        """Initialize the selection widget."""
        super().__init__(parent)
        
        self.current_config = None
        self.full_config = None  # For dependency resolution
        self.selected_items = None
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Title row with continue button
        title_row = QHBoxLayout()
        
        title = QLabel("<h2>Select Components to Push</h2>")
        title_row.addWidget(title)
        
        title_row.addStretch()
        
        # Continue to push button (top right)
        self.continue_btn = QPushButton("➡️ Continue to Push")
        self.continue_btn.setEnabled(False)
        self.continue_btn.setMinimumWidth(180)
        self.continue_btn.setFixedHeight(40)
        self.continue_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 10px 20px; font-size: 14px; font-weight: bold; border-radius: 5px; }"
            "QPushButton:hover { background-color: #45a049; }"
            "QPushButton:disabled { background-color: #BDBDBD; }"
        )
        self.continue_btn.clicked.connect(self._continue_to_push)
        title_row.addWidget(self.continue_btn)
        
        layout.addLayout(title_row)
        
        # Info text
        info = QLabel(
            "Select which components from the current configuration to push to the destination tenant."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # Selection controls row
        controls_layout = QHBoxLayout()
        
        self.select_all_check = QCheckBox("Select All")
        self.select_all_check.stateChanged.connect(self._on_select_all)
        self.select_all_check.setEnabled(False)
        controls_layout.addWidget(self.select_all_check)
        
        controls_layout.addStretch()
        
        expand_btn = QPushButton("Expand All")
        expand_btn.clicked.connect(self._expand_all)
        controls_layout.addWidget(expand_btn)
        
        collapse_btn = QPushButton("Collapse All")
        collapse_btn.clicked.connect(self._collapse_all)
        controls_layout.addWidget(collapse_btn)
        
        layout.addLayout(controls_layout)
        
        # Main tree widget for component selection
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Component", "Type", "Count"])
        self.tree.setColumnWidth(0, 400)
        self.tree.setColumnWidth(1, 150)
        self.tree.itemChanged.connect(self._on_item_changed)
        self.tree.setAlternatingRowColors(True)
        layout.addWidget(self.tree, stretch=1)
        
        # Selection summary at bottom
        self.summary_label = QLabel("Load a configuration first")
        self.summary_label.setStyleSheet(
            "color: gray; padding: 15px; background-color: #f5f5f5; border-radius: 5px;"
        )
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)
    
    def set_config(self, config: Dict[str, Any]):
        """Set the current configuration to work with."""
        self.current_config = config
        self.full_config = config  # Same for now, could be different for dependency resolution
        self.selected_items = None  # Reset selection
        
        if not config:
            self.tree.clear()
            self.summary_label.setText("⏳ No configuration loaded.\n\nGo to Pull or Review tab to load a configuration first.")
            self.summary_label.setStyleSheet(
                "color: gray; padding: 15px; background-color: #f5f5f5; border-radius: 5px;"
            )
            self.select_all_check.setEnabled(False)
            self.continue_btn.setEnabled(False)
            return
        
        # Populate the tree with config
        self._populate_tree()
        
        # Enable controls
        self.select_all_check.setEnabled(True)
        
        # Update summary
        self._update_summary()
    
    def _populate_tree(self):
        """Populate the tree with configuration components."""
        self.tree.blockSignals(True)
        self.tree.clear()
        
        # Use shared tree builder with checkboxes enabled and simplified structure
        builder = ConfigTreeBuilder(enable_checkboxes=True, simplified=True)
        builder.build_tree(self.tree, self.current_config)
        
        # Auto-expand top level and folders
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
                if self._uses_cie(data):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                    item.setForeground(0, Qt.GlobalColor.gray)
                    item.setToolTip(0, "⚠️ Cannot push: Profile depends on Cloud Identity Engine (CIE)")
                    item.setText(2, "CIE Dependency")
            
            # Check security rules for authentication profiles
            elif item_type == 'security_rule':
                auth_profile_name = data.get('authentication_profile')
                if auth_profile_name:
                    profile_data = self._find_auth_profile(auth_profile_name)
                    if profile_data and self._uses_cie(profile_data):
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                        item.setForeground(0, Qt.GlobalColor.gray)
                        item.setToolTip(0, f"⚠️ Cannot push: Rule uses authentication profile '{auth_profile_name}' which depends on CIE")
                        item.setText(2, "CIE Dependency")
        
        # Check children
        for i in range(item.childCount()):
            self._check_item_for_cie(item.child(i))
    
    def _uses_cie(self, profile: Dict) -> bool:
        """Check if authentication profile uses Cloud Identity Engine."""
        if profile.get('type') == 'cloud':
            return True
        if profile.get('cloud_authentication'):
            return True
        
        method = profile.get('method', {})
        if isinstance(method, dict):
            if 'cloud' in method:
                return True
            if method.get('cloud_authentication'):
                return True
        
        if 'cloud_identity_engine' in str(profile).lower():
            return True
        if 'cie' in str(profile.get('name', '')).lower():
            return True
        
        return False
    
    def _find_auth_profile(self, profile_name: str) -> Optional[Dict]:
        """Find an authentication profile by name across all folders."""
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
            self.summary_label.setText("⚠️ No components selected. Check items above to include them in the push.")
            self.summary_label.setStyleSheet(
                "color: #F57C00; padding: 15px; background-color: #FFF3E0; border-radius: 5px; border: 2px solid #FF9800;"
            )
            self.continue_btn.setEnabled(False)
        else:
            summary = f"✅ <b>Selected:</b> {total} items"
            parts = []
            if folders_count > 0:
                parts.append(f"{folders_count} folder{'s' if folders_count != 1 else ''}")
            if snippets_count > 0:
                parts.append(f"{snippets_count} snippet{'s' if snippets_count != 1 else ''}")
            if objects_count > 0:
                parts.append(f"{objects_count} object{'s' if objects_count != 1 else ''}")
            if infra_count > 0:
                parts.append(f"{infra_count} infrastructure")
            
            if parts:
                summary += f" ({', '.join(parts)})"
            
            self.summary_label.setText(summary)
            self.summary_label.setStyleSheet(
                "color: #2e7d32; padding: 15px; background-color: #e8f5e9; border-radius: 5px; border: 2px solid #4CAF50;"
            )
            self.continue_btn.setEnabled(True)
    
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
                count += self._count_checked_children_recursive(child)
            else:
                if child.checkState(0) == Qt.CheckState.Checked:
                    count += 1
        return count
    
    def _continue_to_push(self):
        """Validate selection and emit signal to continue to push tab."""
        if not self.current_config:
            QMessageBox.warning(self, "No Config", "Please load a configuration first")
            return
        
        # Get selected items from tree
        selected = self._get_selected_items()
        
        # Count total
        total = (len(selected.get('folders', [])) + 
                len(selected.get('snippets', [])) +
                sum(len(v) for v in selected.get('objects', {}).values() if isinstance(v, list)) +
                sum(len(v) if isinstance(v, list) else 1 for v in selected.get('infrastructure', {}).values()))
        
        if total == 0:
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
            
            # Find required dependencies
            required_deps = resolver.find_required_dependencies(selected_config, self.full_config)
            
            # Check if there are actually any dependencies
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
                    return  # User cancelled
                
                # Add dependencies to selection
                selected = self._merge_dependencies(selected, required_deps)
                
                # Check the newly added dependencies in the tree
                self._check_merged_dependencies(required_deps)
            
            # Store final selection
            self.selected_items = selected
            
            # Emit signal
            self.selection_ready.emit(self.selected_items)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(
                self,
                "Dependency Analysis Error",
                f"Error analyzing dependencies:\n{str(e)}\n\nProceeding without dependency validation."
            )
            self.selected_items = selected
            self.selection_ready.emit(self.selected_items)
    
    def _get_selected_items(self) -> Dict[str, Any]:
        """Get the selected items from the tree."""
        selected = {
            'folders': [],
            'snippets': [],
            'objects': {},
            'infrastructure': {}
        }
        
        for i in range(self.tree.topLevelItemCount()):
            top_item = self.tree.topLevelItem(i)
            section_name = top_item.text(0)
            
            if section_name == "Security Policies":
                for j in range(top_item.childCount()):
                    child = top_item.child(j)
                    child_name = child.text(0)
                    
                    if child_name == "Folders":
                        selected['folders'] = self._collect_folders_with_contents(child)
                    elif child_name == "Snippets":
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
                            if (rule_item.checkState(0) == Qt.CheckState.Checked and
                                rule_item.flags() & Qt.ItemFlag.ItemIsEnabled):
                                rule_data = rule_item.data(0, Qt.ItemDataRole.UserRole)
                                if rule_data:
                                    selected_rules.append(rule_data.get('data'))
                    
                    # Collect objects
                    elif content_name == "Objects":
                        for k in range(content_item.childCount()):
                            obj_type_item = content_item.child(k)
                            obj_type_data = obj_type_item.data(0, Qt.ItemDataRole.UserRole)
                            if obj_type_data and obj_type_data.get('type') == 'folder_object_type':
                                obj_type = obj_type_data.get('object_type')
                                for m in range(obj_type_item.childCount()):
                                    obj_item = obj_type_item.child(m)
                                    if (obj_item.checkState(0) == Qt.CheckState.Checked and
                                        obj_item.flags() & Qt.ItemFlag.ItemIsEnabled):
                                        obj_data = obj_item.data(0, Qt.ItemDataRole.UserRole)
                                        if obj_data:
                                            if obj_type not in selected_objects:
                                                selected_objects[obj_type] = []
                                            selected_objects[obj_type].append(obj_data.get('data'))
                    
                    # Collect profiles
                    elif content_name == "Profiles":
                        for k in range(content_item.childCount()):
                            prof_type_item = content_item.child(k)
                            prof_type_data = prof_type_item.data(0, Qt.ItemDataRole.UserRole)
                            if prof_type_data and prof_type_data.get('type') == 'folder_profile_type':
                                profile_type = prof_type_data.get('profile_type')
                                for m in range(prof_type_item.childCount()):
                                    profile_item = prof_type_item.child(m)
                                    if (profile_item.checkState(0) == Qt.CheckState.Checked and 
                                        profile_item.flags() & Qt.ItemFlag.ItemIsEnabled):
                                        profile_data = profile_item.data(0, Qt.ItemDataRole.UserRole)
                                        if profile_data:
                                            if profile_type not in selected_profiles:
                                                selected_profiles[profile_type] = []
                                            selected_profiles[profile_type].append(profile_data.get('data'))
                    
                    # Collect HIP
                    elif content_name == "HIP":
                        for k in range(content_item.childCount()):
                            hip_type_item = content_item.child(k)
                            hip_type_name = hip_type_item.text(0)
                            
                            for m in range(hip_type_item.childCount()):
                                hip_item = hip_type_item.child(m)
                                if (hip_item.checkState(0) == Qt.CheckState.Checked and
                                    hip_item.flags() & Qt.ItemFlag.ItemIsEnabled):
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
                
                # Only include folder if it has selected contents
                has_content = (
                    len(selected_rules) > 0 or
                    len(selected_objects) > 0 or
                    len(selected_profiles) > 0 or
                    len(selected_hip) > 0
                )
                
                if folder_item.checkState(0) == Qt.CheckState.Checked or has_content:
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
                    
                    folders.append(folder)
        
        return folders
    
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
                    if (obj_item.checkState(0) == Qt.CheckState.Checked and
                        obj_item.flags() & Qt.ItemFlag.ItemIsEnabled):
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
            item_data = item.data(0, Qt.ItemDataRole.UserRole)
            
            if item_data and item_data.get('type') == 'infrastructure':
                if (item.checkState(0) == Qt.CheckState.Checked and
                    item.flags() & Qt.ItemFlag.ItemIsEnabled):
                    infra_type = item_data.get('infra_type')
                    data = item_data.get('data')
                    
                    if infra_type and data:
                        if infra_type not in infrastructure:
                            infrastructure[infra_type] = []
                        
                        if isinstance(data, list):
                            infrastructure[infra_type].extend(data)
                        elif isinstance(data, dict):
                            infrastructure[infra_type].append(data)
                        else:
                            infrastructure[infra_type] = data
            
            for i in range(item.childCount()):
                collect_recursive(item.child(i), depth + 1)
        
        for i in range(parent.childCount()):
            collect_recursive(parent.child(i))
        
        return infrastructure
    
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
        
        # Merge profiles
        if 'profiles' in required_deps:
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
            def find_and_check_item(parent: QTreeWidgetItem, name: str, check_type: str) -> bool:
                for i in range(parent.childCount()):
                    item = parent.child(i)
                    item_data = item.data(0, Qt.ItemDataRole.UserRole)
                    
                    if item_data:
                        data = item_data.get('data', {})
                        item_type = item_data.get('type')
                        
                        if check_type == 'infrastructure' and item_type == 'infrastructure':
                            if data.get('name') == name:
                                item.setCheckState(0, Qt.CheckState.Checked)
                                return True
                        elif item_type == check_type and data.get('name') == name:
                            item.setCheckState(0, Qt.CheckState.Checked)
                            return True
                    
                    if find_and_check_item(item, name, check_type):
                        return True
                
                return False
            
            # Check infrastructure dependencies
            if 'infrastructure' in required_deps:
                for infra_type, items in required_deps['infrastructure'].items():
                    if not isinstance(items, list):
                        continue
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        item_name = item.get('name', item.get('id'))
                        if item_name:
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
        
        finally:
            self.tree.blockSignals(False)
