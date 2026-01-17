"""
Selection List Widget - Card-based hierarchical selection for push configuration.

This module provides the main selection list that displays configuration items
as card-style rows with expand/collapse, checkboxes, and detail panels.
"""

import logging
from typing import Optional, Dict, Any, List

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QScrollArea,
    QFrame,
    QPushButton,
    QCheckBox,
    QGroupBox,
    QMessageBox,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread

from gui.widgets.selection_row import SelectionRow
from gui.widgets.tenant_selector import TenantSelectorWidget
from gui.widgets.selection_tree import COMPONENT_SECTIONS

logger = logging.getLogger(__name__)

# Build reverse mapping from item_type to section name
ITEM_TYPE_TO_SECTION: Dict[str, str] = {}
for section_name, components in COMPONENT_SECTIONS.items():
    for item_type, display_name in components:
        ITEM_TYPE_TO_SECTION[item_type] = section_name


class DestinationFetchWorker(QThread):
    """Background worker to fetch folders and snippets from destination tenant."""
    
    # Signals
    finished = pyqtSignal(list, list, str)  # (folders, snippets, tenant_name)
    error = pyqtSignal(str)  # error_message
    
    def __init__(self, api_client, tenant_name: str):
        super().__init__()
        self.api_client = api_client
        self.tenant_name = tenant_name
    
    def run(self):
        """Fetch folders and snippets in background."""
        try:
            folder_names = []
            snippet_names = []
            
            # Fetch folders
            try:
                folders_response = self.api_client.get_security_policy_folders()
                if isinstance(folders_response, list):
                    folder_names = [f.get('name', '') for f in folders_response if f.get('name')]
                elif isinstance(folders_response, dict):
                    folders_data = folders_response.get('data', [])
                    folder_names = [f.get('name', '') for f in folders_data if f.get('name')]
                
                logger.info(f"Fetched {len(folder_names)} folders from destination tenant '{self.tenant_name}'")
                logger.debug(f"Raw folder names from API: {folder_names}")
            except Exception as e:
                logger.warning(f"Could not fetch folders from destination: {e}")
                # Try fallback method
                try:
                    folders_response = self.api_client.get_folders()
                    if isinstance(folders_response, list):
                        folder_names = [f.get('name', '') for f in folders_response if f.get('name')]
                    elif isinstance(folders_response, dict):
                        folders_data = folders_response.get('data', [])
                        folder_names = [f.get('name', '') for f in folders_data if f.get('name')]
                except Exception as e2:
                    logger.warning(f"Fallback folder fetch also failed: {e2}")
            
            # Fetch snippets
            try:
                snippets_response = self.api_client.get_security_policy_snippets()
                all_snippets = []
                if isinstance(snippets_response, list):
                    all_snippets = snippets_response
                elif isinstance(snippets_response, dict):
                    all_snippets = snippets_response.get('data', [])
                
                # Filter out predefined/readonly snippets
                editable_snippets = []
                for s in all_snippets:
                    snippet_name = s.get('name', '')
                    snippet_type = s.get('type', '')
                    
                    if not snippet_name:
                        continue
                    
                    if snippet_type in ('predefined', 'readonly'):
                        continue
                    
                    if len(s) <= 2:
                        continue
                    
                    editable_snippets.append(snippet_name)
                
                snippet_names = editable_snippets
                logger.info(f"Fetched {len(all_snippets)} snippets, {len(snippet_names)} are editable")
            except Exception as e:
                logger.warning(f"Could not fetch snippets from destination: {e}")
            
            self.finished.emit(folder_names, snippet_names, self.tenant_name)
            
        except Exception as e:
            logger.error(f"Error fetching destination data: {e}")
            self.error.emit(str(e))


