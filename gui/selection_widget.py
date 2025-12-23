"""
Selection widget for choosing components to push.

This module provides the UI for selecting specific components 
(folders, snippets, objects) from the currently loaded configuration.
"""

from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QPushButton,
    QLabel,
    QMessageBox,
)
from PyQt6.QtCore import pyqtSignal


class SelectionWidget(QWidget):
    """Widget for selecting components from loaded config to push."""
    
    # Signal emitted when selection is ready
    selection_ready = pyqtSignal(object)  # (selected_items)
    
    def __init__(self, parent=None):
        """Initialize the selection widget."""
        super().__init__(parent)
        
        self.current_config = None
        self.selected_items = None
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("<h2>Select Components to Push</h2>")
        layout.addWidget(title)
        
        info = QLabel(
            "Select which components from the current configuration to push to the destination tenant."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 20px;")
        layout.addWidget(info)
        
        # Component selection (removed "Current Configuration" section per user request)
        selection_group = QGroupBox("Select Components")
        selection_layout = QVBoxLayout()
        
        # Selection summary
        self.selection_summary_label = QLabel("Load a configuration first")
        self.selection_summary_label.setStyleSheet(
            "color: gray; padding: 15px; background-color: #f5f5f5; border-radius: 5px;"
        )
        self.selection_summary_label.setWordWrap(True)
        selection_layout.addWidget(self.selection_summary_label)
        
        # Select components button
        select_btn_layout = QHBoxLayout()
        select_btn_layout.addStretch()
        
        self.select_components_btn = QPushButton("📋 Select Components...")
        self.select_components_btn.setEnabled(False)
        self.select_components_btn.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; padding: 12px 24px; font-size: 14px; font-weight: bold; }"
            "QPushButton:hover { background-color: #1976D2; }"
            "QPushButton:disabled { background-color: #BDBDBD; }"
        )
        self.select_components_btn.clicked.connect(self._select_components)
        select_btn_layout.addWidget(self.select_components_btn)
        select_btn_layout.addStretch()
        
        selection_layout.addLayout(select_btn_layout)
        
        selection_group.setLayout(selection_layout)
        layout.addWidget(selection_group)
        
        layout.addStretch()
        
        # Continue to push button (bottom right corner)
        continue_btn_layout = QHBoxLayout()
        continue_btn_layout.addStretch()
        
        self.continue_btn = QPushButton("➡️ Continue to Push")
        self.continue_btn.setEnabled(False)
        self.continue_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 12px 24px; font-size: 14px; font-weight: bold; }"
            "QPushButton:hover { background-color: #45a049; }"
            "QPushButton:disabled { background-color: #BDBDBD; }"
        )
        self.continue_btn.clicked.connect(self._continue_to_push)
        continue_btn_layout.addWidget(self.continue_btn)
        
        layout.addLayout(continue_btn_layout)
    
    def set_config(self, config: Dict[str, Any]):
        """Set the current configuration to work with."""
        self.current_config = config
        self.selected_items = None  # Reset selection
        
        if not config:
            self.selection_summary_label.setText("⏳ No configuration loaded.\n\nGo to Pull or Review tab to load a configuration first.")
            self.selection_summary_label.setStyleSheet(
                "color: gray; padding: 15px; background-color: #f5f5f5; border-radius: 5px;"
            )
            self.select_components_btn.setEnabled(False)
            self.continue_btn.setEnabled(False)
            return
        
        # Config is loaded - show selection prompt
        self.selection_summary_label.setText(
            "📋 Click 'Select Components' to choose which items to push"
        )
        self.selection_summary_label.setStyleSheet(
            "color: #1565C0; padding: 15px; background-color: #E3F2FD; border-radius: 5px; border: 2px solid #2196F3;"
        )
        
        self.select_components_btn.setEnabled(True)
    
    def _select_components(self):
        """Open dialog to select components to push."""
        if not self.current_config:
            QMessageBox.warning(self, "No Config", "Please load a configuration first")
            return
        
        # Open component selection dialog
        from gui.dialogs.component_selection_dialog import ComponentSelectionDialog
        
        # Pass current_config, full_config, and previous selection to restore
        dialog = ComponentSelectionDialog(
            self.current_config, 
            self.current_config, 
            previous_selection=self.selected_items,
            parent=self
        )
        if dialog.exec():
            # Get selected items (now includes dependencies)
            self.selected_items = dialog.get_selected_items()
        else:
            # User cancelled - keep existing selection
            return
        
        # Count selected items
        folders_count = len(self.selected_items.get('folders', []))
        snippets_count = len(self.selected_items.get('snippets', []))
        
        objects = self.selected_items.get('objects', {})
        objects_count = sum(len(v) for v in objects.values() if isinstance(v, list))
        
        infrastructure = self.selected_items.get('infrastructure', {})
        infra_count = sum(len(v) for v in infrastructure.values() if isinstance(v, list))
        
        total = folders_count + snippets_count + objects_count + infra_count
        
        if total == 0:
            self.selection_summary_label.setText(
                "⚠️ No components selected. Click 'Select Components' to choose items."
            )
            self.selection_summary_label.setStyleSheet(
                "color: #F57C00; padding: 15px; background-color: #FFF3E0; border-radius: 5px; border: 2px solid #FF9800;"
            )
            self.continue_btn.setEnabled(False)
            return
        
        # Build summary with selection details
        summary = f"✅ <b>Selection Complete - Ready to Push</b><br><br>"
        summary += f"<b>Total Selected:</b> {total} items<br>"
        if folders_count > 0:
            summary += f"• {folders_count} folder{'s' if folders_count != 1 else ''}<br>"
        if snippets_count > 0:
            summary += f"• {snippets_count} snippet{'s' if snippets_count != 1 else ''}<br>"
        if objects_count > 0:
            summary += f"• {objects_count} object{'s' if objects_count != 1 else ''}<br>"
        if infra_count > 0:
            summary += f"• {infra_count} infrastructure component{'s' if infra_count != 1 else ''}<br>"
        summary += f"<br>Click 'Continue to Push' to proceed to the push configuration."
        
        self.selection_summary_label.setText(summary)
        self.selection_summary_label.setStyleSheet(
            "color: #2e7d32; padding: 15px; background-color: #e8f5e9; border-radius: 5px; border: 2px solid #4CAF50;"
        )
        
        self.continue_btn.setEnabled(True)
    
    def _continue_to_push(self):
        """Emit signal to continue to push tab with selection."""
        if self.current_config and self.selected_items:
            self.selection_ready.emit(self.selected_items)
        else:
            QMessageBox.warning(
                self,
                "Not Ready",
                "Please select components first."
            )
