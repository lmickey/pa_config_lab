"""
Push configuration widget for the GUI.

This module provides the UI for pushing configurations to Prisma Access,
including conflict detection and resolution options.
"""

from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QRadioButton,
    QPushButton,
    QLabel,
    QProgressBar,
    QTextEdit,
    QCheckBox,
    QMessageBox,
    QButtonGroup,
    QComboBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from gui.workers import PushWorker


class PushConfigWidget(QWidget):
    """Widget for pushing configurations to Prisma Access."""

    # Signal emitted when push completes
    push_completed = pyqtSignal(object)  # result

    def __init__(self, parent=None):
        """Initialize the push widget."""
        super().__init__(parent)

        self.api_client = None
        self.destination_client = None  # Separate destination tenant
        self.config = None
        self.worker = None

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("<h2>Push Configuration</h2>")
        layout.addWidget(title)

        info = QLabel(
            "Push configuration to a Prisma Access tenant.\n"
            "Select destination tenant and configure conflict resolution."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(info)

        # Destination tenant selection
        dest_group = QGroupBox("Destination Tenant")
        dest_layout = QVBoxLayout()
        
        tenant_select_layout = QHBoxLayout()
        
        tenant_select_layout.addWidget(QLabel("Push to:"))
        
        self.destination_combo = QComboBox()
        self.destination_combo.addItem("-- Select Destination --", None)
        self.destination_combo.currentIndexChanged.connect(self._on_destination_selected)
        tenant_select_layout.addWidget(self.destination_combo, 1)
        
        connect_btn = QPushButton("Connect to Different Tenant...")
        connect_btn.clicked.connect(self._connect_destination)
        tenant_select_layout.addWidget(connect_btn)
        
        dest_layout.addLayout(tenant_select_layout)
        
        # Destination status
        self.dest_status_label = QLabel("No destination selected")
        self.dest_status_label.setStyleSheet("color: gray; padding: 5px;")
        dest_layout.addWidget(self.dest_status_label)
        
        dest_group.setLayout(dest_layout)
        layout.addWidget(dest_group)

        # Status
        self.status_label = QLabel("No configuration loaded")
        self.status_label.setStyleSheet(
            "color: gray; padding: 10px; background-color: #f0f0f0;"
        )
        layout.addWidget(self.status_label)

        # Conflict resolution group
        conflict_group = QGroupBox("Conflict Resolution")
        conflict_layout = QVBoxLayout()

        self.conflict_button_group = QButtonGroup()

        self.skip_radio = QRadioButton("Skip - Skip conflicting items")
        self.skip_radio.setToolTip("Do not push items that already exist")
        self.skip_radio.setChecked(True)
        self.conflict_button_group.addButton(self.skip_radio, 0)
        conflict_layout.addWidget(self.skip_radio)

        self.overwrite_radio = QRadioButton("Overwrite - Replace existing items")
        self.overwrite_radio.setToolTip(
            "Overwrite existing items with new configuration"
        )
        self.conflict_button_group.addButton(self.overwrite_radio, 1)
        conflict_layout.addWidget(self.overwrite_radio)

        self.rename_radio = QRadioButton(
            "Rename - Create new items with modified names"
        )
        self.rename_radio.setToolTip("Create new items with '-copy' suffix")
        self.conflict_button_group.addButton(self.rename_radio, 2)
        conflict_layout.addWidget(self.rename_radio)

        conflict_layout.addWidget(
            QLabel(
                "<small><b>Note:</b> Conflicts occur when items with the same name already "
                "exist in the target tenant.</small>"
            )
        )

        conflict_group.setLayout(conflict_layout)
        layout.addWidget(conflict_group)

        # Push options
        options_group = QGroupBox("Push Options")
        options_layout = QVBoxLayout()

        self.dry_run_check = QCheckBox("Dry Run (simulate without making changes)")
        self.dry_run_check.setToolTip(
            "Test the push without actually making any changes"
        )
        self.dry_run_check.setChecked(False)
        options_layout.addWidget(self.dry_run_check)

        self.validate_check = QCheckBox("Validate configuration before push")
        self.validate_check.setToolTip(
            "Validate configuration structure and dependencies"
        )
        self.validate_check.setChecked(True)
        options_layout.addWidget(self.validate_check)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.push_btn = QPushButton("Push Configuration")
        self.push_btn.setMinimumWidth(150)
        self.push_btn.setEnabled(False)
        self.push_btn.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; padding: 8px; }"
            "QPushButton:hover { background-color: #0b7dda; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        self.push_btn.clicked.connect(self._start_push)
        button_layout.addWidget(self.push_btn)

        layout.addLayout(button_layout)

        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()

        self.progress_label = QLabel("Ready to push")
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
        self.results_text.setPlaceholderText("Push results will appear here...")
        results_layout.addWidget(self.results_text)

        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        layout.addStretch()

    def set_api_client(self, api_client):
        """Set the API client for push operations (source tenant)."""
        self.api_client = api_client
        self._load_destination_tenants()
        self._update_status()
    
    def _load_destination_tenants(self):
        """Load available destination tenants."""
        from config.tenant_manager import TenantManager
        
        # Block signals during load
        self.destination_combo.blockSignals(True)
        
        # Clear existing (except first item)
        while self.destination_combo.count() > 1:
            self.destination_combo.removeItem(1)
        
        # Add "Use Source Tenant" option if connected
        if self.api_client:
            self.destination_combo.addItem(
                f"Use Source Tenant ({self.api_client.tsg_id})",
                {"type": "source", "client": self.api_client}
            )
        
        # Add saved tenants
        manager = TenantManager()
        tenants = manager.list_tenants(sort_by="last_used")
        
        for tenant in tenants:
            display_name = f"{tenant['name']} ({tenant['tsg_id']})"
            self.destination_combo.addItem(display_name, {"type": "saved", "tenant": tenant})
        
        # Re-enable signals
        self.destination_combo.blockSignals(False)
    
    def _on_destination_selected(self, index):
        """Handle destination tenant selection."""
        try:
            data = self.destination_combo.currentData()
            
            if data is None:
                # No selection
                self.destination_client = None
                self.dest_status_label.setText("No destination selected")
                self.dest_status_label.setStyleSheet("color: gray; padding: 5px;")
            elif data["type"] == "source":
                # Use source tenant
                self.destination_client = data["client"]
                self.dest_status_label.setText(f"✓ Using source tenant: {self.destination_client.tsg_id}")
                self.dest_status_label.setStyleSheet("color: green; padding: 5px;")
            elif data["type"] == "saved":
                # Saved tenant - need to connect
                tenant = data["tenant"]
                self._connect_to_tenant(tenant)
            
            self._update_status()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Selection Error",
                f"Error selecting destination tenant:\n\n{str(e)}\n\nPlease check the console for details."
            )
            import traceback
            traceback.print_exc()
            self.destination_combo.setCurrentIndex(0)
            self.destination_client = None
            self._update_status()
    
    def _connect_to_tenant(self, tenant):
        """Connect to a saved tenant."""
        from prisma.api_client import PrismaAccessAPIClient
        from PyQt6.QtWidgets import QProgressDialog
        from PyQt6.QtCore import QTimer, QCoreApplication
        
        # Show progress
        progress = QProgressDialog("Connecting to destination tenant...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        
        try:
            # Process events before showing to avoid issues
            QCoreApplication.processEvents()
            progress.show()
            QCoreApplication.processEvents()
            
            # Create client
            client = PrismaAccessAPIClient(
                tsg_id=tenant['tsg_id'],
                api_user=tenant['client_id'],
                api_secret=tenant['client_secret']
            )
            
            # Test authentication
            if client.token:
                self.destination_client = client
                self.dest_status_label.setText(f"✓ Connected to: {tenant['name']}")
                self.dest_status_label.setStyleSheet("color: green; padding: 5px;")
                
                # Mark as used
                from config.tenant_manager import TenantManager
                manager = TenantManager()
                manager.mark_used(tenant['id'])
            else:
                self.destination_combo.setCurrentIndex(0)
                self.destination_client = None
                # Show error after closing progress
                progress.close()
                QCoreApplication.processEvents()
                QMessageBox.critical(self, "Connection Failed", "Failed to authenticate with destination tenant.")
                return
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.destination_combo.setCurrentIndex(0)
            self.destination_client = None
            # Show error after closing progress
            progress.close()
            QCoreApplication.processEvents()
            QMessageBox.critical(
                self, 
                "Connection Error", 
                f"Error connecting to tenant:\n\n{str(e)}"
            )
            return
        finally:
            # Safely close progress dialog
            if progress:
                progress.close()
                progress.deleteLater()
            # Process events to ensure clean close
            QCoreApplication.processEvents()
            # Update status after a brief delay
            QTimer.singleShot(100, self._update_status)
    
    def _connect_destination(self):
        """Open connection dialog for destination tenant."""
        from gui.connection_dialog import ConnectionDialog
        from PyQt6.QtCore import QCoreApplication
        
        try:
            dialog = ConnectionDialog(self)
            result = dialog.exec()
            
            # Process events to ensure dialog is fully closed
            QCoreApplication.processEvents()
            
            if result:
                # Get data before dialog is deleted
                client = dialog.get_api_client()
                connection_name = dialog.get_connection_name() or "Manual"
                
                # Delete dialog explicitly
                dialog.deleteLater()
                QCoreApplication.processEvents()
                
                if client:
                    self.destination_client = client
                    
                    # Add to combo if not already there
                    self.destination_combo.blockSignals(True)
                    self.destination_combo.addItem(
                        f"{connection_name} ({client.tsg_id})",
                        {"type": "manual", "client": client}
                    )
                    self.destination_combo.setCurrentIndex(self.destination_combo.count() - 1)
                    self.destination_combo.blockSignals(False)
                    
                    self.dest_status_label.setText(f"✓ Connected to: {connection_name}")
                    self.dest_status_label.setStyleSheet("color: green; padding: 5px;")
                    self._update_status()
            else:
                # Dialog cancelled
                dialog.deleteLater()
                QCoreApplication.processEvents()
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Connection Error",
                f"Error connecting to destination tenant:\n\n{str(e)}"
            )

    def set_config(self, config: Optional[Dict[str, Any]]):
        """Set the configuration to push."""
        self.config = config
        self._update_status()

    def _update_status(self):
        """Update status label and enable/disable push button."""
        if not self.destination_client:
            self.status_label.setText("❌ No destination tenant selected")
            self.status_label.setStyleSheet(
                "color: orange; padding: 10px; background-color: #fff4e6;"
            )
            self.push_btn.setEnabled(False)
            self.progress_label.setText("Select destination tenant")
        elif not self.config:
            self.status_label.setText("❌ No configuration loaded")
            self.status_label.setStyleSheet(
                "color: orange; padding: 10px; background-color: #fff4e6;"
            )
            self.push_btn.setEnabled(False)
            self.progress_label.setText("No configuration")
        else:
            # Count items
            total_items = self._count_items()
            self.status_label.setText(
                f"✓ Ready to push | Target: {self.destination_client.tsg_id} | Items: {total_items}"
            )
            self.status_label.setStyleSheet(
                "color: green; padding: 10px; background-color: #e6ffe6;"
            )
            self.push_btn.setEnabled(True)
            self.progress_label.setText("Ready to push")
            self.progress_label.setStyleSheet("color: green;")

    def _count_items(self) -> int:
        """Count total items in configuration."""
        if not self.config:
            return 0

        count = 0
        sec_policies = self.config.get("security_policies", {})
        count += len(sec_policies.get("snippets", []))
        count += len(sec_policies.get("security_rules", []))

        objects = self.config.get("objects", {})
        count += len(objects.get("addresses", []))
        count += len(objects.get("address_groups", []))
        count += len(objects.get("services", []))
        count += len(objects.get("service_groups", []))

        return count

    def _start_push(self):
        """Start the push operation."""
        if not self.destination_client or not self.config:
            return

        # Get conflict resolution
        if self.skip_radio.isChecked():
            resolution = "SKIP"
        elif self.overwrite_radio.isChecked():
            resolution = "OVERWRITE"
        else:
            resolution = "RENAME"

        dry_run = self.dry_run_check.isChecked()

        # Confirm push
        if not dry_run:
            reply = QMessageBox.question(
                self,
                "Confirm Push",
                f"Push configuration to {self.destination_client.tsg_id}?\n\n"
                f"Conflict Resolution: {resolution}\n"
                f"This will modify the target tenant.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # Disable UI during push
        self._set_ui_enabled(False)

        # Show progress bar
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.progress_label.setText("Preparing to push configuration...")

        # Clear previous results
        self.results_text.clear()

        # Create and start worker (use destination_client)
        self.worker = PushWorker(self.destination_client, self.config, resolution, dry_run)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_push_finished)
        self.worker.error.connect(self._on_error)
        self.worker.conflicts_detected.connect(self._on_conflicts)
        self.worker.start()

    def _on_progress(self, message: str, percentage: int):
        """Handle progress updates."""
        self.progress_label.setText(message)
        self.progress_bar.setValue(percentage)

    def _on_push_finished(self, success: bool, message: str, result: Optional[Dict]):
        """Handle push completion."""
        # Re-enable UI
        self._set_ui_enabled(True)

        if success:
            self.progress_label.setText("Push completed successfully!")
            self.progress_label.setStyleSheet("color: green;")
            self.results_text.setPlainText(message)

            # Emit signal
            self.push_completed.emit(result)

            QMessageBox.information(
                self, "Success", "Configuration pushed successfully!"
            )
        else:
            self.progress_label.setText("Push failed")
            self.progress_label.setStyleSheet("color: red;")
            self.results_text.setPlainText(f"Error: {message}")

    def _on_error(self, error_message: str):
        """Handle errors."""
        self.progress_label.setText("Error occurred")
        self.progress_label.setStyleSheet("color: red;")
        QMessageBox.critical(self, "Error", error_message)

    def _on_conflicts(self, conflicts: list):
        """Handle detected conflicts."""
        conflict_text = f"Detected {len(conflicts)} conflicts:\n\n"
        for conflict in conflicts[:10]:  # Show first 10
            conflict_text += f"- {conflict.get('name', 'Unknown')}\n"
        if len(conflicts) > 10:
            conflict_text += f"\n... and {len(conflicts) - 10} more"

        self.results_text.setPlainText(conflict_text)

    def _set_ui_enabled(self, enabled: bool):
        """Enable or disable UI controls."""
        self.skip_radio.setEnabled(enabled)
        self.overwrite_radio.setEnabled(enabled)
        self.rename_radio.setEnabled(enabled)
        self.dry_run_check.setEnabled(enabled)
        self.validate_check.setEnabled(enabled)
        self.push_btn.setEnabled(enabled and self.api_client and self.config)
