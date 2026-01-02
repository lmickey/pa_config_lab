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
        
        # Source tenant selection (NEW - embedded like Push widget)
        from PyQt6.QtWidgets import QComboBox
        
        source_group = QGroupBox("Source Tenant")
        source_layout = QVBoxLayout()
        
        tenant_select_layout = QHBoxLayout()
        tenant_select_layout.addWidget(QLabel("Pull from:"))
        
        self.source_combo = QComboBox()
        self.source_combo.addItem("-- Select Source Tenant --", None)
        self.source_combo.currentIndexChanged.connect(self._on_source_selected)
        tenant_select_layout.addWidget(self.source_combo, 1)
        
        connect_btn = QPushButton("Connect to Tenant...")
        connect_btn.clicked.connect(self._connect_source)
        tenant_select_layout.addWidget(connect_btn)
        
        source_layout.addLayout(tenant_select_layout)
        
        # Source connection status
        self.source_status_label = QLabel("No source tenant connected")
        self.source_status_label.setStyleSheet("color: gray; padding: 8px; margin-top: 5px;")
        source_layout.addWidget(self.source_status_label)
        
        source_group.setLayout(source_layout)
        layout.addWidget(source_group)

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
        
        This method is called from main_window when a connection is established.
        It also updates the source combo dropdown to reflect the new connection.
        """
        self.api_client = api_client
        self.connection_name = connection_name or "Manual"
        self.pull_btn.setEnabled(api_client is not None)
        self.folder_select_btn.setEnabled(api_client is not None)  # NEW

        if api_client:
            # Update connection status
            self.source_status_label.setText(f"✓ Connected to {self.connection_name}")
            self.source_status_label.setStyleSheet("color: green; padding: 8px; margin-top: 5px; font-weight: bold;")
            
            self.progress_label.setText(
                f"Connected to {self.connection_name} - Ready to pull"
            )
            self.progress_label.setStyleSheet("color: green;")
        else:
            # Clear connection status
            self.source_status_label.setText("No source tenant connected")
            self.source_status_label.setStyleSheet("color: gray; padding: 8px; margin-top: 5px;")
            
            self.progress_label.setText("Connect to a source tenant to begin")
            self.progress_label.setStyleSheet("color: gray;")
    
    def populate_source_tenants(self, tenants: list):
        """
        Populate the source tenant dropdown with saved tenants.
        
        Args:
            tenants: List of tenant dictionaries with 'name' key
        """
        # Clear existing items except the placeholder
        self.source_combo.clear()
        self.source_combo.addItem("-- Select Source Tenant --", None)
        
        # Add saved tenants
        for tenant in tenants:
            tenant_name = tenant.get('name', 'Unknown')
            self.source_combo.addItem(tenant_name, tenant)
    
    def _on_source_selected(self, index):
        """Handle source tenant selection from dropdown."""
        try:
            data = self.source_combo.currentData()
            
            if data is None:
                # Placeholder selected
                self.api_client = None
                self.connection_name = None
                self.source_status_label.setText("No source tenant connected")
                self.source_status_label.setStyleSheet("color: gray; padding: 8px; margin-top: 5px;")
                self.pull_btn.setEnabled(False)
                self.folder_select_btn.setEnabled(False)
                self.progress_label.setText("Connect to a source tenant to begin")
                self.progress_label.setStyleSheet("color: gray;")
                return
            
            # Connect to selected tenant
            self._connect_to_saved_tenant(data)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to select source tenant: {str(e)}"
            )
    
    def _connect_to_saved_tenant(self, tenant_data: Dict[str, Any]):
        """Connect to a saved tenant."""
        from gui.connection_dialog import ConnectionDialog
        from PyQt6.QtCore import QCoreApplication
        from PyQt6.QtWidgets import QProgressDialog
        
        try:
            # Show progress
            progress = QProgressDialog("Connecting to source tenant...", None, 0, 0, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            
            try:
                progress.show()
                QCoreApplication.processEvents()
                
                # Attempt connection using saved credentials
                dialog = ConnectionDialog(self)
                client = dialog.connect_with_saved_tenant(tenant_data)
                
                if client:
                    self.set_api_client(client, tenant_data.get('name', 'Unknown'))
                    
                    # Show success
                    self.toast_manager.show_toast(
                        f"✓ Connected to {tenant_data.get('name', 'Unknown')}",
                        "success",
                        duration=2000
                    )
                else:
                    # Show error after closing progress
                    progress.close()
                    
                    self.error_notification.show_error(
                        f"Connection Failed: Failed to connect to {tenant_data.get('name', 'Unknown')}. Please check credentials."
                    )
                    
                    # Reset combo to placeholder
                    self.source_combo.setCurrentIndex(0)
            finally:
                # Safely close progress dialog
                if progress:
                    progress.close()
                    progress.deleteLater()
                    
        except Exception as e:
            self.error_notification.show_error(
                f"Connection Error: Error connecting to tenant: {str(e)}"
            )
            # Reset combo to placeholder
            self.source_combo.setCurrentIndex(0)
    
    def _connect_source(self):
        """Open connection dialog for source tenant."""
        from gui.connection_dialog import ConnectionDialog
        from PyQt6.QtCore import QCoreApplication
        
        try:
            dialog = ConnectionDialog(self)
            result = dialog.exec()
            
            QCoreApplication.processEvents()
            
            if result and dialog.api_client:
                # Get tenant name
                tenant_name = dialog.tenant_name if hasattr(dialog, 'tenant_name') else "Manual Connection"
                
                self.set_api_client(dialog.api_client, tenant_name)
                
                # Show success
                self.toast_manager.show_toast(
                    f"✓ Connected to {tenant_name}",
                    "success",
                    duration=2000
                )
                
                # Add to combo if not already there
                # Check if this tenant is in the combo
                found = False
                for i in range(self.source_combo.count()):
                    if self.source_combo.itemText(i) == tenant_name:
                        self.source_combo.setCurrentIndex(i)
                        found = True
                        break
                
                if not found and tenant_name != "Manual Connection":
                    # Add to combo
                    self.source_combo.addItem(tenant_name, {"name": tenant_name})
                    self.source_combo.setCurrentIndex(self.source_combo.count() - 1)
                    
        except Exception as e:
            self.error_notification.show_error(
                f"Connection Error: Error opening connection dialog: {str(e)}"
            )

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
