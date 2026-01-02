"""
Shared configuration tree builder.

This module provides a reusable tree-building component for displaying
Prisma Access configurations. Used by both the config viewer and
component selection dialog to ensure consistency.
"""

from typing import Dict, Any, Optional, Callable
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PyQt6.QtCore import Qt


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
        tree.clear()
        root = tree.invisibleRootItem()
        
        # Build each section
        if not self.simplified:
            # Only show metadata in viewer mode
            self._build_metadata_section(root, config)
        
        self._build_security_policies_section(root, config)
        self._build_objects_section(root, config)
        self._build_infrastructure_section(root, config)
        
        # Expand top level
        tree.expandToDepth(0)
    
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
        """Build security policies section (folders and snippets)."""
        sec_policies = config.get("security_policies", {})
        if not sec_policies:
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
            return
        
        infra_item = self._create_item(["Infrastructure", "container", ""])
        
        # Remote Networks
        remote_networks = infrastructure.get("remote_networks", [])
        if remote_networks:
            rn_item = self._create_item(["Remote Networks", "list", str(len(remote_networks))])
            for rn in remote_networks:
                name = rn.get("name", "Unknown")
                rn_child = self._create_item([name, "remote_network", ""], item_type="infrastructure")
                rn_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'infrastructure', 'infra_type': 'remote_networks', 'data': rn})
                rn_item.addChild(rn_child)
            infra_item.addChild(rn_item)
        
        # Service Connections
        service_connections = infrastructure.get("service_connections", [])
        if service_connections:
            sc_item = self._create_item(["Service Connections", "list", str(len(service_connections))])
            for sc in service_connections:
                name = sc.get("name", "Unknown")
                sc_child = self._create_item([name, "service_connection", ""], item_type="infrastructure")
                sc_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'infrastructure', 'infra_type': 'service_connections', 'data': sc})
                sc_item.addChild(sc_child)
            infra_item.addChild(sc_item)
        
        # IPSec Tunnels
        ipsec_tunnels = infrastructure.get("ipsec_tunnels", [])
        if ipsec_tunnels:
            it_item = self._create_item(["IPSec Tunnels", "list", str(len(ipsec_tunnels))])
            for it in ipsec_tunnels:
                name = it.get("name", "Unknown")
                it_child = self._create_item([name, "ipsec_tunnel", ""], item_type="infrastructure")
                it_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'infrastructure', 'infra_type': 'ipsec_tunnels', 'data': it})
                it_item.addChild(it_child)
            infra_item.addChild(it_item)
        
        # IKE Gateways
        ike_gateways = infrastructure.get("ike_gateways", [])
        if ike_gateways:
            ike_item = self._create_item(["IKE Gateways", "list", str(len(ike_gateways))])
            for ike in ike_gateways:
                name = ike.get("name", "Unknown")
                ike_child = self._create_item([name, "ike_gateway", ""], item_type="infrastructure")
                ike_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'infrastructure', 'infra_type': 'ike_gateways', 'data': ike})
                ike_item.addChild(ike_child)
            infra_item.addChild(ike_item)
        
        # IKE Crypto Profiles
        ike_crypto_profiles = infrastructure.get("ike_crypto_profiles", [])
        if ike_crypto_profiles:
            ike_crypto_item = self._create_item(["IKE Crypto Profiles", "list", str(len(ike_crypto_profiles))])
            
            # Sort: custom first (snippet != 'default'), then default, alphabetically
            def crypto_sort_key(p):
                snippet = p.get("snippet", "")
                is_default = snippet == "default"
                name = p.get("name", "").lower()
                return (is_default, name)
            
            sorted_profiles = sorted(ike_crypto_profiles, key=crypto_sort_key)
            
            for prof in sorted_profiles:
                name = prof.get("name", "Unknown")
                snippet = prof.get("snippet", "")
                type_indicator = "default" if snippet == "default" else "custom"
                prof_child = self._create_item([name, type_indicator, ""], item_type="infrastructure")
                prof_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'infrastructure', 'infra_type': 'ike_crypto_profiles', 'data': prof})
                ike_crypto_item.addChild(prof_child)
            infra_item.addChild(ike_crypto_item)
        
        # IPSec Crypto Profiles
        ipsec_crypto_profiles = infrastructure.get("ipsec_crypto_profiles", [])
        if ipsec_crypto_profiles:
            ipsec_crypto_item = self._create_item(["IPSec Crypto Profiles", "list", str(len(ipsec_crypto_profiles))])
            
            # Sort: custom first (snippet != 'default'), then default, alphabetically
            def crypto_sort_key(p):
                snippet = p.get("snippet", "")
                is_default = snippet == "default"
                name = p.get("name", "").lower()
                return (is_default, name)
            
            sorted_profiles = sorted(ipsec_crypto_profiles, key=crypto_sort_key)
            
            for prof in sorted_profiles:
                name = prof.get("name", "Unknown")
                snippet = prof.get("snippet", "")
                type_indicator = "default" if snippet == "default" else "custom"
                prof_child = self._create_item([name, type_indicator, ""], item_type="infrastructure")
                prof_child.setData(0, Qt.ItemDataRole.UserRole, {'type': 'infrastructure', 'infra_type': 'ipsec_crypto_profiles', 'data': prof})
                ipsec_crypto_item.addChild(prof_child)
            infra_item.addChild(ipsec_crypto_item)
        
        # Mobile Users
        mobile_users = infrastructure.get("mobile_users", {})
        if mobile_users:
            if self.simplified:
                # Simplified mode: Show high-level items as pushable units
                mu_item = self._create_item(["Mobile Users", "container", ""], item_type="infrastructure")
                mu_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'infrastructure', 'infra_type': 'mobile_users', 'data': mobile_users})
                
                # Show major components as individual pushable items
                if mobile_users.get("agent_profiles"):
                    profiles = mobile_users["agent_profiles"]
                    count = len(profiles) if isinstance(profiles, list) else 1
                    prof_item = self._create_item([f"Agent Profiles ({count})", "mobile_users", ""], item_type="infrastructure")
                    prof_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'infrastructure', 'infra_type': 'agent_profiles', 'data': profiles})
                    mu_item.addChild(prof_item)
                
                if mobile_users.get("agent_versions"):
                    # Agent versions - just show as single item (will push activated version)
                    ver_item = self._create_item(["Agent Versions", "mobile_users", ""], item_type="infrastructure")
                    ver_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'infrastructure', 'infra_type': 'agent_versions', 'data': mobile_users["agent_versions"]})
                    mu_item.addChild(ver_item)
                
                # Other mobile user settings as single items
                for key in ["authentication_settings", "infrastructure_settings", "onboarding", "portal_settings"]:
                    if mobile_users.get(key):
                        display_name = key.replace("_", " ").title()
                        item = self._create_item([display_name, "mobile_users", ""], item_type="infrastructure")
                        item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'infrastructure', 'infra_type': key, 'data': mobile_users[key]})
                        mu_item.addChild(item)
                
                infra_item.addChild(mu_item)
            else:
                # Full detail mode for viewer
                mu_item = self._create_item(["Mobile Users", "dict", ""])
                self._add_dict_items(mu_item, mobile_users)
                infra_item.addChild(mu_item)
        
        # Regions
        regions = infrastructure.get("regions", {})
        if regions:
            if self.simplified:
                # Simplified mode: Show as single pushable item
                reg_item = self._create_item(["Regions", "infrastructure", ""], item_type="infrastructure")
                reg_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'infrastructure', 'infra_type': 'regions', 'data': regions})
                infra_item.addChild(reg_item)
            else:
                # Full detail mode for viewer
                reg_item = self._create_item(["Regions", "dict", ""])
                self._add_dict_items(reg_item, regions)
                infra_item.addChild(reg_item)
        
        root.addChild(infra_item)
    
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
