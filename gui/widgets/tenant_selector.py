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
from PyQt6.QtCore import Qt, pyqtSignal, QCoreApplication, QThread, QTimer

import logging


class TenantConnectionWorker(QThread):
    """Background worker for tenant connection."""
    
    # Signals
    connected = pyqtSignal(object, str)  # (api_client, tenant_name)
    failed = pyqtSignal(str, str)  # (tenant_name, error_message)
    
    def __init__(self, tenant_name: str, tenant_data: dict, timeout: int = 60, 
                 rate_limit: int = 100, cache_ttl: int = 300):
        super().__init__()
        self.tenant_name = tenant_name
        self.tenant_data = tenant_data
        self.timeout = timeout
        self.rate_limit = rate_limit
        self.cache_ttl = cache_ttl
        self.logger = logging.getLogger(__name__)
    
    def run(self):
        """Connect to tenant in background."""
        try:
            from prisma.api_client import PrismaAccessAPIClient
            
            tsg_id = self.tenant_data.get('tsg_id')
            api_user = self.tenant_data.get('client_id')
            api_secret = self.tenant_data.get('client_secret')
            
            if not all([tsg_id, api_user, api_secret]):
                self.failed.emit(self.tenant_name, "Incomplete credentials")
                return
            
            # Create API client
            api_client = PrismaAccessAPIClient(
                tsg_id=tsg_id,
                api_user=api_user,
                api_secret=api_secret,
                rate_limit=self.rate_limit,
                cache_ttl=self.cache_ttl,
                timeout=self.timeout
            )
            
            # Verify connection
            if api_client.token:
                self.connected.emit(api_client, self.tenant_name)
            else:
                self.failed.emit(self.tenant_name, "Authentication failed")
                
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            self.failed.emit(self.tenant_name, str(e))


