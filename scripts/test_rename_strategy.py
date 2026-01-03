#!/usr/bin/env python3
"""
Test RENAME functionality specifically.

Tests the RENAME conflict resolution strategy with dependency updates.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from prisma.api_client import PrismaAccessAPIClient
from prisma.push.push_orchestrator_v2 import PushOrchestratorV2
from config.models.objects import AddressObject, AddressGroup, ServiceObject, ServiceGroup
from config.models.policies import SecurityRule
from config.workflows.workflow_config import WorkflowConfig
from config.tenant_manager import TenantManager


def main():
    print("\n" + "="*70)
    print("RENAME STRATEGY TEST - WITH REFERENCE UPDATES")
    print("="*70)
    
    # Load credentials
    print("\n1. Loading credentials...")
    tenant_manager = TenantManager()
    tenants = tenant_manager.list_tenants()
    if not tenants:
        print("❌ No tenants found")
        return 1
    
    tenant = tenants[0]
    print(f"   Using tenant: {tenant['name']}")
    
    # Create API client
    print("\n2. Creating API client...")
    api_client = PrismaAccessAPIClient(
        tsg_id=tenant['tsg_id'],
        api_user=tenant['client_id'],
        api_secret=tenant['client_secret']
    )
    
    if not api_client.authenticate():
        print("❌ Authentication failed")
        return 1
    print("   ✅ Authenticated")
    
    # Create test items with dependencies
    print("\n3. Creating test items with dependencies...")
    
    # Base address (will be referenced by group)
    addr1 = AddressObject.from_dict({
        'name': 'test-rename-addr-base',
        'folder': 'Mobile Users',
        'ip_netmask': '10.1.1.1/32',
        'description': 'Base address that will be referenced'
    })
    
    # Group referencing the address
    addr_group = AddressGroup.from_dict({
        'name': 'test-rename-group',
        'folder': 'Mobile Users',
        'static': ['test-rename-addr-base'],  # References addr1
        'description': 'Group with dependency on address'
    })
    
    # Service (will be referenced by group)
    svc1 = ServiceObject.from_dict({
        'name': 'test-rename-svc-base',
        'folder': 'Mobile Users',
        'protocol': {
            'tcp': {'port': '8080'}
        },
        'description': 'Base service that will be referenced'
    })
    
    # Service group referencing the service
    svc_group = ServiceGroup.from_dict({
        'name': 'test-rename-svc-group',
        'folder': 'Mobile Users',
        'members': ['test-rename-svc-base'],  # References svc1
        'description': 'Service group with dependency'
    })
    
    items = [addr1, addr_group, svc1, svc_group]
    
    print(f"   Created {len(items)} test items:")
    print(f"   - {addr1.item_type}: {addr1.name}")
    print(f"   - {addr_group.item_type}: {addr_group.name} → references {addr1.name}")
    print(f"   - {svc1.item_type}: {svc1.name}")
    print(f"   - {svc_group.item_type}: {svc_group.name} → references {svc1.name}")
    
    # Step 1: Create items initially (to set up conflicts)
    print("\n4. Creating initial items (to create conflicts)...")
    config = WorkflowConfig()
    orchestrator1 = PushOrchestratorV2(api_client, config)
    
    result1 = orchestrator1.push_items(items, conflict_strategy="SKIP", check_existing=True)
    
    print(f"\n   Initial creation:")
    print(f"   - Created:  {result1.items_created}")
    print(f"   - Skipped:  {result1.items_skipped}")
    print(f"   - Failed:   {result1.items_failed}")
    
    if result1.items_failed > 0:
        print("\n   ⚠️  Some items failed to create")
        for error in result1.errors[:3]:
            print(f"   - {error.code}: {error.message}")
    
    # Step 2: Push again with RENAME strategy
    print("\n5. Pushing again with RENAME strategy...")
    print("   (Should rename conflicts and update references)")
    
    orchestrator2 = PushOrchestratorV2(api_client, config)
    
    result2 = orchestrator2.push_items(items, conflict_strategy="RENAME", check_existing=True)
    
    print(f"\n   Rename results:")
    print(f"   - Created:  {result2.items_created}")
    print(f"   - Skipped:  {result2.items_skipped}")
    print(f"   - Failed:   {result2.items_failed}")
    print(f"   - Renamed:  {len(orchestrator2.name_mappings)}")
    
    if orchestrator2.name_mappings:
        print(f"\n   Name mappings created:")
        for old_name, new_name in orchestrator2.name_mappings.items():
            print(f"   - {old_name} → {new_name}")
    
    # Step 3: Verify references were updated
    print("\n6. Verifying reference updates...")
    
    verification_passed = True
    
    # Check address group references
    for item in items:
        if item.item_type == 'address_group' and item.name.startswith('test-rename-group'):
            static_members = item.raw_config.get('static', [])
            print(f"\n   Address Group '{item.name}':")
            print(f"   - Static members: {static_members}")
            
            # Check if it references the renamed address
            for member in static_members:
                if member in orchestrator2.name_mappings.values():
                    print(f"   ✅ Reference updated correctly: {member}")
                elif member == 'test-rename-addr-base' and 'test-rename-addr-base' in orchestrator2.name_mappings:
                    print(f"   ❌ Reference NOT updated (still has old name)")
                    verification_passed = False
        
        elif item.item_type == 'service_group' and item.name.startswith('test-rename-svc-group'):
            members = item.raw_config.get('members', [])
            print(f"\n   Service Group '{item.name}':")
            print(f"   - Members: {members}")
            
            # Check if it references the renamed service
            for member in members:
                if member in orchestrator2.name_mappings.values():
                    print(f"   ✅ Reference updated correctly: {member}")
                elif member == 'test-rename-svc-base' and 'test-rename-svc-base' in orchestrator2.name_mappings:
                    print(f"   ❌ Reference NOT updated (still has old name)")
                    verification_passed = False
    
    # Step 4: Cleanup - delete all test items
    print("\n7. Cleanup - deleting test items...")
    
    # Need to delete both original and renamed items
    cleanup_items = list(items)
    for old_name, new_name in orchestrator2.name_mappings.items():
        # Find item and create renamed version
        for item in items:
            if item.name == old_name:
                from config.models.factory import ConfigItemFactory
                renamed_item = ConfigItemFactory.create_from_dict(
                    item.item_type,
                    item.raw_config.copy()
                )
                if renamed_item:
                    renamed_item.raw_config['name'] = new_name
                    cleanup_items.append(renamed_item)
                break
    
    result3 = orchestrator1.delete_items(cleanup_items)
    
    print(f"\n   Cleanup results:")
    print(f"   - Deleted:  {result3.items_deleted}")
    print(f"   - Failed:   {result3.items_failed}")
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    tests_passed = 0
    tests_total = 4
    
    # Test 1: Initial creation
    if result1.items_created >= 2:
        print("✅ Test 1: Initial creation succeeded")
        tests_passed += 1
    else:
        print("❌ Test 1: Initial creation failed")
    
    # Test 2: Rename happened
    if len(orchestrator2.name_mappings) >= 2:
        print("✅ Test 2: Items were renamed")
        tests_passed += 1
    else:
        print("❌ Test 2: No items were renamed")
    
    # Test 3: Items created after rename
    if result2.items_created >= 2:
        print("✅ Test 3: Renamed items created successfully")
        tests_passed += 1
    else:
        print("❌ Test 3: Renamed items not created")
    
    # Test 4: References updated
    if verification_passed:
        print("✅ Test 4: References updated correctly")
        tests_passed += 1
    else:
        print("❌ Test 4: References NOT updated")
    
    print(f"\n{tests_passed}/{tests_total} tests passed")
    
    if tests_passed == tests_total:
        print("\n🎉 ALL RENAME TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {tests_total - tests_passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
