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
        tree_layout.addWidget(self.tree)

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

        splitter.setSizes([400, 600])
        layout.addWidget(splitter)

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
        source = metadata.get("source_tenant", "Unknown")

        self.info_label.setText(f"Version: {version} | Source: {source}")
        self.info_label.setStyleSheet("color: green;")

        # Build tree
        root = self.tree.invisibleRootItem()

        # Metadata
        metadata_item = QTreeWidgetItem(["Metadata", "info", ""])
        self._add_dict_items(metadata_item, metadata)
        root.addChild(metadata_item)

        # Security Policies
        sec_policies = self.current_config.get("security_policies", {})
        if sec_policies:
            sec_item = QTreeWidgetItem(["Security Policies", "container", ""])

            # Folders
            folders = sec_policies.get("folders", [])
            if folders:
                folders_item = QTreeWidgetItem(["Folders", "list", str(len(folders))])
                for folder in folders:
                    name = folder.get("name", "Unknown")
                    folder_item = QTreeWidgetItem([name, "folder", ""])
                    folder_item.setData(0, Qt.ItemDataRole.UserRole, folder)
                    folders_item.addChild(folder_item)
                sec_item.addChild(folders_item)

            # Snippets
            snippets = sec_policies.get("snippets", [])
            if snippets:
                snippets_item = QTreeWidgetItem(
                    ["Snippets", "list", str(len(snippets))]
                )
                for snippet in snippets:
                    name = snippet.get("name", "Unknown")
                    snip_item = QTreeWidgetItem([name, "snippet", ""])
                    snip_item.setData(0, Qt.ItemDataRole.UserRole, snippet)
                    snippets_item.addChild(snip_item)
                sec_item.addChild(snippets_item)

            # Security Rules
            rules = sec_policies.get("security_rules", [])
            if rules:
                rules_item = QTreeWidgetItem(
                    ["Security Rules", "list", str(len(rules))]
                )
                for rule in rules:
                    name = rule.get("name", "Unknown")
                    rule_item = QTreeWidgetItem([name, "rule", ""])
                    rule_item.setData(0, Qt.ItemDataRole.UserRole, rule)
                    rules_item.addChild(rule_item)
                sec_item.addChild(rules_item)

            root.addChild(sec_item)

        # Objects
        objects = self.current_config.get("objects", {})
        if objects:
            obj_item = QTreeWidgetItem(["Objects", "container", ""])

            # Addresses
            addresses = objects.get("addresses", [])
            if addresses:
                addr_item = QTreeWidgetItem(["Addresses", "list", str(len(addresses))])
                for addr in addresses[:100]:  # Limit display
                    name = addr.get("name", "Unknown")
                    a_item = QTreeWidgetItem([name, "address", ""])
                    a_item.setData(0, Qt.ItemDataRole.UserRole, addr)
                    addr_item.addChild(a_item)
                if len(addresses) > 100:
                    more = QTreeWidgetItem([f"... {len(addresses)-100} more", "", ""])
                    addr_item.addChild(more)
                obj_item.addChild(addr_item)

            # Address Groups
            addr_groups = objects.get("address_groups", [])
            if addr_groups:
                ag_item = QTreeWidgetItem(
                    ["Address Groups", "list", str(len(addr_groups))]
                )
                obj_item.addChild(ag_item)

            # Services
            services = objects.get("services", [])
            if services:
                svc_item = QTreeWidgetItem(["Services", "list", str(len(services))])
                obj_item.addChild(svc_item)

            root.addChild(obj_item)

        # Update stats
        total_items = self._count_items(self.current_config)
        self.stats_label.setText(f"Total items: {total_items}")

        # Expand top level
        self.tree.expandToDepth(0)

    def _add_dict_items(self, parent: QTreeWidgetItem, data: Dict):
        """Add dictionary items to tree."""
        for key, value in data.items():
            if isinstance(value, dict):
                item = QTreeWidgetItem([str(key), "dict", ""])
                self._add_dict_items(item, value)
                parent.addChild(item)
            elif isinstance(value, list):
                item = QTreeWidgetItem([str(key), "list", str(len(value))])
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
        count += len(objects.get("service_groups", []))
        count += len(objects.get("applications", []))
        count += len(objects.get("application_groups", []))

        return count

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item click."""
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
