"""
Shared configuration tree builder.

This module provides a reusable tree-building component for displaying
Prisma Access configurations. Used by both the config viewer and
component selection dialog to ensure consistency.
"""

import logging
from typing import Dict, Any, Optional, Callable
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

logger = logging.getLogger(__name__)


# Default snippet values that indicate system/predefined items
DEFAULT_SNIPPETS = {
    'default',           # General system defaults
    'hip-default',       # HIP-specific defaults
    'optional-default',  # Optional pre-built defaults
}


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
        logger.info("ConfigTreeBuilder.build_tree called")
        logger.info(f"  config type: {type(config)}")
        logger.info(f"  config keys: {list(config.keys()) if isinstance(config, dict) else 'not a dict'}")
        logger.info(f"  simplified mode: {self.simplified}")
        
        tree.clear()
        root = tree.invisibleRootItem()
        
        # Build each section
        if not self.simplified:
            # Only show metadata in viewer mode
            self._build_metadata_section(root, config)
        
        logger.info("  Calling _build_security_policies_section")
        self._build_security_policies_section(root, config)
        logger.info("  Calling _build_objects_section")
        self._build_objects_section(root, config)
        logger.info("  Calling _build_infrastructure_section")
        self._build_infrastructure_section(root, config)
        
        # Expand top level
        logger.info("  Expanding tree to depth 0")
        tree.expandToDepth(0)
        logger.info("  Tree building complete")
    
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
        
        logger.info(f"  _build_security_policies_section: has_folders={has_folders}, has_snippets={has_snippets}, has_security_policies={has_security_policies}")
        
        if "folders" in config or "snippets" in config:
            # New format from ConfigAdapter - add Folders and Snippets directly to root
            logger.info("  Using NEW format (folders/snippets at top level)")
            
            # Folders - added directly to root
            if config.get("folders"):
                logger.info(f"  Calling _build_folders_section_new with {len(config.get('folders', {}))} folders")
                self._build_folders_section_new(root, config.get("folders", {}))
            
            # Snippets - added directly to root
            if config.get("snippets"):
                logger.info(f"  Calling _build_snippets_section_new with {len(config.get('snippets', {}))} snippets")
                self._build_snippets_section_new(root, config.get("snippets", {}))
        
        elif has_security_policies:
            # Old format with security_policies
            logger.info("  Using OLD format (security_policies)")
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
        """Build infrastructure section."""
        infrastructure = config.get("infrastructure", {})
        if not infrastructure:
            logger.debug("No infrastructure data found")
            return
        
        logger.info(f"Building infrastructure section with keys: {list(infrastructure.keys())}")
        
        infra_item = self._create_item(["Infrastructure", "container", ""])
        
        # Mapping from item_type to display name
        # Handles both singular (from ConfigAdapter) and plural (legacy) formats
        INFRA_TYPE_DISPLAY = {
            # Singular (current format from item_type)
            'remote_network': 'Remote Networks',
            'service_connection': 'Service Connections',
            'ipsec_tunnel': 'IPSec Tunnels',
            'ike_gateway': 'IKE Gateways',
            'ike_crypto_profile': 'IKE Crypto Profiles',
            'ipsec_crypto_profile': 'IPSec Crypto Profiles',
            'agent_profile': 'Agent Profiles',
            'portal': 'Portals',
            'gateway': 'Gateways',
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
        }
        
        # Order for display
        INFRA_ORDER = [
            'remote_network', 'remote_networks',
            'service_connection', 'service_connections',
            'ike_gateway', 'ike_gateways',
            'ipsec_tunnel', 'ipsec_tunnels',
            'ike_crypto_profile', 'ike_crypto_profiles',
            'ipsec_crypto_profile', 'ipsec_crypto_profiles',
            'agent_profile', 'agent_profiles',
            'portal', 'portals',
            'gateway', 'gateways',
        ]
        
        # Sort infrastructure keys by order, then alphabetically for unknowns
        def infra_sort_key(key):
            if key in INFRA_ORDER:
                return (0, INFRA_ORDER.index(key))
            return (1, key.lower())
        
        sorted_keys = sorted(infrastructure.keys(), key=infra_sort_key)
        
        # Handle legacy nested format (items list)
        if "items" in infrastructure and isinstance(infrastructure["items"], list):
            logger.debug("Found legacy 'items' format in infrastructure")
            items_list = infrastructure["items"]
            # Group by item_type
            grouped = {}
            for item in items_list:
                item_type = item.get("item_type", "unknown")
                if item_type not in grouped:
                    grouped[item_type] = []
                grouped[item_type].append(item)
            
            # Process grouped items
            for item_type in sorted(grouped.keys(), key=infra_sort_key):
                items = grouped[item_type]
                self._build_infra_type_section(infra_item, item_type, items, INFRA_TYPE_DISPLAY)
        else:
            # New format: infrastructure is Dict[item_type, List[items]]
            for item_type in sorted_keys:
                items = infrastructure[item_type]
                
                # Skip non-list items (like nested dicts for mobile_users/regions)
                if isinstance(items, dict):
                    logger.debug(f"  {item_type} is dict, using _add_dict_items")
                    display_name = INFRA_TYPE_DISPLAY.get(item_type, item_type.replace('_', ' ').title())
                    if self.simplified:
                        type_item = self._create_item([display_name, "infrastructure", ""], item_type="infrastructure")
                        type_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'infrastructure', 'infra_type': item_type, 'data': items})
                        infra_item.addChild(type_item)
                    else:
                        type_item = self._create_item([display_name, "dict", ""])
                        self._add_dict_items(type_item, items)
                        infra_item.addChild(type_item)
                    continue
                
                if not isinstance(items, list):
                    logger.debug(f"  Skipping {item_type} (not a list: {type(items)})")
                    continue
                
                if not items:
                    logger.debug(f"  Skipping {item_type} (empty list)")
                    continue
                
                self._build_infra_type_section(infra_item, item_type, items, INFRA_TYPE_DISPLAY)
        
        root.addChild(infra_item)
    
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
    
    def _build_folders_section_new(self, parent: QTreeWidgetItem, folders: Dict[str, Any]):
        """Build folders section from new Configuration format."""
        logger.info(f"    _build_folders_section_new called with {len(folders)} folders")
        
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
        
        # Ensure Mobile Users Container exists (even if empty)
        if 'Mobile Users Container' not in folders:
            folders['Mobile Users Container'] = {}
            logger.info("    Added empty 'Mobile Users Container' folder to maintain hierarchy")
        
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
            logger.info(f"      Processing folder: {folder_name}")
            logger.info(f"        folder_data type: {type(folder_data)}")
            logger.info(f"        folder_data keys: {list(folder_data.keys()) if isinstance(folder_data, dict) else 'not a dict'}")
            
            # Get display name
            display_name = FOLDER_DISPLAY_NAMES.get(folder_name, folder_name)
            
            # Create folder item with display name
            folder_item = self._create_item([display_name, "folder", ""], item_type="folder")
            folder_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'folder', 'name': folder_name, 'display_name': display_name, 'data': folder_data})
            
            # Add items by type
            for item_type, items_list in folder_data.items():
                if isinstance(items_list, list) and items_list:
                    # Count custom vs default items
                    custom_count = sum(1 for i in items_list if not is_default_item(i))
                    default_count = len(items_list) - custom_count
                    
                    # Show counts in type display
                    type_display = item_type.replace('_', ' ').title()
                    if default_count > 0 and custom_count > 0:
                        count_str = f"{custom_count} custom, {default_count} default"
                    elif default_count > 0:
                        count_str = f"{default_count} default"
                    else:
                        count_str = str(len(items_list))
                    
                    logger.info(f"        Adding {len(items_list)} items of type {item_type} ({custom_count} custom, {default_count} default)")
                    type_item = self._create_item([type_display, "list", count_str], item_type=f"folder_{item_type}")
                    type_item.setData(0, Qt.ItemDataRole.UserRole, {'type': f'folder_{item_type}', 'folder': folder_name, 'item_type': item_type})
                    
                    for item_dict in items_list:
                        item_name = item_dict.get('name', 'Unknown')
                        
                        # Add indicator for default items
                        is_default = is_default_item(item_dict)
                        if is_default:
                            display_type = f"{item_type} (default)"
                        else:
                            display_type = item_type
                        
                        item_child = self._create_item([item_name, display_type, ""], data=item_dict, item_type=item_type)
                        item_child.setData(0, Qt.ItemDataRole.UserRole, {'type': item_type, 'folder': folder_name, 'data': item_dict, 'is_default': is_default})
                        
                        # Visual indicator: gray out default items
                        if is_default:
                            item_child.setForeground(0, QColor(128, 128, 128))  # Gray text
                            item_child.setForeground(1, QColor(128, 128, 128))
                        
                        type_item.addChild(item_child)
                    
                    folder_item.addChild(type_item)
            
            folders_item.addChild(folder_item)
        
        logger.info(f"    Adding folders_item to parent")
        parent.addChild(folders_item)
    
    def _build_snippets_section_new(self, parent: QTreeWidgetItem, snippets: Dict[str, Any]):
        """Build snippets section from new Configuration format."""
        logger.info(f"  _build_snippets_section_new: received {len(snippets) if snippets else 0} snippets")
        if snippets:
            logger.info(f"    Snippet names: {list(snippets.keys())}")
        if not snippets:
            logger.info(f"    No snippets to display")
            return
        
        snippets_item = self._create_item(["Snippets", "container", str(len(snippets))], item_type="snippets_parent")
        
        for snippet_name, snippet_data in snippets.items():
            # Create snippet item
            snippet_item = self._create_item([snippet_name, "snippet", ""], item_type="snippet")
            snippet_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'snippet', 'name': snippet_name, 'data': snippet_data})
            
            # Add items by type
            for item_type, items_list in snippet_data.items():
                if isinstance(items_list, list) and items_list:
                    # Count custom vs default items
                    custom_count = sum(1 for i in items_list if not is_default_item(i))
                    default_count = len(items_list) - custom_count
                    
                    # Show counts in type display
                    type_display = item_type.replace('_', ' ').title()
                    if default_count > 0 and custom_count > 0:
                        count_str = f"{custom_count} custom, {default_count} default"
                    elif default_count > 0:
                        count_str = f"{default_count} default"
                    else:
                        count_str = str(len(items_list))
                    
                    type_item = self._create_item([type_display, "list", count_str], item_type=f"snippet_{item_type}")
                    type_item.setData(0, Qt.ItemDataRole.UserRole, {'type': f'snippet_{item_type}', 'snippet': snippet_name, 'item_type': item_type})
                    
                    for item_dict in items_list:
                        item_name = item_dict.get('name', 'Unknown')
                        
                        # Add indicator for default items
                        is_default = is_default_item(item_dict)
                        if is_default:
                            display_type = f"{item_type} (default)"
                        else:
                            display_type = item_type
                        
                        item_child = self._create_item([item_name, display_type, ""], data=item_dict, item_type=item_type)
                        item_child.setData(0, Qt.ItemDataRole.UserRole, {'type': item_type, 'snippet': snippet_name, 'data': item_dict, 'is_default': is_default})
                        
                        # Visual indicator: gray out default items
                        if is_default:
                            item_child.setForeground(0, QColor(128, 128, 128))  # Gray text
                            item_child.setForeground(1, QColor(128, 128, 128))
                        
                        type_item.addChild(item_child)
                    
                    snippet_item.addChild(type_item)
            
            snippets_item.addChild(snippet_item)
        
        parent.addChild(snippets_item)
