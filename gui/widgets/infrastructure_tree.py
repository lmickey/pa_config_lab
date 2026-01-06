"""
Infrastructure Selection Tree Widget for Pull Configuration.

Specialized tree widget for selecting infrastructure components with
their specific hierarchy (Remote Networks, Service Connections, Mobile Users).
"""

import logging
from typing import Dict, List, Optional, Any

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QCheckBox,
    QLabel,
    QHeaderView,
)
from PyQt6.QtCore import Qt, pyqtSignal

logger = logging.getLogger(__name__)


class InfrastructureTreeWidget(QWidget):
    """
    Tree widget for selecting infrastructure components.
    
    Hierarchy:
    - Remote Networks
      ├─ IPsec Tunnels
      │    ├─ IKE Gateways
      │    │   └─ IKE Crypto Profiles
      │    └─ IPsec Crypto Profiles
      └─ Regions & Bandwidth
           ├─ Enabled Regions
           └─ Bandwidth Allocations
    
    - Service Connections
      └─ IPsec Tunnels
           ├─ IKE Gateways
           │   └─ IKE Crypto Profiles
           └─ IPsec Crypto Profiles
    
    - Mobile Users
      └─ Agent Profiles
           └─ [Profile names from API]
    """
    
    # Signal emitted when selection changes
    selection_changed = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the infrastructure tree widget."""
        super().__init__(parent)
        
        self._updating = False
        self._agent_profiles: List[Dict[str, Any]] = []
        self._agent_profiles_cached = False
        
        self._init_ui()
        self._build_tree()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title_label = QLabel("<b>Infrastructure</b>")
        layout.addWidget(title_label)
        
        # Select All checkbox
        self.select_all_check = QCheckBox("Select All")
        self.select_all_check.stateChanged.connect(self._on_select_all_changed)
        layout.addWidget(self.select_all_check)
        
        # Tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Component", "Type"])
        self.tree.setColumnWidth(0, 200)
        self.tree.header().setStretchLastSection(True)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tree.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.tree)
    
    def _build_tree(self):
        """Build the infrastructure tree structure."""
        self.tree.clear()
        
        # Remote Networks
        self.remote_networks_item = self._create_checked_item("Remote Networks", "infrastructure")
        self._add_ipsec_hierarchy(self.remote_networks_item, "remote_networks")
        
        # Regions & Bandwidth (under Remote Networks)
        self.regions_item = self._create_checked_item("Regions & Bandwidth", "regions")
        
        regions_item = self._create_checked_item("Enabled Regions", "region")
        regions_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'region'})
        self.regions_item.addChild(regions_item)
        
        bandwidth_item = self._create_checked_item("Bandwidth Allocations", "bandwidth")
        bandwidth_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'bandwidth'})
        self.regions_item.addChild(bandwidth_item)
        
        self.remote_networks_item.addChild(self.regions_item)
        
        self.tree.addTopLevelItem(self.remote_networks_item)
        
        # Service Connections
        self.service_connections_item = self._create_checked_item("Service Connections", "infrastructure")
        self._add_ipsec_hierarchy(self.service_connections_item, "service_connections")
        self.tree.addTopLevelItem(self.service_connections_item)
        
        # Mobile Users Infrastructure
        self.mobile_users_item = self._create_checked_item("Mobile User Infrastructure", "infrastructure")
        
        # Agent Profiles (with dynamic profile list)
        self.agent_profiles_item = self._create_checked_item("Agent Profiles", "agent_profile")
        self.agent_profiles_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'agent_profile', 'parent': 'mobile_users'})
        self.mobile_users_item.addChild(self.agent_profiles_item)
        
        self.tree.addTopLevelItem(self.mobile_users_item)
        
        # Start collapsed (like folders/snippets)
        self.tree.collapseAll()
        
        # Update select all state
        self._update_select_all_state()
    
    def _add_ipsec_hierarchy(self, parent: QTreeWidgetItem, parent_type: str):
        """Add IPsec tunnel hierarchy to a parent item."""
        # IPsec Tunnels
        ipsec_item = self._create_checked_item("IPsec Tunnels", "ipsec_tunnel")
        ipsec_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'ipsec_tunnel', 'parent': parent_type})
        
        # IKE Gateways
        ike_gw_item = self._create_checked_item("IKE Gateways", "ike_gateway")
        ike_gw_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'ike_gateway', 'parent': parent_type})
        
        # IKE Crypto Profiles (under IKE Gateways)
        ike_crypto_item = self._create_checked_item("IKE Crypto Profiles", "ike_crypto_profile")
        ike_crypto_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'ike_crypto_profile', 'parent': parent_type})
        ike_gw_item.addChild(ike_crypto_item)
        
        ipsec_item.addChild(ike_gw_item)
        
        # IPsec Crypto Profiles
        ipsec_crypto_item = self._create_checked_item("IPsec Crypto Profiles", "ipsec_crypto_profile")
        ipsec_crypto_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'ipsec_crypto_profile', 'parent': parent_type})
        ipsec_item.addChild(ipsec_crypto_item)
        
        parent.addChild(ipsec_item)
    
    def _create_checked_item(self, name: str, item_type: str) -> QTreeWidgetItem:
        """Create a tree item with checkbox, checked by default."""
        item = QTreeWidgetItem([name, item_type])
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Checked)
        return item
    
    def set_agent_profiles(self, profiles: List[Dict[str, Any]]):
        """
        Set the agent profiles to display under Mobile Users.
        
        Args:
            profiles: List of profile dicts with 'name' and optionally 'id'
        """
        self._agent_profiles = profiles
        self._agent_profiles_cached = True
        
        # Clear existing profile children (but keep Agent Profiles item)
        while self.agent_profiles_item.childCount() > 0:
            self.agent_profiles_item.removeChild(self.agent_profiles_item.child(0))
        
        # Add profile items
        for profile in profiles:
            profile_name = profile.get('name', 'Unknown')
            profile_item = self._create_checked_item(profile_name, "agent_profile_instance")
            profile_item.setData(0, Qt.ItemDataRole.UserRole, {
                'type': 'agent_profile_instance',
                'name': profile_name,
                'id': profile.get('id'),
                'parent': 'agent_profiles'
            })
            self.agent_profiles_item.addChild(profile_item)
        
        # Expand agent profiles
        self.agent_profiles_item.setExpanded(True)
        
        logger.info(f"Added {len(profiles)} agent profiles to infrastructure tree")
    
    def _on_select_all_changed(self, state: int):
        """Handle Select All checkbox change."""
        if self._updating:
            return
        
        self._updating = True
        try:
            checked = state == Qt.CheckState.Checked.value
            for i in range(self.tree.topLevelItemCount()):
                item = self.tree.topLevelItem(i)
                self._set_item_checked_recursive(item, checked)
        finally:
            self._updating = False
        
        self.selection_changed.emit()
    
    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        """Handle item check state change."""
        if self._updating or column != 0:
            return
        
        self._updating = True
        try:
            # If item has children and was checked/unchecked, update all children
            if item.childCount() > 0:
                checked = item.checkState(0) == Qt.CheckState.Checked
                for i in range(item.childCount()):
                    self._set_item_checked_recursive(item.child(i), checked)
            
            # Update parent state based on children
            parent = item.parent()
            if parent:
                self._update_parent_check_state(parent)
            
            # Update Select All state
            self._update_select_all_state()
        finally:
            self._updating = False
        
        self.selection_changed.emit()
    
    def _set_item_checked_recursive(self, item: QTreeWidgetItem, checked: bool):
        """Recursively set checked state for item and all children."""
        item.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        for i in range(item.childCount()):
            self._set_item_checked_recursive(item.child(i), checked)
    
    def _update_parent_check_state(self, parent: QTreeWidgetItem):
        """Update parent check state based on children."""
        checked_count = 0
        total_count = parent.childCount()
        
        for i in range(total_count):
            if parent.child(i).checkState(0) == Qt.CheckState.Checked:
                checked_count += 1
        
        if checked_count == 0:
            parent.setCheckState(0, Qt.CheckState.Unchecked)
        elif checked_count == total_count:
            parent.setCheckState(0, Qt.CheckState.Checked)
        else:
            parent.setCheckState(0, Qt.CheckState.PartiallyChecked)
        
        # Recurse up
        grandparent = parent.parent()
        if grandparent:
            self._update_parent_check_state(grandparent)
    
    def _update_select_all_state(self):
        """Update Select All checkbox based on tree state."""
        all_checked = True
        
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.checkState(0) != Qt.CheckState.Checked:
                all_checked = False
                break
        
        self._updating = True
        try:
            self.select_all_check.setChecked(all_checked)
        finally:
            self._updating = False
    
    def get_selected_infrastructure(self) -> Dict[str, Any]:
        """
        Get the selected infrastructure configuration.
        
        Returns:
            Dict with infrastructure selection state
        """
        result = {
            'remote_networks': self.remote_networks_item.checkState(0) != Qt.CheckState.Unchecked,
            'service_connections': self.service_connections_item.checkState(0) != Qt.CheckState.Unchecked,
            'mobile_users': self.mobile_users_item.checkState(0) != Qt.CheckState.Unchecked,
            'agent_profiles': self.agent_profiles_item.checkState(0) != Qt.CheckState.Unchecked,
            'regions': self.regions_item.checkState(0) != Qt.CheckState.Unchecked,
            'selected_agent_profiles': [],
        }
        
        # Get selected agent profile names
        for i in range(self.agent_profiles_item.childCount()):
            child = self.agent_profiles_item.child(i)
            if child.checkState(0) == Qt.CheckState.Checked:
                data = child.data(0, Qt.ItemDataRole.UserRole)
                if data and 'name' in data:
                    result['selected_agent_profiles'].append(data['name'])
        
        # Get detailed IPsec selections from Remote Networks
        rn_ipsec = self.remote_networks_item.child(0)  # IPsec Tunnels
        if rn_ipsec:
            result['rn_ipsec_tunnels'] = rn_ipsec.checkState(0) != Qt.CheckState.Unchecked
            ike_gw = rn_ipsec.child(0)  # IKE Gateways
            if ike_gw:
                result['rn_ike_gateways'] = ike_gw.checkState(0) != Qt.CheckState.Unchecked
                ike_crypto = ike_gw.child(0)  # IKE Crypto
                if ike_crypto:
                    result['rn_ike_crypto'] = ike_crypto.checkState(0) != Qt.CheckState.Unchecked
            ipsec_crypto = rn_ipsec.child(1)  # IPsec Crypto
            if ipsec_crypto:
                result['rn_ipsec_crypto'] = ipsec_crypto.checkState(0) != Qt.CheckState.Unchecked
        
        # Get detailed IPsec selections from Service Connections
        sc_ipsec = self.service_connections_item.child(0)  # IPsec Tunnels
        if sc_ipsec:
            result['sc_ipsec_tunnels'] = sc_ipsec.checkState(0) != Qt.CheckState.Unchecked
            ike_gw = sc_ipsec.child(0)  # IKE Gateways
            if ike_gw:
                result['sc_ike_gateways'] = ike_gw.checkState(0) != Qt.CheckState.Unchecked
                ike_crypto = ike_gw.child(0)  # IKE Crypto
                if ike_crypto:
                    result['sc_ike_crypto'] = ike_crypto.checkState(0) != Qt.CheckState.Unchecked
            ipsec_crypto = sc_ipsec.child(1)  # IPsec Crypto
            if ipsec_crypto:
                result['sc_ipsec_crypto'] = ipsec_crypto.checkState(0) != Qt.CheckState.Unchecked
        
        # Get Regions selections
        if self.regions_item.childCount() >= 2:
            result['regions_enabled'] = self.regions_item.child(0).checkState(0) != Qt.CheckState.Unchecked
            result['bandwidth'] = self.regions_item.child(1).checkState(0) != Qt.CheckState.Unchecked
        
        return result
    
    def clear(self):
        """Clear and rebuild the tree."""
        self._agent_profiles = []
        self._agent_profiles_cached = False
        self._build_tree()
    
    def set_enabled(self, enabled: bool):
        """Enable or disable the widget."""
        self.select_all_check.setEnabled(enabled)
        self.tree.setEnabled(enabled)
    
    def expand_all(self):
        """Expand all items in the tree."""
        self.tree.expandAll()
    
    def collapse_all(self):
        """Collapse all items in the tree."""
        self.tree.collapseAll()
