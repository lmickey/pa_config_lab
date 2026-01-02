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
    QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal

from gui.workers import PushWorker
from gui.widgets import TenantSelectorWidget
from gui.toast_notification import ToastManager, DismissibleErrorNotification


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
        self.push_completed_successfully = False  # Track if push just completed
        
        # Toast and error notification managers
        self.toast_manager = ToastManager(self)
        self.error_notification = DismissibleErrorNotification(self)

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

        # Destination tenant selection (using reusable widget)
        self.tenant_selector = TenantSelectorWidget(
            parent=self,
            title="Destination Tenant",
            label="Push to:",
            show_success_toast=lambda msg, dur: self.toast_manager.show_success(msg, dur),
            show_error_banner=lambda msg: self.error_notification.show_error(msg)
        )
        self.tenant_selector.connection_changed.connect(self._on_destination_changed)
        layout.addWidget(self.tenant_selector)

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
        
        # Add buttons for results actions
        results_buttons_layout = QHBoxLayout()
        
        self.copy_results_btn = QPushButton("📋 Copy Results")
        self.copy_results_btn.setToolTip("Copy all results to clipboard")
        self.copy_results_btn.clicked.connect(self._copy_results)
        self.copy_results_btn.setEnabled(False)
        results_buttons_layout.addWidget(self.copy_results_btn)
        
        self.view_details_btn = QPushButton("📄 View Full Details")
        self.view_details_btn.setToolTip("Open detailed log viewer")
        self.view_details_btn.clicked.connect(self._view_full_details)
        self.view_details_btn.setEnabled(False)
        results_buttons_layout.addWidget(self.view_details_btn)
        
        results_buttons_layout.addStretch()
        results_layout.addLayout(results_buttons_layout)

        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        layout.addStretch()

    def set_api_client(self, api_client):
        """Set the API client for push operations (source tenant)."""
        self.api_client = api_client
        self._update_status()
    
    def _on_destination_changed(self, api_client, tenant_name: str):
        """
        Handle destination connection changes from the tenant selector.
        
        Args:
            api_client: The API client (or None if disconnected)
            tenant_name: Name of the tenant (or empty string if disconnected)
        """
        self.destination_client = api_client
        self.destination_name = tenant_name if tenant_name else None
        self._update_status()
    
    def populate_destination_tenants(self, tenants: list):
        """
        Populate the destination tenant dropdown with saved tenants.
        
        Args:
            tenants: List of tenant dictionaries with 'name' key
        """
        self.tenant_selector.populate_tenants(tenants)

    def set_config(self, config: Optional[Dict[str, Any]]):
        """Set the configuration to push."""
        self.config = config
        self._update_status()

    def _update_status(self):
        """Update status label and enable/disable push button."""
        # Don't overwrite success message after push completes
        if self.push_completed_successfully:
            return
        
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

        # Reset push completion flag
        self.push_completed_successfully = False
        
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
                # Mark push as completed successfully
                self.push_completed_successfully = True
                
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
                could_not_overwrite = summary.get('could_not_overwrite', 0) if isinstance(summary, dict) else 0
                
                # Calculate unique items from detailed results
                results_data = result.get('results', {}) if isinstance(result, dict) else {}
                all_details = results_data.get('details', []) if isinstance(results_data, dict) else []
                unique_items = set()
                for d in all_details:
                    item_key = (d.get('type'), d.get('name'), d.get('folder'))
                    unique_items.add(item_key)
                unique_count = len(unique_items)
                
                # Determine status based on results
                has_failures = (failed > 0 or could_not_overwrite > 0)
                has_successes = (created > 0 or updated > 0 or deleted > 0 or renamed > 0)
                
                try:
                    if has_failures and has_successes:
                        # Partial success - yellow
                        status_msg = f"⚠️ Push completed with issues ({unique_count} items)"
                        status_color = "#F57F17"  # Dark yellow/amber
                        status_bg = "#FFF9C4"     # Light yellow
                        status_border = "#FBC02D" # Medium yellow
                        progress_text = "Completed with issues"
                        progress_color = "#F57F17"
                    elif has_failures and not has_successes:
                        # All failed - red
                        status_msg = f"❌ Push failed ({unique_count} items)"
                        status_color = "#c62828"  # Dark red
                        status_bg = "#ffebee"     # Light red
                        status_border = "#f44336" # Medium red
                        progress_text = "Push failed"
                        progress_color = "red"
                    else:
                        # All successful - green
                        status_msg = f"✅ Push completed successfully ({unique_count} items)"
                        status_color = "#2e7d32"  # Dark green
                        status_bg = "#e8f5e9"     # Light green
                        status_border = "#4CAF50" # Medium green
                        progress_text = "Push completed successfully"
                        progress_color = "green"
                    
                    self.status_label.setText(status_msg)
                    self.status_label.setStyleSheet(
                        f"color: {status_color}; background-color: {status_bg}; border: 2px solid {status_border}; "
                        "border-radius: 5px; padding: 12px; font-weight: bold; font-size: 13px;"
                    )
                    self.status_label.setVisible(True)
                except Exception as label_err:
                    # Avoid print in case this runs in thread context
                    pass
                
                # Update progress label
                try:
                    self.progress_label.setText(progress_text)
                    self.progress_label.setStyleSheet(f"color: {progress_color}; font-weight: bold;")
                except Exception as prog_err:
                    # Avoid print in case this runs in thread context
                    pass
                
                # Show detailed results in the output box
                try:
                    # Get detailed results from the orchestrator
                    results_data = result.get('results', {}) if isinstance(result, dict) else {}
                    all_details = results_data.get('details', []) if isinstance(results_data, dict) else []
                    
                    # Count unique items (items that went through BOTH delete and create are one item)
                    # Track unique items by (type, name, folder)
                    unique_items = set()
                    for d in all_details:
                        item_key = (d.get('type'), d.get('name'), d.get('folder'))
                        unique_items.add(item_key)
                    
                    total_unique_items = len(unique_items)
                    
                    # Separate results by phase
                    phase1_deletes = [d for d in all_details if d.get('action') == 'deleted']
                    phase1_skipped = [d for d in all_details if d.get('action') == 'skipped' and 
                                     ('dependent item failed' in d.get('message', '') or 
                                      'Skipped - dependency' in d.get('message', ''))]
                    
                    phase2_creates = [d for d in all_details if d.get('action') == 'created']
                    phase2_updates = [d for d in all_details if d.get('action') == 'updated']
                    phase2_renamed = [d for d in all_details if d.get('action') == 'renamed']
                    
                    # Count by status within each phase
                    p1_deleted_success = [d for d in phase1_deletes if d.get('status') == 'success']
                    p1_deleted_failed = [d for d in phase1_deletes if d.get('status') == 'failed']
                    p1_skipped = phase1_skipped
                    
                    p2_created_success = [d for d in phase2_creates if d.get('status') == 'success']
                    p2_created_failed = [d for d in phase2_creates if d.get('status') == 'failed']
                    p2_updated_success = [d for d in phase2_updates if d.get('status') == 'success']
                    p2_renamed_success = [d for d in phase2_renamed if d.get('status') == 'success']
                    p2_renamed_failed = [d for d in phase2_renamed if d.get('status') == 'failed']
                    
                    details = []
                    details.append("=" * 70)
                    details.append("PUSH OPERATION SUMMARY")
                    details.append("=" * 70)
                    details.append(f"Total Unique Items: {total_unique_items}")
                    details.append("")
                    
                    # Phase 1 Summary
                    details.append("Phase 1 - Delete Operations:")
                    details.append(f"  ✓ Deleted:   {len(p1_deleted_success)}")
                    details.append(f"  ✗ Failed:    {len(p1_deleted_failed)}")
                    details.append(f"  ⊘ Skipped:   {len(p1_skipped)}")
                    details.append("")
                    
                    # Phase 2 Summary
                    details.append("Phase 2 - Create/Update Operations:")
                    details.append(f"  ✓ Created:   {len(p2_created_success)}")
                    if len(p2_created_failed) > 0:
                        details.append(f"  ✗ Failed:    {len(p2_created_failed)}")
                    if len(p2_renamed_success) > 0:
                        details.append(f"  ✓ Renamed:   {len(p2_renamed_success)}")
                    if len(p2_renamed_failed) > 0:
                        details.append(f"  ✗ Failed (Rename): {len(p2_renamed_failed)}")
                    if len(p2_updated_success) > 0:
                        details.append(f"  ✓ Updated:   {len(p2_updated_success)}")
                    details.append("")
                    
                    # PHASE 1 DETAILS
                    details.append("=" * 70)
                    details.append("PHASE 1: DELETE OPERATIONS")
                    details.append("=" * 70)
                    
                    # Failed deletes FIRST (most important)
                    if p1_deleted_failed:
                        details.append("")
                        details.append(f"✗ Failed to Delete ({len(p1_deleted_failed)}):")
                        for item in p1_deleted_failed:
                            details.append(f"  • {item.get('type', 'unknown')}: {item.get('name', 'unknown')} ({item.get('folder', 'unknown')})")
                            msg = item.get('message', 'No reason provided')
                            if msg:
                                details.append(f"    Reason: {msg}")
                    
                    # Skipped deletes (dependencies)
                    if p1_skipped:
                        details.append("")
                        details.append(f"⊘ Skipped Deletes ({len(p1_skipped)}):")
                        for item in p1_skipped:
                            details.append(f"  • {item.get('type', 'unknown')}: {item.get('name', 'unknown')} ({item.get('folder', 'unknown')})")
                            msg = item.get('message', 'No reason provided')
                            if msg:
                                details.append(f"    Reason: {msg}")
                    
                    # Successful deletes
                    if p1_deleted_success:
                        details.append("")
                        details.append(f"✓ Successfully Deleted ({len(p1_deleted_success)}):")
                        for item in p1_deleted_success:
                            details.append(f"  • {item.get('type', 'unknown')}: {item.get('name', 'unknown')} ({item.get('folder', 'unknown')})")
                    
                    details.append("")
                    
                    # PHASE 2 DETAILS
                    details.append("=" * 70)
                    details.append("PHASE 2: CREATE/UPDATE OPERATIONS")
                    details.append("=" * 70)
                    
                    # Failed creates FIRST
                    if p2_created_failed:
                        details.append("")
                        details.append(f"✗ Failed to Create ({len(p2_created_failed)}):")
                        for item in p2_created_failed:
                            details.append(f"  • {item.get('type', 'unknown')}: {item.get('name', 'unknown')} ({item.get('folder', 'unknown')})")
                            msg = item.get('message', 'No reason provided')
                            if msg:
                                details.append(f"    Reason: {msg}")
                    
                    # Failed renames
                    if p2_renamed_failed:
                        details.append("")
                        details.append(f"✗ Failed to Rename ({len(p2_renamed_failed)}):")
                        for item in p2_renamed_failed:
                            old_name = item.get('name', 'unknown')
                            # For failed renames, the 'name' field is the new name (e.g., "item-copy")
                            # Strip -copy to show the original name
                            if old_name.endswith('-copy'):
                                original_name = old_name[:-5]  # Remove "-copy"
                            else:
                                original_name = old_name
                            details.append(f"  • {item.get('type', 'unknown')}: {original_name} → {old_name} ({item.get('folder', 'unknown')})")
                            msg = item.get('message', 'No reason provided')
                            if msg:
                                details.append(f"    Reason: {msg}")
                    
                    # Successfully created
                    if p2_created_success:
                        details.append("")
                        details.append(f"✓ Successfully Created ({len(p2_created_success)}):")
                        for item in p2_created_success:
                            details.append(f"  • {item.get('type', 'unknown')}: {item.get('name', 'unknown')} ({item.get('folder', 'unknown')})")
                    
                    # Successfully updated
                    if p2_updated_success:
                        details.append("")
                        details.append(f"✓ Successfully Updated ({len(p2_updated_success)}):")
                        for item in p2_updated_success:
                            details.append(f"  • {item.get('type', 'unknown')}: {item.get('name', 'unknown')} ({item.get('folder', 'unknown')})")
                    
                    # Successfully renamed items
                    if p2_renamed_success:
                        details.append("")
                        details.append(f"✓ Successfully Renamed ({len(p2_renamed_success)}):")
                        for item in p2_renamed_success:
                            # For renamed items, extract original and new names
                            # The 'name' in results is the new name (with -copy)
                            new_name = item.get('name', 'unknown')
                            if new_name.endswith('-copy'):
                                original_name = new_name[:-5]
                            else:
                                original_name = 'unknown'
                            details.append(f"  • {item.get('type', 'unknown')}: {original_name} → {new_name} ({item.get('folder', 'unknown')})")
                    
                    details.append("")
                    
                    details.append("=" * 70)
                    details.append("")
                    details.append("See activity.log for complete details")
                    details.append("")
                    
                    self.results_text.setPlainText("\n".join(details))
                    
                    # Enable results action buttons
                    self.copy_results_btn.setEnabled(True)
                    self.view_details_btn.setEnabled(True)
                except Exception as results_err:
                    # Avoid print in case this runs in thread context
                    pass

                # Emit signal (wrapped in try/except)
                try:
                    self.push_completed.emit(result)
                except Exception as e:
                    # Avoid print in case this runs in thread context
                    pass
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
            # Avoid print in case this runs in thread context
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in _on_push_finished: {e}")
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
    
    def _copy_results(self):
        """Copy results text to clipboard."""
        try:
            from PyQt6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(self.results_text.toPlainText())
            
            # Show brief feedback
            original_text = self.copy_results_btn.text()
            self.copy_results_btn.setText("✓ Copied!")
            self.copy_results_btn.setStyleSheet("background-color: #4CAF50; color: white;")
            
            # Reset after 2 seconds
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(2000, lambda: (
                self.copy_results_btn.setText(original_text),
                self.copy_results_btn.setStyleSheet("")
            ))
        except Exception as e:
            QMessageBox.warning(self, "Copy Failed", f"Failed to copy results: {e}")
    
    def _view_full_details(self):
        """Open a dialog to view full activity log details."""
        try:
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Push Operation - Full Details")
            dialog.resize(1000, 700)
            
            layout = QVBoxLayout(dialog)
            
            # Add header
            from PyQt6.QtWidgets import QLabel
            header = QLabel("<h3>Complete Activity Log</h3>")
            layout.addWidget(header)
            
            # Text area with full log
            log_text = QTextEdit()
            log_text.setReadOnly(True)
            log_text.setStyleSheet("font-family: monospace; font-size: 10pt;")
            
            # Read activity.log
            try:
                with open('activity.log', 'r') as f:
                    # Get last 500 lines to avoid overwhelming the viewer
                    lines = f.readlines()
                    log_content = ''.join(lines[-500:])
                    log_text.setPlainText(log_content)
                    
                    # Scroll to bottom
                    log_text.verticalScrollBar().setValue(log_text.verticalScrollBar().maximum())
            except Exception as read_err:
                log_text.setPlainText(f"Error reading activity.log: {read_err}")
            
            layout.addWidget(log_text)
            
            # Close button
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            
            copy_log_btn = QPushButton("📋 Copy Full Log")
            copy_log_btn.clicked.connect(lambda: QApplication.clipboard().setText(log_text.toPlainText()))
            button_layout.addWidget(copy_log_btn)
            
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.close)
            button_layout.addWidget(close_btn)
            
            layout.addLayout(button_layout)
            
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self, "View Details Failed", f"Failed to open details viewer: {e}")
