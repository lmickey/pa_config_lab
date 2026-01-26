"""
Push configuration widget for the GUI.

This module provides the UI for pushing configurations to Prisma Access,
including conflict detection and resolution options.
"""

from typing import Optional, Dict, Any, List, Set
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
from gui.widgets import TenantSelectorWidget, ResultsPanel, LiveLogViewer, WorkflowLockManager
from gui.toast_notification import ToastManager, DismissibleErrorNotification


class PushConfigWidget(QWidget):
    """Widget for pushing configurations to Prisma Access."""

    # Signal emitted when push completes
    push_completed = pyqtSignal(object)  # result
    
    # Signal to return to selection screen
    return_to_selection_requested = pyqtSignal()
    
    # Signal to request adding missing dependencies (list of dependency dicts)
    add_dependencies_requested = pyqtSignal(list)

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
        self._push_cancelled = False  # Track if push was cancelled
        
        # Toast and error notification managers
        self.toast_manager = ToastManager(self)
        self.error_notification = DismissibleErrorNotification(self)
        
        # Workflow lock manager for preventing navigation during operations
        self.workflow_lock = WorkflowLockManager.instance()
        
        # Live log viewer reference (created on demand)
        self._live_log_viewer = None

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)  # Add more spacing between sections

        # Title
        title = QLabel("<h2>Push Configuration</h2>")
        layout.addWidget(title)

        info = QLabel(
            "Review your selection and validate before pushing."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(info)

        # === Selection Summary Section ===
        self.summary_group = QGroupBox("Selection Summary")
        summary_layout = QVBoxLayout()
        summary_layout.setSpacing(8)
        
        self.summary_label = QLabel("No items selected")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("padding: 8px;")
        summary_layout.addWidget(self.summary_label)
        
        # New snippet indicator (shown only if creating new snippets)
        self.new_snippet_indicator = QLabel("")
        self.new_snippet_indicator.setStyleSheet(
            "color: #1976D2; padding: 8px; background-color: #E3F2FD; "
            "border-radius: 4px; font-weight: bold;"
        )
        self.new_snippet_indicator.setVisible(False)
        summary_layout.addWidget(self.new_snippet_indicator)
        
        self.summary_group.setLayout(summary_layout)
        layout.addWidget(self.summary_group)
        
        # === Action buttons row (at top, near summary) ===
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Dry Run checkbox next to push button
        self.dry_run_check = QCheckBox("🧪 Dry Run (simulate only)")
        self.dry_run_check.setToolTip("Test the push without making changes")
        self.dry_run_check.setChecked(False)
        self.dry_run_check.setEnabled(False)  # Disabled until validation completes
        self.dry_run_check.setStyleSheet("font-size: 13px; padding-right: 15px;")
        button_layout.addWidget(self.dry_run_check)

        self.push_btn = QPushButton("🚀 Push Configuration")
        self.push_btn.setMinimumWidth(180)
        self.push_btn.setMinimumHeight(40)
        self.push_btn.setEnabled(False)  # Disabled until validation completes
        self.push_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #4CAF50; color: white; padding: 10px 20px; "
            "  font-size: 14px; font-weight: bold; border-radius: 5px; "
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
            "  background-color: #BDBDBD; "
            "  border: 1px solid #9E9E9E; "
            "  border-bottom: 3px solid #757575; "
            "}"
        )
        self.push_btn.clicked.connect(self._start_push)
        button_layout.addWidget(self.push_btn)

        # Validation return button (shown when nothing to push)
        self.validation_return_btn = QPushButton("↩ Return to Selection")
        self.validation_return_btn.setMinimumWidth(180)
        self.validation_return_btn.setMinimumHeight(40)
        self.validation_return_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #2196F3; color: white; padding: 10px 20px; "
            "  font-size: 14px; font-weight: bold; border-radius: 5px; "
            "  border: 1px solid #1976D2; border-bottom: 3px solid #1565C0; "
            "}"
            "QPushButton:hover { background-color: #1E88E5; border-bottom: 3px solid #0D47A1; }"
            "QPushButton:pressed { background-color: #1976D2; border-bottom: 1px solid #1565C0; }"
        )
        self.validation_return_btn.clicked.connect(self._return_to_selection)
        self.validation_return_btn.setVisible(False)
        button_layout.addWidget(self.validation_return_btn)

        # Cancel button (hidden by default, shown during push)
        self.cancel_btn = QPushButton("Cancel Push")
        self.cancel_btn.setMinimumWidth(150)
        self.cancel_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #f44336; "
            "  color: white; "
            "  border: none; "
            "  padding: 12px 24px; "
            "  font-size: 16px; "
            "  font-weight: bold; "
            "  border-radius: 4px; "
            "  border-bottom: 3px solid #c62828; "
            "}"
            "QPushButton:hover { "
            "  background-color: #e53935; "
            "  border-bottom: 3px solid #b71c1c; "
            "}"
            "QPushButton:pressed { "
            "  background-color: #d32f2f; "
            "  border-bottom: 1px solid #c62828; "
            "}"
        )
        self.cancel_btn.clicked.connect(self._cancel_push)
        self.cancel_btn.setVisible(False)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)
        
        # Hidden conflict resolution settings (used internally but not shown)
        # These are now set per-item in the selection screen
        self.conflict_button_group = QButtonGroup()
        self.skip_radio = QRadioButton()
        self.skip_radio.setChecked(True)
        self.conflict_button_group.addButton(self.skip_radio, 0)
        self.overwrite_radio = QRadioButton()
        self.conflict_button_group.addButton(self.overwrite_radio, 1)
        self.rename_radio = QRadioButton()
        self.conflict_button_group.addButton(self.rename_radio, 2)
        # Don't add to layout - these are hidden
        
        # Hidden validate checkbox (validation is now automatic)
        self.validate_check = QCheckBox()
        self.validate_check.setChecked(True)
        
        # Create a hidden status label for internal state (not shown in UI)
        self.status_label = QLabel("")
        self.status_label.setVisible(False)

        # === Validation Results Section (shown after validation completes) ===
        self.validation_group = QGroupBox("Validation Results")
        validation_layout = QVBoxLayout()
        
        # Summary status line
        self.validation_status = QLabel("Waiting for validation...")
        self.validation_status.setStyleSheet("padding: 8px; color: gray;")
        validation_layout.addWidget(self.validation_status)
        
        # Detailed validation results (scrollable text area)
        self.validation_details = QTextEdit()
        self.validation_details.setReadOnly(True)
        self.validation_details.setMinimumHeight(200)
        self.validation_details.setStyleSheet(
            "QTextEdit { font-family: 'Courier New', monospace; font-size: 11px; }"
        )
        validation_layout.addWidget(self.validation_details)
        
        self.validation_group.setLayout(validation_layout)
        self.validation_group.setVisible(False)  # Hidden until validation completes
        layout.addWidget(self.validation_group)

        # Progress section (initially hidden)
        self.progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()

        self.progress_label = QLabel("Ready to push")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)

        self.progress_group.setLayout(progress_layout)
        self.progress_group.setVisible(False)  # Hide until push starts
        layout.addWidget(self.progress_group)

        # Results section (using reusable ResultsPanel)
        self.results_group = QGroupBox("Results")
        results_layout = QVBoxLayout()

        self.results_panel = ResultsPanel(
            parent=self,
            title="Push Operation",
            log_file="logs/activity.log",
            placeholder="Push results will appear here...",
            use_embedded_log_viewer=False  # Use dialog instead of embedded viewer
        )
        self.results_panel.results_text.setMaximumHeight(150)
        self.results_panel.view_details_btn.setText("📄 View Details")
        results_layout.addWidget(self.results_panel)
        
        # Live Log Viewer (initially hidden, shown when "View Activity Log" is clicked)
        self.live_log_container = QWidget()
        live_log_layout = QVBoxLayout(self.live_log_container)
        live_log_layout.setContentsMargins(0, 0, 0, 0)
        
        self.live_log_viewer = LiveLogViewer(
            parent=self,
            log_file="logs/activity.log",
            title="Activity Log",
            show_close_button=True,
            poll_interval_ms=300,
            compact=True
        )
        self.live_log_viewer.close_requested.connect(self._hide_live_log_viewer)
        self.live_log_viewer.setMinimumHeight(250)
        self.live_log_viewer.setMaximumHeight(350)
        live_log_layout.addWidget(self.live_log_viewer)
        
        self.live_log_container.setVisible(False)
        results_layout.addWidget(self.live_log_container)
        
        # Return to Selection button (shown after push completes)
        return_btn_layout = QHBoxLayout()
        return_btn_layout.addStretch()
        
        self.return_to_selection_btn = QPushButton("↩ Return to Selection")
        self.return_to_selection_btn.setMinimumWidth(180)
        self.return_to_selection_btn.setFixedHeight(36)
        self.return_to_selection_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #2196F3; color: white; padding: 8px 16px; "
            "  font-weight: bold; border-radius: 5px; "
            "  border: 1px solid #1976D2; border-bottom: 3px solid #1565C0; "
            "}"
            "QPushButton:hover { background-color: #1E88E5; border-bottom: 3px solid #0D47A1; }"
            "QPushButton:pressed { background-color: #1976D2; border-bottom: 1px solid #1565C0; }"
        )
        self.return_to_selection_btn.clicked.connect(self._return_to_selection)
        self.return_to_selection_btn.setVisible(False)  # Hidden until push completes
        return_btn_layout.addWidget(self.return_to_selection_btn)
        
        return_btn_layout.addStretch()
        results_layout.addLayout(return_btn_layout)

        self.results_group.setLayout(results_layout)
        self.results_group.setVisible(False)  # Hide until push completes
        layout.addWidget(self.results_group)

        layout.addStretch()
        
        # Keep tenant_selector as None - we'll get destination from selection widget
        self.tenant_selector = None

    def set_api_client(self, api_client):
        """Set the API client for push operations (source tenant)."""
        self.api_client = api_client
        self._update_status()
    
    def set_destination_client(self, api_client, tenant_name: str = None):
        """
        Set the destination API client (called from selection widget).
        
        Args:
            api_client: The API client (or None if disconnected)
            tenant_name: Name of the tenant (or empty string if disconnected)
        """
        self.destination_client = api_client
        self.destination_name = tenant_name if tenant_name else None
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
        # Tenant selector is now in selection widget, not here
        pass

    def set_config(self, config: Optional[Dict[str, Any]]):
        """Set the configuration to push."""
        self.config = config
        self._update_status()
    
    def showEvent(self, event):
        """Handle widget show event - auto-trigger validation."""
        super().showEvent(event)
        # Auto-trigger validation when the push tab is shown
        # Use a short delay to ensure UI is fully rendered
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self._auto_validate)
    
    def _auto_validate(self):
        """Auto-trigger validation if ready."""
        if self.destination_client and self.selected_items and not self.push_completed_successfully:
            # Only validate if we have what we need and haven't already pushed
            self._start_validation()

    def _start_validation(self):
        """Start validation of selected items against destination."""
        if not self.destination_client or not self.selected_items:
            self.validation_group.setVisible(True)
            self.validation_status.setText("[WARN] Select a destination tenant to validate")
            self.validation_status.setStyleSheet("padding: 8px; color: #F57F17;")
            self.validation_details.setPlainText("Please select a destination tenant in the 'Select Components' tab.")
            return

        # Early validation: Check name lengths before any API calls
        name_errors = self._validate_name_lengths(self.selected_items)
        if name_errors:
            self.validation_group.setVisible(True)
            self.validation_status.setText("[ERROR] Name length validation failed")
            self.validation_status.setStyleSheet("padding: 8px; color: #c62828; background-color: #ffebee; border-radius: 4px;")
            error_text = "The following names exceed the 55 character limit:\n\n"
            for err in name_errors:
                error_text += f"  • {err}\n"
            error_text += "\nPlease shorten the names and try again."
            self.validation_details.setPlainText(error_text)
            self.push_btn.setEnabled(False)
            self.push_btn.setVisible(False)
            self.dry_run_check.setVisible(False)
            self.validation_return_btn.setVisible(True)
            return

        # Acquire workflow lock to prevent navigation during validation
        self.workflow_lock.acquire_lock(
            owner=self,
            operation_name="Validation",
            cancel_callback=self._cancel_validation
        )
        
        # Disable push controls during validation
        self.push_btn.setEnabled(False)
        self.dry_run_check.setEnabled(False)
        
        # Hide validation results section during validation
        self.validation_group.setVisible(False)
        
        # Show progress section for validation feedback
        self.progress_group.setVisible(True)
        self.progress_label.setText("🔄 Fetching destination configuration...")
        self.progress_label.setStyleSheet("color: #1976D2;")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Show results section for validation output
        self.results_group.setVisible(True)
        self.results_panel.set_text("Validating items...\n\nPlease wait while we check your configuration against the destination tenant.")
        
        # Hide return button during validation
        self.return_to_selection_btn.setVisible(False)
        
        # Import and run the validation worker (same as push preview dialog)
        from gui.dialogs.push_preview_dialog import ConfigFetchWorker
        
        # Clear results panel for new validation
        self.results_panel.set_text("")
        
        self.validation_worker = ConfigFetchWorker(self.destination_client, self.selected_items)
        self.validation_worker.progress.connect(self._on_validation_progress)
        self.validation_worker.detail.connect(self._on_validation_detail)
        self.validation_worker.finished.connect(self._on_validation_finished)
        self.validation_worker.error.connect(self._on_validation_error)
        self.validation_worker.start()
    
    def _cancel_validation(self) -> bool:
        """
        Cancel the current validation operation.
        
        Returns:
            True if cancellation was successful, False otherwise
        """
        if hasattr(self, 'validation_worker') and self.validation_worker and self.validation_worker.isRunning():
            # Try to stop the worker (it may not support cancellation)
            try:
                self.validation_worker.terminate()
                self.validation_worker.wait(1000)  # Wait up to 1 second
                return not self.validation_worker.isRunning()
            except Exception:
                return False
        return True  # No validation running
    
    def _on_validation_progress(self, message: str, percentage: int):
        """Handle validation progress updates."""
        # Update the progress section
        self.progress_label.setText(f"🔄 {message}")
        self.progress_bar.setValue(percentage)
    
    def _on_validation_detail(self, message: str):
        """Handle detailed validation messages - append to results panel."""
        current_text = self.results_panel.results_text.toPlainText()
        if current_text:
            self.results_panel.results_text.setPlainText(current_text + "\n" + message)
        else:
            self.results_panel.results_text.setPlainText(message)
        
        # Auto-scroll to bottom
        scrollbar = self.results_panel.results_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _on_validation_error(self, error: str):
        """Handle validation errors."""
        # Release workflow lock
        self.workflow_lock.release_lock(self)
        
        # Update progress section
        self.progress_label.setText("[ERROR] Validation failed")
        self.progress_label.setStyleSheet("color: red;")
        self.progress_bar.setVisible(False)
        self.results_panel.set_text(f"Validation Error:\n\n{error}")
        
        # After 2 seconds, hide progress and show validation results
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(2000, lambda: self._show_validation_error_results(error))
    
    def _show_validation_error_results(self, error: str):
        """Show validation error in the validation results section."""
        # Hide progress/results sections
        self.progress_group.setVisible(False)
        self.results_group.setVisible(False)

        # Show validation section with error
        self.validation_group.setVisible(True)
        self.validation_status.setText("[ERROR] Validation failed")
        self.validation_status.setStyleSheet("padding: 8px; color: #c62828; background-color: #ffebee; border-radius: 4px;")
        self.validation_details.setPlainText(f"Error during validation:\n\n{error}")

        # Keep push disabled, but show return to selection button
        self.push_btn.setEnabled(False)
        self.push_btn.setVisible(False)
        self.dry_run_check.setEnabled(False)
        self.dry_run_check.setVisible(False)
        self.validation_return_btn.setVisible(True)
    
    def _on_validation_finished(self, destination_config):
        """Handle validation completion."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Update progress section to show complete
            self.progress_label.setText("✓ Validation complete")
            self.progress_label.setStyleSheet("color: #2e7d32; font-weight: bold;")
            self.progress_bar.setValue(100)
            
            # Store destination config for push
            self._destination_config = destination_config
            
            # Debug: Log destination_config keys and all_rule_names count
            all_rule_names = destination_config.get('all_rule_names', {})
            logger.debug(f"[Validation] destination_config keys: {list(destination_config.keys())}")
            logger.debug(f"[Validation] all_rule_names count: {len(all_rule_names)}")
            if all_rule_names:
                sample_rules = list(all_rule_names.keys())[:5]
                logger.debug(f"[Validation] Sample rule names: {sample_rules}")
            
            # Run comprehensive validation
            logger.debug("[Validation] Running _validate_items...")
            validation_results = self._validate_items(destination_config)
            logger.debug(f"[Validation] _validate_items returned: {len(validation_results.get('item_details', []))} items")
            
            # Store validation results for display
            self._validation_results = validation_results
            
            # Show validation details in results panel (temporarily)
            self._show_validation_details_in_results(validation_results)
            
            # After 2 seconds, hide progress/results and show validation section
            from PyQt6.QtCore import QTimer
            logger.debug("[Validation] Scheduling _finalize_validation in 2 seconds...")
            QTimer.singleShot(2000, lambda: self._finalize_validation(validation_results))
        except Exception as e:
            import traceback
            logger.error(f"[Validation] Error in _on_validation_finished: {e}")
            traceback.print_exc()
            self._on_validation_error(str(e))
    
    def _finalize_validation(self, validation_results):
        """Finalize validation UI - hide progress/results, show validation section."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Release workflow lock - validation is complete
        self.workflow_lock.release_lock(self)
        
        try:
            logger.debug("[Validation] _finalize_validation called")
            errors = validation_results.get('errors', [])
            warnings = validation_results.get('warnings', [])
            new_items = validation_results.get('new_items', 0)
            conflicts = validation_results.get('conflicts', 0)
            total_items = validation_results.get('total_items', 0)
            missing_dependencies = validation_results.get('missing_dependencies', [])
            skipped_items = validation_results.get('skipped_items', 0)
            reference_conflicts = validation_results.get('reference_conflicts', [])
            
            # Store missing dependencies for the "Add and Revalidate" action
            self._pending_missing_dependencies = missing_dependencies
            
            # Store reference conflicts for handling
            self._pending_reference_conflicts = reference_conflicts
            
            # Filter reference conflicts to only those with OVERWRITE strategy
            # (SKIP doesn't need to delete, so no reference conflict)
            # Check item strategies from item_details
            overwrite_objects = set()
            for item in validation_results.get('item_details', []):
                if item.get('strategy') == 'overwrite' and item.get('exists'):
                    overwrite_objects.add(f"{item.get('type')}:{item.get('name')}")
            
            logger.debug(f"[Validation] overwrite_objects: {overwrite_objects}")
            logger.debug(f"[Validation] reference_conflicts from destination: {len(reference_conflicts)}")
            
            # Filter reference conflicts to only overwrite items
            active_reference_conflicts = [
                rc for rc in reference_conflicts
                if f"{rc['referenced_type']}:{rc['referenced_object']}" in overwrite_objects
            ]
            
            logger.debug(f"[Validation] active_reference_conflicts: {len(active_reference_conflicts)}")
            
            # Hide progress and results sections
            self.progress_group.setVisible(False)
            self.results_group.setVisible(False)
            
            # Show validation results section
            self.validation_group.setVisible(True)

            # Check if there's nothing to push by examining item_details
            # Items will be pushed if: exists=False (new) OR exists=True with non-skip strategy
            items_to_push = 0
            for item in validation_results.get('item_details', []):
                if not item.get('exists', False):
                    # New item - will be created
                    items_to_push += 1
                elif item.get('strategy', 'skip') != 'skip':
                    # Exists but will be overwritten/renamed
                    items_to_push += 1
            nothing_to_push = total_items > 0 and items_to_push == 0
            
            # Set summary status based on validation outcome
            if errors:
                # Hard errors - can't push
                self.validation_status.setText(
                    f"[ERROR] Validation failed - {len(errors)} error(s), {len(warnings)} warning(s)"
                )
                self.validation_status.setStyleSheet(
                    "padding: 8px; color: #c62828; background-color: #ffebee; border-radius: 4px;"
                )
                self.push_btn.setEnabled(False)
                self.push_btn.setText("Push Config")
                self.dry_run_check.setEnabled(False)
            elif active_reference_conflicts:
                # Reference conflicts - rules reference objects we're trying to overwrite
                # Group by referenced object
                ref_objects = set()
                ref_rules = set()
                for rc in active_reference_conflicts:
                    ref_objects.add(rc['referenced_object'])
                    ref_rules.add(rc['rule_name'])
                
                self.validation_status.setText(
                    f"🔗 Reference conflict - {len(ref_rules)} rule(s) reference {len(ref_objects)} object(s) being overwritten"
                )
                self.validation_status.setStyleSheet(
                    "padding: 8px; color: #c62828; background-color: #ffebee; border-radius: 4px;"
                )
                self.push_btn.setEnabled(False)
                self.push_btn.setText("Resolve Conflicts First")
                self.dry_run_check.setEnabled(False)
            elif nothing_to_push:
                # All items already exist and will be skipped - nothing to push
                self.validation_status.setText(
                    f"ℹ️ Nothing to push - All {total_items} item(s) already exist with SKIP strategy"
                )
                self.validation_status.setStyleSheet(
                    "padding: 8px; color: #1565C0; background-color: #E3F2FD; border-radius: 4px;"
                )
                # Hide push button, show validation return button (in button bar)
                self.push_btn.setVisible(False)
                self.dry_run_check.setVisible(False)
                self.validation_return_btn.setVisible(True)
            elif missing_dependencies:
                # Missing dependencies - need to add them first
                dep_count = len(missing_dependencies)
                self.validation_status.setText(
                    f"[WARN] {dep_count} missing dependenc{'y' if dep_count == 1 else 'ies'} - Add required items to continue"
                )
                self.validation_status.setStyleSheet(
                    "padding: 8px; color: #E65100; background-color: #FFF3E0; border-radius: 4px;"
                )
                self.push_btn.setEnabled(True)
                self.push_btn.setText("Add Dependencies and Revalidate")
                self.dry_run_check.setEnabled(False)
            elif warnings:
                self.validation_status.setText(
                    f"[WARN] {total_items} items: {new_items} new, {conflicts} conflicts, {len(warnings)} warning(s)"
                )
                self.validation_status.setStyleSheet(
                    "padding: 8px; color: #F57F17; background-color: #FFF9C4; border-radius: 4px;"
                )
                self.push_btn.setEnabled(True)
                self.push_btn.setText("Push Config")
                self.dry_run_check.setEnabled(True)
            elif conflicts > 0:
                self.validation_status.setText(
                    f"[WARN] {total_items} items: {new_items} new, {conflicts} conflicts - Review strategies"
                )
                self.validation_status.setStyleSheet(
                    "padding: 8px; color: #F57F17; background-color: #FFF9C4; border-radius: 4px;"
                )
                self.push_btn.setEnabled(True)
                self.push_btn.setText("Push Config")
                self.dry_run_check.setEnabled(True)
            else:
                self.validation_status.setText(f"✅ Validation passed - {new_items} new items, no conflicts")
                self.validation_status.setStyleSheet(
                    "padding: 8px; color: #2e7d32; background-color: #e8f5e9; border-radius: 4px;"
                )
                self.push_btn.setEnabled(True)
                self.push_btn.setText("Push Config")
                self.dry_run_check.setEnabled(True)
            
            # Show detailed validation results in the text area
            self._show_detailed_validation_table(validation_results)
            logger.debug("[Validation] _finalize_validation complete")
            
        except Exception as e:
            import traceback
            logger.error(f"[Validation] Error in _finalize_validation: {e}")
            traceback.print_exc()
            self.validation_status.setText(f"[ERROR] Validation error: {e}")
            self.validation_status.setStyleSheet(
                "padding: 8px; color: #c62828; background-color: #ffebee; border-radius: 4px;"
            )
            self.push_btn.setEnabled(False)
    
    def _show_validation_details_in_results(self, validation_results):
        """Show validation details in results panel during validation."""
        lines = []
        lines.append("Validation Complete - Analyzing results...")
        lines.append("")
        lines.append(f"Total Items: {validation_results['total_items']}")
        lines.append(f"New: {validation_results['new_items']}")
        lines.append(f"Conflicts: {validation_results['conflicts']}")
        lines.append(f"Errors: {len(validation_results['errors'])}")
        lines.append(f"Warnings: {len(validation_results['warnings'])}")
        self.results_panel.set_text("\n".join(lines))
    
    def _show_detailed_validation_table(self, validation_results):
        """Show detailed validation results as a table in the validation details area."""
        import logging
        logger = logging.getLogger(__name__)
        
        lines = []
        
        # Get default strategy for comparison
        default_strategy = self.selected_items.get('default_strategy', 'skip') if self.selected_items else 'skip'
        
        # Header
        lines.append("=" * 115)
        lines.append("VALIDATION RESULTS - ITEM DETAILS")
        lines.append("=" * 115)
        lines.append("")
        
        # Log validation results header to activity log
        logger.normal("[Validation] " + "=" * 60)
        logger.normal("[Validation] VALIDATION RESULTS SUMMARY")
        logger.normal("[Validation] " + "=" * 60)
        
        # Table header - include DESTINATION and STRATEGY columns
        lines.append(f"{'TYPE':<20} {'NAME':<22} {'DESTINATION':<22} {'STRATEGY':<12} {'STATUS':<10} {'ACTION'}")
        lines.append("-" * 115)
        
        # Show each item
        for item in validation_results.get('item_details', []):
            item_type = item.get('type', 'unknown')[:18]
            item_name = item.get('name', 'unknown')[:20]
            exists = item.get('exists', False)
            strategy = item.get('strategy', 'skip')
            existing_loc = item.get('existing_location', '')
            
            # Get destination info
            dest_location = item.get('location', item.get('destination', ''))
            dest_type = item.get('dest_type', '')  # 'snippet' or 'folder'
            
            # Format destination with type indicator
            if dest_type == 'snippet':
                dest_display = f"📄 {dest_location}"[:20] if dest_location else "📄 (inherit)"
            elif dest_type == 'folder':
                dest_display = f"📁 {dest_location}"[:20] if dest_location else "📁 (inherit)"
            elif dest_location:
                dest_display = dest_location[:20]
            else:
                dest_display = "(inherit)"
            
            # Format strategy - show "default" if matches default, otherwise show actual
            if strategy == default_strategy:
                strategy_display = f"(default)"
            else:
                strategy_display = strategy.upper()
            
            if exists:
                status = "EXISTS"
                # For security rules, show where the conflict is
                loc_info = f" in '{existing_loc}'" if existing_loc else ""
                if strategy == 'skip':
                    action = f"→ SKIP{loc_info}"
                elif strategy == 'overwrite':
                    # For overwrite, clarify what will happen:
                    # - If existing_loc differs from destination, show both delete location and create destination
                    # - If same location, just show "DELETE then CREATE"
                    if existing_loc and dest_location and existing_loc != dest_location:
                        # Rule exists elsewhere - will delete from there and create in destination
                        action = f"→ DELETE from '{existing_loc}', CREATE in dest"
                    else:
                        action = f"→ DELETE then CREATE"
                elif strategy == 'rename':
                    action = f"→ RENAME (add -copy){loc_info}"
                else:
                    action = f"→ {strategy.upper()}{loc_info}"
            else:
                status = "NEW"
                action = "→ CREATE"
            
            lines.append(f"{item_type:<20} {item_name:<22} {dest_display:<22} {strategy_display:<12} {status:<10} {action}")
            
            # Log each item to activity log
            logger.normal(f"[Validation] {item_type}/{item_name}: {status} -> {action} (dest={dest_location}, strategy={strategy})")
            
            # Show existing location detail for security rules with global conflicts
            # Only show warning for SKIP strategy - for OVERWRITE the conflict is expected and handled
            if exists and existing_loc and item_type == 'security_rule' and strategy == 'skip':
                lines.append(f"{'':20} [WARN] Rule name already exists in: {existing_loc}")
                logger.warning(f"[Validation]   [WARN] Rule name conflict: '{item_name}' exists in {existing_loc}")
            
            # Show errors/warnings for this item
            if item.get('error'):
                lines.append(f"{'':20} [ERROR] ERROR: {item['error']}")
                logger.error(f"[Validation]   [ERROR] {item['error']}")
            if item.get('warning'):
                lines.append(f"{'':20} [WARN] WARNING: {item['warning']}")
                logger.warning(f"[Validation]   [WARN] {item['warning']}")
            
            # Show missing dependencies
            if item.get('missing_deps'):
                deps_str = ', '.join(item['missing_deps'])
                lines.append(f"{'':20} [WARN] Missing deps: {deps_str}")
                logger.warning(f"[Validation]   [WARN] Missing deps: {deps_str}")
        
        lines.append("-" * 115)
        lines.append("")
        
        # Log summary counts to activity log
        logger.normal(f"[Validation] " + "-" * 40)
        logger.normal(f"[Validation] Total: {validation_results['total_items']}, New: {validation_results['new_items']}, Conflicts: {validation_results['conflicts']}")
        if validation_results.get('errors'):
            logger.error(f"[Validation] Errors: {len(validation_results['errors'])}")
        if validation_results.get('warnings'):
            logger.warning(f"[Validation] Warnings: {len(validation_results['warnings'])}")
        
        # Reference conflicts section (rules that reference objects being overwritten)
        reference_conflicts = validation_results.get('reference_conflicts', [])
        
        # Filter to only OVERWRITE items that exist
        overwrite_objects = set()
        for item in validation_results.get('item_details', []):
            if item.get('strategy') == 'overwrite' and item.get('exists'):
                overwrite_objects.add(f"{item.get('type')}:{item.get('name')}")
        
        active_ref_conflicts = [
            rc for rc in reference_conflicts
            if f"{rc['referenced_type']}:{rc['referenced_object']}" in overwrite_objects
        ]
        
        if active_ref_conflicts:
            lines.append("=" * 115)
            lines.append("🔗 REFERENCE CONFLICTS - Rules referencing objects being overwritten")
            lines.append("=" * 115)
            lines.append("")
            lines.append("The following destination rules reference objects you are trying to OVERWRITE.")
            lines.append("These objects cannot be deleted while rules reference them.")
            lines.append("")
            
            # Group by referenced object
            refs_by_object = {}
            for rc in active_ref_conflicts:
                obj_key = f"{rc['referenced_type']}:{rc['referenced_object']}"
                if obj_key not in refs_by_object:
                    refs_by_object[obj_key] = []
                refs_by_object[obj_key].append(rc)
            
            for obj_key, conflicts in refs_by_object.items():
                obj_type, obj_name = obj_key.split(':', 1)
                lines.append(f"  📦 {obj_type}: {obj_name}")
                lines.append(f"     Referenced by:")
                for rc in conflicts:
                    loc_type = "📄" if rc['rule_location_type'] == 'snippet' else "📁"
                    lines.append(f"       - Rule '{rc['rule_name']}' ({loc_type} {rc['rule_location']}) in field: {rc['reference_field']}")
                lines.append("")
            
            lines.append("OPTIONS TO RESOLVE:")
            lines.append("  A) Change items to SKIP strategy (don't overwrite)")
            lines.append("  B) Delete/recreate the referencing rules (add them to push with OVERWRITE)")
            lines.append("  C) Manually remove the object references from rules before push")
            lines.append("")
            lines.append("-" * 115)
            lines.append("")
        
        # Summary section
        lines.append("SUMMARY:")
        lines.append(f"  Total Items: {validation_results['total_items']}")
        lines.append(f"  New Items: {validation_results['new_items']}")
        lines.append(f"  Conflicts: {validation_results['conflicts']}")
        
        if active_ref_conflicts:
            lines.append(f"  Reference Conflicts: {len(active_ref_conflicts)} (blocking push)")
        
        if validation_results['errors']:
            lines.append("")
            lines.append("ERRORS (must fix before push):")
            for err in validation_results['errors']:
                lines.append(f"  [ERROR] {err}")
        
        if validation_results['warnings']:
            lines.append("")
            lines.append("WARNINGS:")
            for warn in validation_results['warnings']:
                lines.append(f"  [WARN] {warn}")
        
        lines.append("")
        lines.append("=" * 80)
        
        self.validation_details.setPlainText("\n".join(lines))
    
    def _validate_items(self, destination_config) -> Dict[str, Any]:
        """
        Perform comprehensive validation on selected items.
        
        Checks:
        - Name length limits (55 chars max)
        - Name length with '-copy' suffix for rename strategy
        - Conflicts with existing items (considering destination type)
        - NEW SNIPPET: If destination is a new snippet, skip conflict checks (auto-pass)
        - FOLDER: Check global uniqueness for rules, folder-scope for objects
        - Dependencies: Check if required dependencies are also selected
        
        Returns:
            Dict with errors, warnings, item_details, counts, missing_dependencies
        """
        import logging
        logger = logging.getLogger(__name__)
        
        MAX_NAME_LENGTH = 55
        COPY_SUFFIX = "-copy"
        
        errors = []
        warnings = []
        item_details = []  # Per-item validation results
        new_items = 0
        conflicts = 0
        total_items = 0
        skipped_items = 0  # Track items that will be skipped (exists + skip strategy)
        missing_dependencies = []  # Track missing dependencies for "Add Missing" feature
        
        default_strategy = self.selected_items.get('default_strategy', 'skip')
        
        # Dependency mappings: what fields in each type reference other objects
        # Format: {type: {field_name: [(referenced_type, is_list), ...]}}
        # Multiple types can be checked for the same field (e.g., members can be filters OR groups)
        DEPENDENCY_FIELDS = {
            'application_group': {
                # members can contain: application filter names OR other application group names
                'members': [('application_filter', True), ('application_group', True)],
            },
            'address_group': {
                'static': [('address', True), ('address_group', True)],  # Can reference addresses or other groups
                'dynamic': [(None, False)],  # Dynamic filters, not object references
            },
            'service_group': {
                'members': [('service', True), ('service_group', True)],  # Can reference services or other groups
            },
            'security_rule': {
                'source': [('address', True), ('address_group', True)],
                'destination': [('address', True), ('address_group', True)],
                'application': [('application_group', True), ('application_filter', True)],
                'service': [('service', True), ('service_group', True)],
                'profile_setting': [(None, False)],  # Profile groups - complex
            },
        }
        
        # Build set of all selected item names by type for dependency checking
        selected_names_by_type = {}
        
        def collect_selected_names(items_dict, container_type='folder'):
            """Collect names of all selected items by type."""
            for container in items_dict:
                for obj_type, obj_list in container.get('objects', {}).items():
                    if obj_type not in selected_names_by_type:
                        selected_names_by_type[obj_type] = set()
                    for obj in obj_list:
                        name = obj.get('name', '')
                        if name:
                            selected_names_by_type[obj_type].add(name)
                # Also check profiles
                for obj_type, obj_list in container.get('profiles', {}).items():
                    if obj_type not in selected_names_by_type:
                        selected_names_by_type[obj_type] = set()
                    for obj in obj_list:
                        name = obj.get('name', '')
                        if name:
                            selected_names_by_type[obj_type].add(name)
        
        # Collect from folders and snippets
        collect_selected_names(self.selected_items.get('folders', []))
        collect_selected_names(self.selected_items.get('snippets', []))
        
        # Build index of all available items from the loaded config for dependency resolution
        # This allows us to find items that exist in config but weren't selected
        # Structure: {obj_type: {name: [(container_type, container_name, obj_data), ...]}}
        available_items_by_type = {}
        
        def index_container_items(container_data: Dict, container_type: str, container_name: str):
            """Index items from a single container (folder/snippet data dict)."""
            if not isinstance(container_data, dict):
                return
            
            # New format: container_data is {item_type: [items], ...}
            for key, value in container_data.items():
                if not isinstance(value, list):
                    continue
                # Check if this looks like a list of objects (dicts with 'name')
                if value and isinstance(value[0], dict) and 'name' in value[0]:
                    obj_type = key
                    if obj_type not in available_items_by_type:
                        available_items_by_type[obj_type] = {}
                    for obj in value:
                        if isinstance(obj, dict):
                            name = obj.get('name', '')
                            if name:
                                # Store as list of (container_type, container_name, data)
                                if name not in available_items_by_type[obj_type]:
                                    available_items_by_type[obj_type][name] = []
                                available_items_by_type[obj_type][name].append(
                                    (container_type, container_name, obj)
                                )
        
        def index_available_items(items_source, container_type: str):
            """Index all available items from config (not just selected).
            
            Handles both dict format (new) and list format (legacy/selected).
            """
            if isinstance(items_source, dict):
                # New format: {container_name: {item_type: [items], ...}, ...}
                for container_name, container_data in items_source.items():
                    index_container_items(container_data, container_type, container_name)
            elif isinstance(items_source, list):
                # List format (from selected_items): [{name: ..., objects: {...}, ...}, ...]
                for container in items_source:
                    if not isinstance(container, dict):
                        continue
                    container_name = container.get('name', '')
                    # Check for objects dict
                    for obj_type, obj_list in container.get('objects', {}).items():
                        if obj_type not in available_items_by_type:
                            available_items_by_type[obj_type] = {}
                        if isinstance(obj_list, list):
                            for obj in obj_list:
                                if isinstance(obj, dict):
                                    name = obj.get('name', '')
                                    if name:
                                        if name not in available_items_by_type[obj_type]:
                                            available_items_by_type[obj_type][name] = []
                                        available_items_by_type[obj_type][name].append(
                                            (container_type, container_name, obj)
                                        )
                    # Check for profiles dict
                    for obj_type, obj_list in container.get('profiles', {}).items():
                        if obj_type not in available_items_by_type:
                            available_items_by_type[obj_type] = {}
                        if isinstance(obj_list, list):
                            for obj in obj_list:
                                if isinstance(obj, dict):
                                    name = obj.get('name', '')
                                    if name:
                                        if name not in available_items_by_type[obj_type]:
                                            available_items_by_type[obj_type][name] = []
                                        available_items_by_type[obj_type][name].append(
                                            (container_type, container_name, obj)
                                        )
        
        # Index available items from the original loaded config
        if hasattr(self, 'loaded_config') and self.loaded_config:
            index_available_items(self.loaded_config.get('folders', {}), 'folder')
            index_available_items(self.loaded_config.get('snippets', {}), 'snippet')
        
        def check_dependencies(item_data: Dict, item_type: str, item_name: str, 
                                item_container_type: str = None, item_container_name: str = None) -> List[Dict]:
            """Check if item's dependencies are selected.
            
            Returns list of missing dependencies with info to add them.
            Prefers dependencies from the same container as the item.
            """
            missing = []
            dep_fields = DEPENDENCY_FIELDS.get(item_type, {})
            
            for field_name, ref_type_list in dep_fields.items():
                field_value = item_data.get(field_name, [])
                if not field_value:
                    continue
                
                # Normalize to list
                if isinstance(field_value, str):
                    field_value = [field_value]
                elif not isinstance(field_value, list):
                    continue
                
                # Check each referenced item
                for ref_name in field_value:
                    if not ref_name or ref_name in ('any', 'application-default'):
                        continue  # Skip special values
                    
                    # Check against all possible reference types for this field
                    found_selected = False
                    found_available = None
                    
                    for ref_type, is_list in ref_type_list:
                        if ref_type is None:
                            continue  # Skip non-object references
                        
                        # Check if this reference is already selected
                        if ref_name in selected_names_by_type.get(ref_type, set()):
                            found_selected = True
                            break
                        
                        # Check if it's available in the config (but not selected)
                        # available_items_by_type[type][name] = [(container_type, container_name, data), ...]
                        available_list = available_items_by_type.get(ref_type, {}).get(ref_name, [])
                        if available_list:
                            # Prefer item from same container
                            best_match = None
                            for cont_type, cont_name, obj_data in available_list:
                                if cont_type == item_container_type and cont_name == item_container_name:
                                    # Exact container match - use this one
                                    best_match = (cont_type, cont_name, obj_data)
                                    break
                                elif best_match is None:
                                    # First available match as fallback
                                    best_match = (cont_type, cont_name, obj_data)
                            
                            if best_match:
                                cont_type, cont_name, obj_data = best_match
                                # Add container info to the data for proper selection
                                obj_data_with_container = obj_data.copy()
                                if cont_type == 'snippet':
                                    obj_data_with_container['snippet'] = cont_name
                                else:
                                    obj_data_with_container['folder'] = cont_name
                                
                                found_available = {
                                    'name': ref_name,
                                    'type': ref_type,
                                    'required_by': item_name,
                                    'required_by_type': item_type,
                                    'data': obj_data_with_container,
                                    'source_container_type': cont_type,
                                    'source_container_name': cont_name,
                                }
                    
                    # If not selected but available, add to missing
                    if not found_selected and found_available:
                        missing.append(found_available)
            
            return missing
        
        # Get snippets being created (these auto-pass validation for their contents)
        new_snippets = destination_config.get('new_snippets', set())
        existing_snippets = set(destination_config.get('snippets', {}).keys())
        
        # Folder display name mapping (API name -> User-friendly name)
        FOLDER_DISPLAY_NAMES = {
            'All': 'Global',
            'Shared': 'Prisma Access',
        }
        
        def get_display_name(name: str) -> str:
            """Get display name for a folder (e.g., 'Shared' -> 'Prisma Access')."""
            return FOLDER_DISPLAY_NAMES.get(name, name)
        
        # Default/system profile names that cannot be modified
        DEFAULT_PROFILE_NAMES = {'best-practice', 'default', 'strict', 'Strict'}
        PROFILE_ITEM_TYPES = {
            'wildfire_profile', 'wildfire_antivirus_profile',
            'anti_spyware_profile',
            'vulnerability_profile', 'vulnerability_protection_profile',
            'url_filtering_profile',
            'file_blocking_profile',
            'dns_security_profile',
            'decryption_profile',
            'security_profile_group', 'profile_group',
        }
        
        def is_default_profile(item_type: str, item_name: str) -> bool:
            """Check if an item is a default/system profile that should be skipped."""
            return item_type in PROFILE_ITEM_TYPES and item_name in DEFAULT_PROFILE_NAMES
        
        def check_name_length(name: str, item_type: str, strategy: str) -> tuple:
            """Check name length, returns (error, warning) messages."""
            if not name:
                return None, None
            
            current_len = len(name)
            
            # Check if name already exceeds limit
            if current_len > MAX_NAME_LENGTH:
                return f"Name '{name}' ({current_len} chars) exceeds {MAX_NAME_LENGTH} char limit", None
            
            # Check if rename strategy would exceed limit
            if strategy == 'rename':
                new_len = current_len + len(COPY_SUFFIX)
                if new_len > MAX_NAME_LENGTH:
                    return None, f"Name '{name}' with '{COPY_SUFFIX}' would be {new_len} chars (max {MAX_NAME_LENGTH})"
            
            return None, None
        
        def get_item_strategy(item_data: Dict) -> str:
            """Get the effective strategy for an item."""
            dest = item_data.get('_destination', {})
            return dest.get('strategy', default_strategy)

        def get_destination_name(source_name: str, strategy: str, item_data: Dict = None) -> str:
            """Get the destination name based on strategy and user input.

            For 'rename' strategy:
              - If user specified a custom name in _destination.name, use it
              - Otherwise, append COPY_SUFFIX to the source name
            For other strategies, returns the source name unchanged.
            """
            if strategy == 'rename':
                # Check if user specified a custom destination name
                if item_data:
                    dest = item_data.get('_destination', {})
                    custom_name = dest.get('name', '')
                    # Use custom name if it's set and different from source
                    if custom_name and custom_name != source_name:
                        return custom_name
                # Default: append -copy suffix
                return f"{source_name}{COPY_SUFFIX}"
            return source_name

        def get_item_destination(item_data: Dict) -> tuple:
            """Get destination info for an item.
            
            Returns:
                tuple: (dest_name, is_new_snippet, is_snippet)
            """
            dest = item_data.get('_destination', {})
            is_new = dest.get('is_new_snippet', False)
            new_snippet_name = dest.get('new_snippet_name', '')
            
            if is_new and new_snippet_name:
                return new_snippet_name, True, True
            
            # Check if destination folder is actually a snippet name
            folder = dest.get('folder', '')
            if folder in existing_snippets:
                return folder, False, True
            
            return folder, False, False
        
        def is_destination_new_snippet(item_data: Dict) -> bool:
            """Check if item is going to a NEW snippet (auto-pass)."""
            dest_name, is_new, _ = get_item_destination(item_data)
            if is_new:
                return True
            # Also check if destination is in new_snippets set
            return dest_name in new_snippets
        
        # Check folders
        # Note: Folders themselves are NOT counted as items - they are built-in in Prisma Access
        # Only their contents (objects, profiles, etc.) are counted and validated
        # Exception: If creating a NEW snippet, that snippet creation IS counted
        for folder_data in self.selected_items.get('folders', []):
            folder_name = folder_data.get('name', '')
            folder_display_name = get_display_name(folder_name)  # User-friendly name
            strategy = get_item_strategy(folder_data)
            
            # Check destination type
            dest_info = folder_data.get('_destination', {})
            is_to_new_snippet = dest_info.get('is_new_snippet', False) or dest_info.get('is_rename_snippet', False)
            is_to_existing_snippet = dest_info.get('is_existing_snippet', False)
            new_snippet_name = dest_info.get('new_snippet_name', '')
            dest_folder = dest_info.get('folder', '')
            
            # Check if destination folder is actually an existing snippet name
            # This catches cases where is_existing_snippet flag wasn't set but the folder name matches a snippet
            if not is_to_existing_snippet and not is_to_new_snippet and dest_folder and dest_folder in existing_snippets:
                is_to_existing_snippet = True
                logger.debug(f"Folder '{folder_name}' destination '{dest_folder}' detected as existing snippet")
            
            if is_to_new_snippet and new_snippet_name:
                # This folder's contents are going to a new snippet
                # Check if snippet already exists!
                snippet_exists = new_snippet_name in existing_snippets
                total_items += 1  # Count the new snippet as an item

                if snippet_exists:
                    # Snippet name conflict - this is an error/conflict
                    conflicts += 1
                    action = f"[WARN] Snippet '{new_snippet_name}' already exists!"
                    err = f"Cannot create snippet '{new_snippet_name}' - name already exists"
                    errors.append(err)
                    
                    item_details.append({
                        'type': 'snippet (conflict)',
                        'name': new_snippet_name,
                        'exists': True,
                        'strategy': strategy,
                        'action': action,
                        'error': err,
                        'warning': None,
                    })
                else:
                    # Snippet name is available
                    item_details.append({
                        'type': 'snippet (new)',
                        'name': new_snippet_name,
                        'exists': False,
                        'strategy': strategy,
                        'action': f"Will create snippet '{new_snippet_name}'",
                        'error': None,
                        'warning': None,
                    })
                    new_items += 1
                
                # Check name length for new snippet
                err, warn = check_name_length(new_snippet_name, 'snippet', 'skip')
                if err:
                    errors.append(err)
                if warn:
                    warnings.append(warn)
            elif is_to_existing_snippet:
                # Pushing folder contents to an existing snippet
                target_snippet = dest_folder
                
                # The folder container itself doesn't get pushed - only its contents
                # Show this as a "merge" operation into the snippet
                item_details.append({
                    'type': 'folder → snippet',
                    'name': f"{folder_name} → {target_snippet}",
                    'exists': True,  # Snippet exists
                    'strategy': strategy,
                    'action': f"Will merge contents into snippet '{target_snippet}'",
                    'error': None,
                    'warning': None,
                })
                # Don't count the folder itself as a new item - it's a container operation
            else:
                # Regular folder push (to a folder destination)
                # Folders are built-in in Prisma Access - they cannot be created/deleted
                # Only the contents within folders are pushed, not the folder container itself
                # So we don't add the folder to item_details - only its contents will be validated
                pass
            
            # Check objects within folder
            # If the container is going to a new snippet, all children auto-pass
            container_is_new_snippet = is_to_new_snippet and new_snippet_name
            # If going to existing snippet, need to check snippet-scoped conflicts
            container_is_existing_snippet = is_to_existing_snippet
            target_snippet_name = dest_folder if is_to_existing_snippet else new_snippet_name
            
            # Debug: Log container destination settings
            logger.debug(f"[Validation] Folder '{folder_name}' destination settings:")
            logger.debug(f"  is_to_new_snippet={is_to_new_snippet}, is_to_existing_snippet={is_to_existing_snippet}")
            logger.debug(f"  container_is_new_snippet={container_is_new_snippet}, container_is_existing_snippet={container_is_existing_snippet}")
            logger.debug(f"  target_snippet_name={target_snippet_name}, dest_folder={dest_folder}")
            
            for obj_type, obj_list in folder_data.get('objects', {}).items():
                if not isinstance(obj_list, list):
                    continue
                dest_objects = destination_config.get('objects', {}).get(obj_type, {})
                
                for obj in obj_list:
                    obj_name = obj.get('name', '')
                    total_items += 1
                    obj_strategy = get_item_strategy(obj)
                    obj_dest_name = get_destination_name(obj_name, obj_strategy, obj)

                    # Get per-item destination (overrides container destination if set)
                    item_dest_name, item_is_new_snippet, item_is_snippet = get_item_destination(obj)

                    # Use item destination if set, otherwise fall back to container destination
                    if item_dest_name:
                        # Item has its own destination
                        if item_is_new_snippet:
                            obj_is_new_snippet = True
                            obj_is_existing_snippet = False
                            obj_target_name = item_dest_name
                        elif item_is_snippet:
                            obj_is_new_snippet = False
                            obj_is_existing_snippet = True
                            obj_target_name = item_dest_name
                        else:
                            # Going to a folder
                            obj_is_new_snippet = False
                            obj_is_existing_snippet = False
                            obj_target_name = item_dest_name
                    else:
                        # Use container destination
                        obj_is_new_snippet = container_is_new_snippet
                        obj_is_existing_snippet = container_is_existing_snippet
                        obj_target_name = target_snippet_name if (container_is_new_snippet or container_is_existing_snippet) else folder_display_name

                    # Determine destination type
                    if obj_is_new_snippet or obj_is_existing_snippet:
                        dest_type = 'snippet'
                    else:
                        dest_type = 'folder'

                    # Check if this is a default/system profile - always skip
                    if is_default_profile(obj_type, obj_name):
                        skipped_items += 1
                        action = "Will SKIP (default/system profile)"
                        item_details.append({
                            'type': obj_type,
                            'name': obj_name,
                            'location': obj_target_name,
                            'dest_type': dest_type,
                            'exists': True,
                            'strategy': 'skip',
                            'action': action,
                            'warning': 'Default profile - cannot be modified',
                        })
                        continue

                    # Determine destination and conflict check
                    if obj_is_new_snippet:
                        # Going to NEW snippet - auto-pass (no conflicts possible)
                        exists = False
                        action = f"Will create in new snippet '{obj_target_name}'"
                        dest_location = obj_target_name
                    elif obj_is_existing_snippet:
                        # Going to EXISTING snippet - check snippet-scoped conflicts
                        snippet_objects = destination_config.get('snippet_objects', {}).get(obj_target_name, {}).get(obj_type, {})
                        exists = obj_name in snippet_objects
                        dest_location = obj_target_name
                        if exists:
                            action = f"Will {obj_strategy} in snippet '{obj_target_name}'"
                        else:
                            action = f"Will create in snippet '{obj_target_name}'"
                    else:
                        # Regular folder destination - global object check
                        exists = obj_name in dest_objects
                        dest_location = obj_target_name

                    if exists:
                        if obj_strategy == 'skip':
                            skipped_items += 1
                            if not obj_is_existing_snippet:
                                action = "Will SKIP (already exists)"
                        else:
                            conflicts += 1
                            if not obj_is_existing_snippet:
                                action = f"Will {obj_strategy}"
                    else:
                        new_items += 1
                        if not obj_is_new_snippet and not obj_is_existing_snippet:
                            action = "Will create"
                    
                    # Validate destination name length (use 'skip' strategy since we already have the dest name)
                    err, warn = check_name_length(obj_dest_name, obj_type, 'skip')
                    if err:
                        errors.append(err)
                    if warn:
                        warnings.append(warn)

                    # Only check dependencies if item will actually be pushed
                    # If item exists and strategy is SKIP, no need to check dependencies
                    obj_missing_deps = []
                    if not (exists and obj_strategy == 'skip'):
                        # Check dependencies - pass container info to find deps in same container
                        obj_missing_deps = check_dependencies(obj, obj_type, obj_name, 'folder', folder_name)

                    if obj_missing_deps:
                        for dep in obj_missing_deps:
                            # Add target destination info to the dependency
                            # Dependencies should go to the SAME destination as the item requiring them
                            dep['target_destination'] = {
                                'folder': dest_location,
                                'dest_type': dest_type,
                                'is_existing_snippet': obj_is_existing_snippet,
                                'is_new_snippet': obj_is_new_snippet,
                            }
                            if dep not in missing_dependencies:
                                missing_dependencies.append(dep)
                        dep_names = [d['name'] for d in obj_missing_deps]
                        dep_warning = f"Missing dependencies: {', '.join(dep_names)}"
                        warnings.append(f"{obj_dest_name}: {dep_warning}")

                    item_details.append({
                        'type': obj_type,
                        'name': obj_dest_name,
                        'location': dest_location,
                        'dest_type': dest_type,
                        'exists': exists,
                        'strategy': obj_strategy,
                        'action': action,
                        'error': err,
                        'warning': warn,
                        'missing_deps': [d['name'] for d in obj_missing_deps] if obj_missing_deps else None,
                    })
            
            # Check PROFILES within folder (wildfire_profile, anti_spyware_profile, etc.)
            for prof_type, prof_list in folder_data.get('profiles', {}).items():
                if not isinstance(prof_list, list):
                    continue
                dest_profiles = destination_config.get('objects', {}).get(prof_type, {})
                
                for prof in prof_list:
                    prof_name = prof.get('name', '')
                    total_items += 1
                    prof_strategy = get_item_strategy(prof)
                    prof_dest_name = get_destination_name(prof_name, prof_strategy, prof)

                    # Get per-item destination (overrides container destination if set)
                    item_dest_name, item_is_new_snippet, item_is_snippet = get_item_destination(prof)

                    # Use item destination if set, otherwise fall back to container destination
                    if item_dest_name:
                        if item_is_new_snippet:
                            prof_is_new_snippet = True
                            prof_is_existing_snippet = False
                            prof_target_name = item_dest_name
                        elif item_is_snippet:
                            prof_is_new_snippet = False
                            prof_is_existing_snippet = True
                            prof_target_name = item_dest_name
                        else:
                            prof_is_new_snippet = False
                            prof_is_existing_snippet = False
                            prof_target_name = item_dest_name
                    else:
                        prof_is_new_snippet = container_is_new_snippet
                        prof_is_existing_snippet = container_is_existing_snippet
                        prof_target_name = target_snippet_name if (container_is_new_snippet or container_is_existing_snippet) else folder_display_name

                    # Determine destination type
                    if prof_is_new_snippet or prof_is_existing_snippet:
                        dest_type = 'snippet'
                    else:
                        dest_type = 'folder'

                    # Check if this is a default/system profile - always skip
                    if is_default_profile(prof_type, prof_name):
                        skipped_items += 1
                        action = "Will SKIP (default/system profile)"
                        item_details.append({
                            'type': prof_type,
                            'name': prof_name,
                            'location': prof_target_name,
                            'dest_type': dest_type,
                            'exists': True,  # Mark as exists to prevent push
                            'strategy': 'skip',
                            'action': action,
                            'warning': 'Default profile - cannot be modified',
                        })
                        continue

                    if prof_is_new_snippet:
                        exists = False
                        action = f"Will create in new snippet '{prof_target_name}'"
                        dest_location = prof_target_name
                    elif prof_is_existing_snippet:
                        snippet_profs = destination_config.get('snippet_objects', {}).get(prof_target_name, {}).get(prof_type, {})
                        exists = prof_name in snippet_profs
                        dest_location = prof_target_name
                        if exists:
                            action = f"Will {prof_strategy} in snippet '{prof_target_name}'"
                        else:
                            action = f"Will create in snippet '{prof_target_name}'"
                    else:
                        exists = prof_name in dest_profiles
                        dest_location = prof_target_name

                    if exists:
                        if prof_strategy == 'skip':
                            skipped_items += 1
                            if not prof_is_existing_snippet:
                                action = "Will SKIP (already exists)"
                        else:
                            conflicts += 1
                            if not prof_is_existing_snippet:
                                action = f"Will {prof_strategy}"
                    else:
                        new_items += 1
                        if not prof_is_new_snippet and not prof_is_existing_snippet:
                            action = "Will create"
                    
                    # Validate destination name length
                    err, warn = check_name_length(prof_dest_name, prof_type, 'skip')
                    if err:
                        errors.append(err)
                    if warn:
                        warnings.append(warn)

                    # Special warning for certificate_profile - certificates need manual upload
                    cert_warning = None
                    if prof_type == 'certificate_profile' and not exists:
                        cert_warning = "[WARN] Certificate profile will be created but referenced certificates may need to be uploaded manually"
                        warnings.append(f"{prof_dest_name}: Certificates may need manual configuration")

                    item_details.append({
                        'type': prof_type,
                        'name': prof_dest_name,
                        'location': dest_location,
                        'dest_type': dest_type,
                        'exists': exists,
                        'strategy': prof_strategy,
                        'action': action,
                        'error': err,
                        'warning': cert_warning or warn,
                    })
            
            # Check HIP items within folder (hip_object, hip_profile)
            for hip_type, hip_list in folder_data.get('hip', {}).items():
                if not isinstance(hip_list, list):
                    continue
                dest_hip = destination_config.get('objects', {}).get(hip_type, {})

                for hip in hip_list:
                    hip_name = hip.get('name', '')
                    total_items += 1
                    hip_strategy = get_item_strategy(hip)
                    hip_dest_name = get_destination_name(hip_name, hip_strategy, hip)

                    # Get per-item destination (overrides container destination if set)
                    item_dest_name, item_is_new_snippet, item_is_snippet = get_item_destination(hip)

                    # Use item destination if set, otherwise fall back to container destination
                    if item_dest_name:
                        if item_is_new_snippet:
                            hip_is_new_snippet = True
                            hip_is_existing_snippet = False
                            hip_target_name = item_dest_name
                        elif item_is_snippet:
                            hip_is_new_snippet = False
                            hip_is_existing_snippet = True
                            hip_target_name = item_dest_name
                        else:
                            hip_is_new_snippet = False
                            hip_is_existing_snippet = False
                            hip_target_name = item_dest_name
                    else:
                        hip_is_new_snippet = container_is_new_snippet
                        hip_is_existing_snippet = container_is_existing_snippet
                        hip_target_name = target_snippet_name if (container_is_new_snippet or container_is_existing_snippet) else folder_display_name

                    # Determine destination type
                    if hip_is_new_snippet or hip_is_existing_snippet:
                        dest_type = 'snippet'
                    else:
                        dest_type = 'folder'

                    if hip_is_new_snippet:
                        exists = False
                        action = f"Will create in new snippet '{hip_target_name}'"
                        dest_location = hip_target_name
                    elif hip_is_existing_snippet:
                        snippet_hip = destination_config.get('snippet_objects', {}).get(hip_target_name, {}).get(hip_type, {})
                        exists = hip_name in snippet_hip
                        dest_location = hip_target_name
                        if exists:
                            action = f"Will {hip_strategy} in snippet '{hip_target_name}'"
                        else:
                            action = f"Will create in snippet '{hip_target_name}'"
                    else:
                        exists = hip_name in dest_hip
                        dest_location = hip_target_name

                    if exists:
                        if hip_strategy == 'skip':
                            skipped_items += 1
                            if not hip_is_existing_snippet:
                                action = "Will SKIP (already exists)"
                        else:
                            conflicts += 1
                            if not hip_is_existing_snippet:
                                action = f"Will {hip_strategy}"
                    else:
                        new_items += 1
                        if not hip_is_new_snippet and not hip_is_existing_snippet:
                            action = "Will create"
                    
                    # Validate destination name length
                    err, warn = check_name_length(hip_dest_name, hip_type, 'skip')
                    if err:
                        errors.append(err)
                    if warn:
                        warnings.append(warn)

                    item_details.append({
                        'type': hip_type,
                        'name': hip_dest_name,
                        'location': dest_location,
                        'dest_type': dest_type,
                        'exists': exists,
                        'strategy': hip_strategy,
                        'action': action,
                        'error': err,
                        'warning': warn,
                    })
            
            # Check rules within folder
            # Check security rules within folder
            # IMPORTANT: Security rules must be GLOBALLY unique across the entire tenant
            # UNLESS the destination is a NEW snippet (then auto-pass)
            # OR going to an existing snippet (rules scoped to snippet)
            rules_in_folder = folder_data.get('security_rules', [])
            if rules_in_folder:
                logger.debug(f"[Validation] Processing {len(rules_in_folder)} security rules for folder '{folder_name}'")
                logger.debug(f"[Validation] container_is_existing_snippet={container_is_existing_snippet}, target_snippet_name={target_snippet_name}")
            
            for rule in rules_in_folder:
                if not isinstance(rule, dict):
                    continue
                rule_name = rule.get('name', '')
                total_items += 1
                rule_strategy = get_item_strategy(rule)
                rule_dest_name = get_destination_name(rule_name, rule_strategy, rule)

                # Get per-item destination (overrides container destination if set)
                item_dest_name, item_is_new_snippet, item_is_snippet = get_item_destination(rule)

                # Use item destination if set, otherwise fall back to container destination
                if item_dest_name:
                    if item_is_new_snippet:
                        rule_is_new_snippet = True
                        rule_is_existing_snippet = False
                        rule_target_name = item_dest_name
                    elif item_is_snippet:
                        rule_is_new_snippet = False
                        rule_is_existing_snippet = True
                        rule_target_name = item_dest_name
                    else:
                        rule_is_new_snippet = False
                        rule_is_existing_snippet = False
                        rule_target_name = item_dest_name
                else:
                    rule_is_new_snippet = container_is_new_snippet
                    rule_is_existing_snippet = container_is_existing_snippet
                    rule_target_name = target_snippet_name if (container_is_new_snippet or container_is_existing_snippet) else folder_display_name

                # Determine destination and conflict check
                name_conflict_warn = None  # Track global name conflict warning separately

                if rule_is_new_snippet:
                    # Going to NEW snippet - still check global uniqueness for warnings
                    # The push can proceed, but user should know if rule names will conflict
                    # when the snippet is eventually associated with a folder
                    all_rule_names = destination_config.get('all_rule_names', {})
                    global_exists = rule_name in all_rule_names
                    existing_location = all_rule_names.get(rule_name, {})
                    display_location = rule_target_name

                    # For NEW snippets, mark as NEW (not EXISTS) but add warning if name conflicts
                    exists = False  # Don't block - new snippet has no local conflicts
                    new_items += 1

                    if global_exists:
                        conflict_loc = existing_location.get('folder') or existing_location.get('snippet') or 'unknown'
                        action = f"Will create in new snippet '{rule_target_name}'"
                        # Add warning about name conflict - store separately so it's shown in item details
                        name_conflict_warn = f"[WARN] Name conflict with '{conflict_loc}' - will need renaming before snippet association"
                        warnings.append(f"Rule '{rule_name}' name conflicts with existing rule in '{conflict_loc}'")
                    else:
                        action = f"Will create in new snippet '{rule_target_name}'"
                elif rule_is_existing_snippet:
                    # Going to EXISTING snippet - only check if rule exists in THIS snippet
                    # Snippets are isolated until associated with a folder
                    all_rule_names = destination_config.get('all_rule_names', {})
                    display_location = rule_target_name

                    # Check if rule exists in THIS specific snippet
                    rule_info = all_rule_names.get(rule_name, {})
                    rule_in_this_snippet = (
                        rule_info.get('snippet') == rule_target_name
                    )

                    if rule_in_this_snippet:
                        exists = True
                        existing_location = rule_info
                        conflicts += 1
                        action = f"Will {rule_strategy} in snippet '{rule_target_name}'"
                    else:
                        exists = False
                        existing_location = {}
                        new_items += 1
                        action = f"Will create in snippet '{rule_target_name}'"
                else:
                    # Regular folder destination - check if rule exists in ANY folder
                    # Folder rules are globally unique across all folders
                    all_rule_names = destination_config.get('all_rule_names', {})
                    display_location = folder_display_name  # Use display name
                    
                    # Debug: Log what we're checking
                    logger.debug(f"[Validation] Checking rule '{rule_name}' against all_rule_names ({len(all_rule_names)} rules)")
                    
                    # Check if rule exists in ANY folder (not snippets)
                    rule_info = all_rule_names.get(rule_name, {})
                    rule_in_folder = rule_info.get('folder') is not None
                    
                    # Debug: Log lookup result
                    if rule_info:
                        logger.debug(f"[Validation] Found rule '{rule_name}' in all_rule_names: folder={rule_info.get('folder')}, snippet={rule_info.get('snippet')}")
                    else:
                        logger.debug(f"[Validation] Rule '{rule_name}' NOT found in all_rule_names")
                    
                    if rule_in_folder:
                        exists = True
                        existing_location = rule_info
                        conflicts += 1
                        conflict_loc = existing_location.get('folder', 'unknown')
                        action = f"Will {rule_strategy} (exists in folder '{conflict_loc}')"
                    else:
                        exists = False
                        existing_location = {}
                        new_items += 1
                        action = "Will create"
                
                # Validate destination name length
                err, length_warn = check_name_length(rule_dest_name, 'security_rule', 'skip')
                if err:
                    errors.append(err)
                if length_warn:
                    warnings.append(length_warn)

                # Combine warnings - name conflict warning takes precedence for item display
                item_warn = name_conflict_warn or length_warn

                # Determine dest_type based on per-item destination
                if rule_is_new_snippet or rule_is_existing_snippet:
                    dest_type = 'snippet'
                else:
                    dest_type = 'folder'

                item_details.append({
                    'type': 'security_rule',
                    'name': rule_dest_name,
                    'location': display_location,
                    'dest_type': dest_type,
                    'exists': exists,
                    'existing_location': existing_location.get('folder') or existing_location.get('snippet') if exists else None,
                    'strategy': rule_strategy,
                    'action': action,
                    'error': err,
                    'warning': item_warn,
                })
        
        # Check snippets
        for snippet_data in self.selected_items.get('snippets', []):
            snippet_name = snippet_data.get('name', '')
            strategy = get_item_strategy(snippet_data)
            
            # Check if this is a new/renamed snippet
            dest_info = snippet_data.get('_destination', {})
            is_new_snippet = dest_info.get('is_new_snippet', False)
            is_rename_snippet = dest_info.get('is_rename_snippet', False)
            is_to_existing_snippet = dest_info.get('is_existing_snippet', False)
            new_snippet_name = dest_info.get('new_snippet_name', '')
            dest_folder = dest_info.get('folder', '')
            
            # Check if destination is an existing snippet (fallback detection)
            if not is_to_existing_snippet and not is_new_snippet and not is_rename_snippet:
                if dest_folder and dest_folder in existing_snippets:
                    is_to_existing_snippet = True
                # Also check if source snippet name exists in destination (inheriting location)
                elif snippet_name in existing_snippets:
                    is_to_existing_snippet = True
            
            err = None
            warn = None
            
            # IMPORTANT: Only add the snippet itself to validation results if:
            # 1. Creating a new snippet (is_new_snippet)
            # 2. Renaming a snippet (is_rename_snippet)
            # 
            # If pushing to an existing snippet or inheriting, the snippet container
            # is just organizational - only validate the objects inside.
            # The snippet is NOT counted as an item to validate.
            
            if is_new_snippet and new_snippet_name:
                # Creating a NEW snippet - check if the name already exists!
                total_items += 1  # Count this as a validation item
                snippet_exists = new_snippet_name in existing_snippets
                
                if snippet_exists:
                    # Snippet name conflict - this is an error
                    conflicts += 1
                    action = f"[WARN] Snippet '{new_snippet_name}' already exists!"
                    err = f"Cannot create snippet '{new_snippet_name}' - name already exists"
                    errors.append(err)
                    
                    item_details.append({
                        'type': 'snippet (conflict)',
                        'name': new_snippet_name,
                        'exists': True,
                        'strategy': strategy,
                        'action': action,
                        'error': err,
                        'warning': None,
                    })
                else:
                    # Validate the new snippet name length
                    err, warn = check_name_length(new_snippet_name, 'snippet', 'skip')
                    if err:
                        errors.append(err)
                    if warn:
                        warnings.append(warn)
                    action = f"Will create snippet '{new_snippet_name}'"
                    new_items += 1
                    
                    item_details.append({
                        'type': 'snippet (new)',
                        'name': new_snippet_name,
                        'exists': False,
                        'strategy': strategy,
                        'action': action,
                        'error': err,
                        'warning': warn,
                    })
            elif is_rename_snippet:
                # Renaming a snippet - check if the new name already exists
                total_items += 1  # Count this as a validation item
                # The new name is derived from destination_name (user may have edited it)
                renamed_name = dest_info.get('new_snippet_name', '') or f"{snippet_name}-copy"
                snippet_exists = renamed_name in existing_snippets
                
                if snippet_exists:
                    conflicts += 1
                    action = f"[WARN] Renamed snippet '{renamed_name}' already exists!"
                    err = f"Cannot rename snippet to '{renamed_name}' - name already exists"
                    errors.append(err)
                    
                    item_details.append({
                        'type': 'snippet (rename conflict)',
                        'name': renamed_name,
                        'exists': True,
                        'strategy': strategy,
                        'action': action,
                        'error': err,
                        'warning': None,
                    })
                else:
                    err, warn = check_name_length(renamed_name, 'snippet', 'skip')
                    if err:
                        errors.append(err)
                    if warn:
                        warnings.append(warn)
                    action = f"Will rename snippet to '{renamed_name}'"
                    new_items += 1
                    
                    item_details.append({
                        'type': 'snippet (rename)',
                        'name': f"{snippet_name} → {renamed_name}",
                        'exists': False,
                        'strategy': strategy,
                        'action': action,
                        'error': err,
                        'warning': warn,
                    })
            elif is_to_existing_snippet:
                # Pushing to an EXISTING snippet (selected from dropdown)
                # Don't add snippet to validation - only validate objects inside
                # The snippet exists, that's why we selected it - nothing to validate
                pass
            else:
                # Inheriting destination - keeping original snippet location
                # The source snippet may or may not exist in destination
                dest_snippets = destination_config.get('snippets', {})
                exists = snippet_name in dest_snippets
                
                if exists:
                    # Snippet exists in destination - just validate objects inside
                    # Don't add snippet itself to validation results
                    pass
                else:
                    # Snippet doesn't exist in destination - it will be created
                    # This IS a validation item since we're creating a new snippet
                    total_items += 1
                    new_items += 1
                    err, warn = check_name_length(snippet_name, 'snippet', strategy)
                    if err:
                        errors.append(err)
                    if warn:
                        warnings.append(warn)
                    
                    item_details.append({
                        'type': 'snippet (auto-create)',
                        'name': snippet_name,
                        'exists': False,
                        'strategy': strategy,
                        'action': f"Will create snippet '{snippet_name}'",
                        'error': err,
                        'warning': warn,
                    })
            
            # Check objects within snippet
            # If this is a new/renamed snippet, all objects auto-pass (no conflict possible)
            snippet_is_new = is_new_snippet and new_snippet_name
            
            for obj_type, obj_list in snippet_data.get('objects', {}).items():
                if not isinstance(obj_list, list):
                    continue
                dest_objects = destination_config.get('objects', {}).get(obj_type, {})
                
                for obj in obj_list:
                    obj_name = obj.get('name', '')
                    total_items += 1
                    obj_strategy = get_item_strategy(obj)
                    obj_dest_name = get_destination_name(obj_name, obj_strategy, obj)

                    # Check item-level destination (may override container destination)
                    obj_dest_info = obj.get('_destination', {})
                    obj_dest_folder = obj_dest_info.get('folder', '') or dest_folder
                    obj_is_existing_snippet = obj_dest_info.get('is_existing_snippet', False) or is_to_existing_snippet
                    obj_is_new_snippet = obj_dest_info.get('is_new_snippet', False) or snippet_is_new
                    obj_new_snippet_name = obj_dest_info.get('new_snippet_name', '') or new_snippet_name
                    
                    # DEBUG: Log destination resolution for each item
                    logger.debug(f"[Validation] Item '{obj_name}' ({obj_type}) destination: "
                                f"obj_dest_info={obj_dest_info}, "
                                f"obj_dest_folder={obj_dest_folder}, "
                                f"obj_is_existing_snippet={obj_is_existing_snippet}")
                    
                    # Re-check if destination is an existing snippet based on item's destination
                    if not obj_is_existing_snippet and not obj_is_new_snippet:
                        if obj_dest_folder and obj_dest_folder in existing_snippets:
                            obj_is_existing_snippet = True
                        # Also check source snippet name for inherit case
                        elif not obj_dest_folder and snippet_name in existing_snippets:
                            obj_is_existing_snippet = True
                            obj_dest_folder = snippet_name  # Use source snippet as destination
                    
                    # If dest_folder is empty but we're going to existing snippet, use snippet_name
                    if obj_is_existing_snippet and not obj_dest_folder:
                        obj_dest_folder = snippet_name
                    
                    # If parent snippet is new OR item is going to a new snippet, auto-pass
                    if obj_is_new_snippet or is_destination_new_snippet(obj):
                        exists = False
                        new_items += 1
                        action = f"Will create in '{obj_new_snippet_name}'"
                    elif obj_is_existing_snippet:
                        # Going to an existing snippet - check within that snippet
                        target_snippet = obj_dest_folder
                        snippet_objects = destination_config.get('snippet_objects', {}).get(target_snippet, {}).get(obj_type, {})
                        exists = obj_name in snippet_objects
                        if exists:
                            if obj_strategy == 'skip':
                                skipped_items += 1
                                action = f"Will SKIP (already exists in '{target_snippet}')"
                            else:
                                conflicts += 1
                                action = f"Will {obj_strategy} in snippet '{target_snippet}'"
                        else:
                            new_items += 1
                            action = f"Will create in snippet '{target_snippet}'"
                    else:
                        exists = obj_name in dest_objects
                        if exists:
                            if obj_strategy == 'skip':
                                skipped_items += 1
                                action = "Will SKIP (already exists)"
                            else:
                                conflicts += 1
                                action = f"Will {obj_strategy}"
                        else:
                            new_items += 1
                            action = "Will create"
                    
                    # Validate destination name length
                    err, warn = check_name_length(obj_dest_name, obj_type, 'skip')
                    if err:
                        errors.append(err)
                    if warn:
                        warnings.append(warn)

                    # Only check dependencies if item will actually be pushed
                    # If item exists and strategy is SKIP, no need to check dependencies
                    obj_missing_deps = []
                    if not (exists and obj_strategy == 'skip'):
                        # Check dependencies - pass container info to find deps in same snippet
                        obj_missing_deps = check_dependencies(obj, obj_type, obj_name, 'snippet', snippet_name)

                    if obj_missing_deps:
                        # Determine target destination for dependencies - use ITEM's destination, not container
                        dep_dest_location = obj_new_snippet_name if obj_is_new_snippet else obj_dest_folder if obj_dest_folder else snippet_name
                        dep_is_existing = obj_is_existing_snippet
                        dep_is_new = obj_is_new_snippet

                        # DEBUG: Log the destination resolution for dependencies
                        logger.debug(f"[Validation] Dependencies for '{obj_dest_name}' will use destination:")
                        logger.debug(f"  obj_new_snippet_name={obj_new_snippet_name}, obj_dest_folder={obj_dest_folder}, snippet_name={snippet_name}")
                        logger.debug(f"  -> dep_dest_location={dep_dest_location}, dep_is_existing={dep_is_existing}")

                        for dep in obj_missing_deps:
                            # Add target destination info to the dependency
                            # Dependencies should go to the SAME destination as the item requiring them
                            dep['target_destination'] = {
                                'folder': dep_dest_location,
                                'dest_type': 'snippet',
                                'is_existing_snippet': dep_is_existing,
                                'is_new_snippet': dep_is_new,
                            }
                            if dep not in missing_dependencies:
                                missing_dependencies.append(dep)
                        dep_names = [d['name'] for d in obj_missing_deps]
                        dep_warning = f"Missing dependencies: {', '.join(dep_names)}"
                        warnings.append(f"{obj_dest_name}: {dep_warning}")
                    
                    # Determine the correct destination location to display - use ITEM's destination
                    if obj_is_new_snippet:
                        display_location = obj_new_snippet_name
                    elif obj_is_existing_snippet and obj_dest_folder:
                        display_location = obj_dest_folder
                    else:
                        display_location = snippet_name  # Keeping original location
                    
                    item_details.append({
                        'type': obj_type,
                        'name': obj_dest_name,
                        'location': display_location,
                        'dest_type': 'snippet',
                        'exists': exists,
                        'strategy': obj_strategy,
                        'action': action,
                        'error': err,
                        'warning': warn,
                        'missing_deps': [d['name'] for d in obj_missing_deps] if obj_missing_deps else None,
                    })

            # Check security rules within snippet
            # Rule conflict logic:
            # 1. NEW snippet destination: No conflict (warn about global name conflicts for future association)
            # 2. EXISTING snippet destination: Only conflict if rule exists in THIS snippet
            for rule in snippet_data.get('security_rules', []):
                if not isinstance(rule, dict):
                    continue
                rule_name = rule.get('name', '')
                total_items += 1
                rule_strategy = get_item_strategy(rule)
                rule_dest_name = get_destination_name(rule_name, rule_strategy, rule)
                name_conflict_warn = None  # Track global name conflict warning separately
                
                all_rule_names = destination_config.get('all_rule_names', {})
                rule_info = all_rule_names.get(rule_name, {})
                global_exists = rule_name in all_rule_names
                
                # Determine destination snippet name
                target_snippet = new_snippet_name if snippet_is_new else snippet_name
                
                # If parent snippet is new, rule goes in, but warn about conflicts
                if snippet_is_new or is_destination_new_snippet(rule):
                    exists = False  # Don't block - new snippet has no local conflicts
                    existing_location = {}
                    new_items += 1
                    target_name = new_snippet_name or snippet_name
                    
                    if global_exists:
                        conflict_loc = rule_info.get('folder') or rule_info.get('snippet') or 'unknown'
                        action = f"Will create in '{target_name}'"
                        name_conflict_warn = f"[WARN] Name conflict with '{conflict_loc}' - will need renaming before snippet association"
                        warnings.append(f"Rule '{rule_name}' name conflicts with existing rule in '{conflict_loc}'")
                    else:
                        action = f"Will create in '{target_name}'"
                else:
                    # Existing snippet - only conflict if rule exists in THIS specific snippet
                    rule_in_this_snippet = (rule_info.get('snippet') == target_snippet)
                    
                    if rule_in_this_snippet:
                        exists = True
                        existing_location = rule_info
                        conflicts += 1
                        action = f"Will {rule_strategy} in snippet '{target_snippet}'"
                    else:
                        exists = False
                        existing_location = {}
                        new_items += 1
                        action = f"Will create in snippet '{target_snippet}'"
                
                # Validate destination name length
                err, length_warn = check_name_length(rule_dest_name, 'security_rule', 'skip')
                if err:
                    errors.append(err)
                if length_warn:
                    warnings.append(length_warn)

                # Combine warnings - name conflict warning takes precedence for item display
                item_warn = name_conflict_warn or length_warn

                item_details.append({
                    'type': 'security_rule',
                    'name': rule_dest_name,
                    'location': target_snippet,
                    'dest_type': 'snippet',
                    'exists': exists,
                    'existing_location': f"{existing_location.get('folder') or existing_location.get('snippet')}" if exists else None,
                    'strategy': rule_strategy,
                    'action': action,
                    'error': err,
                    'warning': item_warn,
                })
        
        # Check infrastructure
        for infra_type, infra_list in self.selected_items.get('infrastructure', {}).items():
            if not isinstance(infra_list, list):
                continue
            dest_infra = destination_config.get('infrastructure', {}).get(infra_type, {})
            
            for item in infra_list:
                item_name = item.get('name', item.get('id', ''))
                total_items += 1
                item_strategy = get_item_strategy(item)
                item_dest_name = get_destination_name(item_name, item_strategy, item)

                exists = item_name in dest_infra
                if exists:
                    conflicts += 1
                    action = f"Will {item_strategy}"
                else:
                    new_items += 1
                    action = "Will create"
                
                # Validate destination name length
                err, warn = check_name_length(item_dest_name, infra_type, 'skip')
                if err:
                    errors.append(err)
                if warn:
                    warnings.append(warn)

                item_details.append({
                    'type': infra_type,
                    'name': item_dest_name,
                    'exists': exists,
                    'strategy': item_strategy,
                    'action': action,
                    'error': err,
                    'warning': warn,
                })
        
        # Get reference conflicts from destination config (rules referencing objects we're pushing)
        reference_conflicts = destination_config.get('reference_conflicts', [])
        
        return {
            'errors': errors,
            'warnings': warnings,
            'item_details': item_details,
            'new_items': new_items,
            'conflicts': conflicts,
            'skipped_items': skipped_items,
            'total_items': total_items,
            'missing_dependencies': missing_dependencies,
            'reference_conflicts': reference_conflicts,
        }
    
    def _show_validation_details(self, validation_results: Dict[str, Any]):
        """Show validation details in the results panel."""
        lines = []
        lines.append("=" * 70)
        lines.append("PUSH VALIDATION SUMMARY")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"Total Items: {validation_results['total_items']}")
        lines.append(f"  New: {validation_results['new_items']}")
        lines.append(f"  Conflicts: {validation_results['conflicts']}")
        lines.append(f"  Errors: {len(validation_results['errors'])}")
        lines.append(f"  Warnings: {len(validation_results['warnings'])}")
        lines.append("")
        
        # Show errors first
        if validation_results['errors']:
            lines.append("=" * 70)
            lines.append("[ERROR] ERRORS (must fix before push)")
            lines.append("=" * 70)
            for err in validation_results['errors']:
                lines.append(f"  ✗ {err}")
            lines.append("")
        
        # Show warnings
        if validation_results['warnings']:
            lines.append("=" * 70)
            lines.append("[WARN] WARNINGS")
            lines.append("=" * 70)
            for warn in validation_results['warnings']:
                lines.append(f"  ⚠ {warn}")
            lines.append("")
        
        # Show per-item details
        lines.append("=" * 70)
        lines.append("ITEM DETAILS")
        lines.append("=" * 70)
        
        for item in validation_results['item_details']:
            status_icon = "✓" if not item.get('exists') else "⚠"
            location = f" ({item.get('location', '')})" if item.get('location') else ""
            lines.append(f"  {status_icon} {item['type']}: {item['name']}{location}")
            lines.append(f"      Action: {item['action']}")
            if item.get('error'):
                lines.append(f"      [ERROR] {item['error']}")
            if item.get('warning'):
                lines.append(f"      [WARN] {item['warning']}")
        
        lines.append("")
        lines.append("=" * 70)
        
        self.results_panel.set_text("\n".join(lines))
    
    def _update_status(self):
        """Update status label and enable/disable push button."""
        # Don't overwrite success message after push completes
        if self.push_completed_successfully:
            return
        
        if not self.destination_client:
            self.status_label.setText("[ERROR] Select destination tenant in 'Select Components' tab")
            self.status_label.setStyleSheet(
                "color: orange; padding: 10px; background-color: #fff4e6;"
            )
            self.push_btn.setEnabled(False)
            self.progress_label.setText("Select destination tenant")
            self._update_summary_label()
        elif not self.config:
            self.status_label.setText("[ERROR] No configuration loaded - Pull or load a config first")
            self.status_label.setStyleSheet(
                "color: orange; padding: 10px; background-color: #fff4e6;"
            )
            self.push_btn.setEnabled(False)
            self.progress_label.setText("Load or pull a configuration")
            self._update_summary_label()
        elif not self.selected_items:
            self.status_label.setText("[ERROR] Go to 'Select Components' tab to choose what to push")
            self.status_label.setStyleSheet(
                "color: orange; padding: 10px; background-color: #fff4e6;"
            )
            self.push_btn.setEnabled(False)
            self.progress_label.setText("Select components to push")
            self._update_summary_label()
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
            
            # Update summary label
            self._update_summary_label()
            
            if is_same_tenant:
                # Warning: pushing to same tenant
                status_text = f"[WARN] Warning: Pushing {total_items} items to the Same Tenant"
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
                status_text = f"✓ Ready to validate {total_items} items for {dest_display}"
                if status_parts:
                    status_text += f" ({', '.join(status_parts)})"
                
                self.status_label.setText(status_text)
                self.status_label.setStyleSheet(
                    "color: #2e7d32; padding: 12px; background-color: #e8f5e9; border-radius: 5px; "
                    "font-size: 13px; border: 1px solid #4CAF50;"
                )
                # Reset push button to default style
                self.push_btn.setStyleSheet(
                    "QPushButton { "
                    "  background-color: #4CAF50; color: white; padding: 10px 20px; "
                    "  font-size: 14px; font-weight: bold; border-radius: 5px; "
                    "  border: 1px solid #388E3C; border-bottom: 3px solid #2E7D32; "
                    "}"
                    "QPushButton:hover { background-color: #45a049; border-bottom: 3px solid #1B5E20; }"
                    "QPushButton:pressed { background-color: #388E3C; border-bottom: 1px solid #2E7D32; }"
                    "QPushButton:disabled { background-color: #BDBDBD; border: 1px solid #9E9E9E; border-bottom: 3px solid #757575; }"
                )
                self.progress_label.setText("Ready - click Validate to check for conflicts")
                self.progress_label.setStyleSheet("color: green;")
            
            # Push button will be enabled after auto-validation passes
            # Validation is auto-triggered when tab is shown
    
    def _update_summary_label(self):
        """Update the selection summary label with comprehensive summary."""
        if not self.selected_items:
            self.summary_label.setText("No items selected")
            self.new_snippet_indicator.setVisible(False)
            return
        
        # Count items from the nested folder structure
        folder_items = {}  # folder_name -> count
        snippet_items = {}  # snippet_name -> count
        infra_items = {}  # infra_type -> count
        
        # Track special operations
        new_snippets = []
        rename_count = 0
        overwrite_count = 0
        
        # Count items in folders
        for folder in self.selected_items.get('folders', []):
            folder_name = folder.get('name', 'Unknown')
            count = 0
            
            # Count objects
            for obj_type, items in folder.get('objects', {}).items():
                count += len(items)
                for item in items:
                    self._check_item_operations(item, new_snippets)
            
            # Count profiles
            for prof_type, items in folder.get('profiles', {}).items():
                count += len(items)
                for item in items:
                    self._check_item_operations(item, new_snippets)
            
            # Count HIP
            for hip_type, items in folder.get('hip', {}).items():
                count += len(items)
            
            # Count rules
            count += len(folder.get('security_rules', []))
            for rule in folder.get('security_rules', []):
                self._check_item_operations(rule, new_snippets)
            
            if count > 0:
                folder_items[folder_name] = count
        
        # Count items in snippets
        for snippet in self.selected_items.get('snippets', []):
            snippet_name = snippet.get('name', 'Unknown')
            count = 0
            
            for obj_type, items in snippet.get('objects', {}).items():
                count += len(items)
            for prof_type, items in snippet.get('profiles', {}).items():
                count += len(items)
            count += len(snippet.get('security_rules', []))
            
            if count > 0:
                snippet_items[snippet_name] = count
        
        # Count infrastructure by type
        infrastructure = self.selected_items.get('infrastructure', {})
        for infra_type, items in infrastructure.items():
            if isinstance(items, list) and len(items) > 0:
                infra_items[infra_type] = len(items)
        
        # Build summary text
        lines = []
        
        # Total count
        total_folders = sum(folder_items.values())
        total_snippets = sum(snippet_items.values())
        total_infra = sum(infra_items.values())
        total = total_folders + total_snippets + total_infra
        
        lines.append(f"<b>{total} items selected</b>")
        
        # Breakdown by location
        location_parts = []
        if folder_items:
            for folder, count in sorted(folder_items.items()):
                display_name = self._get_folder_display_name(folder)
                location_parts.append(f"📁 {display_name}: {count}")
        if snippet_items:
            for snippet, count in sorted(snippet_items.items()):
                location_parts.append(f"📄 {snippet}: {count}")
        if infra_items:
            infra_total = sum(infra_items.values())
            location_parts.append(f"🏗️ Infrastructure: {infra_total}")
        
        if location_parts:
            lines.append(" | ".join(location_parts))
        
        # Special operations summary
        ops_parts = []
        if new_snippets:
            ops_parts.append(f"➕ Creating {len(new_snippets)} new snippet(s)")
        
        default_strategy = self.selected_items.get('default_strategy', 'skip')
        if default_strategy == 'rename':
            ops_parts.append(f"📝 Strategy: Rename duplicates")
        elif default_strategy == 'overwrite':
            ops_parts.append(f"📋 Strategy: Overwrite existing")
        else:
            ops_parts.append(f"⏭️ Strategy: Skip existing")
        
        if ops_parts:
            lines.append(" | ".join(ops_parts))
        
        self.summary_label.setText("<br>".join(lines))
        
        # New snippet indicator
        if new_snippets:
            self.new_snippet_indicator.setText(f"➕ Creating new snippet(s): {', '.join(new_snippets)}")
            self.new_snippet_indicator.setVisible(True)
        else:
            self.new_snippet_indicator.setVisible(False)
    
    def _check_item_operations(self, item: Dict[str, Any], new_snippets: list):
        """Check item for special operations like new snippets."""
        dest = item.get('_destination', {})
        if dest.get('is_new_snippet'):
            new_name = dest.get('new_snippet_name', 'unnamed')
            if new_name and new_name not in new_snippets:
                new_snippets.append(new_name)
    
    def _get_folder_display_name(self, folder: str) -> str:
        """Get display name for a folder."""
        display_names = {
            'All': 'Global',
            'Shared': 'Prisma Access',
        }
        return display_names.get(folder, folder)

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
        """Start the push operation or handle Add & Revalidate."""
        # Check if we're in "Add and Revalidate" mode
        if hasattr(self, '_pending_missing_dependencies') and self._pending_missing_dependencies:
            self._add_missing_dependencies_and_revalidate()
            return
        
        if not self.destination_client or not self.config:
            return

        # Get conflict resolution from default strategy in selected_items
        # (per-item strategies are handled by the push orchestrator)
        default_strategy = self.selected_items.get('default_strategy', 'skip').upper()
        resolution = default_strategy

        dry_run = self.dry_run_check.isChecked()

        # Use the destination config from validation if available
        destination_config = getattr(self, '_destination_config', None)
        
        dest_display = self.destination_name if self.destination_name else self.destination_client.tsg_id

        # Show warning confirmation AFTER preview
        if not dry_run:
            # Use warning dialog with red border and ! icon
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("[WARN] Confirm Push")
            msg_box.setText(f"<b>Push configuration to {dest_display}?</b>")
            msg_box.setInformativeText(
                f"Conflict Resolution: {resolution}\n\n"
                f"[WARN] This will modify the target tenant.\n"
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
        
        # Reset cancelled flag
        self._push_cancelled = False
        
        # Acquire workflow lock to prevent navigation during push
        self.workflow_lock.acquire_lock(
            owner=self,
            operation_name="Push",
            cancel_callback=self._cancel_push_operation
        )
        
        # Disable UI during push
        self._set_ui_enabled(False)

        # Hide validation section to make room for progress/results
        self.validation_group.setVisible(False)
        
        # Hide push button and dry run checkbox during push, show cancel button
        self.push_btn.setVisible(False)
        self.dry_run_check.setVisible(False)
        self.return_to_selection_btn.setVisible(False)
        self.cancel_btn.setVisible(True)

        # Show progress section
        self.progress_group.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.progress_label.setText("Preparing to push configuration...")
        
        # Show results section
        self.results_group.setVisible(True)

        # Initialize results panel with header
        dest_name = self.destination_name if self.destination_name else "destination"
        dry_run_text = " (DRY RUN - No changes will be made)" if dry_run else ""
        header = f"{'='*70}\nPUSH OPERATION{dry_run_text}\nDestination: {dest_name}\n{'='*70}\n\n"
        self.results_panel.set_text(header)

        # Create and start worker
        from gui.workers import SelectivePushWorker

        # Filter selected_items to only include items that need action
        # (excludes items that validation determined will be skipped)
        filtered_items = self._filter_items_for_push(self.selected_items)

        self.worker = SelectivePushWorker(
            self.destination_client,
            filtered_items,
            destination_config,
            resolution
        )
        self.worker.progress.connect(self._on_push_progress, Qt.ConnectionType.QueuedConnection)
        self.worker.finished.connect(self._on_push_finished, Qt.ConnectionType.QueuedConnection)
        self.worker.error.connect(self._on_error, Qt.ConnectionType.QueuedConnection)
        self.worker.start()
    
    def _cancel_push_operation(self) -> bool:
        """
        Cancel the current push operation.
        
        Returns:
            True if cancellation was successful, False otherwise
        """
        # Use existing cancel push logic
        return self._cancel_push()

    def _on_push_progress(self, message: str, current: int, total: int):
        """Handle selective push progress updates."""
        self.progress_label.setText(message)
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
        
        # Append progress message to results panel for real-time tracking
        current_text = self.results_panel.results_text.toPlainText()
        timestamp = ""
        # Format: [current/total] message
        progress_line = f"[{current}/{total}] {message}\n"
        self.results_panel.results_text.setPlainText(current_text + progress_line)
        # Auto-scroll to bottom
        scrollbar = self.results_panel.results_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_progress(self, message: str, percentage: int):
        """Handle progress updates."""
        self.progress_label.setText(message)
        self.progress_bar.setValue(percentage)

    def _on_push_finished(self, success: bool, message: str, result: Optional[Dict]):
        """Handle push completion."""
        # Release workflow lock - push is complete
        self.workflow_lock.release_lock(self)
        
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
                        status_msg = f"[WARN] Push completed with issues ({unique_count} items)"
                        status_color = "#F57F17"  # Dark yellow/amber
                        status_bg = "#FFF9C4"     # Light yellow
                        status_border = "#FBC02D" # Medium yellow
                        progress_text = "Completed with issues"
                        progress_color = "#F57F17"
                    elif has_failures and not has_successes:
                        # All failed - red
                        status_msg = f"[ERROR] Push failed ({unique_count} items)"
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
                    
                    # Note: status_label is internal state only, not added to layout
                    # Don't make it visible as it would appear as floating window
                    self.status_label.setText(status_msg)
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
                
                # APPEND summary to existing results (don't overwrite)
                try:
                    # Get detailed results from the orchestrator
                    results_data = result.get('results', {}) if isinstance(result, dict) else {}
                    all_details = results_data.get('details', []) if isinstance(results_data, dict) else []
                    
                    # Count unique items by (type, name, destination)
                    # Exclude validation-only skips (default profiles that were never sent to push)
                    unique_items = set()
                    for d in all_details:
                        # Skip items that were validation-only skips (default profiles)
                        msg = d.get('message', '')
                        if d.get('action') == 'skipped' and 'Default' in msg and 'system profile' in msg:
                            continue
                        item_key = (d.get('type'), d.get('name'), d.get('destination'))
                        unique_items.add(item_key)
                    
                    total_unique_items = len(unique_items)
                    
                    # Categorize results by action and success
                    created_success = [d for d in all_details if d.get('action') == 'created' and d.get('success')]
                    deleted_success = [d for d in all_details if d.get('action') == 'deleted' and d.get('success')]
                    created_failed = [d for d in all_details if d.get('action') == 'failed' and not d.get('success')]
                    updated_success = [d for d in all_details if d.get('action') == 'updated' and d.get('success')]
                    renamed_success = [d for d in all_details if d.get('action') == 'renamed' and d.get('success')]
                    # Filter skipped items to exclude validation-only skips (default profiles)
                    skipped_items = [
                        d for d in all_details 
                        if d.get('action') == 'skipped' 
                        and not ('Default' in d.get('message', '') and 'system profile' in d.get('message', ''))
                    ]
                    
                    # Build summary to APPEND to existing output
                    summary_lines = []
                    summary_lines.append("")
                    summary_lines.append("=" * 70)
                    summary_lines.append("PUSH OPERATION COMPLETE")
                    summary_lines.append("=" * 70)
                    summary_lines.append("")
                    summary_lines.append(f"Total Items: {total_unique_items}")
                    if deleted_success:
                        summary_lines.append(f"  ✓ Deleted:   {len(deleted_success)}")
                    summary_lines.append(f"  ✓ Created:   {len(created_success)}")
                    if updated_success:
                        summary_lines.append(f"  ✓ Updated:   {len(updated_success)}")
                    if renamed_success:
                        summary_lines.append(f"  ✓ Renamed:   {len(renamed_success)}")
                    if skipped_items:
                        summary_lines.append(f"  ⊘ Skipped:   {len(skipped_items)}")
                    if created_failed:
                        summary_lines.append(f"  ✗ Failed:    {len(created_failed)}")
                    
                    # Show failed items in summary
                    if created_failed:
                        summary_lines.append("")
                        summary_lines.append("[ERROR] FAILED ITEMS:")
                        for item in created_failed:
                            item_type = item.get('type', 'unknown')
                            item_name = item.get('name', 'unknown')
                            error_msg = item.get('error', item.get('message', 'Unknown error'))
                            # Extract meaningful error message
                            import re
                            unique_match = re.search(r"'([^']+)' is already in use", error_msg)
                            ref_match = re.search(r"'([^']+)' is not a valid reference", error_msg)
                            if unique_match:
                                summary_lines.append(f"  ✗ {item_type}: {item_name}")
                                summary_lines.append(f"      Error: Name '{unique_match.group(1)}' already exists in tenant")
                            elif ref_match:
                                summary_lines.append(f"  ✗ {item_type}: {item_name}")
                                summary_lines.append(f"      Error: Invalid reference - '{ref_match.group(1)}' not found")
                            else:
                                summary_lines.append(f"  ✗ {item_type}: {item_name}")
                                summary_lines.append(f"      Error: {error_msg[:100]}")
                    
                    summary_lines.append("")
                    summary_lines.append("=" * 70)
                    summary_lines.append("Click 'View Details' for complete activity log")
                    summary_lines.append("=" * 70)
                    
                    # APPEND to existing results instead of overwriting
                    current_text = self.results_panel.results_text.toPlainText()
                    self.results_panel.results_text.setPlainText(current_text + "\n".join(summary_lines))
                    
                    # Auto-scroll to bottom
                    scrollbar = self.results_panel.results_text.verticalScrollBar()
                    scrollbar.setValue(scrollbar.maximum())
                except Exception as results_err:
                    # Log the error for debugging
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error formatting results: {results_err}")

                # Emit signal (wrapped in try/except)
                try:
                    self.push_completed.emit(result)
                except Exception as e:
                    # Avoid print in case this runs in thread context
                    pass
            else:
                # Update status banner with error message
                # Note: status_label is internal state only, not added to layout
                self.status_label.setText(f"[ERROR] Push failed: {message}")
                
                self.progress_label.setText("Push failed")
                self.progress_label.setStyleSheet("color: red;")
                
                # APPEND error to existing results
                current_text = self.results_panel.results_text.toPlainText()
                error_lines = [
                    "",
                    "=" * 70,
                    "[ERROR] PUSH OPERATION FAILED",
                    "=" * 70,
                    "",
                    f"Error: {message}",
                    "",
                    "=" * 70,
                ]
                self.results_panel.results_text.setPlainText(current_text + "\n".join(error_lines))
                
                # Auto-scroll to bottom
                scrollbar = self.results_panel.results_text.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
        except Exception as e:
            # Avoid print in case this runs in thread context
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in _on_push_finished: {e}")
        finally:
            # Hide cancel button, show return to selection button
            self.cancel_btn.setVisible(False)
            self.return_to_selection_btn.setVisible(True)
            
            # Clean up worker after a delay to prevent premature garbage collection
            try:
                from PyQt6.QtCore import QTimer
                if hasattr(self, 'worker') and self.worker:
                    QTimer.singleShot(1000, lambda: self.worker.deleteLater() if hasattr(self, 'worker') else None)
            except:
                pass

    def _on_error(self, error_message: str):
        """Handle errors - just log, don't show popup (results panel is enough)."""
        # Don't treat "Push completed!" as an error - it's a summary message
        if "Push completed" in error_message:
            return
        
        # Release workflow lock on error
        self.workflow_lock.release_lock(self)
        
        self.progress_label.setText("Error occurred")
        self.progress_label.setStyleSheet("color: red;")
        # Don't show popup - the results panel and status bar already show the error
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Push issue: {error_message}")

    def _on_conflicts(self, conflicts: list):
        """Handle detected conflicts."""
        conflict_text = f"Detected {len(conflicts)} conflicts:\n\n"
        for conflict in conflicts[:10]:  # Show first 10
            conflict_text += f"- {conflict.get('name', 'Unknown')}\n"
        if len(conflicts) > 10:
            conflict_text += f"\n... and {len(conflicts) - 10} more"

        self.results_panel.set_text(conflict_text)
    
    def _cancel_push(self) -> bool:
        """
        Cancel the ongoing push operation.
        
        Returns:
            True if cancellation was successful
        """
        import logging
        logger = logging.getLogger(__name__)
        
        self._push_cancelled = True
        logger.normal("[Push] Cancelling push operation...")
        
        # Stop the worker if it exists
        if hasattr(self, 'worker') and self.worker:
            # Signal the worker to stop
            if hasattr(self.worker, 'stop'):
                self.worker.stop()
            
            # Wait briefly for worker to stop
            self.worker.wait(2000)  # Wait up to 2 seconds
            
            # Force terminate if still running
            if self.worker.isRunning():
                self.worker.terminate()
                self.worker.wait()
        
        # Release workflow lock
        self.workflow_lock.release_lock(self)
        
        # Update UI
        self.progress_label.setText("Push cancelled by user")
        self.progress_label.setStyleSheet("color: #F57F17; font-weight: bold;")
        
        # Append cancellation message to results
        current_text = self.results_panel.results_text.toPlainText()
        cancel_lines = [
            "",
            "=" * 70,
            "[WARN] PUSH OPERATION CANCELLED",
            "=" * 70,
            "",
            "Push was cancelled by user. Some items may have been pushed before cancellation.",
            "",
        ]
        self.results_panel.results_text.setPlainText(current_text + "\n".join(cancel_lines))
        
        # Auto-scroll to bottom
        scrollbar = self.results_panel.results_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        # Hide cancel button, show return to selection
        self.cancel_btn.setVisible(False)
        self.return_to_selection_btn.setVisible(True)
        
        # Re-enable UI
        self._set_ui_enabled(True)
        
        logger.normal("[Push] Push operation cancelled")
        
        return True

    def _set_ui_enabled(self, enabled: bool):
        """Enable or disable UI controls."""
        self.dry_run_check.setEnabled(enabled)
        # Phase 3: Enable push only if we have config, destination, AND selection
        # Convert to bool to avoid passing dict to setEnabled
        should_enable = enabled and bool(self.destination_client) and bool(self.config) and bool(self.selected_items)
        self.push_btn.setEnabled(should_enable)
    
    def _toggle_live_log_viewer(self):
        """Toggle the live log viewer visibility."""
        if self.live_log_container.isVisible():
            self._hide_live_log_viewer()
        else:
            self._show_live_log_viewer()
    
    def _show_live_log_viewer(self):
        """Show and start the live log viewer."""
        self.live_log_container.setVisible(True)
        
        # Update button text to indicate it can be hidden
        self.results_panel.view_details_btn.setText("📄 Hide Activity Log")
        
        # Load recent entries and start live monitoring
        self.live_log_viewer.load_recent(50)
        self.live_log_viewer.start_live()
    
    def _hide_live_log_viewer(self):
        """Hide and stop the live log viewer."""
        self.live_log_container.setVisible(False)
        
        # Restore button text
        self.results_panel.view_details_btn.setText("📄 View Activity Log")
        
        # Stop live monitoring
        self.live_log_viewer.stop_live()
    
    def _return_to_selection(self):
        """Return to the selection screen to modify selection or push again."""
        # Hide progress and results
        self.progress_group.setVisible(False)
        self.results_group.setVisible(False)
        self.return_to_selection_btn.setVisible(False)
        
        # Hide live log viewer if visible
        self._hide_live_log_viewer()
        
        # Show validation section again
        self.validation_group.setVisible(True)
        
        # Show push button and dry run checkbox again
        self.push_btn.setVisible(True)
        self.dry_run_check.setVisible(True)
        
        # Reset progress
        self.progress_bar.setValue(0)
        self.progress_label.setText("Ready to push")
        self.progress_label.setStyleSheet("")
        
        # Clear results
        self.results_panel.clear()
        
        # Clear live log viewer
        self.live_log_viewer.clear()
        
        # Emit signal to go back to selection tab
        self.return_to_selection_requested.emit()
    
    def _add_missing_dependencies_and_revalidate(self):
        """Add missing dependencies to selection and trigger revalidation."""
        if not hasattr(self, '_pending_missing_dependencies') or not self._pending_missing_dependencies:
            return
        
        import logging
        logger = logging.getLogger(__name__)
        
        missing_deps = self._pending_missing_dependencies
        logger.normal(f"[Push] Adding {len(missing_deps)} missing dependencies and revalidating")
        
        # Log what we're adding
        for dep in missing_deps:
            logger.normal(f"[Push]   + {dep.get('type', 'unknown')}: {dep.get('name', 'unknown')} "
                         f"(required by {dep.get('required_by', 'unknown')})")
        
        # Clear the pending dependencies BEFORE emitting signal
        # This prevents re-triggering if user clicks again
        self._pending_missing_dependencies = []
        
        # Disable button while revalidation happens
        self.push_btn.setEnabled(False)
        self.push_btn.setText("Adding dependencies...")
        
        # Emit signal to request adding dependencies
        # The workflow will handle updating the selection and re-triggering validation
        # When validation completes, _finalize_validation will reset the button appropriately
        self.add_dependencies_requested.emit(missing_deps)
    
    def _validate_name_lengths(self, selected_items: dict) -> list:
        """Validate all destination names for length before API calls.

        Returns a list of error messages for names exceeding 55 characters.
        """
        MAX_NAME_LENGTH = 55
        COPY_SUFFIX = "-copy"
        errors = []

        def get_dest_name(item_data, source_name):
            """Get destination name based on strategy and user input."""
            dest = item_data.get('_destination', {})
            strategy = dest.get('strategy', 'skip')
            if strategy == 'rename':
                custom_name = dest.get('name', '')
                if custom_name and custom_name != source_name:
                    return custom_name
                return f"{source_name}{COPY_SUFFIX}"
            return source_name

        def check_item(item_type, item_data, source_name):
            """Check a single item's destination name length."""
            dest_name = get_dest_name(item_data, source_name)
            if len(dest_name) > MAX_NAME_LENGTH:
                errors.append(f"{item_type}: '{dest_name}' ({len(dest_name)} chars)")

        # Check folders
        for folder in selected_items.get('folders', []):
            folder_name = folder.get('name', '')
            # Check objects
            for obj_type, obj_list in folder.get('objects', {}).items():
                if isinstance(obj_list, list):
                    for obj in obj_list:
                        check_item(obj_type, obj, obj.get('name', ''))
            # Check profiles
            for prof_type, prof_list in folder.get('profiles', {}).items():
                if isinstance(prof_list, list):
                    for prof in prof_list:
                        check_item(prof_type, prof, prof.get('name', ''))
            # Check HIP
            for hip_type, hip_list in folder.get('hip', {}).items():
                if isinstance(hip_list, list):
                    for hip in hip_list:
                        check_item(hip_type, hip, hip.get('name', ''))
            # Check security rules
            for rule in folder.get('security_rules', []):
                check_item('security_rule', rule, rule.get('name', ''))

        # Check snippets
        for snippet in selected_items.get('snippets', []):
            snippet_name = snippet.get('name', '')
            # Check new snippet name
            dest_info = snippet.get('_destination', {})
            if dest_info.get('is_new_snippet') or dest_info.get('is_rename_snippet'):
                new_name = dest_info.get('new_snippet_name', '')
                if new_name and len(new_name) > MAX_NAME_LENGTH:
                    errors.append(f"snippet: '{new_name}' ({len(new_name)} chars)")
            # Check objects
            for obj_type, obj_list in snippet.get('objects', {}).items():
                if isinstance(obj_list, list):
                    for obj in obj_list:
                        check_item(obj_type, obj, obj.get('name', ''))
            # Check profiles
            for prof_type, prof_list in snippet.get('profiles', {}).items():
                if isinstance(prof_list, list):
                    for prof in prof_list:
                        check_item(prof_type, prof, prof.get('name', ''))
            # Check HIP
            for hip_type, hip_list in snippet.get('hip', {}).items():
                if isinstance(hip_list, list):
                    for hip in hip_list:
                        check_item(hip_type, hip, hip.get('name', ''))
            # Check security rules
            for rule in snippet.get('security_rules', []):
                check_item('security_rule', rule, rule.get('name', ''))

        # Check infrastructure
        for infra_type, infra_list in selected_items.get('infrastructure', {}).items():
            if isinstance(infra_list, list):
                for item in infra_list:
                    check_item(infra_type, item, item.get('name', item.get('id', '')))

        return errors

    # Phase 3: Receive selection from selection widget

    def set_selected_items(self, selected_items):
        """Set the selected items from selection widget."""
        import logging
        logger = logging.getLogger(__name__)

        logger.debug("[Push] set_selected_items called - resetting push state")

        # Reset all push state for new selection
        self._reset_for_new_selection()

        # Store new selection
        self.selected_items = selected_items

        # Log detailed selection info at DETAIL level
        self._log_selected_items_detail(selected_items)

        self._update_status()

    def _log_selected_items_detail(self, selected_items):
        """Log detailed info about each selected item."""
        import logging
        logger = logging.getLogger(__name__)

        if not selected_items:
            return

        logger.log(15, "[Selection] " + "=" * 80)  # 15 = DETAIL level
        logger.log(15, "[Selection] SELECTED ITEMS DETAIL")
        logger.log(15, "[Selection] " + "=" * 80)

        def get_dest_name(item_data, source_name):
            """Get destination name based on strategy and user input."""
            dest = item_data.get('_destination', {})
            strategy = dest.get('strategy', 'skip')
            if strategy == 'rename':
                # Check if user specified a custom destination name
                custom_name = dest.get('name', '')
                if custom_name and custom_name != source_name:
                    return custom_name
                # Default: append -copy suffix
                return f"{source_name}-copy"
            return source_name

        def log_item(item_type, source_name, source_location, dest_location, dest_name, strategy):
            """Log a single item's details."""
            logger.log(15, f"[Selection] {item_type:20} | Source: {source_name:40} | "
                          f"From: {source_location:25} | To: {dest_location:25} | "
                          f"Dest Name: {dest_name:40} | Strategy: {strategy}")

        # Log header
        logger.log(15, f"[Selection] {'TYPE':20} | {'SOURCE NAME':40} | "
                      f"{'SOURCE LOCATION':25} | {'DEST LOCATION':25} | "
                      f"{'DEST NAME':40} | STRATEGY")
        logger.log(15, "[Selection] " + "-" * 180)

        # Process folders
        for folder in selected_items.get('folders', []):
            folder_name = folder.get('name', '')
            dest_info = folder.get('_destination', {})
            dest_location = dest_info.get('folder', folder_name)
            if dest_info.get('is_new_snippet'):
                dest_location = dest_info.get('new_snippet_name', dest_location) + ' (NEW)'
            elif dest_info.get('is_existing_snippet'):
                dest_location = dest_location + ' (snippet)'

            # Log objects in folder
            for obj_type, obj_list in folder.get('objects', {}).items():
                if isinstance(obj_list, list):
                    for obj in obj_list:
                        name = obj.get('name', '')
                        item_dest = obj.get('_destination', {})
                        item_dest_loc = item_dest.get('folder', '') or dest_location
                        if item_dest.get('is_new_snippet'):
                            item_dest_loc = item_dest.get('new_snippet_name', item_dest_loc) + ' (NEW)'
                        elif item_dest.get('is_existing_snippet'):
                            item_dest_loc = item_dest_loc + ' (snippet)'
                        strategy = item_dest.get('strategy', dest_info.get('strategy', 'skip'))
                        dest_name = get_dest_name(obj, name)
                        log_item(obj_type, name, f"folder:{folder_name}", item_dest_loc, dest_name, strategy)

            # Log profiles in folder
            for prof_type, prof_list in folder.get('profiles', {}).items():
                if isinstance(prof_list, list):
                    for prof in prof_list:
                        name = prof.get('name', '')
                        item_dest = prof.get('_destination', {})
                        item_dest_loc = item_dest.get('folder', '') or dest_location
                        if item_dest.get('is_new_snippet'):
                            item_dest_loc = item_dest.get('new_snippet_name', item_dest_loc) + ' (NEW)'
                        elif item_dest.get('is_existing_snippet'):
                            item_dest_loc = item_dest_loc + ' (snippet)'
                        strategy = item_dest.get('strategy', dest_info.get('strategy', 'skip'))
                        dest_name = get_dest_name(prof, name)
                        log_item(prof_type, name, f"folder:{folder_name}", item_dest_loc, dest_name, strategy)

            # Log HIP in folder
            for hip_type, hip_list in folder.get('hip', {}).items():
                if isinstance(hip_list, list):
                    for hip in hip_list:
                        name = hip.get('name', '')
                        item_dest = hip.get('_destination', {})
                        item_dest_loc = item_dest.get('folder', '') or dest_location
                        if item_dest.get('is_new_snippet'):
                            item_dest_loc = item_dest.get('new_snippet_name', item_dest_loc) + ' (NEW)'
                        elif item_dest.get('is_existing_snippet'):
                            item_dest_loc = item_dest_loc + ' (snippet)'
                        strategy = item_dest.get('strategy', dest_info.get('strategy', 'skip'))
                        dest_name = get_dest_name(hip, name)
                        log_item(hip_type, name, f"folder:{folder_name}", item_dest_loc, dest_name, strategy)

            # Log security rules in folder
            for rule in folder.get('security_rules', []):
                name = rule.get('name', '')
                item_dest = rule.get('_destination', {})
                item_dest_loc = item_dest.get('folder', '') or dest_location
                if item_dest.get('is_new_snippet'):
                    item_dest_loc = item_dest.get('new_snippet_name', item_dest_loc) + ' (NEW)'
                elif item_dest.get('is_existing_snippet'):
                    item_dest_loc = item_dest_loc + ' (snippet)'
                strategy = item_dest.get('strategy', dest_info.get('strategy', 'skip'))
                dest_name = get_dest_name(rule, name)
                log_item('security_rule', name, f"folder:{folder_name}", item_dest_loc, dest_name, strategy)

        # Process snippets
        for snippet in selected_items.get('snippets', []):
            snippet_name = snippet.get('name', '')
            dest_info = snippet.get('_destination', {})
            dest_location = dest_info.get('folder', snippet_name)
            if dest_info.get('is_new_snippet'):
                dest_location = dest_info.get('new_snippet_name', dest_location) + ' (NEW)'
            elif dest_info.get('is_existing_snippet'):
                dest_location = dest_location + ' (snippet)'

            # Log objects in snippet
            for obj_type, obj_list in snippet.get('objects', {}).items():
                if isinstance(obj_list, list):
                    for obj in obj_list:
                        name = obj.get('name', '')
                        item_dest = obj.get('_destination', {})
                        item_dest_loc = item_dest.get('folder', '') or dest_location
                        if item_dest.get('is_new_snippet'):
                            item_dest_loc = item_dest.get('new_snippet_name', item_dest_loc) + ' (NEW)'
                        elif item_dest.get('is_existing_snippet'):
                            item_dest_loc = item_dest_loc + ' (snippet)'
                        strategy = item_dest.get('strategy', dest_info.get('strategy', 'skip'))
                        dest_name = get_dest_name(obj, name)
                        log_item(obj_type, name, f"snippet:{snippet_name}", item_dest_loc, dest_name, strategy)

            # Log profiles in snippet
            for prof_type, prof_list in snippet.get('profiles', {}).items():
                if isinstance(prof_list, list):
                    for prof in prof_list:
                        name = prof.get('name', '')
                        item_dest = prof.get('_destination', {})
                        item_dest_loc = item_dest.get('folder', '') or dest_location
                        if item_dest.get('is_new_snippet'):
                            item_dest_loc = item_dest.get('new_snippet_name', item_dest_loc) + ' (NEW)'
                        elif item_dest.get('is_existing_snippet'):
                            item_dest_loc = item_dest_loc + ' (snippet)'
                        strategy = item_dest.get('strategy', dest_info.get('strategy', 'skip'))
                        dest_name = get_dest_name(prof, name)
                        log_item(prof_type, name, f"snippet:{snippet_name}", item_dest_loc, dest_name, strategy)

            # Log HIP in snippet
            for hip_type, hip_list in snippet.get('hip', {}).items():
                if isinstance(hip_list, list):
                    for hip in hip_list:
                        name = hip.get('name', '')
                        item_dest = hip.get('_destination', {})
                        item_dest_loc = item_dest.get('folder', '') or dest_location
                        if item_dest.get('is_new_snippet'):
                            item_dest_loc = item_dest.get('new_snippet_name', item_dest_loc) + ' (NEW)'
                        elif item_dest.get('is_existing_snippet'):
                            item_dest_loc = item_dest_loc + ' (snippet)'
                        strategy = item_dest.get('strategy', dest_info.get('strategy', 'skip'))
                        dest_name = get_dest_name(hip, name)
                        log_item(hip_type, name, f"snippet:{snippet_name}", item_dest_loc, dest_name, strategy)

            # Log security rules in snippet
            for rule in snippet.get('security_rules', []):
                name = rule.get('name', '')
                item_dest = rule.get('_destination', {})
                item_dest_loc = item_dest.get('folder', '') or dest_location
                if item_dest.get('is_new_snippet'):
                    item_dest_loc = item_dest.get('new_snippet_name', item_dest_loc) + ' (NEW)'
                elif item_dest.get('is_existing_snippet'):
                    item_dest_loc = item_dest_loc + ' (snippet)'
                strategy = item_dest.get('strategy', dest_info.get('strategy', 'skip'))
                dest_name = get_dest_name(rule, name)
                log_item('security_rule', name, f"snippet:{snippet_name}", item_dest_loc, dest_name, strategy)

        # Process infrastructure
        for infra_type, infra_list in selected_items.get('infrastructure', {}).items():
            if isinstance(infra_list, list):
                for infra in infra_list:
                    name = infra.get('name', '')
                    item_dest = infra.get('_destination', {})
                    item_dest_loc = item_dest.get('folder', 'Shared')
                    strategy = item_dest.get('strategy', 'skip')
                    dest_name = get_dest_name(infra, name)
                    log_item(infra_type, name, "infrastructure", item_dest_loc, dest_name, strategy)

        logger.log(15, "[Selection] " + "=" * 80)
    
    def _reset_for_new_selection(self):
        """Reset push widget state for a new selection."""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.debug("[Push] Resetting push widget state")
        
        # Clear validation state
        self._destination_config = None
        self._validation_results = None
        self._pending_missing_dependencies = []
        self._pending_reference_conflicts = []
        
        # Clear push completion flag
        self.push_completed_successfully = False
        
        # Stop any running validation worker
        if hasattr(self, 'validation_worker') and self.validation_worker:
            if self.validation_worker.isRunning():
                logger.debug("[Push] Stopping running validation worker")
                self.validation_worker.quit()
                self.validation_worker.wait(1000)  # Wait up to 1 second
            self.validation_worker = None
        
        # Reset UI to initial state
        # Hide validation and results sections
        self.validation_group.setVisible(False)
        self.results_group.setVisible(False)
        
        # Show and reset progress section
        self.progress_group.setVisible(True)
        self.progress_label.setText("⏳ Ready to validate...")
        self.progress_label.setStyleSheet("")
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        
        # Reset results panel
        self.results_panel.results_text.clear()
        
        # Reset push button and return button visibility
        self.push_btn.setVisible(True)
        self.push_btn.setEnabled(False)
        self.push_btn.setText("Push Config")
        self.dry_run_check.setVisible(True)
        self.dry_run_check.setEnabled(False)
        self.dry_run_check.setChecked(False)
        self.validation_return_btn.setVisible(False)
        self.return_to_selection_btn.setVisible(False)

        # Clear validation details
        self.validation_details.clear()

        logger.debug("[Push] Push widget state reset complete")

    def _filter_items_for_push(self, selected_items: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter selected_items to only include items that need to be pushed.

        Based on validation results, excludes items that:
        - Already exist in destination AND have 'skip' strategy

        Keeps items that:
        - Don't exist in destination (will be created)
        - Exist but have 'overwrite' or 'rename' strategy

        Returns:
            Filtered copy of selected_items with only items that need action
        """
        import copy
        import logging
        logger = logging.getLogger(__name__)

        if not hasattr(self, '_validation_results') or not self._validation_results:
            logger.warning("[Push] No validation results available, returning all items")
            return selected_items

        item_details = self._validation_results.get('item_details', [])
        if not item_details:
            logger.warning("[Push] No item details in validation results, returning all items")
            return selected_items

        # Build set of items that should be SKIPPED (exists=True AND strategy=skip)
        items_to_skip = set()
        items_to_push = set()
        for item in item_details:
            key = (item.get('type', ''), item.get('name', ''))
            if item.get('exists', False) and item.get('strategy', 'skip') == 'skip':
                items_to_skip.add(key)
            else:
                items_to_push.add(key)

        logger.info(f"[Push] Filtering: {len(items_to_push)} items to push, {len(items_to_skip)} items to skip")

        # Deep copy to avoid modifying original
        filtered = copy.deepcopy(selected_items)

        def filter_item_list(items: list, item_type: str) -> list:
            """Filter a list of items, keeping only those that need action."""
            result = []
            for item in items:
                name = item.get('name', '')
                key = (item_type, name)
                if key not in items_to_skip:
                    result.append(item)
                else:
                    logger.debug(f"[Push] Filtering out {item_type}/{name} (will skip)")
            return result

        def filter_typed_dict(typed_dict: Dict[str, list]) -> Dict[str, list]:
            """Filter a dict of {type: [items]} keeping only items that need action."""
            result = {}
            for item_type, items in typed_dict.items():
                filtered_items = filter_item_list(items, item_type)
                if filtered_items:
                    result[item_type] = filtered_items
            return result

        # Filter folders
        filtered_folders = []
        for folder in filtered.get('folders', []):
            new_folder = {
                'name': folder.get('name', ''),
            }
            # Filter objects
            if 'objects' in folder:
                new_folder['objects'] = filter_typed_dict(folder['objects'])
            # Filter profiles
            if 'profiles' in folder:
                new_folder['profiles'] = filter_typed_dict(folder['profiles'])
            # Filter HIP
            if 'hip' in folder:
                new_folder['hip'] = filter_typed_dict(folder['hip'])
            # Filter security rules
            if 'security_rules' in folder:
                new_folder['security_rules'] = filter_item_list(
                    folder['security_rules'], 'security_rule'
                )
            # Filter authentication rules
            if 'authentication_rules' in folder:
                new_folder['authentication_rules'] = filter_item_list(
                    folder['authentication_rules'], 'authentication_rule'
                )
            # Filter decryption rules
            if 'decryption_rules' in folder:
                new_folder['decryption_rules'] = filter_item_list(
                    folder['decryption_rules'], 'decryption_rule'
                )
            # Only include folder if it has any items
            has_items = (
                new_folder.get('objects') or
                new_folder.get('profiles') or
                new_folder.get('hip') or
                new_folder.get('security_rules') or
                new_folder.get('authentication_rules') or
                new_folder.get('decryption_rules')
            )
            if has_items:
                filtered_folders.append(new_folder)
        filtered['folders'] = filtered_folders

        # Filter snippets (same structure as folders)
        filtered_snippets = []
        for snippet in filtered.get('snippets', []):
            new_snippet = {
                'name': snippet.get('name', ''),
            }
            if 'objects' in snippet:
                new_snippet['objects'] = filter_typed_dict(snippet['objects'])
            if 'profiles' in snippet:
                new_snippet['profiles'] = filter_typed_dict(snippet['profiles'])
            if 'hip' in snippet:
                new_snippet['hip'] = filter_typed_dict(snippet['hip'])
            if 'security_rules' in snippet:
                new_snippet['security_rules'] = filter_item_list(
                    snippet['security_rules'], 'security_rule'
                )
            if 'authentication_rules' in snippet:
                new_snippet['authentication_rules'] = filter_item_list(
                    snippet['authentication_rules'], 'authentication_rule'
                )
            if 'decryption_rules' in snippet:
                new_snippet['decryption_rules'] = filter_item_list(
                    snippet['decryption_rules'], 'decryption_rule'
                )
            has_items = (
                new_snippet.get('objects') or
                new_snippet.get('profiles') or
                new_snippet.get('hip') or
                new_snippet.get('security_rules') or
                new_snippet.get('authentication_rules') or
                new_snippet.get('decryption_rules')
            )
            if has_items:
                filtered_snippets.append(new_snippet)
        filtered['snippets'] = filtered_snippets

        # Filter infrastructure
        if 'infrastructure' in filtered:
            filtered['infrastructure'] = filter_typed_dict(filtered['infrastructure'])

        # Count filtered items
        total_filtered = 0
        for folder in filtered['folders']:
            for items in folder.get('objects', {}).values():
                total_filtered += len(items)
            for items in folder.get('profiles', {}).values():
                total_filtered += len(items)
            for items in folder.get('hip', {}).values():
                total_filtered += len(items)
            total_filtered += len(folder.get('security_rules', []))
            total_filtered += len(folder.get('authentication_rules', []))
            total_filtered += len(folder.get('decryption_rules', []))
        for snippet in filtered['snippets']:
            for items in snippet.get('objects', {}).values():
                total_filtered += len(items)
            for items in snippet.get('profiles', {}).values():
                total_filtered += len(items)
            for items in snippet.get('hip', {}).values():
                total_filtered += len(items)
            total_filtered += len(snippet.get('security_rules', []))
            total_filtered += len(snippet.get('authentication_rules', []))
            total_filtered += len(snippet.get('decryption_rules', []))
        for items in filtered.get('infrastructure', {}).values():
            total_filtered += len(items)

        logger.info(f"[Push] After filtering: {total_filtered} items to push")

        return filtered
