"""
Pull configuration widget for the GUI.

This module provides the UI for pulling configurations from Prisma Access,
including options selection, progress tracking, and results display.
"""

from typing import Optional, Dict, Any, List
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QProgressBar,
    QMessageBox,
    QSplitter,
    QStackedWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSettings
import logging

from gui.workers import PullWorker
from gui.toast_notification import ToastManager, DismissibleErrorNotification
from gui.widgets import (
    TenantSelectorWidget,
    ResultsPanel,
    SelectionTreeWidget,
    InfrastructureTreeWidget,
)
from gui.dialogs import AdvancedOptionsDialog, FindApplicationsDialog


class PullConfigWidget(QWidget):
    """Widget for pulling configurations from Prisma Access."""

    # Signal emitted when pull completes successfully
    pull_completed = pyqtSignal(object)  # config
    
    # Signal to request loading config from file (handled by parent workflow)
    load_file_requested = pyqtSignal()

    # Prisma Access folders - complete hierarchy
    PRISMA_ACCESS_FOLDERS = [
        ('Global', 'All'),  # Display name, API name
        ('Prisma Access', 'Shared'),
        ('Mobile Users Container', 'Mobile Users Container'),
        ('Mobile Users', 'Mobile Users'),
        ('Remote Networks', 'Remote Networks'),
        ('Mobile Users Explicit Proxy', 'Mobile Users Explicit Proxy'),
    ]

    def __init__(self, parent=None):
        """Initialize the pull widget."""
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)
        self.settings = QSettings("PrismaAccess", "ConfigManager")
        self.api_client = None
        self.toast_manager = ToastManager(self)
        self.error_notification = DismissibleErrorNotification(self)
        self.connection_name = None
        self.worker = None
        self.pulled_config = None
        
        # Cached data
        self._snippets_cache: List[Dict[str, Any]] = []
        self._agent_profiles_cache: List[Dict[str, Any]] = []
        
        # Custom applications selected via Find Applications dialog
        # Maps folder name -> list of application dicts
        self._custom_applications: Dict[str, List[Dict[str, Any]]] = {}
        
        # Applications cache for Find Custom Applications dialog
        # Session-only cache - cleared on tenant change
        self._applications_cache: Dict[str, Any] = {
            'loaded': False,           # Whether full load completed
            'total': 0,                # Total apps from API
            'loaded_count': 0,         # Progress for resume support
            'all_apps': [],            # All apps during load (cleared after)
            'custom_apps': [],         # Filtered custom apps only
            'tenant_id': None,         # Track tenant for invalidation
        }
        
        # Batch GUI updates to prevent segfaults from rapid updates
        self.pending_messages = []
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._flush_pending_messages)
        self.update_timer.setInterval(250)

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # === Header Row: Title + Advanced Options Button ===
        header_layout = QHBoxLayout()
        
        title = QLabel("<h2>Pull Configuration</h2>")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        self.advanced_btn = QPushButton("⚙ Advanced Options")
        self.advanced_btn.setMaximumWidth(150)
        self.advanced_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #757575; color: white; padding: 6px 12px; "
            "  font-size: 12px; border-radius: 4px; "
            "  border: 1px solid #616161; border-bottom: 2px solid #424242; "
            "}"
            "QPushButton:hover { background-color: #616161; border-bottom: 2px solid #212121; }"
            "QPushButton:pressed { background-color: #616161; border-bottom: 1px solid #424242; }"
        )
        self.advanced_btn.clicked.connect(self._open_advanced_options)
        header_layout.addWidget(self.advanced_btn)
        
        layout.addLayout(header_layout)

        # Info text
        info = QLabel(
            "Connect to a source tenant and select which components to retrieve."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # === Source Tenant + Pull Button Row ===
        tenant_row = QHBoxLayout()
        
        # Tenant selector (left half) with Load from File option
        self.tenant_selector = TenantSelectorWidget(
            parent=self,
            title="Source Tenant",
            label="Pull from:",
            show_success_toast=lambda msg, dur: self.toast_manager.show_success(msg, dur),
            show_error_banner=lambda msg: self.error_notification.show_error(msg),
            show_load_button=True  # Enable "Load from File" button for pull
        )
        self.tenant_selector.connection_changed.connect(self._on_connection_changed)
        self.tenant_selector.load_file_requested.connect(self._on_load_file_requested)
        tenant_row.addWidget(self.tenant_selector, stretch=1)
        
        # Button container for Pull, Load Apps, and Update Selection (stacked vertically)
        button_container = QVBoxLayout()
        button_container.setSpacing(4)
        
        # Load Custom Applications button - enabled when connected (moved to top)
        self.find_apps_btn = QPushButton("📦 Load Custom Apps")
        self.find_apps_btn.setMinimumWidth(180)
        self.find_apps_btn.setFixedHeight(36)
        self.find_apps_btn.setToolTip("Add custom applications to include in pull")
        self.find_apps_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #4CAF50; color: white; padding: 10px 20px; "
            "  font-size: 13px; font-weight: bold; border-radius: 5px; "
            "  border: 1px solid #388E3C; border-bottom: 3px solid #2E7D32; "
            "}"
            "QPushButton:hover { background-color: #45a049; border-bottom: 3px solid #1B5E20; }"
            "QPushButton:pressed { background-color: #388E3C; border-bottom: 1px solid #2E7D32; }"
            "QPushButton:disabled { background-color: #BDBDBD; color: #666666; border: 1px solid #9E9E9E; border-bottom: 3px solid #757575; }"
        )
        self.find_apps_btn.clicked.connect(self._open_find_applications)
        self.find_apps_btn.setEnabled(False)
        button_container.addWidget(self.find_apps_btn)
        
        # Pull button - fixed height
        self.pull_btn = QPushButton("🔄 Pull Configuration")
        self.pull_btn.setMinimumWidth(180)
        self.pull_btn.setFixedHeight(36)
        self.pull_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #4CAF50; color: white; padding: 10px 20px; "
            "  font-size: 13px; font-weight: bold; border-radius: 5px; "
            "  border: 1px solid #388E3C; "
            "  border-bottom: 3px solid #2E7D32; "
            "}"
            "QPushButton:hover { "
            "  background-color: #45a049; "
            "  border-bottom: 3px solid #1B5E20; "
            "}"
            "QPushButton:pressed { "
            "  background-color: #388E3C; "
            "  border-bottom: 1px solid #2E7D32; "
            "}"
            "QPushButton:disabled { "
            "  background-color: #BDBDBD; color: #666666; "
            "  border: 1px solid #9E9E9E; "
            "  border-bottom: 3px solid #757575; "
            "}"
        )
        self.pull_btn.clicked.connect(self._start_pull)
        self.pull_btn.setEnabled(False)
        button_container.addWidget(self.pull_btn)
        
        # Update Selection button - starts hidden, shown after pull completes
        self.update_selection_btn = QPushButton("↩ Return to Selection")
        self.update_selection_btn.setMinimumWidth(180)
        self.update_selection_btn.setFixedHeight(36)
        self.update_selection_btn.setToolTip("Return to selection to modify options")
        self.update_selection_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #2196F3; color: white; font-weight: bold; font-size: 13px; "
            "  border-radius: 5px; border: 1px solid #1976D2; border-bottom: 3px solid #1565C0; "
            "}"
            "QPushButton:hover { background-color: #1E88E5; border-bottom: 3px solid #0D47A1; }"
            "QPushButton:pressed { background-color: #1976D2; border-bottom: 1px solid #1565C0; }"
            "QPushButton:disabled { background-color: #BDBDBD; color: #666666; border: 1px solid #9E9E9E; border-bottom: 3px solid #757575; }"
        )
        self.update_selection_btn.clicked.connect(self._show_selection_page)
        self.update_selection_btn.setVisible(False)
        button_container.addWidget(self.update_selection_btn)
        
        tenant_row.addLayout(button_container)
        
        layout.addLayout(tenant_row)

        # === Stacked Widget: Selection vs Progress/Results ===
        self.stacked_widget = QStackedWidget()
        
        # Page 0: Selection Area (three columns)
        selection_page = QWidget()
        selection_layout = QVBoxLayout(selection_page)
        selection_layout.setContentsMargins(0, 0, 0, 0)
        
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: Folders
        self.folders_tree = SelectionTreeWidget("Folders", show_components=True)
        self.folders_tree.set_enabled(False)
        self._populate_folders()
        self.splitter.addWidget(self.folders_tree)
        
        # Middle: Snippets
        self.snippets_tree = SelectionTreeWidget("Snippets", show_components=True)
        self.snippets_tree.set_enabled(False)
        self.splitter.addWidget(self.snippets_tree)
        
        # Right: Infrastructure
        self.infrastructure_tree = InfrastructureTreeWidget()
        self.infrastructure_tree.set_enabled(False)
        self.splitter.addWidget(self.infrastructure_tree)
        
        # Set initial splitter sizes (equal thirds)
        self.splitter.setSizes([300, 300, 300])
        
        selection_layout.addWidget(self.splitter)
        self.stacked_widget.addWidget(selection_page)
        
        # Page 1: Progress and Results
        results_page = QWidget()
        results_layout = QVBoxLayout(results_page)
        results_layout.setContentsMargins(0, 0, 0, 0)
        
        # Progress section
        self.progress_label = QLabel("Pulling configuration...")
        self.progress_label.setStyleSheet("color: #1976D2; font-size: 14px; font-weight: bold;")
        results_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(25)
        results_layout.addWidget(self.progress_bar)
        
        # Results panel (takes remaining space)
        self.results_panel = ResultsPanel(parent=self, title="Pull Results")
        results_layout.addWidget(self.results_panel, stretch=1)
        
        # Button row: Cancel (right-aligned)
        button_layout = QHBoxLayout()
        
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("✕ Cancel Pull")
        self.cancel_btn.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; padding: 8px 16px; font-weight: bold; }"
            "QPushButton:hover { background-color: #d32f2f; }"
        )
        self.cancel_btn.clicked.connect(self._cancel_pull)
        self.cancel_btn.setVisible(True)  # Visible during pull, hidden after
        button_layout.addWidget(self.cancel_btn)
        
        results_layout.addLayout(button_layout)
        
        self.stacked_widget.addWidget(results_page)
        
        # Start on selection page
        self.stacked_widget.setCurrentIndex(0)
        
        layout.addWidget(self.stacked_widget, stretch=1)

    def _populate_folders(self):
        """Populate the folders tree with Prisma Access folders."""
        self.folders_tree.clear()
        for display_name, api_name in self.PRISMA_ACCESS_FOLDERS:
            self.folders_tree.add_top_level_item(
                name=display_name,
                item_type="folder",
                data={'name': api_name, 'display_name': display_name, 'type': 'folder'},
                checked=True,
                add_components=True
            )

    def _open_advanced_options(self):
        """Open the advanced options dialog."""
        dialog = AdvancedOptionsDialog(self)
        dialog.exec()

    def _open_find_applications(self):
        """Open the Find Custom Applications dialog."""
        if not self.api_client:
            self.error_notification.show_error(
                "Not Connected: Please connect to a source tenant first."
            )
            return
        
        # Pass cache by reference so dialog can update it
        dialog = FindApplicationsDialog(self.api_client, self._applications_cache, self)
        if dialog.exec() == FindApplicationsDialog.DialogCode.Accepted:
            selected_apps = dialog.get_selected_applications()
            if selected_apps:
                self._add_custom_applications(selected_apps)
    
    def _add_custom_applications(self, apps_by_folder: Dict[str, List[Dict[str, Any]]]):
        """
        Add selected custom applications to the appropriate folder trees.
        
        Args:
            apps_by_folder: Dict mapping folder name to list of application dicts
        """
        from PyQt6.QtGui import QColor
        from PyQt6.QtWidgets import QTreeWidgetItem
        
        total_added = 0
        
        for folder_name, apps in apps_by_folder.items():
            # Store in our cache
            if folder_name not in self._custom_applications:
                self._custom_applications[folder_name] = []
            
            # Add only new applications (avoid duplicates)
            existing_ids = {a.get('id') for a in self._custom_applications[folder_name]}
            for app in apps:
                if app.get('id') not in existing_ids:
                    self._custom_applications[folder_name].append(app)
                    total_added += 1
            
            # Find the folder in the tree and add/update Applications section
            self._update_folder_applications(folder_name, self._custom_applications[folder_name])
        
        if total_added > 0:
            self.toast_manager.show_success(
                f"Added {total_added} custom application{'s' if total_added != 1 else ''} to selection",
                duration=3000
            )
            self.logger.info(f"Added {total_added} custom applications to selection")
    
    def _update_folder_applications(self, folder_name: str, apps: List[Dict[str, Any]]):
        """
        Update the Applications section in a folder's tree entry.
        
        Adds a "Custom Applications (N)" entry under the existing "Applications" section.
        
        Args:
            folder_name: API name of the folder
            apps: List of application dicts to add
        """
        from PyQt6.QtGui import QColor, QFont
        from PyQt6.QtWidgets import QTreeWidgetItem
        
        # Find the folder item in the tree
        folder_item = None
        for i in range(self.folders_tree.tree.topLevelItemCount()):
            item = self.folders_tree.tree.topLevelItem(i)
            item_data = item.data(0, Qt.ItemDataRole.UserRole)
            if item_data and item_data.get('name') == folder_name:
                folder_item = item
                break
        
        if not folder_item:
            self.logger.warning(f"Could not find folder '{folder_name}' in tree")
            return
        
        # Find the "Applications" section within the folder
        apps_section = None
        for i in range(folder_item.childCount()):
            child = folder_item.child(i)
            # Check if this is the Applications section (by text or data)
            if child.text(0) == "Applications" or (
                child.data(0, Qt.ItemDataRole.UserRole) and 
                child.data(0, Qt.ItemDataRole.UserRole).get('type') == 'section' and
                child.data(0, Qt.ItemDataRole.UserRole).get('section') == 'Applications'
            ):
                apps_section = child
                break
        
        # If no Applications section exists, create one
        if not apps_section:
            apps_section = QTreeWidgetItem(["Applications", "section"])
            apps_section.setFlags(apps_section.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            apps_section.setCheckState(0, Qt.CheckState.Checked)
            apps_section.setData(0, Qt.ItemDataRole.UserRole, {
                'type': 'section',
                'section': 'Applications',
                'parent': folder_name
            })
            
            # Make section name bold
            font = apps_section.font(0)
            font.setBold(True)
            apps_section.setFont(0, font)
            
            # Add to folder
            folder_item.addChild(apps_section)
        
        # Find or create "Custom Applications" entry under Applications section
        custom_apps_item = None
        for i in range(apps_section.childCount()):
            child = apps_section.child(i)
            child_data = child.data(0, Qt.ItemDataRole.UserRole)
            if child_data and child_data.get('type') == 'custom_applications':
                custom_apps_item = child
                break
        
        if not custom_apps_item:
            # Create new Custom Applications entry with item_type from ApplicationObject
            custom_apps_item = QTreeWidgetItem([f"Custom Applications ({len(apps)})", "application_object"])
            custom_apps_item.setFlags(custom_apps_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            custom_apps_item.setCheckState(0, Qt.CheckState.Checked)
            # Make it non-interactive (locked)
            custom_apps_item.setFlags(custom_apps_item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            custom_apps_item.setData(0, Qt.ItemDataRole.UserRole, {
                'type': 'custom_applications',
                'item_type': 'application_object',
                'parent': folder_name,
                'apps': apps
            })
            
            # Grey out and use blue color to indicate it's locked but special
            custom_apps_item.setForeground(0, QColor(33, 150, 243))  # Blue
            
            apps_section.addChild(custom_apps_item)
        else:
            # Update existing entry
            existing_data = custom_apps_item.data(0, Qt.ItemDataRole.UserRole)
            existing_apps = existing_data.get('apps', []) if existing_data else []
            
            # Merge apps (avoid duplicates by ID)
            existing_ids = {a.get('id') for a in existing_apps}
            for app in apps:
                if app.get('id') not in existing_ids:
                    existing_apps.append(app)
            
            # Update text and data
            custom_apps_item.setText(0, f"Custom Applications ({len(existing_apps)})")
            custom_apps_item.setData(0, Qt.ItemDataRole.UserRole, {
                'type': 'custom_applications',
                'item_type': 'application_object',
                'parent': folder_name,
                'apps': existing_apps
            })
        
        # Expand folder and Applications section to show the entry
        folder_item.setExpanded(True)
        apps_section.setExpanded(True)
        
        # Scroll to make visible
        self.folders_tree.tree.scrollToItem(custom_apps_item)

    def _show_selection_page(self):
        """Switch to selection page."""
        self.stacked_widget.setCurrentIndex(0)
        self.cancel_btn.setVisible(False)
        # Re-enable pull button and find apps, hide update selection
        self.pull_btn.setEnabled(self.api_client is not None)
        self.update_selection_btn.setVisible(False)
        self.find_apps_btn.setEnabled(self.api_client is not None)
        self._set_ui_enabled(True)

    def _show_results_page(self):
        """Switch to results page."""
        self.stacked_widget.setCurrentIndex(1)
        self.results_panel.clear()
        self.cancel_btn.setVisible(True)
        # Disable pull button and find apps, hide update selection (shown after pull completes)
        self.pull_btn.setEnabled(False)
        self.update_selection_btn.setVisible(False)
        self.find_apps_btn.setEnabled(False)

    def _cancel_pull(self):
        """Cancel the current pull operation."""
        if self.worker and self.worker.isRunning():
            self.logger.info("User requested pull cancellation")
            self.results_panel.append_text("\n⚠ Cancelling pull operation...")
            self.progress_label.setText("Cancelling...")
            self.progress_label.setStyleSheet("color: #FF9800; font-size: 14px; font-weight: bold;")
            
            # Signal the worker to stop
            self.worker.stop()
            
            # Hide cancel button immediately
            self.cancel_btn.setVisible(False)
        self.progress_bar.setValue(0)

    def _on_load_file_requested(self):
        """Handle request to load config from file."""
        # Emit signal to be handled by parent workflow
        self.load_file_requested.emit()
    
    def _on_connection_changed(self, api_client, tenant_name: str):
        """Handle connection state changes."""
        self.api_client = api_client
        self.connection_name = tenant_name if tenant_name else None
        
        connected = api_client is not None
        
        # Clear applications cache if tenant changed
        if self._applications_cache.get('tenant_id') != tenant_name:
            self.logger.info(f"Tenant changed from '{self._applications_cache.get('tenant_id')}' to '{tenant_name}' - clearing applications cache")
            self._applications_cache = {
                'loaded': False,
                'total': 0,
                'loaded_count': 0,
                'all_apps': [],
                'custom_apps': [],
                'tenant_id': tenant_name,
            }
            # Also clear selected custom applications since they're tenant-specific
            self._custom_applications = {}
        
        # Enable/disable UI elements
        self.folders_tree.set_enabled(connected)
        self.snippets_tree.set_enabled(connected)
        self.infrastructure_tree.set_enabled(connected)
        self.pull_btn.setEnabled(connected)
        self.find_apps_btn.setEnabled(connected)
        
        if connected:
            self.progress_label.setText(f"Connected to {tenant_name} - Ready to pull")
            self.progress_label.setStyleSheet("color: green;")
            # Discover snippets and agent profiles
            self._discover_snippets()
            self._discover_agent_profiles()
        else:
            self.progress_label.setText("Not connected")
            self.progress_label.setStyleSheet("color: gray;")
            self.snippets_tree.clear()
            self._snippets_cache = []

    def _discover_snippets(self):
        """Discover available snippets from the API."""
        if not self.api_client:
            return
        
        try:
            self.progress_label.setText("Discovering snippets...")
            
            from prisma.api_endpoints import APIEndpoints
            response = self.api_client._make_request(
                "GET",
                APIEndpoints.SECURITY_POLICY_SNIPPETS,
                item_type='snippet'
            )
            
            snippets = []
            if isinstance(response, dict) and 'data' in response:
                for snippet in response['data']:
                    snippet_name = snippet.get('name', '')
                    snippet_type = snippet.get('type', '')
                    
                    # Filter out predefined/readonly snippets by type field only
                    if snippet_type in ('predefined', 'readonly'):
                        continue
                    
                    snippets.append({
                        'name': snippet_name,
                        'id': snippet.get('id', ''),
                        'type': snippet_type,
                    })
            
            self._snippets_cache = snippets
            self._populate_snippets(snippets)
            
            self.progress_label.setText(f"Connected to {self.connection_name} - Found {len(snippets)} custom snippets")
            self.logger.info(f"Discovered {len(snippets)} custom snippets")
            
        except Exception as e:
            self.logger.error(f"Error discovering snippets: {e}")
            self.progress_label.setText(f"Connected - Error discovering snippets: {e}")

    def _populate_snippets(self, snippets: List[Dict[str, Any]]):
        """Populate the snippets tree."""
        self.snippets_tree.clear()
        
        if not snippets:
            # Add placeholder
            self.snippets_tree.add_top_level_item(
                name="(No custom snippets found)",
                item_type="info",
                checked=False,
                add_components=False
            )
            return
        
        for snippet in snippets:
            self.snippets_tree.add_top_level_item(
                name=snippet['name'],
                item_type="snippet",
                data=snippet,
                checked=True,
                add_components=True
            )

    def _discover_agent_profiles(self):
        """Discover agent profiles for Mobile Users infrastructure."""
        if not self.api_client:
            return
        
        try:
            from config.models.factory import ConfigItemFactory
            
            model_class = ConfigItemFactory.get_model_class('agent_profile')
            if not model_class or not hasattr(model_class, 'api_endpoint'):
                self.logger.warning("No model class for agent_profile")
                return
            
            # Fetch agent profiles
            url = f"{model_class.api_endpoint}?folder=Mobile%20Users"
            response = self.api_client._make_request("GET", url, item_type='agent_profile')
            
            profiles = []
            if isinstance(response, dict) and 'data' in response:
                for profile in response['data']:
                    profiles.append({
                        'name': profile.get('name', 'Unknown'),
                        'id': profile.get('id', ''),
                    })
            
            self._agent_profiles_cache = profiles
            self.infrastructure_tree.set_agent_profiles(profiles)
            
            self.logger.info(f"Discovered {len(profiles)} agent profiles")
            
        except Exception as e:
            self.logger.error(f"Error discovering agent profiles: {e}")

    def set_api_client(self, api_client, connection_name=None):
        """Set the API client for this widget."""
        self.api_client = api_client
        self.connection_name = connection_name or "Manual"
        
        connected = api_client is not None
        self.folders_tree.set_enabled(connected)
        self.snippets_tree.set_enabled(connected)
        self.infrastructure_tree.set_enabled(connected)
        self.pull_btn.setEnabled(connected)
        
        if api_client and connection_name:
            self.tenant_selector.set_connection(api_client, connection_name)

    def populate_source_tenants(self, tenants: list):
        """
        Populate the source tenant dropdown with saved tenants.
        
        Args:
            tenants: List of tenant dictionaries with 'name' key
        """
        self.tenant_selector.populate_tenants(tenants)

    def _start_pull(self):
        """Start the configuration pull operation."""
        if not self.api_client:
            self.error_notification.show_error(
                "Not Connected: Please connect to a source tenant before pulling configuration."
            )
            return

        # Get filter defaults setting
        filter_defaults = self.settings.value("pull/filter_defaults", True, type=bool)

        # Gather selected folders and their components
        selected_folders = self.folders_tree.get_selected_items()
        selected_snippets = self.snippets_tree.get_selected_items()
        infrastructure_config = self.infrastructure_tree.get_selected_infrastructure()

        # Build options dict for the worker
        options = {
            "folders": True,
            "snippets": True,
            "rules": True,
            "objects": True,
            "profiles": True,
            # Folder selection
            "selected_folders": selected_folders,
            # Snippet selection
            "selected_snippets": selected_snippets,
            # Infrastructure options
            "include_remote_networks": infrastructure_config.get('remote_networks', False),
            "include_service_connections": infrastructure_config.get('service_connections', False),
            "include_mobile_users": infrastructure_config.get('mobile_users', False),
            "infrastructure_config": infrastructure_config,
            # Custom applications loaded via Find Applications dialog
            "custom_applications": self._custom_applications,
        }

        self.logger.normal(f"Starting pull with options: folders={len(selected_folders)}, "
                          f"snippets={len(selected_snippets)}, filter_defaults={filter_defaults}")

        # Disable UI during pull
        self._set_ui_enabled(False)

        # Switch to results page
        self._show_results_page()
        self.progress_label.setText("Preparing to pull configuration...")
        
        # Start the batch update timer
        self.pending_messages.clear()
        self.update_timer.start()

        # Create and start worker
        self.worker = PullWorker(self.api_client, options, filter_defaults, self.connection_name)
        self.worker.progress.connect(self._on_progress, Qt.ConnectionType.QueuedConnection)
        self.worker.finished.connect(self._on_pull_finished, Qt.ConnectionType.QueuedConnection)
        self.worker.error.connect(self._on_error, Qt.ConnectionType.QueuedConnection)
        self.worker.start()

    def _on_progress(self, message: str, percentage: int):
        """Handle progress updates - batched to prevent GUI overload."""
        try:
            # Ensure progress never goes backwards
            current_value = self.progress_bar.value()
            if percentage < current_value:
                percentage = current_value
            
            # Update progress label and bar immediately
            self.progress_label.setText(message)
            self.progress_bar.setValue(percentage)
            
            # Queue message for batched update
            self.pending_messages.append(f"[{percentage}%] {message}")
            
        except RuntimeError as e:
            self.logger.warning(f"Progress update error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected progress update error: {e}")

    def _flush_pending_messages(self):
        """Flush all pending messages to results panel."""
        if not self.pending_messages:
            return
        
        try:
            if hasattr(self.results_panel, 'append_text'):
                combined = "\n".join(self.pending_messages)
                self.results_panel.append_text(combined)
            self.pending_messages.clear()
        except RuntimeError:
            self.pending_messages.clear()
        except Exception as e:
            self.logger.error(f"Error flushing messages: {e}")
            self.pending_messages.clear()

    def _on_pull_finished(self, success: bool, message: str, config_unused):
        """Handle pull completion."""
        self.update_timer.stop()
        self._flush_pending_messages()
        
        # Get config from worker before cleanup
        pulled_config = None
        if self.worker:
            try:
                pulled_config = self.worker.config
                if pulled_config:
                    self.logger.detail(f"Retrieved configuration from worker: {len(str(pulled_config))} bytes")
            except Exception as e:
                self.logger.error(f"Error getting config from worker: {e}")
            
            # Wait for thread to fully finish before cleanup
            if self.worker.isRunning():
                self.worker.wait(1000)  # 1 second timeout
            self.worker = None

        self._set_ui_enabled(True)
        
        # Hide cancel button, show update selection button
        self.cancel_btn.setVisible(False)
        self.update_selection_btn.setVisible(True)
        # Re-enable pull button
        self.pull_btn.setEnabled(self.api_client is not None)

        if success:
            self.progress_label.setText("✓ Pull completed successfully!")
            self.progress_label.setStyleSheet("color: green; font-size: 14px; font-weight: bold;")
            
            self.results_panel.set_success(True)
            self.results_panel.append_text(f"\n{'='*50}\n✓ {message}")
            
            if pulled_config:
                self.pulled_config = pulled_config
                self.logger.detail(f"Emitting pull_completed signal with config: {len(str(pulled_config))} bytes")
                self.pull_completed.emit(pulled_config)
            else:
                self.logger.warning("No pulled_config to emit!")
        else:
            self.progress_label.setText(f"✗ Pull failed: {message}")
            self.progress_label.setStyleSheet("color: red; font-size: 14px; font-weight: bold;")
            
            self.results_panel.set_success(False)
            self.results_panel.append_text(f"\n{'='*50}\n✗ Pull failed: {message}")

    def _on_error(self, error_message: str):
        """Handle errors during pull."""
        self.update_timer.stop()
        self._flush_pending_messages()
        
        # Wait for thread to fully finish before cleanup
        if self.worker:
            if self.worker.isRunning():
                self.worker.wait(1000)  # 1 second timeout
            self.worker = None
        self._set_ui_enabled(True)
        
        # Hide cancel button, show update selection button
        self.cancel_btn.setVisible(False)
        self.update_selection_btn.setVisible(True)
        # Re-enable pull button
        self.pull_btn.setEnabled(self.api_client is not None)
        
        self.progress_label.setText(f"✗ Error: {error_message}")
        self.progress_label.setStyleSheet("color: red; font-size: 14px; font-weight: bold;")
        
        self.results_panel.set_success(False)
        self.results_panel.append_text(f"\n{'='*50}\n✗ Error: {error_message}")

    def _set_ui_enabled(self, enabled: bool):
        """Enable or disable UI elements."""
        self.tenant_selector.setEnabled(enabled)
        self.folders_tree.set_enabled(enabled and self.api_client is not None)
        self.snippets_tree.set_enabled(enabled and self.api_client is not None)
        self.infrastructure_tree.set_enabled(enabled and self.api_client is not None)
        self.pull_btn.setEnabled(enabled and self.api_client is not None)
        self.advanced_btn.setEnabled(enabled)
        self.find_apps_btn.setEnabled(enabled and self.api_client is not None)

    def get_pulled_config(self):
        """Get the most recently pulled configuration."""
        return self.pulled_config
