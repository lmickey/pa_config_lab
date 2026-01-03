"""
Configuration viewer widget for the GUI.

This module provides a tree view for browsing and viewing
loaded configurations with search and filter capabilities.
"""

from typing import Optional, Dict, Any, List
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QSplitter,
    QGroupBox,
    QComboBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import json

from gui.config_tree_builder import ConfigTreeBuilder


class ConfigViewerWidget(QWidget):
    """Widget for viewing and browsing configuration data."""

    def __init__(self, parent=None):
        """Initialize the config viewer widget."""
        super().__init__(parent)

        self.current_config = None

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("<h2>Configuration Viewer</h2>")
        layout.addWidget(title)

        # Info bar
        info_layout = QHBoxLayout()

        self.info_label = QLabel("No configuration loaded")
        self.info_label.setStyleSheet("color: gray;")
        info_layout.addWidget(self.info_label)

        info_layout.addStretch()

        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: gray; font-size: 11px;")
        info_layout.addWidget(self.stats_label)

        layout.addLayout(info_layout)

        # Search and filter
        search_layout = QHBoxLayout()

        search_layout.addWidget(QLabel("Search:"))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search configuration...")
        self.search_input.textChanged.connect(self._on_search)
        search_layout.addWidget(self.search_input)

        search_layout.addWidget(QLabel("Filter by:"))

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(
            [
                "All",
                "Security Rules",
                "Addresses",
                "Address Groups",
                "Services",
                "Service Groups",
                "Applications",
                "Snippets",
                "Profiles",
                "Infrastructure",
            ]
        )
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        search_layout.addWidget(self.filter_combo)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_search)
        search_layout.addWidget(clear_btn)

        layout.addLayout(search_layout)

        # Splitter for tree and details
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Tree view
        tree_widget = QWidget()
        tree_layout = QVBoxLayout(tree_widget)
        tree_layout.setContentsMargins(0, 0, 0, 0)

        tree_label = QLabel("<b>Configuration Tree</b>")
        tree_layout.addWidget(tree_label)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Item", "Type", "Count"])
        self.tree.setColumnWidth(0, 250)
        self.tree.itemClicked.connect(self._on_item_clicked)
        # Add keyboard navigation support with delayed refresh
        self.tree.currentItemChanged.connect(self._on_item_selection_changed)
        tree_layout.addWidget(self.tree)
        
        # Timer for delayed detail refresh (prevents crashes from rapid updates)
        from PyQt6.QtCore import QTimer
        self.detail_refresh_timer = QTimer()
        self.detail_refresh_timer.setSingleShot(True)
        self.detail_refresh_timer.timeout.connect(self._refresh_details)
        self.pending_item = None

        splitter.addWidget(tree_widget)

        # Details view
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(0, 0, 0, 0)

        details_label = QLabel("<b>Details</b>")
        details_layout.addWidget(details_label)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setPlaceholderText("Select an item to view details...")
        font = QFont("Courier New", 10)
        self.details_text.setFont(font)
        details_layout.addWidget(self.details_text)

        splitter.addWidget(details_widget)

        # Set splitter sizes - give more space to both panels
        # Left panel (tree): 40%, Right panel (details): 60%
        splitter.setSizes([400, 600])
        splitter.setStretchFactor(0, 4)  # Tree gets 40% when resizing
        splitter.setStretchFactor(1, 6)  # Details gets 60% when resizing
        
        # Add splitter with stretch to fill available space
        layout.addWidget(splitter, stretch=1)

    def set_config(self, config: Optional[Dict[str, Any]]):
        """Set the configuration to display."""
        self.current_config = config
        self._refresh_view()

    def _refresh_view(self):
        """Refresh the tree view with current configuration."""
        self.tree.clear()
        self.details_text.clear()

        if not self.current_config:
            self.info_label.setText("No configuration loaded")
            self.info_label.setStyleSheet("color: gray;")
            self.stats_label.setText("")
            return

        # Update info
        metadata = self.current_config.get("metadata", {})
        version = metadata.get("version", "Unknown")
        
        # Determine action and source
        source = metadata.get("source_tenant", "Unknown")
        load_type = metadata.get("load_type", "unknown")
        
        if load_type == "pull":
            action = "Pulled from"
        elif load_type == "file":
            action = "Loaded from file"
        else:
            action = "Source"
        
        self.info_label.setText(f"<b>{action}:</b> {source}")
        self.info_label.setStyleSheet("color: #2196F3;")

        # Calculate and display stats
        stats = self.current_config.get("stats", {})
        total = stats.get("total_items", 0)
        
        # Count by container type
        folders_count = stats.get("total_folders", 0)
        snippets_count = stats.get("total_snippets", 0)
        infra_count = stats.get("total_infrastructure", 0)
        
        self.stats_label.setText(
            f"Total: {total} items | "
            f"Folders: {folders_count} | "
            f"Snippets: {snippets_count} | "
            f"Infrastructure: {infra_count}"
        )

        # Build tree using ConfigTreeBuilder
        import logging
        logger = logging.getLogger(__name__)
        logger.info("="*80)
        logger.info("ConfigViewer._refresh_view - Building tree")
        logger.info(f"self.current_config type: {type(self.current_config)}")
        logger.info(f"self.current_config keys: {list(self.current_config.keys()) if isinstance(self.current_config, dict) else 'not a dict'}")
        if isinstance(self.current_config, dict):
            logger.info(f"  folders keys: {list(self.current_config.get('folders', {}).keys())}")
            logger.info(f"  snippets keys: {list(self.current_config.get('snippets', {}).keys())}")
            logger.info(f"  infrastructure keys: {list(self.current_config.get('infrastructure', {}).keys())}")
        logger.info("="*80)
        
        builder = ConfigTreeBuilder(enable_checkboxes=False)
        builder.build_tree(self.tree, self.current_config)
        
        saved_name = metadata.get("saved_name")
        source_tenant = metadata.get("source_tenant", "Unknown")
        
        if saved_name:
            # Config was loaded from a saved file
            action_source = f"Load - {saved_name}"
        else:
            # Config was pulled from tenant
            action_source = f"Pull - {source_tenant}"
        
        self.info_label.setText(f"Version: {version} | Source: {action_source}")
        self.info_label.setStyleSheet("color: green;")
        
        # Update stats
        total_items = self._count_items(self.current_config)
        self.stats_label.setText(f"Total items: {total_items}")

    def _add_dict_items(self, parent: QTreeWidgetItem, data: Dict):
        """Add dictionary items to tree, recursively expanding lists and dicts."""
        for key, value in data.items():
            if isinstance(value, dict):
                item = QTreeWidgetItem([str(key), "dict", ""])
                self._add_dict_items(item, value)
                parent.addChild(item)
            elif isinstance(value, list):
                item = QTreeWidgetItem([str(key), "list", str(len(value))])
                # Expand list items if they're dictionaries
                for idx, list_item in enumerate(value):
                    if isinstance(list_item, dict):
                        # Try to get a name for the item
                        item_name = list_item.get("name", list_item.get("id", f"Item {idx + 1}"))
                        child_item = QTreeWidgetItem([str(item_name), "dict", ""])
                        child_item.setData(0, Qt.ItemDataRole.UserRole, list_item)
                        self._add_dict_items(child_item, list_item)
                        item.addChild(child_item)
                    else:
                        # Simple value in list
                        child_item = QTreeWidgetItem([str(list_item), "value", ""])
                        item.addChild(child_item)
                parent.addChild(item)
            else:
                item = QTreeWidgetItem([str(key), "value", str(value)])
                parent.addChild(item)

    def _count_items(self, config: Dict) -> int:
        """Count total items in configuration."""
        count = 0

        sec_policies = config.get("security_policies", {})
        count += len(sec_policies.get("folders", []))
        count += len(sec_policies.get("snippets", []))
        count += len(sec_policies.get("security_rules", []))

        objects = config.get("objects", {})
        count += len(objects.get("addresses", []))
        count += len(objects.get("address_groups", []))
        count += len(objects.get("services", []))

        infrastructure = config.get("infrastructure", {})
        count += len(infrastructure.get("remote_networks", []))
        count += len(infrastructure.get("service_connections", []))
        count += len(infrastructure.get("ipsec_tunnels", []))
        count += len(infrastructure.get("hip_objects", []))
        count += len(infrastructure.get("hip_profiles", []))
        count += len(objects.get("service_groups", []))
        count += len(objects.get("applications", []))
        count += len(objects.get("application_groups", []))

        return count

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item click - immediate refresh."""
        self._show_item_details(item)
    
    def _on_item_selection_changed(self, current: QTreeWidgetItem, previous: QTreeWidgetItem):
        """Handle keyboard navigation - delayed refresh to prevent crashes."""
        if current:
            # Store the item and start/restart the timer
            self.pending_item = current
            self.detail_refresh_timer.start(250)  # 250ms delay
    
    def _refresh_details(self):
        """Refresh details for pending item (called after delay)."""
        if self.pending_item:
            self._show_item_details(self.pending_item)
            self.pending_item = None
    
    def _show_item_details(self, item: QTreeWidgetItem):
        """Show details for an item."""
        if not item:
            return
        
        # Get data from item
        data = item.data(0, Qt.ItemDataRole.UserRole)

        if data:
            # Format as JSON
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            self.details_text.setPlainText(json_str)
        else:
            # Show item info
            name = item.text(0)
            item_type = item.text(1)
            count = item.text(2)

            info = f"Name: {name}\nType: {item_type}"
            if count:
                info += f"\nCount: {count}"

            self.details_text.setPlainText(info)

    def _on_search(self, text: str):
        """Handle search text change."""
        if not text:
            # Show all items
            iterator = QTreeWidgetItemIterator(self.tree)
            while iterator.value():
                iterator.value().setHidden(False)
                iterator += 1
            return

        # Hide items that don't match
        search_lower = text.lower()
        iterator = QTreeWidgetItemIterator(self.tree)

        while iterator.value():
            item = iterator.value()
            item_text = item.text(0).lower()
            matches = search_lower in item_text
            item.setHidden(not matches)
            iterator += 1

    def _on_filter_changed(self, filter_type: str):
        """Handle filter change."""
        # Simple implementation - refresh with filter
        # Could be enhanced to show/hide specific types
        pass

    def _clear_search(self):
        """Clear search and filters."""
        self.search_input.clear()
        self.filter_combo.setCurrentIndex(0)
