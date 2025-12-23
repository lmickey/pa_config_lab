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
            folders_item = QTreeWidgetItem(self.tree, ["Folders", "Security Policy", f"{len(folders)} required"])
            folders_item.setExpanded(True)
            
            for folder in folders:
                name = folder.get('name', 'Unknown')
                QTreeWidgetItem(folders_item, [name, "Folder", "Required by rules"])
            
            total_count += len(folders)
        
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
