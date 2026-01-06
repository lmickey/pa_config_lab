"""
Shared configuration tree builder.

This module provides a reusable tree-building component for displaying
Prisma Access configurations. Used by both the config viewer and
component selection dialog to ensure consistency.
"""

import logging
from typing import Dict, Any, Optional, Callable, List, Tuple
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

# Import component sections from selection tree for consistent hierarchy
from gui.widgets.selection_tree import COMPONENT_SECTIONS

logger = logging.getLogger(__name__)


# Default snippet values that indicate system/predefined items
DEFAULT_SNIPPETS = {
    'default',           # General system defaults
    'hip-default',       # HIP-specific defaults
    'optional-default',  # Optional pre-built defaults
}

# Build reverse mapping from item_type to section name
# This allows grouping items by their logical section in the tree
ITEM_TYPE_TO_SECTION: Dict[str, str] = {}
for section_name, components in COMPONENT_SECTIONS.items():
    for item_type, display_name in components:
        ITEM_TYPE_TO_SECTION[item_type] = section_name

# Section display order (matches selection_tree.py order)
SECTION_ORDER = [
    'Addresses',
    'Services', 
    'Applications',
    'Tags & Schedules',
    'External Lists',
    'Security Profiles',
    'Other Profiles',
    'HIP',
    'Security Policy',
    'Other Policies',
]

# Display names for item types (from COMPONENT_SECTIONS)
ITEM_TYPE_DISPLAY_NAMES: Dict[str, str] = {}
for section_name, components in COMPONENT_SECTIONS.items():
    for item_type, display_name in components:
        ITEM_TYPE_DISPLAY_NAMES[item_type] = display_name


def is_default_item(item_dict: Dict[str, Any]) -> bool:
    """
    Check if an item is a system default based on its snippet field.
    
    Args:
        item_dict: Item dictionary containing 'snippet' field
        
    Returns:
        True if item is a system default
    """
    snippet = item_dict.get('snippet', '')
    if not snippet:
        return False
    if snippet in DEFAULT_SNIPPETS:
        return True
    if snippet.endswith('-default'):
        return True
    return False