class TenantSelectorWidget(QWidget):
    """
    Reusable widget for tenant selection and connection.
    
    Provides:
    - Dropdown for saved tenants
    - "Connect to Tenant..." button for manual entry
    - Optional "Load from File" button
    - Connection status display
    - Automatic connection to selected tenant
    
    Signals:
        connection_changed: Emitted when connection state changes (api_client, tenant_name)
        load_file_requested: Emitted when "Load from File" button is clicked
    """
    
    connection_changed = pyqtSignal(object, str)  # (api_client, tenant_name)
    load_file_requested = pyqtSignal()  # Emitted when load from file button clicked
    
    def __init__(
        self,
        parent=None,
        title: str = "Tenant",
        label: str = "Select:",
        show_success_toast: Optional[Callable] = None,
        show_error_banner: Optional[Callable] = None,
        show_load_button: bool = False
    ):
        """
        Initialize the tenant selector widget.
        
        Args:
            parent: Parent widget
            title: Title for the group box (e.g., "Source Tenant", "Destination Tenant")
            label: Label for the dropdown (e.g., "Pull from:", "Push to:")
            show_success_toast: Optional callback for showing success toasts (message, duration)
            show_error_banner: Optional callback for showing error messages (message)
            show_load_button: Whether to show "Load from File" button (default False)
        """
        super().__init__(parent)
        
        self.logger = logging.getLogger(__name__)
        self.api_client = None
        self.connection_name = None
        self.show_success_toast = show_success_toast
        self.show_error_banner = show_error_banner
        self._show_load_button = show_load_button
        
        self._title = title
        self._label = label
        
        # Connection worker
        self._connection_worker = None
        
        # Animated status timer
        self._status_animation_timer = QTimer(self)
        self._status_animation_timer.timeout.connect(self._animate_status)
        self._status_dot_count = 0
        self._connecting_tenant_name = ""
        
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
        self.connect_btn.setFixedSize(160, 36)
        self.connect_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #2196F3; color: white; padding: 8px 16px; "
            "  font-weight: bold; border-radius: 5px; "
            "  border: 1px solid #1976D2; border-bottom: 3px solid #1565C0; "
            "}"
            "QPushButton:hover { background-color: #1E88E5; border-bottom: 3px solid #0D47A1; }"
            "QPushButton:pressed { background-color: #1976D2; border-bottom: 1px solid #1565C0; }"
        )
        self.connect_btn.clicked.connect(self._connect_manual)
        select_layout.addWidget(self.connect_btn)
        
        group_layout.addLayout(select_layout)
        
        # Optional "Load from File" button row
        if self._show_load_button:
            load_row = QHBoxLayout()
            load_row.addStretch()
            
            self.load_btn = QPushButton("📂 Load from File...")
            self.load_btn.setFixedSize(160, 36)
            self.load_btn.setStyleSheet(
                "QPushButton { "
                "  background-color: #FF9800; color: white; padding: 8px 16px; "
                "  font-weight: bold; border-radius: 5px; "
                "  border: 1px solid #F57C00; border-bottom: 3px solid #E65100; "
                "}"
                "QPushButton:hover { background-color: #FB8C00; border-bottom: 3px solid #BF360C; }"
                "QPushButton:pressed { background-color: #F57C00; border-bottom: 1px solid #E65100; }"
            )
            self.load_btn.clicked.connect(self._on_load_clicked)
            load_row.addWidget(self.load_btn)
            
            group_layout.addLayout(load_row)
        
        # Connection status
        self.status_label = QLabel("No tenant connected")
        self.status_label.setStyleSheet("color: gray; padding: 8px; margin-top: 5px;")
        group_layout.addWidget(self.status_label)
        
        self.group_box.setLayout(group_layout)
        layout.addWidget(self.group_box)
    
    def _on_load_clicked(self):
        """Handle click on 'Load from File' button."""
        self.load_file_requested.emit()
    
    def _animate_status(self):
        """Animate the connecting status with dots."""
        self._status_dot_count = (self._status_dot_count + 1) % 4
        dots = "." * self._status_dot_count
        spaces = " " * (3 - self._status_dot_count)
        self.status_label.setText(f"⏳ Connecting to {self._connecting_tenant_name}{dots}{spaces}")
    
    def _start_connecting_animation(self, tenant_name: str):
        """Start the connecting animation."""
        self._connecting_tenant_name = tenant_name
        self._status_dot_count = 0
        self.status_label.setText(f"⏳ Connecting to {tenant_name}")
        self.status_label.setStyleSheet(
            "color: #1565C0; padding: 8px; margin-top: 5px; font-style: italic;"
        )
        self._status_animation_timer.start(400)  # Update every 400ms
    
    def _stop_connecting_animation(self):
        """Stop the connecting animation."""
        self._status_animation_timer.stop()
        self._connecting_tenant_name = ""
    
    def populate_tenants(self, tenants: list):
        """
        Populate the dropdown with saved tenants.
        
        Args:
            tenants: List of tenant dictionaries with 'name' key
        """
        # Remember current connection name to restore selection
        current_connection = self.connection_name
        
        # Block signals while repopulating to avoid triggering connection
        self.tenant_combo.blockSignals(True)
        
        try:
            # Clear existing items except placeholder
            self.tenant_combo.clear()
            self.tenant_combo.addItem("-- Select Tenant --", None)
            
            # Add saved tenants
            selected_index = 0
            for i, tenant in enumerate(tenants):
                tenant_name = tenant.get('name', 'Unknown')
                self.tenant_combo.addItem(tenant_name, tenant)
                
                # If this is the currently connected tenant, remember its index
                if current_connection and tenant_name == current_connection:
                    selected_index = i + 1  # +1 for placeholder
            
            # Restore selection to currently connected tenant (if any)
            if selected_index > 0:
                self.tenant_combo.setCurrentIndex(selected_index)
            
            self.logger.detail(f"Populated tenant selector with {len(tenants)} tenant(s)")
            
        finally:
            self.tenant_combo.blockSignals(False)
    
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
        Connect to a saved tenant by name (in background).
        
        Args:
            tenant_name: Name of the saved tenant
        """
        from config.tenant_manager import TenantManager
        
        self.logger.info(f"Attempting to connect to saved tenant: {tenant_name}")
        
        try:
            # Load tenant credentials
            manager = TenantManager()
            tenant = manager.get_tenant_by_name(tenant_name)
            
            if not tenant:
                self.logger.error(f"Tenant not found: {tenant_name}")
                available = [t.get('name') for t in manager.list_tenants()]
                self.logger.info(f"Available tenants: {available}")
                
                if self.show_error_banner:
                    self.show_error_banner(f"Connection Failed: Tenant '{tenant_name}' not found.")
                
                self.tenant_combo.blockSignals(True)
                self.tenant_combo.setCurrentIndex(0)
                self.tenant_combo.blockSignals(False)
                return
            
            self.logger.detail(f"Tenant loaded: {tenant_name}")
            
            # Validate credentials
            tsg_id = tenant.get('tsg_id')
            api_user = tenant.get('client_id')
            api_secret = tenant.get('client_secret')
            
            if not all([tsg_id, api_user, api_secret]):
                self.logger.error(f"Missing credentials for tenant: {tenant_name}")
                
                if self.show_error_banner:
                    self.show_error_banner(f"Connection Failed: Incomplete credentials for '{tenant_name}'.")
                
                self.tenant_combo.blockSignals(True)
                self.tenant_combo.setCurrentIndex(0)
                self.tenant_combo.blockSignals(False)
                return
            
            # Load API settings
            from PyQt6.QtCore import QSettings
            settings = QSettings("PrismaAccess", "ConfigManager")
            timeout = settings.value("api/timeout", 60, type=int)
            rate_limit = settings.value("api/rate_limit", 100, type=int)
            cache_ttl = settings.value("api/cache_ttl", 300, type=int)
            
            # Start animated status
            self._start_connecting_animation(tenant_name)
            
            # Disable UI during connection
            self.tenant_combo.setEnabled(False)
            self.connect_btn.setEnabled(False)
            
            # Store tenant data for mark_used after connection
            self._pending_tenant_data = tenant
            
            # Start background connection
            self._connection_worker = TenantConnectionWorker(
                tenant_name=tenant_name,
                tenant_data=tenant,
                timeout=timeout,
                rate_limit=rate_limit,
                cache_ttl=cache_ttl
            )
            self._connection_worker.connected.connect(self._on_connection_success)
            self._connection_worker.failed.connect(self._on_connection_failed)
            self._connection_worker.finished.connect(self._on_connection_finished)
            self._connection_worker.start()
            
            self.logger.info(f"Background connection started for: {tenant_name}")
                    
        except Exception as e:
            self.logger.error(f"Exception connecting to tenant '{tenant_name}': {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            
            self._stop_connecting_animation()
            self.tenant_combo.setEnabled(True)
            self.connect_btn.setEnabled(True)
            
            if self.show_error_banner:
                self.show_error_banner(f"Connection Error: {str(e)}")
            
            self.tenant_combo.blockSignals(True)
            self.tenant_combo.setCurrentIndex(0)
            self.tenant_combo.blockSignals(False)
    
    def _on_connection_success(self, api_client, tenant_name: str):
        """Handle successful background connection."""
        from config.tenant_manager import TenantManager
        
        self.logger.normal(f"✓ Successfully connected to: {tenant_name}")
        
        # Update last used timestamp
        if hasattr(self, '_pending_tenant_data') and self._pending_tenant_data:
            try:
                manager = TenantManager()
                manager.mark_used(self._pending_tenant_data.get('id'))
            except Exception as e:
                self.logger.warning(f"Failed to update last_used: {e}")
        
        # Set connection
        self.set_connection(api_client, tenant_name)
        
        # Show success
        if self.show_success_toast:
            self.show_success_toast(f"✓ Connected to {tenant_name}", 2000)
    
    def _on_connection_failed(self, tenant_name: str, error_message: str):
        """Handle failed background connection."""
        self.logger.error(f"Connection failed for {tenant_name}: {error_message}")
        
        if self.show_error_banner:
            self.show_error_banner(f"Connection Failed: {error_message}")
        
        # Reset combo selection
        self.tenant_combo.blockSignals(True)
        self.tenant_combo.setCurrentIndex(0)
        self.tenant_combo.blockSignals(False)
        
        # Update status
        self.status_label.setText(f"❌ Connection failed: {error_message[:50]}")
        self.status_label.setStyleSheet(
            "color: #c62828; padding: 8px; margin-top: 5px;"
        )
    
    def _on_connection_finished(self):
        """Handle connection worker finished (success or failure)."""
        self._stop_connecting_animation()
        
        # Re-enable UI
        self.tenant_combo.setEnabled(True)
        self.connect_btn.setEnabled(True)
        
        # Clean up worker
        if self._connection_worker:
            self._connection_worker.deleteLater()
            self._connection_worker = None
        
        # Clear pending data
        self._pending_tenant_data = None
    
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
    
    def set_connection(self, api_client, tenant_name: str, update_dropdown: bool = True):
        """
        Set the current connection.
        
        Args:
            api_client: PrismaAccessAPIClient instance or None
            tenant_name: Name of the connected tenant
            update_dropdown: Whether to update the dropdown selection (default True)
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
            
            # Update dropdown to show selected tenant (if requested)
            if update_dropdown and tenant_name:
                self.tenant_combo.blockSignals(True)
                found = False
                for i in range(self.tenant_combo.count()):
                    if self.tenant_combo.itemText(i) == tenant_name:
                        self.tenant_combo.setCurrentIndex(i)
                        found = True
                        break
                
                # If not found in list, add it
                if not found:
                    self.tenant_combo.addItem(tenant_name, {"name": tenant_name})
                    self.tenant_combo.setCurrentIndex(self.tenant_combo.count() - 1)
                self.tenant_combo.blockSignals(False)
        else:
            # Update status - disconnected
            self.status_label.setText("No tenant connected")
            self.status_label.setStyleSheet("color: gray; padding: 8px; margin-top: 5px;")
            self.logger.detail("Connection cleared")
            
            # Reset dropdown
            if update_dropdown:
                self.tenant_combo.blockSignals(True)
                self.tenant_combo.setCurrentIndex(0)
                self.tenant_combo.blockSignals(False)
        
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