class SelectionListWidget(QWidget):
    """
    Card-based hierarchical selection widget for push configuration.
    
    Layout:
    1. Title: "Select Components to Push"
    2. Destination Tenant Selector
    3. Push Configuration (Default Strategy)
    4. Component List (scrollable card rows)
    5. Summary bar
    """
    
    # Signal emitted when selection is ready to push
    selection_ready = pyqtSignal(object)  # (selection_data)
    
    # Signal to request destination tenant connection
    destination_tenant_requested = pyqtSignal()
    
    # Signal emitted when destination connection changes
    destination_connection_changed = pyqtSignal(object, str)  # (api_client, tenant_name)
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the selection list widget."""
        super().__init__(parent)
        
        self.current_config = None
        self.full_config = None
        self.destination_api_client = None
        
        # Source folders/snippets (from pulled config)
        self.source_folders: List[str] = []
        self.source_snippets: List[str] = []
        
        # Config-level metadata (tenant name, version, dates)
        self.config_metadata: Dict[str, Any] = {}
        
        # Destination folders/snippets (from connected destination tenant)
        self.destination_folders: List[str] = []
        self.destination_snippets: List[str] = []
        
        # Track if destination is connected
        self._destination_connected = False
        
        # All selection rows (flat list for easy access)
        self._all_rows: List[SelectionRow] = []
        # Top-level rows only
        self._top_rows: List[SelectionRow] = []
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 12, 16, 12)
        
        # === Title Row with Continue Button ===
        title_row = QHBoxLayout()
        
        title = QLabel("<h2>Select Components to Push</h2>")
        title_row.addWidget(title)
        
        title_row.addStretch()
        
        # Continue button - 3D style matching other workflow buttons
        self.continue_btn = QPushButton("➡️ Continue to Push")
        self.continue_btn.setEnabled(False)
        self.continue_btn.setMinimumWidth(180)
        self.continue_btn.setFixedHeight(36)
        self.continue_btn.setStyleSheet(
            "QPushButton { "
            "  background-color: #4CAF50; color: white; padding: 10px 20px; "
            "  font-size: 13px; font-weight: bold; border-radius: 5px; "
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
            "  padding-top: 12px; "
            "}"
            "QPushButton:disabled { "
            "  background-color: #BDBDBD; "
            "  border: 1px solid #9E9E9E; "
            "  border-bottom: 3px solid #757575; "
            "}"
        )
        self.continue_btn.clicked.connect(self._on_continue)
        title_row.addWidget(self.continue_btn)
        
        layout.addLayout(title_row)
        
        # === Combined Destination & Push Config Row ===
        config_row = QHBoxLayout()
        config_row.setSpacing(16)
        
        # Destination Tenant (left side)
        self.tenant_selector = TenantSelectorWidget(
            parent=self,
            title="Destination Tenant",
            label="Push to:"
        )
        self.tenant_selector.connection_changed.connect(self._on_destination_connection_changed)
        config_row.addWidget(self.tenant_selector, stretch=1)
        
        # Push Configuration (right side)
        config_group = QGroupBox("Push Configuration")
        config_group_layout = QVBoxLayout(config_group)
        config_group_layout.setContentsMargins(12, 8, 12, 8)
        config_group_layout.setSpacing(6)
        
        # Row 1: Default Strategy
        strategy_row = QHBoxLayout()
        strategy_row.addWidget(QLabel("Default Strategy:"))
        
        self.default_strategy_combo = QComboBox()
        self.default_strategy_combo.addItems(["Skip", "Overwrite", "Rename"])
        self.default_strategy_combo.setCurrentText("Skip")
        self.default_strategy_combo.setToolTip(
            "Skip: Don't push if item exists\n"
            "Overwrite: Replace existing item\n"
            "Rename: Create with new name if exists"
        )
        self.default_strategy_combo.currentTextChanged.connect(self._on_default_strategy_changed)
        strategy_row.addWidget(self.default_strategy_combo)
        strategy_row.addStretch()
        
        config_group_layout.addLayout(strategy_row)
        
        # Row 2: Select All and Expand/Collapse
        controls_row = QHBoxLayout()
        
        # Select All checkbox
        self.select_all_check = QCheckBox("Select All")
        self.select_all_check.stateChanged.connect(self._on_select_all)
        self.select_all_check.setEnabled(False)
        controls_row.addWidget(self.select_all_check)
        
        controls_row.addStretch()
        
        # Expand/Collapse buttons (micro grey style)
        micro_btn_style = (
            "QPushButton { "
            "  background-color: #9E9E9E; color: white; "
            "  font-size: 12px; font-weight: bold; border-radius: 3px; "
            "  border: 1px solid #757575; border-bottom: 2px solid #616161; "
            "}"
            "QPushButton:hover { background-color: #757575; border-bottom: 2px solid #424242; }"
            "QPushButton:pressed { background-color: #757575; border-bottom: 1px solid #616161; }"
        )
        
        expand_btn = QPushButton("⊞")
        expand_btn.setToolTip("Expand All")
        expand_btn.setFixedSize(28, 24)
        expand_btn.setStyleSheet(micro_btn_style)
        expand_btn.clicked.connect(self._expand_all)
        controls_row.addWidget(expand_btn)
        
        collapse_btn = QPushButton("⊟")
        collapse_btn.setToolTip("Collapse All")
        collapse_btn.setFixedSize(28, 24)
        collapse_btn.setStyleSheet(micro_btn_style)
        collapse_btn.clicked.connect(self._collapse_all)
        controls_row.addWidget(collapse_btn)
        
        config_group_layout.addLayout(controls_row)
        
        config_row.addWidget(config_group)
        
        layout.addLayout(config_row)
        
        # === Scrollable Component List ===
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                background-color: #ffffff;
            }
        """)
        
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setSpacing(4)
        self.list_layout.setContentsMargins(8, 8, 8, 8)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Placeholder when no config loaded
        self.placeholder_label = QLabel(
            "⏳ No configuration loaded.\n\n"
            "Go to the Pull tab to load a configuration first."
        )
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet("color: #999; padding: 40px; font-size: 14px;")
        self.list_layout.addWidget(self.placeholder_label)
        
        scroll_area.setWidget(self.list_container)
        layout.addWidget(scroll_area, stretch=1)
    
    def set_config(self, config: Dict[str, Any]):
        """
        Set the configuration to display.
        
        Args:
            config: The pulled configuration dictionary
        """
        self.current_config = config
        self.full_config = config
        
        if not config:
            self._clear_list()
            self.placeholder_label.setVisible(True)
            self.select_all_check.setEnabled(False)
            self.continue_btn.setEnabled(False)
            self.source_folders = []
            self.source_snippets = []
            self.config_metadata = {}
            self._update_summary()
            return
        
        # Extract source folders and snippets from config
        self._extract_source_containers(config)
        
        # Extract config-level metadata for display in source panel
        self._extract_config_metadata(config)
        
        self._build_selection_list()
        self.placeholder_label.setVisible(False)
        self.select_all_check.setEnabled(True)
        
        # Auto-select all items when config is loaded
        self.select_all_check.setChecked(True)
        for row in self._top_rows:
            row.set_checked(True)
        
        self._update_summary()
    
    def _extract_config_metadata(self, config: Dict[str, Any]):
        """Extract config-level metadata (tenant, version, dates) from config."""
        metadata = config.get('metadata', {})
        self.config_metadata = {
            'source_tenant': metadata.get('source_tenant', ''),
            'source_config': metadata.get('source_config', ''),
            'program_version': config.get('program_version', ''),
            'created_at': metadata.get('created_at', ''),
            'modified_at': metadata.get('modified_at', ''),
            'load_type': metadata.get('load_type', ''),
        }
        logger.debug(f"Extracted config metadata: {self.config_metadata}")
    
    def _extract_source_containers(self, config: Dict[str, Any]):
        """Extract folder and snippet names from the source config."""
        self.source_folders = []
        self.source_snippets = []
        
        # New format: folders/snippets are dicts keyed by name
        folders_dict = config.get('folders', {})
        if folders_dict:
            self.source_folders = list(folders_dict.keys())
        
        snippets_dict = config.get('snippets', {})
        if snippets_dict:
            self.source_snippets = list(snippets_dict.keys())
        
        # Legacy format: security_policies.folders/snippets are lists
        sec_policies = config.get('security_policies', {})
        if not self.source_folders:
            folders_list = sec_policies.get('folders', [])
            self.source_folders = [f.get('name', '') for f in folders_list if f.get('name')]
        
        if not self.source_snippets:
            snippets_list = sec_policies.get('snippets', [])
            self.source_snippets = [s.get('name', '') for s in snippets_list if s.get('name')]
        
        logger.debug(f"Extracted source folders: {self.source_folders}")
        logger.debug(f"Extracted source snippets: {self.source_snippets}")
    
    def populate_destination_tenants(self, tenants: List[Dict[str, Any]]):
        """
        Populate the destination tenant dropdown with saved tenants.
        
        Args:
            tenants: List of tenant dicts with 'name' key
        """
        self.tenant_selector.populate_tenants(tenants)
    
    def set_destination_connected(self, connected: bool, folders: List[str] = None, snippets: List[str] = None):
        """
        Update the destination connection status and available folders.
        
        Args:
            connected: Whether connected to destination tenant
            folders: List of available folders in destination
            snippets: List of available snippets in destination
        """
        self._destination_connected = connected
        
        if connected:
            self.destination_folders = folders or []
            self.destination_snippets = snippets or []
            
            # Update all rows with destination folders/snippets
            for row in self._all_rows:
                row.set_available_folders(self.destination_folders)
                row.set_available_snippets(self.destination_snippets)
        else:
            self.destination_folders = []
            self.destination_snippets = []
            
            # When not connected, don't show any destination options
            # (dropdown will only show: inherit, original, new snippet)
            for row in self._all_rows:
                row.set_available_folders([])
                row.set_available_snippets([])
    
    def get_destination_api_client(self):
        """Get the destination tenant API client."""
        return self.tenant_selector.api_client
    
    def get_destination_name(self) -> Optional[str]:
        """Get the destination tenant name."""
        return self.tenant_selector.connection_name
    
    def set_destination_from_source(self, api_client, tenant_name: str):
        """
        Set the destination connection from the source tenant.
        
        This is used to auto-connect to the same tenant that was used for pull.
        
        Args:
            api_client: API client from source connection
            tenant_name: Name of the source tenant
        """
        if api_client and tenant_name:
            self.tenant_selector.set_connection(api_client, tenant_name)
    
    def _clear_list(self):
        """Clear all rows from the list."""
        for row in self._all_rows:
            row.deleteLater()
        self._all_rows.clear()
        self._top_rows.clear()
        
        # Clear layout
        while self.list_layout.count() > 1:  # Keep placeholder
            item = self.list_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
    
    # Folder display name mapping
    FOLDER_DISPLAY_NAMES = {
        'All': 'Global',
        'Shared': 'Prisma Access',
        'Mobile Users Container': 'Mobile Users Container',
        'Mobile Users': 'Mobile Users',
        'Mobile Users Explicit Proxy': 'Mobile Users Explicit Proxy',
        'Remote Networks': 'Remote Networks',
        'Service Connections': 'Service Connections',
    }
    
    def _has_actual_items(self, data: Dict) -> bool:
        """Check if a folder/snippet dict has actual configuration items (not just empty lists)."""
        if not data or not isinstance(data, dict):
            return False
        
        for key, value in data.items():
            # Skip metadata keys
            if key in ('name', 'folder', 'snippet', 'display_name'):
                continue
            if isinstance(value, list) and len(value) > 0:
                return True
            if isinstance(value, dict) and value:
                return True
        return False
    
    def _get_folder_display_name(self, folder_name: str) -> str:
        """Get display name for a folder (e.g., 'All' -> 'Global')."""
        return self.FOLDER_DISPLAY_NAMES.get(folder_name, folder_name)
    
    def _build_selection_list(self):
        """Build the selection list from config."""
        self._clear_list()
        
        default_strategy = self.default_strategy_combo.currentText().lower()
        
        # Config can be in two formats:
        # 1. New format from ConfigAdapter: { "folders": {name: {items}}, "snippets": {name: {items}}, ... }
        # 2. Legacy format: { "security_policies": { "folders": [...], "snippets": [...] }, ... }
        
        # === Folders Section ===
        # Try new format first (dict keyed by name), then legacy format (list)
        folders_dict = self.current_config.get('folders', {})
        folders_list = self.current_config.get('security_policies', {}).get('folders', [])
        
        # Filter out empty folders
        non_empty_folders = {}
        if folders_dict:
            for folder_name, folder_data in folders_dict.items():
                if self._has_actual_items(folder_data):
                    non_empty_folders[folder_name] = folder_data
        
        non_empty_folders_list = []
        if folders_list:
            for folder in folders_list:
                # Check if legacy folder has content
                has_content = any([
                    folder.get('security_rules', []),
                    folder.get('address_objects', []),
                    folder.get('address_groups', []),
                    folder.get('service_objects', []),
                    folder.get('service_groups', []),
                    folder.get('applications', []),
                ])
                if has_content:
                    non_empty_folders_list.append(folder)
        
        if non_empty_folders or non_empty_folders_list:
            folders_row = self._create_row(
                "Folders",
                "container",
                level=0,
                has_children=True
            )
            self._add_top_row(folders_row)
            
            if non_empty_folders:
                # New format: dict keyed by folder name
                for folder_name, folder_data in non_empty_folders.items():
                    # folder_data is a dict of item_type -> [items]
                    folder_info = {'name': folder_name, 'folder': folder_name}
                    folder_info.update(folder_data)
                    
                    display_name = self._get_folder_display_name(folder_name)
                    
                    folder_row = self._create_row(
                        display_name,
                        "folder",
                        data=folder_info,
                        level=1,
                        has_children=bool(folder_data)
                    )
                    folders_row.add_child(folder_row)
                    
                    # Add folder contents from the new format
                    self._add_folder_contents_new_format(folder_row, folder_data, folder_name, level=2)
            else:
                # Legacy format: list of folder dicts
                for folder in non_empty_folders_list:
                    folder_name = folder.get('name', 'Unknown Folder')
                    display_name = self._get_folder_display_name(folder_name)
                    
                    folder_row = self._create_row(
                        display_name,
                        "folder",
                        data=folder,
                        level=1,
                        has_children=True
                    )
                    folders_row.add_child(folder_row)
                    
                    # Add folder contents
                    self._add_folder_contents(folder_row, folder, level=2)
        
        # === Snippets Section ===
        snippets_dict = self.current_config.get('snippets', {})
        snippets_list = self.current_config.get('security_policies', {}).get('snippets', [])

        # Include ALL snippets (including empty ones) so user can see what was pulled
        # Empty snippets will be shown with "(empty)" suffix
        if snippets_dict or snippets_list:
            snippets_row = self._create_row(
                "Snippets",
                "container",
                level=0,
                has_children=True
            )
            self._add_top_row(snippets_row)

            if snippets_dict:
                # New format: dict keyed by snippet name
                for snippet_name, snippet_data in snippets_dict.items():
                    snippet_info = {'name': snippet_name, 'snippet': snippet_name}
                    snippet_info.update(snippet_data)

                    has_items = self._has_actual_items(snippet_data)
                    has_children = bool(snippet_data) and has_items

                    # Show "(empty)" suffix for snippets with no items
                    display_name = snippet_name if has_items else f"{snippet_name} (empty)"

                    snippet_row = self._create_row(
                        display_name,
                        "snippet",
                        data=snippet_info,
                        level=1,
                        has_children=has_children
                    )
                    snippets_row.add_child(snippet_row)

                    # Disable checkbox for empty snippets - nothing to push
                    if not has_items:
                        snippet_row.checkbox.setEnabled(False)
                        snippet_row.checkbox.setToolTip("Empty snippet - no items to push")

                    # Add snippet contents if any
                    if snippet_data and has_items:
                        self._add_folder_contents_new_format(snippet_row, snippet_data, snippet_name, level=2, is_snippet=True)
            else:
                # Legacy format: list
                for snippet in snippets_list:
                    snippet_name = snippet.get('name', 'Unknown Snippet')
                    snippet_row = self._create_row(
                        snippet_name,
                        "snippet",
                        data=snippet,
                        level=1,
                        has_children=False
                    )
                    snippets_row.add_child(snippet_row)
        
        # === Objects Section ===
        objects = self.current_config.get('objects', {})
        if objects:
            objects_row = self._create_row(
                "Objects",
                "container",
                level=0,
                has_children=True
            )
            self._add_top_row(objects_row)
            
            for obj_type, obj_list in objects.items():
                if not obj_list:
                    continue
                
                type_display = obj_type.replace('_', ' ').title()
                type_row = self._create_row(
                    type_display,
                    "object_type",
                    level=1,
                    has_children=True
                )
                objects_row.add_child(type_row)
                
                for obj in obj_list:
                    obj_name = obj.get('name', 'Unknown')
                    obj_row = self._create_row(
                        obj_name,
                        obj_type,
                        data=obj,
                        level=2,
                        has_children=False
                    )
                    type_row.add_child(obj_row)
        
        # === Infrastructure Section ===
        # Build hierarchy matching the pull selection tree:
        # - Remote Networks
        #   ├─ IPsec Tunnels
        #   │    ├─ IKE Gateways
        #   │    │   └─ IKE Crypto Profiles  
        #   │    └─ IPsec Crypto Profiles
        #   └─ Regions & Bandwidth
        # - Service Connections
        #   └─ IPsec Tunnels (same sub-hierarchy)
        # - Mobile Users
        #   └─ Agent Profiles
        
        infrastructure = self.current_config.get('infrastructure', {})
        if infrastructure:
            infra_row = self._create_row(
                "Infrastructure",
                "container",
                level=0,
                has_children=True
            )
            
            # Group items by their folder (Remote Networks, Service Connections, etc.)
            rn_items = {}  # Remote Networks items
            sc_items = {}  # Service Connections items
            mu_items = {}  # Mobile Users items
            other_items = {}  # Other items
            
            for infra_type, infra_items in infrastructure.items():
                if not infra_items:
                    continue
                
                items_list = infra_items if isinstance(infra_items, list) else [infra_items]
                
                for item in items_list:
                    if not isinstance(item, dict):
                        continue
                    
                    folder = item.get('folder', '')
                    
                    # Categorize by folder
                    if folder == 'Remote Networks':
                        if infra_type not in rn_items:
                            rn_items[infra_type] = []
                        rn_items[infra_type].append(item)
                    elif folder == 'Service Connections':
                        if infra_type not in sc_items:
                            sc_items[infra_type] = []
                        sc_items[infra_type].append(item)
                    elif infra_type in ('agent_profile', 'globalprotect_portal', 'globalprotect_gateway'):
                        if infra_type not in mu_items:
                            mu_items[infra_type] = []
                        mu_items[infra_type].append(item)
                    else:
                        # Bandwidth/regions or other items without folder
                        if infra_type not in other_items:
                            other_items[infra_type] = []
                        other_items[infra_type].append(item)
            
            has_any_infra = rn_items or sc_items or mu_items or other_items
            
            if has_any_infra:
                self._add_top_row(infra_row)
                
                # Remote Networks section
                if rn_items or 'bandwidth_allocation' in other_items or 'region' in other_items:
                    rn_row = self._create_row(
                        "Remote Networks",
                        "infrastructure_section",
                        level=1,
                        has_children=True
                    )
                    infra_row.add_child(rn_row)
                    
                    # Add IPsec hierarchy for Remote Networks
                    self._add_ipsec_hierarchy(rn_row, rn_items, "Remote Networks", level=2)
                    
                    # Add Regions & Bandwidth under Remote Networks
                    regions_bandwidth_items = {}
                    if 'bandwidth_allocation' in other_items:
                        regions_bandwidth_items['bandwidth_allocation'] = other_items.pop('bandwidth_allocation')
                    if 'region' in other_items:
                        regions_bandwidth_items['region'] = other_items.pop('region')
                    
                    if regions_bandwidth_items:
                        rb_row = self._create_row(
                            "Regions & Bandwidth",
                            "infrastructure_section",
                            level=2,
                            has_children=True
                        )
                        rn_row.add_child(rb_row)
                        
                        for rb_type, rb_items in regions_bandwidth_items.items():
                            type_display = rb_type.replace('_', ' ').title()
                            for item in rb_items:
                                item_name = item.get('name', item.get('region', 'Unknown'))
                                item_row = self._create_row(
                                    item_name,
                                    rb_type,
                                    data=item,
                                    level=3,
                                    has_children=False
                                )
                                rb_row.add_child(item_row)
                
                # Service Connections section
                if sc_items:
                    sc_row = self._create_row(
                        "Service Connections",
                        "infrastructure_section",
                        level=1,
                        has_children=True
                    )
                    infra_row.add_child(sc_row)
                    
                    # Add IPsec hierarchy for Service Connections
                    self._add_ipsec_hierarchy(sc_row, sc_items, "Service Connections", level=2)
                
                # Mobile Users section
                if mu_items:
                    mu_row = self._create_row(
                        "Mobile Users",
                        "infrastructure_section",
                        level=1,
                        has_children=True
                    )
                    infra_row.add_child(mu_row)
                    
                    # Agent Profiles
                    if 'agent_profile' in mu_items:
                        ap_row = self._create_row(
                            "Agent Profiles",
                            "agent_profile_container",
                            level=2,
                            has_children=True
                        )
                        mu_row.add_child(ap_row)
                        
                        for item in mu_items['agent_profile']:
                            item_name = item.get('name', 'Unknown')
                            item_row = self._create_row(
                                item_name,
                                'agent_profile',
                                data=item,
                                level=3,
                                has_children=False
                            )
                            ap_row.add_child(item_row)
                    
                    # Other Mobile Users items (portals, gateways)
                    for mu_type in ('globalprotect_portal', 'globalprotect_gateway'):
                        if mu_type in mu_items:
                            type_display = mu_type.replace('_', ' ').title()
                            type_row = self._create_row(
                                type_display,
                                f"{mu_type}_container",
                                level=2,
                                has_children=True
                            )
                            mu_row.add_child(type_row)
                            
                            for item in mu_items[mu_type]:
                                item_name = item.get('name', 'Unknown')
                                item_row = self._create_row(
                                    item_name,
                                    mu_type,
                                    data=item,
                                    level=3,
                                    has_children=False
                                )
                                type_row.add_child(item_row)
                
                # Any remaining other items
                for other_type, items in other_items.items():
                    type_display = other_type.replace('_', ' ').title()
                    type_row = self._create_row(
                        type_display,
                        "infrastructure_type",
                        level=1,
                        has_children=True
                    )
                    infra_row.add_child(type_row)
                    
                    for item in items:
                        item_name = item.get('name', 'Unknown')
                        item_row = self._create_row(
                            item_name,
                            other_type,
                            data=item,
                            level=2,
                            has_children=False
                        )
                        type_row.add_child(item_row)
        
        # Expand top level and select all by default
        for row in self._top_rows:
            row.set_expanded(True)
            row.set_checked(True)
        
        # Update select all checkbox to reflect the state
        self.select_all_check.blockSignals(True)
        self.select_all_check.setChecked(True)
        self.select_all_check.blockSignals(False)
    
    def _add_folder_contents_new_format(self, parent_row: SelectionRow, items_dict: Dict, container_name: str, level: int, is_snippet: bool = False):
        """
        Add folder/snippet contents from new config format with section groupings.

        Creates a hierarchy matching COMPONENT_SECTIONS:
        - Section (e.g., "Addresses")
          - Type (e.g., "Address Objects")
            - Item (e.g., "my-address")

        Args:
            parent_row: The parent row to add items to
            items_dict: Dictionary of {item_type: [items]}
            container_name: Name of the containing folder/snippet
            level: Indentation level
            is_snippet: True if parent is a snippet (sets 'snippet' key), False for folder
        """
        # Group items by section
        items_by_section: Dict[str, Dict[str, List]] = {}
        ungrouped_items: Dict[str, List] = {}

        for item_type, items in items_dict.items():
            if not items or not isinstance(items, list):
                continue

            section = ITEM_TYPE_TO_SECTION.get(item_type)
            if section:
                if section not in items_by_section:
                    items_by_section[section] = {}
                items_by_section[section][item_type] = items
            else:
                # Items not in any section (e.g., profiles dict, hip dict)
                ungrouped_items[item_type] = items

        # Add sections in COMPONENT_SECTIONS order
        for section_name, section_components in COMPONENT_SECTIONS.items():
            if section_name not in items_by_section:
                continue

            section_items = items_by_section[section_name]

            # Create section container
            section_row = self._create_row(
                section_name,
                "section_container",
                level=level,
                has_children=True
            )
            parent_row.add_child(section_row)

            # Add item types within section (in COMPONENT_SECTIONS order)
            for item_type, type_display in section_components:
                if item_type not in section_items:
                    continue

                items = section_items[item_type]

                # Create type container
                type_row = self._create_row(
                    type_display,
                    f"{item_type}_container",
                    level=level + 1,
                    has_children=True
                )
                section_row.add_child(type_row)

                # Add individual items
                for item in items:
                    if not isinstance(item, dict):
                        continue

                    item_name = item.get('name', 'Unknown')
                    # Add folder/snippet info to item data for destination defaults
                    item_data = item.copy()
                    if is_snippet:
                        # Item is from a snippet - set snippet key
                        item_data['snippet'] = item.get('snippet', container_name)
                        # Clear folder if it was set to the snippet name
                        if item_data.get('folder') == container_name:
                            item_data.pop('folder', None)
                    else:
                        # Item is from a folder
                        item_data['folder'] = item.get('folder', container_name)

                    item_row = self._create_row(
                        item_name,
                        item_type,
                        data=item_data,
                        level=level + 2,
                        has_children=False
                    )
                    type_row.add_child(item_row)

        # Handle ungrouped items (profiles dict, hip dict, etc.)
        for item_type, items in ungrouped_items.items():
            if not items:
                continue

            type_display = item_type.replace('_', ' ').title()
            type_row = self._create_row(
                type_display,
                f"{item_type}_container",
                level=level,
                has_children=True
            )
            parent_row.add_child(type_row)

            for item in items:
                if not isinstance(item, dict):
                    continue

                item_name = item.get('name', 'Unknown')
                item_data = item.copy()
                if is_snippet:
                    item_data['snippet'] = item.get('snippet', container_name)
                    if item_data.get('folder') == container_name:
                        item_data.pop('folder', None)
                else:
                    item_data['folder'] = item.get('folder', container_name)

                item_row = self._create_row(
                    item_name,
                    item_type,
                    data=item_data,
                    level=level + 1,
                    has_children=False
                )
                type_row.add_child(item_row)
    
    def _add_ipsec_hierarchy(self, parent_row: SelectionRow, items_by_type: Dict, folder_name: str, level: int):
        """
        Add IPsec hierarchy to a parent row (Remote Networks or Service Connections).
        
        Hierarchy:
        - IPsec Tunnels
          ├─ IKE Gateways
          │   └─ IKE Crypto Profiles
          └─ IPsec Crypto Profiles
        """
        # Check if we have any IPsec-related items
        ipsec_tunnels = items_by_type.get('ipsec_tunnel', [])
        ike_gateways = items_by_type.get('ike_gateway', [])
        ike_crypto = items_by_type.get('ike_crypto_profile', [])
        ipsec_crypto = items_by_type.get('ipsec_crypto_profile', [])
        
        # Also check for network/connection items
        remote_networks = items_by_type.get('remote_network', [])
        service_connections = items_by_type.get('service_connection', [])
        
        # Add Remote Network / Service Connection items directly
        main_items = remote_networks if folder_name == "Remote Networks" else service_connections
        for item in main_items:
            item_name = item.get('name', 'Unknown')
            item_row = self._create_row(
                item_name,
                'remote_network' if folder_name == "Remote Networks" else 'service_connection',
                data=item,
                level=level,
                has_children=False
            )
            parent_row.add_child(item_row)
        
        # IPsec Tunnels section (if we have tunnels, gateways, or crypto profiles)
        has_ipsec = ipsec_tunnels or ike_gateways or ike_crypto or ipsec_crypto
        if has_ipsec:
            tunnels_row = self._create_row(
                "IPsec Tunnels",
                "ipsec_tunnel_container",
                level=level,
                has_children=True
            )
            parent_row.add_child(tunnels_row)
            
            # Add actual tunnel items
            for item in ipsec_tunnels:
                item_name = item.get('name', 'Unknown')
                item_row = self._create_row(
                    item_name,
                    'ipsec_tunnel',
                    data=item,
                    level=level + 1,
                    has_children=False
                )
                tunnels_row.add_child(item_row)
            
            # IKE Gateways section
            if ike_gateways or ike_crypto:
                ike_gw_row = self._create_row(
                    "IKE Gateways",
                    "ike_gateway_container",
                    level=level + 1,
                    has_children=True
                )
                tunnels_row.add_child(ike_gw_row)
                
                # Add gateway items
                for item in ike_gateways:
                    item_name = item.get('name', 'Unknown')
                    item_row = self._create_row(
                        item_name,
                        'ike_gateway',
                        data=item,
                        level=level + 2,
                        has_children=False
                    )
                    ike_gw_row.add_child(item_row)
                
                # IKE Crypto Profiles under IKE Gateways
                if ike_crypto:
                    ike_crypto_row = self._create_row(
                        "IKE Crypto Profiles",
                        "ike_crypto_profile_container",
                        level=level + 2,
                        has_children=True
                    )
                    ike_gw_row.add_child(ike_crypto_row)
                    
                    for item in ike_crypto:
                        item_name = item.get('name', 'Unknown')
                        item_row = self._create_row(
                            item_name,
                            'ike_crypto_profile',
                            data=item,
                            level=level + 3,
                            has_children=False
                        )
                        ike_crypto_row.add_child(item_row)
            
            # IPsec Crypto Profiles (under IPsec Tunnels, sibling to IKE Gateways)
            if ipsec_crypto:
                ipsec_crypto_row = self._create_row(
                    "IPsec Crypto Profiles",
                    "ipsec_crypto_profile_container",
                    level=level + 1,
                    has_children=True
                )
                tunnels_row.add_child(ipsec_crypto_row)
                
                for item in ipsec_crypto:
                    item_name = item.get('name', 'Unknown')
                    item_row = self._create_row(
                        item_name,
                        'ipsec_crypto_profile',
                        data=item,
                        level=level + 2,
                        has_children=False
                    )
                    ipsec_crypto_row.add_child(item_row)
    
    def _add_folder_contents(self, folder_row: SelectionRow, folder: Dict, level: int):
        """Add folder contents (rules, objects, profiles) to folder row - legacy format."""
        # Security Rules
        rules = folder.get('security_rules', [])
        if rules:
            rules_container = self._create_row(
                "Security Rules",
                "rules_container",
                level=level,
                has_children=True
            )
            folder_row.add_child(rules_container)
            
            for rule in rules:
                rule_name = rule.get('name', 'Unknown Rule')
                rule_row = self._create_row(
                    rule_name,
                    "security_rule",
                    data=rule,
                    level=level + 1,
                    has_children=False
                )
                rules_container.add_child(rule_row)
        
        # Objects
        objects = folder.get('objects', {})
        if objects:
            obj_container = self._create_row(
                "Objects",
                "objects_container",
                level=level,
                has_children=True
            )
            folder_row.add_child(obj_container)
            
            for obj_type, obj_list in objects.items():
                if not obj_list:
                    continue
                type_display = obj_type.replace('_', ' ').title()
                type_row = self._create_row(
                    type_display,
                    "object_type",
                    level=level + 1,
                    has_children=True
                )
                obj_container.add_child(type_row)
                
                for obj in obj_list:
                    obj_name = obj.get('name', 'Unknown')
                    obj_row = self._create_row(
                        obj_name,
                        obj_type,
                        data=obj,
                        level=level + 2,
                        has_children=False
                    )
                    type_row.add_child(obj_row)
        
        # Profiles
        profiles = folder.get('profiles', {})
        if profiles:
            prof_container = self._create_row(
                "Profiles",
                "profiles_container",
                level=level,
                has_children=True
            )
            folder_row.add_child(prof_container)
            
            for prof_type, prof_list in profiles.items():
                if not prof_list:
                    continue
                type_display = prof_type.replace('_', ' ').title()
                type_row = self._create_row(
                    type_display,
                    "profile_type",
                    level=level + 1,
                    has_children=True
                )
                prof_container.add_child(type_row)
                
                for profile in prof_list:
                    prof_name = profile.get('name', 'Unknown')
                    prof_row = self._create_row(
                        prof_name,
                        prof_type,
                        data=profile,
                        level=level + 2,
                        has_children=False
                    )
                    type_row.add_child(prof_row)
    
    def _create_row(
        self,
        label: str,
        item_type: str,
        data: Dict = None,
        level: int = 0,
        has_children: bool = False
    ) -> SelectionRow:
        """Create a selection row."""
        # Only show destination folders/snippets if connected to destination tenant
        # Otherwise show empty list (dropdown will only have: inherit, original, new snippet)
        if self._destination_connected:
            available_folders = self.destination_folders
            available_snippets = self.destination_snippets
        else:
            available_folders = []
            available_snippets = []
        
        row = SelectionRow(
            label=label,
            item_type=item_type,
            data=data,
            level=level,
            has_children=has_children,
            parent_widget=self.list_container,
            available_folders=available_folders,
            available_snippets=available_snippets,
            default_push_strategy=self.default_strategy_combo.currentText().lower(),
            config_metadata=self.config_metadata,
        )
        
        # Connect signals
        row.selection_changed.connect(self._on_row_selection_changed)
        row.detail_changed.connect(self._on_row_detail_changed)
        
        self._all_rows.append(row)
        return row
    
    def _add_top_row(self, row: SelectionRow):
        """Add a top-level row to the list."""
        self._top_rows.append(row)
        self.list_layout.addWidget(row)
    
    def _on_row_selection_changed(self, row: SelectionRow, is_checked: bool):
        """Handle row selection change."""
        self._update_summary()
    
    def _on_row_detail_changed(self, row: SelectionRow):
        """Handle row detail settings change."""
        # Could trigger validation or preview updates
        pass
    
    def _on_select_all(self, state):
        """Handle select all checkbox."""
        is_checked = state == Qt.CheckState.Checked.value
        for row in self._top_rows:
            row.set_checked(is_checked)
        self._update_summary()
    
    def _on_default_strategy_changed(self, strategy: str):
        """Handle default strategy change."""
        strategy_lower = strategy.lower()
        for row in self._all_rows:
            row.update_default_strategy(strategy_lower)
    
    # Folders that cannot be pushed to (read-only or special)
    # These are specifically folders under "Prisma Access" that are not directly editable
    # Include variations (space vs hyphen) and exact names as they appear
    NON_EDITABLE_FOLDERS = {
        'ngfw-shared',
        'colo-connect', 'colo connect',  # Under Prisma Access - not editable
        'service-connections', 'service connections',  # Under Prisma Access - not editable
        'predefined', 'default',
        # Note: Remote Networks IS a valid Security Policy folder and should NOT be filtered
    }
    
    # Note: Snippets are now filtered by type='Custom' in _on_destination_connection_changed
    # This set is kept for backwards compatibility but not used for snippet filtering
    DEFAULT_SNIPPETS = set()  # Filtering done by type field instead
    
    def _filter_editable_folders(self, folders: list) -> list:
        """Filter out non-editable folders."""
        result = []
        blocked_folders = []
        for f in folders:
            if not f:
                continue
            # Normalize: lowercase and replace hyphens with spaces for comparison
            normalized = f.lower().replace('-', ' ')
            # Check against normalized versions of blocklist
            is_blocked = False
            for blocked in self.NON_EDITABLE_FOLDERS:
                blocked_normalized = blocked.lower().replace('-', ' ')
                if normalized == blocked_normalized:
                    is_blocked = True
                    blocked_folders.append(f"'{f}' (matched '{blocked}')")
                    break
            if not is_blocked:
                result.append(f)
        
        if blocked_folders:
            logger.debug(f"Blocked folders: {blocked_folders}")
        
        return result
    
    def _on_destination_connection_changed(self, api_client, tenant_name: str):
        """Handle destination tenant connection change."""
        # Check if destination is same as source - just note it, don't block
        source_tenant = self.config_metadata.get('source_tenant', '')
        self._dest_is_same_as_source = False
        if api_client and tenant_name and source_tenant:
            # Normalize names for comparison (strip whitespace, case-insensitive)
            source_normalized = source_tenant.strip().lower()
            dest_normalized = tenant_name.strip().lower()
            
            if source_normalized == dest_normalized:
                self._dest_is_same_as_source = True
                logger.info(f"Destination tenant is same as source: {tenant_name}")
        
        self.destination_api_client = api_client
        self._pending_dest_tenant_name = tenant_name
        
        if api_client:
            # Connected - fetch folders and snippets in background to avoid UI freeze
            logger.info(f"Starting background fetch for destination tenant '{tenant_name}'")
            
            # Show loading state
            self.tenant_selector.status_label.setText(f"⏳ Loading folders from {tenant_name}...")
            self.tenant_selector.status_label.setStyleSheet(
                "color: #1565C0; padding: 8px; margin-top: 5px; font-style: italic;"
            )
            
            # Start background worker
            self._dest_fetch_worker = DestinationFetchWorker(api_client, tenant_name)
            self._dest_fetch_worker.finished.connect(self._on_destination_fetch_finished)
            self._dest_fetch_worker.error.connect(self._on_destination_fetch_error)
            self._dest_fetch_worker.start()
        else:
            self.set_destination_connected(False)
            # Emit signal so other widgets (like push_widget) can sync
            self.destination_connection_changed.emit(api_client, tenant_name if tenant_name else "")
            # Update continue button state
            self._update_summary()
    
    def _on_destination_fetch_finished(self, folder_names: list, snippet_names: list, tenant_name: str):
        """Handle completion of background folder/snippet fetch."""
        logger.debug(f"Received folders from worker: {folder_names}")
        
        # Filter out non-editable folders
        filtered_folders = self._filter_editable_folders(folder_names)
        filtered_snippets = snippet_names  # Already filtered by type in worker
        
        logger.info(f"After filtering: {len(filtered_folders)} editable folders, {len(filtered_snippets)} editable snippets")
        logger.debug(f"Filtered folders result: {filtered_folders}")
        logger.debug(f"Filtered out folders: {set(folder_names) - set(filtered_folders)}")
        
        self.set_destination_connected(True, folders=filtered_folders, snippets=filtered_snippets)
        logger.info(f"Connected to destination tenant '{tenant_name}' with {len(filtered_folders)} folders and {len(filtered_snippets)} snippets")
        
        # Update status to connected
        if getattr(self, '_dest_is_same_as_source', False):
            self.tenant_selector.status_label.setText(f"✓ Connected to {tenant_name} (same as source)")
            self.tenant_selector.status_label.setStyleSheet(
                "color: #1565C0; padding: 8px; margin-top: 5px; font-weight: bold;"
            )
        else:
            self.tenant_selector.status_label.setText(f"✓ Connected to {tenant_name}")
            self.tenant_selector.status_label.setStyleSheet(
                "color: #2e7d32; padding: 8px; margin-top: 5px; font-weight: bold;"
            )
        
        # Emit signal so other widgets (like push_widget) can sync
        self.destination_connection_changed.emit(self.destination_api_client, tenant_name if tenant_name else "")
        
        # Update continue button state
        self._update_summary()
        
        # Cleanup worker
        if hasattr(self, '_dest_fetch_worker') and self._dest_fetch_worker:
            self._dest_fetch_worker.deleteLater()
            self._dest_fetch_worker = None
    
    def _on_destination_fetch_error(self, error_message: str):
        """Handle error during background folder/snippet fetch."""
        tenant_name = getattr(self, '_pending_dest_tenant_name', 'Unknown')
        logger.error(f"Error fetching destination data for {tenant_name}: {error_message}")
        
        # Still mark as connected, just with empty folders/snippets
        self.set_destination_connected(True, folders=[], snippets=[])
        
        # Update status
        self.tenant_selector.status_label.setText(f"✓ Connected to {tenant_name} (folder fetch failed)")
        self.tenant_selector.status_label.setStyleSheet(
            "color: #F57F17; padding: 8px; margin-top: 5px; font-weight: bold;"
        )
        
        # Emit signal so other widgets (like push_widget) can sync
        self.destination_connection_changed.emit(self.destination_api_client, tenant_name if tenant_name else "")
        
        # Update continue button state
        self._update_summary()
        
        # Cleanup worker
        if hasattr(self, '_dest_fetch_worker') and self._dest_fetch_worker:
            self._dest_fetch_worker.deleteLater()
            self._dest_fetch_worker = None
    
    def _expand_all(self):
        """Expand all rows."""
        for row in self._all_rows:
            if row.has_children:
                row.set_expanded(True)
    
    def _collapse_all(self):
        """Collapse all rows."""
        for row in self._all_rows:
            if row.has_children:
                row.set_expanded(False)
    
    def _update_summary(self):
        """Update the continue button state based on selection."""
        if not self.current_config:
            self.continue_btn.setEnabled(False)
            return
        
        # Count selected items
        selected_count = sum(1 for row in self._all_rows if row.is_checked() and not row.has_children)
        
        # Enable continue button only if:
        # 1. Items are selected AND
        # 2. Destination tenant is connected
        can_continue = selected_count > 0 and self._destination_connected
        self.continue_btn.setEnabled(can_continue)
        
        # Update button tooltip to explain why it's disabled
        if not self._destination_connected:
            self.continue_btn.setToolTip("Select a destination tenant first")
        elif selected_count == 0:
            self.continue_btn.setToolTip("Select items to push")
        else:
            self.continue_btn.setToolTip(f"Continue to push {selected_count} item(s)")
    
    def _on_continue(self):
        """Handle continue to push button."""
        if not self.current_config:
            QMessageBox.warning(self, "No Config", "Please load a configuration first")
            return
        
        # Collect selected items with their destination settings
        selection = self._collect_selection()
        
        if not selection:
            QMessageBox.warning(self, "No Selection", "Please select at least one component.")
            return
        
        # Emit the selection
        self.selection_ready.emit(selection)
    
    def _collect_selection(self) -> Dict[str, Any]:
        """Collect all selected items with their destination settings.
        
        The push orchestrator expects this format:
        {
            'folders': [
                {
                    'name': 'folder_name',
                    'objects': {type: [items]},
                    'profiles': {type: [items]},
                    'hip': {type: [items]},
                    'security_rules': [items]
                }
            ],
            'snippets': [{snippet with rules}],
            'infrastructure': {type: [items]},
            'default_strategy': 'skip'
        }
        """
        # Track folders/snippets as containers for grouping items
        folders_dict = {}  # folder_name -> {objects: {}, profiles: {}, hip: {}, security_rules: []}
        snippets_dict = {}  # snippet_name -> {rules: [], ...}
        infrastructure = {}  # type -> [items]
        
        default_strategy = self.default_strategy_combo.currentText().lower()
        
        # Object types that go into 'profiles' category
        PROFILE_TYPES = {
            'decryption_profile', 'hip_profile', 'security_profile_group',
            'url_filtering_profile', 'vulnerability_protection_profile',
            'anti_spyware_profile', 'antivirus_profile', 'file_blocking_profile',
            'wildfire_antivirus_profile', 'dns_security_profile', 'data_filtering_profile',
        }
        
        # Object types that go into 'hip' category
        HIP_TYPES = {
            'hip_object', 'hip_profile',
        }
        
        # Infrastructure types
        INFRA_TYPES = {
            'remote_network', 'service_connection', 'ipsec_tunnel',
            'ike_gateway', 'ike_crypto_profile', 'ipsec_crypto_profile',
            'agent_profile', 'bandwidth_allocation', 'regions',
        }
        
        # Track container-level destination settings (for rename/new snippet operations)
        container_destinations = {}  # source_name -> destination_settings
        
        def collect_container_destinations(row: SelectionRow):
            """First pass: collect destination settings from container rows."""
            if row.has_children and row.item_type in ('folder', 'snippet'):
                source_name = row.label_text
                dest = row.get_destination_settings()
                container_destinations[source_name] = dest
                logger.debug(f"Container destination for '{source_name}': {dest}")
                
                # Also store by API name (from row data) if different from display name
                # This handles folder name mappings like 'Shared' -> 'Prisma Access'
                row_data = row.get_data()
                if row_data:
                    api_name = row_data.get('name', '')
                    if api_name and api_name != source_name:
                        container_destinations[api_name] = dest
                        logger.debug(f"Container destination for '{api_name}' (API name): {dest}")
            
            for child in row.get_children():
                collect_container_destinations(child)
        
        # First pass: collect container destinations
        for row in self._top_rows:
            collect_container_destinations(row)
        
        def collect_recursive(row: SelectionRow):
            # Only collect checked leaf items (actual config objects)
            if row.is_checked() and not row.has_children:
                data = row.get_data()
                if not data:
                    return

                item_type = row.item_type

                # Skip container types (folder, snippet) that are empty
                # These are just container markers, not actual pushable items
                if item_type in ('folder', 'snippet', 'container'):
                    logger.debug(f"Skipping empty container '{row.label_text}' (type: {item_type})")
                    return

                dest = row.get_destination_settings()
                
                # Merge destination settings into data
                item_data = data.copy()
                item_data['_destination'] = dest
                
                # Get source location
                folder = data.get('folder', '')
                snippet = data.get('snippet', '')
                
                # Debug: log items that have both folder and snippet set
                if folder and snippet:
                    logger.warning(f"Item '{data.get('name', '?')}' has both folder='{folder}' and snippet='{snippet}' - using snippet")
                
                # Handle infrastructure items separately
                if item_type in INFRA_TYPES:
                    if item_type not in infrastructure:
                        infrastructure[item_type] = []
                    infrastructure[item_type].append(item_data)
                    return
                
                # Group by folder or snippet
                # IMPORTANT: Prefer snippet over folder if both are set
                if snippet:
                    if snippet not in snippets_dict:
                        # Get container-level destination settings
                        container_dest = container_destinations.get(snippet, {})
                        snippets_dict[snippet] = {
                            'name': snippet,
                            '_destination': container_dest,  # Container destination settings
                            'objects': {},
                            'profiles': {},
                            'security_rules': []
                        }
                    
                    snippet_entry = snippets_dict[snippet]
                    
                    if item_type == 'security_rule' or item_type == 'rule':
                        snippet_entry['security_rules'].append(item_data)
                    elif item_type in PROFILE_TYPES:
                        if item_type not in snippet_entry['profiles']:
                            snippet_entry['profiles'][item_type] = []
                        snippet_entry['profiles'][item_type].append(item_data)
                    else:
                        if item_type not in snippet_entry['objects']:
                            snippet_entry['objects'][item_type] = []
                        snippet_entry['objects'][item_type].append(item_data)
                
                elif folder:
                    if folder not in folders_dict:
                        # Get container-level destination settings
                        container_dest = container_destinations.get(folder, {})
                        folders_dict[folder] = {
                            'name': folder,
                            '_destination': container_dest,  # Container destination settings
                            'objects': {},
                            'profiles': {},
                            'hip': {},
                            'security_rules': []
                        }
                    
                    folder_entry = folders_dict[folder]
                    
                    # Determine category
                    if item_type == 'security_rule' or item_type == 'rule':
                        folder_entry['security_rules'].append(item_data)
                    elif item_type in HIP_TYPES:
                        if item_type not in folder_entry['hip']:
                            folder_entry['hip'][item_type] = []
                        folder_entry['hip'][item_type].append(item_data)
                    elif item_type in PROFILE_TYPES:
                        if item_type not in folder_entry['profiles']:
                            folder_entry['profiles'][item_type] = []
                        folder_entry['profiles'][item_type].append(item_data)
                    else:
                        # Regular objects
                        if item_type not in folder_entry['objects']:
                            folder_entry['objects'][item_type] = []
                        folder_entry['objects'][item_type].append(item_data)
            
            # Recurse into children
            for child in row.get_children():
                collect_recursive(child)
        
        for row in self._top_rows:
            collect_recursive(row)
        
        # Convert dicts to lists
        folders_list = list(folders_dict.values())
        snippets_list = list(snippets_dict.values())
        
        result = {
            'folders': folders_list,
            'snippets': snippets_list,
            'infrastructure': infrastructure,
            'default_strategy': default_strategy,
        }
        
        # Debug logging to understand what we're sending
        logger.info("=" * 60)
        logger.info("SELECTION COLLECTION DEBUG")
        logger.info(f"Default strategy: {default_strategy}")
        logger.info(f"Folders: {len(folders_list)}")
        for folder in folders_list:
            folder_name = folder.get('name', 'Unknown')
            folder_dest = folder.get('_destination', {})
            dest_info = ""
            if folder_dest.get('is_new_snippet') or folder_dest.get('is_rename_snippet'):
                new_name = folder_dest.get('new_snippet_name', '')
                dest_info = f" → NEW SNIPPET '{new_name}'"
            obj_count = sum(len(v) for v in folder.get('objects', {}).values())
            prof_count = sum(len(v) for v in folder.get('profiles', {}).values())
            hip_count = sum(len(v) for v in folder.get('hip', {}).values())
            rule_count = len(folder.get('security_rules', []))
            logger.info(f"  📁 {folder_name}{dest_info}: {obj_count} objects, {prof_count} profiles, {hip_count} HIP, {rule_count} rules")
        
        logger.info(f"Snippets: {len(snippets_list)}")
        for snippet in snippets_list:
            snippet_name = snippet.get('name', 'Unknown')
            snippet_dest = snippet.get('_destination', {})
            dest_info = ""
            if snippet_dest.get('is_new_snippet') or snippet_dest.get('is_rename_snippet'):
                new_name = snippet_dest.get('new_snippet_name', '')
                dest_info = f" → NEW SNIPPET '{new_name}'"
            obj_count = sum(len(v) for v in snippet.get('objects', {}).values())
            prof_count = sum(len(v) for v in snippet.get('profiles', {}).values())
            rule_count = len(snippet.get('security_rules', []))
            logger.info(f"  📄 {snippet_name}{dest_info}: {obj_count} objects, {prof_count} profiles, {rule_count} rules")
        
        logger.info(f"Infrastructure types: {list(infrastructure.keys())}")
        for infra_type, items in infrastructure.items():
            logger.info(f"  🏗️ {infra_type}: {len(items)} items")
        
        logger.info("=" * 60)
        
        return result
    
    def get_selected_items(self) -> Dict[str, Any]:
        """Get the current selection (public API)."""
        return self._collect_selection()
    
    def add_items_to_selection(self, items: List[Dict]):
        """
        Add items to the selection by checking their corresponding rows.
        
        Used to add missing dependencies identified during validation.
        
        Args:
            items: List of dicts with 'name', 'type', 'data' keys
                   The 'data' dict may contain 'folder' or 'snippet' to match container
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if not items:
            return
        
        logger.info(f"Adding {len(items)} items to selection")
        
        # Build a lookup of items to add
        # Key: (name, type, folder_or_snippet) or (name, type, None) as fallback
        items_to_add = {}
        for item in items:
            name = item.get('name', '')
            item_type = item.get('type', '')
            data = item.get('data', {})
            # Get container info from the item's data
            container = data.get('snippet') or data.get('folder') or None
            
            if name and item_type:
                # Store with container info for precise matching
                key = (name, item_type, container)
                items_to_add[key] = item
                logger.info(f"  Looking for: {item_type} '{name}' in '{container or 'any'}'")
        
        def find_and_check_rows(row: 'SelectionRow', current_container: str = None):
            """Recursively find and check rows matching items to add."""
            # Track container as we traverse
            row_container = current_container
            if row.item_type in ('folder', 'snippet') and row.has_children:
                row_container = row.label_text
            
            # Check if this row matches any item to add
            if not row.has_children:
                row_name = row.label_text
                row_type = row.item_type
                
                # Try exact match with container first
                exact_key = (row_name, row_type, row_container)
                # Also get container from row's data
                row_data_container = row.data.get('snippet') or row.data.get('folder')
                data_key = (row_name, row_type, row_data_container)
                
                matched_key = None
                if exact_key in items_to_add:
                    matched_key = exact_key
                elif data_key in items_to_add:
                    matched_key = data_key
                else:
                    # Fallback: match by name and type only IF the item has no container specified
                    # This prevents matching items in the wrong folder/snippet
                    for key in list(items_to_add.keys()):
                        item_name, item_type_key, item_container = key
                        if item_name == row_name and item_type_key == row_type:
                            # Only use fallback if NO container was specified in the request
                            if item_container is None:
                                matched_key = key
                                break
                            # Otherwise skip - we need an exact container match
                
                if matched_key:
                    item_info = items_to_add[matched_key]
                    if not row.is_checked():
                        container_info = row_data_container or row_container or 'unknown'
                        logger.info(f"  ✓ Selecting: {row_type} '{row_name}' from '{container_info}'")
                        row.set_checked(True)
                    
                    # Apply target destination if specified (from dependency resolution)
                    target_dest = item_info.get('target_destination')
                    if target_dest:
                        dest_folder = target_dest.get('folder', '')
                        is_existing_snippet = target_dest.get('is_existing_snippet', False)
                        is_new_snippet = target_dest.get('is_new_snippet', False)
                        
                        logger.info(f"    → Setting destination: {dest_folder} "
                                   f"(existing_snippet={is_existing_snippet}, new_snippet={is_new_snippet})")
                        
                        # Set the destination on the row
                        if hasattr(row, 'set_destination'):
                            row.set_destination(dest_folder, is_existing_snippet, is_new_snippet)
                        elif hasattr(row, '_destination_folder'):
                            # Fallback: directly set internal state
                            row._destination_folder = dest_folder
                            if hasattr(row, '_is_existing_snippet'):
                                row._is_existing_snippet = is_existing_snippet
                            if hasattr(row, '_is_new_snippet'):
                                row._is_new_snippet = is_new_snippet
                    
                    items_to_add.pop(matched_key, None)  # Remove from list once found
            
            # Recurse into children
            for child in row.get_children():
                find_and_check_rows(child, row_container)
        
        # Search through all rows
        for row in self._top_rows:
            find_and_check_rows(row)
        
        # Log any items not found
        if items_to_add:
            logger.warning(f"Could not find rows for {len(items_to_add)} items:")
            for (name, item_type, container) in items_to_add.keys():
                logger.warning(f"  - {item_type}: {name} (container: {container})")