class ConfigTreeBuilder:
    """Build configuration trees with consistent structure."""
    
    def __init__(self, enable_checkboxes: bool = False, simplified: bool = False):
        """
        Initialize the tree builder.
        
        Args:
            enable_checkboxes: If True, add checkboxes to all items
            simplified: If True, use simplified structure for selection (no deep drill-down)
        """
        self.enable_checkboxes = enable_checkboxes
        self.simplified = simplified
    
    def build_tree(self, tree: QTreeWidget, config: Dict[str, Any]):
        """
        Build a complete configuration tree.
        
        Args:
            tree: QTreeWidget to populate
            config: Configuration dictionary
        """
        logger.detail("ConfigTreeBuilder.build_tree called")
        logger.detail(f"  config type: {type(config)}")
        logger.detail(f"  config keys: {list(config.keys()) if isinstance(config, dict) else 'not a dict'}")
        logger.detail(f"  simplified mode: {self.simplified}")
        
        tree.clear()
        root = tree.invisibleRootItem()
        
        # Build each section
        if not self.simplified:
            # Only show metadata in viewer mode
            self._build_metadata_section(root, config)
        
        logger.detail("  Calling _build_security_policies_section")
        self._build_security_policies_section(root, config)
        logger.detail("  Calling _build_objects_section")
        self._build_objects_section(root, config)
        logger.detail("  Calling _build_infrastructure_section")
        self._build_infrastructure_section(root, config)
        
        # Smart expand based on config size
        self._smart_expand(tree, root)
        logger.detail("  Tree building complete")
    
    def _smart_expand(self, tree: QTreeWidget, root: QTreeWidgetItem):
        """
        Smart expand tree based on configuration size.
        
        Rules:
        - Metadata is always collapsed
        - If < 20 objects total, expand all
        - If >= 20 objects and only 1 main section (folders/snippets/infrastructure), expand 2 levels
        - If >= 20 objects and multiple sections, expand only 1 level
        """
        # Count total objects and sections
        total_objects = 0
        main_sections = []  # Folders, Snippets, Infrastructure
        metadata_item = None
        
        for i in range(root.childCount()):
            child = root.child(i)
            child_text = child.text(0).lower()
            
            if 'metadata' in child_text:
                metadata_item = child
                # Always collapse metadata
                child.setExpanded(False)
            elif child_text in ('folders', 'snippets', 'infrastructure'):
                main_sections.append(child)
                # Count objects in this section
                total_objects += self._count_leaf_items(child)
        
        logger.detail(f"  Smart expand: {total_objects} objects, {len(main_sections)} main sections")
        
        if total_objects < 20:
            # Small config - expand everything except metadata
            logger.detail("  Expanding all (small config)")
            tree.expandAll()
            # Re-collapse metadata
            if metadata_item:
                metadata_item.setExpanded(False)
        elif len(main_sections) == 1:
            # One main section - expand 2 levels
            logger.detail("  Expanding 2 levels (single section)")
            tree.expandToDepth(1)
            # Re-collapse metadata
            if metadata_item:
                metadata_item.setExpanded(False)
        else:
            # Multiple sections - expand only 1 level
            logger.detail("  Expanding 1 level (multiple sections)")
            tree.expandToDepth(0)
            # Re-collapse metadata
            if metadata_item:
                metadata_item.setExpanded(False)
    
    def _count_leaf_items(self, item: QTreeWidgetItem) -> int:
        """Count leaf items (actual config objects) under an item."""
        if item.childCount() == 0:
            return 1
        
        count = 0
        for i in range(item.childCount()):
            child = item.child(i)
            # Check if this is a config item (has data) or a container
            child_type = child.text(1) if child.columnCount() > 1 else ''
            if child_type and child_type not in ('container', 'section', 'info', 'dict', 'list', ''):
                count += 1
            count += self._count_leaf_items(child)
        return count
    
    def _create_item(self, texts: list, data: Any = None, item_type: str = None) -> QTreeWidgetItem:
        """
        Create a tree item with optional checkbox and data.
        
        Args:
            texts: List of column texts [name, type, count]
            data: Optional data to attach to item (can be dict or raw data)
            item_type: Optional type identifier for the item
            
        Returns:
            Configured QTreeWidgetItem
        """
        item = QTreeWidgetItem(texts)
        
        if self.enable_checkboxes:
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(0, Qt.CheckState.Unchecked)
        
        if data is not None:
            # If data is already a dict with 'type', use it as-is
            if isinstance(data, dict) and 'type' in data:
                item.setData(0, Qt.ItemDataRole.UserRole, data)
            # Otherwise, wrap it with type metadata if provided
            elif item_type:
                item.setData(0, Qt.ItemDataRole.UserRole, {'type': item_type, 'data': data})
            else:
                item.setData(0, Qt.ItemDataRole.UserRole, data)
        elif item_type:
            # Just type, no data
            item.setData(0, Qt.ItemDataRole.UserRole, {'type': item_type})
        
        return item
    
    def _build_metadata_section(self, root: QTreeWidgetItem, config: Dict[str, Any]):
        """Build metadata section."""
        metadata = config.get("metadata", {})
        if not metadata:
            return
        
        metadata_item = self._create_item(["Metadata", "info", ""])
        self._add_dict_items(metadata_item, metadata)
        root.addChild(metadata_item)
    
    def _build_security_policies_section(self, root: QTreeWidgetItem, config: Dict[str, Any]):
        """Build security policies section (folders and snippets) - added directly to root."""
        # Check for new format (folders/snippets at top level)
        has_folders = "folders" in config
        has_snippets = "snippets" in config
        has_security_policies = "security_policies" in config
        
        logger.detail(f"  _build_security_policies_section: has_folders={has_folders}, has_snippets={has_snippets}, has_security_policies={has_security_policies}")
        
        if "folders" in config or "snippets" in config:
            # New format from ConfigAdapter - add Folders and Snippets directly to root
            logger.detail("  Using NEW format (folders/snippets at top level)")
            
            # Folders - added directly to root
            if config.get("folders"):
                logger.detail(f"  Calling _build_folders_section_new with {len(config.get('folders', {}))} folders")
                self._build_folders_section_new(root, config.get("folders", {}))
            
            # Snippets - added directly to root
            if config.get("snippets"):
                logger.detail(f"  Calling _build_snippets_section_new with {len(config.get('snippets', {}))} snippets")
                self._build_snippets_section_new(root, config.get("snippets", {}))
        
        elif has_security_policies:
            # Old format with security_policies
            logger.detail("  Using OLD format (security_policies)")
            sec_policies = config.get("security_policies", {})
            if not sec_policies:
                logger.warning("  No security_policies found in config!")
                return
            
            sec_item = self._create_item(["Security Policies", "container", ""])
            
            # Folders
            self._build_folders_section(sec_item, sec_policies)
            
            # Snippets
            self._build_snippets_section(sec_item, sec_policies)
            
            root.addChild(sec_item)
    
    def _build_folders_section(self, parent: QTreeWidgetItem, sec_policies: Dict[str, Any]):
        """Build folders section with full drill-down."""
        folders = sec_policies.get("folders", [])
        if not folders:
            return
        
        folders_item = self._create_item(["Folders", "list", str(len(folders))], item_type="folders_parent")
        
        for folder in folders:
            name = folder.get("name", "Unknown")
            folder_item = self._create_item([name, "folder", ""], data=folder, item_type="folder")
            
            # Security Rules
            security_rules = folder.get("security_rules", [])
            if security_rules:
                rules_item = self._create_item(["Security Rules", "list", str(len(security_rules))], item_type="rules_parent")
                rules_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'rules_parent', 'folder': name})
                for rule in security_rules:
                    rule_name = rule.get("name", "Unknown")
                    rule_child = self._create_item([rule_name, "security_rule", ""], data=rule, item_type="security_rule")
                    rule_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'security_rule', 'folder': name, 'data': rule})
                    rules_item.addChild(rule_child)
                folder_item.addChild(rules_item)
            
            # Objects (by type)
            objects_in_folder = folder.get("objects", {})
            if objects_in_folder:
                total_objects = sum(len(v) for v in objects_in_folder.values() if isinstance(v, list))
                if total_objects > 0:
                    objects_item = self._create_item(["Objects", "container", str(total_objects)])
                    
                    # Address Objects
                    if objects_in_folder.get("address_objects"):
                        addr_item = self._create_item(["Addresses", "list", str(len(objects_in_folder["address_objects"]))], item_type="folder_object_type")
                        addr_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'folder_object_type', 'object_type': 'address_objects', 'folder': name})
                        for obj in objects_in_folder["address_objects"]:
                            obj_name = obj.get("name", "Unknown")
                            obj_child = self._create_item([obj_name, "address", ""], data=obj, item_type="folder_object")
                            obj_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'folder_object', 'object_type': 'address_objects', 'folder': name, 'data': obj})
                            addr_item.addChild(obj_child)
                        objects_item.addChild(addr_item)
                    
                    # Address Groups
                    if objects_in_folder.get("address_groups"):
                        ag_item = self._create_item(["Address Groups", "list", str(len(objects_in_folder["address_groups"]))], item_type="folder_object_type")
                        ag_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'folder_object_type', 'object_type': 'address_groups', 'folder': name})
                        for obj in objects_in_folder["address_groups"]:
                            obj_name = obj.get("name", "Unknown")
                            obj_child = self._create_item([obj_name, "address_group", ""], data=obj, item_type="folder_object")
                            obj_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'folder_object', 'object_type': 'address_groups', 'folder': name, 'data': obj})
                            ag_item.addChild(obj_child)
                        objects_item.addChild(ag_item)
                    
                    # Service Objects
                    if objects_in_folder.get("service_objects"):
                        svc_item = self._create_item(["Services", "list", str(len(objects_in_folder["service_objects"]))], item_type="folder_object_type")
                        svc_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'folder_object_type', 'object_type': 'service_objects', 'folder': name})
                        for obj in objects_in_folder["service_objects"]:
                            obj_name = obj.get("name", "Unknown")
                            obj_child = self._create_item([obj_name, "service", ""], data=obj, item_type="folder_object")
                            obj_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'folder_object', 'object_type': 'service_objects', 'folder': name, 'data': obj})
                            svc_item.addChild(obj_child)
                        objects_item.addChild(svc_item)
                    
                    # Service Groups
                    if objects_in_folder.get("service_groups"):
                        sg_item = self._create_item(["Service Groups", "list", str(len(objects_in_folder["service_groups"]))], item_type="folder_object_type")
                        sg_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'folder_object_type', 'object_type': 'service_groups', 'folder': name})
                        for obj in objects_in_folder["service_groups"]:
                            obj_name = obj.get("name", "Unknown")
                            obj_child = self._create_item([obj_name, "service_group", ""], data=obj, item_type="folder_object")
                            obj_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'folder_object', 'object_type': 'service_groups', 'folder': name, 'data': obj})
                            sg_item.addChild(obj_child)
                        objects_item.addChild(sg_item)
                    
                    # Applications
                    if objects_in_folder.get("applications"):
                        app_item = self._create_item(["Applications", "list", str(len(objects_in_folder["applications"]))], item_type="folder_object_type")
                        app_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'folder_object_type', 'object_type': 'applications', 'folder': name})
                        for obj in objects_in_folder["applications"]:
                            obj_name = obj.get("name", "Unknown")
                            obj_child = self._create_item([obj_name, "application", ""], data=obj, item_type="folder_object")
                            obj_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'folder_object', 'object_type': 'applications', 'folder': name, 'data': obj})
                            app_item.addChild(obj_child)
                        objects_item.addChild(app_item)
                    
                    folder_item.addChild(objects_item)
            
            # Profiles (by type)
            profiles_in_folder = folder.get("profiles", {})
            if profiles_in_folder:
                total_profiles = sum(len(v) for v in profiles_in_folder.values() if isinstance(v, list))
                if total_profiles > 0:
                    profiles_item = self._create_item(["Profiles", "container", str(total_profiles)])
                    
                    # Authentication Profiles
                    if profiles_in_folder.get("authentication_profiles"):
                        auth_item = self._create_item(["Authentication", "list", str(len(profiles_in_folder["authentication_profiles"]))], item_type="folder_profile_type")
                        auth_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'folder_profile_type', 'profile_type': 'authentication_profiles', 'folder': name})
                        for prof in profiles_in_folder["authentication_profiles"]:
                            prof_name = prof.get("name", "Unknown")
                            prof_child = self._create_item([prof_name, "authentication_profile", ""], data=prof, item_type="folder_profile")
                            prof_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'folder_profile', 'profile_type': 'authentication_profiles', 'folder': name, 'data': prof})
                            auth_item.addChild(prof_child)
                        profiles_item.addChild(auth_item)
                    
                    # Decryption Profiles
                    if profiles_in_folder.get("decryption_profiles"):
                        dec_item = self._create_item(["Decryption", "list", str(len(profiles_in_folder["decryption_profiles"]))], item_type="folder_profile_type")
                        dec_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'folder_profile_type', 'profile_type': 'decryption_profiles', 'folder': name})
                        for prof in profiles_in_folder["decryption_profiles"]:
                            prof_name = prof.get("name", "Unknown")
                            prof_child = self._create_item([prof_name, "decryption_profile", ""], data=prof, item_type="folder_profile")
                            prof_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'folder_profile', 'profile_type': 'decryption_profiles', 'folder': name, 'data': prof})
                            dec_item.addChild(prof_child)
                        profiles_item.addChild(dec_item)
                    
                    # Security Profiles (various types)
                    security_profile_types = [
                        ("anti_spyware_profiles", "Anti-Spyware"),
                        ("vulnerability_profiles", "Vulnerability"),
                        ("url_filtering_profiles", "URL Filtering"),
                        ("file_blocking_profiles", "File Blocking"),
                        ("wildfire_profiles", "WildFire"),
                        ("dns_security_profiles", "DNS Security"),
                    ]
                    
                    for key, display_name in security_profile_types:
                        if profiles_in_folder.get(key):
                            prof_type_item = self._create_item([display_name, "list", str(len(profiles_in_folder[key]))], item_type="folder_profile_type")
                            prof_type_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'folder_profile_type', 'profile_type': key, 'folder': name})
                            for prof in profiles_in_folder[key]:
                                prof_name = prof.get("name", "Unknown")
                                prof_child = self._create_item([prof_name, key, ""], data=prof, item_type="folder_profile")
                                prof_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'folder_profile', 'profile_type': key, 'folder': name, 'data': prof})
                                prof_type_item.addChild(prof_child)
                            profiles_item.addChild(prof_type_item)
                    
                    folder_item.addChild(profiles_item)
            
            # HIP (Host Information Profile) objects and profiles
            hip_data = folder.get("hip", {})
            if hip_data:
                hip_objects = hip_data.get("hip_objects", [])
                hip_profiles = hip_data.get("hip_profiles", [])
                total_hip = len(hip_objects) + len(hip_profiles)
                
                if total_hip > 0:
                    hip_item = self._create_item(["HIP", "container", str(total_hip)])
                    
                    # HIP Objects
                    if hip_objects:
                        hip_obj_item = self._create_item(["HIP Objects", "list", str(len(hip_objects))])
                        for hip_obj in hip_objects:
                            obj_name = hip_obj.get("name", "Unknown")
                            obj_child = self._create_item([obj_name, "hip_object", ""], hip_obj)
                            hip_obj_item.addChild(obj_child)
                        hip_item.addChild(hip_obj_item)
                    
                    # HIP Profiles
                    if hip_profiles:
                        hip_prof_item = self._create_item(["HIP Profiles", "list", str(len(hip_profiles))])
                        for hip_prof in hip_profiles:
                            prof_name = hip_prof.get("name", "Unknown")
                            prof_child = self._create_item([prof_name, "hip_profile", ""], hip_prof)
                            hip_prof_item.addChild(prof_child)
                        hip_item.addChild(hip_prof_item)
                    
                    folder_item.addChild(hip_item)
            
            folders_item.addChild(folder_item)
        
        parent.addChild(folders_item)
    
    def _build_snippets_section(self, parent: QTreeWidgetItem, sec_policies: Dict[str, Any]):
        """Build snippets section with full drill-down (like folders)."""
        snippets = sec_policies.get("snippets", [])
        if not snippets:
            return
        
        # Filter snippets (same logic as folder selection dialog)
        filtered_snippets = []
        for snippet in snippets:
            # Get original keys if available (for filtering)
            original_keys = snippet.get("_original_keys", set())
            
            # Skip if snippet only has id and name in the original API response
            if original_keys == {"id", "name"} or original_keys == {"name", "id"}:
                continue
            
            filtered_snippets.append(snippet)
        
        if not filtered_snippets:
            return
        
        snippets_item = self._create_item(["Snippets", "list", str(len(filtered_snippets))], item_type="snippets_parent")
        
        # Sort: custom first (type not in ['predefined', 'readonly']), then alphabetically
        def sort_key(s):
            snippet_type = s.get("type", "")
            is_default = s.get("is_default", False)
            is_predefined = snippet_type in ["predefined", "readonly"] or is_default
            # Use display_name if available, otherwise name
            display_name = s.get("display_name", "").strip()
            name = display_name if display_name else s.get("name", "")
            return (is_predefined, name.lower())
        
        filtered_snippets.sort(key=sort_key)
        
        for snippet in filtered_snippets:
            # Use display_name if available, otherwise name
            display_name = snippet.get("display_name", "").strip()
            name = display_name if display_name else snippet.get("name", "Unknown")
            
            # Add type indicator - check both 'type' field and 'is_default' field
            snippet_type = snippet.get("type", "")
            is_default = snippet.get("is_default", False)
            if snippet_type in ["predefined", "readonly"] or is_default:
                type_indicator = "predefined"
            else:
                type_indicator = "custom"
            
            # Create snippet item
            snip_item = self._create_item([name, type_indicator, ""], data=snippet, item_type="snippet")
            
            # Security Rules
            security_rules = snippet.get("security_rules", [])
            if security_rules:
                rules_item = self._create_item(["Security Rules", "list", str(len(security_rules))], item_type="rules_parent")
                rules_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'rules_parent', 'snippet': name})
                for rule in security_rules:
                    rule_name = rule.get("name", "Unknown")
                    rule_child = self._create_item([rule_name, "security_rule", ""], data=rule, item_type="security_rule")
                    rule_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'security_rule', 'snippet': name, 'data': rule})
                    rules_item.addChild(rule_child)
                snip_item.addChild(rules_item)
            
            # Objects (by type)
            objects_in_snippet = snippet.get("objects", {})
            if objects_in_snippet:
                total_objects = sum(len(v) for v in objects_in_snippet.values() if isinstance(v, list))
                if total_objects > 0:
                    objects_item = self._create_item(["Objects", "container", str(total_objects)])
                    
                    # Address Objects
                    if objects_in_snippet.get("address_objects"):
                        addr_item = self._create_item(["Addresses", "list", str(len(objects_in_snippet["address_objects"]))], item_type="snippet_object_type")
                        addr_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'snippet_object_type', 'object_type': 'address_objects', 'snippet': name})
                        for obj in objects_in_snippet["address_objects"]:
                            obj_name = obj.get("name", "Unknown")
                            obj_child = self._create_item([obj_name, "address", ""], data=obj, item_type="snippet_object")
                            obj_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'snippet_object', 'object_type': 'address_objects', 'snippet': name, 'data': obj})
                            addr_item.addChild(obj_child)
                        objects_item.addChild(addr_item)
                    
                    # Address Groups
                    if objects_in_snippet.get("address_groups"):
                        ag_item = self._create_item(["Address Groups", "list", str(len(objects_in_snippet["address_groups"]))], item_type="snippet_object_type")
                        ag_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'snippet_object_type', 'object_type': 'address_groups', 'snippet': name})
                        for obj in objects_in_snippet["address_groups"]:
                            obj_name = obj.get("name", "Unknown")
                            obj_child = self._create_item([obj_name, "address_group", ""], data=obj, item_type="snippet_object")
                            obj_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'snippet_object', 'object_type': 'address_groups', 'snippet': name, 'data': obj})
                            ag_item.addChild(obj_child)
                        objects_item.addChild(ag_item)
                    
                    # Service Objects
                    if objects_in_snippet.get("service_objects"):
                        svc_item = self._create_item(["Services", "list", str(len(objects_in_snippet["service_objects"]))], item_type="snippet_object_type")
                        svc_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'snippet_object_type', 'object_type': 'service_objects', 'snippet': name})
                        for obj in objects_in_snippet["service_objects"]:
                            obj_name = obj.get("name", "Unknown")
                            obj_child = self._create_item([obj_name, "service", ""], data=obj, item_type="snippet_object")
                            obj_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'snippet_object', 'object_type': 'service_objects', 'snippet': name, 'data': obj})
                            svc_item.addChild(obj_child)
                        objects_item.addChild(svc_item)
                    
                    # Service Groups
                    if objects_in_snippet.get("service_groups"):
                        sg_item = self._create_item(["Service Groups", "list", str(len(objects_in_snippet["service_groups"]))], item_type="snippet_object_type")
                        sg_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'snippet_object_type', 'object_type': 'service_groups', 'snippet': name})
                        for obj in objects_in_snippet["service_groups"]:
                            obj_name = obj.get("name", "Unknown")
                            obj_child = self._create_item([obj_name, "service_group", ""], data=obj, item_type="snippet_object")
                            obj_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'snippet_object', 'object_type': 'service_groups', 'snippet': name, 'data': obj})
                            sg_item.addChild(obj_child)
                        objects_item.addChild(sg_item)
                    
                    # Applications
                    if objects_in_snippet.get("applications"):
                        app_item = self._create_item(["Applications", "list", str(len(objects_in_snippet["applications"]))], item_type="snippet_object_type")
                        app_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'snippet_object_type', 'object_type': 'applications', 'snippet': name})
                        for obj in objects_in_snippet["applications"]:
                            obj_name = obj.get("name", "Unknown")
                            obj_child = self._create_item([obj_name, "application", ""], data=obj, item_type="snippet_object")
                            obj_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'snippet_object', 'object_type': 'applications', 'snippet': name, 'data': obj})
                            app_item.addChild(obj_child)
                        objects_item.addChild(app_item)
                    
                    snip_item.addChild(objects_item)
            
            # Profiles (by type)
            profiles_in_snippet = snippet.get("profiles", {})
            if profiles_in_snippet:
                total_profiles = sum(len(v) for v in profiles_in_snippet.values() if isinstance(v, list))
                if total_profiles > 0:
                    profiles_item = self._create_item(["Profiles", "container", str(total_profiles)])
                    
                    # Authentication Profiles
                    if profiles_in_snippet.get("authentication_profiles"):
                        auth_item = self._create_item(["Authentication", "list", str(len(profiles_in_snippet["authentication_profiles"]))], item_type="snippet_profile_type")
                        auth_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'snippet_profile_type', 'profile_type': 'authentication_profiles', 'snippet': name})
                        for prof in profiles_in_snippet["authentication_profiles"]:
                            prof_name = prof.get("name", "Unknown")
                            prof_child = self._create_item([prof_name, "authentication_profile", ""], data=prof, item_type="snippet_profile")
                            prof_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'snippet_profile', 'profile_type': 'authentication_profiles', 'snippet': name, 'data': prof})
                            auth_item.addChild(prof_child)
                        profiles_item.addChild(auth_item)
                    
                    # Decryption Profiles
                    if profiles_in_snippet.get("decryption_profiles"):
                        dec_item = self._create_item(["Decryption", "list", str(len(profiles_in_snippet["decryption_profiles"]))], item_type="snippet_profile_type")
                        dec_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'snippet_profile_type', 'profile_type': 'decryption_profiles', 'snippet': name})
                        for prof in profiles_in_snippet["decryption_profiles"]:
                            prof_name = prof.get("name", "Unknown")
                            prof_child = self._create_item([prof_name, "decryption_profile", ""], data=prof, item_type="snippet_profile")
                            prof_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'snippet_profile', 'profile_type': 'decryption_profiles', 'snippet': name, 'data': prof})
                            dec_item.addChild(prof_child)
                        profiles_item.addChild(dec_item)
                    
                    # Security Profiles (various types)
                    security_profile_types = [
                        ("anti_spyware_profiles", "Anti-Spyware"),
                        ("vulnerability_profiles", "Vulnerability"),
                        ("url_filtering_profiles", "URL Filtering"),
                        ("file_blocking_profiles", "File Blocking"),
                        ("wildfire_profiles", "WildFire"),
                        ("dns_security_profiles", "DNS Security"),
                    ]
                    
                    for key, display_name in security_profile_types:
                        if profiles_in_snippet.get(key):
                            prof_type_item = self._create_item([display_name, "list", str(len(profiles_in_snippet[key]))], item_type="snippet_profile_type")
                            prof_type_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'snippet_profile_type', 'profile_type': key, 'snippet': name})
                            for prof in profiles_in_snippet[key]:
                                prof_name = prof.get("name", "Unknown")
                                prof_child = self._create_item([prof_name, key, ""], data=prof, item_type="snippet_profile")
                                prof_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'snippet_profile', 'profile_type': key, 'snippet': name, 'data': prof})
                                prof_type_item.addChild(prof_child)
                            profiles_item.addChild(prof_type_item)
                    
                    snip_item.addChild(profiles_item)
            
            # HIP (Host Information Profile) objects and profiles
            hip_data = snippet.get("hip", {})
            if hip_data:
                hip_objects = hip_data.get("hip_objects", [])
                hip_profiles = hip_data.get("hip_profiles", [])
                total_hip = len(hip_objects) + len(hip_profiles)
                
                if total_hip > 0:
                    hip_item = self._create_item(["HIP", "container", str(total_hip)])
                    
                    # HIP Objects
                    if hip_objects:
                        hip_obj_item = self._create_item(["HIP Objects", "list", str(len(hip_objects))])
                        for hip_obj in hip_objects:
                            obj_name = hip_obj.get("name", "Unknown")
                            obj_child = self._create_item([obj_name, "hip_object", ""], hip_obj)
                            hip_obj_item.addChild(obj_child)
                        hip_item.addChild(hip_obj_item)
                    
                    # HIP Profiles
                    if hip_profiles:
                        hip_prof_item = self._create_item(["HIP Profiles", "list", str(len(hip_profiles))])
                        for hip_prof in hip_profiles:
                            prof_name = hip_prof.get("name", "Unknown")
                            prof_child = self._create_item([prof_name, "hip_profile", ""], hip_prof)
                            hip_prof_item.addChild(prof_child)
                        hip_item.addChild(hip_prof_item)
                    
                    snip_item.addChild(hip_item)
            
            snippets_item.addChild(snip_item)
        
        parent.addChild(snippets_item)
    
    def _build_objects_section(self, root: QTreeWidgetItem, config: Dict[str, Any]):
        """Build objects section."""
        objects = config.get("objects", {})
        if not objects:
            return
        
        obj_item = self._create_item(["Objects", "container", ""])
        
        # Addresses
        addresses = objects.get("addresses", [])
        if addresses:
            addr_item = self._create_item(["Addresses", "list", str(len(addresses))])
            for addr in addresses[:100]:  # Limit display
                name = addr.get("name", "Unknown")
                a_item = self._create_item([name, "address", ""], addr)
                addr_item.addChild(a_item)
            if len(addresses) > 100:
                more = self._create_item([f"... {len(addresses)-100} more", "", ""])
                addr_item.addChild(more)
            obj_item.addChild(addr_item)
        
        # Address Groups
        addr_groups = objects.get("address_groups", [])
        if addr_groups:
            ag_item = self._create_item(["Address Groups", "list", str(len(addr_groups))])
            obj_item.addChild(ag_item)
        
        # Services
        services = objects.get("services", [])
        if services:
            svc_item = self._create_item(["Services", "list", str(len(services))])
            obj_item.addChild(svc_item)
        
        root.addChild(obj_item)
    
    def _build_infrastructure_section(self, root: QTreeWidgetItem, config: Dict[str, Any]):
        """Build infrastructure section with hierarchical structure matching selection tree."""
        infrastructure = config.get("infrastructure", {})
        if not infrastructure:
            logger.debug("No infrastructure data found")
            return
        
        logger.detail(f"Building infrastructure section with keys: {list(infrastructure.keys())}")
        
        infra_item = self._create_item(["Infrastructure", "container", ""])
        
        # Mapping from item_type to display name
        INFRA_TYPE_DISPLAY = {
            'remote_network': 'Remote Networks',
            'service_connection': 'Service Connections',
            'ipsec_tunnel': 'IPSec Tunnels',
            'ike_gateway': 'IKE Gateways',
            'ike_crypto_profile': 'IKE Crypto Profiles',
            'ipsec_crypto_profile': 'IPSec Crypto Profiles',
            'agent_profile': 'Agent Profiles',
            'portal': 'Portals',
            'gateway': 'Gateways',
            'bandwidth_allocation': 'Bandwidth Allocations',
            # Plural (legacy format)
            'remote_networks': 'Remote Networks',
            'service_connections': 'Service Connections',
            'ipsec_tunnels': 'IPSec Tunnels',
            'ike_gateways': 'IKE Gateways',
            'ike_crypto_profiles': 'IKE Crypto Profiles',
            'ipsec_crypto_profiles': 'IPSec Crypto Profiles',
            'agent_profiles': 'Agent Profiles',
            'portals': 'Portals',
            'gateways': 'Gateways',
            'bandwidth_allocations': 'Bandwidth Allocations',
        }
        
        # Normalize keys to singular form
        def normalize_key(key):
            """Convert plural keys to singular."""
            plural_to_singular = {
                'remote_networks': 'remote_network',
                'service_connections': 'service_connection',
                'ipsec_tunnels': 'ipsec_tunnel',
                'ike_gateways': 'ike_gateway',
                'ike_crypto_profiles': 'ike_crypto_profile',
                'ipsec_crypto_profiles': 'ipsec_crypto_profile',
                'agent_profiles': 'agent_profile',
                'portals': 'portal',
                'gateways': 'gateway',
            }
            return plural_to_singular.get(key, key)
        
        # Extract items by type (normalize keys)
        infra_by_type = {}
        for key, items in infrastructure.items():
            if isinstance(items, list) and items:
                normalized_key = normalize_key(key)
                infra_by_type[normalized_key] = items
            elif isinstance(items, dict):
                # Handle nested dict format (e.g., mobile_users, regions)
                normalized_key = normalize_key(key)
                infra_by_type[normalized_key] = items
        
        # Build hierarchical structure:
        # Remote Networks
        #   └─ IPSec Tunnels (filtered by folder=Remote Networks)
        #        ├─ IKE Gateways (filtered by folder=Remote Networks)
        #        │   └─ IKE Crypto Profiles
        #        └─ IPSec Crypto Profiles
        # Service Connections
        #   └─ IPSec Tunnels (filtered by folder=Service Connections)
        #        ├─ IKE Gateways (filtered by folder=Service Connections)
        #        │   └─ IKE Crypto Profiles
        #        └─ IPSec Crypto Profiles
        # Mobile Users Infrastructure
        #   └─ Agent Profiles
        
        # Remote Networks section
        # Check if we have any RN-related items (remote_network, IPSec items in RN folder, or bandwidth allocations)
        has_rn_items = 'remote_network' in infra_by_type
        has_rn_ipsec = self._has_ipsec_items_for_folder(infra_by_type, 'Remote Networks')
        has_bandwidth = 'bandwidth_allocation' in infra_by_type
        
        if has_rn_items or has_rn_ipsec or has_bandwidth:
            rn_items = infra_by_type.get('remote_network', [])
            rn_section = self._create_item(["Remote Networks", "container", str(len(rn_items)) if rn_items else ""])
            
            # Add remote network items directly under this section
            for item in sorted(rn_items, key=lambda x: x.get("name", "").lower()):
                name = item.get("name", "Unknown")
                item_child = self._create_item([name, "remote_network", ""], item_type="infrastructure")
                item_child.setData(0, Qt.ItemDataRole.UserRole, {
                    'type': 'infrastructure', 
                    'infra_type': 'remote_network', 
                    'data': item,
                    'is_default': is_default_item(item)
                })
                rn_section.addChild(item_child)
            
            # Add IPSec hierarchy under Remote Networks
            self._add_ipsec_hierarchy_viewer(rn_section, infra_by_type, 'Remote Networks', INFRA_TYPE_DISPLAY)
            
            # Add Regions & Bandwidth under Remote Networks
            if 'bandwidth_allocation' in infra_by_type:
                bandwidth_items = infra_by_type['bandwidth_allocation']
                regions_section = self._create_item(["Regions & Bandwidth", "container", str(len(bandwidth_items))])
                
                # Build bandwidth allocations section
                self._build_bandwidth_section(regions_section, bandwidth_items, INFRA_TYPE_DISPLAY)
                
                rn_section.addChild(regions_section)
            
            infra_item.addChild(rn_section)
        
        # Service Connections section
        # Check if we have any SC-related items (service_connection OR IPSec items in SC folder)
        has_sc_items = 'service_connection' in infra_by_type
        has_sc_ipsec = self._has_ipsec_items_for_folder(infra_by_type, 'Service Connections')
        
        if has_sc_items or has_sc_ipsec:
            sc_items = infra_by_type.get('service_connection', [])
            sc_section = self._create_item(["Service Connections", "container", str(len(sc_items)) if sc_items else ""])
            
            # Add service connection items directly under this section
            for item in sorted(sc_items, key=lambda x: x.get("name", "").lower()):
                name = item.get("name", "Unknown")
                item_child = self._create_item([name, "service_connection", ""], item_type="infrastructure")
                item_child.setData(0, Qt.ItemDataRole.UserRole, {
                    'type': 'infrastructure', 
                    'infra_type': 'service_connection', 
                    'data': item,
                    'is_default': is_default_item(item)
                })
                sc_section.addChild(item_child)
            
            # Add IPSec hierarchy under Service Connections
            self._add_ipsec_hierarchy_viewer(sc_section, infra_by_type, 'Service Connections', INFRA_TYPE_DISPLAY)
            
            infra_item.addChild(sc_section)
        
        # Mobile Users Infrastructure section
        has_mobile_users = any(k in infra_by_type for k in ['agent_profile', 'portal', 'gateway'])
        if has_mobile_users:
            mu_section = self._create_item(["Mobile User Infrastructure", "container", ""])
            
            # Agent Profiles
            if 'agent_profile' in infra_by_type:
                self._build_infra_type_section(mu_section, 'agent_profile', infra_by_type['agent_profile'], INFRA_TYPE_DISPLAY)
            
            # Portals
            if 'portal' in infra_by_type:
                self._build_infra_type_section(mu_section, 'portal', infra_by_type['portal'], INFRA_TYPE_DISPLAY)
            
            # Gateways
            if 'gateway' in infra_by_type:
                self._build_infra_type_section(mu_section, 'gateway', infra_by_type['gateway'], INFRA_TYPE_DISPLAY)
            
            infra_item.addChild(mu_section)
        
        # Handle any remaining types not covered above
        handled_types = {
            'remote_network', 'service_connection', 
            'ipsec_tunnel', 'ike_gateway', 'ike_crypto_profile', 'ipsec_crypto_profile',
            'agent_profile', 'portal', 'gateway',
            'bandwidth_allocation'
        }
        
        for item_type, items in infra_by_type.items():
            if item_type not in handled_types:
                if isinstance(items, dict):
                    display_name = INFRA_TYPE_DISPLAY.get(item_type, item_type.replace('_', ' ').title())
                    if self.simplified:
                        type_item = self._create_item([display_name, "infrastructure", ""], item_type="infrastructure")
                        type_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'infrastructure', 'infra_type': item_type, 'data': items})
                        infra_item.addChild(type_item)
                    else:
                        type_item = self._create_item([display_name, "dict", ""])
                        self._add_dict_items(type_item, items)
                        infra_item.addChild(type_item)
                elif isinstance(items, list) and items:
                    self._build_infra_type_section(infra_item, item_type, items, INFRA_TYPE_DISPLAY)
        
        root.addChild(infra_item)
    
    def _build_bandwidth_section(
        self,
        parent: QTreeWidgetItem,
        bandwidth_items: List[Dict[str, Any]],
        display_names: Dict[str, str]
    ):
        """
        Build bandwidth allocations section showing regional bandwidth data.
        
        Args:
            parent: Parent tree item (Regions & Bandwidth section)
            bandwidth_items: List of bandwidth allocation dicts from API
            display_names: Display name mapping
        """
        if not bandwidth_items:
            return
        
        # Create Bandwidth Allocations container
        bandwidth_section = self._create_item(["Bandwidth Allocations", "list", str(len(bandwidth_items))])
        
        # Sort by region name
        sorted_items = sorted(bandwidth_items, key=lambda x: x.get("name", x.get("region", "")).lower())
        
        for item in sorted_items:
            # Get display name - could be 'name' or 'region' field
            name = item.get("name", item.get("region", "Unknown"))
            
            # Get allocated bandwidth if available
            allocated = item.get("allocated_bandwidth_mbps", item.get("allocated_bandwidth", ""))
            if allocated:
                display_text = f"{name} ({allocated} Mbps)"
            else:
                display_text = name
            
            item_child = self._create_item([display_text, "bandwidth_allocation", ""], item_type="infrastructure")
            item_child.setData(0, Qt.ItemDataRole.UserRole, {
                'type': 'infrastructure',
                'infra_type': 'bandwidth_allocation',
                'data': item,
                'is_default': False
            })
            bandwidth_section.addChild(item_child)
        
        parent.addChild(bandwidth_section)
    
    def _has_ipsec_items_for_folder(self, infra_by_type: Dict[str, Any], folder_filter: str) -> bool:
        """
        Check if there are any IPSec-related items for a specific folder.
        
        Args:
            infra_by_type: Dictionary of all infrastructure items by type
            folder_filter: Folder name to check ('Remote Networks' or 'Service Connections')
            
        Returns:
            True if there are any IPSec tunnels, IKE gateways, or crypto profiles for this folder
        """
        ipsec_types = ['ipsec_tunnel', 'ike_gateway', 'ike_crypto_profile', 'ipsec_crypto_profile']
        
        for ipsec_type in ipsec_types:
            items = infra_by_type.get(ipsec_type, [])
            # Check if any items belong to this folder
            for item in items:
                if item.get('folder') == folder_filter:
                    return True
        
        return False
    
    def _add_ipsec_hierarchy_viewer(
        self, 
        parent: QTreeWidgetItem, 
        infra_by_type: Dict[str, Any],
        folder_filter: str,
        display_names: Dict[str, str]
    ):
        """
        Add IPSec tunnel hierarchy under a parent (Remote Networks or Service Connections).
        
        Hierarchy:
        └─ IPSec Tunnels
             ├─ IKE Gateways
             │   └─ IKE Crypto Profiles
             └─ IPSec Crypto Profiles
        
        Args:
            parent: Parent tree item
            infra_by_type: Dictionary of all infrastructure items by type
            folder_filter: Folder name to filter items ('Remote Networks' or 'Service Connections')
            display_names: Display name mapping
        """
        # Filter all IPSec-related items by folder
        ipsec_tunnels = infra_by_type.get('ipsec_tunnel', [])
        filtered_tunnels = [t for t in ipsec_tunnels if t.get('folder') == folder_filter]
        
        ike_gateways = infra_by_type.get('ike_gateway', [])
        filtered_ike_gw = [g for g in ike_gateways if g.get('folder') == folder_filter]
        
        ike_crypto_profiles = infra_by_type.get('ike_crypto_profile', [])
        filtered_ike_crypto = [p for p in ike_crypto_profiles if p.get('folder') == folder_filter]
        
        ipsec_crypto_profiles = infra_by_type.get('ipsec_crypto_profile', [])
        filtered_ipsec_crypto = [p for p in ipsec_crypto_profiles if p.get('folder') == folder_filter]
        
        # Check if we have ANY IPSec-related items for this folder
        has_any_ipsec = filtered_tunnels or filtered_ike_gw or filtered_ike_crypto or filtered_ipsec_crypto
        
        if not has_any_ipsec:
            return
        
        # Create IPSec Tunnels container
        tunnel_count = len(filtered_tunnels)
        ipsec_section = self._create_item(["IPSec Tunnels", "list", str(tunnel_count) if tunnel_count else ""])
        
        # Add tunnel items
        for tunnel in sorted(filtered_tunnels, key=lambda x: x.get("name", "").lower()):
            name = tunnel.get("name", "Unknown")
            is_default = is_default_item(tunnel)
            
            tunnel_item = self._create_item([name, "ipsec_tunnel", ""], item_type="infrastructure")
            tunnel_item.setData(0, Qt.ItemDataRole.UserRole, {
                'type': 'infrastructure', 
                'infra_type': 'ipsec_tunnel', 
                'data': tunnel,
                'is_default': is_default
            })
            
            if is_default:
                tunnel_item.setForeground(0, QColor(128, 128, 128))
                tunnel_item.setForeground(1, QColor(128, 128, 128))
            
            ipsec_section.addChild(tunnel_item)
        
        # Add IKE Gateways section under IPSec Tunnels (if we have gateways OR IKE crypto profiles)
        if filtered_ike_gw or filtered_ike_crypto:
            ike_gw_section = self._create_item(["IKE Gateways", "list", str(len(filtered_ike_gw)) if filtered_ike_gw else ""])
            
            for gw in sorted(filtered_ike_gw, key=lambda x: x.get("name", "").lower()):
                name = gw.get("name", "Unknown")
                is_default = is_default_item(gw)
                
                gw_item = self._create_item([name, "ike_gateway", ""], item_type="infrastructure")
                gw_item.setData(0, Qt.ItemDataRole.UserRole, {
                    'type': 'infrastructure', 
                    'infra_type': 'ike_gateway', 
                    'data': gw,
                    'is_default': is_default
                })
                
                if is_default:
                    gw_item.setForeground(0, QColor(128, 128, 128))
                    gw_item.setForeground(1, QColor(128, 128, 128))
                
                ike_gw_section.addChild(gw_item)
            
            # Add IKE Crypto Profiles under IKE Gateways
            if filtered_ike_crypto:
                ike_crypto_section = self._build_crypto_profile_section(
                    'ike_crypto_profile', filtered_ike_crypto, display_names
                )
                ike_gw_section.addChild(ike_crypto_section)
            
            ipsec_section.addChild(ike_gw_section)
        
        # Add IPSec Crypto Profiles under IPSec Tunnels
        if filtered_ipsec_crypto:
            ipsec_crypto_section = self._build_crypto_profile_section(
                'ipsec_crypto_profile', filtered_ipsec_crypto, display_names
            )
            ipsec_section.addChild(ipsec_crypto_section)
        
        parent.addChild(ipsec_section)
    
    def _build_crypto_profile_section(
        self,
        profile_type: str,
        profiles: List[Dict[str, Any]],
        display_names: Dict[str, str]
    ) -> QTreeWidgetItem:
        """Build a crypto profile section with custom/default sorting."""
        display_name = display_names.get(profile_type, profile_type.replace('_', ' ').title())
        
        # Count custom vs default
        custom_count = sum(1 for p in profiles if not is_default_item(p))
        default_count = len(profiles) - custom_count
        
        if default_count > 0 and custom_count > 0:
            count_str = f"{custom_count} custom, {default_count} default"
        elif default_count > 0:
            count_str = f"{default_count} default"
        else:
            count_str = str(len(profiles))
        
        section = self._create_item([display_name, "list", count_str])
        
        # Sort: custom first, then default, alphabetically
        def sort_key(item):
            is_def = is_default_item(item)
            name = item.get("name", "").lower()
            return (is_def, name)
        
        for profile in sorted(profiles, key=sort_key):
            name = profile.get("name", "Unknown")
            is_default = is_default_item(profile)
            
            type_indicator = f"{profile_type} (default)" if is_default else profile_type
            
            profile_item = self._create_item([name, type_indicator, ""], item_type="infrastructure")
            profile_item.setData(0, Qt.ItemDataRole.UserRole, {
                'type': 'infrastructure', 
                'infra_type': profile_type, 
                'data': profile,
                'is_default': is_default
            })
            
            if is_default:
                profile_item.setForeground(0, QColor(128, 128, 128))
                profile_item.setForeground(1, QColor(128, 128, 128))
            
            section.addChild(profile_item)
        
        return section
    
    def _build_infra_type_section(
        self, 
        parent: QTreeWidgetItem, 
        item_type: str, 
        items: list, 
        display_names: Dict[str, str]
    ):
        """Build a section for a specific infrastructure type."""
        display_name = display_names.get(item_type, item_type.replace('_', ' ').title())
        logger.debug(f"  Building {item_type} section ({len(items)} items)")
        
        # Count custom vs default for crypto profiles
        is_crypto_type = 'crypto' in item_type.lower()
        
        if is_crypto_type:
            custom_count = sum(1 for p in items if not is_default_item(p))
            default_count = len(items) - custom_count
            
            if default_count > 0 and custom_count > 0:
                count_str = f"{custom_count} custom, {default_count} default"
            elif default_count > 0:
                count_str = f"{default_count} default"
            else:
                count_str = str(len(items))
        else:
            count_str = str(len(items))
        
        type_item = self._create_item([display_name, "list", count_str])
        
        # Sort items: custom first, then default, alphabetically
        def sort_key(item):
            is_def = is_default_item(item)
            name = item.get("name", "").lower()
            return (is_def, name)
        
        sorted_items = sorted(items, key=sort_key)
        
        for item in sorted_items:
            name = item.get("name", "Unknown")
            is_default = is_default_item(item)
            
            if is_default:
                type_indicator = f"{item_type} (default)"
            else:
                type_indicator = item_type
            
            item_child = self._create_item([name, type_indicator, ""], item_type="infrastructure")
            item_child.setData(0, Qt.ItemDataRole.UserRole, {
                'type': 'infrastructure', 
                'infra_type': item_type, 
                'data': item,
                'is_default': is_default
            })
            
            # Gray out default items
            if is_default:
                item_child.setForeground(0, QColor(128, 128, 128))
                item_child.setForeground(1, QColor(128, 128, 128))
            
            type_item.addChild(item_child)
        
        parent.addChild(type_item)
    
    def _add_dict_items(self, parent: QTreeWidgetItem, data: Dict):
        """Add dictionary items to tree, recursively expanding lists and dicts."""
        for key, value in data.items():
            if isinstance(value, dict):
                item = self._create_item([str(key), "dict", ""])
                self._add_dict_items(item, value)
                parent.addChild(item)
            elif isinstance(value, list):
                item = self._create_item([str(key), "list", str(len(value))])
                # Expand list items if they're dictionaries
                for idx, list_item in enumerate(value):
                    if isinstance(list_item, dict):
                        # Try to get a name for the item
                        item_name = list_item.get("name", list_item.get("id", f"Item {idx + 1}"))
                        child_item = self._create_item([str(item_name), "dict", ""], list_item)
                        self._add_dict_items(child_item, list_item)
                        item.addChild(child_item)
                    else:
                        # Simple value in list
                        child_item = self._create_item([str(list_item), "value", ""])
                        item.addChild(child_item)
                parent.addChild(item)
            else:
                item = self._create_item([str(key), "value", str(value)])
                parent.addChild(item)
    
    def _add_item_type_node(
        self, 
        parent: QTreeWidgetItem, 
        item_type: str, 
        items_list: list, 
        container_name: str,
        container_type: str = 'folder'
    ):
        """
        Add a node for an item type with its items as children.
        
        Args:
            parent: Parent tree item (section or folder/snippet)
            item_type: The item type (e.g., 'address_object')
            items_list: List of item dictionaries
            container_name: Name of the containing folder or snippet
            container_type: 'folder' or 'snippet'
        """
        # Count custom vs default items
        custom_count = sum(1 for i in items_list if not is_default_item(i))
        default_count = len(items_list) - custom_count
        
        # Get display name from mapping, fallback to title case
        type_display = ITEM_TYPE_DISPLAY_NAMES.get(item_type, item_type.replace('_', ' ').title())
        
        # Show counts in type display
        if default_count > 0 and custom_count > 0:
            count_str = f"{custom_count} custom, {default_count} default"
        elif default_count > 0:
            count_str = f"{default_count} default"
        else:
            count_str = str(len(items_list))
        
        logger.detail(f"        Adding {len(items_list)} items of type {item_type} ({custom_count} custom, {default_count} default)")
        type_item = self._create_item([type_display, "list", count_str], item_type=f"{container_type}_{item_type}")
        type_item.setData(0, Qt.ItemDataRole.UserRole, {
            'type': f'{container_type}_{item_type}', 
            container_type: container_name, 
            'item_type': item_type
        })
        
        for item_dict in items_list:
            item_name = item_dict.get('name', 'Unknown')
            
            # Add indicator for default items
            is_default = is_default_item(item_dict)
            if is_default:
                display_type = f"{item_type} (default)"
            else:
                display_type = item_type
            
            item_child = self._create_item([item_name, display_type, ""], data=item_dict, item_type=item_type)
            item_child.setData(0, Qt.ItemDataRole.UserRole, {
                'type': item_type, 
                container_type: container_name, 
                'data': item_dict, 
                'is_default': is_default
            })
            
            # Visual indicator: gray out default items
            if is_default:
                item_child.setForeground(0, QColor(128, 128, 128))  # Gray text
                item_child.setForeground(1, QColor(128, 128, 128))
            
            type_item.addChild(item_child)
        
        parent.addChild(type_item)
    
    def _build_folders_section_new(self, parent: QTreeWidgetItem, folders: Dict[str, Any]):
        """Build folders section from new Configuration format."""
        logger.detail(f"    _build_folders_section_new called with {len(folders)} folders")
        
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
        
        # Folder ordering (priority folders first)
        FOLDER_ORDER = [
            'All',  # Global - TLD
            'Shared',  # Prisma Access - Shared folder
            'Mobile Users Container',  # Container
            'Mobile Users',
            'Mobile Users Explicit Proxy',
            'Remote Networks',
            'Service Connections',
        ]
        
        # Note: We no longer add empty 'Mobile Users Container' folder automatically
        # Only folders with actual content should be displayed
        
        if not folders:
            logger.warning("    No folders to build!")
            return
        
        folders_item = self._create_item(["Folders", "container", str(len(folders))], item_type="folders_parent")
        
        # Sort folders: priority folders first (in order), then alphabetically
        def folder_sort_key(folder_name):
            if folder_name in FOLDER_ORDER:
                return (0, FOLDER_ORDER.index(folder_name))
            else:
                return (1, folder_name.lower())
        
        sorted_folder_names = sorted(folders.keys(), key=folder_sort_key)
        
        for folder_name in sorted_folder_names:
            folder_data = folders[folder_name]
            logger.detail(f"      Processing folder: {folder_name}")
            logger.detail(f"        folder_data type: {type(folder_data)}")
            logger.detail(f"        folder_data keys: {list(folder_data.keys()) if isinstance(folder_data, dict) else 'not a dict'}")
            
            # Get display name
            display_name = FOLDER_DISPLAY_NAMES.get(folder_name, folder_name)
            
            # Create folder item with display name
            folder_item = self._create_item([display_name, "folder", ""], item_type="folder")
            folder_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'folder', 'name': folder_name, 'display_name': display_name, 'data': folder_data})
            
            # Group items by section first
            # Build a dict of section_name -> {item_type -> items_list}
            section_items: Dict[str, Dict[str, list]] = {}
            uncategorized_items: Dict[str, list] = {}  # For items not in COMPONENT_SECTIONS
            
            for item_type, items_list in folder_data.items():
                if isinstance(items_list, list) and items_list:
                    section_name = ITEM_TYPE_TO_SECTION.get(item_type)
                    if section_name:
                        if section_name not in section_items:
                            section_items[section_name] = {}
                        section_items[section_name][item_type] = items_list
                    else:
                        # Item type not in known sections (e.g., custom types)
                        uncategorized_items[item_type] = items_list
            
            # Add sections in order (only sections with items)
            for section_name in SECTION_ORDER:
                if section_name not in section_items:
                    continue
                
                # Create section node
                section_type_count = len(section_items[section_name])
                section_item_count = sum(len(items) for items in section_items[section_name].values())
                section_node = self._create_item(
                    [section_name, "section", f"{section_item_count} items"],
                    item_type=f"section_{section_name.lower().replace(' ', '_').replace('&', 'and')}"
                )
                section_node.setData(0, Qt.ItemDataRole.UserRole, {
                    'type': 'section', 
                    'name': section_name, 
                    'folder': folder_name
                })
                
                # Add item types within this section
                for item_type, items_list in section_items[section_name].items():
                    self._add_item_type_node(section_node, item_type, items_list, folder_name)
                
                folder_item.addChild(section_node)
            
            # Add any uncategorized items directly under folder
            for item_type, items_list in uncategorized_items.items():
                self._add_item_type_node(folder_item, item_type, items_list, folder_name)
            
            folders_item.addChild(folder_item)
        
        logger.detail(f"    Adding folders_item to parent")
        parent.addChild(folders_item)
    
    def _build_snippets_section_new(self, parent: QTreeWidgetItem, snippets: Dict[str, Any]):
        """Build snippets section from new Configuration format with section grouping."""
        logger.detail(f"  _build_snippets_section_new: received {len(snippets) if snippets else 0} snippets")
        if snippets:
            logger.detail(f"    Snippet names: {list(snippets.keys())}")
        if not snippets:
            logger.detail(f"    No snippets to display")
            return
        
        snippets_item = self._create_item(["Snippets", "container", str(len(snippets))], item_type="snippets_parent")
        
        for snippet_name, snippet_data in snippets.items():
            # Create snippet item
            snippet_item = self._create_item([snippet_name, "snippet", ""], item_type="snippet")
            snippet_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'snippet', 'name': snippet_name, 'data': snippet_data})
            
            # Group items by section first (same as folders)
            section_items: Dict[str, Dict[str, list]] = {}
            uncategorized_items: Dict[str, list] = {}
            
            for item_type, items_list in snippet_data.items():
                if isinstance(items_list, list) and items_list:
                    section_name = ITEM_TYPE_TO_SECTION.get(item_type)
                    if section_name:
                        if section_name not in section_items:
                            section_items[section_name] = {}
                        section_items[section_name][item_type] = items_list
                    else:
                        uncategorized_items[item_type] = items_list
            
            # Add sections in order (only sections with items)
            for section_name in SECTION_ORDER:
                if section_name not in section_items:
                    continue
                
                # Create section node
                section_item_count = sum(len(items) for items in section_items[section_name].values())
                section_node = self._create_item(
                    [section_name, "section", f"{section_item_count} items"],
                    item_type=f"section_{section_name.lower().replace(' ', '_').replace('&', 'and')}"
                )
                section_node.setData(0, Qt.ItemDataRole.UserRole, {
                    'type': 'section',
                    'name': section_name,
                    'snippet': snippet_name
                })
                
                # Add item types within this section
                for item_type, items_list in section_items[section_name].items():
                    self._add_item_type_node(section_node, item_type, items_list, snippet_name, container_type='snippet')
                
                snippet_item.addChild(section_node)
            
            # Add any uncategorized items directly under snippet
            for item_type, items_list in uncategorized_items.items():
                self._add_item_type_node(snippet_item, item_type, items_list, snippet_name, container_type='snippet')
            
            snippets_item.addChild(snippet_item)
        
        parent.addChild(snippets_item)
