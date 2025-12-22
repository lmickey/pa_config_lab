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


class PullConfigWidget(QWidget):
    """Widget for pulling configurations from Prisma Access."""

    # Signal emitted when pull completes successfully
    pull_completed = pyqtSignal(object)  # config

    def __init__(self, parent=None):
        """Initialize the pull widget."""
        super().__init__(parent)

        self.api_client = None
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
            "Pull configuration from the connected Prisma Access tenant.\n"
            "Select which components to retrieve."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(info)

        # Scroll area for options
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(450)  # Increased from 300 to accommodate infrastructure options

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Options group
        options_group = QGroupBox("Configuration Components")
        options_layout = QVBoxLayout()

        self.folders_check = QCheckBox("Security Policy Folders")
        self.folders_check.setChecked(True)
        self.folders_check.setToolTip("Pull folder structure and organization")
        options_layout.addWidget(self.folders_check)

        self.snippets_check = QCheckBox("Configuration Snippets")
        self.snippets_check.setChecked(True)
        self.snippets_check.setToolTip("Pull configuration snippets")
        options_layout.addWidget(self.snippets_check)

        self.rules_check = QCheckBox("Security Rules")
        self.rules_check.setChecked(True)
        self.rules_check.setToolTip("Pull security policy rules")
        options_layout.addWidget(self.rules_check)

        self.objects_check = QCheckBox("Security Objects")
        self.objects_check.setChecked(True)
        self.objects_check.setToolTip(
            "Pull addresses, address groups, services, service groups, etc."
        )
        options_layout.addWidget(self.objects_check)

        self.profiles_check = QCheckBox("Security Profiles")
        self.profiles_check.setChecked(True)
        self.profiles_check.setToolTip(
            "Pull security profiles (AV, AS, vulnerability, etc.)"
        )
        options_layout.addWidget(self.profiles_check)

        # Custom Applications section (NEW)
        self.applications_check = QCheckBox("Custom Applications")
        self.applications_check.setChecked(False)
        self.applications_check.setToolTip(
            "Select custom applications to capture (rarely needed - most apps are predefined)"
        )
        self.applications_check.stateChanged.connect(self._on_applications_toggle)
        options_layout.addWidget(self.applications_check)

        # Application selector button (initially disabled)
        app_button_layout = QHBoxLayout()
        app_button_layout.addSpacing(20)  # Indent
        self.applications_btn = QPushButton("Select Applications...")
        self.applications_btn.setEnabled(False)
        self.applications_btn.setMaximumWidth(200)
        self.applications_btn.clicked.connect(self._select_applications)
        app_button_layout.addWidget(self.applications_btn)
        app_button_layout.addStretch()
        options_layout.addLayout(app_button_layout)

        # Application selection label
        app_label_layout = QHBoxLayout()
        app_label_layout.addSpacing(20)  # Indent
        self.applications_label = QLabel("No applications selected")
        self.applications_label.setStyleSheet("color: gray; font-size: 10px;")
        app_label_layout.addWidget(self.applications_label)
        app_label_layout.addStretch()
        options_layout.addLayout(app_label_layout)

        # Store selected applications
        self.selected_applications = []

        options_group.setLayout(options_layout)
        scroll_layout.addWidget(options_group)

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

    def set_api_client(self, api_client):
        """Set the API client for pull operations."""
        self.api_client = api_client
        self.pull_btn.setEnabled(api_client is not None)

        if api_client:
            self.progress_label.setText(
                f"Connected to {api_client.tsg_id} - Ready to pull"
            )
            self.progress_label.setStyleSheet("color: green;")
        else:
            self.progress_label.setText("Not connected")
            self.progress_label.setStyleSheet("color: gray;")

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
        """Select all checkboxes."""
        self.folders_check.setChecked(True)
        self.snippets_check.setChecked(True)
        self.rules_check.setChecked(True)
        self.objects_check.setChecked(True)
        self.profiles_check.setChecked(True)
        self.applications_check.setChecked(False)  # Don't auto-select
        # Infrastructure
        self.remote_networks_check.setChecked(True)
        self.service_connections_check.setChecked(True)
        self.ipsec_tunnels_check.setChecked(True)
        self.mobile_users_check.setChecked(True)
        self.hip_check.setChecked(True)
        self.regions_check.setChecked(True)

    def _select_none(self):
        """Deselect all checkboxes."""
        self.folders_check.setChecked(False)
        self.snippets_check.setChecked(False)
        self.rules_check.setChecked(False)
        self.objects_check.setChecked(False)
        self.profiles_check.setChecked(False)
        self.applications_check.setChecked(False)
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
            # Show connection prompt
            reply = QMessageBox.question(
                self,
                "Connect to Prisma Access",
                "You need to connect to Prisma Access before pulling configuration.\n\n"
                "Would you like to connect now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Import and show connection dialog
                from gui.connection_dialog import ConnectionDialog
                
                dialog = ConnectionDialog(self)
                if dialog.exec():
                    # Get the API client from the dialog
                    self.api_client = dialog.get_api_client()
                    
                    if not self.api_client:
                        QMessageBox.warning(
                            self,
                            "Connection Failed",
                            "Failed to connect to Prisma Access. Please try again."
                        )
                        return
                    
                    # Connection successful
                    QMessageBox.information(
                        self,
                        "Connected",
                        "Successfully connected to Prisma Access.\n\nYou can now pull the configuration."
                    )
                else:
                    # User cancelled connection
                    return
            else:
                # User declined to connect
                return
        
        # Validate that we have an API client now
        if not self.api_client:
            QMessageBox.warning(
                self, "Not Connected", "Please connect to Prisma Access first."
            )
            return

        # Validate at least one option is selected
        if not any(
            [
                self.folders_check.isChecked(),
                self.snippets_check.isChecked(),
                self.rules_check.isChecked(),
                self.objects_check.isChecked(),
                self.profiles_check.isChecked(),
            ]
        ):
            QMessageBox.warning(
                self,
                "No Options Selected",
                "Please select at least one configuration component to pull.",
            )
            return

        # Gather options
        options = {
            "folders": self.folders_check.isChecked(),
            "snippets": self.snippets_check.isChecked(),
            "rules": self.rules_check.isChecked(),
            "objects": self.objects_check.isChecked(),
            "profiles": self.profiles_check.isChecked(),
            # NEW: Custom applications
            "application_names": self.selected_applications if self.applications_check.isChecked() and self.selected_applications else None,
            # NEW: Infrastructure options
            "include_remote_networks": self.remote_networks_check.isChecked(),
            "include_service_connections": self.service_connections_check.isChecked(),
            "include_ipsec_tunnels": self.ipsec_tunnels_check.isChecked(),
            "include_mobile_users": self.mobile_users_check.isChecked(),
            "include_hip": self.hip_check.isChecked(),
            "include_regions": self.regions_check.isChecked(),
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
                
                # Emit signal for other components
                if self.pulled_config:
                    self.pull_completed.emit(self.pulled_config)
                
                QMessageBox.information(
                    self, "Success", "Configuration pulled successfully!"
                )
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
        self.folders_check.setEnabled(enabled)
        self.snippets_check.setEnabled(enabled)
        self.rules_check.setEnabled(enabled)
        self.objects_check.setEnabled(enabled)
        self.profiles_check.setEnabled(enabled)
        self.filter_defaults_check.setEnabled(enabled)
        self.select_all_btn.setEnabled(enabled)
        self.select_none_btn.setEnabled(enabled)
        self.pull_btn.setEnabled(enabled)

    def get_pulled_config(self) -> Optional[Dict[str, Any]]:
        """Get the pulled configuration."""
        return self.pulled_config
