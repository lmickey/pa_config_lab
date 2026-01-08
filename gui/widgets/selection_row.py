"""
Selection Row Widget - Card-style row for hierarchical selection.

This module provides a card/button-style row widget for the push selection screen.
Each row has:
- Expand/collapse indicator (for items with children)
- Checkbox for selection
- Label
- Chevron for detail panel
"""

import logging
from typing import Optional, Dict, Any, List, Callable

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QPushButton,
    QFrame,
    QSizePolicy,
    QLineEdit,
    QComboBox,
    QTextEdit,
    QScrollArea,
    QRadioButton,
    QButtonGroup,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from gui.widgets.no_scroll_combo import NoScrollComboBox

logger = logging.getLogger(__name__)


class SelectionRow(QFrame):
    """
    A card-style row widget for hierarchical selection.
    
    Features:
    - Expand/collapse triangle for items with children
    - Tri-state checkbox for selection
    - Item label
    - Chevron (>) to open detail panel
    - Detail panel with metadata, destination settings, and config preview
    """
    
    # Signals
    selection_changed = pyqtSignal(object, bool)  # (row, is_checked)
    expanded_changed = pyqtSignal(object, bool)   # (row, is_expanded)
    detail_changed = pyqtSignal(object)           # (row) - when detail settings change
    
    # Indentation per level (pixels)
    INDENT_PER_LEVEL = 24
    
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
    
    # Folders that cannot be pushed to (read-only or special)
    # Use lowercase for case-insensitive matching
    # Folders that cannot be pushed to (read-only or special)
    # Include variations (space vs hyphen) and exact names as they appear
    NON_EDITABLE_FOLDERS = {
        'ngfw-shared',
        'colo-connect', 'colo connect',
        'service-connections', 'service connections',
        'remote-networks', 'remote networks',
        'predefined', 'default',
    }
    
    # Note: Snippets are pre-filtered by type='Custom' in selection_list.py
    # This set is kept empty - all snippets passed here are already editable
    DEFAULT_SNIPPETS = set()
    
    def __init__(
        self,
        label: str,
        item_type: str,
        data: Optional[Dict[str, Any]] = None,
        level: int = 0,
        has_children: bool = False,
        parent_widget: Optional[QWidget] = None,
        available_folders: Optional[List[str]] = None,
        available_snippets: Optional[List[str]] = None,
        default_push_strategy: str = "skip",
        config_metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the selection row.
        
        Args:
            label: Display label for the row
            item_type: Type of item (folder, snippet, rule, object, etc.)
            data: The configuration data for this item
            level: Hierarchy level (0 = top level)
            has_children: Whether this row has child rows
            parent_widget: Parent widget reference
            available_folders: List of available destination folders
            available_snippets: List of available destination snippets
            default_push_strategy: Default push strategy (skip/overwrite/rename)
            config_metadata: Config-level metadata (tenant name, version, dates)
        """
        super().__init__(parent_widget)
        
        self.label_text = label
        self.item_type = item_type
        self.data = data or {}
        self.level = level
        self.has_children = has_children
        self.available_folders = available_folders or []
        self.available_snippets = available_snippets or []
        self.default_push_strategy = default_push_strategy
        self.config_metadata = config_metadata or {}
        
        # State
        self._is_expanded = False
        self._is_checked = False
        self._is_partial = False  # For tri-state
        self._detail_visible = False
        self._children: List['SelectionRow'] = []
        self._parent_row: Optional['SelectionRow'] = None
        
        # Destination settings (per-item overrides)
        # Use special "inherit" value to indicate inheriting from parent
        self._destination_folder = "inherit"  # Default to inherit from parent
        self._destination_name = self.data.get('name', label)
        self._push_strategy = default_push_strategy
        self._is_dest_new_snippet = False  # Track if destination is a new/renamed snippet
        self._dest_is_existing_snippet = False  # Track if destination is an existing snippet (not folder)
        
        # Track original values to detect customization
        self._original_folder = self.data.get('folder', '')
        self._original_name = self.data.get('name', label)
        self._original_strategy = default_push_strategy
        
        # Customization state
        self._is_customized = False
        
        # Click cycle state for containers: 0=collapsed, 1=children expanded, 2=detail expanded
        self._click_cycle_state = 0
        
        self._init_ui()
        self._apply_styles()
    
    def _init_ui(self):
        """Initialize the user interface."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # === Header Row (the clickable card) ===
        self.header_frame = QFrame()
        self.header_frame.setObjectName("headerFrame")
        self.header_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(8, 8, 8, 8)
        header_layout.setSpacing(8)
        
        # Left indent based on level
        if self.level > 0:
            indent_spacer = QWidget()
            indent_spacer.setFixedWidth(self.level * self.INDENT_PER_LEVEL)
            header_layout.addWidget(indent_spacer)
        
        # Determine item characteristics
        # Leaf items: no children, has config data (name)
        # Container items: has children (folders, snippets containers, object type containers)
        # Top-level containers (folder, snippet): should have destination options AND rename capability
        # Intermediate containers (objects_container, object_type, etc.): destination options but NO rename
        self._is_leaf_item = not self.has_children and bool(self.data.get('name'))
        
        # Containers that can be renamed (folder name stays, but snippet can be renamed)
        self._is_renameable_container = self.item_type == 'snippet' and self.has_children
        
        # Containers that should have destination/strategy options (all containers with children)
        # This includes: folder, snippet, objects_container, profiles_container, object_type, profile_type, etc.
        CONFIGURABLE_CONTAINER_TYPES = {
            'folder', 'snippet',  # Top-level
            'objects_container', 'profiles_container', 'hip_container',  # Category containers
            'object_type', 'profile_type',  # Type containers (e.g., "Application Group", "Address")
        }
        self._is_configurable_container = self.has_children and self.item_type in CONFIGURABLE_CONTAINER_TYPES
        
        # Also make any container with children configurable if it has a reasonable type
        # This catches custom type names like specific object types used as containers
        if self.has_children and not self._is_configurable_container:
            # If this container has children, allow configuration for strategy/location
            self._is_configurable_container = True
        
        self._has_detail_panel = self._is_leaf_item or self._is_configurable_container
        
        if self.has_children:
            # Container: show expand/collapse arrow
            self.expand_btn = QPushButton("▶")
            self.expand_btn.setFixedSize(24, 24)
            self.expand_btn.setObjectName("expandBtn")
            self.expand_btn.clicked.connect(self._toggle_expanded)
            header_layout.addWidget(self.expand_btn)
            
            # For configurable containers (folder/snippet), also show chevron for detail panel
            if self._is_configurable_container:
                self.chevron_btn = QPushButton("›")
                self.chevron_btn.setFixedSize(24, 24)
                self.chevron_btn.setObjectName("chevronBtn")
                self.chevron_btn.clicked.connect(self._toggle_detail)
                header_layout.addWidget(self.chevron_btn)
            else:
                self.chevron_btn = None
        elif self._is_leaf_item:
            # Leaf item with data: show chevron (detail toggle) on the left
            self.chevron_btn = QPushButton("›")
            self.chevron_btn.setFixedSize(24, 24)
            self.chevron_btn.setObjectName("chevronBtn")
            self.chevron_btn.clicked.connect(self._toggle_detail)
            header_layout.addWidget(self.chevron_btn)
            
            # No expand button for leaf items
            self.expand_btn = None
        else:
            # Neither container nor leaf (e.g., intermediate nodes without data)
            # Add spacer to maintain alignment
            spacer = QWidget()
            spacer.setFixedWidth(24)
            header_layout.addWidget(spacer)
            self.expand_btn = None
            self.chevron_btn = None
        
        # Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setTristate(True)
        self.checkbox.stateChanged.connect(self._on_checkbox_changed)
        header_layout.addWidget(self.checkbox)
        
        # Label
        self.label = QLabel(self.label_text)
        self.label.setObjectName("rowLabel")
        header_layout.addWidget(self.label)
        
        # Type badge
        self.type_badge = QLabel(self._format_type_badge())
        self.type_badge.setObjectName("typeBadge")
        header_layout.addWidget(self.type_badge)
        
        # Status indicators (inherit/customized)
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        self._update_status_indicator()
        header_layout.addWidget(self.status_label)
        
        # Stretch to push count to right
        header_layout.addStretch()
        
        # Item count (for containers)
        self.count_label = QLabel("")
        self.count_label.setObjectName("countLabel")
        header_layout.addWidget(self.count_label)
        
        self.main_layout.addWidget(self.header_frame)
        
        # === Detail Panel (hidden by default) ===
        self.detail_panel = QFrame()
        self.detail_panel.setObjectName("detailPanel")
        self.detail_panel.setVisible(False)
        self._build_detail_panel()
        self.main_layout.addWidget(self.detail_panel)
        
        # === Children Container (hidden by default) ===
        self.children_container = QWidget()
        self.children_layout = QVBoxLayout(self.children_container)
        self.children_layout.setContentsMargins(0, 0, 0, 0)
        self.children_layout.setSpacing(2)
        self.children_container.setVisible(False)
        self.main_layout.addWidget(self.children_container)
        
        # Connect header click to expand (but not checkbox or chevron areas)
        self.header_frame.mousePressEvent = self._on_header_click
    
    def _build_detail_panel(self):
        """Build the detail panel with three columns."""
        detail_layout = QHBoxLayout(self.detail_panel)
        detail_layout.setContentsMargins(16 + (self.level * self.INDENT_PER_LEVEL), 12, 16, 12)
        detail_layout.setSpacing(20)
        
        # === Left Column: Metadata ===
        left_frame = QFrame()
        left_frame.setObjectName("metadataFrame")
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(4)
        
        left_title = QLabel("<b>Source</b>")
        left_layout.addWidget(left_title)
        
        # Source tenant name
        tenant_name = self.config_metadata.get('source_tenant', '')
        if tenant_name:
            tenant_label = QLabel(f"🏢 <b>Tenant:</b> {tenant_name}")
            tenant_label.setStyleSheet("font-size: 11px;")
            left_layout.addWidget(tenant_label)
        
        # Determine source container (folder or snippet)
        source_folder = self.data.get('folder', '')
        source_snippet = self.data.get('snippet', '')
        
        if source_folder:
            location_label = QLabel(f"📁 <b>Location:</b> {source_folder}")
        elif source_snippet:
            location_label = QLabel(f"📄 <b>Location:</b> {source_snippet}")
        else:
            # For infrastructure items, show the required folder
            infra_folders = {
                'remote_network': 'Remote Networks',
                'service_connection': 'Service Connections',
                'ipsec_tunnel': 'Remote Networks / Service Connections',
                'ike_gateway': 'Remote Networks / Service Connections',
                'ike_crypto_profile': 'Remote Networks / Service Connections',
                'ipsec_crypto_profile': 'Remote Networks / Service Connections',
                'agent_profile': 'Mobile Users',
                'bandwidth_allocation': 'Remote Networks',
            }
            infra_folder = infra_folders.get(self.item_type, '')
            if infra_folder:
                location_label = QLabel(f"🏗️ <b>Location:</b> {infra_folder}")
            else:
                location_label = QLabel("")
        
        location_label.setStyleSheet("font-size: 11px;")
        left_layout.addWidget(location_label)
        
        # Program version
        version = self.config_metadata.get('program_version', '')
        if version:
            version_label = QLabel(f"📦 <b>Version:</b> {version}")
            version_label.setStyleSheet("font-size: 11px;")
            left_layout.addWidget(version_label)
        
        # Date - prefer item-level metadata, fall back to config-level
        item_created = self.data.get('metadata', {}).get('created', '')
        item_updated = self.data.get('metadata', {}).get('updated', '')
        config_created = self.config_metadata.get('created_at', '')
        config_modified = self.config_metadata.get('modified_at', '')
        
        # Use item date if available, else config date
        display_date = item_updated or item_created or config_modified or config_created
        if display_date:
            # Format the date nicely
            try:
                from datetime import datetime
                if 'T' in display_date:
                    dt = datetime.fromisoformat(display_date.replace('Z', '+00:00'))
                    display_date = dt.strftime('%Y-%m-%d %H:%M')
            except:
                pass  # Use raw date if parsing fails
            
            date_label = QLabel(f"📅 <b>Pulled:</b> {display_date}")
            date_label.setStyleSheet("font-size: 11px;")
            left_layout.addWidget(date_label)
        
        left_layout.addStretch()
        detail_layout.addWidget(left_frame, stretch=1)
        
        # === Center Column: Destination Settings ===
        center_frame = QFrame()
        center_frame.setObjectName("destinationFrame")
        center_layout = QVBoxLayout(center_frame)
        center_layout.setContentsMargins(12, 12, 12, 12)
        center_layout.setSpacing(8)
        
        center_title = QLabel("<b>Destination</b>")
        center_layout.addWidget(center_title)
        
        # Item name (editable for leaf items and renameable containers like snippets)
        # For intermediate containers (Objects, Addresses, etc.), show but disable
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Name:"))
        self.dest_name_edit = QLineEdit(self.data.get('name', self.label_text))
        self.dest_name_edit.textChanged.connect(self._on_destination_changed)
        
        # Disable name editing for containers that can't be renamed
        # Only snippet containers and leaf items can have their names changed
        can_rename = self._is_leaf_item or self._is_renameable_container
        if not can_rename:
            self.dest_name_edit.setEnabled(False)
            self.dest_name_edit.setStyleSheet("background-color: #f5f5f5; color: #888;")
            self.dest_name_edit.setToolTip("Container names cannot be changed")
        
        name_row.addWidget(self.dest_name_edit, stretch=1)
        center_layout.addLayout(name_row)
        
        # Push strategy dropdown - second row
        strategy_row = QHBoxLayout()
        strategy_row.addWidget(QLabel("Strategy:"))
        self.strategy_combo = NoScrollComboBox()
        self.strategy_combo.addItems(["Skip", "Overwrite", "Rename"])
        self.strategy_combo.setCurrentText(self.default_push_strategy.capitalize())
        self.strategy_combo.currentTextChanged.connect(self._on_destination_changed)
        strategy_row.addWidget(self.strategy_combo, stretch=1)
        center_layout.addLayout(strategy_row)
        
        # Destination location dropdown
        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Location:"))
        self.dest_folder_combo = NoScrollComboBox()
        self._populate_location_dropdown()
        self.dest_folder_combo.currentIndexChanged.connect(self._on_location_changed)
        folder_row.addWidget(self.dest_folder_combo, stretch=1)
        center_layout.addLayout(folder_row)
        
        # Dependency options (shown only for leaf items when "New Snippet" selected)
        # Containers don't need this - they include all their children automatically
        # Uses radio buttons - only one option can be selected
        self.dependency_widget = QWidget()
        dependency_layout = QVBoxLayout(self.dependency_widget)
        dependency_layout.setContentsMargins(0, 4, 0, 0)
        dependency_layout.setSpacing(2)
        
        # Radio button group for dependency handling
        self.dependency_button_group = QButtonGroup(self)
        
        self.include_deps_radio = QRadioButton("Include Dependencies")
        self.include_deps_radio.setChecked(True)  # Default: include dependencies
        self.include_deps_radio.setToolTip("Pull required dependencies into the new snippet")
        self.include_deps_radio.setStyleSheet("font-size: 11px;")
        self.dependency_button_group.addButton(self.include_deps_radio, 0)
        dependency_layout.addWidget(self.include_deps_radio)
        
        self.create_dups_radio = QRadioButton("Create Duplicates")
        self.create_dups_radio.setToolTip("Create duplicate objects instead of referencing existing ones")
        self.create_dups_radio.setStyleSheet("font-size: 11px;")
        self.dependency_button_group.addButton(self.create_dups_radio, 1)
        dependency_layout.addWidget(self.create_dups_radio)
        
        self.dependency_widget.setVisible(False)
        # Only show dependency options for leaf items (not containers)
        # Containers automatically include all dependencies (their children)
        if self._is_configurable_container:
            self.dependency_widget.setEnabled(False)
        center_layout.addWidget(self.dependency_widget)
        
        # New Snippet Name textbox (hidden by default, shown when "New Snippet" selected)
        # Appears above the object name when creating a new snippet
        self.new_snippet_widget = QWidget()
        new_snippet_layout = QHBoxLayout(self.new_snippet_widget)
        new_snippet_layout.setContentsMargins(0, 0, 0, 0)
        self.new_snippet_label = QLabel("Snippet Name:")
        self.new_snippet_edit = QLineEdit()
        self.new_snippet_edit.setPlaceholderText("Enter new snippet name...")
        self.new_snippet_edit.setMaxLength(55)  # Prisma Access name limit
        self.new_snippet_edit.textChanged.connect(self._on_destination_changed)
        new_snippet_layout.addWidget(self.new_snippet_label)
        new_snippet_layout.addWidget(self.new_snippet_edit, stretch=1)
        self.new_snippet_widget.setVisible(False)
        center_layout.addWidget(self.new_snippet_widget)
        
        center_layout.addStretch()
        detail_layout.addWidget(center_frame, stretch=1)
        
        # === Right Column: Config Preview (only for leaf items, not containers) ===
        if self._is_leaf_item:
            right_frame = QFrame()
            right_frame.setObjectName("configFrame")
            right_layout = QVBoxLayout(right_frame)
            right_layout.setContentsMargins(12, 12, 12, 12)
            right_layout.setSpacing(8)
            
            right_title = QLabel("<b>Configuration</b>")
            right_layout.addWidget(right_title)
            
            # Config preview (key=value pairs)
            self.config_preview = QTextEdit()
            self.config_preview.setReadOnly(True)
            self.config_preview.setFont(QFont("Courier New", 9))
            self.config_preview.setPlainText(self._format_config_preview())
            self.config_preview.setMinimumHeight(120)
            right_layout.addWidget(self.config_preview, stretch=1)
            
            detail_layout.addWidget(right_frame, stretch=2)
        elif self._is_configurable_container:
            # For containers, show a summary/help panel instead
            right_frame = QFrame()
            right_frame.setObjectName("configFrame")
            right_layout = QVBoxLayout(right_frame)
            right_layout.setContentsMargins(12, 12, 12, 12)
            right_layout.setSpacing(8)
            
            right_title = QLabel("<b>Container Settings</b>")
            right_layout.addWidget(right_title)
            
            help_text = QLabel(
                "💡 <b>Tip:</b> Changes to this container's destination "
                "will apply to all items within it.<br><br>"
                "• Select a new location to move all items<br>"
                "• Create a new snippet to group items together<br>"
                "• Child items can still override these settings"
            )
            help_text.setWordWrap(True)
            help_text.setStyleSheet("color: #666; padding: 8px; background: #f5f5f5; border-radius: 4px;")
            right_layout.addWidget(help_text)
            
            right_layout.addStretch()
            detail_layout.addWidget(right_frame, stretch=2)
            self.config_preview = None
        else:
            self.config_preview = None
    
    def _get_display_name(self, name: str) -> str:
        """Get display name for a folder/snippet (e.g., 'All' -> 'Global')."""
        return self.FOLDER_DISPLAY_NAMES.get(name, name)
    
    def _is_editable_destination(self, name: str, is_snippet: bool = False) -> bool:
        """Check if a folder/snippet can be used as a push destination."""
        if not name:
            return False
        
        # Normalize: lowercase and replace hyphens with spaces for comparison
        normalized = name.lower().replace('-', ' ')
        
        blocklist = self.DEFAULT_SNIPPETS if is_snippet else self.NON_EDITABLE_FOLDERS
        
        for blocked in blocklist:
            blocked_normalized = blocked.lower().replace('-', ' ')
            if normalized == blocked_normalized:
                return False
        
        return True
    
    def _populate_location_dropdown(self):
        """Populate the location dropdown with appropriate options.
        
        Before destination tenant is connected:
        - Inherit from Parent
        - Original location
        - New Snippet (or Rename Snippet for snippet containers)
        
        After destination tenant is connected:
        - (above) + separator + filtered destination folders/snippets
        """
        self.dest_folder_combo.blockSignals(True)
        self.dest_folder_combo.clear()
        
        # Check if this is a snippet container (top-level snippet with children)
        is_snippet_container = self.item_type == 'snippet' and self.has_children
        
        # 1. Inherit from Parent (default)
        self.dest_folder_combo.addItem("⬆ Inherit from Parent", "inherit")
        
        # 2. Original location (the location this item was pulled from)
        source_folder = self.data.get('folder', '')
        source_snippet = self.data.get('snippet', '')
        current_location = source_folder or source_snippet or ''
        is_source_snippet = bool(source_snippet and not source_folder)
        
        if current_location:
            display_name = self._get_display_name(current_location)
            # Use document emoji for snippets, folder emoji for folders
            location_emoji = "📄" if is_source_snippet else "📁"
            self.dest_folder_combo.addItem(f"{location_emoji} {display_name} (original)", current_location)
        
        # 3. New Snippet or Rename Snippet option
        # For snippet containers: "Rename Snippet" which appends "-copy" to the name
        # For other items: "New Snippet" which allows creating a new snippet
        if is_snippet_container:
            self.dest_folder_combo.addItem("✏️ Rename Snippet", "rename_snippet")
        else:
            self.dest_folder_combo.addItem("➕ New Snippet", "new_snippet")
        
        # Only add destination folders/snippets if they have been provided
        # (i.e., after destination tenant is connected)
        # Double filter: first by editable, then by not being current location
        filtered_folders = []
        for f in self.available_folders:
            if f and f != current_location and self._is_editable_destination(f, is_snippet=False):
                filtered_folders.append(f)
        
        filtered_snippets = []
        for s in self.available_snippets:
            if s and s != current_location and self._is_editable_destination(s, is_snippet=True):
                filtered_snippets.append(s)
        
        logger.debug(f"_populate_location_dropdown: available_folders={len(self.available_folders)}, "
                    f"available_snippets={len(self.available_snippets)}, "
                    f"filtered_folders={len(filtered_folders)}, filtered_snippets={len(filtered_snippets)}")
        
        if filtered_folders or filtered_snippets:
            # 4. Separator before destination folders
            self.dest_folder_combo.insertSeparator(self.dest_folder_combo.count())
            
            # 5. Available destination folders (filtered)
            for folder in filtered_folders:
                display_name = self._get_display_name(folder)
                self.dest_folder_combo.addItem(f"📁 {display_name}", folder)
            
            # 6. Available destination snippets (filtered)
            for snippet in filtered_snippets:
                self.dest_folder_combo.addItem(f"📄 {snippet}", snippet)
        
        # Default to "Inherit from Parent"
        self.dest_folder_combo.setCurrentIndex(0)
        self.dest_folder_combo.blockSignals(False)
    
    def _on_location_changed(self, index):
        """Handle location dropdown change."""
        location_value = self.dest_folder_combo.currentData()
        location_text = self.dest_folder_combo.currentText()
        
        # Check if this is a snippet container
        is_snippet_container = self.item_type == 'snippet' and self.has_children
        
        # Show/hide new snippet options
        # For "new_snippet": show snippet name field for non-snippet-containers
        # For "rename_snippet": don't show snippet name field (name derived from original + "-copy")
        is_new_snippet = (location_value == "new_snippet")
        is_rename_snippet = (location_value == "rename_snippet")
        
        # Track if destination is an existing snippet (not folder)
        # Snippets in dropdown have 📄 prefix in display text
        self._dest_is_existing_snippet = location_text.startswith("📄 ") if location_text else False
        
        # Show snippet name field for "new_snippet" but NOT for snippet containers (rename)
        # Snippet containers use the original name + "-copy" automatically
        show_snippet_field = is_new_snippet and not is_snippet_container
        self.new_snippet_widget.setVisible(show_snippet_field)
        
        # Only show dependency options for leaf items, not containers
        # Containers automatically include all their children (dependencies)
        show_deps = is_new_snippet and self._is_leaf_item
        self.dependency_widget.setVisible(show_deps)
        
        # Trigger general destination change handling
        self._on_destination_changed()
    
    def _format_type_badge(self) -> str:
        """Format the type badge text."""
        type_map = {
            'folder': '📁',
            'snippet': '📄',
            'security_rule': '🔒',
            'rule': '🔒',
            'address': '📍',
            'address_group': '📍',
            'service': '🔌',
            'service_group': '🔌',
            'application': '📱',
            'application_group': '📱',
            'application_filter': '🔍',
            'tag': '🏷️',
            'schedule': '📅',
            'infrastructure': '🏗️',
            'remote_network': '🌐',
            'service_connection': '🔗',
            'ipsec_tunnel': '🔐',
            'ike_gateway': '🚪',
            'agent_profile': '👤',
        }
        icon = type_map.get(self.item_type, '📦')
        return f"{icon} {self.item_type.replace('_', ' ').title()}"
    
    # Keys to exclude from config preview (metadata and internal fields)
    EXCLUDED_CONFIG_KEYS = {
        'id', 'folder', 'snippet', 'is_default', 'item_type', 
        'push_strategy', '_pull_date', '_source', '_metadata',
        'position', 'device_group', 'type',  # Common metadata fields
        'deleted', 'delete_success',  # Delete operation fields
        'metadata',  # Metadata block (created, updated, created_by, updated_by)
    }
    
    def _format_config_preview(self) -> str:
        """Format config data as key=value pairs, excluding metadata fields."""
        if not self.data:
            return "No configuration data"
        
        lines = []
        for key, value in self.data.items():
            # Skip internal/metadata keys (starting with _ or in exclusion list)
            if key.startswith('_') or key in self.EXCLUDED_CONFIG_KEYS:
                continue
            
            # Format value
            if isinstance(value, dict):
                # Only show non-empty dicts
                if value:
                    lines.append(f"{key}:")
                    for k, v in value.items():
                        if not k.startswith('_'):
                            lines.append(f"  {k} = {v}")
            elif isinstance(value, list):
                if len(value) == 0:
                    continue
                elif len(value) <= 3:
                    # Show simple representation for short lists
                    simple_items = []
                    for item in value:
                        if isinstance(item, dict):
                            simple_items.append(item.get('name', item.get('member', str(item))))
                        else:
                            simple_items.append(str(item))
                    lines.append(f"{key} = {simple_items}")
                else:
                    lines.append(f"{key} = [{len(value)} items]")
            else:
                lines.append(f"{key} = {value}")
        
        return "\n".join(lines) if lines else "No configuration data"
    
    def _apply_styles(self):
        """Apply CSS styles to the widget."""
        self.setStyleSheet("""
            SelectionRow {
                background: transparent;
            }
            
            #headerFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                margin: 2px 0;
            }
            
            #headerFrame:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            
            #expandBtn {
                background: transparent;
                border: none;
                font-size: 12px;
                color: #495057;
            }
            
            #expandBtn:hover {
                background-color: #dee2e6;
                border-radius: 4px;
            }
            
            #rowLabel {
                font-size: 13px;
                font-weight: 500;
                color: #212529;
            }
            
            #typeBadge {
                font-size: 11px;
                color: #6c757d;
                padding: 2px 8px;
                background-color: #e9ecef;
                border-radius: 10px;
            }
            
            #countLabel {
                font-size: 11px;
                color: #6c757d;
                padding: 2px 6px;
            }
            
            #chevronBtn {
                background: transparent;
                border: none;
                font-size: 20px;
                font-weight: bold;
                color: #6c757d;
            }
            
            #chevronBtn:hover {
                color: #495057;
                background-color: #dee2e6;
                border-radius: 4px;
            }
            
            #detailPanel {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-top: none;
                border-radius: 0 0 6px 6px;
                margin: 0 2px 2px 2px;
            }
            
            #metadataFrame, #destinationFrame, #configFrame {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 4px;
            }
            
            QComboBox, QLineEdit {
                padding: 6px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: white;
                color: #333333;
            }
            
            QComboBox:hover, QLineEdit:hover {
                border-color: #80bdff;
            }
            
            QComboBox QAbstractItemView {
                background-color: white;
                color: #333333;
                selection-background-color: #4CAF50;
                selection-color: white;
                border: 1px solid #ced4da;
            }
            
            QComboBox QAbstractItemView::item {
                padding: 6px;
                color: #333333;
            }
            
            QComboBox QAbstractItemView::item:hover {
                background-color: #e8f5e9;
                color: #333333;
            }
            
            QTextEdit {
                border: 1px solid #e9ecef;
                border-radius: 4px;
                background-color: #f8f9fa;
            }
        """)
    
    def _on_header_click(self, event):
        """Handle click on header row."""
        # Get click position relative to header
        click_x = event.pos().x()
        
        # Calculate the end of the left control area (indent + button + spacing)
        left_control_end = (self.level * self.INDENT_PER_LEVEL) + 24 + 8
        # Add checkbox width
        checkbox_end = left_control_end + 24
        
        if click_x < left_control_end:
            # Clicked on chevron/expand button area - let button handle it
            return
        
        if click_x < checkbox_end:
            # Clicked on checkbox area - let checkbox handle it
            return
        
        # For leaf items (config objects), clicking anywhere toggles detail panel
        if self._is_leaf_item:
            self._toggle_detail()
        elif self.has_children:
            # For containers: cycle through states
            # State 0 (collapsed) -> State 1 (children expanded)
            # State 1 (children expanded) -> State 2 (detail also expanded)
            # State 2 (both expanded) -> State 0 (both collapsed)
            self._cycle_container_expansion()
    
    def _cycle_container_expansion(self):
        """
        Cycle through container expansion states.
        
        For containers (folders/snippets with children):
        - State 0: Both collapsed
        - State 1: Children expanded, detail collapsed
        - State 2: Both expanded
        
        Click cycle: 0 -> 1 -> 2 -> 0
        """
        # Only applies to configurable containers (folder/snippet with chevron)
        if self._is_configurable_container:
            if self._click_cycle_state == 0:
                # Expand children only
                self._click_cycle_state = 1
                if not self._is_expanded:
                    self._is_expanded = True
                    self.expand_btn.setText("▼")
                    self.children_container.setVisible(True)
                    self.expanded_changed.emit(self, True)
            elif self._click_cycle_state == 1:
                # Also expand detail panel
                self._click_cycle_state = 2
                if not self._detail_visible:
                    self._detail_visible = True
                    self.detail_panel.setVisible(True)
                    if self.chevron_btn:
                        self.chevron_btn.setText("⌄")
            else:
                # Collapse both
                self._click_cycle_state = 0
                if self._is_expanded:
                    self._is_expanded = False
                    self.expand_btn.setText("▶")
                    self.children_container.setVisible(False)
                    self.expanded_changed.emit(self, False)
                if self._detail_visible:
                    self._detail_visible = False
                    self.detail_panel.setVisible(False)
                    if self.chevron_btn:
                        self.chevron_btn.setText("›")
        else:
            # Non-configurable container: just toggle expand
            self._toggle_expanded()
    
    def _toggle_expanded(self):
        """Toggle the expanded state."""
        self._is_expanded = not self._is_expanded
        self.expand_btn.setText("▼" if self._is_expanded else "▶")
        self.children_container.setVisible(self._is_expanded)
        self.expanded_changed.emit(self, self._is_expanded)
    
    def _toggle_detail(self):
        """Toggle the detail panel visibility."""
        self._detail_visible = not self._detail_visible
        self.detail_panel.setVisible(self._detail_visible)
        if self.chevron_btn:
            self.chevron_btn.setText("⌄" if self._detail_visible else "›")
    
    def _on_checkbox_changed(self, state):
        """Handle checkbox state change."""
        # When user clicks checkbox, treat PartiallyChecked as wanting to check
        # (User clicking a partial checkbox should fully select, not partial)
        if state == Qt.CheckState.PartiallyChecked.value:
            # User clicked a partial checkbox - convert to fully checked
            self.checkbox.blockSignals(True)
            self.checkbox.setCheckState(Qt.CheckState.Checked)
            self.checkbox.blockSignals(False)
            state = Qt.CheckState.Checked.value
        
        self._is_checked = state == Qt.CheckState.Checked.value
        self._is_partial = False  # User action always results in definite state
        
        # Update children
        for child in self._children:
            child.set_checked(self._is_checked)
        
        # Collapse children when unchecking
        if not self._is_checked and self._is_expanded:
            self._collapse_recursive()
        
        # Emit signal
        self.selection_changed.emit(self, self._is_checked)
        
        # Update parent
        if self._parent_row:
            self._parent_row._update_check_state_from_children()
    
    def _collapse_recursive(self):
        """Collapse this row and all children recursively."""
        if self._is_expanded:
            self._is_expanded = False
            self.expand_btn.setText("▶")
            self.children_container.setVisible(False)
            self.expanded_changed.emit(self, False)
        
        # Also collapse all children
        for child in self._children:
            child._collapse_recursive()
    
    def _on_destination_changed(self, *args):
        """Handle changes to destination settings."""
        old_folder = self._destination_folder
        old_strategy = self._push_strategy
        old_name = getattr(self, '_destination_name', self._original_name)
        
        # Get folder value from combo data (not display text)
        self._destination_folder = self.dest_folder_combo.currentData() or "inherit"
        self._destination_name = self.dest_name_edit.text()
        self._push_strategy = self.strategy_combo.currentText().lower()
        
        # Auto-append "-copy" when Rename strategy is selected (if name hasn't been manually changed)
        if self._push_strategy == 'rename' and old_strategy != 'rename':
            # Only append if current name equals original (user hasn't edited it)
            if self._destination_name == self._original_name:
                self.dest_name_edit.blockSignals(True)
                self._destination_name = f"{self._original_name}-copy"
                self.dest_name_edit.setText(self._destination_name)
                self.dest_name_edit.blockSignals(False)
        elif self._push_strategy != 'rename' and old_strategy == 'rename':
            # Revert to original name if switching away from Rename and name ends with -copy
            if self._destination_name == f"{self._original_name}-copy":
                self.dest_name_edit.blockSignals(True)
                self._destination_name = self._original_name
                self.dest_name_edit.setText(self._destination_name)
                self.dest_name_edit.blockSignals(False)
        
        # For snippet containers: Auto-select "Rename Snippet" when name is changed
        # This must happen AFTER the rename strategy auto-appends "-copy" so we detect the name change
        is_snippet_container = self.item_type == 'snippet' and self.has_children
        if is_snippet_container and self._destination_name != old_name:
            # User changed the name - auto-select "Rename Snippet" if not already
            if self._destination_folder not in ("rename_snippet", "new_snippet"):
                logger.debug(f"Auto-selecting 'Rename Snippet' for container '{self.label_text}' because name changed")
                # Find and select "Rename Snippet" option
                for i in range(self.dest_folder_combo.count()):
                    if self.dest_folder_combo.itemData(i) == "rename_snippet":
                        self.dest_folder_combo.blockSignals(True)
                        self.dest_folder_combo.setCurrentIndex(i)
                        self._destination_folder = "rename_snippet"
                        self.dest_folder_combo.blockSignals(False)
                        break
        
        # Update customization state
        self._update_customization_state()
        
        # Auto-select this item for push when any changes are made
        if self._is_customized and not self._is_checked:
            self.set_checked(True)
            # Emit selection change so parents are updated
            self.selection_changed.emit(self, True)
        
        # Update parent status indicators (propagate up)
        self._update_parent_status_indicators()
        
        # Propagate folder change to children (only if not inherit)
        if old_folder != self._destination_folder and self._children:
            if self._destination_folder != "inherit":
                self._propagate_folder_to_children(self._destination_folder)
        
        # For folder/snippet containers, also propagate the destination folder to all children
        # This allows changing all children's destination when renaming a snippet
        if self._is_configurable_container and self._children:
            self._propagate_container_settings_to_children()
        
        self.detail_changed.emit(self)
    
    def _update_parent_status_indicators(self):
        """Update status indicators on all parent rows."""
        if self._parent_row:
            self._parent_row._update_status_indicator()
            self._parent_row._update_parent_status_indicators()
    
    def _update_customization_state(self):
        """Update whether this item has customized settings."""
        # Check if any setting differs from defaults
        folder_changed = self._destination_folder != "inherit"
        name_changed = self._destination_name != self._original_name
        strategy_changed = self._push_strategy != self._original_strategy
        
        self._is_customized = folder_changed or name_changed or strategy_changed
        self._update_status_indicator()
    
    def _update_status_indicator(self):
        """Update the status label in the header."""
        if not hasattr(self, 'status_label'):
            return
        
        # For leaf items with config data, show status
        if self._is_leaf_item:
            if self._is_customized:
                self.status_label.setText("⚙ customized")
                self.status_label.setStyleSheet("color: #FF9800; font-size: 10px; padding: 2px 6px; "
                                                "background-color: #FFF3E0; border-radius: 3px;")
            else:
                self.status_label.setText("↩ inherit")
                self.status_label.setStyleSheet("color: #4CAF50; font-size: 10px; padding: 2px 6px; "
                                                "background-color: #E8F5E9; border-radius: 3px;")
        elif self._is_configurable_container:
            # For configurable containers (folder/snippet), show own status + child tally
            inherited, customized = self._count_child_customization()
            
            if self._is_customized:
                # Container itself is customized
                status_text = "⚙ customized"
                if inherited > 0 or customized > 0:
                    status_text += f" (↩{inherited}|⚙{customized})"
                self.status_label.setText(status_text)
                self.status_label.setStyleSheet("color: #FF9800; font-size: 10px; padding: 2px 6px; "
                                                "background-color: #FFF3E0; border-radius: 3px;")
            elif customized > 0:
                self.status_label.setText(f"↩ {inherited} | ⚙ {customized}")
                self.status_label.setStyleSheet("color: #FF9800; font-size: 10px; padding: 2px 6px; "
                                                "background-color: #FFF3E0; border-radius: 3px;")
            else:
                # All inherited - don't show status
                self.status_label.setText("")
                self.status_label.setStyleSheet("")
        elif self._children:
            # For containers, tally children customization
            inherited, customized = self._count_child_customization()
            
            # Only show status if there are any customized items
            if customized > 0:
                self.status_label.setText(f"↩ {inherited} | ⚙ {customized}")
                self.status_label.setStyleSheet("color: #FF9800; font-size: 10px; padding: 2px 6px; "
                                                "background-color: #FFF3E0; border-radius: 3px;")
            else:
                # All inherited - don't show status (clean look)
                self.status_label.setText("")
                self.status_label.setStyleSheet("")
        else:
            # Empty containers don't show status
            self.status_label.setText("")
            self.status_label.setStyleSheet("")
    
    def _count_child_customization(self) -> tuple:
        """Count inherited vs customized children recursively.
        
        Returns:
            tuple: (inherited_count, customized_count)
        """
        inherited = 0
        customized = 0
        
        for child in self._children:
            if child._children:
                # Recurse into children
                child_inherited, child_customized = child._count_child_customization()
                inherited += child_inherited
                customized += child_customized
            elif child.data.get('name'):
                # Leaf item - check customization
                if child._is_customized:
                    customized += 1
                else:
                    inherited += 1
        
        return inherited, customized
    
    def _propagate_folder_to_children(self, folder: str, is_new_snippet: bool = False, is_existing_snippet: bool = False, strategy: str = None):
        """Propagate destination folder change to all children.
        
        Args:
            folder: The destination folder/snippet name
            is_new_snippet: If True, this is a new snippet being created (rename or new)
            is_existing_snippet: If True, destination is an existing snippet (not folder)
            strategy: Optional strategy to propagate to children
        """
        for child in self._children:
            # Update the child's folder selection
            if folder in child.available_folders or not child.available_folders:
                child.dest_folder_combo.blockSignals(True)
                if folder in [child.dest_folder_combo.itemText(i) for i in range(child.dest_folder_combo.count())]:
                    child.dest_folder_combo.setCurrentText(folder)
                child._destination_folder = folder
                child.dest_folder_combo.blockSignals(False)
            else:
                # Folder not in dropdown (e.g., new snippet) - just set the internal value
                child._destination_folder = folder
            
            # Propagate the new_snippet flag so children know this is a new snippet
            child._is_dest_new_snippet = is_new_snippet
            # Propagate the existing_snippet flag so children know destination is a snippet
            child._dest_is_existing_snippet = is_existing_snippet
            
            # Propagate strategy if provided
            if strategy:
                child.strategy_combo.blockSignals(True)
                child.strategy_combo.setCurrentText(strategy.capitalize())
                child._push_strategy = strategy.lower()
                child.strategy_combo.blockSignals(False)
            
            # Recurse to grandchildren
            child._propagate_folder_to_children(folder, is_new_snippet, is_existing_snippet, strategy)
    
    def _propagate_container_settings_to_children(self):
        """Propagate container's destination settings to all children.
        
        When a folder or snippet container's destination is changed (e.g., rename a snippet),
        update all children's folder/snippet reference to match.
        """
        # Get the destination from this container
        dest_folder = self._destination_folder
        is_new_snippet = False
        is_existing_snippet = getattr(self, '_dest_is_existing_snippet', False)
        
        # For new_snippet, use the new snippet name as the destination
        if dest_folder == "new_snippet" and hasattr(self, 'new_snippet_edit'):
            new_snippet_name = self.new_snippet_edit.text()
            if new_snippet_name:
                dest_folder = new_snippet_name
                is_new_snippet = True
                is_existing_snippet = False  # New snippet, not existing
        
        # For rename_snippet, use the user's edited name or derive from original + "-copy"
        if dest_folder == "rename_snippet":
            original_name = self._original_name
            current_name = self._destination_name  # User's current name in the edit field
            
            if current_name and current_name != original_name:
                # User has edited the name - use their custom name
                dest_folder = current_name
                logger.debug(f"Propagating rename: user edited name to '{dest_folder}'")
            else:
                # Name unchanged - auto-append "-copy"
                dest_folder = self._get_truncated_copy_name(original_name)
                logger.debug(f"Propagating rename: using auto-generated name '{dest_folder}'")
            is_new_snippet = True  # This is creating a new snippet with a new name
            is_existing_snippet = False  # New snippet, not existing
        
        # Get the strategy to propagate
        strategy = self._push_strategy
        
        # Propagate to children - either specific destination or just strategy
        if dest_folder and dest_folder != "inherit":
            self._propagate_folder_to_children(dest_folder, is_new_snippet, is_existing_snippet, strategy)
        elif strategy:
            # If no folder change but strategy changed, still propagate strategy
            self._propagate_folder_to_children(self._destination_folder, is_new_snippet, is_existing_snippet, strategy)
    
    def _update_check_state_from_children(self):
        """Update this row's check state based on children."""
        if not self._children:
            return
        
        checked_count = sum(1 for c in self._children if c.is_checked())
        partial_count = sum(1 for c in self._children if c.is_partial())
        total = len(self._children)
        
        self.checkbox.blockSignals(True)
        if checked_count == 0 and partial_count == 0:
            self.checkbox.setCheckState(Qt.CheckState.Unchecked)
            self._is_checked = False
            self._is_partial = False
        elif checked_count == total:
            self.checkbox.setCheckState(Qt.CheckState.Checked)
            self._is_checked = True
            self._is_partial = False
        else:
            self.checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
            self._is_checked = False
            self._is_partial = True
        self.checkbox.blockSignals(False)
        
        # Propagate up
        if self._parent_row:
            self._parent_row._update_check_state_from_children()
    
    # === Public API ===
    
    def add_child(self, child: 'SelectionRow'):
        """Add a child row."""
        child._parent_row = self
        self._children.append(child)
        self.children_layout.addWidget(child)
        
        # Update count label
        self.count_label.setText(f"({len(self._children)})")
        
        # Show expand button if this is first child
        if len(self._children) == 1:
            self.has_children = True
            self.expand_btn.setVisible(True)
    
    def set_checked(self, checked: bool):
        """Set the checked state."""
        self.checkbox.blockSignals(True)
        self.checkbox.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        self._is_checked = checked
        self._is_partial = False
        self.checkbox.blockSignals(False)
        
        # Update children
        for child in self._children:
            child.set_checked(checked)
    
    def is_checked(self) -> bool:
        """Check if this row is checked."""
        return self._is_checked
    
    def is_partial(self) -> bool:
        """Check if this row is in partial state."""
        return self._is_partial
    
    def is_expanded(self) -> bool:
        """Check if this row is expanded."""
        return self._is_expanded
    
    def set_expanded(self, expanded: bool):
        """Set the expanded state."""
        if self.has_children and self._is_expanded != expanded:
            self._toggle_expanded()
    
    def get_children(self) -> List['SelectionRow']:
        """Get child rows."""
        return self._children
    
    def get_data(self) -> Dict[str, Any]:
        """Get the item data."""
        return self.data
    
    def set_destination(self, folder: str, is_existing_snippet: bool = False, is_new_snippet: bool = False):
        """Set the destination for this item programmatically.
        
        Used when adding items as dependencies - they should inherit the same
        destination as the item that requires them.
        
        Args:
            folder: The destination folder/snippet name
            is_existing_snippet: True if destination is an existing snippet
            is_new_snippet: True if destination is a new snippet being created
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.debug(f"set_destination for '{self.label_text}': folder='{folder}', "
                    f"is_existing_snippet={is_existing_snippet}, is_new_snippet={is_new_snippet}")
        
        # Set the internal destination folder
        if is_existing_snippet and folder:
            # Find the matching item in the dropdown if it exists
            if hasattr(self, 'dest_folder_combo'):
                for i in range(self.dest_folder_combo.count()):
                    if self.dest_folder_combo.itemData(i) == folder:
                        self.dest_folder_combo.setCurrentIndex(i)
                        break
            self._destination_folder = folder
        elif is_new_snippet:
            self._destination_folder = "new_snippet"
        elif folder and folder != "inherit":
            self._destination_folder = folder
        else:
            self._destination_folder = "inherit"
        
        # Set the flags
        self._dest_is_existing_snippet = is_existing_snippet
        self._is_dest_new_snippet = is_new_snippet
    
    def get_destination_settings(self) -> Dict[str, Any]:
        """Get the destination settings for this item."""
        # Resolve inherited folder
        effective_folder = self._get_effective_folder()
        
        # Check if this is a rename_snippet operation (this row directly)
        is_rename = self._destination_folder == "rename_snippet"
        is_new = self._destination_folder == "new_snippet"
        
        # Debug logging for containers
        if self.has_children and self.item_type in ('folder', 'snippet'):
            logger.debug(f"get_destination_settings for container '{self.label_text}':")
            logger.debug(f"  _destination_folder: '{self._destination_folder}'")
            logger.debug(f"  effective_folder: '{effective_folder}'")
            logger.debug(f"  is_rename: {is_rename}, is_new: {is_new}")
        
        # Also check if parent propagated new_snippet flag (for children of renamed/new snippets)
        is_dest_new_snippet = getattr(self, '_is_dest_new_snippet', False)
        
        # Check if destination is an existing snippet (selected from dropdown)
        is_existing_snippet = getattr(self, '_dest_is_existing_snippet', False)
        
        settings = {
            'folder': effective_folder,
            'name': self._destination_name,
            'strategy': self._push_strategy,
            'is_inherited': self._destination_folder == "inherit",
            # A snippet is "new" if:
            # 1. This row directly chose new_snippet or rename_snippet, OR
            # 2. Parent propagated the _is_dest_new_snippet flag (children of container)
            'is_new_snippet': is_new or is_rename or is_dest_new_snippet,
            'is_rename_snippet': is_rename,
            # Track if destination is an existing snippet (not folder, not new)
            'is_existing_snippet': is_existing_snippet and not is_new and not is_rename and not is_dest_new_snippet,
        }
        
        # Include new snippet settings if applicable
        if is_new:
            settings['new_snippet_name'] = self.new_snippet_edit.text() if hasattr(self, 'new_snippet_edit') else ''
            # Radio buttons - include_dependencies is checked when that radio is selected
            settings['include_dependencies'] = self.include_deps_radio.isChecked() if hasattr(self, 'include_deps_radio') else True
            settings['create_duplicates'] = self.create_dups_radio.isChecked() if hasattr(self, 'create_dups_radio') else False
        elif is_rename:
            # For rename_snippet (container level):
            # - If user edited the name, use their edited name
            # - If name unchanged from original, auto-append "-copy"
            original_name = self._original_name  # The original name from data
            current_name = self._destination_name  # User's current name in the edit field
            
            logger.debug(f"Rename snippet settings for '{self.label_text}':")
            logger.debug(f"  original_name (from data): '{original_name}'")
            logger.debug(f"  current_name (from edit): '{current_name}'")
            
            if current_name and current_name != original_name:
                # User has edited the name - use their custom name
                new_name = current_name
                logger.debug(f"  -> User edited name, using: '{new_name}'")
            else:
                # Name unchanged - auto-append "-copy"
                new_name = self._get_truncated_copy_name(original_name)
                logger.debug(f"  -> Name unchanged, appending -copy: '{new_name}'")
            
            settings['new_snippet_name'] = new_name
            settings['include_dependencies'] = True  # Always include all children
            settings['create_duplicates'] = False
        elif is_dest_new_snippet:
            # Child of a container that's being renamed/created as new snippet
            # The effective_folder IS the new snippet name (propagated from parent)
            settings['new_snippet_name'] = effective_folder
            settings['include_dependencies'] = True
            settings['create_duplicates'] = False
        
        return settings
    
    def _get_truncated_copy_name(self, original_name: str, max_length: int = 55) -> str:
        """
        Get a copy name that fits within the max length.
        
        Appends '-copy' to the name, truncating if necessary to fit.
        
        Args:
            original_name: The original name
            max_length: Maximum allowed length (default 55 for Prisma Access)
            
        Returns:
            Name with '-copy' suffix, truncated if needed
        """
        suffix = "-copy"
        suffix_len = len(suffix)
        
        if len(original_name) + suffix_len <= max_length:
            return original_name + suffix
        else:
            # Truncate the original name to make room for suffix
            truncated = original_name[:max_length - suffix_len]
            return truncated + suffix
    
    def _get_effective_folder(self) -> str:
        """Get the effective folder, resolving inheritance."""
        if self._destination_folder != "inherit":
            return self._destination_folder
        
        # Walk up the parent chain to find an explicit folder
        if self._parent_row:
            parent_folder = self._parent_row._get_effective_folder()
            if parent_folder and parent_folder != "inherit":
                return parent_folder
        
        # Fall back to original source folder
        return self._original_folder
    
    def set_available_folders(self, folders: List[str]):
        """Update the available destination folders."""
        logger.debug(f"set_available_folders called for '{self.label_text}' with {len(folders)} folders: {folders[:5]}...")
        self.available_folders = folders
        current_data = self.dest_folder_combo.currentData()
        
        # Repopulate the dropdown
        self._populate_location_dropdown()
        
        # Restore previous selection or default to inherit
        if current_data:
            for i in range(self.dest_folder_combo.count()):
                if self.dest_folder_combo.itemData(i) == current_data:
                    self.dest_folder_combo.setCurrentIndex(i)
                    break
        
        logger.debug(f"After repopulate, combo has {self.dest_folder_combo.count()} items")
    
    def set_available_snippets(self, snippets: List[str]):
        """Update the available destination snippets."""
        self.available_snippets = snippets
        current_data = self.dest_folder_combo.currentData()
        
        # Repopulate the dropdown to include new snippets
        self._populate_location_dropdown()
        
        # Restore previous selection or default to inherit
        if current_data:
            for i in range(self.dest_folder_combo.count()):
                if self.dest_folder_combo.itemData(i) == current_data:
                    self.dest_folder_combo.setCurrentIndex(i)
                    break
    
    def update_default_strategy(self, strategy: str):
        """Update the default push strategy."""
        self.default_push_strategy = strategy
        # Only update if user hasn't changed it
        if self.strategy_combo.currentText().lower() == self._push_strategy:
            self.strategy_combo.setCurrentText(strategy.capitalize())
            self._push_strategy = strategy
