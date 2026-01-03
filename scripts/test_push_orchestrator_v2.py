#!/usr/bin/env python3
"""
Test script for the new PushOrchestratorV2.

Tests the ConfigItem-based push orchestrator with various scenarios.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from prisma.api_client import PrismaAccessAPIClient
from prisma.push.push_orchestrator_v2 import PushOrchestratorV2
from config.models.objects import AddressObject, AddressGroup, ServiceObject
from config.models.policies import SecurityRule
from config.workflows.workflow_config import WorkflowConfig
from config.tenant_manager import TenantManager


def main():
    print("\n" + "="*70)
    print("PUSH ORCHESTRATOR V2 TEST")
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
    
    # Create test items
    print("\n3. Creating test items...")
    
    # Simple address object (no dependencies)
    addr1 = AddressObject.from_dict({
        'name': 'test-push-addr-1',
        'folder': 'Mobile Users',
        'ip_netmask': '192.168.100.1/32',
        'description': 'Test address for push orchestrator'
    })
    
    # Address object that will be used in a group (dependency)
    addr2 = AddressObject.from_dict({
        'name': 'test-push-addr-2',
        'folder': 'Mobile Users',
        'ip_netmask': '192.168.100.2/32',
        'description': 'Dependency address'
    })
    
    # Address group (depends on addr2)
    addr_group = AddressGroup.from_dict({
        'name': 'test-push-group',
        'folder': 'Mobile Users',
        'static': ['test-push-addr-2'],
        'description': 'Test group with dependency'
    })
    
    # Service object
    svc = ServiceObject.from_dict({
        'name': 'test-push-svc',
        'folder': 'Mobile Users',
        'protocol': {
            'tcp': {
                'port': '8080'
            }
        },
        'description': 'Test service'
    })
    
    items = [addr1, addr2, addr_group, svc]
    print(f"   Created {len(items)} test items")
    print(f"   - {addr1.item_type}: {addr1.name}")
    print(f"   - {addr2.item_type}: {addr2.name}")
    print(f"   - {addr_group.item_type}: {addr_group.name} (depends on {addr2.name})")
    print(f"   - {svc.item_type}: {svc.name}")
    
    # Test 1: Push with SKIP strategy (safest)
    print("\n4. Test 1: Push with SKIP strategy")
    print("   (Creates new items, skips existing)")
    
    config = WorkflowConfig()
    orchestrator = PushOrchestratorV2(api_client, config)
    
    result = orchestrator.push_items(items, conflict_strategy="SKIP")
    
    print(f"\n   Results:")
    print(f"   - Processed: {result.items_processed}")
    print(f"   - Created:   {result.items_created}")
    print(f"   - Skipped:   {result.items_skipped}")
    print(f"   - Failed:    {result.items_failed}")
    
    if result.errors:
        print(f"\n   Errors ({len(result.errors)}):")
        for error in result.errors[:5]:  # Show first 5
            print(f"   - {error.code}: {error.message}")
    
    if result.warnings:
        print(f"\n   Warnings ({len(result.warnings)}):")
        for warning in result.warnings[:5]:
            print(f"   - {warning.code}: {warning.message}")
    
    # Test 2: Push again with SKIP (should skip all)
    print("\n5. Test 2: Push again with SKIP (should skip existing)")
    
    result2 = orchestrator.push_items(items, conflict_strategy="SKIP", check_existing=True)
    
    print(f"\n   Results:")
    print(f"   - Processed: {result2.items_processed}")
    print(f"   - Created:   {result2.items_created}")
    print(f"   - Skipped:   {result2.items_skipped}")
    print(f"   - Failed:    {result2.items_failed}")
    
    # Test 3: Cleanup - delete test items
    print("\n6. Test 3: Cleanup - Delete test items")
    print("   (Top-down: group first, then addresses)")
    
    result3 = orchestrator.delete_items(items)
    
    print(f"\n   Results:")
    print(f"   - Processed: {result3.items_processed}")
    print(f"   - Deleted:   {result3.items_deleted}")
    print(f"   - Failed:    {result3.items_failed}")
    
    if result3.errors:
        print(f"\n   Errors ({len(result3.errors)}):")
        for error in result3.errors[:5]:
            print(f"   - {error.code}: {error.message}")
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Test 1 (SKIP - first push):  {result.items_created} created, {result.items_failed} failed")
    print(f"Test 2 (SKIP - second push): {result2.items_skipped} skipped")
    print(f"Test 3 (DELETE):             {result3.items_deleted} deleted")
    
    success = (
        result.items_failed == 0 and
        result.items_created > 0 and
        result2.items_skipped > 0 and
        result3.items_deleted > 0
    )
    
    if success:
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n⚠️  SOME TESTS HAD ISSUES")
    
    print("="*70 + "\n")
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
