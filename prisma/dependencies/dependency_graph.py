"""
Dependency Graph Structure for Prisma Access Configurations.

This module provides a graph structure to represent dependencies between
configuration objects (address groups → addresses, rules → profiles, etc.).
"""

from typing import Dict, List, Set, Optional, Any, Tuple
from collections import defaultdict, deque


class DependencyNode:
    """Represents a node in the dependency graph."""

    def __init__(
        self, node_id: str, node_type: str, data: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize dependency node.

        Args:
            node_id: Unique identifier for the node (e.g., object name)
            node_type: Type of node (e.g., 'address_object', 'address_group', 'rule', 'profile')
            data: Optional data dictionary for the node
        """
        self.id = node_id
        self.type = node_type
        self.data = data or {}
        self.dependencies: Set[str] = set()  # Nodes this node depends on
        self.dependents: Set[str] = set()  # Nodes that depend on this node

    def add_dependency(self, node_id: str):
        """Add a dependency to this node."""
        self.dependencies.add(node_id)

    def add_dependent(self, node_id: str):
        """Add a dependent to this node."""
        self.dependents.add(node_id)

    def __repr__(self):
        return f"DependencyNode(id={self.id}, type={self.type}, deps={len(self.dependencies)}, dependents={len(self.dependents)})"


class DependencyGraph:
    """Graph structure for tracking dependencies between configuration objects."""

    def __init__(self):
        """Initialize dependency graph."""
        self.nodes: Dict[str, DependencyNode] = {}
        self.edges: List[Tuple[str, str]] = []  # (from_node, to_node) tuples

    def add_node(
        self, node_id: str, node_type: str, data: Optional[Dict[str, Any]] = None
    ) -> DependencyNode:
        """
        Add a node to the graph.

        Args:
            node_id: Unique identifier for the node
            node_type: Type of node
            data: Optional data dictionary

        Returns:
            The created or existing node
        """
        if node_id not in self.nodes:
            node = DependencyNode(node_id, node_type, data)
            # Mark as reference if data is None/empty
            node.is_reference = (data is None or len(data) == 0)
            self.nodes[node_id] = node
        return self.nodes[node_id]

    def add_dependency(
        self,
        from_node_id: str,
        to_node_id: str,
        from_type: Optional[str] = None,
        to_type: Optional[str] = None,
    ):
        """
        Add a dependency edge: from_node depends on to_node.

        Args:
            from_node_id: Node that has the dependency
            to_node_id: Node that is depended upon
            from_type: Optional type of from_node (creates node if doesn't exist)
            to_type: Optional type of to_node (creates node if doesn't exist)
        """
        # Ensure nodes exist
        if from_node_id not in self.nodes and from_type:
            self.add_node(from_node_id, from_type)
        if to_node_id not in self.nodes and to_type:
            self.add_node(to_node_id, to_type)

        # Add dependency if both nodes exist
        if from_node_id in self.nodes and to_node_id in self.nodes:
            self.nodes[from_node_id].add_dependency(to_node_id)
            self.nodes[to_node_id].add_dependent(from_node_id)
            self.edges.append((from_node_id, to_node_id))

    def get_node(self, node_id: str) -> Optional[DependencyNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def get_dependencies(self, node_id: str) -> Set[str]:
        """Get all nodes that the given node depends on."""
        node = self.nodes.get(node_id)
        return node.dependencies if node else set()

    def get_dependents(self, node_id: str) -> Set[str]:
        """Get all nodes that depend on the given node."""
        node = self.nodes.get(node_id)
        return node.dependents if node else set()

    def get_topological_order(self) -> List[str]:
        """
        Get nodes in topological order (dependencies before dependents).

        Returns:
            List of node IDs in topological order
        """
        # Kahn's algorithm for topological sorting
        in_degree = defaultdict(int)

        # Calculate in-degrees
        for node_id in self.nodes:
            in_degree[node_id] = len(self.nodes[node_id].dependencies)

        # Find nodes with no dependencies
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
        result = []

        while queue:
            node_id = queue.popleft()
            result.append(node_id)

            # Reduce in-degree for dependents
            node = self.nodes[node_id]
            for dependent_id in node.dependents:
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    queue.append(dependent_id)

        # Check for cycles
        if len(result) != len(self.nodes):
            # There's a cycle - return nodes in order found
            return list(self.nodes.keys())

        return result

    def find_missing_dependencies(
        self, available_nodes: Set[str]
    ) -> Dict[str, List[str]]:
        """
        Find missing dependencies for nodes.

        Args:
            available_nodes: Set of node IDs that are available

        Returns:
            Dictionary mapping node_id to list of missing dependency IDs
        """
        missing = {}
        for node_id, node in self.nodes.items():
            missing_deps = [
                dep for dep in node.dependencies if dep not in available_nodes
            ]
            if missing_deps:
                missing[node_id] = missing_deps
        return missing

    def get_validation_order(self) -> List[str]:
        """
        Get order for validating dependencies (dependencies before dependents).

        Returns:
            List of node IDs in validation order
        """
        return self.get_topological_order()

    def get_push_order(self) -> List[str]:
        """
        Get order for pushing configurations (dependencies before dependents).

        Returns:
            List of node IDs in push order
        """
        return self.get_topological_order()

    def has_cycles(self) -> bool:
        """
        Check if the graph has cycles.

        Returns:
            True if cycles exist, False otherwise
        """
        visited = set()
        rec_stack = set()

        def has_cycle_util(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)

            node = self.nodes[node_id]
            for dep_id in node.dependencies:
                if dep_id not in visited:
                    if has_cycle_util(dep_id):
                        return True
                elif dep_id in rec_stack:
                    return True

            rec_stack.remove(node_id)
            return False

        for node_id in self.nodes:
            if node_id not in visited:
                if has_cycle_util(node_id):
                    return True

        return False

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get graph statistics.

        Returns:
            Dictionary with graph statistics
        """
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "nodes_by_type": self._count_nodes_by_type(),
            "has_cycles": self.has_cycles(),
            "max_dependencies": max(
                (len(n.dependencies) for n in self.nodes.values()), default=0
            ),
            "max_dependents": max(
                (len(n.dependents) for n in self.nodes.values()), default=0
            ),
        }

    def _count_nodes_by_type(self) -> Dict[str, int]:
        """Count nodes by type."""
        counts = defaultdict(int)
        for node in self.nodes.values():
            counts[node.type] += 1
        return dict(counts)

    def __repr__(self):
        return f"DependencyGraph(nodes={len(self.nodes)}, edges={len(self.edges)})"
