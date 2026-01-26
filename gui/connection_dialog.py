"""
Connection dialog for Prisma Access API authentication.

This module provides a dialog for entering Prisma Access credentials
and establishing API connections.
"""

from typing import Optional, Tuple
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QCheckBox,
    QMessageBox,
    QProgressDialog,
    QComboBox,
    QGroupBox,
    QTextEdit,
)
from PyQt6.QtCore import Qt, QSettings, QThread, pyqtSignal
from PyQt6.QtGui import QIcon


class AuthenticationWorker(QThread):
    """Background worker for API authentication."""

    finished = pyqtSignal(bool, str)  # success, message
    progress = pyqtSignal(str)  # status message

    def __init__(self, tsg_id: str, api_user: str, api_secret: str):
        """Initialize the authentication worker."""
        super().__init__()
        self.tsg_id = tsg_id
        self.api_user = api_user
        self.api_secret = api_secret
        self.api_client = None

    def run(self):
        """Run the authentication process."""
        try:
            self.progress.emit("Initializing API client...")

            from prisma.api_client import PrismaAccessAPIClient
            from PyQt6.QtCore import QSettings

            # Load API settings from application preferences
            settings = QSettings("PrismaAccess", "ConfigManager")
            timeout = settings.value("api/timeout", 60, type=int)
            rate_limit = settings.value("api/rate_limit", 100, type=int)
            cache_ttl = settings.value("api/cache_ttl", 300, type=int)

            self.progress.emit("Connecting to Prisma Access...")

            # Create API client with settings
            self.api_client = PrismaAccessAPIClient(
                tsg_id=self.tsg_id, 
                api_user=self.api_user, 
                api_secret=self.api_secret,
                rate_limit=rate_limit,
                cache_ttl=cache_ttl,
                timeout=timeout
            )

            self.progress.emit("Authenticating...")

            # Authentication happens in __init__
            # Note: api_client uses 'token' attribute, not 'access_token'
            if self.api_client.token:
                self.progress.emit("Authentication successful!")
                self.finished.emit(True, f"Connected to tenant: {self.tsg_id}")
            else:
                self.finished.emit(False, "Authentication failed: No token received")

        except Exception as e:
            self.finished.emit(False, f"Authentication error: {str(e)}")


