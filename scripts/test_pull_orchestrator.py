#!/usr/bin/env python3
"""
Test script for new bulk query pull orchestrator.

This script tests the rewritten pull orchestrator against a real API.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from prisma.api_client import PrismaAccessAPIClient
from prisma.pull.pull_orchestrator import PullOrchestrator
from config.workflows import WorkflowConfig
from config.tenant_manager import TenantManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run pull orchestrator test."""
    
    print("\n" + "=" * 70)
    print("PULL ORCHESTRATOR TEST")
    print("=" * 70)
    
    # Load credentials
    print("\n1. Loading credentials...")
    tenant_manager = TenantManager()
    tenants = tenant_manager.list_tenants()
    
    if not tenants:
        print("❌ No tenants configured. Run tenant configuration first.")
        return 1
    
    # Use first tenant (list_tenants returns full tenant dicts)
    tenant = tenants[0]
    print(f"   Using tenant: {tenant['name']}")
    
    # Extract credentials from tenant dict
    creds = {
        'tsg_id': tenant['tsg_id'],
        'client_id': tenant['client_id'],
        'client_secret': tenant['client_secret'],
    }
    
    if not all(creds.values()):
        print(f"❌ Incomplete credentials for {tenant['name']}")
        return 1
    
    # Create API client
    print("\n2. Creating API client...")
    api_client = PrismaAccessAPIClient(
        tsg_id=creds['tsg_id'],
        api_user=creds['client_id'],
        api_secret=creds['client_secret']
    )
    
    # Authenticate
    print("   Authenticating...")
    if not api_client.authenticate():
        print("❌ Authentication failed")
        return 1
    print("   ✅ Authenticated")
    
    # Configure workflow
    print("\n3. Configuring workflow...")
    config = WorkflowConfig(
        excluded_folders={'Colo Connect', 'Service Connections'},
        include_defaults=False,
        validate_before_pull=False,  # Don't validate during pull (too slow)
        stop_on_error=False,
    )
    print("   ✅ Configuration ready")
    
    # Create orchestrator
    print("\n4. Creating pull orchestrator...")
    orchestrator = PullOrchestrator(api_client, config)
    print("   ✅ Orchestrator ready")
    
    # Pull configurations
    print("\n5. Pulling configurations (BULK QUERY MODE)...")
    print("   This uses ONE query per type (not per folder)")
    print("   Expected: ~40 API calls instead of 50-100+")
    print()
    
    result = orchestrator.pull_all(
        include_folders=True,
        include_snippets=False,  # Skip snippets for now
        include_infrastructure=False,  # Skip infrastructure for now
    )
    
    # Display results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    result.print_summary()
    
    # Show folder breakdown if available
    folders = result.metadata.get('folders', [])
    if folders:
        print(f"\nFolders processed: {len(folders)}")
        for folder in folders[:5]:  # Show first 5
            print(f"  - {folder}")
        if len(folders) > 5:
            print(f"  ... and {len(folders) - 5} more")
    
    # Show type breakdown
    print("\nTypes captured:")
    print(f"  Folder types: {len(orchestrator.FOLDER_TYPES)}")
    print(f"  Snippet types: {len(orchestrator.SNIPPET_TYPES)}")
    print(f"  Infrastructure types: {len(orchestrator.INFRASTRUCTURE_TYPES)}")
    
    # Check for errors
    if result.has_errors:
        print(f"\n⚠️  Errors encountered: {result.error_count}")
        print("\nFirst 5 errors:")
        for error in result.errors[:5]:
            print(f"  - {error.item_type}/{error.item_name}: {error.message}")
    
    # Success/failure
    print("\n" + "=" * 70)
    if result.success:
        print("✅ PULL TEST SUCCESSFUL")
    else:
        print("❌ PULL TEST FAILED")
    print("=" * 70 + "\n")
    
    return 0 if result.success else 1


if __name__ == '__main__':
    sys.exit(main())
