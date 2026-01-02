"""
Pull configuration widget for the GUI.

This module provides the UI for pulling configurations from Prisma Access,
including options selection, progress tracking, and results display.
"""

from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QCheckBox,
    QPushButton,
    QLabel,
    QProgressBar,
    QTextEdit,
    QMessageBox,
    QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from gui.workers import PullWorker
from gui.toast_notification import ToastManager, DismissibleErrorNotification
from gui.widgets import TenantSelectorWidget


class PullConfigWidget(QWidget):
    """Widget for pulling configurations from Prisma Access."""

    # Signal emitted when pull completes successfully
    pull_completed = pyqtSignal(object)  # config

    def __init__(self, parent=None):
        """Initialize the pull widget."""
        super().__init__(parent)

        self.api_client = None
        self.toast_manager = ToastManager(self)
        self.error_notification = DismissibleErrorNotification(self)
        self.connection_name = None
        self.worker = None
        self.pulled_config = None
        
        # Batch GUI updates to prevent segfaults from rapid updates
        self.pending_messages = []
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._flush_pending_messages)
        self.update_timer.setInterval(250)  # Update GUI every 250ms
        # Timer will be started when pull begins, not on every progress update

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("<h2>Pull Configuration</h2>")
        layout.addWidget(title)

        info = QLabel(
            "Pull configuration from a Prisma Access tenant.\n"
            "Connect to a source tenant and select which components to retrieve."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # Source tenant selection (using reusable widget)
        self.tenant_selector = TenantSelectorWidget(
            parent=self,
            title="Source Tenant",
            label="Pull from:",
            show_toast=lambda msg, typ, dur: self.toast_manager.show_toast(msg, typ, dur),
            show_error=lambda msg: self.error_notification.show_error(msg)
        )
        self.tenant_selector.connection_changed.connect(self._on_connection_changed)
        layout.addWidget(self.tenant_selector)

        # Scroll area for options
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(450)  # Increased from 300 to accommodate infrastructure options

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Folder selection button (NEW)
        folder_selection_layout = QHBoxLayout()
        folder_selection_layout.addStretch()
        
        self.folder_select_btn = QPushButton("📁 Select Folders & Snippets...")
        self.folder_select_btn.setMinimumWidth(250)
        self.folder_select_btn.setStyleSheet(
            "QPushButton { background-color: #FF9800; color: white; padding: 10px; font-weight: bold; }"
            "QPushButton:hover { background-color: #F57C00; }"
        )
        self.folder_select_btn.clicked.connect(self._open_folder_selection)
        self.folder_select_btn.setEnabled(False)  # Enable when connected
        folder_selection_layout.addWidget(self.folder_select_btn)
        
        folder_selection_layout.addStretch()
        scroll_layout.addLayout(folder_selection_layout)
        
        # Folder selection status label (NEW)
        self.folder_selection_label = QLabel("No specific folders selected (will pull all)")
        self.folder_selection_label.setStyleSheet("color: gray; font-size: 10px; padding: 5px; text-align: center;")
        self.folder_selection_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll_layout.addWidget(self.folder_selection_label)
        
        # Store selected folders/components/snippets (NEW)
        self.selected_folders = []
        self.selected_components = {}
        self.selected_snippets = []
        
        # Store selected applications
        self.selected_applications = []

        # Infrastructure Components group (NEW)
        infra_group = QGroupBox("Infrastructure Components")
        infra_layout = QVBoxLayout()

        self.remote_networks_check = QCheckBox("Remote Networks")
        self.remote_networks_check.setChecked(True)
        self.remote_networks_check.setToolTip(
            "Pull remote network configurations (branches, data centers)"
        )
        infra_layout.addWidget(self.remote_networks_check)

        self.service_connections_check = QCheckBox("Service Connections")
        self.service_connections_check.setChecked(True)
        self.service_connections_check.setToolTip(
            "Pull service connection configurations (on-prem connectivity)"
        )
        infra_layout.addWidget(self.service_connections_check)

        self.ipsec_tunnels_check = QCheckBox("IPsec Tunnels & Crypto")
        self.ipsec_tunnels_check.setChecked(True)
        self.ipsec_tunnels_check.setToolTip(
            "Pull IPsec tunnel configs, IKE gateways, and crypto profiles"
        )
        infra_layout.addWidget(self.ipsec_tunnels_check)

        self.mobile_users_check = QCheckBox("Mobile User Infrastructure")
        self.mobile_users_check.setChecked(True)
        self.mobile_users_check.setToolTip(
            "Pull GlobalProtect gateway/portal configs and mobile user settings"
        )
        infra_layout.addWidget(self.mobile_users_check)

        self.hip_check = QCheckBox("HIP Objects & Profiles")
        self.hip_check.setChecked(True)
        self.hip_check.setToolTip(
            "Pull Host Information Profile (HIP) objects and profiles"
        )
        infra_layout.addWidget(self.hip_check)

        self.regions_check = QCheckBox("Regions & Bandwidth")
        self.regions_check.setChecked(True)
        self.regions_check.setToolTip(
            "Pull enabled regions and bandwidth allocations"
        )
        infra_layout.addWidget(self.regions_check)

        infra_group.setLayout(infra_layout)
        scroll_layout.addWidget(infra_group)

        # Advanced options
        advanced_group = QGroupBox("Advanced Options")
        advanced_layout = QVBoxLayout()

        self.filter_defaults_check = QCheckBox("Filter Default Configurations")
        self.filter_defaults_check.setChecked(False)
        self.filter_defaults_check.setToolTip(
            "Automatically detect and exclude default configurations"
        )
        advanced_layout.addWidget(self.filter_defaults_check)

        advanced_group.setLayout(advanced_layout)
        scroll_layout.addWidget(advanced_group)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self._select_all)
        button_layout.addWidget(self.select_all_btn)

        self.select_none_btn = QPushButton("Select None")
        self.select_none_btn.clicked.connect(self._select_none)
        button_layout.addWidget(self.select_none_btn)

        button_layout.addStretch()

        self.pull_btn = QPushButton("Pull Configuration")
        self.pull_btn.setMinimumWidth(150)
        self.pull_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 8px; }"
            "QPushButton:hover { background-color: #45a049; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        self.pull_btn.clicked.connect(self._start_pull)
        button_layout.addWidget(self.pull_btn)

        layout.addLayout(button_layout)

        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()

        self.progress_label = QLabel("Ready to pull")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)

        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

        # Results section
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout()

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(150)
        self.results_text.setPlaceholderText("Pull results will appear here...")
        results_layout.addWidget(self.results_text)

        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        layout.addStretch()

    def set_api_client(self, api_client, connection_name=None):
        """
        Set the API client for pull operations.
        
        This method is called from main_window when a connection is established,
        or internally via the tenant selector widget.
        """
        self.api_client = api_client
        self.connection_name = connection_name or "Manual"
        
        # Update tenant selector if called externally
        if api_client and connection_name:
            self.tenant_selector.set_connection(api_client, connection_name)
        
        # Update UI state
        self._update_ui_for_connection()
    
    def populate_source_tenants(self, tenants: list):
        """
        Populate the source tenant dropdown with saved tenants.
        
        Args:
            tenants: List of tenant dictionaries with 'name' key
        """
        self.tenant_selector.populate_tenants(tenants)
    
    def _on_connection_changed(self, api_client, tenant_name: str):
        """
        Handle connection changes from the tenant selector.
        
        Args:
            api_client: The API client (or None if disconnected)
            tenant_name: Name of the tenant (or empty string if disconnected)
        """
        self.api_client = api_client
        self.connection_name = tenant_name if tenant_name else None
        self._update_ui_for_connection()
    
    def _update_ui_for_connection(self):
        """Update UI elements based on connection state."""
        connected = self.api_client is not None
        
        # Update button states
        self.pull_btn.setEnabled(connected)
        self.folder_select_btn.setEnabled(connected)
        
        # Update progress label
        if connected:
            self.progress_label.setText(
                f"Connected to {self.connection_name} - Ready to pull"
            )
            self.progress_label.setStyleSheet("color: green;")
        else:
            self.progress_label.setText("Connect to a source tenant to begin")
            self.progress_label.setStyleSheet("color: gray;")

    def _open_folder_selection(self):
        """Open folder selection dialog."""
        if not self.api_client:
            # Show inline error instead of dialog
            self.error_notification.show_error(
                "Not Connected: Please connect to a source tenant before selecting folders."
            )
            return
        
        from gui.dialogs.folder_selection_dialog import FolderSelectionDialog
        
        dialog = FolderSelectionDialog(self.api_client, self)
        if dialog.exec():
            self.selected_folders = dialog.get_selected_folders()
            self.selected_components = dialog.get_selected_components()
            self.selected_snippets = dialog.get_selected_snippets()
            
            # Update label
            folder_count = len(self.selected_folders)
            snippet_count = len(self.selected_snippets)
            
            if folder_count == 0 and snippet_count == 0:
                self.folder_selection_label.setText("No specific folders selected (will pull all)")
                self.folder_selection_label.setStyleSheet("color: gray; font-size: 10px; padding: 5px;")
            else:
                parts = []
                if folder_count > 0:
                    parts.append(f"{folder_count} folder(s)")
                if snippet_count > 0:
                    parts.append(f"{snippet_count} snippet(s)")
                
                self.folder_selection_label.setText(f"Selected: {', '.join(parts)}")
                self.folder_selection_label.setStyleSheet("color: green; font-size: 10px; padding: 5px;")

    def _on_applications_toggle(self, state):
        """Enable/disable applications button when checkbox toggled."""
        from PyQt6.QtCore import Qt
        self.applications_btn.setEnabled(state == Qt.CheckState.Checked.value)
        if state != Qt.CheckState.Checked.value:
            self.selected_applications = []
            self.applications_label.setText("No applications selected")
            self.applications_label.setStyleSheet("color: gray; font-size: 10px;")

    def _select_applications(self):
        """Open application search dialog."""
        if not self.api_client:
            QMessageBox.warning(
                self,
                "Not Connected",
                "Please connect to Prisma Access before selecting applications."
            )
            return
        
        # Use CLI application search for now (simple implementation)
        from PyQt6.QtWidgets import QInputDialog
        
        # Simple input dialog for application names
        text, ok = QInputDialog.getText(
            self,
            "Custom Applications",
            "Enter application names (comma-separated):\n"
            "Note: Only include custom/user-created applications.\n"
            "Most applications are predefined and don't need to be specified.",
            text=", ".join(self.selected_applications)
        )
        
        if ok and text:
            # Parse comma-separated list
            apps = [app.strip() for app in text.split(",") if app.strip()]
            self.selected_applications = apps
            count = len(apps)
            self.applications_label.setText(
                f"{count} application{'s' if count != 1 else ''} selected"
            )
            self.applications_label.setStyleSheet("color: green; font-size: 10px;")
        elif ok:
            # Empty input - clear selection
            self.selected_applications = []
            self.applications_label.setText("No applications selected")
            self.applications_label.setStyleSheet("color: gray; font-size: 10px;")

    def _select_all(self):
        """Select all infrastructure checkboxes."""
        # Infrastructure
        self.remote_networks_check.setChecked(True)
        self.service_connections_check.setChecked(True)
        self.ipsec_tunnels_check.setChecked(True)
        self.mobile_users_check.setChecked(True)
        self.hip_check.setChecked(True)
        self.regions_check.setChecked(True)

    def _select_none(self):
        """Deselect all infrastructure checkboxes."""
        # Infrastructure
        self.remote_networks_check.setChecked(False)
        self.service_connections_check.setChecked(False)
        self.ipsec_tunnels_check.setChecked(False)
        self.mobile_users_check.setChecked(False)
        self.hip_check.setChecked(False)
        self.regions_check.setChecked(False)

    def _start_pull(self):
        """Start the pull operation."""
        # Check if API client is set
        if not self.api_client:
            # Show inline error instead of dialog
            self.error_notification.show_error(
                "Not Connected: Please connect to a source tenant before pulling configuration."
            )
            return
        
        # Gather options (folder/snippet selection handled by dialog)
        options = {
            # Configuration components are now selected via the folder selection dialog
            "folders": True,  # Always pull folders
            "snippets": True,  # Always pull snippets
            "rules": True,  # Always pull rules
            "objects": True,  # Always pull objects
            "profiles": True,  # Always pull profiles
            # Custom applications (if any selected)
            "application_names": self.selected_applications if self.selected_applications else None,
            # Infrastructure options
            "include_remote_networks": self.remote_networks_check.isChecked(),
            "include_service_connections": self.service_connections_check.isChecked(),
            "include_ipsec_tunnels": self.ipsec_tunnels_check.isChecked(),
            "include_mobile_users": self.mobile_users_check.isChecked(),
            "include_hip": self.hip_check.isChecked(),
            "include_regions": self.regions_check.isChecked(),
            # Folder and snippet selection (from dialog)
            # Convert empty lists to None so orchestrator knows to pull all
            "selected_folders": self.selected_folders if self.selected_folders else None,
            "selected_components": self.selected_components if self.selected_components else None,
            "selected_snippets": self.selected_snippets if self.selected_snippets else None,
        }

        filter_defaults = self.filter_defaults_check.isChecked()

        # Disable UI during pull
        self._set_ui_enabled(False)

        # Show progress bar
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.progress_label.setText("Preparing to pull configuration...")

        # Clear previous results
        self.results_text.clear()
        
        # Start the batch update timer (runs continuously during pull)
        self.pending_messages.clear()
        self.update_timer.start()

        # Create and start worker
        self.worker = PullWorker(self.api_client, options, filter_defaults)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_pull_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, message: str, percentage: int):
        """Handle progress updates - batched to prevent GUI overload."""
        try:
            # Ensure progress never goes backwards
            current_value = self.progress_bar.value()
            if percentage < current_value:
                percentage = current_value  # Don't allow backwards progress
            
            # Update progress label and bar immediately (lightweight)
            self.progress_label.setText(message)
            self.progress_bar.setValue(percentage)
            
            # Queue message for batched update (prevents rapid GUI updates that cause segfaults)
            self.pending_messages.append(f"[{percentage}%] {message}")
            
            # Timer is already running continuously - no need to start/stop
            
        except RuntimeError as e:
            # Widget might have been deleted - ignore
            print(f"Progress update error: {e}")
        except Exception as e:
            print(f"Unexpected progress update error: {e}")
    
    def _flush_pending_messages(self):
        """Flush all pending messages to results text widget in one batch."""
        if not self.pending_messages:
            return
        
        try:
            # Append all pending messages at once (more efficient than one-by-one)
            self.results_text.append("\n".join(self.pending_messages))
            self.pending_messages.clear()
            
            # DO NOT call QApplication.processEvents() - causes segfaults on Linux!
            # Qt will update the GUI naturally on the next event loop iteration
            
        except RuntimeError as e:
            print(f"Batch update error: {e}")
        except Exception as e:
            print(f"Unexpected batch update error: {e}")

    def _on_error(self, error_message: str):
        """Handle error from worker."""
        try:
            self.results_text.append(f"\n❌ ERROR: {error_message}")
        except RuntimeError as e:
            print(f"Error display failed (widget deleted?): {e}")
        except Exception as e:
            print(f"Unexpected error display error: {e}")

    def _on_pull_finished(self, success: bool, message: str, config: Optional[Dict]):
        """Handle pull completion."""
        try:
            # Stop update timer and flush any remaining messages
            self.update_timer.stop()
            self._flush_pending_messages()
            
            # Wait for worker thread to fully finish
            if self.worker:
                self.worker.wait(1000)  # Wait up to 1 second for thread to finish
            
            # Re-enable UI
            self._set_ui_enabled(True)

            if success:
                self.progress_label.setText("Pull completed successfully!")
                self.progress_label.setStyleSheet("color: green;")
                
                # Append stats to results
                self.results_text.append(f"\n{'='*50}")
                self.results_text.append("✓ Pull completed successfully!")
                self.results_text.append(f"\n{message}")
                
                # Get config from worker (not from signal parameter to avoid threading issues)
                if self.worker and hasattr(self.worker, 'config'):
                    self.pulled_config = self.worker.config
                else:
                    self.pulled_config = config  # Fallback to parameter if worker unavailable
                
                # Emit signal for other components after a brief delay to ensure thread safety
                if self.pulled_config:
                    # Use QTimer to emit from main thread to avoid memory corruption
                    QTimer.singleShot(100, lambda: self.pull_completed.emit(self.pulled_config))
                
                # Show toast notification instead of dialog
                self.toast_manager.show_success("✓ Configuration pulled successfully!")
                
                # TODO: Re-enable error notification once we solve the memory corruption issue
                # The config object is too large and causes heap corruption when accessed immediately
                # For now, users can check api_errors.log manually if they suspect issues
            else:
                self.progress_label.setText("Pull failed")
                self.progress_label.setStyleSheet("color: red;")
                
                # Show error in results
                self.results_text.append(f"\n{'='*50}")
                self.results_text.append(f"✗ Pull failed!")
                self.results_text.append(f"\nError: {message}")
                
                QMessageBox.warning(self, "Pull Failed", f"Pull operation failed:\n\n{message}")
                
        except RuntimeError as e:
            print(f"Pull finished handler error (widget deleted?): {e}")
        except Exception as e:
            print(f"Unexpected pull finished error: {e}")

    def _set_ui_enabled(self, enabled: bool):
        """Enable or disable UI controls."""
        self.filter_defaults_check.setEnabled(enabled)
        self.select_all_btn.setEnabled(enabled)
        self.select_none_btn.setEnabled(enabled)
        self.pull_btn.setEnabled(enabled)
        self.folder_select_btn.setEnabled(enabled)

    def get_pulled_config(self) -> Optional[Dict[str, Any]]:
        """Get the pulled configuration."""
        return self.pulled_config