class ConnectionDialog(QDialog):
    """Dialog for connecting to Prisma Access."""

    def __init__(self, parent=None):
        """Initialize the connection dialog."""
        super().__init__(parent)

        self.settings = QSettings("PrismaAccess", "ConfigManager")
        self.api_client = None
        self.worker = None
        self.selected_tenant = None
        self.connection_name = None  # Store tenant name or "Manual"

        self._init_ui()
        self._load_saved_tenants()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Connect to Prisma Access")
        self.setMinimumWidth(550)

        layout = QVBoxLayout(self)

        # Title
        title = QLabel("<h2>Prisma Access Connection</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Status message (hidden by default)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("padding: 10px; margin: 5px; border-radius: 5px;")
        self.status_label.hide()
        layout.addWidget(self.status_label)

        # Info
        info = QLabel(
            "Select a saved tenant or enter credentials manually."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin: 10px;")
        layout.addWidget(info)

        # Tenant selection section
        tenant_group = QGroupBox("Saved Tenants")
        tenant_layout = QVBoxLayout()
        
        tenant_select_layout = QHBoxLayout()
        
        self.tenant_combo = QComboBox()
        self.tenant_combo.addItem("-- Manual Entry --", None)
        self.tenant_combo.currentIndexChanged.connect(self._on_tenant_selected)
        tenant_select_layout.addWidget(self.tenant_combo, 1)
        
        manage_btn = QPushButton("Manage...")
        manage_btn.clicked.connect(self._manage_tenants)
        tenant_select_layout.addWidget(manage_btn)
        
        tenant_layout.addLayout(tenant_select_layout)
        tenant_group.setLayout(tenant_layout)
        layout.addWidget(tenant_group)

        # Manual entry section
        self.manual_group = QGroupBox("Credentials")
        form_layout = QFormLayout()

        self.tsg_id_input = QLineEdit()
        self.tsg_id_input.setPlaceholderText("e.g., 1234567890")
        form_layout.addRow("TSG ID:", self.tsg_id_input)

        self.api_user_input = QLineEdit()
        self.api_user_input.setPlaceholderText("API Client ID")
        form_layout.addRow("API User (Client ID):", self.api_user_input)

        self.api_secret_input = QLineEdit()
        self.api_secret_input.setPlaceholderText("API Client Secret")
        self.api_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("API Secret:", self.api_secret_input)

        self.manual_group.setLayout(form_layout)
        layout.addWidget(self.manual_group)

        # Save as new tenant checkbox (only for manual entry)
        self.save_tenant_checkbox = QCheckBox("Save as new tenant after successful connection")
        layout.addWidget(self.save_tenant_checkbox)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.connect_button = QPushButton("Connect")
        self.connect_button.setDefault(True)
        self.connect_button.clicked.connect(self._on_connect)
        button_layout.addWidget(self.connect_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

    def _show_status(self, message: str, is_error: bool = False):
        """Show status message with color."""
        if is_error:
            self.status_label.setStyleSheet(
                "background-color: #ffebee; color: #c62828; "
                "padding: 10px; margin: 5px; border-radius: 5px; border: 1px solid #ef5350;"
            )
        else:
            self.status_label.setStyleSheet(
                "background-color: #e8f5e9; color: #2e7d32; "
                "padding: 10px; margin: 5px; border-radius: 5px; border: 1px solid #66bb6a;"
            )
        self.status_label.setText(message)
        self.status_label.show()
    
    def _hide_status(self):
        """Hide status message."""
        self.status_label.hide()
    
    def _load_saved_tenants(self):
        """Load saved tenants into dropdown."""
        from config.tenant_manager import TenantManager
        
        manager = TenantManager()
        tenants = manager.list_tenants(sort_by="last_used")
        
        # Temporarily block signals to prevent triggering selection handler
        self.tenant_combo.blockSignals(True)
        
        # Clear existing items (except "Manual Entry")
        while self.tenant_combo.count() > 1:
            self.tenant_combo.removeItem(1)
        
        # Add tenants
        for tenant in tenants:
            display_name = f"{tenant['name']} ({tenant['tsg_id']})"
            self.tenant_combo.addItem(display_name, tenant)
        
        # Re-enable signals
        self.tenant_combo.blockSignals(False)
    
    def _on_tenant_selected(self, index):
        """Handle tenant selection from dropdown."""
        # Hide any previous status messages
        self._hide_status()
        
        tenant = self.tenant_combo.currentData()
        
        if tenant is None:
            # Manual entry selected
            self.tsg_id_input.clear()
            self.api_user_input.clear()
            self.api_secret_input.clear()
            self.tsg_id_input.setEnabled(True)
            self.api_user_input.setEnabled(True)
            self.api_secret_input.setEnabled(True)
            self.save_tenant_checkbox.setVisible(True)
            self.selected_tenant = None
        else:
            # Saved tenant selected - auto-fill
            self.tsg_id_input.setText(tenant['tsg_id'])
            self.api_user_input.setText(tenant['client_id'])
            self.api_secret_input.setText(tenant['client_secret'])
            self.tsg_id_input.setEnabled(False)
            self.api_user_input.setEnabled(False)
            self.api_secret_input.setEnabled(False)
            self.save_tenant_checkbox.setVisible(False)
            self.selected_tenant = tenant
    
    def _manage_tenants(self):
        """Open tenant management dialog."""
        from gui.dialogs.tenant_manager_dialog import TenantManagerDialog
        
        dialog = TenantManagerDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Refresh tenant list
            self._load_saved_tenants()
    
    def connect_with_saved_tenant(self, tenant_data: dict):
        """
        Connect to a saved tenant programmatically (without showing dialog).
        
        Args:
            tenant_data: Dictionary with at least 'name' key, or can be a string tenant name
            
        Returns:
            API client if successful, None otherwise
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            from prisma.api_client import PrismaAccessAPIClient
            from config.tenant_manager import TenantManager
            
            # Handle both dict and string inputs
            if isinstance(tenant_data, str):
                tenant_name = tenant_data
            else:
                tenant_name = tenant_data.get('name')
            
            logger.info(f"Attempting to connect to saved tenant: {tenant_name}")
            
            if not tenant_name:
                logger.error("No tenant name provided in tenant_data")
                return None
            
            # Get credentials from tenant manager
            manager = TenantManager()
            logger.info(f"Loading tenant details from TenantManager for: {tenant_name}")
            
            # Load full tenant details (including decrypted credentials)
            # Use get_tenant_by_name since we have the name, not the ID
            tenant = manager.get_tenant_by_name(tenant_name)
            if not tenant:
                logger.error(f"Tenant not found in TenantManager: {tenant_name}")
                available = [t.get('name') for t in manager.list_tenants()]
                logger.info(f"Available tenants: {available}")
                return None
            
            logger.info(f"Tenant loaded successfully: {tenant_name}")
            
            # Extract credentials
            tsg_id = tenant.get('tsg_id')
            api_user = tenant.get('client_id')
            api_secret = tenant.get('client_secret')
            
            logger.info(f"Extracted credentials - TSG ID: {tsg_id}, Client ID: {api_user[:10] if api_user else 'None'}..., Secret: {'***' if api_secret else 'None'}")
            
            if not all([tsg_id, api_user, api_secret]):
                logger.error(f"Missing credentials - TSG ID: {bool(tsg_id)}, Client ID: {bool(api_user)}, Secret: {bool(api_secret)}")
                return None
            
            # Create API client
            logger.info(f"Creating PrismaAccessAPIClient for tenant: {tenant_name}")
            api_client = PrismaAccessAPIClient(
                tsg_id=tsg_id,
                api_user=api_user,
                api_secret=api_secret
            )
            
            logger.info("API client created, checking for valid token...")
            
            # Verify connection by checking token
            if api_client.token:
                logger.info(f" Successfully connected to tenant: {tenant_name}")
                self.api_client = api_client
                self.connection_name = tenant_name
                
                # Update last used timestamp
                manager.update_last_used(tenant_name)
                logger.info(f"Updated last_used timestamp for: {tenant_name}")
                
                return api_client
            else:
                logger.error(f"Authentication failed - no token received for tenant: {tenant_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error connecting to saved tenant '{tenant_name}': {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    

    def _save_as_tenant(self, tsg_id: str, api_user: str, api_secret: str):
        """Save credentials as a new tenant."""
        try:
            from config.tenant_manager import TenantManager
            
            # Create custom dialog for name and description
            dialog = QDialog(self)
            dialog.setWindowTitle("Save Tenant")
            dialog.setMinimumWidth(400)
            
            layout = QVBoxLayout(dialog)
            
            # Instructions
            info = QLabel("Save these credentials as a new tenant:")
            info.setWordWrap(True)
            layout.addWidget(info)
            
            # Form
            form_layout = QFormLayout()
            
            name_input = QLineEdit()
            name_input.setPlaceholderText("e.g., Production, Dev, Customer POC")
            name_input.setText(f"Tenant {tsg_id}")
            form_layout.addRow("Name*:", name_input)
            
            description_input = QTextEdit()
            description_input.setPlaceholderText("Optional description or notes")
            description_input.setMaximumHeight(80)
            form_layout.addRow("Description:", description_input)
            
            layout.addLayout(form_layout)
            
            # Buttons
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(dialog.reject)
            button_layout.addWidget(cancel_btn)
            
            save_btn = QPushButton("Save")
            save_btn.clicked.connect(dialog.accept)
            save_btn.setDefault(True)
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
            
            # Show dialog
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            
            name = name_input.text().strip()
            description = description_input.toPlainText().strip()
            
            if not name:
                self._show_status("Tenant name is required", is_error=True)
                return
            
            # Save tenant
            manager = TenantManager()
            success, message, _ = manager.add_tenant(
                name=name,
                tsg_id=tsg_id,
                client_id=api_user,
                client_secret=api_secret,
                description=description,
                validate=False  # Already validated by successful connection
            )
            
            if success:
                self._show_status(f"✓ Tenant '{name}' saved successfully!")
                self._load_saved_tenants()
            else:
                self._show_status(f"Failed to save tenant: {message}", is_error=True)
                
        except Exception as e:
            self._show_status(f"Error saving tenant: {str(e)}", is_error=True)
            import traceback
            traceback.print_exc()

    def _on_connect(self):
        """Handle connect button click."""
        try:
            # Validate inputs
            tsg_id = self.tsg_id_input.text().strip()
            api_user = self.api_user_input.text().strip()
            api_secret = self.api_secret_input.text().strip()

            if not tsg_id:
                QMessageBox.warning(self, "Missing Information", "Please enter TSG ID.")
                self.tsg_id_input.setFocus()
                return

            if not api_user:
                QMessageBox.warning(
                    self, "Missing Information", "Please enter API User (Client ID)."
                )
                self.api_user_input.setFocus()
                return

            if not api_secret:
                QMessageBox.warning(self, "Missing Information", "Please enter API Secret.")
                self.api_secret_input.setFocus()
                return

            # Disable UI during connection
            self.connect_button.setEnabled(False)
            self.tsg_id_input.setEnabled(False)
            self.api_user_input.setEnabled(False)
            self.api_secret_input.setEnabled(False)

            # Create progress dialog
            self.progress_dialog = QProgressDialog(
                "Connecting to Prisma Access...", None, 0, 0, self
            )
            self.progress_dialog.setWindowTitle("Connecting")
            self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            self.progress_dialog.setMinimumDuration(0)
            self.progress_dialog.setCancelButton(None)
            self.progress_dialog.show()

            # Start authentication in background
            self.worker = AuthenticationWorker(tsg_id, api_user, api_secret)
            self.worker.progress.connect(self._on_progress, Qt.ConnectionType.QueuedConnection)
            self.worker.finished.connect(self._on_authentication_finished, Qt.ConnectionType.QueuedConnection)
            self.worker.start()
            
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Connection Error", 
                f"An error occurred while connecting:\n\n{str(e)}\n\nPlease check the console for details."
            )
            import traceback
            traceback.print_exc()
            # Re-enable UI
            self.connect_button.setEnabled(True)
            if self.selected_tenant is None:
                self.tsg_id_input.setEnabled(True)
                self.api_user_input.setEnabled(True)
                self.api_secret_input.setEnabled(True)

    def _on_progress(self, message: str):
        """Handle progress updates."""
        if hasattr(self, "progress_dialog"):
            self.progress_dialog.setLabelText(message)

    def _on_authentication_finished(self, success: bool, message: str):
        """Handle authentication completion."""
        # Close progress dialog
        if hasattr(self, "progress_dialog"):
            self.progress_dialog.close()
            delattr(self, "progress_dialog")

        # Re-enable UI
        self.connect_button.setEnabled(True)
        # Only re-enable inputs if manual entry
        if self.selected_tenant is None:
            self.tsg_id_input.setEnabled(True)
            self.api_user_input.setEnabled(True)
            self.api_secret_input.setEnabled(True)

        if success:
            # Store API client
            self.api_client = self.worker.api_client

            # Set connection name based on source
            if self.selected_tenant:
                # Saved tenant - use tenant name
                self.connection_name = self.selected_tenant['name']
                
                # Mark tenant as used
                from config.tenant_manager import TenantManager
                manager = TenantManager()
                manager.mark_used(self.selected_tenant['id'])
            else:
                # Manual entry
                self.connection_name = "Manual"
            
            # Save as new tenant if requested (manual entry only)
            if self.selected_tenant is None and self.save_tenant_checkbox.isChecked():
                self._save_as_tenant(
                    self.tsg_id_input.text().strip(),
                    self.api_user_input.text().strip(),
                    self.api_secret_input.text().strip()
                )
            else:
                # Show success message
                self._show_status(f"✓ {message}")

            # Close dialog after brief delay to show success message
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1500, self.accept)
        else:
            self._show_status(f"✗ {message}", is_error=True)

    def get_api_client(self):
        """Get the authenticated API client."""
        return self.api_client
    
    def get_connection_name(self):
        """Get the connection name (tenant name or 'Manual')."""
        return self.connection_name
