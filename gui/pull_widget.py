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
from gui.dialogs import AdvancedOptionsDialog


class PullConfigWidget(QWidget):
    """Widget for pulling configurations from Prisma Access."""

    # Signal emitted when pull completes successfully
    pull_completed = pyqtSignal(object)  # config

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
        
        # Tenant selector (left half)
        self.tenant_selector = TenantSelectorWidget(
            parent=self,
            title="Source Tenant",
            label="Pull from:",
            show_success_toast=lambda msg, dur: self.toast_manager.show_success(msg, dur),
            show_error_banner=lambda msg: self.error_notification.show_error(msg)
        )
        self.tenant_selector.connection_changed.connect(self._on_connection_changed)
        tenant_row.addWidget(self.tenant_selector, stretch=1)
        
        # Button container for Pull and Update Selection (stacked vertically)
        button_container = QVBoxLayout()
        button_container.setSpacing(4)
        
        # Pull button - fixed height
        self.pull_btn = QPushButton("🔄 Pull Configuration")
        self.pull_btn.setMinimumWidth(180)
        self.pull_btn.setFixedHeight(36)
        self.pull_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; font-size: 13px; }"
            "QPushButton:hover { background-color: #45a049; }"
            "QPushButton:disabled { background-color: #cccccc; color: #666666; }"
        )
        self.pull_btn.clicked.connect(self._start_pull)
        self.pull_btn.setEnabled(False)
        button_container.addWidget(self.pull_btn)
        
        # Update Selection button - starts disabled, enabled during pull
        self.update_selection_btn = QPushButton("📝 Update Selection")
        self.update_selection_btn.setMinimumWidth(180)
        self.update_selection_btn.setFixedHeight(36)
        self.update_selection_btn.setToolTip("Cancel pull and return to selection")
        self.update_selection_btn.setStyleSheet(
            "QPushButton { background-color: #FF9800; color: white; font-weight: bold; font-size: 13px; }"
            "QPushButton:hover { background-color: #F57C00; }"
            "QPushButton:disabled { background-color: #cccccc; color: #666666; }"
        )
        self.update_selection_btn.clicked.connect(self._update_selection)
        self.update_selection_btn.setEnabled(False)
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
        
        # Button row: Back (left) and Cancel (right)
        button_layout = QHBoxLayout()
        
        self.back_btn = QPushButton("← Back to Selection")
        self.back_btn.clicked.connect(self._show_selection_page)
        self.back_btn.setVisible(False)  # Only show after pull completes
        button_layout.addWidget(self.back_btn)
        
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

    def _show_selection_page(self):
        """Switch to selection page."""
        self.stacked_widget.setCurrentIndex(0)
        self.back_btn.setVisible(False)
        self.cancel_btn.setVisible(False)
        # Re-enable pull button, disable update selection
        self.pull_btn.setEnabled(self.api_client is not None)
        self.update_selection_btn.setEnabled(False)

    def _show_results_page(self):
        """Switch to results page."""
        self.stacked_widget.setCurrentIndex(1)
        self.results_panel.clear()
        self.back_btn.setVisible(False)
        self.cancel_btn.setVisible(True)
        # Disable pull button, enable update selection
        self.pull_btn.setEnabled(False)
        self.update_selection_btn.setEnabled(True)

    def _update_selection(self):
        """Cancel pull if running and return to selection page."""
        # Cancel the pull if it's running
        if self.worker and self.worker.isRunning():
            self.logger.info("User requested to update selection - cancelling pull")
            self.worker.stop()
            self.worker = None
        
        # Return to selection page
        self._show_selection_page()
        self._set_ui_enabled(True)

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

    def _on_connection_changed(self, api_client, tenant_name: str):
        """Handle connection state changes."""
        self.api_client = api_client
        self.connection_name = tenant_name if tenant_name else None
        
        connected = api_client is not None
        
        # Enable/disable UI elements
        self.folders_tree.set_enabled(connected)
        self.snippets_tree.set_enabled(connected)
        self.infrastructure_tree.set_enabled(connected)
        self.pull_btn.setEnabled(connected)
        
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
                    
                    # Filter out predefined/readonly snippets
                    if snippet_type in ('predefined', 'readonly'):
                        continue
                    
                    # Filter out known system snippet patterns
                    if snippet_name.startswith('predefined-') or snippet_name.endswith('-default'):
                        continue
                    if 'Default' in snippet_name and 'Snippet' in snippet_name:
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
        }

        self.logger.info(f"Starting pull with options: folders={len(selected_folders)}, "
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
                    self.logger.info(f"Retrieved configuration from worker: {len(str(pulled_config))} bytes")
            except Exception as e:
                self.logger.error(f"Error getting config from worker: {e}")
            
            self.worker = None

        self._set_ui_enabled(True)
        
        # Show back button, hide cancel button
        self.back_btn.setVisible(True)
        self.cancel_btn.setVisible(False)
        # Re-enable pull, disable update selection (pull is done)
        self.pull_btn.setEnabled(self.api_client is not None)
        self.update_selection_btn.setEnabled(False)

        if success:
            self.progress_label.setText("✓ Pull completed successfully!")
            self.progress_label.setStyleSheet("color: green; font-size: 14px; font-weight: bold;")
            
            self.results_panel.set_success(True)
            self.results_panel.append_text(f"\n{'='*50}\n✓ {message}")
            
            if pulled_config:
                self.pulled_config = pulled_config
                self.logger.info(f"Emitting pull_completed signal with config: {len(str(pulled_config))} bytes")
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
        
        self.worker = None
        self._set_ui_enabled(True)
        
        # Show back button, hide cancel button
        self.back_btn.setVisible(True)
        self.cancel_btn.setVisible(False)
        # Re-enable pull, disable update selection (pull is done)
        self.pull_btn.setEnabled(self.api_client is not None)
        self.update_selection_btn.setEnabled(False)
        
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

    def get_pulled_config(self):
        """Get the most recently pulled configuration."""
        return self.pulled_config
