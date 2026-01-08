"""
Tenant Manager Dialog - Manage saved tenant credentials.

This dialog allows users to add, edit, delete, and manage saved tenants.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QTextEdit,
    QMessageBox, QInputDialog, QGroupBox, QFormLayout, QCheckBox,
    QProgressDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from config.tenant_manager import TenantManager


class TenantManagerDialog(QDialog):
    """Dialog for managing saved tenants."""
    
    # Signal emitted when a tenant is selected for connection
    tenant_selected = pyqtSignal(dict)  # tenant data
    
    def __init__(self, parent=None):
        """Initialize the tenant manager dialog."""
        super().__init__(parent)
        
        self.manager = TenantManager()
        self.current_tenant = None
        
        self._init_ui()
        self._refresh_list()
    
    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Tenant Management")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("<h2>Saved Tenants</h2>")
        layout.addWidget(title)
        
        # Info
        info = QLabel(
            "Manage your saved Prisma Access tenants. Client secrets are never stored."
        )
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Search and actions
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search tenants...")
        self.search_input.textChanged.connect(self._on_search)
        search_layout.addWidget(self.search_input)
        
        add_btn = QPushButton("➕ Add New Tenant")
        add_btn.clicked.connect(self._add_tenant)
        add_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #4CAF50; color: white; padding: 8px; font-weight: bold; "
            "  border-radius: 5px; border: 1px solid #388E3C; border-bottom: 3px solid #2E7D32; "
            "}"
            "QPushButton:hover { background-color: #45a049; border-bottom: 3px solid #1B5E20; }"
            "QPushButton:pressed { background-color: #388E3C; border-bottom: 1px solid #2E7D32; }"
        )
        search_layout.addWidget(add_btn)
        
        layout.addLayout(search_layout)
        
        # Tenant list
        list_group = QGroupBox("Tenants")
        list_layout = QVBoxLayout()
        
        self.tenant_list = QListWidget()
        self.tenant_list.itemClicked.connect(self._on_tenant_selected)
        self.tenant_list.itemDoubleClicked.connect(self._on_tenant_double_clicked)
        list_layout.addWidget(self.tenant_list)
        
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        # Details panel
        details_group = QGroupBox("Tenant Details")
        details_layout = QVBoxLayout()
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(150)
        self.details_text.setPlaceholderText("Select a tenant to view details...")
        font = QFont("Courier New", 10)
        self.details_text.setFont(font)
        details_layout.addWidget(self.details_text)
        
        # Action buttons for selected tenant
        action_layout = QHBoxLayout()
        
        self.edit_btn = QPushButton("✏️ Edit")
        self.edit_btn.clicked.connect(self._edit_tenant)
        self.edit_btn.setEnabled(False)
        action_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("🗑️ Delete")
        self.delete_btn.clicked.connect(self._delete_tenant)
        self.delete_btn.setEnabled(False)
        self.delete_btn.setStyleSheet("QPushButton { color: #d32f2f; }")
        action_layout.addWidget(self.delete_btn)
        
        self.use_btn = QPushButton("🔗 Use for Connection")
        self.use_btn.clicked.connect(self._use_tenant)
        self.use_btn.setEnabled(False)
        self.use_btn.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; padding: 8px; }"
            "QPushButton:hover { background-color: #1976D2; }"
        )
        action_layout.addWidget(self.use_btn)
        
        action_layout.addStretch()
        
        details_layout.addLayout(action_layout)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _refresh_list(self, search_query: str = ""):
        """Refresh the tenant list."""
        self.tenant_list.clear()
        self.current_tenant = None
        self.details_text.clear()
        self._update_button_states()
        
        # Get tenants
        if search_query:
            tenants = self.manager.search_tenants(search_query)
        else:
            tenants = self.manager.list_tenants(sort_by="name")
        
        # Populate list
        for tenant in tenants:
            item = QListWidgetItem()
            
            # Format display
            name = tenant["name"]
            tsg = tenant["tsg_id"]
            last_used = tenant.get("last_used")
            
            if last_used:
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(last_used)
                    time_ago = self._format_time_ago(dt)
                    display = f"{name}\n  TSG: {tsg} | Last used: {time_ago}"
                except:
                    display = f"{name}\n  TSG: {tsg}"
            else:
                display = f"{name}\n  TSG: {tsg} | Never used"
            
            item.setText(display)
            item.setData(Qt.ItemDataRole.UserRole, tenant)
            
            self.tenant_list.addItem(item)
        
        # Show count
        if not tenants:
            if search_query:
                self.details_text.setPlainText("No tenants found matching your search.")
            else:
                self.details_text.setPlainText("No tenants saved. Click 'Add New Tenant' to get started.")
    
    def _format_time_ago(self, dt):
        """Format datetime as 'time ago' string."""
        from datetime import datetime, timedelta
        
        now = datetime.now()
        diff = now - dt
        
        if diff < timedelta(minutes=1):
            return "just now"
        elif diff < timedelta(hours=1):
            mins = int(diff.total_seconds() / 60)
            return f"{mins} minute{'s' if mins != 1 else ''} ago"
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff < timedelta(days=30):
            days = diff.days
            return f"{days} day{'s' if days != 1 else ''} ago"
        else:
            return dt.strftime("%Y-%m-%d")
    
    def _on_search(self, text: str):
        """Handle search text change."""
        self._refresh_list(text)
    
    def _on_tenant_selected(self, item: QListWidgetItem):
        """Handle tenant selection."""
        tenant = item.data(Qt.ItemDataRole.UserRole)
        self.current_tenant = tenant
        
        # Show details (hide secret)
        details = f"Name: {tenant['name']}\n"
        details += f"TSG ID: {tenant['tsg_id']}\n"
        details += f"Client ID: {tenant['client_id']}\n"
        details += f"Client Secret: {'*' * 32} (stored encrypted)\n"
        details += f"Description: {tenant.get('description', '(none)')}\n"
        details += f"\nCreated: {tenant.get('created', 'Unknown')}\n"
        details += f"Last Used: {tenant.get('last_used', 'Never')}"
        
        self.details_text.setPlainText(details)
        
        self._update_button_states()
    
    def _on_tenant_double_clicked(self, item: QListWidgetItem):
        """Handle double-click - use tenant for connection."""
        self._use_tenant()
    
    def _update_button_states(self):
        """Update button enabled states."""
        has_selection = self.current_tenant is not None
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
        self.use_btn.setEnabled(has_selection)
    
    def _add_tenant(self):
        """Add a new tenant."""
        dialog = TenantEditDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            
            # Credentials already validated in dialog, skip re-validation
            success, message, _ = self.manager.add_tenant(
                name=data["name"],
                tsg_id=data["tsg_id"],
                client_id=data["client_id"],
                client_secret=data["client_secret"],
                description=data["description"],
                validate=False  # Already validated in dialog
            )
            
            if success:
                self._refresh_list()
            else:
                QMessageBox.warning(self, "Add Failed", message)
    
    def _edit_tenant(self):
        """Edit the selected tenant."""
        if not self.current_tenant:
            return
        
        dialog = TenantEditDialog(self, tenant=self.current_tenant)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            
            # Credentials already validated in dialog, skip re-validation
            success, message = self.manager.update_tenant(
                tenant_id=self.current_tenant["id"],
                name=data["name"],
                tsg_id=data["tsg_id"],
                client_id=data["client_id"],
                client_secret=data["client_secret"],
                description=data["description"],
                validate=False  # Already validated in dialog
            )
            
            if success:
                self._refresh_list()
            else:
                QMessageBox.warning(self, "Update Failed", message)
    
    def _delete_tenant(self):
        """Delete the selected tenant."""
        if not self.current_tenant:
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete tenant '{self.current_tenant['name']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success, message = self.manager.delete_tenant(self.current_tenant["id"])
            
            if success:
                self._refresh_list()
            else:
                QMessageBox.warning(self, "Delete Failed", message)
    
    def _use_tenant(self):
        """Use the selected tenant for connection."""
        if not self.current_tenant:
            return
        
        # Mark as used
        self.manager.mark_used(self.current_tenant["id"])
        
        # Emit signal
        self.tenant_selected.emit(self.current_tenant)
        
        # Close dialog
        self.accept()
    
    def get_selected_tenant(self) -> Optional[dict]:
        """Get the currently selected tenant."""
        return self.current_tenant


class TenantEditDialog(QDialog):
    """Dialog for adding/editing a tenant."""
    
    def __init__(self, parent=None, tenant: Optional[dict] = None):
        """
        Initialize the edit dialog.
        
        Args:
            parent: Parent widget
            tenant: Existing tenant data (None for new tenant)
        """
        super().__init__(parent)
        
        self.tenant = tenant
        self.is_edit = tenant is not None
        
        self._init_ui()
        
        if tenant:
            self._load_tenant_data()
    
    def _init_ui(self):
        """Initialize the user interface."""
        title = "Edit Tenant" if self.is_edit else "Add New Tenant"
        self.setWindowTitle(title)
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        
        # Form
        form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Production, Dev, Customer POC")
        form_layout.addRow("Name*:", self.name_input)
        
        self.tsg_input = QLineEdit()
        self.tsg_input.setPlaceholderText("10-digit TSG ID")
        form_layout.addRow("TSG ID*:", self.tsg_input)
        
        self.client_id_input = QLineEdit()
        self.client_id_input.setPlaceholderText("sa-xxxxx@...iam.panserviceaccount.com")
        form_layout.addRow("Client ID*:", self.client_id_input)
        
        self.client_secret_input = QLineEdit()
        self.client_secret_input.setPlaceholderText("Enter client secret")
        self.client_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("Client Secret*:", self.client_secret_input)
        
        # Show/hide password checkbox
        self.show_secret_check = QCheckBox("Show secret")
        self.show_secret_check.stateChanged.connect(self._toggle_secret_visibility)
        form_layout.addRow("", self.show_secret_check)
        
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Optional description or notes")
        self.description_input.setMaximumHeight(80)
        form_layout.addRow("Description:", self.description_input)
        
        layout.addLayout(form_layout)
        
        # Note
        note = QLabel("* Required fields\n\nNote: Credentials will be validated before saving. Client secret is stored encrypted.")
        note.setStyleSheet("color: gray; font-size: 10px;")
        note.setWordWrap(True)
        layout.addWidget(note)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        save_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #4CAF50; color: white; padding: 8px; "
            "  border-radius: 5px; border: 1px solid #388E3C; border-bottom: 3px solid #2E7D32; "
            "}"
            "QPushButton:hover { background-color: #45a049; border-bottom: 3px solid #1B5E20; }"
            "QPushButton:pressed { background-color: #388E3C; border-bottom: 1px solid #2E7D32; }"
        )
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    def _toggle_secret_visibility(self, state):
        """Toggle client secret visibility."""
        if state == Qt.CheckState.Checked.value:
            self.client_secret_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.client_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
    
    def _load_tenant_data(self):
        """Load existing tenant data into form."""
        if not self.tenant:
            return
        
        self.name_input.setText(self.tenant.get("name", ""))
        self.tsg_input.setText(self.tenant.get("tsg_id", ""))
        self.client_id_input.setText(self.tenant.get("client_id", ""))
        # Pre-fill with existing secret (user can change or leave as-is)
        self.client_secret_input.setText(self.tenant.get("client_secret", ""))
        self.description_input.setPlainText(self.tenant.get("description", ""))
    
    def _save(self):
        """Validate and save."""
        name = self.name_input.text().strip()
        tsg_id = self.tsg_input.text().strip()
        client_id = self.client_id_input.text().strip()
        client_secret = self.client_secret_input.text().strip()
        
        # Validate
        if not name:
            QMessageBox.warning(self, "Validation Error", "Name is required.")
            self.name_input.setFocus()
            return
        
        if not tsg_id:
            QMessageBox.warning(self, "Validation Error", "TSG ID is required.")
            self.tsg_input.setFocus()
            return
        
        if not client_id:
            QMessageBox.warning(self, "Validation Error", "Client ID is required.")
            self.client_id_input.setFocus()
            return
        
        if not client_secret:
            QMessageBox.warning(self, "Validation Error", "Client secret is required.")
            self.client_secret_input.setFocus()
            return
        
        # Test credentials before saving
        progress = QProgressDialog("Validating credentials...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()
        
        from config.tenant_manager import TenantManager
        manager = TenantManager()
        
        valid, message = manager.validate_credentials(tsg_id, client_id, client_secret)
        
        progress.close()
        
        if not valid:
            QMessageBox.critical(
                self,
                "Credential Validation Failed",
                f"Unable to authenticate with provided credentials:\n\n{message}\n\n"
                "Please verify your TSG ID, Client ID, and Client Secret are correct."
            )
            return
        
        # Accept
        self.accept()
    
    def get_data(self) -> dict:
        """Get the form data."""
        return {
            "name": self.name_input.text().strip(),
            "tsg_id": self.tsg_input.text().strip(),
            "client_id": self.client_id_input.text().strip(),
            "client_secret": self.client_secret_input.text().strip(),
            "description": self.description_input.toPlainText().strip()
        }
