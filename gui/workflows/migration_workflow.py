"""
Configuration Migration Workflow GUI.

This module provides the UI for the configuration migration workflow
(pull/push between tenants).
"""

from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QLabel,
    QPushButton,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from gui.pull_widget import PullConfigWidget
from gui.config_viewer import ConfigViewerWidget
from gui.push_widget import PushConfigWidget


class MigrationWorkflowWidget(QWidget):
    """Widget for configuration migration workflow."""

    def __init__(self, parent=None):
        """Initialize migration workflow widget."""
        super().__init__(parent)

        self.api_client = None
        self.current_config = None

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QHBoxLayout(self)  # Changed to horizontal for sidebar

        # Left sidebar for saved configs
        from gui.saved_configs_sidebar import SavedConfigsSidebar
        self.saved_configs_sidebar = SavedConfigsSidebar()
        self.saved_configs_sidebar.setMaximumWidth(300)
        self.saved_configs_sidebar.config_loaded.connect(self._on_saved_config_loaded)
        layout.addWidget(self.saved_configs_sidebar)

        # Main content area
        main_content = QWidget()
        content_layout = QVBoxLayout(main_content)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Workflow steps
        steps_label = QLabel(
            "<b>Migration Steps:</b> "
            "1️⃣ Pull from Source → 2️⃣ View & Analyze → 3️⃣ Push to Target"
        )
        steps_label.setWordWrap(True)
        steps_label.setStyleSheet(
            "padding: 10px; background-color: #e8f5e9; border-radius: 5px;"
        )
        content_layout.addWidget(steps_label)

        # Tabs for workflow steps
        self.tabs = QTabWidget()

        # Pull tab
        self.pull_widget = PullConfigWidget()
        self.pull_widget.pull_completed.connect(self._on_pull_completed)
        self.tabs.addTab(self.pull_widget, "1️⃣ Pull from SCM")

        # View tab - with save button
        viewer_container = QWidget()
        viewer_layout = QVBoxLayout(viewer_container)
        
        self.config_viewer = ConfigViewerWidget()
        viewer_layout.addWidget(self.config_viewer)
        
        # Add save button to viewer tab
        save_btn_layout = QHBoxLayout()
        save_btn_layout.addStretch()
        
        save_viewer_btn = QPushButton("💾 Save Current Config")
        save_viewer_btn.setStyleSheet(
            "QPushButton { background-color: #FF9800; color: white; padding: 10px 20px; font-weight: bold; }"
            "QPushButton:hover { background-color: #F57C00; }"
        )
        save_viewer_btn.clicked.connect(self._save_current_config)
        save_btn_layout.addWidget(save_viewer_btn)
        
        viewer_layout.addLayout(save_btn_layout)
        
        self.tabs.addTab(viewer_container, "2️⃣ Review Configuration")

        # Push tab
        self.push_widget = PushConfigWidget()
        self.push_widget.push_completed.connect(self._on_push_completed)
        self.tabs.addTab(self.push_widget, "3️⃣ Push to Target")

        content_layout.addWidget(self.tabs)

        # Add main content to layout
        layout.addWidget(main_content)

    def set_api_client(self, api_client):
        """Set API client for all widgets."""
        self.api_client = api_client
        self.pull_widget.set_api_client(api_client)
        self.push_widget.set_api_client(api_client)

    def _on_pull_completed(self, config):
        """Handle pull completion."""
        self.current_config = config
        self.config_viewer.set_config(config)
        self.push_widget.set_config(config)

        # Move to view tab
        self.tabs.setCurrentIndex(1)

    def _on_push_completed(self, result):
        """Handle push completion."""
        QMessageBox.information(
            self,
            "Push Complete",
            "Configuration migration completed successfully!",
        )

    def _save_current_config(self):
        """Save the current configuration to saved configs."""
        # Get config from viewer's internal storage
        config = self.config_viewer.current_config
        
        if not config:
            QMessageBox.information(
                self,
                "No Configuration",
                "Please pull a configuration first."
            )
            return
        
        # Generate default name
        default_name = config.get("metadata", {}).get("source_tenant", "")
        if not default_name:
            from datetime import datetime
            default_name = f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        success = self.saved_configs_sidebar.save_current_config(
            config,
            default_name=default_name,
            encrypt=True
        )
        
        if success:
            QMessageBox.information(
                self,
                "Saved",
                f"Configuration saved as '{default_name}'"
            )

    def _auto_save_pulled_config(self, config: Dict[str, Any]):
        """Automatically prompt to save pulled configuration."""
        if not config:
            return
        
        # Generate default filename based on TSG and date
        tsg_id = config.get("metadata", {}).get("source_tenant", "unknown")
        from datetime import datetime
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"pulled_{tsg_id}_{date_str}"
        
        # Prompt user to save
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Save Configuration?",
            f"Would you like to save the pulled configuration?\n\n"
            f"Suggested name: {default_name}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Save unencrypted for quick access (user can encrypt later if needed)
            success = self.saved_configs_sidebar.save_current_config(
                config,
                default_name=default_name,
                encrypt=False  # Quick save without encryption
            )
            
            if success:
                QMessageBox.information(
                    self,
                    "Saved",
                    f"Configuration saved as '{default_name}'"
                )

    def _on_saved_config_loaded(self, config: Dict[str, Any]):
        """Handle when a saved configuration is loaded from sidebar."""
        # Store as current config
        self.current_config = config
        
        # Load into viewer
        self.config_viewer.set_config(config)
        
        # Load into push widget (for migration workflow)
        self.push_widget.set_config(config)
        
        # Switch to review tab to show loaded config
        self.tabs.setCurrentIndex(1)
        
        # Show success message
        source_name = config.get("metadata", {}).get("saved_name", "saved config")
        QMessageBox.information(
            self,
            "Configuration Loaded",
            f"Configuration '{source_name}' loaded successfully.\n\n"
            f"Viewing in the Review tab."
        )

    def set_api_client(self, client):
        """Set API client for pull/push operations."""
        self.api_client = client
        self.pull_widget.set_api_client(client)
        self.push_widget.set_api_client(client)
