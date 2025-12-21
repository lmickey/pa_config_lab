"""
Tests for dependency validation and graph operations.

Tests cover:
- Dependency graph construction
- Circular dependency detection
- Missing dependency detection
- Dependency ordering
"""

import pytest
from typing import Dict, Any, Set

from prisma.dependencies.dependency_graph import DependencyGraph, DependencyNode
from tests.conftest import sample_config_v2


@pytest.mark.unit
class TestDependencyGraph:
    """Test dependency graph structure."""
    
    def test_create_empty_graph(self):
        """Test creating an empty dependency graph."""
        graph = DependencyGraph()
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0
    
    def test_add_node(self):
        """Test adding a node to the graph."""
        graph = DependencyGraph()
        node = graph.add_node("test-node", "address_object", {"name": "Test"})
        
        assert "test-node" in graph.nodes
        assert graph.nodes["test-node"] == node
        assert node.id == "test-node"
        assert node.type == "address_object"
    
    def test_add_duplicate_node(self):
        """Test adding a duplicate node (should return existing)."""
        graph = DependencyGraph()
        node1 = graph.add_node("test-node", "address_object")
        node2 = graph.add_node("test-node", "address_group")
        
        assert node1 == node2
        assert len(graph.nodes) == 1
        # Type should remain as first added
        assert graph.nodes["test-node"].type == "address_object"
    
    def test_add_dependency(self):
        """Test adding a dependency between nodes."""
        graph = DependencyGraph()
        graph.add_node("group1", "address_group")
        graph.add_node("addr1", "address_object")
        
        graph.add_dependency("group1", "addr1")
        
        assert "addr1" in graph.get_dependencies("group1")
        assert "group1" in graph.get_dependents("addr1")
        assert ("group1", "addr1") in graph.edges
    
    def test_add_dependency_creates_nodes(self):
        """Test that adding dependency creates nodes if they don't exist."""
        graph = DependencyGraph()
        graph.add_dependency("group1", "addr1", "address_group", "address_object")
        
        assert "group1" in graph.nodes
        assert "addr1" in graph.nodes
        assert graph.nodes["group1"].type == "address_group"
        assert graph.nodes["addr1"].type == "address_object"
    
    def test_get_dependencies(self):
        """Test getting dependencies for a node."""
        graph = DependencyGraph()
        graph.add_node("group1", "address_group")
        graph.add_node("addr1", "address_object")
        graph.add_node("addr2", "address_object")
        
        graph.add_dependency("group1", "addr1")
        graph.add_dependency("group1", "addr2")
        
        deps = graph.get_dependencies("group1")
        assert len(deps) == 2
        assert "addr1" in deps
        assert "addr2" in deps
    
    def test_get_dependents(self):
        """Test getting dependents for a node."""
        graph = DependencyGraph()
        graph.add_node("addr1", "address_object")
        graph.add_node("group1", "address_group")
        graph.add_node("group2", "address_group")
        
        graph.add_dependency("group1", "addr1")
        graph.add_dependency("group2", "addr1")
        
        dependents = graph.get_dependents("addr1")
        assert len(dependents) == 2
        assert "group1" in dependents
        assert "group2" in dependents
    
    def test_get_nonexistent_node(self):
        """Test getting a node that doesn't exist."""
        graph = DependencyGraph()
        node = graph.get_node("nonexistent")
        assert node is None
    
    def test_get_dependencies_nonexistent_node(self):
        """Test getting dependencies for nonexistent node."""
        graph = DependencyGraph()
        deps = graph.get_dependencies("nonexistent")
        assert deps == set()


@pytest.mark.unit
class TestCircularDependencyDetection:
    """Test circular dependency detection."""
    
    def test_no_circular_dependencies(self):
        """Test graph with no circular dependencies."""
        graph = DependencyGraph()
        graph.add_dependency("group1", "addr1", "address_group", "address_object")
        graph.add_dependency("rule1", "group1", "security_rule", "address_group")
        
        assert not graph.has_cycles()
    
    def test_simple_circular_dependency(self):
        """Test simple circular dependency (A -> B -> A)."""
        graph = DependencyGraph()
        graph.add_dependency("group1", "group2", "address_group", "address_group")
        graph.add_dependency("group2", "group1", "address_group", "address_group")
        
        assert graph.has_cycles()
    
    def test_complex_circular_dependency(self):
        """Test complex circular dependency (A -> B -> C -> A)."""
        graph = DependencyGraph()
        graph.add_dependency("group1", "group2", "address_group", "address_group")
        graph.add_dependency("group2", "group3", "address_group", "address_group")
        graph.add_dependency("group3", "group1", "address_group", "address_group")
        
        assert graph.has_cycles()
    
    def test_self_reference(self):
        """Test self-referencing node."""
        graph = DependencyGraph()
        graph.add_node("group1", "address_group")
        # Self-reference should be detected as cycle
        graph.add_dependency("group1", "group1")
        
        assert graph.has_cycles()


