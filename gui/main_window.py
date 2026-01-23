"""
Main GUI Application - Multi-Function Configuration Manager.

This module provides the main window with support for multiple workflows:
1. POV Configuration - Configure new POV environments
2. Configuration Migration - Pull/push between tenants
3. Future workflows - Extensible architecture
"""

import sys
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QStatusBar,
    QMessageBox,
    QFileDialog,
    QStackedWidget,
    QListWidget,
)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QAction, QIcon

from gui.connection_dialog import ConnectionDialog
from gui.logs_widget import LogsWidget
from gui.settings_dialog import SettingsDialog
from gui.dialogs import SaveConfigDialog, LoadConfigDialog, ExportConfigDialog
from gui.widgets.workflow_lock import WorkflowLockManager


class PrismaConfigMainWindow(QMainWindow):
    """Main window for Prisma Access Configuration Manager - Multi-function."""

    def __init__(self):
        """Initialize the main window."""
        super().__init__()

        self.settings = QSettings("PrismaAccess", "ConfigManager")
        self.api_client = None
        self.current_config = None
        
        # Initialize workflow lock manager
        self.workflow_lock = WorkflowLockManager.instance()

        self._ensure_saved_folder()
        self._init_ui()
        self._restore_window_state()
    
    def _ensure_saved_folder(self):
        """Ensure the saved folder exists."""
        import os
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        saved_path = os.path.join(base_path, "saved")
        os.makedirs(saved_path, exist_ok=True)

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Prisma Access Configuration Manager")
        self.setMinimumSize(1400, 900)

        # Create menu bar
        self._create_menu_bar()

        # Create central widget with workflow selector
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        # Left sidebar - Workflow selector
        sidebar = QWidget()
        sidebar.setMaximumWidth(250)
        sidebar.setStyleSheet("QWidget { background-color: #f5f5f5; }")
        sidebar_layout = QVBoxLayout(sidebar)

        sidebar_title = QLabel("<h3>Workflows</h3>")
        sidebar_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(sidebar_title)

        self.workflow_list = QListWidget()
        self.workflow_list.addItem("🏠 Home")
        self.workflow_list.addItem("🔧 POV Configuration")
        self.workflow_list.addItem("🔄 Configuration Migration")
        self.workflow_list.addItem("📊 Activity Logs")
        sidebar_layout.addWidget(self.workflow_list)

        sidebar_layout.addStretch()

        # Connection status in sidebar
        sidebar_layout.addWidget(QLabel("<b>Connection Status:</b>"))
        self.connection_status = QLabel("Not Connected")
        self.connection_status.setStyleSheet("color: gray; padding: 5px;")
        self.connection_status.setWordWrap(True)
        sidebar_layout.addWidget(self.connection_status)

        main_layout.addWidget(sidebar)

        # Right side - Stacked widget for different workflows
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # Create workflow pages
        self._create_home_page()
        self._create_pov_workflow_page()
        self._create_migration_workflow_page()
        self._create_logs_page()

        # Now connect the signal after everything is initialized
        self.workflow_list.currentRowChanged.connect(self._on_workflow_changed)
        self.workflow_list.setCurrentRow(0)

        # Set up GUI logging after logs widget is created
        from gui.gui_logger import setup_gui_logging
        self._original_stdout, self._original_stderr = setup_gui_logging(self.logs_widget)

        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - Select a workflow to begin")

    def _create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        # Save Configuration (new dialog)
        save_config_action = QAction("&Save Configuration...", self)
        save_config_action.setShortcut("Ctrl+S")
        save_config_action.setStatusTip("Save current configuration with encryption")
        save_config_action.triggered.connect(self._save_configuration_file)
        file_menu.addAction(save_config_action)

        # Load Configuration (new dialog)
        load_config_action = QAction("&Load Configuration...", self)
        load_config_action.setShortcut("Ctrl+O")
        load_config_action.setStatusTip("Load configuration from saved files")
        load_config_action.triggered.connect(self._load_configuration_file)
        file_menu.addAction(load_config_action)

        # Resume POV Deployment
        resume_pov_action = QAction("&Resume POV Deployment...", self)
        resume_pov_action.setShortcut("Ctrl+R")
        resume_pov_action.setStatusTip("Resume a saved POV deployment workflow")
        resume_pov_action.triggered.connect(self._resume_pov_deployment)
        file_menu.addAction(resume_pov_action)

        file_menu.addSeparator()

        # Export Configuration (new)
        export_config_action = QAction("&Export Configuration...", self)
        export_config_action.setShortcut("Ctrl+E")
        export_config_action.setStatusTip("Export configuration to custom location")
        export_config_action.triggered.connect(self._export_configuration)
        file_menu.addAction(export_config_action)

        file_menu.addSeparator()

        # Recent Configurations submenu
        self.recent_menu = file_menu.addMenu("Recent Configurations")
        self._update_recent_menu()

        file_menu.addSeparator()

        # Configuration Info
        config_info_action = QAction("Configuration &Info...", self)
        config_info_action.setShortcut("Ctrl+I")
        config_info_action.setStatusTip("View configuration metadata")
        config_info_action.triggered.connect(self._show_configuration_info)
        file_menu.addAction(config_info_action)

        file_menu.addSeparator()

        connect_action = QAction("&Connect to API...", self)
        connect_action.setShortcut("Ctrl+N")
        connect_action.setStatusTip("Connect to Prisma Access API")
        connect_action.triggered.connect(self._show_connection_dialog)
        file_menu.addAction(connect_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("Exit application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        
        tenants_action = QAction("&Manage Tenants...", self)
        tenants_action.setShortcut("Ctrl+T")
        tenants_action.setStatusTip("Manage saved tenant credentials")
        tenants_action.triggered.connect(self._show_tenant_manager)
        tools_menu.addAction(tenants_action)
        
        tools_menu.addSeparator()

        settings_action = QAction("&Settings...", self)
        settings_action.setStatusTip("Application settings")
        settings_action.triggered.connect(self._show_settings)
        tools_menu.addAction(settings_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        docs_action = QAction("&Documentation", self)
        docs_action.setShortcut("F1")
        docs_action.setStatusTip("Open documentation")
        docs_action.triggered.connect(self._show_documentation)
        help_menu.addAction(docs_action)

        about_action = QAction("&About", self)
        about_action.setStatusTip("About this application")
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_home_page(self):
        """Create the home/dashboard page."""
        home = QWidget()
        layout = QVBoxLayout(home)

        # Welcome
        welcome = QLabel("<h1>Prisma Access Configuration Manager</h1>")
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(welcome)

        tagline = QLabel(
            "<p style='font-size: 14px; color: gray;'>"
            "Comprehensive tool for Prisma Access configuration management</p>"
        )
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tagline)

        layout.addStretch()

        # Workflow cards
        workflows_label = QLabel("<h2>Select a Workflow</h2>")
        workflows_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(workflows_label)

        cards_layout = QHBoxLayout()
        cards_layout.addStretch()

        # POV Configuration card
        pov_card = self._create_workflow_card(
            "🔧 POV Configuration",
            "Configure new POV environments\n"
            "• Load from SCM/Terraform/JSON\n"
            "• Configure firewall settings\n"
            "• Set up service connections\n"
            "• Deploy to NGFW and Prisma Access",
            lambda: self.workflow_list.setCurrentRow(1),
        )
        cards_layout.addWidget(pov_card)

        # Migration card
        migration_card = self._create_workflow_card(
            "🔄 Configuration Migration",
            "Migrate configurations between tenants\n"
            "• Pull from source tenant\n"
            "• View and analyze\n"
            "• Detect conflicts\n"
            "• Push to target tenant",
            lambda: self.workflow_list.setCurrentRow(2),
        )
        cards_layout.addWidget(migration_card)

        cards_layout.addStretch()
        layout.addLayout(cards_layout)

        layout.addStretch()

        # Quick actions
        actions_label = QLabel("<h3>Quick Actions</h3>")
        actions_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(actions_label)

        actions_layout = QHBoxLayout()
        actions_layout.addStretch()

        connect_btn = QPushButton("Connect to Prisma Access API")
        connect_btn.setMinimumSize(220, 50)
        connect_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #2196F3; color: white; padding: 10px 20px; "
            "  font-size: 14px; font-weight: bold; border-radius: 5px; "
            "  border: 1px solid #1976D2; border-bottom: 3px solid #1565C0; "
            "}"
            "QPushButton:hover { background-color: #1E88E5; border-bottom: 3px solid #0D47A1; }"
            "QPushButton:pressed { background-color: #1976D2; border-bottom: 1px solid #1565C0; }"
        )
        connect_btn.clicked.connect(self._show_connection_dialog)
        actions_layout.addWidget(connect_btn)

        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        layout.addStretch()

        self.stacked_widget.addWidget(home)

    def _create_workflow_card(self, title: str, description: str, on_click) -> QWidget:
        """Create a workflow card."""
        card = QPushButton()
        card.setMinimumSize(300, 200)
        card.setStyleSheet(
            """
            QPushButton {
                background-color: white;
                border: 2px solid #ddd;
                border-radius: 10px;
                text-align: left;
                padding: 20px;
            }
            QPushButton:hover {
                background-color: #f0f8ff;
                border: 2px solid #4CAF50;
            }
        """
        )

        card.setText(f"{title}\n\n{description}")
        card.clicked.connect(on_click)

        return card

    def _create_pov_workflow_page(self):
        """Create the POV configuration workflow page."""
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("<h2>🔧 POV Configuration Workflow</h2>")
        layout.addWidget(title)

        subtitle = QLabel(
            "Configure a new POV (Proof of Value) environment for Prisma Access.\n"
            "This workflow guides you through setting up a complete POV deployment."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: gray; margin-bottom: 20px;")
        layout.addWidget(subtitle)

        # Import POV workflow module
        from gui.workflows.pov_workflow import POVWorkflowWidget

        self.pov_workflow = POVWorkflowWidget()
        layout.addWidget(self.pov_workflow)

        self.stacked_widget.addWidget(page)

    def _create_migration_workflow_page(self):
        """Create the configuration migration workflow page."""
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("<h2>🔄 Configuration Migration Workflow</h2>")
        layout.addWidget(title)

        subtitle = QLabel(
            "Migrate configurations between Prisma Access tenants.\n"
            "Pull from source, analyze, and push to target with conflict resolution."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: gray; margin-bottom: 20px;")
        layout.addWidget(subtitle)

        # Import migration workflow module
        from gui.workflows.migration_workflow import MigrationWorkflowWidget

        self.migration_workflow = MigrationWorkflowWidget()
        
        # Connect signal to update main window's current_config
        self.migration_workflow.configuration_loaded.connect(self._on_config_loaded_from_workflow)
        
        # Connect signal to update connection status in sidebar
        self.migration_workflow.connection_changed.connect(self._on_workflow_connection_changed)
        
        # Connect signal to handle load file request from workflow
        self.migration_workflow.load_file_requested.connect(self._load_configuration_file)
        
        layout.addWidget(self.migration_workflow)

        self.stacked_widget.addWidget(page)

    def _create_logs_page(self):
        """Create the logs and monitoring page."""
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("<h2>📊 Logs & Monitoring</h2>")
        layout.addWidget(title)

        self.logs_widget = LogsWidget()
        layout.addWidget(self.logs_widget)

        self.stacked_widget.addWidget(page)

    def _on_workflow_changed(self, index: int):
        """Handle workflow selection change with confirmation if work in progress."""
        # Get current workflow index before switching
        current_index = self.stacked_widget.currentIndex()
        
        # If switching to same workflow, do nothing
        if current_index == index:
            return
        
        # Check if workflow is locked (operation in progress)
        if self.workflow_lock.is_locked():
            # Revert selection first
            self.workflow_list.blockSignals(True)
            self.workflow_list.setCurrentRow(current_index)
            self.workflow_list.blockSignals(False)
            
            # Show warning and optionally allow cancellation
            if not self.workflow_lock.request_switch(self):
                return  # User chose not to cancel or cancel failed
        
        # Check if current workflow has unsaved work
        current_widget = self.stacked_widget.widget(current_index)
        if hasattr(current_widget, 'has_unsaved_work') and current_widget.has_unsaved_work():
            # Prompt for confirmation
            reply = QMessageBox.question(
                self,
                'Confirm Workflow Switch',
                'You have work in progress. Switching workflows will clear all current selections, '
                'loaded configurations, and connection states.\n\n'
                'Are you sure you want to continue?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No  # Default to No for safety
            )
            
            if reply == QMessageBox.StandardButton.No:
                # User cancelled - revert selection
                self.workflow_list.blockSignals(True)
                self.workflow_list.setCurrentRow(current_index)
                self.workflow_list.blockSignals(False)
                return
        
        # Clear state of current workflow before switching
        if hasattr(current_widget, 'clear_state'):
            try:
                current_widget.clear_state()
            except Exception as e:
                # Log error but continue with switch
                import logging
                logging.getLogger(__name__).warning(f"Error clearing workflow state: {e}")
        
        workflow_names = [
            "Home",
            "POV Configuration",
            "Configuration Migration",
            "Logs & Monitoring",
        ]
        
        # Log the workflow switch
        import logging
        logger = logging.getLogger(__name__)
        if index < len(workflow_names):
            logger.normal(f"[Navigation] Switched to: {workflow_names[index]}")
        
        # Switch to new workflow
        self.stacked_widget.setCurrentIndex(index)

        if index < len(workflow_names):
            # Use statusBar() method instead of status_bar attribute
            self.statusBar().showMessage(f"Switched to: {workflow_names[index]}")

    # Action handlers

    def _show_connection_dialog(self):
        """Show the connection dialog."""
        from PyQt6.QtCore import QCoreApplication
        
        try:
            dialog = ConnectionDialog(self)
            result = dialog.exec()
            
            # Process events to ensure dialog is fully closed
            QCoreApplication.processEvents()
            
            if result:
                # Get data before dialog is deleted
                self.api_client = dialog.get_api_client()
                connection_name = dialog.get_connection_name() or "Manual"

                # Delete dialog explicitly
                dialog.deleteLater()
                QCoreApplication.processEvents()

                if self.api_client:
                    tsg_id = self.api_client.tsg_id
                    
                    # Update UI with tenant name instead of TSG
                    self.connection_status.setText(f"✓ Connected\n{connection_name}")
                    self.connection_status.setStyleSheet("color: green; padding: 5px;")

                    self.statusBar().showMessage(f"Connected to {connection_name} ({tsg_id})", 5000)

                    # Update workflows with connection name
                    self.migration_workflow.set_api_client(self.api_client, connection_name)
                    self.pov_workflow.set_api_client(self.api_client, connection_name)

                    # Log connection
                    self.logs_widget.log(f"Connected to {connection_name} (TSG: {tsg_id})", "success")
            else:
                # Dialog cancelled
                dialog.deleteLater()
                QCoreApplication.processEvents()
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Connection Error",
                f"Error during connection:\n\n{str(e)}\n\nPlease check the console for details."
            )
    
    def _on_workflow_connection_changed(self, api_client, tenant_name: str, source_type: str):
        """Handle connection changes from workflow widgets (pull/push tenant selectors)."""
        if api_client and tenant_name:
            # Update connection status in sidebar
            source_label = "Pull" if source_type == "pull" else "Push"
            self.connection_status.setText(f"✓ {source_label}: {tenant_name}")
            self.connection_status.setStyleSheet("color: green; padding: 5px;")
            
            # Update status bar
            tsg_id = api_client.tsg_id if hasattr(api_client, 'tsg_id') else "Unknown"
            self.statusBar().showMessage(f"{source_label} connected to {tenant_name} ({tsg_id})", 5000)
            
            # Log connection
            self.logs_widget.log(f"{source_label} connected to {tenant_name}", "success")
        else:
            # Disconnected
            self.connection_status.setText("Not Connected")
            self.connection_status.setStyleSheet("color: gray; padding: 5px;")

    def _show_tenant_manager(self):
        """Show tenant manager dialog."""
        from gui.dialogs.tenant_manager_dialog import TenantManagerDialog
        
        dialog = TenantManagerDialog(self)
        dialog.exec()
    
    def _show_settings(self):
        """Show settings dialog."""
        dialog = SettingsDialog(self)
        dialog.exec()

    def _show_documentation(self):
        """Show documentation."""
        QMessageBox.information(
            self,
            "Documentation",
            "Documentation is available in the docs/ directory:\n\n"
            "• GUI_USER_GUIDE.md - GUI usage guide\n"
            "• PULL_PUSH_GUIDE.md - Migration workflow\n"
            "• API_REFERENCE.md - Technical reference\n"
            "• TROUBLESHOOTING.md - Common issues",
        )

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Prisma Access Configuration Manager",
            "<h2>Prisma Access Configuration Manager</h2>"
            "<p>Version 3.1.0</p>"
            "<p>A comprehensive multi-function tool for Prisma Access:</p>"
            "<p><b>Workflows:</b></p>"
            "<ul>"
            "<li><b>POV Configuration:</b> Set up new POV environments</li>"
            "<li><b>Configuration Migration:</b> Clone/migrate between tenants</li>"
            "<li><b>Logs & Monitoring:</b> Track all operations</li>"
            "</ul>"
            "<p><b>New in 3.1:</b></p>"
            "<ul>"
            "<li>5-level logging system (ERROR/WARNING/NORMAL/INFO/DEBUG)</li>"
            "<li>Configuration save/load with compression</li>"
            "<li>Enhanced orchestrators with dependency management</li>"
            "<li>Comprehensive metadata tracking</li>"
            "</ul>"
        )
    
    def _load_configuration_file(self):
        """Load configuration from file using new dialog."""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.normal("[Config] Opening configuration file dialog...")
        
        dialog = LoadConfigDialog(self)
        if dialog.exec() == LoadConfigDialog.DialogCode.Accepted:
            config_data = dialog.get_config()
            metadata = dialog.get_metadata()
            
            if config_data:
                try:
                    config_name = metadata.get('name', 'Configuration') if metadata else 'Configuration'
                    logger.normal(f"[Config] Loading configuration: {config_name}")
                    
                    # Log what's in the config
                    folders_count = len(config_data.get('folders', {}))
                    snippets_count = len(config_data.get('snippets', {}))
                    infra_data = config_data.get('infrastructure', {})
                    infra_count = len(infra_data.get('items', [])) if 'items' in infra_data else sum(
                        len(v) for v in infra_data.values() if isinstance(v, list)
                    )
                    
                    logger.normal(f"[Config] File contains: {folders_count} folders, {snippets_count} snippets, {infra_count} infrastructure items")
                    
                    # Convert to Configuration object
                    logger.detail(f"[Config] Converting to Configuration object...")
                    config = self._convert_dict_to_configuration(config_data, logger)
                    self.current_config = config
                    
                    # Log detailed counts
                    total_folder_items = sum(len(f.items) for f in config.folders.values())
                    total_snippet_items = sum(len(s.items) for s in config.snippets.values())
                    
                    logger.normal(f"[Config] Loaded successfully:")
                    logger.normal(f"[Config]   Folders: {len(config.folders)} ({total_folder_items} items)")
                    for folder_name, folder in config.folders.items():
                        if folder.items:
                            logger.detail(f"[Config]     📁 {folder_name}: {len(folder.items)} items")
                    
                    logger.normal(f"[Config]   Snippets: {len(config.snippets)} ({total_snippet_items} items)")
                    for snippet_name, snippet in config.snippets.items():
                        if snippet.items:
                            logger.detail(f"[Config]     📄 {snippet_name}: {len(snippet.items)} items")
                    
                    logger.normal(f"[Config]   Infrastructure: {len(config.infrastructure.items)} items")
                    
                    self.status_bar.showMessage(f"Loaded: {config_name}")
                    
                    # Update the workflow with loaded config
                    logger.detail(f"[Config] Updating workflow with loaded configuration...")
                    self._update_workflow_with_config(self.current_config)
                    
                    logger.normal(f"[Config] Configuration '{config_name}' ready for use")
                    
                except Exception as e:
                    logger.error(f"[Config] Failed to process loaded config: {e}", exc_info=True)
                    QMessageBox.critical(
                        self,
                        "Load Error",
                        f"Failed to process configuration:\n\n{str(e)}"
                    )
        else:
            logger.detail("[Config] Configuration load cancelled by user")

    def _resume_pov_deployment(self):
        """Open the Resume POV Deployment dialog."""
        # Switch to POV Builder workflow if not already active
        if hasattr(self, 'workflow_selector'):
            # Find the POV Builder option
            for i in range(self.workflow_selector.count()):
                if "POV" in self.workflow_selector.itemText(i):
                    self.workflow_selector.setCurrentIndex(i)
                    break

        # Get the current workflow widget
        current_widget = self.stacked_widget.currentWidget()

        # Check if it has the resume dialog method
        if hasattr(current_widget, '_show_resume_pov_dialog'):
            current_widget._show_resume_pov_dialog()
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "POV Builder Required",
                "Please switch to the POV Builder workflow to resume a POV deployment."
            )

    def _convert_dict_to_configuration(self, config_data: dict, logger=None):
        """
        Convert a configuration dictionary to a Configuration object.
        
        Handles both formats:
        - New format: folders/snippets contain {item_type: [items]}
        - Legacy format: folders/snippets contain {"items": [...], "parent": ...}
        
        Args:
            config_data: Configuration dictionary
            logger: Optional logger instance
            
        Returns:
            Configuration object
        """
        if logger is None:
            import logging
            logger = logging.getLogger(__name__)
        
        from config.models.containers import Configuration, FolderConfig, SnippetConfig
        from config.models.factory import ConfigItemFactory
        
        config = Configuration()
        
        # Copy metadata
        metadata = config_data.get('metadata', {})
        config.source_tsg = metadata.get('source_tsg')
        config.source_tenant = metadata.get('source_tenant')
        config.source_config = metadata.get('source_config') or metadata.get('source_file')  # Backwards compat
        config.load_type = metadata.get('load_type', 'From File')
        config.saved_credentials_ref = metadata.get('saved_credentials_ref')
        config.created_at = metadata.get('created_at')
        config.modified_at = metadata.get('modified_at')
        config.program_version = config_data.get('program_version', Configuration.PROGRAM_VERSION)
        config.config_version = config_data.get('config_version', 1)
        
        # Process folders
        for folder_name, folder_data in config_data.get('folders', {}).items():
            folder_config = FolderConfig(folder_name)
            
            if isinstance(folder_data, dict):
                # Check for legacy format {"items": [...], "parent": ...}
                if 'items' in folder_data and isinstance(folder_data['items'], list):
                    # Legacy format - items is a flat list
                    folder_config.parent = folder_data.get('parent')
                    for item_dict in folder_data['items']:
                        try:
                            item_type = item_dict.get('item_type', 'unknown')
                            item = ConfigItemFactory.create_from_dict(item_type, item_dict)
                            folder_config.add_item(item)
                        except Exception as e:
                            logger.warning(f"Error creating folder item: {e}")
                else:
                    # New format - items grouped by type {item_type: [items]}
                    for item_type, items in folder_data.items():
                        if item_type == 'parent':
                            folder_config.parent = items
                            continue
                        if isinstance(items, list):
                            for item_dict in items:
                                try:
                                    item = ConfigItemFactory.create_from_dict(item_type, item_dict)
                                    folder_config.add_item(item)
                                except Exception as e:
                                    logger.warning(f"Error creating folder item ({item_type}): {e}")
            
            config.add_folder(folder_config)
        
        # Process snippets
        for snippet_name, snippet_data in config_data.get('snippets', {}).items():
            snippet_config = SnippetConfig(snippet_name)
            
            if isinstance(snippet_data, dict):
                # Check for legacy format {"items": [...]}
                if 'items' in snippet_data and isinstance(snippet_data['items'], list):
                    # Legacy format
                    for item_dict in snippet_data['items']:
                        try:
                            item_type = item_dict.get('item_type', 'unknown')
                            item = ConfigItemFactory.create_from_dict(item_type, item_dict)
                            snippet_config.add_item(item)
                        except Exception as e:
                            logger.warning(f"Error creating snippet item: {e}")
                else:
                    # New format
                    for item_type, items in snippet_data.items():
                        if isinstance(items, list):
                            for item_dict in items:
                                try:
                                    item = ConfigItemFactory.create_from_dict(item_type, item_dict)
                                    snippet_config.add_item(item)
                                except Exception as e:
                                    logger.warning(f"Error creating snippet item ({item_type}): {e}")
            
            config.add_snippet(snippet_config)
        
        # Process infrastructure
        infra_data = config_data.get('infrastructure', {})
        logger.info(f"Processing infrastructure - data type: {type(infra_data)}, keys: {list(infra_data.keys()) if isinstance(infra_data, dict) else 'N/A'}")
        
        if isinstance(infra_data, dict):
            # Check for legacy format {"items": [...]}
            if 'items' in infra_data and isinstance(infra_data['items'], list):
                # Legacy format
                items_list = infra_data['items']
                logger.info(f"  Legacy format: {len(items_list)} infrastructure items to process")
                for item_dict in items_list:
                    try:
                        item_type = item_dict.get('item_type', 'unknown')
                        item = ConfigItemFactory.create_from_dict(item_type, item_dict)
                        config.infrastructure.add_item(item)
                    except Exception as e:
                        logger.warning(f"Error creating infrastructure item ({item_type}): {e}")
                logger.info(f"  Loaded {len(config.infrastructure.items)} infrastructure items")
            else:
                # New format - items grouped by type
                logger.info(f"  New format: infrastructure grouped by type")
                for item_type, items in infra_data.items():
                    if isinstance(items, list):
                        logger.debug(f"    Processing {item_type}: {len(items)} items")
                        for item_dict in items:
                            try:
                                item = ConfigItemFactory.create_from_dict(item_type, item_dict)
                                config.infrastructure.add_item(item)
                            except Exception as e:
                                logger.warning(f"Error creating infrastructure item ({item_type}): {e}")
                logger.info(f"  Loaded {len(config.infrastructure.items)} infrastructure items")
        else:
            logger.warning(f"  Infrastructure data is not a dict: {type(infra_data)}")
        
        logger.info(f"Converted configuration: {len(config.folders)} folders, {len(config.snippets)} snippets, {len(config.infrastructure.items)} infrastructure items")
        return config
    
    def _save_configuration_file(self):
        """Save current configuration to file using new dialog."""
        import logging
        logger = logging.getLogger(__name__)
        
        if not self.current_config:
            QMessageBox.warning(
                self,
                "No Configuration",
                "No configuration loaded. Please pull configuration first or load from file."
            )
            return
        
        try:
            # Get default name from source tenant if available
            default_name = getattr(self.current_config, 'source_tenant', '') or ''
            
            # Pass Configuration object directly to dialog
            dialog = SaveConfigDialog(self.current_config, self, default_name=default_name)
            if dialog.exec() == SaveConfigDialog.DialogCode.Accepted:
                saved_path = dialog.get_saved_path()
                if saved_path:
                    self.status_bar.showMessage(f"Saved configuration")
                    # Update recent menu
                    self._update_recent_menu()
                    
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save configuration:\n\n{str(e)}"
            )
    
    def _export_configuration(self):
        """Export configuration to custom location."""
        import logging
        logger = logging.getLogger(__name__)
        
        if not self.current_config:
            QMessageBox.warning(
                self,
                "No Configuration",
                "No configuration loaded. Please pull configuration first or load from file."
            )
            return
        
        try:
            # Get config name
            config_name = getattr(self.current_config, 'source_tenant', None) or "Configuration"
            
            # Pass Configuration object directly to dialog
            dialog = ExportConfigDialog(self.current_config, self, config_name)
            if dialog.exec() == ExportConfigDialog.DialogCode.Accepted:
                exported_path = dialog.get_exported_path()
                if exported_path:
                    self.status_bar.showMessage(f"Exported configuration")
                    
        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export configuration:\n\n{str(e)}"
            )
    
    def _update_recent_menu(self):
        """Update the Recent Configurations menu."""
        self.recent_menu.clear()
        
        recent = self.settings.value("recent_configs", [], type=list)
        
        if not recent:
            no_recent_action = QAction("(No recent configurations)", self)
            no_recent_action.setEnabled(False)
            self.recent_menu.addAction(no_recent_action)
        else:
            for entry in recent[:10]:  # Limit to 10
                name = entry.get("name", "Unknown")
                path = entry.get("path", "")
                date = entry.get("date", "")
                
                # Format date for display
                if date:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(date)
                        date_str = dt.strftime("%m/%d/%Y")
                    except Exception:
                        date_str = ""
                else:
                    date_str = ""
                
                display_text = f"{name}"
                if date_str:
                    display_text += f" ({date_str})"
                
                action = QAction(display_text, self)
                action.setToolTip(path)
                action.setData(path)
                action.triggered.connect(lambda checked, p=path: self._load_recent_config(p))
                self.recent_menu.addAction(action)
            
            self.recent_menu.addSeparator()
            
            clear_action = QAction("Clear Recent", self)
            clear_action.triggered.connect(self._clear_recent_configs)
            self.recent_menu.addAction(clear_action)
    
    def _load_recent_config(self, file_path: str):
        """Load a configuration from recent list."""
        import os
        import logging
        logger = logging.getLogger(__name__)
        
        if not os.path.exists(file_path):
            QMessageBox.warning(
                self,
                "File Not Found",
                f"The configuration file no longer exists:\n\n{file_path}"
            )
            # Remove from recent
            recent = self.settings.value("recent_configs", [], type=list)
            recent = [r for r in recent if r.get("path") != file_path]
            self.settings.setValue("recent_configs", recent)
            self._update_recent_menu()
            return
        
        # Use LoadConfigDialog to handle decryption if needed
        from config.utils.encryption import is_encrypted_file, get_config_metadata, load_config_from_file
        from gui.dialogs import PasswordDialog
        
        encrypted = is_encrypted_file(file_path)
        metadata = get_config_metadata(file_path)
        name = metadata.get("name", os.path.basename(file_path)) if metadata else os.path.basename(file_path)
        
        password = None
        if encrypted:
            dialog = PasswordDialog(name, self)
            if dialog.exec() != PasswordDialog.DialogCode.Accepted:
                return
            password = dialog.get_password()
        
        try:
            config_data = load_config_from_file(file_path, password)
            
            # Convert to Configuration object using shared helper
            config = self._convert_dict_to_configuration(config_data, logger)
            
            self.current_config = config
            self.status_bar.showMessage(f"Loaded: {name}")
            self._update_workflow_with_config(self.current_config)
            
            logger.info(f"Loaded recent configuration: {name}")
            
        except ValueError as e:
            if "Incorrect password" in str(e):
                QMessageBox.warning(self, "Incorrect Password", "The password is incorrect.")
            else:
                QMessageBox.critical(self, "Load Error", f"Failed to load configuration:\n\n{str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load configuration:\n\n{str(e)}")
    
    def _clear_recent_configs(self):
        """Clear the recent configurations list."""
        reply = QMessageBox.question(
            self,
            "Clear Recent",
            "Clear all recent configurations?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.settings.setValue("recent_configs", [])
            self._update_recent_menu()
    
    def _show_configuration_info(self):
        """Show configuration metadata and statistics."""
        if not self.current_config:
            QMessageBox.warning(
                self,
                "No Configuration",
                "No configuration loaded. Please pull configuration first or load from file."
            )
            return
        
        # Build info message
        config = self.current_config
        all_items = config.get_all_items()
        
        # Count items by type
        items_by_type = {}
        for item in all_items:
            items_by_type[item.item_type] = items_by_type.get(item.item_type, 0) + 1
        
        # Build type summary (top 10)
        type_summary = "\n".join([
            f"  • {item_type}: {count}"
            for item_type, count in sorted(items_by_type.items(), key=lambda x: x[1], reverse=True)[:10]
        ])
        
        info_text = f"""<h3>Configuration Information</h3>
        
<p><b>Metadata:</b></p>
<table>
<tr><td><b>Source Tenant:</b></td><td>{getattr(config, 'source_tenant', None) or 'N/A'}</td></tr>
<tr><td><b>Source TSG:</b></td><td>{config.source_tsg or 'N/A'}</td></tr>
<tr><td><b>Source Config:</b></td><td>{getattr(config, 'source_config', None) or 'N/A'}</td></tr>
<tr><td><b>Load Type:</b></td><td>{config.load_type or 'N/A'}</td></tr>
<tr><td><b>Credentials Ref:</b></td><td>{config.saved_credentials_ref or 'N/A'}</td></tr>
<tr><td><b>Created:</b></td><td>{config.created_at or 'N/A'}</td></tr>
<tr><td><b>Modified:</b></td><td>{config.modified_at or 'N/A'}</td></tr>
<tr><td><b>Program Version:</b></td><td>{getattr(config, 'program_version', 'N/A')}</td></tr>
<tr><td><b>Config Version:</b></td><td>{getattr(config, 'config_version', 'N/A')}</td></tr>
</table>

<p><b>Statistics:</b></p>
<table>
<tr><td><b>Total Items:</b></td><td>{len(all_items)}</td></tr>
<tr><td><b>Folders:</b></td><td>{len(config.folders)}</td></tr>
<tr><td><b>Snippets:</b></td><td>{len(config.snippets)}</td></tr>
<tr><td><b>Infrastructure:</b></td><td>{len(config.infrastructure.items)}</td></tr>
<tr><td><b>Push History:</b></td><td>{len(config.push_history)} operations</td></tr>
</table>

<p><b>Top Item Types:</b></p>
<pre>{type_summary}</pre>
"""
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Configuration Information")
        msg_box.setText(info_text)
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
    
    def _update_workflow_with_config(self, config):
        """Update workflows with loaded configuration."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Always update migration workflow if it exists (regardless of current page)
        if hasattr(self, 'migration_workflow'):
            logger.info("Updating migration workflow with loaded config")
            self.migration_workflow.load_configuration_from_main(config)
        
        # Show message based on current page
        current_page = self.stacked_widget.currentIndex()
        if current_page == 2:
            # Already on migration workflow
            self.status_bar.showMessage("Configuration loaded into Migration workflow")
        elif current_page == 1:
            # On POV workflow
            self.status_bar.showMessage("Configuration loaded - switch to Migration workflow to view")

    def _restore_window_state(self):
        """Restore window state from settings."""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)

    def closeEvent(self, event):
        """Handle window close event."""
        # Save window state
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())

        # Accept the close event
        event.accept()
    
    def _on_config_loaded_from_workflow(self, config_dict):
        """
        Handle configuration loaded from workflow (pull operation).
        
        Convert dict format back to Configuration object for File → Save to work.
        
        Args:
            config_dict: Configuration in dictionary format
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("="*80)
        logger.info("_on_config_loaded_from_workflow called")
        logger.info(f"config_dict type: {type(config_dict)}")
        logger.info(f"config_dict is None: {config_dict is None}")
        
        if config_dict:
            logger.info(f"config_dict keys: {list(config_dict.keys())}")
            logger.info(f"Folders: {list(config_dict.get('folders', {}).keys())}")
            logger.info(f"Snippets: {list(config_dict.get('snippets', {}).keys())}")
            logger.info(f"Infrastructure keys: {list(config_dict.get('infrastructure', {}).keys())}")
        
        try:
            # Convert dict back to Configuration object
            from config.models.containers import Configuration, FolderConfig, SnippetConfig
            from config.models.factory import ConfigItemFactory
            
            logger.info("Starting Configuration object creation")
            config = Configuration()
            
            # Add folders
            folders_dict = config_dict.get('folders', {})
            logger.info(f"Processing {len(folders_dict)} folders")
            for folder_name, folder_data in folders_dict.items():
                logger.info(f"  Processing folder: {folder_name}")
                folder_config = FolderConfig(folder_name)
                # folder_data is a dict of {item_type: [items]}
                total_items = 0
                for item_type, items in folder_data.items():
                    logger.info(f"    {item_type}: {len(items)} items")
                    for item_dict in items:
                        item = ConfigItemFactory.create_from_dict(item_type, item_dict)
                        folder_config.add_item(item)
                        total_items += 1
                config.add_folder(folder_config)
                logger.info(f"  Added folder '{folder_name}' with {total_items} items")
            
            # Add snippets
            snippets_dict = config_dict.get('snippets', {})
            logger.info(f"Processing {len(snippets_dict)} snippets")
            for snippet_name, snippet_data in snippets_dict.items():
                logger.info(f"  Processing snippet: {snippet_name}")
                snippet_config = SnippetConfig(snippet_name)
                # snippet_data is a dict of {item_type: [items]}
                total_items = 0
                for item_type, items in snippet_data.items():
                    logger.info(f"    {item_type}: {len(items)} items")
                    for item_dict in items:
                        item = ConfigItemFactory.create_from_dict(item_type, item_dict)
                        snippet_config.add_item(item)
                        total_items += 1
                config.add_snippet(snippet_config)
                logger.info(f"  Added snippet '{snippet_name}' with {total_items} items")
            
            # Add infrastructure
            infra_data = config_dict.get('infrastructure', {})
            if infra_data:
                logger.info(f"Processing {len(infra_data)} infrastructure types")
                for item_type, items in infra_data.items():
                    logger.info(f"  {item_type}: {len(items)} items")
                    for item_dict in items:
                        item = ConfigItemFactory.create_from_dict(item_type, item_dict)
                        config.infrastructure.add_item(item)
            
            # Set metadata
            metadata = config_dict.get('metadata', {})
            config.version = metadata.get('version', '1.0')
            config.created_at = metadata.get('created_at', '')
            config.modified_at = metadata.get('modified_at', '')
            config.source_tenant = metadata.get('source_tenant', 'Unknown')
            
            # Store in main window
            logger.info(f"Total items in Configuration object: {len(config.get_all_items())}")
            logger.info(f"Setting self.current_config")
            self.current_config = config
            logger.info(f"self.current_config is now: {self.current_config is not None}")
            logger.info(f"self.current_config type: {type(self.current_config)}")
            logger.info("="*80)
            
        except Exception as e:
            logger.error("="*80)
            logger.error(f"EXCEPTION in _on_config_loaded_from_workflow: {e}", exc_info=True)
            logger.error("="*80)

    def log(self, message: str, level: str = "info"):
        """Add log entry."""
        self.logs_widget.log(message, level)


def main():
    """Main entry point for the GUI application."""
    # Initialize logging system with rotation
    from config.logging_config import setup_logging, NORMAL, set_log_level, enable_debug_mode
    from pathlib import Path
    import logging
    
    log_dir = Path(__file__).parent.parent / "logs"
    log_file = log_dir / "activity.log"
    
    # Load log level from settings (before creating QApplication for settings)
    from PyQt6.QtCore import QSettings
    settings = QSettings("PrismaAccess", "ConfigManager")
    log_level = settings.value("advanced/log_level", NORMAL, type=int)
    
    setup_logging(
        log_file=log_file,
        level=log_level,
        console=False,  # NO console output in GUI (prevents segfaults)
        rotate=True,
        keep_rotations=7
    )
    
    # Enable debug mode if DEBUG level selected
    if log_level == logging.DEBUG:
        enable_debug_mode()
    
    app = QApplication(sys.argv)
    
    # Install global exception handler for Qt
    def exception_hook(exctype, value, tb):
        """Global exception handler to catch all unhandled exceptions."""
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        
        # Format exception
        tb_str = ''.join(traceback.format_exception(exctype, value, tb))
        
        # Log to file
        logger.critical(f"Unhandled exception:\n{tb_str}")
        
        # Print to stderr (will be captured by debug mode)
        print(f"\n{'='*80}", file=sys.stderr)
        print("UNHANDLED EXCEPTION", file=sys.stderr)
        print('='*80, file=sys.stderr)
        print(tb_str, file=sys.stderr)
        print('='*80, file=sys.stderr)
        
        # Don't crash - let Qt handle it
        sys.__excepthook__(exctype, value, tb)
    
    sys.excepthook = exception_hook

    # Set application metadata
    app.setApplicationName("Prisma Access Configuration Manager")
    app.setOrganizationName("PrismaAccess")
    app.setOrganizationDomain("prismaaccess.config")

    # Create and show main window with exception protection
    try:
        window = PrismaConfigMainWindow()
        window.show()
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.critical(f"Failed to create main window: {e}\n{traceback.format_exc()}")
        print(f"FATAL ERROR: Failed to create main window: {e}", file=sys.stderr)
        return 1

    # Start event loop
    return app.exec()


if __name__ == "__main__":
    main()
