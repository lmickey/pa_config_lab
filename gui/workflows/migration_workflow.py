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
    
    # Signal emitted when configuration is loaded/pulled (dict format)
    configuration_loaded = pyqtSignal(object)  # Emits dict config

    def __init__(self, parent=None):
        """Initialize migration workflow widget."""
        super().__init__(parent)

        self.api_client = None
        self.current_config = None

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)  # Changed back to vertical layout
        layout.setContentsMargins(0, 0, 0, 0)

        # Workflow steps
        steps_label = QLabel(
            "<b>Migration Steps:</b> "
            "1️⃣ Pull from Source → 2️⃣ View & Analyze → 3️⃣ Push to Target<br/>"
            "<i>Or use File → Load Configuration to load a saved config</i>"
        )
        steps_label.setWordWrap(True)
        steps_label.setStyleSheet(
            "padding: 10px; background-color: #e8f5e9; border-radius: 5px;"
        )
        layout.addWidget(steps_label)

        # Tabs for workflow steps
        self.tabs = QTabWidget()

        # Pull tab
        self.pull_widget = PullConfigWidget()
        # Use QueuedConnection to ensure signal is handled in main thread
        from PyQt6.QtCore import Qt
        self.pull_widget.pull_completed.connect(
            self._on_pull_completed,
            Qt.ConnectionType.QueuedConnection
        )
        self.tabs.addTab(self.pull_widget, "1️⃣ Pull from SCM")

        # View tab - with save button
        viewer_container = QWidget()
        viewer_layout = QVBoxLayout(viewer_container)
        
        self.config_viewer = ConfigViewerWidget()
        viewer_layout.addWidget(self.config_viewer)
        
        # Add buttons to viewer tab
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        save_viewer_btn = QPushButton("💾 Save Current Config")
        save_viewer_btn.setStyleSheet(
            "QPushButton { background-color: #FF9800; color: white; padding: 10px 20px; font-weight: bold; }"
            "QPushButton:hover { background-color: #F57C00; }"
        )
        save_viewer_btn.clicked.connect(self._save_current_config)
        buttons_layout.addWidget(save_viewer_btn)
        
        # Add "Next" button to go to selection tab
        next_btn = QPushButton("➡️ Select Config to Push")
        next_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 10px 20px; font-weight: bold; }"
            "QPushButton:hover { background-color: #45a049; }"
        )
        next_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(2))  # Go to selection tab
        buttons_layout.addWidget(next_btn)
        
        viewer_layout.addLayout(buttons_layout)
        
        self.tabs.addTab(viewer_container, "2️⃣ Review Configuration")

        # Selection tab (Phase 3)
        from gui.selection_widget import SelectionWidget
        self.selection_widget = SelectionWidget()
        self.selection_widget.selection_ready.connect(self._on_selection_ready)
        self.tabs.addTab(self.selection_widget, "3️⃣ Select Components")

        # Push tab
        self.push_widget = PushConfigWidget()
        self.push_widget.push_completed.connect(self._on_push_completed)
        self.tabs.addTab(self.push_widget, "4️⃣ Push to Target")

        layout.addWidget(self.tabs)
        
        # Populate tenant dropdowns from saved tenants
        self._populate_tenant_dropdowns()

    def _populate_tenant_dropdowns(self):
        """Populate source and destination tenant dropdowns with saved tenants."""
        try:
            from config.tenant_manager import TenantManager
            
            tenant_mgr = TenantManager()
            tenants = tenant_mgr.list_tenants()
            
            # Populate pull widget source dropdown
            if hasattr(self.pull_widget, 'populate_source_tenants'):
                self.pull_widget.populate_source_tenants(tenants)
            
            # Populate push widget destination dropdown
            if hasattr(self.push_widget, 'populate_destination_tenants'):
                # Convert tenant list to format expected by push widget
                tenant_list = [{"name": t.get('name'), "data": t} for t in tenants]
                self.push_widget.populate_destination_tenants(tenant_list)
                
        except Exception as e:
            # Silently fail if tenants can't be loaded
            pass
    
    def has_unsaved_work(self) -> bool:
        """
        Check if workflow has unsaved work that would be lost on switch.
        
        Returns:
            True if there is unsaved work, False otherwise
        """
        # Check if there's a pulled config that hasn't been saved
        if self.current_config is not None:
            return True
        
        # Check if there's an active connection
        if self.api_client is not None:
            return True
        
        # Check if push widget has selections or loaded config
        if hasattr(self.push_widget, 'loaded_config') and self.push_widget.loaded_config is not None:
            return True
        
        if hasattr(self.push_widget, 'selected_items') and self.push_widget.selected_items is not None:
            return True
        
        return False
    
    def clear_state(self):
        """Clear all workflow state when switching workflows."""
        # Clear current config
        self.current_config = None
        
        # Clear API client
        self.api_client = None
        
        # Clear pull widget
        if hasattr(self.pull_widget, 'api_client'):
            self.pull_widget.set_api_client(None)
            self.pull_widget.pulled_config = None
        
        # Clear config viewer
        if hasattr(self.config_viewer, 'set_config'):
            self.config_viewer.set_config(None)
        
        # Clear selection widget
        if hasattr(self.selection_widget, 'set_config'):
            self.selection_widget.set_config(None)
        
        # Clear push widget
        if hasattr(self.push_widget, 'set_config'):
            self.push_widget.set_config(None)
        if hasattr(self.push_widget, 'loaded_config'):
            self.push_widget.loaded_config = None
        if hasattr(self.push_widget, 'selected_items'):
            self.push_widget.selected_items = None
        if hasattr(self.push_widget, 'destination_client'):
            self.push_widget.destination_client = None
        if hasattr(self.push_widget, 'destination_name'):
            self.push_widget.destination_name = None
        
        # Reset to first tab
        self.tabs.setCurrentIndex(0)

    def set_api_client(self, api_client, connection_name=None):
        """Set API client for all widgets."""
        self.api_client = api_client
        self.connection_name = connection_name  # Store for use in save dialog
        self.pull_widget.set_api_client(api_client, connection_name)
        self.push_widget.set_api_client(api_client)

    def _on_pull_completed(self, config):
        """Handle pull completion."""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("=== _on_pull_completed called ===")
        logger.info(f"Config parameter type: {type(config)}")
        logger.info(f"Config parameter value: {config is not None}")
        
        # Get config from pull_widget instead of signal parameter to avoid memory issues
        # The signal parameter is now None to prevent memory corruption
        config_from_widget = self.pull_widget.get_pulled_config()
        logger.info(f"Config from widget: {config_from_widget is not None}")
        
        if config:
            logger.info(f"Using config from signal parameter (size: {len(str(config))} bytes)")
            self.current_config = config
            self.config_viewer.set_config(config)
            self.push_widget.set_config(config)
            self.selection_widget.set_config(config)  # Phase 3: Update selection widget
            
            # Notify main window that config is loaded
            self.configuration_loaded.emit(config)

            # Move to view tab
            logger.info("Switching to view tab (index 1)")
            self.tabs.setCurrentIndex(1)
        elif config_from_widget:
            logger.info(f"Using config from widget (size: {len(str(config_from_widget))} bytes)")
            self.current_config = config_from_widget
            self.config_viewer.set_config(config_from_widget)
            self.push_widget.set_config(config_from_widget)
            self.selection_widget.set_config(config_from_widget)
            
            # Notify main window that config is loaded
            self.configuration_loaded.emit(config_from_widget)

            # Move to view tab
            logger.info("Switching to view tab (index 1)")
            self.tabs.setCurrentIndex(1)
        else:
            logger.error("No config available from either signal or widget!")

    def _on_push_completed(self, result):
        """Handle push completion."""
        # Status is already shown in push_widget banner, no popup needed
        pass

    def _save_current_config(self):
        """Save the current configuration using the save dialog."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Get config from viewer's internal storage (dict format)
        config_dict = self.config_viewer.current_config
        
        logger.info(f"Save button clicked - config is: {config_dict is not None}")
        
        if not config_dict:
            logger.warning("No configuration loaded when trying to save")
            QMessageBox.information(
                self,
                "No Configuration",
                "Please pull a configuration first."
            )
            return
        
        # Get the Configuration object from main window if available
        main_window = self.window()
        config_obj = getattr(main_window, 'current_config', None)
        
        if not config_obj:
            # Try to convert dict to Configuration object
            logger.info("Converting config dict to Configuration object for save")
            try:
                from config.models.containers import Configuration, FolderConfig, SnippetConfig
                from config.models.factory import ConfigItemFactory
                
                config_obj = Configuration()
                
                # Copy metadata from dict
                metadata = config_dict.get('metadata', {})
                config_obj.source_tsg = metadata.get('source_tsg')
                config_obj.source_tenant = metadata.get('source_tenant')
                config_obj.source_config = metadata.get('source_config')
                config_obj.load_type = metadata.get('load_type')
                config_obj.saved_credentials_ref = metadata.get('saved_credentials_ref')
                config_obj.created_at = metadata.get('created_at')
                config_obj.modified_at = metadata.get('modified_at')
                
                # Process folders
                for folder_name, folder_data in config_dict.get('folders', {}).items():
                    folder_config = FolderConfig(folder_name)
                    if isinstance(folder_data, dict):
                        for item_type, items in folder_data.items():
                            if isinstance(items, list):
                                for item_dict in items:
                                    try:
                                        item = ConfigItemFactory.create_from_dict(item_type, item_dict)
                                        folder_config.add_item(item)
                                    except Exception as e:
                                        logger.warning(f"Error creating folder item: {e}")
                    config_obj.add_folder(folder_config)
                
                # Process snippets
                for snippet_name, snippet_data in config_dict.get('snippets', {}).items():
                    snippet_config = SnippetConfig(snippet_name)
                    if isinstance(snippet_data, dict):
                        for item_type, items in snippet_data.items():
                            if isinstance(items, list):
                                for item_dict in items:
                                    try:
                                        item = ConfigItemFactory.create_from_dict(item_type, item_dict)
                                        snippet_config.add_item(item)
                                    except Exception as e:
                                        logger.warning(f"Error creating snippet item: {e}")
                    config_obj.add_snippet(snippet_config)
                
                # Process infrastructure
                infra_data = config_dict.get('infrastructure', {})
                if isinstance(infra_data, dict):
                    if 'items' in infra_data and isinstance(infra_data['items'], list):
                        for item_dict in infra_data['items']:
                            try:
                                item_type = item_dict.get('item_type', 'unknown')
                                item = ConfigItemFactory.create_from_dict(item_type, item_dict)
                                config_obj.infrastructure.add_item(item)
                            except Exception as e:
                                logger.warning(f"Error creating infrastructure item: {e}")
                    else:
                        for item_type, items in infra_data.items():
                            if isinstance(items, list):
                                for item_dict in items:
                                    try:
                                        item = ConfigItemFactory.create_from_dict(item_type, item_dict)
                                        config_obj.infrastructure.add_item(item)
                                    except Exception as e:
                                        logger.warning(f"Error creating infrastructure item: {e}")
                
            except Exception as e:
                logger.error(f"Failed to convert config: {e}")
                QMessageBox.warning(
                    self,
                    "Save Error",
                    f"Failed to prepare configuration for saving: {e}"
                )
                return
        
        # Open the save dialog
        try:
            from gui.dialogs.save_config_dialog import SaveConfigDialog
            
            # Generate default name from source tenant/TSG
            default_name = ""
            if hasattr(config_obj, 'source_tenant') and config_obj.source_tenant:
                default_name = config_obj.source_tenant
            elif hasattr(config_obj, 'source_tsg') and config_obj.source_tsg:
                default_name = f"TSG-{config_obj.source_tsg}"
            
            dialog = SaveConfigDialog(config_obj, self, default_name=default_name)
            if dialog.exec():
                logger.info("Configuration saved successfully via save dialog")
                QMessageBox.information(
                    self,
                    "Save Successful",
                    "Configuration saved successfully!"
                )
        except Exception as e:
            logger.error(f"Error opening save dialog: {e}")
            QMessageBox.warning(
                self,
                "Save Error",
                f"Failed to save configuration: {e}"
            )
    
    def load_configuration_from_main(self, config):
        """
        Load configuration from main window File→Load.
        
        Args:
            config: Configuration object from main window
        """
        # Store Configuration object
        self.current_config = config
        
        # Convert to dict format for widgets using ConfigAdapter
        from gui.config_adapter import ConfigAdapter
        config_dict = ConfigAdapter.to_dict(config)
        
        # Load into all widgets
        self.config_viewer.set_config(config_dict)
        self.push_widget.set_config(config_dict)
        self.selection_widget.set_config(config_dict)
        
        # Switch to review tab to show loaded config
        self.tabs.setCurrentIndex(1)

    def _auto_save_pulled_config(self, config: Dict[str, Any]):
        """Automatically prompt to save pulled configuration."""
        if not config:
            return
        
        # Generate default filename based on connection name (tenant name) instead of TSG
        connection_name = getattr(self, 'connection_name', None)
        if not connection_name or connection_name == "Manual":
            # Fall back to TSG
            connection_name = config.get("metadata", {}).get("source_tenant", "unknown")
        
        from datetime import datetime
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"pulled_{connection_name}_{date_str}"
        
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
        """Handle when a saved configuration is loaded (legacy - no longer used)."""
        pass
    
    def _on_selection_ready(self, selected_items):
        """Handle when selection is ready from selection widget."""
        # Set the selection in push widget (config already set)
        self.push_widget.set_selected_items(selected_items)
        
        # Switch to push tab
        self.tabs.setCurrentIndex(3)  # Push is now tab 3 (0-indexed)
