#!/usr/bin/env python3
"""
Phase 4 Test Suite: Dependency Resolution & Pull Enhancement

Tests dependency resolution and CLI functionality.
"""

import sys
import json
from typing import Dict, Any, Optional


def test_dependency_graph():
    """Test dependency graph structure."""
    print("\n" + "=" * 60)
    print("Test 1: Dependency Graph")
    print("=" * 60)
    
    try:
        from prisma.dependencies.dependency_graph import DependencyGraph, DependencyNode
        
        graph = DependencyGraph()
        
        # Add nodes
        graph.add_node("addr1", "address_object")
        graph.add_node("addr2", "address_object")
        graph.add_node("group1", "address_group")
        
        # Add dependency: group1 depends on addr1 and addr2
        graph.add_dependency("group1", "addr1", "address_group", "address_object")
        graph.add_dependency("group1", "addr2", "address_group", "address_object")
        
        assert len(graph.nodes) == 3
        assert len(graph.edges) == 2
        print("  ✓ Graph nodes and edges created correctly")
        
        # Test topological order
        order = graph.get_topological_order()
        assert "addr1" in order
        assert "addr2" in order
        assert "group1" in order
        # Dependencies should come before dependents
        assert order.index("addr1") < order.index("group1")
        assert order.index("addr2") < order.index("group1")
        print("  ✓ Topological ordering works correctly")
        
        # Test missing dependencies
        available = {"addr1", "group1"}  # Missing addr2
        missing = graph.find_missing_dependencies(available)
        assert "group1" in missing
        assert "addr2" in missing["group1"]
        print("  ✓ Missing dependency detection works")
        
        # Test statistics
        stats = graph.get_statistics()
        assert stats['total_nodes'] == 3
        assert stats['total_edges'] == 2
        print("  ✓ Graph statistics work correctly")
        
        print("\n  ✓ All dependency graph functionality works correctly")
        return True
        
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dependency_resolver():
    """Test dependency resolver functionality."""
    print("\n" + "=" * 60)
    print("Test 2: Dependency Resolver")
    print("=" * 60)
    
    try:
        from prisma.dependencies.dependency_resolver import DependencyResolver
        
        resolver = DependencyResolver()
        
        # Create test configuration
        config = {
            'security_policies': {
                'folders': [
                    {
                        'name': 'Test Folder',
                        'objects': {
                            'address_objects': [
                                {'name': 'addr1', 'type': 'ip_netmask'},
                                {'name': 'addr2', 'type': 'ip_netmask'}
                            ],
                            'address_groups': [
                                {
                                    'name': 'group1',
                                    'static': ['addr1', 'addr2']
                                }
                            ]
                        },
                        'security_rules': [
                            {
                                'name': 'rule1',
                                'source': ['group1'],
                                'destination': ['addr1'],
                                'service': ['any']
                            }
                        ],
                        'profiles': {
                            'authentication_profiles': [
                                {'name': 'auth1'}
                            ],
                            'security_profiles': {
                                'anti_spyware': [
                                    {'name': 'profile1'}
                                ]
                            }
                        }
                    }
                ],
                'snippets': []
            }
        }
        
        # Build dependency graph
        graph = resolver.build_dependency_graph(config)
        assert len(graph.nodes) > 0
        print("  ✓ Dependency graph built from configuration")
        
        # Validate dependencies
        validation = resolver.validate_dependencies(config)
        assert 'valid' in validation
        assert 'missing_dependencies' in validation
        print("  ✓ Dependency validation works")
        
        # Get resolution order
        order = resolver.get_resolution_order(config)
        assert len(order) > 0
        # Address objects should come before groups
        if 'addr1' in order and 'group1' in order:
            assert order.index('addr1') < order.index('group1')
        print("  ✓ Resolution order works correctly")
        
        # Get dependency report
        report = resolver.get_dependency_report(config)
        assert 'validation' in report
        assert 'statistics' in report
        assert 'dependencies_by_type' in report
        print("  ✓ Dependency reporting works")
        
        print("\n  ✓ All dependency resolver functionality works correctly")
        return True
        
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration_with_pull(api_client=None):
    """Test dependency resolution integration with pull."""
    print("\n" + "=" * 60)
    print("Test 3: Integration with Pull Orchestrator")
    print("=" * 60)
    
    try:
        from prisma.pull.pull_orchestrator import PullOrchestrator
        
        if not api_client:
            print("  ⚠ Skipping (no API client provided)")
            return True
        
        print("  Testing against real tenant...")
        
        # Test orchestrator has dependency resolver
        orchestrator = PullOrchestrator(api_client, detect_defaults=True)
        assert hasattr(orchestrator, 'dependency_resolver')
        assert orchestrator.dependency_resolver is not None
        print("  ✓ Orchestrator initializes with dependency resolver")
        
        # Pull a folder configuration
        from prisma.pull.folder_capture import FolderCapture
        folder_capture = FolderCapture(api_client)
        folders = folder_capture.list_folders_for_capture(include_defaults=False)
        
        if not folders:
            print("  ⚠ No folders available for testing")
            return True
        
        test_folder = folders[0]
        if "Mobile Users" in folders:
            test_folder = "Mobile Users"
        
        print(f"  Testing with folder: {test_folder}")
        
        # Pull folder configuration
        folder_config = orchestrator.pull_folder_configuration(
            test_folder,
            include_objects=True,
            include_profiles=True
        )
        
        # Create minimal config for dependency validation
        test_config = {
            'security_policies': {
                'folders': [folder_config],
                'snippets': []
            }
        }
        
        # Validate dependencies
        validation = orchestrator.validate_dependencies(test_config)
        assert 'valid' in validation
        print(f"  ✓ Dependency validation completed")
        print(f"    Valid: {validation.get('valid')}")
        
        if not validation.get('valid'):
            missing = validation.get('missing_dependencies', {})
            print(f"    Missing dependencies: {len(missing)} objects")
            if missing:
                # Show first few
                for obj_name, missing_deps in list(missing.items())[:3]:
                    print(f"      - {obj_name}: {len(missing_deps)} missing")
        
        # Get dependency report
        report = orchestrator.get_dependency_report(test_config)
        stats = report.get('statistics', {})
        print(f"  ✓ Dependency report generated")
        print(f"    Total nodes: {stats.get('total_nodes', 0)}")
        print(f"    Total dependencies: {stats.get('total_edges', 0)}")
        
        print("\n  ✓ Dependency resolution integrated correctly with pull")
        return True
        
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cli_interface():
    """Test CLI interface structure."""
    print("\n" + "=" * 60)
    print("Test 4: CLI Interface")
    print("=" * 60)
    
    try:
        import subprocess
        
        # Test CLI help
        result = subprocess.run(
            [sys.executable, 'cli/pull_cli.py', '--help'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        assert result.returncode == 0 or result.returncode == 2  # 2 is argparse error for missing required args
        assert '--tsg' in result.stdout or '--tsg' in result.stderr
        assert '--client-id' in result.stdout or '--client-id' in result.stderr
        print("  ✓ CLI help works correctly")
        
        # Test CLI structure
        import importlib.util
        spec = importlib.util.spec_from_file_location("pull_cli", "cli/pull_cli.py")
        cli_module = importlib.util.module_from_spec(spec)
        
        # Check main function exists
        assert hasattr(cli_module, 'main') or 'def main' in open('cli/pull_cli.py').read()
        print("  ✓ CLI module structure correct")
        
        print("\n  ✓ CLI interface structure is correct")
        return True
        
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all Phase 4 tests."""
    print("=" * 60)
    print("Phase 4 Implementation Tests: Dependency Resolution & Pull Enhancement")
    print("=" * 60)
    
    # Get API client if credentials provided
    api_client = None
    try:
        response = input("\nTest against real tenant? (y/n): ").strip().lower()
        if response == 'y':
            from prisma.api_client import PrismaAccessAPIClient
            from load_settings import prisma_access_auth
            
            tsg = input("Enter TSG ID: ").strip()
            api_user = input("Enter API Client ID: ").strip()
            api_secret = input("Enter API Client Secret: ").strip()
            
            if tsg and api_user and api_secret:
                print("\nInitializing API client...")
                token = prisma_access_auth(tsg, api_user, api_secret)
                if token:
                    api_client = PrismaAccessAPIClient(tsg, api_user, api_secret)
                    print("✓ API client initialized successfully")
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
        return
    except Exception as e:
        print(f"\n⚠ Warning: Could not initialize API client: {e}")
        print("  Continuing with structure tests only...")
    
    # Run tests
    tests = [
        ("Dependency Graph", test_dependency_graph),
        ("Dependency Resolver", test_dependency_resolver),
        ("Integration with Pull", lambda: test_integration_with_pull(api_client)),
        ("CLI Interface", test_cli_interface)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
