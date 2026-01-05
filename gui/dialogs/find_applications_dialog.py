"""
Find Custom Applications Dialog.

Allows users to manually specify custom applications by name and folder/snippet,
then validates them against the API before adding to selection.
"""

import logging
from typing import Dict, List, Any, Optional

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QWidget,
    QMessageBox,
    QAbstractItemView,
    QComboBox,
    QLineEdit,
    QGroupBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

logger = logging.getLogger(__name__)


# Default folders where applications can exist
DEFAULT_FOLDERS = [
    ('Folder: Mobile Users', 'folder', 'Mobile Users'),
    ('Folder: Mobile Users Explicit Proxy', 'folder', 'Mobile Users Explicit Proxy'),
    ('Folder: Remote Networks', 'folder', 'Remote Networks'),
    ('Folder: Shared', 'folder', 'Shared'),
]


class ApplicationLookupWorker(QThread):
    """Worker thread for looking up applications by name."""
    
    # Signals: row_index, app_data or None, error_message or None
    result = pyqtSignal(int, object, str)
    finished = pyqtSignal()
    
    def __init__(self, api_client, lookups: List[tuple]):
        """
        Initialize the worker.
        
        Args:
            api_client: PrismaAccessAPIClient instance
            lookups: List of (row_index, app_name, location_type, location_name) tuples
        """
        super().__init__()
        self.api_client = api_client
        self.lookups = lookups
        self._stop_requested = False
    
    def stop(self):
        """Request the worker to stop."""
        self._stop_requested = True
    
    def run(self):
        """Execute the lookups."""
        for row_idx, app_name, loc_type, loc_name in self.lookups:
            if self._stop_requested:
                break
            
            try:
                # Build query URL with name filter
                encoded_name = app_name.replace(' ', '%20')
                encoded_loc = loc_name.replace(' ', '%20')
                
                if loc_type == 'folder':
                    url = f"https://api.sase.paloaltonetworks.com/sse/config/v1/applications?folder={encoded_loc}&name={encoded_name}"
                else:
                    url = f"https://api.sase.paloaltonetworks.com/sse/config/v1/applications?snippet={encoded_loc}&name={encoded_name}"
                
                response = self.api_client._make_request("GET", url, item_type='application')
                
                # Handle response - could be:
                # 1. Direct app object (when querying by name)
                # 2. List in 'data' key (when listing)
                # 3. Empty response
                
                apps = []
                if isinstance(response, dict):
                    if 'data' in response:
                        # List response
                        apps = response.get('data', [])
                    elif 'name' in response:
                        # Direct app object response
                        apps = [response]
                    elif 'id' in response:
                        # Direct app object response (alternate check)
                        apps = [response]
                elif isinstance(response, list):
                    apps = response
                
                if apps:
                    # Find exact match (case-sensitive)
                    matching_app = None
                    for app in apps:
                        if app.get('name') == app_name:
                            matching_app = dict(app)  # Make a copy
                            break
                    
                    if matching_app:
                        # Use the app's actual folder from API (might differ from selected location)
                        actual_folder = matching_app.get('folder', loc_name)
                        matching_app['_folder'] = actual_folder
                        matching_app['_location_type'] = loc_type
                        matching_app['_item_type'] = 'application_object'  # From ApplicationObject class
                        # Also keep track of the originally searched location for comparison
                        matching_app['_searched_folder'] = loc_name
                        self.result.emit(row_idx, matching_app, "")
                    else:
                        self.result.emit(row_idx, None, f"No exact match (case-sensitive)")
                else:
                    self.result.emit(row_idx, None, "Application not found")
                    
            except Exception as e:
                logger.error(f"Error looking up {app_name}: {e}")
                self.result.emit(row_idx, None, str(e))
        
        self.finished.emit()


