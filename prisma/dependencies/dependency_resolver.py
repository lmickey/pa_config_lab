"""
Dependency Resolution for Prisma Access Configurations.

This module provides functionality to map and resolve dependencies between
configuration objects (address groups → addresses, rules → profiles, etc.).
"""

from typing import Dict, List, Set, Optional, Any
from collections import defaultdict
from .dependency_graph import DependencyGraph, DependencyNode


class DependencyResolver:
    """Resolve dependencies between Prisma Access configuration objects."""

    def __init__(self):
        """Initialize dependency resolver."""
        self.graph = DependencyGraph()
        self.resolved_dependencies: Dict[str, Set[str]] = {}
        self.missing_dependencies: Dict[str, List[str]] = {}

    def build_dependency_graph(self, config: Dict[str, Any]) -> DependencyGraph:
        """
        Build dependency graph from configuration.

        Args:
            config: Configuration dictionary (v2.0 schema)

        Returns:
            DependencyGraph with all dependencies mapped
        """
        self.graph = DependencyGraph()

        # Process security policies
        if "security_policies" in config:
            security_policies = config["security_policies"]

            # Process folders
            if "folders" in security_policies:
                for folder in security_policies["folders"]:
                    self._process_folder_dependencies(folder)

            # Process snippets
            if "snippets" in security_policies:
                for snippet in security_policies["snippets"]:
                    self._process_snippet_dependencies(snippet)
        
        # Process infrastructure
        if "infrastructure" in config:
            self._process_infrastructure_dependencies(config["infrastructure"])

        return self.graph

    def _process_folder_dependencies(self, folder: Dict[str, Any]):
        """Process dependencies within a folder."""
        folder_name = folder.get("name", "")

        # Process objects and their dependencies
        objects = folder.get("objects", {})

        # Address objects
        address_objects = objects.get("address_objects", [])
        for addr_obj in address_objects:
            obj_name = addr_obj.get("name", "")
            if obj_name:
                self.graph.add_node(
                    obj_name, "address_object", {"folder": folder_name, **addr_obj}
                )

        # Address groups → address objects
        address_groups = objects.get("address_groups", [])
        for addr_group in address_groups:
            group_name = addr_group.get("name", "")
            if group_name:
                self.graph.add_node(
                    group_name, "address_group", {"folder": folder_name, **addr_group}
                )

                # Add dependencies on address objects
                static_addresses = addr_group.get("static", [])
                dynamic_addresses = addr_group.get("dynamic", [])

                for addr_name in static_addresses:
                    if isinstance(addr_name, str):
                        self.graph.add_dependency(
                            group_name, addr_name, "address_group", "address_object"
                        )
                    elif isinstance(addr_name, dict):
                        addr_name_str = addr_name.get("name", "")
                        if addr_name_str:
                            self.graph.add_dependency(
                                group_name,
                                addr_name_str,
                                "address_group",
                                "address_object",
                            )

                for addr_name in dynamic_addresses:
                    if isinstance(addr_name, str):
                        self.graph.add_dependency(
                            group_name, addr_name, "address_group", "address_object"
                        )
                    elif isinstance(addr_name, dict):
                        addr_name_str = addr_name.get("name", "")
                        if addr_name_str:
                            self.graph.add_dependency(
                                group_name,
                                addr_name_str,
                                "address_group",
                                "address_object",
                            )

        # Service objects
        service_objects = objects.get("service_objects", [])
        for svc_obj in service_objects:
            obj_name = svc_obj.get("name", "")
            if obj_name:
                self.graph.add_node(
                    obj_name, "service_object", {"folder": folder_name, **svc_obj}
                )

        # Service groups → service objects
        service_groups = objects.get("service_groups", [])
        for svc_group in service_groups:
            group_name = svc_group.get("name", "")
            if group_name:
                self.graph.add_node(
                    group_name, "service_group", {"folder": folder_name, **svc_group}
                )

                # Add dependencies on service objects
                services = svc_group.get("services", [])
                for svc_name in services:
                    if isinstance(svc_name, str):
                        self.graph.add_dependency(
                            group_name, svc_name, "service_group", "service_object"
                        )
                    elif isinstance(svc_name, dict):
                        svc_name_str = svc_name.get("name", "")
                        if svc_name_str:
                            self.graph.add_dependency(
                                group_name,
                                svc_name_str,
                                "service_group",
                                "service_object",
                            )

        # Process profiles
        profiles = folder.get("profiles", {})

        # Authentication profiles
        auth_profiles = profiles.get("authentication_profiles", [])
        for auth_profile in auth_profiles:
            profile_name = auth_profile.get("name", "")
            if profile_name:
                self.graph.add_node(
                    profile_name,
                    "authentication_profile",
                    {"folder": folder_name, **auth_profile},
                )

        # Security profiles
        security_profiles = profiles.get("security_profiles", {})
        for profile_type, profile_list in security_profiles.items():
            if isinstance(profile_list, list):
                for profile in profile_list:
                    profile_name = profile.get("name", "")
                    if profile_name:
                        self.graph.add_node(
                            profile_name,
                            f"security_profile_{profile_type}",
                            {"folder": folder_name, **profile},
                        )

        # Decryption profiles
        decryption_profiles = profiles.get("decryption_profiles", [])
        for dec_profile in decryption_profiles:
            profile_name = dec_profile.get("name", "")
            if profile_name:
                self.graph.add_node(
                    profile_name,
                    "decryption_profile",
                    {"folder": folder_name, **dec_profile},
                )

        # Process rules → profiles and objects
        rules = folder.get("security_rules", [])
        for rule in rules:
            rule_name = rule.get("name", "")
            if not rule_name:
                rule_name = f"rule_{rule.get('position', 'unknown')}"

            self.graph.add_node(
                rule_name, "security_rule", {"folder": folder_name, **rule}
            )

            # Rule → Authentication profile
            auth_profile = rule.get("authentication_profile", [])
            if isinstance(auth_profile, list) and auth_profile:
                for profile_name in auth_profile:
                    if isinstance(profile_name, str):
                        self.graph.add_dependency(
                            rule_name,
                            profile_name,
                            "security_rule",
                            "authentication_profile",
                        )

            # Rule → Security profiles
            profile_group = rule.get("profile_group", [])
            if isinstance(profile_group, list) and profile_group:
                for profile_name in profile_group:
                    if isinstance(profile_name, str):
                        # Try to find matching security profile
                        self.graph.add_dependency(
                            rule_name, profile_name, "security_rule", "security_profile"
                        )

            # Rule → Decryption profile
            decryption_profile = rule.get("decryption_profile", [])
            if isinstance(decryption_profile, list) and decryption_profile:
                for profile_name in decryption_profile:
                    if isinstance(profile_name, str):
                        self.graph.add_dependency(
                            rule_name,
                            profile_name,
                            "security_rule",
                            "decryption_profile",
                        )

            # Rule → Address objects/groups
            source_addresses = rule.get("source", [])
            dest_addresses = rule.get("destination", [])

            for addr_name in source_addresses + dest_addresses:
                if isinstance(addr_name, str) and addr_name.lower() != "any":
                    # Could be address object or group
                    self.graph.add_dependency(
                        rule_name, addr_name, "security_rule", "address_object"
                    )

            # Rule → Service objects/groups
            services = rule.get("service", [])
            for svc_name in services:
                if isinstance(svc_name, str) and svc_name.lower() != "any":
                    # Could be service object or group
                    self.graph.add_dependency(
                        rule_name, svc_name, "security_rule", "service_object"
                    )

    def _process_snippet_dependencies(self, snippet: Dict[str, Any]):
        """Process dependencies within a snippet."""
        # Snippets are metadata containers, so they typically don't have
        # the same level of dependencies as folders
        snippet_name = snippet.get("name", "")
        if snippet_name:
            self.graph.add_node(snippet_name, "snippet", snippet)
    
    def _process_infrastructure_dependencies(self, infrastructure: Dict[str, Any]):
        """Process dependencies within infrastructure components."""
        
        # Process IKE Crypto Profiles (no dependencies)
        ike_crypto_profiles = infrastructure.get("ike_crypto_profiles", [])
        for profile in ike_crypto_profiles:
            profile_name = profile.get("name", "")
            if profile_name:
                self.graph.add_node(profile_name, "ike_crypto_profile", profile)
        
        # Process IPSec Crypto Profiles (no dependencies)
        ipsec_crypto_profiles = infrastructure.get("ipsec_crypto_profiles", [])
        for profile in ipsec_crypto_profiles:
            profile_name = profile.get("name", "")
            if profile_name:
                self.graph.add_node(profile_name, "ipsec_crypto_profile", profile)
        
        # Process IKE Gateways → IKE Crypto Profile
        ike_gateways = infrastructure.get("ike_gateways", [])
        for gateway in ike_gateways:
            gateway_name = gateway.get("name", "")
            if gateway_name:
                self.graph.add_node(gateway_name, "ike_gateway", gateway)
                
                # IKE Gateway depends on IKE Crypto Profile
                ike_crypto_profile = gateway.get("protocol", {}).get("ikev1", {}).get("ike_crypto_profile")
                if not ike_crypto_profile:
                    ike_crypto_profile = gateway.get("protocol", {}).get("ikev2", {}).get("ike_crypto_profile")
                
                if ike_crypto_profile:
                    self.graph.add_dependency(
                        gateway_name, ike_crypto_profile, "ike_gateway", "ike_crypto_profile"
                    )
        
        # Process IPSec Tunnels → IKE Gateway + IPSec Crypto Profile
        ipsec_tunnels = infrastructure.get("ipsec_tunnels", [])
        for tunnel in ipsec_tunnels:
            tunnel_name = tunnel.get("name", "")
            if tunnel_name:
                self.graph.add_node(tunnel_name, "ipsec_tunnel", tunnel)
                
                # IPSec Tunnel depends on IKE Gateway (auto_key)
                auto_key = tunnel.get("auto_key", {})
                ike_gateway_name = auto_key.get("ike_gateway", {})
                if isinstance(ike_gateway_name, list) and ike_gateway_name:
                    ike_gateway_name = ike_gateway_name[0]
                if isinstance(ike_gateway_name, dict):
                    ike_gateway_name = ike_gateway_name.get("name", "")
                
                if ike_gateway_name:
                    self.graph.add_dependency(
                        tunnel_name, ike_gateway_name, "ipsec_tunnel", "ike_gateway"
                    )
                
                # IPSec Tunnel depends on IPSec Crypto Profile
                ipsec_crypto_profile = auto_key.get("ipsec_crypto_profile")
                if ipsec_crypto_profile:
                    self.graph.add_dependency(
                        tunnel_name, ipsec_crypto_profile, "ipsec_tunnel", "ipsec_crypto_profile"
                    )
        
        # Process Service Connections → IPSec Tunnel
        service_connections = infrastructure.get("service_connections", [])
        for sc in service_connections:
            sc_name = sc.get("name", "")
            if sc_name:
                self.graph.add_node(sc_name, "service_connection", sc)
                
                # Service Connection depends on IPSec Tunnel (if using IPSec)
                ipsec_tunnel = sc.get("ipsec_tunnel")
                if ipsec_tunnel:
                    self.graph.add_dependency(
                        sc_name, ipsec_tunnel, "service_connection", "ipsec_tunnel"
                    )
                
                # Service Connection may also depend on BGP peer (if configured)
                bgp_peer = sc.get("bgp_peer", {}).get("local_ip_address")
                # BGP peer dependencies are complex and may require further analysis
        
        # Process Remote Networks (may have dependencies on IKE Gateways/IPSec Tunnels)
        remote_networks = infrastructure.get("remote_networks", [])
        for rn in remote_networks:
            rn_name = rn.get("name", "")
            if rn_name:
                self.graph.add_node(rn_name, "remote_network", rn)
                
                # Remote Network may depend on IPSec Tunnel
                ipsec_tunnel = rn.get("ipsec_tunnel")
                if ipsec_tunnel:
                    self.graph.add_dependency(
                        rn_name, ipsec_tunnel, "remote_network", "ipsec_tunnel"
                    )

    def validate_dependencies(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that all dependencies are present in configuration.

        Args:
            config: Configuration dictionary

        Returns:
            Dictionary with validation results
        """
        # Build graph
        self.build_dependency_graph(config)

        # Get all available nodes
        available_nodes = set(self.graph.nodes.keys())

        # Find missing dependencies
        missing = self.graph.find_missing_dependencies(available_nodes)

        # Check for cycles
        has_cycles = self.graph.has_cycles()

        # Get statistics
        stats = self.graph.get_statistics()

        return {
            "valid": len(missing) == 0 and not has_cycles,
            "missing_dependencies": missing,
            "has_cycles": has_cycles,
            "statistics": stats,
            "total_nodes": len(self.graph.nodes),
            "total_dependencies": len(self.graph.edges),
        }

    def get_resolution_order(self, config: Dict[str, Any]) -> List[str]:
        """
        Get order for resolving dependencies (dependencies before dependents).

        Args:
            config: Configuration dictionary

        Returns:
            List of node IDs in resolution order
        """
        self.build_dependency_graph(config)
        return self.graph.get_topological_order()

    def get_push_order(self, config: Dict[str, Any]) -> List[str]:
        """
        Get order for pushing configurations (dependencies before dependents).

        Args:
            config: Configuration dictionary

        Returns:
            List of node IDs in push order
        """
        return self.get_resolution_order(config)

    def find_required_dependencies(self, selected_config: Dict[str, Any], full_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find dependencies required by selected items that are available in full config.
        
        Args:
            selected_config: Configuration with only selected items
            full_config: Full configuration to search for dependencies
            
        Returns:
            Dictionary with required dependencies organized by type
        """
        # Validate selected config to find missing deps
        validation = self.validate_dependencies(selected_config)
        missing_deps = validation.get('missing_dependencies', [])
        
        if not missing_deps:
            return {}
        
        # Extract missing dependency names and types
        required = {
            'folders': [],
            'snippets': [],
            'objects': {},
            'profiles': [],
            'infrastructure': {}
        }
        
        # Search full config for missing dependencies
        for dep in missing_deps:
            dep_name = dep.get('name', '')
            dep_type = dep.get('type', '')
            
            if not dep_name:
                continue
            
            # Search in folders
            if dep_type in ['folder']:
                folders = full_config.get('security_policies', {}).get('folders', [])
                for folder in folders:
                    if folder.get('name') == dep_name:
                        required['folders'].append(folder)
                        break
            
            # Search in objects
            elif dep_type in ['address_object', 'address_group', 'service_object', 'service_group', 
                             'application_object', 'application_group']:
                objects = full_config.get('objects', {})
                
                # Map dependency types to object keys
                type_map = {
                    'address_object': 'addresses',
                    'address_group': 'address_groups',
                    'service_object': 'services',
                    'service_group': 'service_groups',
                    'application_object': 'applications',
                    'application_group': 'application_groups'
                }
                
                obj_key = type_map.get(dep_type)
                if obj_key and obj_key in objects:
                    for obj in objects[obj_key]:
                        if obj.get('name') == dep_name:
                            if obj_key not in required['objects']:
                                required['objects'][obj_key] = []
                            required['objects'][obj_key].append(obj)
                            break
            
            # Search in profiles
            elif dep_type in ['security_profile', 'url_filtering_profile', 'file_blocking_profile',
                             'wildfire_profile', 'decryption_profile', 'authentication_profile']:
                # Profiles would be in folders
                folders = full_config.get('security_policies', {}).get('folders', [])
                for folder in folders:
                    profiles = folder.get('profiles', {})
                    for profile_type, profile_list in profiles.items():
                        if isinstance(profile_list, list):
                            for profile in profile_list:
                                if profile.get('name') == dep_name:
                                    required['profiles'].append(profile)
                                    break
            
            # Search in infrastructure
            elif dep_type in ['ike_crypto_profile', 'ipsec_crypto_profile', 'ike_gateway', 
                             'ipsec_tunnel', 'service_connection', 'remote_network']:
                infrastructure = full_config.get('infrastructure', {})
                
                # Map dependency types to infrastructure keys
                type_map = {
                    'ike_crypto_profile': 'ike_crypto_profiles',
                    'ipsec_crypto_profile': 'ipsec_crypto_profiles',
                    'ike_gateway': 'ike_gateways',
                    'ipsec_tunnel': 'ipsec_tunnels',
                    'service_connection': 'service_connections',
                    'remote_network': 'remote_networks'
                }
                
                infra_key = type_map.get(dep_type)
                if infra_key:
                    infra_items = infrastructure.get(infra_key, [])
                    for item in infra_items:
                        if item.get('name') == dep_name:
                            # Store in infrastructure dict by type
                            if infra_key not in required['infrastructure']:
                                required['infrastructure'][infra_key] = []
                            required['infrastructure'][infra_key].append(item)
                            break
        
        # Remove empty categories
        required = {k: v for k, v in required.items() if v}
        
        return required
    
    def get_dependency_report(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate dependency report for configuration.

        Args:
            config: Configuration dictionary

        Returns:
            Dictionary with dependency report
        """
        validation = self.validate_dependencies(config)
        stats = self.graph.get_statistics()

        # Group dependencies by type
        dependencies_by_type = defaultdict(list)
        for from_id, to_id in self.graph.edges:
            from_node = self.graph.get_node(from_id)
            to_node = self.graph.get_node(to_id)
            if from_node and to_node:
                dep_type = f"{from_node.type} → {to_node.type}"
                dependencies_by_type[dep_type].append(
                    {
                        "from": from_id,
                        "to": to_id,
                        "from_type": from_node.type,
                        "to_type": to_node.type,
                    }
                )

        return {
            "validation": validation,
            "statistics": stats,
            "dependencies_by_type": dict(dependencies_by_type),
            "resolution_order": self.get_resolution_order(config),
            "missing_dependencies": validation.get("missing_dependencies", {}),
            "has_cycles": validation.get("has_cycles", False),
        }
