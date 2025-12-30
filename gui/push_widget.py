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
        self.destination_name = None  # Name of destination tenant (for display)
        self.config = None
        self.worker = None
        
        # Phase 3: Selective push
        self.loaded_config = None  # Currently loaded config
        self.selected_items = None  # Selected components to push
        self.saved_configs_manager = None  # Will be set by parent

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)  # Add more spacing between sections

        # Title
        title = QLabel("<h2>Push Configuration</h2>")
        layout.addWidget(title)

        info = QLabel(
            "Select destination tenant and configure push options."
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
        self.dest_status_label.setStyleSheet("color: gray; padding: 8px; margin-top: 5px;")
        dest_layout.addWidget(self.dest_status_label)
        
        dest_group.setLayout(dest_layout)
        layout.addWidget(dest_group)

        # Two-column layout for options
        options_container = QHBoxLayout()
        options_container.setSpacing(20)

        # Left column: Conflict resolution
        conflict_group = QGroupBox("Conflict Resolution")
        conflict_layout = QVBoxLayout()
        conflict_layout.setSpacing(10)

        self.conflict_button_group = QButtonGroup()

        self.skip_radio = QRadioButton("Skip conflicting items")
        self.skip_radio.setToolTip("Do not push items that already exist")
        self.skip_radio.setChecked(True)
        self.conflict_button_group.addButton(self.skip_radio, 0)
        conflict_layout.addWidget(self.skip_radio)

        self.overwrite_radio = QRadioButton("Overwrite existing items")
        self.overwrite_radio.setToolTip("Replace existing items with new configuration")
        self.conflict_button_group.addButton(self.overwrite_radio, 1)
        conflict_layout.addWidget(self.overwrite_radio)

        self.rename_radio = QRadioButton("Rename with suffix")
        self.rename_radio.setToolTip("Create new items with '-copy' suffix")
        self.conflict_button_group.addButton(self.rename_radio, 2)
        conflict_layout.addWidget(self.rename_radio)

        conflict_layout.addStretch()
        conflict_group.setLayout(conflict_layout)
        options_container.addWidget(conflict_group)

        # Right column: Push options
        push_options_group = QGroupBox("Push Options")
        push_options_layout = QVBoxLayout()
        push_options_layout.setSpacing(10)

        self.dry_run_check = QCheckBox("Dry Run (simulate only)")
        self.dry_run_check.setToolTip("Test the push without making changes")
        self.dry_run_check.setChecked(False)
        push_options_layout.addWidget(self.dry_run_check)

        self.validate_check = QCheckBox("Validate before push")
        self.validate_check.setToolTip("Validate configuration structure and dependencies")
        self.validate_check.setChecked(True)
        push_options_layout.addWidget(self.validate_check)

        push_options_layout.addStretch()
        push_options_group.setLayout(push_options_layout)
        options_container.addWidget(push_options_group)

        layout.addLayout(options_container)

        # Status bar
        self.status_label = QLabel("Load configuration in 'Select Components' tab")
        self.status_label.setStyleSheet(
            "color: gray; padding: 12px; background-color: #f0f0f0; border-radius: 5px; font-size: 13px;"
        )
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Action button (bottom right)
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.push_btn = QPushButton("🚀 Push Configuration")
        self.push_btn.setMinimumWidth(180)
        self.push_btn.setMinimumHeight(40)
        self.push_btn.setEnabled(False)
        self.push_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 10px 20px; font-size: 14px; font-weight: bold; border-radius: 5px; }"
            "QPushButton:hover { background-color: #45a049; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        self.push_btn.clicked.connect(self._start_push)
        button_layout.addWidget(self.push_btn)

        layout.addLayout(button_layout)

        # Progress section (initially hidden)
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
        
        # Load destination tenants on initialization
        self._load_destination_tenants()

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
                self.destination_name = None
                self.dest_status_label.setText("No destination selected")
                self.dest_status_label.setStyleSheet("color: gray; padding: 5px;")
            elif data["type"] == "source":
                # Use source tenant
                self.destination_client = data["client"]
                self.destination_name = "Source Tenant"
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
                self.destination_name = tenant['name']  # Store tenant name
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
                    self.destination_name = connection_name  # Store connection name
                    
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
            self.status_label.setText("❌ Select destination tenant first")
            self.status_label.setStyleSheet(
                "color: orange; padding: 10px; background-color: #fff4e6;"
            )
            self.push_btn.setEnabled(False)
            self.progress_label.setText("Select destination tenant")
        elif not self.config:
            self.status_label.setText("❌ No configuration loaded - Pull or load a config first")
            self.status_label.setStyleSheet(
                "color: orange; padding: 10px; background-color: #fff4e6;"
            )
            self.push_btn.setEnabled(False)
            self.progress_label.setText("Load or pull a configuration")
        elif not self.selected_items:
            self.status_label.setText("❌ Go to 'Select Components' tab to choose what to push")
            self.status_label.setStyleSheet(
                "color: orange; padding: 10px; background-color: #fff4e6;"
            )
            self.push_btn.setEnabled(False)
            self.progress_label.setText("Select components to push")
        else:
            # Count selected items
            folders_count = len(self.selected_items.get('folders', []))
            snippets_count = len(self.selected_items.get('snippets', []))
            objects = self.selected_items.get('objects', {})
            objects_count = sum(len(v) for v in objects.values() if isinstance(v, list))
            infrastructure = self.selected_items.get('infrastructure', {})
            infra_count = sum(len(v) for v in infrastructure.values() if isinstance(v, list))
            total_items = folders_count + snippets_count + objects_count + infra_count
            
            # Build status message
            status_parts = []
            if folders_count > 0:
                status_parts.append(f"{folders_count} folder{'s' if folders_count != 1 else ''}")
            if snippets_count > 0:
                status_parts.append(f"{snippets_count} snippet{'s' if snippets_count != 1 else ''}")
            if objects_count > 0:
                status_parts.append(f"{objects_count} object{'s' if objects_count != 1 else ''}")
            if infra_count > 0:
                status_parts.append(f"{infra_count} infrastructure")
            
            # Use tenant name if available, otherwise TSG ID
            dest_display = self.destination_name if self.destination_name else self.destination_client.tsg_id
            
            # Check if source and destination are the same tenant
            # Get source TSG ID from either live connection or config metadata
            source_tsg_id = None
            if self.api_client:
                source_tsg_id = self.api_client.tsg_id
            elif self.config and 'metadata' in self.config:
                source_tsg_id = self.config['metadata'].get('source_tenant')
            
            dest_tsg_id = self.destination_client.tsg_id if self.destination_client else None
            
            is_same_tenant = (source_tsg_id and dest_tsg_id and source_tsg_id == dest_tsg_id)
            
            if is_same_tenant:
                # Warning: pushing to same tenant
                status_text = f"⚠️ Warning: Pushing {total_items} items to the Same Tenant"
                if status_parts:
                    status_text += f" ({', '.join(status_parts)})"
                
                self.status_label.setText(status_text)
                self.status_label.setStyleSheet(
                    "color: #F57F17; padding: 12px; background-color: #FFF9C4; border-radius: 5px; "
                    "font-size: 13px; border: 2px solid #FBC02D; font-weight: bold;"
                )
                # Make push button yellow too
                self.push_btn.setStyleSheet(
                    "QPushButton { background-color: #FBC02D; color: #000000; font-weight: bold; "
                    "padding: 8px 16px; border-radius: 4px; border: 2px solid #F9A825; }"
                    "QPushButton:hover { background-color: #F9A825; }"
                    "QPushButton:pressed { background-color: #F57F17; }"
                )
                self.progress_label.setText("Warning: Same tenant")
                self.progress_label.setStyleSheet("color: #F57F17; font-weight: bold;")
            else:
                # Normal: pushing to different tenant
                status_text = f"✓ Ready to push {total_items} items to {dest_display}"
                if status_parts:
                    status_text += f" ({', '.join(status_parts)})"
                
                self.status_label.setText(status_text)
                self.status_label.setStyleSheet(
                    "color: #2e7d32; padding: 12px; background-color: #e8f5e9; border-radius: 5px; "
                    "font-size: 13px; border: 1px solid #4CAF50;"
                )
                # Reset push button to default style
                self.push_btn.setStyleSheet("")
                self.progress_label.setText("Ready to push")
                self.progress_label.setStyleSheet("color: green;")
            
            self.push_btn.setEnabled(True)

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

        # Show preview dialog first (analyzes conflicts)
        from gui.dialogs.push_preview_dialog import PushPreviewDialog
        
        dest_display = self.destination_name if self.destination_name else self.destination_client.tsg_id
        
        preview_dialog = PushPreviewDialog(
            self.destination_client,
            self.selected_items,
            dest_display,
            resolution,
            self
        )
        
        # Store destination config before dialog closes
        result = preview_dialog.exec()
        destination_config = preview_dialog.destination_config if hasattr(preview_dialog, 'destination_config') else None
        
        if not result:
            # User cancelled from preview
            return

        # Show warning confirmation AFTER preview
        if not dry_run:
            # Use warning dialog with red border and ! icon
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("⚠️ Confirm Push")
            msg_box.setText(f"<b>Push configuration to {dest_display}?</b>")
            msg_box.setInformativeText(
                f"Conflict Resolution: {resolution}\n\n"
                f"⚠️ This will modify the target tenant.\n"
                f"This action cannot be undone."
            )
            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg_box.setDefaultButton(QMessageBox.StandardButton.No)
            
            # Style the dialog with red border
            msg_box.setStyleSheet("""
                QMessageBox {
                    border: 3px solid #f44336;
                    background-color: #fff3f3;
                }
                QLabel {
                    color: #d32f2f;
                }
            """)
            
            reply = msg_box.exec()
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

        # Create and start worker
        from gui.workers import SelectivePushWorker
        
        self.worker = SelectivePushWorker(
            self.destination_client,
            self.selected_items,
            destination_config,
            resolution
        )
        self.worker.progress.connect(self._on_push_progress)
        self.worker.finished.connect(self._on_push_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_push_progress(self, message: str, current: int, total: int):
        """Handle selective push progress updates."""
        self.progress_label.setText(message)
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)

    def _on_progress(self, message: str, percentage: int):
        """Handle progress updates."""
        self.progress_label.setText(message)
        self.progress_bar.setValue(percentage)

    def _on_push_finished(self, success: bool, message: str, result: Optional[Dict]):
        """Handle push completion."""
        try:
            # Re-enable UI
            self._set_ui_enabled(True)

            if success:
                # Update status banner with success message
                # Defensive: handle various result structures
                summary = {}
                try:
                    if result and isinstance(result, dict):
                        if 'results' in result and isinstance(result['results'], dict):
                            summary = result['results'].get('summary', {})
                        elif 'summary' in result:
                            summary = result.get('summary', {})
                except:
                    pass
                
                total = summary.get('total', 0) if isinstance(summary, dict) else 0
                created = summary.get('created', 0) if isinstance(summary, dict) else 0
                updated = summary.get('updated', 0) if isinstance(summary, dict) else 0
                deleted = summary.get('deleted', 0) if isinstance(summary, dict) else 0
                renamed = summary.get('renamed', 0) if isinstance(summary, dict) else 0
                skipped = summary.get('skipped', 0) if isinstance(summary, dict) else 0
                failed = summary.get('failed', 0) if isinstance(summary, dict) else 0
                
                try:
                    status_msg = f"✅ Push completed successfully! Created: {created}, Updated: {updated}"
                    if deleted > 0:
                        status_msg += f", Deleted: {deleted}"
                    if renamed > 0:
                        status_msg += f", Renamed: {renamed}"
                    status_msg += f", Skipped: {skipped}"
                    if failed > 0:
                        status_msg += f", Failed: {failed}"
                    
                    self.status_label.setText(status_msg)
                    self.status_label.setStyleSheet(
                        "color: #2e7d32; background-color: #e8f5e9; border: 1px solid #4CAF50; "
                        "border-radius: 5px; padding: 10px; font-weight: bold;"
                    )
                    self.status_label.setVisible(True)
                except Exception as label_err:
                    print(f"Error updating status label: {label_err}")
                
                # Update progress label
                try:
                    self.progress_label.setText("Push completed successfully!")
                    self.progress_label.setStyleSheet("color: green;")
                except Exception as prog_err:
                    print(f"Error updating progress label: {prog_err}")
                
                # Show detailed results
                try:
                    if message and isinstance(message, str):
                        self.results_text.setPlainText(message)
                except Exception as results_err:
                    print(f"Error updating results text: {results_err}")

                # Emit signal (wrapped in try/except)
                try:
                    self.push_completed.emit(result)
                except Exception as e:
                    print(f"Error emitting push_completed signal: {e}")
            else:
                # Update status banner with error message
                self.status_label.setText(f"❌ Push failed: {message}")
                self.status_label.setStyleSheet(
                    "color: #c62828; background-color: #ffebee; border: 1px solid #f44336; "
                    "border-radius: 5px; padding: 10px; font-weight: bold;"
                )
                self.status_label.setVisible(True)
                
                self.progress_label.setText("Push failed")
                self.progress_label.setStyleSheet("color: red;")
                self.results_text.setPlainText(f"Error: {message}")
        except Exception as e:
            print(f"Error in _on_push_finished: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Clean up worker after a delay to prevent premature garbage collection
            try:
                from PyQt6.QtCore import QTimer
                if hasattr(self, 'worker') and self.worker:
                    QTimer.singleShot(1000, lambda: self.worker.deleteLater() if hasattr(self, 'worker') else None)
            except:
                pass

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
        # Phase 3: Enable push only if we have config, destination, AND selection
        # Convert to bool to avoid passing dict to setEnabled
        should_enable = enabled and bool(self.destination_client) and bool(self.config) and bool(self.selected_items)
        self.push_btn.setEnabled(should_enable)
    
    # Phase 3: Receive selection from selection widget
    
    def set_selected_items(self, selected_items):
        """Set the selected items from selection widget."""
        self.selected_items = selected_items
        self._update_status()
