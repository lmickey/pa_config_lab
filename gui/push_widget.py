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
from gui.widgets import TenantSelectorWidget, ResultsPanel
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
            placeholder="Push results will appear here..."
        )
        self.results_panel.results_text.setMaximumHeight(150)
        results_layout.addWidget(self.results_panel)
        
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
            self.validation_status.setText("⚠️ Select a destination tenant to validate")
            self.validation_status.setStyleSheet("padding: 8px; color: #F57F17;")
            self.validation_details.setPlainText("Please select a destination tenant in the 'Select Components' tab.")
            return
        
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
        # Update progress section
        self.progress_label.setText("❌ Validation failed")
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
        self.validation_status.setText("❌ Validation failed")
        self.validation_status.setStyleSheet("padding: 8px; color: #c62828; background-color: #ffebee; border-radius: 4px;")
        self.validation_details.setPlainText(f"Error during validation:\n\n{error}")
        
        # Keep push disabled
        self.push_btn.setEnabled(False)
        self.dry_run_check.setEnabled(False)
    
    def _on_validation_finished(self, destination_config):
        """Handle validation completion."""
        # Update progress section to show complete
        self.progress_label.setText("✓ Validation complete")
        self.progress_label.setStyleSheet("color: #2e7d32; font-weight: bold;")
        self.progress_bar.setValue(100)
        
        # Store destination config for push
        self._destination_config = destination_config
        
        # Run comprehensive validation
        validation_results = self._validate_items(destination_config)
        
        # Store validation results for display
        self._validation_results = validation_results
        
        # Show validation details in results panel (temporarily)
        self._show_validation_details_in_results(validation_results)
        
        # After 2 seconds, hide progress/results and show validation section
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(2000, lambda: self._finalize_validation(validation_results))
    
    def _finalize_validation(self, validation_results):
        """Finalize validation UI - hide progress/results, show validation section."""
        errors = validation_results.get('errors', [])
        warnings = validation_results.get('warnings', [])
        new_items = validation_results.get('new_items', 0)
        conflicts = validation_results.get('conflicts', 0)
        total_items = validation_results.get('total_items', 0)
        missing_dependencies = validation_results.get('missing_dependencies', [])
        
        # Store missing dependencies for the "Add and Revalidate" action
        self._pending_missing_dependencies = missing_dependencies
        
        # Hide progress and results sections
        self.progress_group.setVisible(False)
        self.results_group.setVisible(False)
        
        # Show validation results section
        self.validation_group.setVisible(True)
        
        # Set summary status based on validation outcome
        if errors:
            # Hard errors - can't push
            self.validation_status.setText(
                f"❌ Validation failed - {len(errors)} error(s), {len(warnings)} warning(s)"
            )
            self.validation_status.setStyleSheet(
                "padding: 8px; color: #c62828; background-color: #ffebee; border-radius: 4px;"
            )
            self.push_btn.setEnabled(False)
            self.push_btn.setText("Push Config")
            self.dry_run_check.setEnabled(False)
        elif missing_dependencies:
            # Missing dependencies - need to add them first
            dep_count = len(missing_dependencies)
            self.validation_status.setText(
                f"⚠️ {dep_count} missing dependenc{'y' if dep_count == 1 else 'ies'} - Add required items to continue"
            )
            self.validation_status.setStyleSheet(
                "padding: 8px; color: #E65100; background-color: #FFF3E0; border-radius: 4px;"
            )
            self.push_btn.setEnabled(True)
            self.push_btn.setText("Add Dependencies and Revalidate")
            self.dry_run_check.setEnabled(False)
        elif warnings:
            self.validation_status.setText(
                f"⚠️ {total_items} items: {new_items} new, {conflicts} conflicts, {len(warnings)} warning(s)"
            )
            self.validation_status.setStyleSheet(
                "padding: 8px; color: #F57F17; background-color: #FFF9C4; border-radius: 4px;"
            )
            self.push_btn.setEnabled(True)
            self.push_btn.setText("Push Config")
            self.dry_run_check.setEnabled(True)
        elif conflicts > 0:
            self.validation_status.setText(
                f"⚠️ {total_items} items: {new_items} new, {conflicts} conflicts - Review strategies"
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
        lines = []
        
        # Header
        lines.append("=" * 100)
        lines.append("VALIDATION RESULTS - ITEM DETAILS")
        lines.append("=" * 100)
        lines.append("")
        
        # Table header - include DESTINATION column
        lines.append(f"{'TYPE':<20} {'NAME':<25} {'DESTINATION':<25} {'STATUS':<10} {'ACTION'}")
        lines.append("-" * 100)
        
        # Show each item
        for item in validation_results.get('item_details', []):
            item_type = item.get('type', 'unknown')[:18]
            item_name = item.get('name', 'unknown')[:23]
            exists = item.get('exists', False)
            strategy = item.get('strategy', 'skip')
            existing_loc = item.get('existing_location', '')
            
            # Get destination info
            dest_location = item.get('location', item.get('destination', ''))
            dest_type = item.get('dest_type', '')  # 'snippet' or 'folder'
            
            # Format destination with type indicator
            if dest_type == 'snippet':
                dest_display = f"📄 {dest_location}"[:23] if dest_location else "📄 (inherit)"
            elif dest_type == 'folder':
                dest_display = f"📁 {dest_location}"[:23] if dest_location else "📁 (inherit)"
            elif dest_location:
                dest_display = dest_location[:23]
            else:
                dest_display = "(inherit)"
            
            if exists:
                status = "EXISTS"
                # For security rules, show where the conflict is
                loc_info = f" in '{existing_loc}'" if existing_loc else ""
                if strategy == 'skip':
                    action = f"→ SKIP (exists{loc_info})"
                elif strategy == 'overwrite':
                    action = f"→ OVERWRITE{loc_info}"
                elif strategy == 'rename':
                    action = f"→ RENAME (add -copy){loc_info}"
                else:
                    action = f"→ {strategy.upper()}{loc_info}"
            else:
                status = "NEW"
                action = "→ CREATE"
            
            lines.append(f"{item_type:<20} {item_name:<25} {dest_display:<25} {status:<10} {action}")
            
            # Show existing location detail for security rules with global conflicts
            if exists and existing_loc and item_type == 'security_rule':
                lines.append(f"{'':20} ⚠️ Rule name already exists in: {existing_loc}")
            
            # Show errors/warnings for this item
            if item.get('error'):
                lines.append(f"{'':20} ❌ ERROR: {item['error']}")
            if item.get('warning'):
                lines.append(f"{'':20} ⚠️ WARNING: {item['warning']}")
            
            # Show missing dependencies
            if item.get('missing_deps'):
                deps_str = ', '.join(item['missing_deps'])
                lines.append(f"{'':20} ⚠️ Missing deps: {deps_str}")
        
        lines.append("-" * 100)
        lines.append("")
        
        # Summary section
        lines.append("SUMMARY:")
        lines.append(f"  Total Items: {validation_results['total_items']}")
        lines.append(f"  New Items: {validation_results['new_items']}")
        lines.append(f"  Conflicts: {validation_results['conflicts']}")
        
        if validation_results['errors']:
            lines.append("")
            lines.append("ERRORS (must fix before push):")
            for err in validation_results['errors']:
                lines.append(f"  ❌ {err}")
        
        if validation_results['warnings']:
            lines.append("")
            lines.append("WARNINGS:")
            for warn in validation_results['warnings']:
                lines.append(f"  ⚠️ {warn}")
        
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
        MAX_NAME_LENGTH = 55
        COPY_SUFFIX = "-copy"
        
        errors = []
        warnings = []
        item_details = []  # Per-item validation results
        new_items = 0
        conflicts = 0
        total_items = 0
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
        for folder_data in self.selected_items.get('folders', []):
            folder_name = folder_data.get('name', '')
            total_items += 1
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
                
                if snippet_exists:
                    # Snippet name conflict - this is an error/conflict
                    conflicts += 1
                    action = f"⚠️ Snippet '{new_snippet_name}' already exists!"
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
                # Check for conflicts
                dest_folders = destination_config.get('folders', {})
                exists = folder_name in dest_folders
                
                if exists:
                    conflicts += 1
                    action = f"Will {strategy}"
                else:
                    new_items += 1
                    action = "Will create"
                
                # Check name length
                err, warn = check_name_length(folder_name, 'folder', strategy)
                if err:
                    errors.append(err)
                if warn:
                    warnings.append(warn)
                
                item_details.append({
                    'type': 'folder',
                    'name': folder_name,
                    'exists': exists,
                    'strategy': strategy,
                    'action': action,
                    'error': err,
                    'warning': warn,
                })
            
            # Check objects within folder
            # If the container is going to a new snippet, all children auto-pass
            container_is_new_snippet = is_to_new_snippet and new_snippet_name
            # If going to existing snippet, need to check snippet-scoped conflicts
            container_is_existing_snippet = is_to_existing_snippet
            target_snippet_name = dest_folder if is_to_existing_snippet else new_snippet_name
            
            for obj_type, obj_list in folder_data.get('objects', {}).items():
                if not isinstance(obj_list, list):
                    continue
                dest_objects = destination_config.get('objects', {}).get(obj_type, {})
                
                for obj in obj_list:
                    obj_name = obj.get('name', '')
                    total_items += 1
                    obj_strategy = get_item_strategy(obj)
                    
                    # Determine destination and conflict check
                    if container_is_new_snippet or is_destination_new_snippet(obj):
                        # Going to NEW snippet - auto-pass (no conflicts possible)
                        exists = False
                        action = f"Will create in new snippet '{target_snippet_name}'"
                        dest_location = target_snippet_name
                    elif container_is_existing_snippet:
                        # Going to EXISTING snippet - check snippet-scoped conflicts
                        # Objects in snippets are scoped to the snippet
                        snippet_objects = destination_config.get('snippet_objects', {}).get(target_snippet_name, {}).get(obj_type, {})
                        exists = obj_name in snippet_objects
                        dest_location = target_snippet_name
                        if exists:
                            action = f"Will {obj_strategy} in snippet '{target_snippet_name}'"
                        else:
                            action = f"Will create in snippet '{target_snippet_name}'"
                    else:
                        # Regular folder destination - global object check
                        exists = obj_name in dest_objects
                        dest_location = folder_name
                    
                    if exists:
                        conflicts += 1
                        if not container_is_existing_snippet:
                            action = f"Will {obj_strategy}"
                    else:
                        new_items += 1
                        if not container_is_new_snippet and not container_is_existing_snippet:
                            action = "Will create"
                    
                    err, warn = check_name_length(obj_name, obj_type, obj_strategy)
                    if err:
                        errors.append(err)
                    if warn:
                        warnings.append(warn)
                    
                    # Check dependencies - pass container info to find deps in same container
                    obj_missing_deps = check_dependencies(obj, obj_type, obj_name, 'folder', folder_name)
                    if obj_missing_deps:
                        for dep in obj_missing_deps:
                            # Add target destination info to the dependency
                            # Dependencies should go to the SAME destination as the item requiring them
                            dep['target_destination'] = {
                                'folder': dest_location,
                                'dest_type': dest_type,
                                'is_existing_snippet': container_is_existing_snippet,
                                'is_new_snippet': container_is_new_snippet,
                            }
                            if dep not in missing_dependencies:
                                missing_dependencies.append(dep)
                        dep_names = [d['name'] for d in obj_missing_deps]
                        dep_warning = f"Missing dependencies: {', '.join(dep_names)}"
                        warnings.append(f"{obj_name}: {dep_warning}")
                    
                    # Determine destination type
                    if container_is_new_snippet or container_is_existing_snippet:
                        dest_type = 'snippet'
                    else:
                        dest_type = 'folder'
                    
                    item_details.append({
                        'type': obj_type,
                        'name': obj_name,
                        'location': dest_location,
                        'dest_type': dest_type,
                        'exists': exists,
                        'strategy': obj_strategy,
                        'action': action,
                        'error': err,
                        'warning': warn,
                        'missing_deps': [d['name'] for d in obj_missing_deps] if obj_missing_deps else None,
                    })
            
            # Check rules within folder
            # Check security rules within folder
            # IMPORTANT: Security rules must be GLOBALLY unique across the entire tenant
            # UNLESS the destination is a NEW snippet (then auto-pass)
            # OR going to an existing snippet (rules scoped to snippet)
            for rule in folder_data.get('security_rules', []):
                if not isinstance(rule, dict):
                    continue
                rule_name = rule.get('name', '')
                total_items += 1
                rule_strategy = get_item_strategy(rule)
                
                # Determine destination and conflict check
                if container_is_new_snippet or is_destination_new_snippet(rule):
                    # Going to NEW snippet - auto-pass (no conflict possible)
                    exists = False
                    existing_location = {}
                    new_items += 1
                    action = f"Will create in new snippet '{target_snippet_name}'"
                    display_location = target_snippet_name
                elif container_is_existing_snippet:
                    # Going to EXISTING snippet - check global rule uniqueness
                    # Security rules are GLOBALLY unique even in snippets
                    all_rule_names = destination_config.get('all_rule_names', {})
                    exists = rule_name in all_rule_names
                    existing_location = all_rule_names.get(rule_name, {})
                    display_location = target_snippet_name
                    
                    if exists:
                        conflicts += 1
                        conflict_loc = existing_location.get('folder') or existing_location.get('snippet') or 'unknown'
                        action = f"Will {rule_strategy} in snippet '{target_snippet_name}' (exists in {conflict_loc})"
                    else:
                        new_items += 1
                        action = f"Will create in snippet '{target_snippet_name}'"
                else:
                    # Regular folder destination - check GLOBAL uniqueness
                    all_rule_names = destination_config.get('all_rule_names', {})
                    exists = rule_name in all_rule_names
                    existing_location = all_rule_names.get(rule_name, {})
                    display_location = folder_name
                    
                    if exists:
                        conflicts += 1
                        conflict_loc = existing_location.get('folder') or existing_location.get('snippet') or 'unknown'
                        action = f"Will {rule_strategy} (exists in {conflict_loc})"
                    else:
                        new_items += 1
                        action = "Will create"
                
                err, warn = check_name_length(rule_name, 'security_rule', rule_strategy)
                if err:
                    errors.append(err)
                if warn:
                    warnings.append(warn)
                
                item_details.append({
                    'type': 'security_rule',
                    'name': rule_name,
                    'location': display_location,
                    'exists': exists,
                    'existing_location': f"{existing_location.get('folder') or existing_location.get('snippet')}" if exists else None,
                    'strategy': rule_strategy,
                    'action': action,
                    'error': err,
                    'warning': warn,
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
                    action = f"⚠️ Snippet '{new_snippet_name}' already exists!"
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
                    action = f"⚠️ Renamed snippet '{renamed_name}' already exists!"
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
                    
                    # Check item-level destination (may override container destination)
                    obj_dest_info = obj.get('_destination', {})
                    obj_dest_folder = obj_dest_info.get('folder', '') or dest_folder
                    obj_is_existing_snippet = obj_dest_info.get('is_existing_snippet', False) or is_to_existing_snippet
                    obj_is_new_snippet = obj_dest_info.get('is_new_snippet', False) or snippet_is_new
                    obj_new_snippet_name = obj_dest_info.get('new_snippet_name', '') or new_snippet_name
                    
                    # Re-check if destination is an existing snippet based on item's destination
                    if not obj_is_existing_snippet and not obj_is_new_snippet:
                        if obj_dest_folder and obj_dest_folder in existing_snippets:
                            obj_is_existing_snippet = True
                    
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
                            conflicts += 1
                            action = f"Will {obj_strategy} in snippet '{target_snippet}'"
                        else:
                            new_items += 1
                            action = f"Will create in snippet '{target_snippet}'"
                    else:
                        exists = obj_name in dest_objects
                        if exists:
                            conflicts += 1
                            action = f"Will {obj_strategy}"
                        else:
                            new_items += 1
                            action = "Will create"
                    
                    err, warn = check_name_length(obj_name, obj_type, obj_strategy)
                    if err:
                        errors.append(err)
                    if warn:
                        warnings.append(warn)
                    
                    # Check dependencies - pass container info to find deps in same snippet
                    obj_missing_deps = check_dependencies(obj, obj_type, obj_name, 'snippet', snippet_name)
                    if obj_missing_deps:
                        # Determine target destination for dependencies - use ITEM's destination, not container
                        dep_dest_location = obj_new_snippet_name if obj_is_new_snippet else obj_dest_folder if obj_dest_folder else snippet_name
                        dep_is_existing = obj_is_existing_snippet
                        dep_is_new = obj_is_new_snippet
                        
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
                        warnings.append(f"{obj_name}: {dep_warning}")
                    
                    # Determine the correct destination location to display - use ITEM's destination
                    if obj_is_new_snippet:
                        display_location = obj_new_snippet_name
                    elif obj_is_existing_snippet and obj_dest_folder:
                        display_location = obj_dest_folder
                    else:
                        display_location = snippet_name  # Keeping original location
                    
                    item_details.append({
                        'type': obj_type,
                        'name': obj_name,
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
            # IMPORTANT: Security rules must be GLOBALLY unique across the entire tenant
            # UNLESS the parent snippet is NEW (then auto-pass)
            for rule in snippet_data.get('security_rules', []):
                if not isinstance(rule, dict):
                    continue
                rule_name = rule.get('name', '')
                total_items += 1
                rule_strategy = get_item_strategy(rule)
                
                # If parent snippet is new, this rule auto-passes (no conflict possible)
                if snippet_is_new or is_destination_new_snippet(rule):
                    exists = False
                    existing_location = {}
                    new_items += 1
                    action = f"Will create in '{new_snippet_name}'"
                else:
                    # Check GLOBAL uniqueness using all_rule_names
                    all_rule_names = destination_config.get('all_rule_names', {})
                    exists = rule_name in all_rule_names
                    existing_location = all_rule_names.get(rule_name, {})
                    
                    if exists:
                        conflicts += 1
                        # Show where the conflict is
                        conflict_loc = existing_location.get('folder') or existing_location.get('snippet') or 'unknown'
                        action = f"Will {rule_strategy} (exists in {conflict_loc})"
                    else:
                        new_items += 1
                        action = "Will create"
                
                err, warn = check_name_length(rule_name, 'security_rule', rule_strategy)
                if err:
                    errors.append(err)
                if warn:
                    warnings.append(warn)
                
                item_details.append({
                    'type': 'security_rule',
                    'name': rule_name,
                    'location': new_snippet_name if snippet_is_new else snippet_name,
                    'exists': exists,
                    'existing_location': f"{existing_location.get('folder') or existing_location.get('snippet')}" if exists else None,
                    'strategy': rule_strategy,
                    'action': action,
                    'error': err,
                    'warning': warn,
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
                
                exists = item_name in dest_infra
                if exists:
                    conflicts += 1
                    action = f"Will {item_strategy}"
                else:
                    new_items += 1
                    action = "Will create"
                
                err, warn = check_name_length(item_name, infra_type, item_strategy)
                if err:
                    errors.append(err)
                if warn:
                    warnings.append(warn)
                
                item_details.append({
                    'type': infra_type,
                    'name': item_name,
                    'exists': exists,
                    'strategy': item_strategy,
                    'action': action,
                    'error': err,
                    'warning': warn,
                })
        
        return {
            'errors': errors,
            'warnings': warnings,
            'item_details': item_details,
            'new_items': new_items,
            'conflicts': conflicts,
            'total_items': total_items,
            'missing_dependencies': missing_dependencies,
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
            lines.append("❌ ERRORS (must fix before push)")
            lines.append("=" * 70)
            for err in validation_results['errors']:
                lines.append(f"  ✗ {err}")
            lines.append("")
        
        # Show warnings
        if validation_results['warnings']:
            lines.append("=" * 70)
            lines.append("⚠️ WARNINGS")
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
                lines.append(f"      ❌ {item['error']}")
            if item.get('warning'):
                lines.append(f"      ⚠️ {item['warning']}")
        
        lines.append("")
        lines.append("=" * 70)
        
        self.results_panel.set_text("\n".join(lines))
    
    def _update_status(self):
        """Update status label and enable/disable push button."""
        # Don't overwrite success message after push completes
        if self.push_completed_successfully:
            return
        
        if not self.destination_client:
            self.status_label.setText("❌ Select destination tenant in 'Select Components' tab")
            self.status_label.setStyleSheet(
                "color: orange; padding: 10px; background-color: #fff4e6;"
            )
            self.push_btn.setEnabled(False)
            self.progress_label.setText("Select destination tenant")
            self._update_summary_label()
        elif not self.config:
            self.status_label.setText("❌ No configuration loaded - Pull or load a config first")
            self.status_label.setStyleSheet(
                "color: orange; padding: 10px; background-color: #fff4e6;"
            )
            self.push_btn.setEnabled(False)
            self.progress_label.setText("Load or pull a configuration")
            self._update_summary_label()
        elif not self.selected_items:
            self.status_label.setText("❌ Go to 'Select Components' tab to choose what to push")
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
        
        # Reset cancelled flag
        self._push_cancelled = False
        
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
        
        self.worker = SelectivePushWorker(
            self.destination_client,
            self.selected_items,
            destination_config,
            resolution
        )
        self.worker.progress.connect(self._on_push_progress, Qt.ConnectionType.QueuedConnection)
        self.worker.finished.connect(self._on_push_finished, Qt.ConnectionType.QueuedConnection)
        self.worker.error.connect(self._on_error, Qt.ConnectionType.QueuedConnection)
        self.worker.start()

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
                    unique_items = set()
                    for d in all_details:
                        item_key = (d.get('type'), d.get('name'), d.get('destination'))
                        unique_items.add(item_key)
                    
                    total_unique_items = len(unique_items)
                    
                    # Categorize results by action and success
                    created_success = [d for d in all_details if d.get('action') == 'created' and d.get('success')]
                    created_failed = [d for d in all_details if d.get('action') == 'failed' and not d.get('success')]
                    updated_success = [d for d in all_details if d.get('action') == 'updated' and d.get('success')]
                    renamed_success = [d for d in all_details if d.get('action') == 'renamed' and d.get('success')]
                    skipped_items = [d for d in all_details if d.get('action') == 'skipped']
                    
                    # Build summary to APPEND to existing output
                    summary_lines = []
                    summary_lines.append("")
                    summary_lines.append("=" * 70)
                    summary_lines.append("PUSH OPERATION COMPLETE")
                    summary_lines.append("=" * 70)
                    summary_lines.append("")
                    summary_lines.append(f"Total Items: {total_unique_items}")
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
                        summary_lines.append("❌ FAILED ITEMS:")
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
                self.status_label.setText(f"❌ Push failed: {message}")
                
                self.progress_label.setText("Push failed")
                self.progress_label.setStyleSheet("color: red;")
                
                # APPEND error to existing results
                current_text = self.results_panel.results_text.toPlainText()
                error_lines = [
                    "",
                    "=" * 70,
                    "❌ PUSH OPERATION FAILED",
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
    
    def _cancel_push(self):
        """Cancel the ongoing push operation."""
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
        
        # Update UI
        self.progress_label.setText("Push cancelled by user")
        self.progress_label.setStyleSheet("color: #F57F17; font-weight: bold;")
        
        # Append cancellation message to results
        current_text = self.results_panel.results_text.toPlainText()
        cancel_lines = [
            "",
            "=" * 70,
            "⚠️ PUSH OPERATION CANCELLED",
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

    def _set_ui_enabled(self, enabled: bool):
        """Enable or disable UI controls."""
        self.dry_run_check.setEnabled(enabled)
        # Phase 3: Enable push only if we have config, destination, AND selection
        # Convert to bool to avoid passing dict to setEnabled
        should_enable = enabled and bool(self.destination_client) and bool(self.config) and bool(self.selected_items)
        self.push_btn.setEnabled(should_enable)
    
    def _return_to_selection(self):
        """Return to the selection screen to modify selection or push again."""
        # Hide progress and results
        self.progress_group.setVisible(False)
        self.results_group.setVisible(False)
        self.return_to_selection_btn.setVisible(False)
        
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
    
    # Phase 3: Receive selection from selection widget
    
    def set_selected_items(self, selected_items):
        """Set the selected items from selection widget."""
        self.selected_items = selected_items
        self._update_status()
