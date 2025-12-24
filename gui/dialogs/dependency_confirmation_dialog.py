"""
Dependency confirmation dialog.

Shows users which dependencies will be automatically added to their selection.
"""

from typing import Dict, Any
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
    QLabel,
    QDialogButtonBox,
)
from PyQt6.QtCore import Qt


class DependencyConfirmationDialog(QDialog):
    """Dialog to confirm automatic dependency inclusion."""
    
    def __init__(self, required_deps: Dict[str, Any], parent=None):
        """Initialize the dependency confirmation dialog.
        
        Args:
            required_deps: Dictionary of required dependencies by type
            parent: Parent widget
        """
        super().__init__(parent)
        self.required_deps = required_deps
        
        self.setWindowTitle("Dependencies Required")
        self.resize(700, 500)
        
        self._init_ui()
        self._populate_tree()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("<h2>⚠️ Dependencies Required</h2>")
        layout.addWidget(header)
        
        info = QLabel(
            "The selected components require the following dependencies to function correctly.\n"
            "These items will be automatically added to your selection."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #F57C00; padding: 10px; background-color: #FFF3E0; border-radius: 5px; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # Tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Component", "Type", "Reason"])
        self.tree.setColumnWidth(0, 300)
        self.tree.setColumnWidth(1, 150)
        layout.addWidget(self.tree)
        
        # Summary
        self.summary_label = QLabel()
        self.summary_label.setStyleSheet(
            "padding: 10px; background-color: #E3F2FD; border-radius: 5px; font-weight: bold;"
        )
        layout.addWidget(self.summary_label)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # Style the OK button
        ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        ok_button.setText("✓ Add Dependencies")
        ok_button.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 8px 16px; font-weight: bold; }"
            "QPushButton:hover { background-color: #45a049; }"
        )
        
        cancel_button = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_button.setText("✗ Cancel Selection")
        
        layout.addWidget(button_box)
    
    def _populate_tree(self):
        """Populate the tree with required dependencies."""
        total_count = 0
        
        # Add folders
        folders = self.required_deps.get('folders', [])
        if folders:
            # Count total items in all folders
            folder_item_count = 0
            for folder in folders:
                objects = folder.get('objects', {})
                profiles = folder.get('profiles', {})
                rules = folder.get('security_rules', [])
                hip = folder.get('hip', {})
                
                folder_item_count += len(rules)
                folder_item_count += sum(len(v) for v in objects.values() if isinstance(v, list))
                folder_item_count += len(profiles.get('authentication_profiles', []))
                folder_item_count += sum(len(v) for v in profiles.get('security_profiles', {}).values() if isinstance(v, list))
                folder_item_count += len(profiles.get('decryption_profiles', []))
                folder_item_count += len(hip.get('hip_objects', []))
                folder_item_count += len(hip.get('hip_profiles', []))
            
            folders_item = QTreeWidgetItem(self.tree, ["Folders", "Security Policy", f"{folder_item_count} items in {len(folders)} folder(s)"])
            folders_item.setExpanded(True)
            
            for folder in folders:
                folder_name = folder.get('name', 'Unknown')
                folder_item = QTreeWidgetItem(folders_item, [folder_name, "Folder", ""])
                folder_item.setExpanded(True)
                
                # Add objects from this folder
                objects = folder.get('objects', {})
                if objects:
                    for obj_type, obj_list in objects.items():
                        if isinstance(obj_list, list) and obj_list:
                            type_name = obj_type.replace('_', ' ').title()
                            type_item = QTreeWidgetItem(folder_item, [type_name, f"{len(obj_list)} items", "Required by rules/groups"])
                            
                            for obj in obj_list:
                                obj_name = obj.get('name', 'Unknown')
                                QTreeWidgetItem(type_item, [f"  {obj_name}", obj_type.replace('_', ' '), ""])
                
                # Add profiles from this folder
                profiles = folder.get('profiles', {})
                if profiles:
                    # Authentication profiles
                    auth_profiles = profiles.get('authentication_profiles', [])
                    if auth_profiles:
                        auth_item = QTreeWidgetItem(folder_item, ["Authentication Profiles", f"{len(auth_profiles)} items", "Required by rules"])
                        for prof in auth_profiles:
                            prof_name = prof.get('name', 'Unknown')
                            QTreeWidgetItem(auth_item, [f"  {prof_name}", "authentication", ""])
                    
                    # Security profiles
                    sec_profiles = profiles.get('security_profiles', {})
                    if sec_profiles:
                        for prof_type, prof_list in sec_profiles.items():
                            if isinstance(prof_list, list) and prof_list:
                                type_name = prof_type.replace('_', ' ').title()
                                sec_item = QTreeWidgetItem(folder_item, [type_name, f"{len(prof_list)} items", "Required by rules/groups"])
                                for prof in prof_list:
                                    prof_name = prof.get('name', 'Unknown')
                                    QTreeWidgetItem(sec_item, [f"  {prof_name}", prof_type, ""])
                    
                    # Decryption profiles
                    dec_profiles = profiles.get('decryption_profiles', [])
                    if dec_profiles:
                        dec_item = QTreeWidgetItem(folder_item, ["Decryption Profiles", f"{len(dec_profiles)} items", "Required by rules"])
                        for prof in dec_profiles:
                            prof_name = prof.get('name', 'Unknown')
                            QTreeWidgetItem(dec_item, [f"  {prof_name}", "decryption", ""])
                
                # Add HIP from this folder
                hip = folder.get('hip', {})
                if hip:
                    hip_objects = hip.get('hip_objects', [])
                    if hip_objects:
                        hip_obj_item = QTreeWidgetItem(folder_item, ["HIP Objects", f"{len(hip_objects)} items", "Required by HIP profiles"])
                        for obj in hip_objects:
                            obj_name = obj.get('name', 'Unknown')
                            QTreeWidgetItem(hip_obj_item, [f"  {obj_name}", "hip_object", ""])
                    
                    hip_profiles = hip.get('hip_profiles', [])
                    if hip_profiles:
                        hip_prof_item = QTreeWidgetItem(folder_item, ["HIP Profiles", f"{len(hip_profiles)} items", "Required by rules"])
                        for prof in hip_profiles:
                            prof_name = prof.get('name', 'Unknown')
                            QTreeWidgetItem(hip_prof_item, [f"  {prof_name}", "hip_profile", ""])
                
                # Add rules from this folder
                rules = folder.get('security_rules', [])
                if rules:
                    rules_item = QTreeWidgetItem(folder_item, ["Security Rules", f"{len(rules)} items", ""])
                    for rule in rules:
                        rule_name = rule.get('name', 'Unknown')
                        QTreeWidgetItem(rules_item, [f"  {rule_name}", "security_rule", ""])
            
            total_count += folder_item_count
        
        # Add snippets
        snippets = self.required_deps.get('snippets', [])
        if snippets:
            snippets_item = QTreeWidgetItem(self.tree, ["Snippets", "Security Policy", f"{len(snippets)} required"])
            snippets_item.setExpanded(True)
            
            for snippet in snippets:
                name = snippet.get('name', 'Unknown')
                QTreeWidgetItem(snippets_item, [name, "Snippet", "Required by policy"])
            
            total_count += len(snippets)
        
        # Add objects
        objects = self.required_deps.get('objects', {})
        if objects:
            objects_count = sum(len(v) for v in objects.values() if isinstance(v, list))
            objects_item = QTreeWidgetItem(self.tree, ["Objects", "Configuration", f"{objects_count} required"])
            objects_item.setExpanded(True)
            
            for obj_type, obj_list in objects.items():
                if isinstance(obj_list, list) and obj_list:
                    type_item = QTreeWidgetItem(
                        objects_item,
                        [obj_type.replace('_', ' ').title(), "Object Type", f"{len(obj_list)} items"]
                    )
                    
                    for obj in obj_list:
                        name = obj.get('name', 'Unknown')
                        QTreeWidgetItem(type_item, [name, obj_type, "Referenced by rules/groups"])
            
            total_count += objects_count
        
        # Add profiles
        profiles = self.required_deps.get('profiles', [])
        if profiles:
            profiles_item = QTreeWidgetItem(self.tree, ["Profiles", "Security", f"{len(profiles)} required"])
            profiles_item.setExpanded(True)
            
            for profile in profiles:
                name = profile.get('name', 'Unknown')
                profile_type = profile.get('type', 'Unknown')
                QTreeWidgetItem(profiles_item, [name, profile_type, "Required by rules"])
            
            total_count += len(profiles)
        
        # Add infrastructure
        infrastructure = self.required_deps.get('infrastructure', {})
        if infrastructure:
            infra_count = sum(len(v) for v in infrastructure.values() if isinstance(v, list))
            infra_item = QTreeWidgetItem(self.tree, ["Infrastructure", "Configuration", f"{infra_count} required"])
            infra_item.setExpanded(True)
            
            for infra_type, infra_list in infrastructure.items():
                if isinstance(infra_list, list) and infra_list:
                    type_item = QTreeWidgetItem(
                        infra_item,
                        [infra_type.replace('_', ' ').title(), "Infrastructure", f"{len(infra_list)} items"]
                    )
                    
                    for item in infra_list:
                        name = item.get('name', item.get('id', 'Unknown'))
                        QTreeWidgetItem(type_item, [name, infra_type, "Required by connections"])
            
            total_count += infra_count
        
        # Update summary
        self.summary_label.setText(
            f"📊 Total: {total_count} dependencies will be added to your selection"
        )
