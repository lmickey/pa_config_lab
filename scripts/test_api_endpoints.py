#!/usr/bin/env python3
"""
API Endpoint Test Script

Tests all API endpoints and saves raw output to test/examples directory.
Uses credentials from the GUI tenant selection (credentials.json).

Usage:
    python scripts/test_api_endpoints.py [--tenant TENANT_NAME]
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from prisma.api_client import PrismaAccessAPIClient as PrismaAPIClient
from prisma.api_endpoints import APIEndpoints, is_folder_allowed, is_snippet_allowed, FOLDER_EXCLUSIONS, FOLDER_ONLY
from config.tenant_manager import TenantManager
from config import logging_config  # Import to add custom log levels


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Define all endpoints to test with their configurations
# Format: (item_type, api_method, requires_folder, requires_snippet)
# Folder restrictions are handled by is_folder_allowed() from api_endpoints
ENDPOINTS_TO_TEST: List[Tuple[str, str, bool, bool]] = [
    # Objects
    ('address_object', 'get_all_addresses', True, True),
    ('address_group', 'get_all_address_groups', True, True),
    ('region', 'get_all_regions', True, True),
    ('service_object', 'get_all_services', True, True),
    ('service_group', 'get_all_service_groups', True, True),
    ('tag', 'get_all_tags', True, True),
    ('application_group', 'get_all_application_groups', True, True),
    ('application_filter', 'get_all_application_filters', True, True),
    ('schedule', 'get_all_schedules', True, True),
    ('external_dynamic_list', 'get_all_external_dynamic_lists', True, True),
    ('custom_url_category', 'get_all_url_categories', True, True),  # Note: endpoint is url-categories
    ('local_user', 'get_all_local_users', True, True),
    ('local_user_group', 'get_all_local_user_groups', True, True),

    # Security Profiles
    ('anti_spyware_profile', 'get_all_anti_spyware_profiles', True, True),
    ('vulnerability_profile', 'get_all_vulnerability_profiles', True, True),
    ('file_blocking_profile', 'get_all_file_blocking_profiles', True, True),
    ('wildfire_profile', 'get_all_wildfire_profiles', True, True),
    ('dns_security_profile', 'get_all_dns_security_profiles', True, True),
    ('decryption_profile', 'get_all_decryption_profiles', True, True),
    ('url_access_profile', 'get_all_url_access_profiles', True, False),
    ('http_header_profile', 'get_all_http_header_profiles', True, True),
    ('certificate_profile', 'get_all_certificate_profiles', True, True),
    ('profile_group', 'get_all_profile_groups', True, True),
    ('qos_profile', 'get_all_qos_profiles', True, False),

    # HIP
    ('hip_object', 'get_all_hip_objects', True, True),
    ('hip_profile', 'get_all_hip_profiles', True, True),

    # Rules/Policies
    ('security_rule', 'get_all_security_rules', True, True),
    ('decryption_rule', 'get_all_decryption_rules', True, True),
    ('authentication_rule', 'get_all_authentication_rules', True, True),
    ('qos_policy_rule', 'get_all_qos_policy_rules', True, True),

    # Infrastructure - IPSec/IKE (folder-based)
    ('ike_crypto_profile', 'get_all_ike_crypto_profiles', True, False),
    ('ipsec_crypto_profile', 'get_all_ipsec_crypto_profiles', True, False),
    ('ike_gateway', 'get_all_ike_gateways', True, False),
    ('ipsec_tunnel', 'get_all_ipsec_tunnels', True, False),

    # Infrastructure - Global (no folder)
    ('remote_network', 'get_all_remote_networks', False, False),
    ('service_connection', 'get_all_service_connections', False, False),
    ('bandwidth_allocation', 'get_all_bandwidth_allocations', False, False),
    ('auto_tag_action', 'get_all_auto_tag_actions', False, False),

    # Mobile Users Infrastructure (special - returns dict not list)
    ('agent_profile', 'get_mobile_agent_profiles', True, False),
]

# Standard folders to test
STANDARD_FOLDERS = ['Mobile Users', 'Remote Networks', 'Service Connections']

# Standard snippets to discover
DISCOVER_SNIPPETS = True


def load_credentials(tenant_name: Optional[str] = None) -> Dict[str, Any]:
    """Load credentials using TenantManager."""
    tenant_manager = TenantManager()
    tenants = tenant_manager.list_tenants()

    if not tenants:
        raise ValueError(
            "No tenants configured.\n"
            "Please configure credentials in the GUI first."
        )

    # If tenant name specified, find it
    if tenant_name:
        for tenant in tenants:
            if tenant.get('name') == tenant_name:
                return tenant
        available = [t['name'] for t in tenants]
        raise ValueError(f"Tenant '{tenant_name}' not found. Available: {available}")

    # Return first tenant (sorted by name)
    return tenants[0]


def get_snippets(client: PrismaAPIClient) -> List[str]:
    """Get list of available snippets."""
    try:
        snippets = client.get_snippets()
        return [s['name'] for s in snippets if s.get('name')]
    except Exception as e:
        logger.warning(f"Failed to get snippets: {e}")
        return []


def test_endpoint(
    client: PrismaAPIClient,
    endpoint_name: str,
    method_name: str,
    folder: Optional[str] = None,
    snippet: Optional[str] = None
) -> Tuple[bool, Any, Optional[str]]:
    """
    Test a single endpoint.

    Returns:
        Tuple of (success, data, error_message)
    """
    try:
        method = getattr(client, method_name, None)
        if not method:
            return False, None, f"Method {method_name} not found"

        # Build kwargs based on what the method accepts
        kwargs = {}
        if folder:
            kwargs['folder'] = folder
        if snippet:
            kwargs['snippet'] = snippet

        # Call the method
        data = method(**kwargs) if kwargs else method()
        return True, data, None

    except Exception as e:
        return False, None, str(e)


def save_results(
    output_dir: Path,
    endpoint_name: str,
    location: str,
    data: Any,
    timestamp: str
):
    """Save endpoint results to a JSON file."""
    # Sanitize location for filename
    safe_location = location.replace(' ', '_').replace('/', '_')
    filename = f"{endpoint_name}_{safe_location}.json"
    filepath = output_dir / filename

    output = {
        'endpoint': endpoint_name,
        'location': location,
        'timestamp': timestamp,
        'item_count': len(data) if isinstance(data, list) else 1,
        'data': data
    }

    with open(filepath, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    logger.info(f"  Saved {len(data) if isinstance(data, list) else 1} items to {filename}")


def main():
    parser = argparse.ArgumentParser(description='Test all API endpoints')
    parser.add_argument('--tenant', '-t', help='Tenant name to use')
    parser.add_argument('--output', '-o', help='Output directory', default='tests/examples/api_raw')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load credentials
    logger.info("Loading credentials...")
    try:
        creds = load_credentials(args.tenant)
        logger.info(f"Using tenant: {creds.get('name', 'unknown')}")
    except Exception as e:
        logger.error(f"Failed to load credentials: {e}")
        return 1

    # Create output directory
    output_dir = project_root / args.output
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")

    # Initialize API client
    logger.info("Initializing API client...")
    try:
        client = PrismaAPIClient(
            tsg_id=creds['tsg_id'],
            api_user=creds['client_id'],
            api_secret=creds['client_secret']
        )
    except Exception as e:
        logger.error(f"Failed to initialize API client: {e}")
        return 1

    # Get snippets if enabled
    snippets = []
    if DISCOVER_SNIPPETS:
        logger.info("Discovering snippets...")
        snippets = get_snippets(client)
        logger.info(f"Found {len(snippets)} snippets: {snippets[:5]}..." if len(snippets) > 5 else f"Found snippets: {snippets}")

    timestamp = datetime.now().isoformat()

    # Track results
    results = {
        'total': 0,
        'success': 0,
        'failed': 0,
        'errors': []
    }

    # Test each endpoint
    logger.info(f"\nTesting {len(ENDPOINTS_TO_TEST)} endpoint types...")

    for item_type, method_name, requires_folder, requires_snippet in ENDPOINTS_TO_TEST:
        logger.info(f"\n--- Testing: {item_type} ---")

        # Determine which locations to test
        locations_to_test = []

        if requires_folder:
            # Filter folders based on API restrictions
            for folder in STANDARD_FOLDERS:
                if is_folder_allowed(item_type, folder):
                    locations_to_test.append(('folder', folder))
                else:
                    logger.info(f"  Skipping folder '{folder}' (API restriction)")

        if requires_snippet and snippets and is_snippet_allowed(item_type):
            # Add first few snippets for testing
            for snippet in snippets[:3]:
                locations_to_test.append(('snippet', snippet))
        elif requires_snippet and snippets and not is_snippet_allowed(item_type):
            logger.info(f"  Skipping snippets (API doesn't support snippets for {item_type})")

        if not locations_to_test:
            # Global endpoint - no folder/snippet needed
            locations_to_test = [(None, None)]

        for loc_type, loc_value in locations_to_test:
            results['total'] += 1

            folder = loc_value if loc_type == 'folder' else None
            snippet = loc_value if loc_type == 'snippet' else None
            location_desc = f"{loc_type}:{loc_value}" if loc_type else "global"

            logger.info(f"  Testing {location_desc}...")

            success, data, error = test_endpoint(client, item_type, method_name, folder, snippet)

            if success:
                results['success'] += 1
                if data:
                    save_results(output_dir, item_type, location_desc, data, timestamp)
                else:
                    logger.info(f"    No data returned (empty)")
            else:
                results['failed'] += 1
                results['errors'].append({
                    'endpoint': item_type,
                    'location': location_desc,
                    'error': error
                })
                logger.warning(f"    FAILED: {error}")

    # Save summary
    summary = {
        'timestamp': timestamp,
        'tenant': creds.get('name', 'unknown'),
        'results': results,
        'endpoints_tested': len(ENDPOINTS_TO_TEST),
        'folders_tested': STANDARD_FOLDERS,
        'snippets_tested': snippets[:3] if snippets else []
    }

    summary_path = output_dir / '_test_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)

    # Print summary
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)
    logger.info(f"Total tests: {results['total']}")
    logger.info(f"Successful:  {results['success']}")
    logger.info(f"Failed:      {results['failed']}")

    if results['errors']:
        logger.info("\nFailed endpoints:")
        for err in results['errors']:
            logger.info(f"  - {err['endpoint']} ({err['location']}): {err['error'][:50]}...")

    logger.info(f"\nResults saved to: {output_dir}")

    return 0 if results['failed'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
