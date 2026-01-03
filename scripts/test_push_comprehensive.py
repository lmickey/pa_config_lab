#!/usr/bin/env python3
"""
Comprehensive test suite for PushOrchestratorV2.

Tests push orchestrator with production examples covering:
- SKIP strategy
- OVERWRITE strategy (with ID change verification)
- RENAME strategy
- Dependency ordering
- Error handling
- Various item types
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from prisma.api_client import PrismaAccessAPIClient
from prisma.push.push_orchestrator_v2 import PushOrchestratorV2
from config.models.factory import ConfigItemFactory
from config.workflows.workflow_config import WorkflowConfig
from config.tenant_manager import TenantManager


def load_example_items(example_dir: Path, limit=5):
    """Load ConfigItem objects from production examples."""
    items = []
    
    if not example_dir.exists():
        print(f"⚠️  Example directory not found: {example_dir}")
        return items
    
    json_files = list(example_dir.glob("*.json"))
    if not json_files:
        print(f"⚠️  No JSON files found in: {example_dir}")
        return items
    
    # Load up to 'limit' examples
    for json_file in json_files[:limit]:
        try:
            with open(json_file, 'r') as f:
                raw_config = json.load(f)
            
            # Determine item type from file or config
            item_type = raw_config.get('item_type')
            if not item_type:
                # Try to infer from filename
                item_type = json_file.stem.rsplit('_', 1)[0]
            
            # Create ConfigItem using factory
            item = ConfigItemFactory.create_from_dict(item_type, raw_config)
            if item:
                # Ensure it has a test-friendly name
                item.raw_config['name'] = f"test-{item.name[:40]}"
                items.append(item)
                
        except Exception as e:
            print(f"⚠️  Failed to load {json_file.name}: {e}")
    
    return items


def main():
    print("\n" + "="*70)
    print("COMPREHENSIVE PUSH ORCHESTRATOR V2 TEST")
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
    
    # Load production examples
    print("\n3. Loading production examples...")
    examples_dir = Path(__file__).parent.parent / "tests" / "examples" / "production" / "raw"
    
    # Load examples from different categories
    categories = {
        'objects': examples_dir / "objects",
        'profiles': examples_dir / "profiles",
        'policies': examples_dir / "policies",
    }
    
    all_items = []
    for category, category_dir in categories.items():
        if category_dir.exists():
            items = load_example_items(category_dir, limit=2)
            print(f"   Loaded {len(items)} {category}")
            all_items.extend(items)
    
    if not all_items:
        print("⚠️  No examples loaded, using synthetic data...")
        # Fall back to synthetic test items (previous test script logic)
        from config.models.objects import AddressObject, AddressGroup, ServiceObject
        
        addr1 = AddressObject.from_dict({
            'name': 'test-push-addr-1',
            'folder': 'Mobile Users',
            'ip_netmask': '192.168.100.1/32',
            'description': 'Test address'
        })
        
        addr2 = AddressObject.from_dict({
            'name': 'test-push-addr-2',
            'folder': 'Mobile Users',
            'ip_netmask': '192.168.100.2/32',
            'description': 'Dependency address'
        })
        
        addr_group = AddressGroup.from_dict({
            'name': 'test-push-group',
            'folder': 'Mobile Users',
            'static': ['test-push-addr-2'],
            'description': 'Test group with dependency'
        })
        
        svc = ServiceObject.from_dict({
            'name': 'test-push-svc',
            'folder': 'Mobile Users',
            'protocol': {
                'tcp': {'port': '8080'}
            },
            'description': 'Test service'
        })
        
        all_items = [addr1, addr2, addr_group, svc]
    
    print(f"\n   Total items for testing: {len(all_items)}")
    for item in all_items[:5]:
        print(f"   - {item.item_type}: {item.name}")
    if len(all_items) > 5:
        print(f"   ... and {len(all_items) - 5} more")
    
    # Create orchestrator
    config = WorkflowConfig()
    orchestrator = PushOrchestratorV2(api_client, config)
    
    # Test 1: Push with SKIP strategy
    print("\n" + "="*70)
    print("TEST 1: SKIP Strategy (Create New Items)")
    print("="*70)
    
    result1 = orchestrator.push_items(all_items, conflict_strategy="SKIP", check_existing=True)
    
    print(f"\nResults:")
    print(f"  Processed:       {result1.items_processed}")
    print(f"  Created:         {result1.items_created}")
    print(f"  Skipped:         {result1.items_skipped}")
    print(f"  Failed:          {result1.items_failed}")
    
    if result1.errors:
        print(f"\nErrors ({len(result1.errors)}):")
        for error in result1.errors[:3]:
            print(f"  - {error.code}: {error.message}")
    
    if result1.warnings:
        print(f"\nWarnings ({len(result1.warnings)}):")
        for warning in result1.warnings[:3]:
            print(f"  - {warning.code}: {warning.message}")
    
    # Test 2: Push again with SKIP (should skip existing)
    print("\n" + "="*70)
    print("TEST 2: SKIP Strategy (Should Skip Existing)")
    print("="*70)
    
    result2 = orchestrator.push_items(all_items, conflict_strategy="SKIP", check_existing=True)
    
    print(f"\nResults:")
    print(f"  Processed:       {result2.items_processed}")
    print(f"  Created:         {result2.items_created}")
    print(f"  Skipped:         {result2.items_skipped}")
    print(f"  Failed:          {result2.items_failed}")
    
    # Test 3: Push with OVERWRITE strategy
    print("\n" + "="*70)
    print("TEST 3: OVERWRITE Strategy (Delete + Recreate, Check ID Change)")
    print("="*70)
    
    # Store IDs before overwrite
    old_ids = {}
    for item in all_items:
        if hasattr(item, 'id') and item.id:
            old_ids[item.name] = item.id
    
    print(f"\nOld IDs captured: {len(old_ids)}")
    
    result3 = orchestrator.push_items(all_items, conflict_strategy="OVERWRITE", check_existing=True)
    
    print(f"\nResults:")
    print(f"  Processed:       {result3.items_processed}")
    print(f"  Created:         {result3.items_created}")
    print(f"  Skipped:         {result3.items_skipped}")
    print(f"  Failed:          {result3.items_failed}")
    print(f"  Could Not Overwrite: {len(result3.could_not_overwrite)}")
    
    if result3.could_not_overwrite:
        print(f"\nItems that could not be overwritten:")
        for item_type, item_name in list(result3.could_not_overwrite)[:3]:
            print(f"  - {item_type}: {item_name}")
    
    # Check ID changes
    id_changes = []
    for item in all_items:
        if item.name in old_ids and hasattr(item, 'id') and item.id:
            if old_ids[item.name] != item.id:
                id_changes.append((item.name, old_ids[item.name], item.id))
    
    print(f"\nID Changes Detected: {len(id_changes)}")
    for name, old_id, new_id in id_changes[:3]:
        print(f"  - {name}: {old_id[:8]}... → {new_id[:8]}...")
    
    # Test 4: RENAME strategy
    print("\n" + "="*70)
    print("TEST 4: RENAME Strategy (Auto-rename Conflicts)")
    print("="*70)
    
    # Create fresh orchestrator for rename test
    orchestrator_rename = PushOrchestratorV2(api_client, config)
    
    result4 = orchestrator_rename.push_items(all_items, conflict_strategy="RENAME", check_existing=True)
    
    print(f"\nResults:")
    print(f"  Processed:       {result4.items_processed}")
    print(f"  Created:         {result4.items_created}")
    print(f"  Skipped:         {result4.items_skipped}")
    print(f"  Failed:          {result4.items_failed}")
    print(f"  Renamed:         {len(orchestrator_rename.name_mappings)}")
    
    if orchestrator_rename.name_mappings:
        print(f"\nItems renamed:")
        for old_name, new_name in list(orchestrator_rename.name_mappings.items())[:3]:
            print(f"  - {old_name} → {new_name}")
    
    # Test 5: Cleanup - Delete all test items
    print("\n" + "="*70)
    print("TEST 5: Cleanup (Dependency-Aware Deletion)")
    print("="*70)
    
    # Collect all items including renamed ones
    all_test_items = list(all_items)
    for old_name, new_name in orchestrator_rename.name_mappings.items():
        # Find and add renamed items
        for item in all_items:
            if item.name == old_name:
                # Create a copy with new name for deletion
                renamed_item = ConfigItemFactory.create_from_dict(item.item_type, item.raw_config.copy())
                renamed_item.raw_config['name'] = new_name
                all_test_items.append(renamed_item)
                break
    
    result5 = orchestrator.delete_items(all_test_items)
    
    print(f"\nResults:")
    print(f"  Processed:       {result5.items_processed}")
    print(f"  Deleted:         {result5.items_deleted}")
    print(f"  Failed:          {result5.items_failed}")
    
    if result5.errors:
        print(f"\nDeletion Errors ({len(result5.errors)}):")
        for error in result5.errors[:3]:
            print(f"  - {error.code}: {error.message}")
    
    # Final Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    tests_passed = 0
    tests_total = 5
    
    # Test 1: Should create items
    if result1.items_created > 0 and result1.items_failed == 0:
        print("✅ Test 1 (SKIP - create):      PASSED")
        tests_passed += 1
    else:
        print("❌ Test 1 (SKIP - create):      FAILED")
    
    # Test 2: Should skip all
    if result2.items_skipped == result2.items_processed and result2.items_created == 0:
        print("✅ Test 2 (SKIP - skip):        PASSED")
        tests_passed += 1
    else:
        print("❌ Test 2 (SKIP - skip):        FAILED")
    
    # Test 3: Should overwrite with ID changes
    if result3.items_created > 0 and len(id_changes) > 0:
        print("✅ Test 3 (OVERWRITE + ID):     PASSED")
        tests_passed += 1
    else:
        print("❌ Test 3 (OVERWRITE + ID):     FAILED")
    
    # Test 4: Should rename items
    if result4.items_created > 0 and len(orchestrator_rename.name_mappings) > 0:
        print("✅ Test 4 (RENAME):             PASSED")
        tests_passed += 1
    else:
        print("❌ Test 4 (RENAME):             FAILED")
    
    # Test 5: Should delete items
    if result5.items_deleted > 0:
        print("✅ Test 5 (DELETE):             PASSED")
        tests_passed += 1
    else:
        print("❌ Test 5 (DELETE):             FAILED")
    
    print(f"\n{tests_passed}/{tests_total} tests passed")
    
    if tests_passed == tests_total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {tests_total - tests_passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
