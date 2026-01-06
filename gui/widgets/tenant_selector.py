"""
Reusable tenant selector widget.

Provides a consistent UI for selecting and connecting to saved tenants,
with status display and connection management.
"""

from typing import Optional, Callable
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QComboBox,
    QPushButton,
    QLabel,
)
from PyQt6.QtCore import Qt, pyqtSignal, QCoreApplication
from PyQt6.QtWidgets import QProgressDialog

import logging


class TenantSelectorWidget(QWidget):
    """
    Reusable widget for tenant selection and connection.
    
    Provides:
    - Dropdown for saved tenants
    - "Connect to Tenant..." button for manual entry
    - Connection status display
    - Automatic connection to selected tenant
    
    Signals:
        connection_changed: Emitted when connection state changes (api_client, tenant_name)
    """
    
    connection_changed = pyqtSignal(object, str)  # (api_client, tenant_name)
    
    def __init__(
        self,
        parent=None,
        title: str = "Tenant",
        label: str = "Select:",
        show_success_toast: Optional[Callable] = None,
        show_error_banner: Optional[Callable] = None
    ):
        """
        Initialize the tenant selector widget.
        
        Args:
            parent: Parent widget
            title: Title for the group box (e.g., "Source Tenant", "Destination Tenant")
            label: Label for the dropdown (e.g., "Pull from:", "Push to:")
            show_success_toast: Optional callback for showing success toasts (message, duration)
            show_error_banner: Optional callback for showing error messages (message)
        """
        super().__init__(parent)
        
        self.logger = logging.getLogger(__name__)
        self.api_client = None
        self.connection_name = None
        self.show_success_toast = show_success_toast
        self.show_error_banner = show_error_banner
        
        self._title = title
        self._label = label
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Group box
        self.group_box = QGroupBox(self._title)
        group_layout = QVBoxLayout()
        
        # Tenant selection row
        select_layout = QHBoxLayout()
        select_layout.addWidget(QLabel(self._label))
        
        self.tenant_combo = QComboBox()
        self.tenant_combo.addItem("-- Select Tenant --", None)
        self.tenant_combo.currentIndexChanged.connect(self._on_tenant_selected)
        select_layout.addWidget(self.tenant_combo, 1)
        
        self.connect_btn = QPushButton("Connect to Tenant...")
        self.connect_btn.clicked.connect(self._connect_manual)
        select_layout.addWidget(self.connect_btn)
        
        group_layout.addLayout(select_layout)
        
        # Connection status
        self.status_label = QLabel("No tenant connected")
        self.status_label.setStyleSheet("color: gray; padding: 8px; margin-top: 5px;")
        group_layout.addWidget(self.status_label)
        
        self.group_box.setLayout(group_layout)
        layout.addWidget(self.group_box)
    
    def populate_tenants(self, tenants: list):
        """
        Populate the dropdown with saved tenants.
        
        Args:
            tenants: List of tenant dictionaries with 'name' key
        """
        # Clear existing items except placeholder
        self.tenant_combo.clear()
        self.tenant_combo.addItem("-- Select Tenant --", None)
        
        # Add saved tenants
        for tenant in tenants:
            tenant_name = tenant.get('name', 'Unknown')
            self.tenant_combo.addItem(tenant_name, tenant)
        
        self.logger.detail(f"Populated tenant selector with {len(tenants)} tenant(s)")
    
    def _on_tenant_selected(self, index):
        """Handle tenant selection from dropdown."""
        try:
            data = self.tenant_combo.currentData()
            
            if data is None:
                # Placeholder selected - clear connection
                self._clear_connection()
                return
            
            # Connect to selected tenant
            tenant_name = data.get('name', 'Unknown')
            self.logger.info(f"Tenant selected from dropdown: {tenant_name}")
            self._connect_to_saved_tenant(tenant_name)
            
        except Exception as e:
            self.logger.error(f"Error selecting tenant: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            
            if self.show_error_banner:
                self.show_error_banner(f"Selection Error: Failed to select tenant: {str(e)}")
    
    def _connect_to_saved_tenant(self, tenant_name: str):
        """
        Connect to a saved tenant by name.
        
        Args:
            tenant_name: Name of the saved tenant
        """
        from gui.connection_dialog import ConnectionDialog
        from config.tenant_manager import TenantManager
        from prisma.api_client import PrismaAccessAPIClient
        
        self.logger.info(f"Attempting to connect to saved tenant: {tenant_name}")
        
        try:
            # Show progress
            progress = QProgressDialog("Connecting to tenant...", None, 0, 0, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            
            try:
                progress.show()
                QCoreApplication.processEvents()
                
                # Load tenant credentials
                manager = TenantManager()
                tenant = manager.get_tenant_by_name(tenant_name)
                
                if not tenant:
                    self.logger.error(f"Tenant not found: {tenant_name}")
                    available = [t.get('name') for t in manager.list_tenants()]
                    self.logger.info(f"Available tenants: {available}")
                    
                    if self.show_error_banner:
                        self.show_error_banner(f"Connection Failed: Tenant '{tenant_name}' not found.")
                    
                    self.tenant_combo.setCurrentIndex(0)
                    return
                
                self.logger.detail(f"Tenant loaded: {tenant_name}")
                
                # Extract credentials
                tsg_id = tenant.get('tsg_id')
                api_user = tenant.get('client_id')
                api_secret = tenant.get('client_secret')
                
                if not all([tsg_id, api_user, api_secret]):
                    self.logger.error(f"Missing credentials for tenant: {tenant_name}")
                    
                    if self.show_error_banner:
                        self.show_error_banner(f"Connection Failed: Incomplete credentials for '{tenant_name}'.")
                    
                    self.tenant_combo.setCurrentIndex(0)
                    return
                
                self.logger.info(f"Creating API client for: {tenant_name}")
                
                # Load API settings from application preferences
                from PyQt6.QtCore import QSettings
                settings = QSettings("PrismaAccess", "ConfigManager")
                timeout = settings.value("api/timeout", 60, type=int)
                rate_limit = settings.value("api/rate_limit", 100, type=int)
                cache_ttl = settings.value("api/cache_ttl", 300, type=int)
                
                # Create API client with settings
                api_client = PrismaAccessAPIClient(
                    tsg_id=tsg_id,
                    api_user=api_user,
                    api_secret=api_secret,
                    rate_limit=rate_limit,
                    cache_ttl=cache_ttl,
                    timeout=timeout
                )
                
                # Verify connection
                if api_client.token:
                    self.logger.normal(f"✓ Successfully connected to: {tenant_name}")
                    
                    # Update last used timestamp
                    manager.mark_used(tenant.get('id'))
                    
                    # Set connection
                    self.set_connection(api_client, tenant_name)
                    
                    # Show success
                    if self.show_success_toast:
                        self.show_success_toast(f"✓ Connected to {tenant_name}", 2000)
                else:
                    self.logger.error(f"Authentication failed for: {tenant_name}")
                    
                    if self.show_error_banner:
                        self.show_error_banner(f"Connection Failed: Authentication failed for '{tenant_name}'. Check credentials.")
                    
                    self.tenant_combo.setCurrentIndex(0)
                    
            finally:
                if progress:
                    progress.close()
                    progress.deleteLater()
                    
        except Exception as e:
            self.logger.error(f"Exception connecting to tenant '{tenant_name}': {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            
            if self.show_error_banner:
                self.show_error_banner(f"Connection Error: {str(e)}")
            
            self.tenant_combo.setCurrentIndex(0)
    
    def _connect_manual(self):
        """Open connection dialog for manual tenant entry."""
        from gui.connection_dialog import ConnectionDialog
        
        try:
            self.logger.detail("Opening manual connection dialog")
            
            dialog = ConnectionDialog(self)
            result = dialog.exec()
            
            QCoreApplication.processEvents()
            
            if result and dialog.api_client:
                # Get tenant name
                tenant_name = dialog.connection_name if hasattr(dialog, 'connection_name') else "Manual Connection"
                
                self.logger.normal(f"✓ Manual connection successful: {tenant_name}")
                
                # Set connection
                self.set_connection(dialog.api_client, tenant_name)
                
                # Show success
                if self.show_success_toast:
                    self.show_success_toast(f"✓ Connected to {tenant_name}", 2000)
                
                # Update combo if this is a saved tenant
                found = False
                for i in range(self.tenant_combo.count()):
                    if self.tenant_combo.itemText(i) == tenant_name:
                        self.tenant_combo.setCurrentIndex(i)
                        found = True
                        break
                
                if not found and tenant_name != "Manual Connection":
                    # Add to combo
                    self.tenant_combo.addItem(tenant_name, {"name": tenant_name})
                    self.tenant_combo.setCurrentIndex(self.tenant_combo.count() - 1)
            else:
                self.logger.warning("Manual connection cancelled or failed")
                
        except Exception as e:
            self.logger.error(f"Error opening connection dialog: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            
            if self.show_error_banner:
                self.show_error_banner(f"Connection Error: {str(e)}")
    
    def set_connection(self, api_client, tenant_name: str):
        """
        Set the current connection.
        
        Args:
            api_client: PrismaAccessAPIClient instance or None
            tenant_name: Name of the connected tenant
        """
        self.api_client = api_client
        self.connection_name = tenant_name
        
        if api_client:
            # Update status - connected
            self.status_label.setText(f"✓ Connected to {tenant_name}")
            self.status_label.setStyleSheet(
                "color: green; padding: 8px; margin-top: 5px; font-weight: bold;"
            )
            self.logger.detail(f"Connection set: {tenant_name}")
        else:
            # Update status - disconnected
            self.status_label.setText("No tenant connected")
            self.status_label.setStyleSheet("color: gray; padding: 8px; margin-top: 5px;")
            self.logger.detail("Connection cleared")
        
        # Emit signal
        self.connection_changed.emit(api_client, tenant_name or "")
    
    def _clear_connection(self):
        """Clear the current connection."""
        self.set_connection(None, "")
    
    def get_connection(self):
        """
        Get the current connection.
        
        Returns:
            Tuple of (api_client, tenant_name)
        """
        return (self.api_client, self.connection_name)
    
    def reset(self):
        """Reset the selector to default state."""
        self.tenant_combo.setCurrentIndex(0)
        self._clear_connection()