class FindApplicationsDialog(QDialog):
    """
    Dialog for manually specifying and validating custom applications.
    """
    
    # Status constants
    STATUS_PENDING = "Pending"
    STATUS_LOADED = "Loaded"
    STATUS_ERROR = "Error"
    
    def __init__(self, api_client, cache: Dict[str, Any], parent=None):
        """
        Initialize the dialog.
        
        Args:
            api_client: PrismaAccessAPIClient instance
            cache: Reference to shared applications cache dict (contains snippets info)
            parent: Parent widget
        """
        super().__init__(parent)
        self.api_client = api_client
        self.cache = cache
        self.worker = None
        
        # Store loaded application data by row
        self.app_data: Dict[int, Dict[str, Any]] = {}
        
        # Get snippets from parent widget if available
        self.snippets = []
        if parent and hasattr(parent, '_snippets_cache'):
            self.snippets = parent._snippets_cache
        
        self.setWindowTitle("Find Custom Applications")
        self.setMinimumSize(800, 500)
        self.resize(900, 550)
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("<h2>🔍 Find Custom Applications</h2>")
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "Add custom applications by name. Applications will be validated against the API."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(instructions)
        
        # === Add Application Section ===
        add_group = QGroupBox("Add Application")
        add_layout = QHBoxLayout(add_group)
        
        # Location dropdown
        add_layout.addWidget(QLabel("Location:"))
        self.location_combo = QComboBox()
        self._populate_locations()
        self.location_combo.setMinimumWidth(250)
        add_layout.addWidget(self.location_combo)
        
        # Application name input
        add_layout.addWidget(QLabel("Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Application name (case-sensitive)")
        self.name_input.returnPressed.connect(self._add_application)
        add_layout.addWidget(self.name_input, stretch=1)
        
        # Add button (green)
        self.add_btn = QPushButton("+")
        self.add_btn.setFixedWidth(40)
        self.add_btn.setToolTip("Add application to list")
        self.add_btn.clicked.connect(self._add_application)
        self.add_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; font-size: 16px; }"
            "QPushButton:hover { background-color: #45a049; }"
            "QPushButton:disabled { background-color: #cccccc; color: #666666; }"
        )
        add_layout.addWidget(self.add_btn)
        
        layout.addWidget(add_group)
        
        # Case-sensitive note
        note_label = QLabel("⚠ Application names are case-sensitive")
        note_label.setStyleSheet("color: #FF9800; font-size: 11px; margin-bottom: 5px;")
        layout.addWidget(note_label)
        
        # === Applications Table ===
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Name", "Location", "Category", "Subcategory", "Status", "Remove"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 70)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, stretch=1)
        
        # === Action Buttons Row ===
        action_layout = QHBoxLayout()
        
        action_layout.addStretch()
        
        # Pull App Config button
        self.pull_btn = QPushButton("🔄 Pull App Config")
        self.pull_btn.setToolTip("Validate and load application details from API")
        self.pull_btn.clicked.connect(self._pull_app_config)
        self.pull_btn.setEnabled(False)
        self.pull_btn.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 6px 12px; }"
            "QPushButton:hover { background-color: #1976D2; }"
            "QPushButton:disabled { background-color: #cccccc; color: #666666; }"
        )
        action_layout.addWidget(self.pull_btn)
        
        layout.addLayout(action_layout)
        
        # === Bottom Buttons ===
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("✓ Save Application Selections")
        self.save_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px 16px; }"
            "QPushButton:hover { background-color: #45a049; }"
            "QPushButton:disabled { background-color: #cccccc; color: #666666; }"
        )
        self.save_btn.clicked.connect(self._save_selections)
        self.save_btn.setEnabled(False)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
    
    def _populate_locations(self):
        """Populate the location dropdown with folders and snippets."""
        self.location_combo.clear()
        
        # Add folders
        for display, loc_type, loc_name in DEFAULT_FOLDERS:
            self.location_combo.addItem(display, (loc_type, loc_name))
        
        # Add separator if we have snippets
        if self.snippets:
            self.location_combo.insertSeparator(self.location_combo.count())
            
            # Add snippets
            for snippet in self.snippets:
                snippet_name = snippet.get('name', '')
                if snippet_name:
                    display = f"Snippet: {snippet_name}"
                    self.location_combo.addItem(display, ('snippet', snippet_name))
    
    def _add_application(self):
        """Add an application to the list."""
        name = self.name_input.text().strip()
        if not name:
            return
        
        # Get location
        loc_data = self.location_combo.currentData()
        if not loc_data:
            return
        loc_type, loc_name = loc_data
        location_display = self.location_combo.currentText()
        
        # Check for duplicates
        for row in range(self.table.rowCount()):
            existing_name = self.table.item(row, 0).text()
            existing_loc = self.table.item(row, 1).text()
            if existing_name == name and existing_loc == location_display:
                QMessageBox.warning(
                    self,
                    "Duplicate Entry",
                    f"'{name}' in '{location_display}' is already in the list."
                )
                return
        
        # Add row to table
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Name
        name_item = QTableWidgetItem(name)
        name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        name_item.setData(Qt.ItemDataRole.UserRole, {'loc_type': loc_type, 'loc_name': loc_name})
        self.table.setItem(row, 0, name_item)
        
        # Location
        loc_item = QTableWidgetItem(location_display)
        loc_item.setFlags(loc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 1, loc_item)
        
        # Category (pending)
        cat_item = QTableWidgetItem("-")
        cat_item.setFlags(cat_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 2, cat_item)
        
        # Subcategory (pending)
        subcat_item = QTableWidgetItem("-")
        subcat_item.setFlags(subcat_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 3, subcat_item)
        
        # Status
        status_item = QTableWidgetItem(self.STATUS_PENDING)
        status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        status_item.setForeground(QColor(128, 128, 128))  # Gray
        self.table.setItem(row, 4, status_item)
        
        # Remove button (red)
        remove_btn = QPushButton("−")
        remove_btn.setFixedSize(50, 25)
        remove_btn.setToolTip("Remove this application")
        remove_btn.clicked.connect(lambda checked, r=row: self._remove_row(r))
        remove_btn.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; font-weight: bold; font-size: 14px; }"
            "QPushButton:hover { background-color: #d32f2f; }"
        )
        self.table.setCellWidget(row, 5, remove_btn)
        
        # Clear input
        self.name_input.clear()
        self.name_input.setFocus()
        
        # Update button states
        self._update_button_states()
    
    def _remove_row(self, row: int):
        """Remove a specific row from the table."""
        # Find the actual row (may have shifted due to other removals)
        # We need to find the row by checking which button was clicked
        for r in range(self.table.rowCount()):
            btn = self.table.cellWidget(r, 5)
            if btn and btn == self.sender():
                row = r
                break
        
        if row >= self.table.rowCount():
            return
        
        # Remove from app_data if present
        if row in self.app_data:
            del self.app_data[row]
        
        # Remove row
        self.table.removeRow(row)
        
        # Reindex app_data (shift keys down for rows after removed)
        new_app_data = {}
        for old_row, data in self.app_data.items():
            if old_row > row:
                new_app_data[old_row - 1] = data
            else:
                new_app_data[old_row] = data
        self.app_data = new_app_data
        
        # Reconnect remove buttons with correct row indices
        self._reconnect_remove_buttons()
        
        self._update_button_states()
    
    def _reconnect_remove_buttons(self):
        """Reconnect all remove buttons after row removal."""
        for row in range(self.table.rowCount()):
            btn = self.table.cellWidget(row, 5)
            if btn:
                # Disconnect all existing connections
                try:
                    btn.clicked.disconnect()
                except TypeError:
                    pass
                # Reconnect with current row
                btn.clicked.connect(lambda checked, r=row: self._remove_row(r))
    
    def _update_button_states(self):
        """Update button enabled states based on table content."""
        has_rows = self.table.rowCount() > 0
        
        # Check if there are any pending rows
        has_pending = False
        has_loaded = False
        for row in range(self.table.rowCount()):
            status = self.table.item(row, 4).text()
            if status == self.STATUS_PENDING:
                has_pending = True
            elif status == self.STATUS_LOADED:
                has_loaded = True
        
        self.pull_btn.setEnabled(has_pending)
        self.save_btn.setEnabled(has_loaded)
    
    def _pull_app_config(self):
        """Pull application configuration from API."""
        # Gather pending lookups
        lookups = []
        for row in range(self.table.rowCount()):
            status = self.table.item(row, 4).text()
            if status == self.STATUS_PENDING:
                name = self.table.item(row, 0).text()
                loc_data = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                loc_type = loc_data['loc_type']
                loc_name = loc_data['loc_name']
                lookups.append((row, name, loc_type, loc_name))
        
        if not lookups:
            return
        
        # Disable buttons during lookup
        self.pull_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.add_btn.setEnabled(False)
        
        # Start worker
        self.worker = ApplicationLookupWorker(self.api_client, lookups)
        self.worker.result.connect(self._on_lookup_result)
        self.worker.finished.connect(self._on_lookup_finished)
        self.worker.start()
    
    def _on_lookup_result(self, row: int, app_data: Optional[Dict], error: str):
        """Handle a single lookup result."""
        if app_data:
            # Success - update row with app info
            self.app_data[row] = app_data
            
            self.table.item(row, 2).setText(app_data.get('category', '-'))
            self.table.item(row, 3).setText(app_data.get('subcategory', '-'))
            
            # Check if the app's actual folder differs from what was selected
            # If so, update the Location column to show the actual folder
            actual_folder = app_data.get('folder') or app_data.get('_folder')
            location_item = self.table.item(row, 1)
            displayed_location = location_item.text() if location_item else ''
            
            if actual_folder and actual_folder not in displayed_location:
                # Update to show actual folder (app is defined in parent folder)
                new_location = f"Folder: {actual_folder}"
                location_item.setText(new_location)
                location_item.setForeground(QColor(255, 152, 0))  # Orange to indicate change
                location_item.setToolTip(f"App found in '{actual_folder}' (originally searched in different folder)")
                
                # Update stored data with actual folder
                app_data['_folder'] = actual_folder
                app_data['_location_type'] = 'folder'
            
            status_item = self.table.item(row, 4)
            status_item.setText(self.STATUS_LOADED)
            status_item.setForeground(QColor(76, 175, 80))  # Green
            
            # Reset row background
            for col in range(5):
                item = self.table.item(row, col)
                if item:
                    item.setBackground(QColor(255, 255, 255, 0))
        else:
            # Error - highlight row red
            status_item = self.table.item(row, 4)
            status_item.setText(self.STATUS_ERROR)
            status_item.setForeground(QColor(244, 67, 54))  # Red
            status_item.setToolTip(error)
            
            # Highlight entire row
            for col in range(5):
                item = self.table.item(row, col)
                if item:
                    item.setBackground(QColor(255, 200, 200))
    
    def _on_lookup_finished(self):
        """Handle lookup completion."""
        self.worker = None
        self.add_btn.setEnabled(True)
        self._update_button_states()
    
    def _save_selections(self):
        """Save the selected applications."""
        # Check for errors
        error_rows = []
        for row in range(self.table.rowCount()):
            status = self.table.item(row, 4).text()
            if status == self.STATUS_ERROR:
                error_rows.append(row)
        
        if error_rows:
            # Prompt user about errors
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Applications with Errors")
            msg_box.setText(f"There are {len(error_rows)} application(s) with errors.")
            msg_box.setInformativeText(
                "• Skip errors: Remove error apps and continue\n"
                "• Fix errors: Return to dialog to fix issues"
            )
            
            skip_btn = msg_box.addButton("Skip Errors", QMessageBox.ButtonRole.AcceptRole)
            fix_btn = msg_box.addButton("Fix Errors", QMessageBox.ButtonRole.RejectRole)
            msg_box.setDefaultButton(fix_btn)
            
            msg_box.exec()
            
            if msg_box.clickedButton() == skip_btn:
                # Skip errors - remove error rows (from bottom up to preserve indices)
                for row in sorted(error_rows, reverse=True):
                    self.table.removeRow(row)
                    if row in self.app_data:
                        del self.app_data[row]
                
                # Reindex app_data after removals
                new_app_data = {}
                sorted_keys = sorted(self.app_data.keys())
                for new_idx, old_idx in enumerate(sorted_keys):
                    new_app_data[new_idx] = self.app_data[old_idx]
                self.app_data = new_app_data
            else:
                # Fix errors - just return without closing
                return
        
        # Check if any loaded apps remain
        if not self.app_data:
            QMessageBox.information(
                self,
                "No Applications",
                "No successfully loaded applications to save."
            )
            return
        
        self.accept()
    
    def get_selected_applications(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get selected applications grouped by folder/snippet.
        
        Returns:
            Dict mapping folder/snippet name to list of application dicts
        """
        by_location: Dict[str, List[Dict[str, Any]]] = {}
        
        for row, app_data in self.app_data.items():
            location = app_data.get('_folder', 'Unknown')
            if location not in by_location:
                by_location[location] = []
            by_location[location].append(app_data)
        
        return by_location
    
    def closeEvent(self, event):
        """Handle dialog close."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(2000)
        super().closeEvent(event)