@pytest.mark.unit
class TestMissingDependencyDetection:
    """Test missing dependency detection."""
    
    def test_no_missing_dependencies(self):
        """Test graph with all dependencies present."""
        graph = DependencyGraph()
        graph.add_node("group1", "address_group")
        graph.add_node("addr1", "address_object")
        graph.add_dependency("group1", "addr1")
        
        available = {"group1", "addr1"}
        missing = graph.find_missing_dependencies(available)
        assert len(missing) == 0
    
    def test_missing_dependency(self):
        """Test graph with missing dependency."""
        graph = DependencyGraph()
        graph.add_node("group1", "address_group")
        graph.add_node("addr1", "address_object")
        graph.add_dependency("group1", "addr1")
        
        # Only group1 is available, addr1 is missing
        available = {"group1"}
        missing = graph.find_missing_dependencies(available)
        assert "group1" in missing
        assert "addr1" in missing["group1"]
    
    def test_multiple_missing_dependencies(self):
        """Test graph with multiple missing dependencies."""
        graph = DependencyGraph()
        graph.add_node("group1", "address_group")
        graph.add_node("addr1", "address_object")
        graph.add_node("addr2", "address_object")
        graph.add_dependency("group1", "addr1")
        graph.add_dependency("group1", "addr2")
        
        available = {"group1"}
        missing = graph.find_missing_dependencies(available)
        assert "group1" in missing
        assert len(missing["group1"]) == 2
        assert "addr1" in missing["group1"]
        assert "addr2" in missing["group1"]


@pytest.mark.unit
class TestTopologicalOrdering:
    """Test topological ordering for dependency resolution."""
    
    def test_simple_ordering(self):
        """Test simple dependency ordering."""
        graph = DependencyGraph()
        graph.add_dependency("group1", "addr1", "address_group", "address_object")
        graph.add_dependency("rule1", "group1", "security_rule", "address_group")
        
        order = graph.get_topological_order()
        # addr1 should come before group1, group1 before rule1
        assert order.index("addr1") < order.index("group1")
        assert order.index("group1") < order.index("rule1")
    
    def test_multiple_independent_chains(self):
        """Test ordering with multiple independent dependency chains."""
        graph = DependencyGraph()
        graph.add_dependency("group1", "addr1", "address_group", "address_object")
        graph.add_dependency("group2", "addr2", "address_group", "address_object")
        
        order = graph.get_topological_order()
        # Both chains should be ordered correctly
        assert order.index("addr1") < order.index("group1")
        assert order.index("addr2") < order.index("group2")
    
    def test_ordering_with_cycles(self):
        """Test ordering with circular dependencies (should handle gracefully)."""
        graph = DependencyGraph()
        graph.add_dependency("group1", "group2", "address_group", "address_group")
        graph.add_dependency("group2", "group1", "address_group", "address_group")
        
        # Should still return an order (may not be unique)
        order = graph.get_topological_order()
        assert len(order) == 2
        assert "group1" in order
        assert "group2" in order


@pytest.mark.unit
class TestGraphStatistics:
    """Test graph statistics."""
    
    def test_empty_graph_statistics(self):
        """Test statistics for empty graph."""
        graph = DependencyGraph()
        stats = graph.get_statistics()
        
        assert stats["total_nodes"] == 0
        assert stats["total_edges"] == 0
        assert stats["nodes_by_type"] == {}
    
    def test_graph_statistics(self):
        """Test statistics for populated graph."""
        graph = DependencyGraph()
        graph.add_node("addr1", "address_object")
        graph.add_node("group1", "address_group")
        graph.add_node("rule1", "security_rule")
        graph.add_dependency("group1", "addr1")
        graph.add_dependency("rule1", "group1")
        
        stats = graph.get_statistics()
        
        assert stats["total_nodes"] == 3
        assert stats["total_edges"] == 2
        assert "address_object" in stats["nodes_by_type"]
        assert "address_group" in stats["nodes_by_type"]
        assert "security_rule" in stats["nodes_by_type"]


@pytest.mark.unit
class TestDependencyNode:
    """Test DependencyNode class."""
    
    def test_create_node(self):
        """Test creating a dependency node."""
        node = DependencyNode("test-id", "address_object", {"name": "Test"})
        
        assert node.id == "test-id"
        assert node.type == "address_object"
        assert node.data == {"name": "Test"}
        assert len(node.dependencies) == 0
        assert len(node.dependents) == 0
    
    def test_add_dependency(self):
        """Test adding a dependency to a node."""
        node = DependencyNode("group1", "address_group")
        node.add_dependency("addr1")
        
        assert "addr1" in node.dependencies
        assert len(node.dependencies) == 1
    
    def test_add_dependent(self):
        """Test adding a dependent to a node."""
        node = DependencyNode("addr1", "address_object")
        node.add_dependent("group1")
        
        assert "group1" in node.dependents
        assert len(node.dependents) == 1
    
    def test_node_repr(self):
        """Test node string representation."""
        node = DependencyNode("test-id", "address_object")
        node.add_dependency("dep1")
        node.add_dependent("dep2")
        
        repr_str = repr(node)
        assert "test-id" in repr_str
        assert "address_object" in repr_str
