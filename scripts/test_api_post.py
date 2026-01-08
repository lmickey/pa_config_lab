#!/usr/bin/env python3
"""
Test script for API POST operations.

Tests POST operations and shows the request body for debugging.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import logging config FIRST to register custom log levels
from config.logging_config import setup_logging, DETAIL
setup_logging(level=DETAIL)

from prisma.api_client import PrismaAccessAPIClient
from config.tenant_manager import TenantManager


def test_post_address(api_client: PrismaAccessAPIClient, dry_run: bool = True):
    """Test creating an address object."""
    print("\n" + "-"*60)
    print("TEST: Create Address Object")
    print("-"*60)
    
    test_data = {
        "name": "test-api-post-address",
        "ip_netmask": "192.168.100.100/32",
        "description": "Test address created by API POST test"
    }
    
    print(f"\nRequest body:")
    print(json.dumps(test_data, indent=2))
    
    if dry_run:
        print("\n[DRY RUN] Would POST to: /sse/config/v1/addresses?folder=Shared")
        return True
    
    try:
        result = api_client.create_address(test_data, folder="Shared")
        print(f"\n✅ Success! Created: {result.get('name')}")
        print(f"   ID: {result.get('id')}")
        return True
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        return False


def test_post_address_to_snippet(api_client: PrismaAccessAPIClient, snippet_name: str, dry_run: bool = True):
    """Test creating an address object in a snippet."""
    print("\n" + "-"*60)
    print(f"TEST: Create Address Object in Snippet '{snippet_name}'")
    print("-"*60)
    
    test_data = {
        "name": "test-snippet-address",
        "ip_netmask": "10.10.10.10/32",
        "description": "Test address in snippet"
    }
    
    print(f"\nRequest body:")
    print(json.dumps(test_data, indent=2))
    
    from urllib.parse import quote
    encoded_snippet = quote(snippet_name, safe="")
    url = f"https://api.sase.paloaltonetworks.com/sse/config/v1/addresses?snippet={encoded_snippet}"
    
    if dry_run:
        print(f"\n[DRY RUN] Would POST to: {url}")
        return True
    
    try:
        # Use _make_request directly for snippet (like the orchestrator does)
        result = api_client._make_request("POST", url, data=test_data, use_cache=False)
        print(f"\n✅ Success! Created: {result.get('name')}")
        print(f"   ID: {result.get('id')}")
        return True
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        return False


def test_post_application_group(api_client: PrismaAccessAPIClient, folder: str = "Shared", dry_run: bool = True):
    """Test creating an application group."""
    print("\n" + "-"*60)
    print(f"TEST: Create Application Group in folder '{folder}'")
    print("-"*60)
    
    test_data = {
        "name": "test-app-group",
        "members": ["web-browsing", "ssl"]
    }
    
    print(f"\nRequest body:")
    print(json.dumps(test_data, indent=2))
    
    from urllib.parse import quote
    encoded_folder = quote(folder, safe="")
    url = f"https://api.sase.paloaltonetworks.com/sse/config/v1/application-groups?folder={encoded_folder}"
    
    if dry_run:
        print(f"\n[DRY RUN] Would POST to: {url}")
        return True
    
    try:
        result = api_client._make_request("POST", url, data=test_data, use_cache=False)
        print(f"\n✅ Success! Created: {result.get('name')}")
        print(f"   ID: {result.get('id')}")
        return True
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        return False


def test_post_application_group_to_snippet(api_client: PrismaAccessAPIClient, snippet_name: str, dry_run: bool = True):
    """Test creating an application group in a snippet."""
    print("\n" + "-"*60)
    print(f"TEST: Create Application Group in Snippet '{snippet_name}'")
    print("-"*60)
    
    test_data = {
        "name": "test-snippet-app-group",
        "members": ["dns", "ntp"]
    }
    
    print(f"\nRequest body:")
    print(json.dumps(test_data, indent=2))
    
    from urllib.parse import quote
    encoded_snippet = quote(snippet_name, safe="")
    url = f"https://api.sase.paloaltonetworks.com/sse/config/v1/application-groups?snippet={encoded_snippet}"
    
    if dry_run:
        print(f"\n[DRY RUN] Would POST to: {url}")
        return True
    
    try:
        result = api_client._make_request("POST", url, data=test_data, use_cache=False)
        print(f"\n✅ Success! Created: {result.get('name')}")
        print(f"   ID: {result.get('id')}")
        return True
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        return False


def test_post_security_rule_to_snippet(api_client: PrismaAccessAPIClient, snippet_name: str, dry_run: bool = True):
    """Test creating a security rule in a snippet."""
    print("\n" + "-"*60)
    print(f"TEST: Create Security Rule in Snippet '{snippet_name}'")
    print("-"*60)
    
    # Full security rule data based on actual config
    test_data = {
        "name": "test-snippet-security-rule",
        "action": "deny",
        "application": ["web-browsing", "ssl"],
        "category": ["any"],
        "destination": ["any"],
        "destination_hip": ["any"],
        "disabled": False,
        "from": ["trust"],
        "log_end": True,
        "log_setting": "Cortex Data Lake",
        "log_start": False,
        "profile_setting": {
            "group": ["best-practice"]
        },
        "service": ["application-default"],
        "source": ["any"],
        "source_hip": ["any"],
        "source_user": ["any"],
        "to": ["untrust"]
    }
    
    print(f"\nRequest body:")
    print(json.dumps(test_data, indent=2))
    
    from urllib.parse import quote
    encoded_snippet = quote(snippet_name, safe="")
    url = f"https://api.sase.paloaltonetworks.com/sse/config/v1/security-rules?snippet={encoded_snippet}"
    
    if dry_run:
        print(f"\n[DRY RUN] Would POST to: {url}")
        return True
    
    try:
        result = api_client._make_request("POST", url, data=test_data, use_cache=False)
        print(f"\n✅ Success! Created: {result.get('name')}")
        print(f"   ID: {result.get('id')}")
        return True
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        return False


def test_create_snippet(api_client: PrismaAccessAPIClient, snippet_name: str, dry_run: bool = True):
    """Test creating a new snippet."""
    print("\n" + "-"*60)
    print(f"TEST: Create New Snippet '{snippet_name}'")
    print("-"*60)
    
    test_data = {
        "name": snippet_name,
        "description": "Test snippet created by API POST test"
    }
    
    print(f"\nRequest body:")
    print(json.dumps(test_data, indent=2))
    
    if dry_run:
        print(f"\n[DRY RUN] Would POST to: /sse/config/v1/snippets")
        return True
    
    try:
        result = api_client.create_snippet(test_data)
        print(f"\n✅ Success! Created snippet: {result.get('name')}")
        print(f"   ID: {result.get('id')}")
        return True
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        return False


def list_snippets(api_client: PrismaAccessAPIClient):
    """List all snippets."""
    print("\n" + "-"*60)
    print("Listing all snippets")
    print("-"*60)
    
    try:
        snippets = api_client.get_security_policy_snippets()
        print(f"\nFound {len(snippets)} snippets:")
        for snippet in snippets:
            name = snippet.get('name', 'Unknown')
            snippet_id = snippet.get('id', 'N/A')
            snippet_type = snippet.get('type', 'N/A')
            print(f"  - {name} (type: {snippet_type}, id: {snippet_id})")
        return snippets
    except Exception as e:
        print(f"❌ Failed to list snippets: {e}")
        return []


def list_folders(api_client: PrismaAccessAPIClient):
    """List all folders."""
    print("\n" + "-"*60)
    print("Listing all folders")
    print("-"*60)
    
    try:
        folders = api_client.get_security_policy_folders()
        print(f"\nFound {len(folders)} folders:")
        for folder in folders:
            name = folder.get('name', 'Unknown')
            folder_id = folder.get('id', 'N/A')
            print(f"  - {name} (id: {folder_id})")
        return folders
    except Exception as e:
        print(f"❌ Failed to list folders: {e}")
        return []


def main():
    print("\n" + "="*70)
    print("API POST TEST SCRIPT")
    print("="*70)
    
    # Check args
    dry_run = "--live" not in sys.argv
    if dry_run:
        print("\n⚠️  DRY RUN MODE - No actual API calls will be made")
        print("   Use --live to perform actual API calls")
    else:
        print("\n🔴 LIVE MODE - Will make actual API calls!")
    
    # Load credentials
    print("\n1. Loading credentials...")
    tenant_manager = TenantManager()
    tenants = tenant_manager.list_tenants()
    if not tenants:
        print("❌ No tenants found")
        return 1
    
    # Use first tenant or specified tenant
    tenant_name = None
    for arg in sys.argv:
        if arg.startswith("--tenant="):
            tenant_name = arg.split("=")[1]
    
    if tenant_name:
        tenant = next((t for t in tenants if t['name'] == tenant_name), None)
        if not tenant:
            print(f"❌ Tenant '{tenant_name}' not found")
            return 1
    else:
        tenant = tenants[0]
    
    print(f"   Using tenant: {tenant['name']} ({tenant['tsg_id']})")
    
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
    
    # List existing resources
    print("\n3. Current resources...")
    list_folders(api_client)
    snippets = list_snippets(api_client)
    
    # Run tests
    print("\n4. Running POST tests...")
    
    test_snippet_name = "api-test-snippet"
    
    # Test 1: Create snippet
    test_create_snippet(api_client, test_snippet_name, dry_run)
    
    # Test 2: Create address in folder
    test_post_address(api_client, dry_run)
    
    # Test 3: Create address in snippet
    test_post_address_to_snippet(api_client, test_snippet_name, dry_run)
    
    # Test 4: Create app group in folder
    test_post_application_group(api_client, "Shared", dry_run)
    
    # Test 5: Create app group in snippet
    test_post_application_group_to_snippet(api_client, test_snippet_name, dry_run)
    
    # Test 6: Create security rule in snippet
    test_post_security_rule_to_snippet(api_client, test_snippet_name, dry_run)
    
    print("\n" + "="*70)
    print("TESTS COMPLETE")
    print("="*70 + "\n")
    
    if dry_run:
        print("To actually create these resources, run with --live")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
