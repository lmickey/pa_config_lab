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
        
        print(f"\nDEBUG: Processing infrastructure dependencies")
        print(f"  Infrastructure keys: {list(infrastructure.keys())}")
        
        # Process IKE Crypto Profiles (no dependencies)
        ike_crypto_profiles = infrastructure.get("ike_crypto_profiles", [])
        print(f"  IKE Crypto Profiles: {len(ike_crypto_profiles)}")
        for profile in ike_crypto_profiles:
            profile_name = profile.get("name", "")
            if profile_name:
                self.graph.add_node(profile_name, "ike_crypto_profile", profile)
                print(f"    Added node: {profile_name}")
        
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
                    # Don't auto-create the crypto profile node
                    self.graph.add_dependency(
                        gateway_name, ike_crypto_profile, "ike_gateway", None
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
                    # Don't auto-create the gateway node
                    self.graph.add_dependency(
                        tunnel_name, ike_gateway_name, "ipsec_tunnel", None
                    )
                
                # IPSec Tunnel depends on IPSec Crypto Profile
                ipsec_crypto_profile = auto_key.get("ipsec_crypto_profile")
                if ipsec_crypto_profile:
                    # Don't auto-create the crypto profile node
                    self.graph.add_dependency(
                        tunnel_name, ipsec_crypto_profile, "ipsec_tunnel", None
                    )
        
        # Process Service Connections → IPSec Tunnel
        service_connections = infrastructure.get("service_connections", [])
        print(f"  Service Connections: {len(service_connections)}")
        for sc in service_connections:
            sc_name = sc.get("name", "")
            if sc_name:
                self.graph.add_node(sc_name, "service_connection", sc)
                print(f"    Added node: {sc_name}")
                print(f"    Service connection keys: {list(sc.keys())}")
                
                # Service Connection depends on IPSec Tunnel (if using IPSec)
                ipsec_tunnel = sc.get("ipsec_tunnel")
                print(f"    Looking for ipsec_tunnel field: {ipsec_tunnel}")
                if ipsec_tunnel:
                    # Add dependency - pass the type so the edge gets created
                    # The tunnel node will be created as a "reference", and if it's not in the actual
                    # config, it will be flagged as missing
                    self.graph.add_dependency(
                        sc_name, ipsec_tunnel, "service_connection", "ipsec_tunnel"
                    )
                    print(f"    Added dependency: {sc_name} -> {ipsec_tunnel}")
                else:
                    print(f"    No ipsec_tunnel field found")
                
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
                    # Don't auto-create the tunnel node
                    self.graph.add_dependency(
                        rn_name, ipsec_tunnel, "remote_network", None
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

        # Get all available nodes (only non-reference nodes that are actually in the config)
        available_nodes = set(node_id for node_id, node in self.graph.nodes.items() 
                             if not getattr(node, 'is_reference', False))
        
        print(f"DEBUG: Available nodes (non-reference): {available_nodes}")
        print(f"DEBUG: All nodes in graph: {set(self.graph.nodes.keys())}")

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
        Find ALL dependencies required by selected items (recursively resolving transitive deps).
        
        Args:
            selected_config: Configuration with only selected items
            full_config: Full configuration to search for dependencies
            
        Returns:
            Dictionary with required dependencies organized by type
        """
        # Accumulate all required dependencies
        all_required = {
            'folders': [],
            'snippets': [],
            'objects': {},
            'profiles': [],
            'infrastructure': {}
        }
        
        # Keep a copy of the config we're analyzing (will grow as we add deps)
        working_config = self._deep_copy_config(selected_config)
        
        # Track what we've already added to avoid infinite loops
        added_names = set()
        
        # Keep finding dependencies until there are none left
        max_iterations = 10  # Safety limit
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            print(f"\nDEBUG: Dependency resolution iteration {iteration}")
            
            # Validate working config to find missing deps
            validation = self.validate_dependencies(working_config)
            missing_deps_dict = validation.get('missing_dependencies', {})
            
            print(f"  Total nodes in graph: {len(self.graph.nodes)}")
            print(f"  Nodes: {list(self.graph.nodes.keys())}")
            print(f"  Total edges in graph: {len(self.graph.edges)}")
            print(f"  Edges: {[(f'{e[0]}->{e[1]}') for e in self.graph.edges]}")
            print(f"  Missing dependencies dict: {missing_deps_dict}")
            
            # Convert missing_deps dict to list
            missing_deps = []
            for node_id, missing_dep_names in missing_deps_dict.items():
                for dep_name in missing_dep_names:
                    if dep_name not in added_names:
                        missing_deps.append({
                            'name': dep_name,
                            'type': 'unknown',
                            'referenced_by': node_id
                        })
            
            print(f"  Missing dependencies list: {len(missing_deps)}")
            for dep in missing_deps:
                print(f"    - {dep.get('name')} (referenced by: {dep.get('referenced_by')})")
            
            # If no missing dependencies, we're done
            if not missing_deps:
                print(f"  No more missing dependencies found after {iteration} iteration(s)")
                break
            
            # Search full config for missing dependencies and add to working config
            found_any = False
            for dep in missing_deps:
                dep_name = dep.get('name', '')
                
                if not dep_name or dep_name in added_names:
                    continue
                
                print(f"\n  Searching for dependency: {dep_name}")
                
                try:
                    # Try infrastructure
                    found = False
                    infrastructure = full_config.get('infrastructure', {})
                    for infra_key in ['ipsec_tunnels', 'ike_gateways', 'ike_crypto_profiles', 
                                     'ipsec_crypto_profiles', 'service_connections', 'remote_networks']:
                        infra_items = infrastructure.get(infra_key, [])
                        if not isinstance(infra_items, list):
                            print(f"    WARNING: {infra_key} is not a list: {type(infra_items)}")
                            continue
                            
                        for item in infra_items:
                            if not isinstance(item, dict):
                                print(f"    WARNING: Item in {infra_key} is not a dict: {type(item)}")
                                continue
                                
                            if item.get('name') == dep_name:
                                print(f"    Found in {infra_key}")
                                
                                # Add to all_required
                                if infra_key not in all_required['infrastructure']:
                                    all_required['infrastructure'][infra_key] = []
                                all_required['infrastructure'][infra_key].append(item)
                                
                                # Add to working_config so next iteration includes it
                                if infra_key not in working_config.get('infrastructure', {}):
                                    working_config.setdefault('infrastructure', {})[infra_key] = []
                                working_config['infrastructure'][infra_key].append(item)
                                
                                added_names.add(dep_name)
                                found = True
                                found_any = True
                                break
                        if found:
                            break
                    
                    if not found:
                        print(f"    NOT FOUND in infrastructure")
                    
                    # Try other types if not found in infrastructure
                    # (folders, snippets, objects, profiles - similar pattern)
                    # For now, focusing on infrastructure since that's the current use case
                
                except Exception as e:
                    import traceback
                    print(f"    ERROR searching for {dep_name}: {e}")
                    traceback.print_exc()
            
            if not found_any:
                print(f"  WARNING: Could not find some dependencies in full config")
                break
        
        if iteration >= max_iterations:
            print(f"  WARNING: Reached max iterations ({max_iterations}), stopping dependency resolution")
        
        return all_required
    
    def _deep_copy_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a deep copy of a config dict."""
        import copy
        return copy.deepcopy(config)
    
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
