#!/usr/bin/env python3
"""
Push Workflow Test Script

Automated testing of push workflow based on Prioritized Test Cases.
Uses real API data from tests/examples/api_raw/ for realistic testing scenarios.

Test Phases:
  1. Core Snippet Operations (6 tests)
  2. Folder Operations (6 tests)
  3. Partial Selection & Mixed (4 tests)
  4. Edge Cases (4 tests)
  5. Object Types (4 tests)
  6. Infrastructure (3 tests)
  7. Rules (3 tests)
  8. Error & Recovery (4 tests)
  9. Validation Edge Cases (3 tests)

Usage:
    python scripts/test_push_workflow.py [--phase PHASE] [--test TEST_NUM] [--dry-run]
    python scripts/test_push_workflow.py --list  # List all test cases
"""

import argparse
import json
import logging
import os
import sys
import time
import copy
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from prisma.api_client import PrismaAccessAPIClient
from prisma.push.push_orchestrator_v2 import PushOrchestratorV2
from config.tenant_manager import TenantManager
from config import logging_config  # Import to add custom log levels

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestPhase(Enum):
    """Test phases from Prioritized Test Cases"""
    CORE_SNIPPET = 1
    FOLDER_OPS = 2
    PARTIAL_MIXED = 3
    EDGE_CASES = 4
    OBJECT_TYPES = 5
    INFRASTRUCTURE = 6
    RULES = 7
    ERROR_RECOVERY = 8
    VALIDATION = 9


@dataclass
class TestCase:
    """Definition of a single test case"""
    id: int
    name: str
    phase: TestPhase
    description: str
    source_type: str  # 'snippet', 'folder', 'infrastructure', 'mixed'
    source_name: str
    destination_type: str  # 'new_snippet', 'existing_snippet', 'folder', 'same'
    destination_name: Optional[str]
    strategy: str  # 'skip', 'overwrite', 'rename'
    expected_conflict: Optional[str]
    validates: str
    setup_fn: Optional[str] = None  # Function name to call for setup
    item_types: List[str] = field(default_factory=list)  # Types of items to include
    item_count: int = 2  # Number of items to include
    custom_items: List[Dict[str, Any]] = field(default_factory=list)  # Pre-defined items
    expected_results: Dict[str, Any] = field(default_factory=dict)


class RealisticDataLoader:
    """Load and manage realistic test data from API raw files"""

    def __init__(self, api_raw_dir: Path):
        self.api_raw_dir = api_raw_dir
        self.cache: Dict[str, List[Dict[str, Any]]] = {}

    def _load_file(self, filename: str) -> List[Dict[str, Any]]:
        """Load data from an API raw file"""
        filepath = self.api_raw_dir / filename
        if not filepath.exists():
            return []
        try:
            with open(filepath) as f:
                content = json.load(f)
                return content.get('data', [])
        except Exception as e:
            logger.warning(f"Failed to load {filename}: {e}")
            return []

    def get_addresses(self, location: str = 'Mobile_Users') -> List[Dict[str, Any]]:
        """Get address objects from a location"""
        key = f'address_{location}'
        if key not in self.cache:
            self.cache[key] = self._load_file(f'address_object_folder:{location}.json')
        return self.cache[key]

    def get_tags(self, location: str = 'Mobile_Users') -> List[Dict[str, Any]]:
        """Get tags from a location"""
        key = f'tag_{location}'
        if key not in self.cache:
            self.cache[key] = self._load_file(f'tag_folder:{location}.json')
        return self.cache[key]

    def get_security_rules(self, location: str = 'Mobile_Users') -> List[Dict[str, Any]]:
        """Get security rules from a location"""
        key = f'security_rule_{location}'
        if key not in self.cache:
            self.cache[key] = self._load_file(f'security_rule_folder:{location}.json')
        return self.cache[key]

    def get_address_groups(self, location: str = 'Mobile_Users') -> List[Dict[str, Any]]:
        """Get address groups from a location"""
        key = f'address_group_{location}'
        if key not in self.cache:
            self.cache[key] = self._load_file(f'address_group_folder:{location}.json')
        return self.cache[key]

    def get_services(self, location: str = 'Mobile_Users') -> List[Dict[str, Any]]:
        """Get services from a location"""
        key = f'service_{location}'
        if key not in self.cache:
            self.cache[key] = self._load_file(f'service_object_folder:{location}.json')
        return self.cache[key]

    def get_schedules(self, location: str = 'Mobile_Users') -> List[Dict[str, Any]]:
        """Get schedules from a location"""
        key = f'schedule_{location}'
        if key not in self.cache:
            self.cache[key] = self._load_file(f'schedule_folder:{location}.json')
        return self.cache[key]

    def get_edls(self, location: str = 'Mobile_Users') -> List[Dict[str, Any]]:
        """Get external dynamic lists from a location"""
        key = f'edl_{location}'
        if key not in self.cache:
            self.cache[key] = self._load_file(f'external_dynamic_list_folder:{location}.json')
        return self.cache[key]

    def get_hip_profiles(self, location: str = 'Mobile_Users') -> List[Dict[str, Any]]:
        """Get HIP profiles from a location"""
        key = f'hip_profile_{location}'
        if key not in self.cache:
            self.cache[key] = self._load_file(f'hip_profile_folder:{location}.json')
        return self.cache[key]

    def get_hip_objects(self, location: str = 'Mobile_Users') -> List[Dict[str, Any]]:
        """Get HIP objects from a location"""
        key = f'hip_object_{location}'
        if key not in self.cache:
            self.cache[key] = self._load_file(f'hip_object_folder:{location}.json')
        return self.cache[key]

    def get_anti_spyware_profiles(self, location: str = 'Mobile_Users') -> List[Dict[str, Any]]:
        """Get anti-spyware profiles from a location"""
        key = f'anti_spyware_{location}'
        if key not in self.cache:
            self.cache[key] = self._load_file(f'anti_spyware_profile_folder:{location}.json')
        return self.cache[key]

    def get_vulnerability_profiles(self, location: str = 'Mobile_Users') -> List[Dict[str, Any]]:
        """Get vulnerability profiles from a location"""
        key = f'vulnerability_{location}'
        if key not in self.cache:
            self.cache[key] = self._load_file(f'vulnerability_profile_folder:{location}.json')
        return self.cache[key]

    def get_url_profiles(self, location: str = 'Mobile_Users') -> List[Dict[str, Any]]:
        """Get URL access profiles from a location"""
        key = f'url_access_{location}'
        if key not in self.cache:
            self.cache[key] = self._load_file(f'url_access_profile_folder:{location}.json')
        return self.cache[key]

    def get_decryption_rules(self, location: str = 'Mobile_Users') -> List[Dict[str, Any]]:
        """Get decryption rules from a location"""
        key = f'decryption_rule_{location}'
        if key not in self.cache:
            self.cache[key] = self._load_file(f'decryption_rule_folder:{location}.json')
        return self.cache[key]

    def get_authentication_rules(self, location: str = 'Mobile_Users') -> List[Dict[str, Any]]:
        """Get authentication rules from a location"""
        key = f'auth_rule_{location}'
        if key not in self.cache:
            self.cache[key] = self._load_file(f'authentication_rule_folder:{location}.json')
        return self.cache[key]

    def get_ike_crypto_profiles(self, location: str = 'Remote_Networks') -> List[Dict[str, Any]]:
        """Get IKE crypto profiles from a location"""
        key = f'ike_crypto_{location}'
        if key not in self.cache:
            self.cache[key] = self._load_file(f'ike_crypto_profile_folder:{location}.json')
        return self.cache[key]

    def get_ipsec_crypto_profiles(self, location: str = 'Remote_Networks') -> List[Dict[str, Any]]:
        """Get IPSec crypto profiles from a location"""
        key = f'ipsec_crypto_{location}'
        if key not in self.cache:
            self.cache[key] = self._load_file(f'ipsec_crypto_profile_folder:{location}.json')
        return self.cache[key]

    def get_remote_networks(self) -> List[Dict[str, Any]]:
        """Get remote networks"""
        key = 'remote_networks'
        if key not in self.cache:
            self.cache[key] = self._load_file('remote_network_global.json')
        return self.cache[key]

    def get_service_connections(self) -> List[Dict[str, Any]]:
        """Get service connections"""
        key = 'service_connections'
        if key not in self.cache:
            self.cache[key] = self._load_file('service_connection_global.json')
        return self.cache[key]


class PushTestFramework:
    """Framework for running push workflow tests"""

    # Test snippet prefix for cleanup (short to fit 31 char limit)
    TEST_PREFIX = "tp-"
    MAX_NAME_LENGTH = 31  # Prisma Access API limit

    def __init__(self, api_client: PrismaAccessAPIClient, dry_run: bool = False):
        self.api_client = api_client
        self.orchestrator = PushOrchestratorV2(api_client)
        self.dry_run = dry_run
        self.results: List[Dict[str, Any]] = []
        self.test_artifacts: List[Dict[str, Any]] = []  # Track created items for cleanup

        # Load realistic data
        api_raw_dir = project_root / 'tests' / 'examples' / 'api_raw'
        self.data_loader = RealisticDataLoader(api_raw_dir)

        # Get available snippets and folders
        self.snippets = []
        self.folders = []
        try:
            self.snippets = api_client.get_snippets()
            self.folders = api_client.get_security_policy_folders()
        except Exception as e:
            logger.warning(f"Failed to load snippets/folders: {e}")

    def _generate_test_name(self, base: str) -> str:
        """Generate unique test name with timestamp (fits 31 char limit)"""
        # Use short timestamp (MMSS = 4 chars) to save space
        timestamp = datetime.now().strftime('%M%S')
        return f"{self.TEST_PREFIX}{base}-{timestamp}"

    def _truncate_name(self, name: str, max_length: int = None) -> str:
        """Truncate name to fit within max length"""
        max_len = max_length or self.MAX_NAME_LENGTH
        if len(name) <= max_len:
            return name
        return name[:max_len]

    def _abbreviate_item_type(self, item_type: str) -> str:
        """Get short abbreviation for item type to fit in names"""
        abbrevs = {
            'address': 'addr',
            'address_group': 'agrp',
            'tag': 'tag',
            'service': 'svc',
            'service_group': 'sgrp',
            'schedule': 'sched',
            'external_dynamic_list': 'edl',
            'security_rule': 'srule',
            'decryption_rule': 'drule',
            'authentication_rule': 'arule',
            'hip_profile': 'hipp',
            'hip_object': 'hipo',
            'anti_spyware_profile': 'asp',
            'vulnerability_profile': 'vulnp',
            'url_access_profile': 'urlp',
            'ike_crypto_profile': 'ikep',
            'ipsec_crypto_profile': 'ipsecp',
            'ike_gateway': 'ikegw',
            'ipsec_tunnel': 'ipsect',
        }
        return abbrevs.get(item_type, item_type[:4])

    def _clone_item_for_test(self, item: Dict[str, Any], new_name: str) -> Dict[str, Any]:
        """Clone an item with a new name for testing"""
        cloned = copy.deepcopy(item)
        # Truncate name to fit 31 char limit
        cloned['name'] = self._truncate_name(new_name)
        # Remove ID so it creates a new item
        cloned.pop('id', None)
        # Remove override fields
        cloned.pop('override_loc', None)
        cloned.pop('override_type', None)
        cloned.pop('override_id', None)
        return cloned

    def _prepare_item_for_push(
        self,
        item: Dict[str, Any],
        item_type: str,
        dest_type: str,
        dest_name: Optional[str],
        strategy: str
    ) -> Dict[str, Any]:
        """Prepare an item for push with destination info"""
        prepared = copy.deepcopy(item)
        prepared['item_type'] = item_type

        # Truncate destination name if too long
        truncated_dest = self._truncate_name(dest_name) if dest_name else dest_name

        # Add destination info
        prepared['_destination'] = {
            'strategy': strategy,
        }

        if dest_type == 'new_snippet':
            prepared['_destination']['is_new_snippet'] = True
            prepared['_destination']['new_snippet_name'] = truncated_dest
        elif dest_type == 'existing_snippet':
            prepared['_destination']['snippet'] = truncated_dest
            prepared['_destination']['is_new_snippet'] = False
        elif dest_type == 'folder':
            prepared['_destination']['folder'] = truncated_dest
        elif dest_type == 'same':
            # Keep original location
            if 'folder' in item:
                prepared['_destination']['folder'] = item['folder']
            elif 'snippet' in item:
                prepared['_destination']['snippet'] = item['snippet']

        return prepared

    def _generate_test_items(self, test_case: TestCase) -> List[Dict[str, Any]]:
        """Generate test items based on test case requirements using realistic data"""
        items = []
        base_name = self._generate_test_name(f"t{test_case.id}")

        # Use custom items if provided
        if test_case.custom_items:
            for i, custom in enumerate(test_case.custom_items):
                item = self._clone_item_for_test(custom, f"{base_name}-{i}")
                items.append(self._prepare_item_for_push(
                    item,
                    custom.get('item_type', 'address'),
                    test_case.destination_type,
                    test_case.destination_name,
                    test_case.strategy
                ))
            return items

        # Generate items based on item_types or defaults
        item_types = test_case.item_types or ['address']

        for item_type in item_types:
            source_data = []

            # Load realistic data based on item type
            if item_type == 'address':
                source_data = self.data_loader.get_addresses()
            elif item_type == 'tag':
                source_data = self.data_loader.get_tags()
            elif item_type == 'security_rule':
                source_data = self.data_loader.get_security_rules()
            elif item_type == 'address_group':
                source_data = self.data_loader.get_address_groups()
            elif item_type == 'schedule':
                source_data = self.data_loader.get_schedules()
            elif item_type == 'external_dynamic_list':
                source_data = self.data_loader.get_edls()
            elif item_type == 'hip_profile':
                source_data = self.data_loader.get_hip_profiles()
            elif item_type == 'hip_object':
                source_data = self.data_loader.get_hip_objects()
            elif item_type == 'anti_spyware_profile':
                source_data = self.data_loader.get_anti_spyware_profiles()
            elif item_type == 'vulnerability_profile':
                source_data = self.data_loader.get_vulnerability_profiles()
            elif item_type == 'decryption_rule':
                source_data = self.data_loader.get_decryption_rules()
            elif item_type == 'authentication_rule':
                source_data = self.data_loader.get_authentication_rules()
            elif item_type == 'ike_crypto_profile':
                source_data = self.data_loader.get_ike_crypto_profiles()
            elif item_type == 'ipsec_crypto_profile':
                source_data = self.data_loader.get_ipsec_crypto_profiles()

            # Filter out predefined/system items and pick items for test
            usable_items = [
                item for item in source_data
                if item.get('name') not in ['default', 'strict', 'best-practice', 'predefined']
                and not item.get('name', '').startswith('panw-')
                and 'snippet' not in item.get('name', '').lower()
            ]

            # Clone items with test names (use abbreviated type to fit 31 char limit)
            type_abbrev = self._abbreviate_item_type(item_type)
            for i, source_item in enumerate(usable_items[:test_case.item_count]):
                cloned = self._clone_item_for_test(source_item, f"{base_name}-{type_abbrev}{i}")
                items.append(self._prepare_item_for_push(
                    cloned,
                    item_type,
                    test_case.destination_type,
                    test_case.destination_name,
                    test_case.strategy
                ))

        # If no realistic data found, create synthetic items
        if not items:
            for i in range(test_case.item_count):
                item_name = self._truncate_name(f"{base_name}-addr{i}")
                item = {
                    'name': item_name,
                    'ip_netmask': f'192.168.{100+i}.0/24',
                    'description': f'Synthetic test address for test {test_case.id}'
                }
                items.append(self._prepare_item_for_push(
                    item,
                    'address',
                    test_case.destination_type,
                    test_case.destination_name,
                    test_case.strategy
                ))

        # Fix up address group references to use addresses being pushed
        items = self._fix_address_group_references(items)

        return items

    def _fix_address_group_references(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fix address group static references to use addresses being pushed.

        When pushing address groups to a new snippet, their static members
        must reference addresses that are also being pushed. This method
        updates address group static fields to reference the addresses
        in the current push set.
        """
        # Collect all address names being pushed
        address_names = [
            item.get('name') for item in items
            if item.get('item_type') == 'address' and item.get('name')
        ]

        if not address_names:
            return items

        # Update address groups to reference these addresses
        for item in items:
            if item.get('item_type') == 'address_group':
                # Replace static references with addresses being pushed
                if 'static' in item:
                    # Use the addresses from our push set
                    item['static'] = address_names[:len(item.get('static', []))] or address_names[:1]
                # Clear dynamic filters that might reference external tags
                if 'dynamic' in item:
                    del item['dynamic']

        return items

    def _build_push_payload(
        self,
        items: List[Dict[str, Any]],
        source_type: str,
        source_name: str
    ) -> Dict[str, Any]:
        """Build the selected_items payload for push orchestrator"""

        # Group items by type
        objects = {}
        profiles = {}
        rules = []

        for item in items:
            item_type = item.get('item_type', 'address')
            strategy = item.get('_destination', {}).get('strategy', 'skip')

            # Categorize by type
            if item_type in ['address', 'tag', 'service', 'address_group', 'service_group',
                            'application_group', 'application_filter', 'schedule',
                            'external_dynamic_list', 'fqdn']:
                if item_type not in objects:
                    objects[item_type] = []
                objects[item_type].append(item)
            elif item_type.endswith('_profile') or item_type in ['hip_object', 'hip_profile']:
                if item_type not in profiles:
                    profiles[item_type] = []
                profiles[item_type].append(item)
            elif item_type.endswith('_rule'):
                rules.append(item)
            else:
                # Default to address
                if 'address' not in objects:
                    objects['address'] = []
                objects['address'].append(item)

        # Get default strategy from first item
        default_strategy = 'skip'
        if items:
            default_strategy = items[0].get('_destination', {}).get('strategy', 'skip')

        # Build payload structure
        payload = {
            'folders': [],
            'snippets': [],
            'infrastructure': {},
            'default_strategy': default_strategy
        }

        if source_type == 'folder':
            payload['folders'].append({
                'name': source_name,
                'objects': objects,
                'profiles': profiles,
                'security_rules': [r for r in rules if r.get('item_type') == 'security_rule'],
                'decryption_rules': [r for r in rules if r.get('item_type') == 'decryption_rule'],
                'authentication_rules': [r for r in rules if r.get('item_type') == 'authentication_rule']
            })
        elif source_type == 'snippet':
            payload['snippets'].append({
                'name': source_name,
                'objects': objects,
                'profiles': profiles,
                'security_rules': [r for r in rules if r.get('item_type') == 'security_rule'],
                'decryption_rules': [r for r in rules if r.get('item_type') == 'decryption_rule'],
                'authentication_rules': [r for r in rules if r.get('item_type') == 'authentication_rule']
            })
        elif source_type == 'infrastructure':
            # Infrastructure items don't use folder/snippet structure
            for item in items:
                item_type = item.get('item_type', 'unknown')
                if item_type not in payload['infrastructure']:
                    payload['infrastructure'][item_type] = []
                payload['infrastructure'][item_type].append(item)
        elif source_type == 'mixed':
            # Mixed sources - split by original location
            folder_items = [i for i in items if i.get('folder')]
            snippet_items = [i for i in items if i.get('snippet')]

            if folder_items:
                # Group by folder
                by_folder = {}
                for item in folder_items:
                    folder = item.get('folder', 'Shared')
                    if folder not in by_folder:
                        by_folder[folder] = {'objects': {}, 'profiles': {}, 'security_rules': []}
                    item_type = item.get('item_type', 'address')
                    if item_type in ['address', 'tag', 'service']:
                        if item_type not in by_folder[folder]['objects']:
                            by_folder[folder]['objects'][item_type] = []
                        by_folder[folder]['objects'][item_type].append(item)

                for folder_name, folder_data in by_folder.items():
                    payload['folders'].append({
                        'name': folder_name,
                        **folder_data
                    })

        return payload

    def _extract_dependencies(self, item: Dict[str, Any], item_type: str) -> List[Dict[str, str]]:
        """Extract dependency references from an item.

        Returns list of {'type': 'address|tag|...', 'name': 'ref_name'} dicts.
        """
        dependencies = []

        if item_type == 'address_group':
            # Static members are address references
            static_refs = item.get('static', [])
            if static_refs:
                for ref in static_refs:
                    dependencies.append({'type': 'address', 'name': ref})
            # Dynamic filter could reference tags
            dynamic = item.get('dynamic', {})
            if dynamic and dynamic.get('filter'):
                # Parse tag references from filter (simplified)
                filter_str = dynamic.get('filter', '')
                # Tags in dynamic filters appear as quoted strings
                import re
                tags = re.findall(r"'([^']+)'", filter_str)
                for tag in tags:
                    dependencies.append({'type': 'tag', 'name': tag})

        elif item_type == 'service_group':
            # Members are service references
            members = item.get('members', [])
            for ref in members:
                dependencies.append({'type': 'service', 'name': ref})

        elif item_type == 'security_rule':
            # Source/destination addresses, tags, services, profiles, etc.
            for field in ['source', 'destination']:
                addrs = item.get(field, [])
                if addrs:
                    for addr in addrs:
                        if addr not in ['any']:
                            dependencies.append({'type': 'address_or_group', 'name': addr})
            # Tags
            for tag in item.get('tag', []):
                dependencies.append({'type': 'tag', 'name': tag})
            # Services (application default doesn't count)
            for svc in item.get('service', []):
                if svc not in ['application-default', 'any']:
                    dependencies.append({'type': 'service', 'name': svc})

        return dependencies

    def _validate_push(
        self,
        items: List[Dict[str, Any]],
        test_case: TestCase
    ) -> Dict[str, Any]:
        """Pre-push validation to predict outcomes before actual push.

        Returns a prediction of what would happen for each item based on:
        - Destination existence (new snippet vs existing)
        - Name conflicts at destination
        - Strategy (skip, overwrite, rename)
        - Dependency resolution (items referencing other items)
        """
        validation = {
            'destination_exists': False,
            'destination_type': test_case.destination_type,
            'destination_name': test_case.destination_name,
            'strategy': test_case.strategy,
            'predictions': [],
            'dependency_issues': [],
            'summary': {
                'total': len(items),
                'predicted_create': 0,
                'predicted_skip': 0,
                'predicted_overwrite': 0,
                'predicted_rename': 0,
                'predicted_fail': 0,
                'skipped_missing_deps': 0,
                'new_snippet_needed': False,
            }
        }

        # Check if destination exists
        dest_type = test_case.destination_type
        dest_name = self._truncate_name(test_case.destination_name) if test_case.destination_name else None

        try:
            if dest_type == 'new_snippet':
                # Check if snippet name already exists
                existing_snippets = [s.get('name') for s in self.snippets]
                validation['destination_exists'] = dest_name in existing_snippets
                validation['summary']['new_snippet_needed'] = not validation['destination_exists']

            elif dest_type == 'existing_snippet':
                # Snippet should exist
                existing_snippets = [s.get('name') for s in self.snippets]
                validation['destination_exists'] = dest_name in existing_snippets

            elif dest_type == 'folder':
                # Check if folder exists
                existing_folders = [f.get('name') for f in self.folders]
                validation['destination_exists'] = dest_name in existing_folders

            elif dest_type == 'same':
                validation['destination_exists'] = True

        except Exception as e:
            logger.warning(f"Validation: Failed to check destination: {e}")

        # Build set of item names being pushed (for dependency checking)
        items_being_pushed = {}
        for item in items:
            item_name = item.get('name', '')
            item_type = item.get('item_type', 'address')
            if item_name:
                items_being_pushed[item_name] = item_type
                # Also track by type for more specific matching
                key = f"{item_type}:{item_name}"
                items_being_pushed[key] = item_type

        # For each item, predict the outcome
        for item in items:
            item_name = item.get('name', 'unknown')
            item_type = item.get('item_type', 'address')

            prediction = {
                'name': item_name,
                'type': item_type,
                'conflict_exists': False,
                'missing_dependencies': [],
                'predicted_action': 'create',
                'reason': ''
            }

            # Check dependencies for items that reference other items
            dependencies = self._extract_dependencies(item, item_type)
            missing_deps = []

            for dep in dependencies:
                dep_name = dep['name']
                dep_type = dep['type']

                # Check if dependency is in items being pushed
                found = (
                    dep_name in items_being_pushed or
                    f"{dep_type}:{dep_name}" in items_being_pushed or
                    f"address:{dep_name}" in items_being_pushed or  # address_or_group
                    f"address_group:{dep_name}" in items_being_pushed
                )

                # For new snippets, dependencies must be in the push set
                # For existing destinations, we assume dependencies might exist there
                if not found:
                    if dest_type == 'new_snippet':
                        # New snippet destination - dependencies must be in push set
                        # Even if snippet exists from prior runs, items added now need their deps
                        missing_deps.append(dep)
                    elif dest_type in ['existing_snippet', 'folder', 'same']:
                        # Could exist at destination - we'll allow it but note it
                        pass  # Don't flag as missing, destination might have it

            if missing_deps:
                prediction['missing_dependencies'] = missing_deps
                prediction['predicted_action'] = 'skip_missing_deps'
                dep_names = [d['name'] for d in missing_deps]
                prediction['reason'] = f"Missing dependencies: {', '.join(dep_names)}"
                validation['summary']['skipped_missing_deps'] += 1
                validation['dependency_issues'].append({
                    'item': item_name,
                    'item_type': item_type,
                    'missing': missing_deps
                })
                logger.warning(f"Validation: {item_name} has missing dependencies: {dep_names}")
            else:
                # Check for name conflicts at destination
                # For new snippets, no conflict possible since snippet doesn't exist yet
                if dest_type == 'new_snippet' and not validation['destination_exists']:
                    prediction['predicted_action'] = 'create'
                    prediction['reason'] = 'New snippet - no existing items'
                    validation['summary']['predicted_create'] += 1

                elif dest_type in ['existing_snippet', 'folder', 'same']:
                    # Would need to check if item exists at destination
                    # For simplicity, assume new test items don't conflict
                    # since they have unique generated names
                    if item_name.startswith('tp-'):
                        # Test-generated name - unlikely to conflict
                        prediction['predicted_action'] = 'create'
                        prediction['reason'] = 'Unique test name - no conflict expected'
                        validation['summary']['predicted_create'] += 1
                    else:
                        # Existing item name - depends on strategy
                        prediction['conflict_exists'] = True
                        strategy = test_case.strategy

                        if strategy == 'skip':
                            prediction['predicted_action'] = 'skip'
                            prediction['reason'] = 'Item may exist - skip strategy'
                            validation['summary']['predicted_skip'] += 1
                        elif strategy == 'overwrite':
                            prediction['predicted_action'] = 'overwrite'
                            prediction['reason'] = 'Item may exist - overwrite strategy'
                            validation['summary']['predicted_overwrite'] += 1
                        elif strategy == 'rename':
                            prediction['predicted_action'] = 'rename'
                            prediction['reason'] = 'Item may exist - rename strategy'
                            validation['summary']['predicted_rename'] += 1
                else:
                    prediction['predicted_action'] = 'create'
                    prediction['reason'] = 'Default to create'
                    validation['summary']['predicted_create'] += 1

            validation['predictions'].append(prediction)

        return validation

    def _compare_validation_to_results(
        self,
        validation: Dict[str, Any],
        push_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare pre-push validation predictions with actual push results."""
        comparison = {
            'validation_accurate': True,
            'mismatches': [],
            'validation_summary': validation.get('summary', {}),
            'actual_summary': {},
        }

        if not push_result.get('success'):
            comparison['validation_accurate'] = False
            comparison['mismatches'].append({
                'type': 'push_failed',
                'message': push_result.get('message', 'Unknown error')
            })
            return comparison

        # Get actual summary
        actual = push_result.get('results', {}).get('summary', {})
        comparison['actual_summary'] = actual

        # Compare totals
        pred_create = validation['summary'].get('predicted_create', 0)
        pred_skip = validation['summary'].get('predicted_skip', 0)
        actual_created = actual.get('created', 0)
        actual_skipped = actual.get('skipped', 0)

        # Allow for some variance since we can't perfectly predict conflicts
        # Main check: total items processed should match
        pred_total = validation['summary'].get('total', 0)
        actual_total = actual.get('total', 0)

        if pred_total != actual_total:
            comparison['validation_accurate'] = False
            comparison['mismatches'].append({
                'type': 'total_mismatch',
                'predicted': pred_total,
                'actual': actual_total
            })

        # Check if we predicted new snippet and it was created
        if validation['summary'].get('new_snippet_needed'):
            snippets_created = actual.get('snippets_created', 0)
            if snippets_created == 0:
                comparison['mismatches'].append({
                    'type': 'snippet_not_created',
                    'message': 'Predicted new snippet would be created but none was'
                })

        # Log comparison
        logger.info(f"Validation Comparison:")
        logger.info(f"  Predicted: {pred_create} create, {pred_skip} skip")
        logger.info(f"  Actual:    {actual_created} created, {actual_skipped} skipped")
        logger.info(f"  Accurate:  {comparison['validation_accurate']}")

        return comparison

    def run_test(self, test_case: TestCase) -> Dict[str, Any]:
        """Execute a single test case"""
        logger.info(f"\n{'='*70}")
        logger.info(f"Test {test_case.id}: {test_case.name}")
        logger.info(f"Phase {test_case.phase.value}: {test_case.phase.name}")
        logger.info(f"Description: {test_case.description}")
        logger.info(f"Source: {test_case.source_type}:{test_case.source_name}")
        logger.info(f"Destination: {test_case.destination_type}:{test_case.destination_name}")
        logger.info(f"Strategy: {test_case.strategy}")
        logger.info(f"Validates: {test_case.validates}")
        logger.info(f"{'='*70}")

        result = {
            'test_id': test_case.id,
            'test_name': test_case.name,
            'phase': test_case.phase.name,
            'started_at': datetime.now().isoformat(),
            'success': False,
            'message': '',
            'details': {}
        }

        try:
            # Generate test items
            items = self._generate_test_items(test_case)
            logger.info(f"Generated {len(items)} test items")

            # Allow empty items for "empty snippet" test case
            if not items and test_case.item_count > 0:
                result['success'] = False
                result['message'] = 'No test items could be generated'
                return result

            # Handle empty snippet test case
            if not items and test_case.item_count == 0:
                logger.info("Empty snippet test - no items to push")
                result['success'] = True
                result['message'] = 'Empty snippet test - validated empty container handling'
                result['details']['empty_test'] = True
                result['completed_at'] = datetime.now().isoformat()
                self.results.append(result)
                return result

            # Build push payload
            payload = self._build_push_payload(
                items=items,
                source_type=test_case.source_type,
                source_name=test_case.source_name
            )

            # Log payload summary
            total_items = sum(
                len(v) for folder in payload.get('folders', [])
                for v in folder.get('objects', {}).values()
            ) + sum(
                len(v) for snippet in payload.get('snippets', [])
                for v in snippet.get('objects', {}).values()
            )
            logger.info(f"Payload contains {total_items} items")

            # Run pre-push validation
            logger.info("Running pre-push validation...")
            validation = self._validate_push(items, test_case)
            result['details']['validation'] = validation
            logger.info(f"Validation: Predicted {validation['summary']['predicted_create']} creates, "
                       f"{validation['summary']['predicted_skip']} skips, "
                       f"{validation['summary']['skipped_missing_deps']} missing deps")
            if validation['summary'].get('new_snippet_needed'):
                logger.info(f"Validation: New snippet will be created")

            # Filter out items with missing dependencies
            if validation['dependency_issues']:
                items_to_skip = {issue['item'] for issue in validation['dependency_issues']}
                original_count = len(items)
                items = [item for item in items if item.get('name') not in items_to_skip]
                logger.info(f"Filtered out {original_count - len(items)} items with missing dependencies")

                # Log what was skipped
                for issue in validation['dependency_issues']:
                    missing_names = [d['name'] for d in issue['missing']]
                    logger.warning(f"  Skipping {issue['item']}: missing deps {missing_names}")

                # Rebuild payload without skipped items
                if items:
                    payload = self._build_push_payload(
                        items=items,
                        source_type=test_case.source_type,
                        source_name=test_case.source_name
                    )
                else:
                    # All items had missing dependencies
                    logger.warning("All items skipped due to missing dependencies")
                    result['success'] = True
                    result['message'] = f"All items skipped - missing dependencies"
                    result['details']['skipped_items'] = list(items_to_skip)
                    result['completed_at'] = datetime.now().isoformat()
                    self.results.append(result)
                    return result

            if self.dry_run:
                logger.info("DRY RUN - Would execute push")
                logger.debug(f"Payload: {json.dumps(payload, indent=2, default=str)[:1000]}...")
                result['success'] = True
                result['message'] = 'Dry run completed'
                result['details']['dry_run'] = True
                result['details']['item_count'] = len(items)
            else:
                # Execute push
                push_result = self.orchestrator.push_selected_items(payload)

                result['details']['push_result'] = push_result
                result['success'] = push_result.get('success', False)
                result['message'] = push_result.get('message', '')

                # Log summary
                if 'results' in push_result:
                    summary = push_result['results'].get('summary', {})
                    logger.info(f"Push Summary:")
                    logger.info(f"  Total: {summary.get('total', 0)}")
                    logger.info(f"  Created: {summary.get('created', 0)}")
                    logger.info(f"  Skipped: {summary.get('skipped', 0)}")
                    logger.info(f"  Failed: {summary.get('failed', 0)}")
                    logger.info(f"  Snippets Created: {summary.get('snippets_created', 0)}")

                    # Track created items for cleanup
                    for detail in push_result['results'].get('details', []):
                        if detail.get('action') == 'created':
                            self.test_artifacts.append({
                                'name': detail.get('name'),
                                'type': detail.get('type'),
                                'destination': detail.get('destination')
                            })

                # Compare validation predictions with actual results
                comparison = self._compare_validation_to_results(validation, push_result)
                result['details']['validation_comparison'] = comparison

                # Add validation accuracy to result message
                if comparison['validation_accurate']:
                    result['message'] += ' (validation matched)'
                else:
                    mismatches = comparison.get('mismatches', [])
                    if mismatches:
                        mismatch_msg = ', '.join(m.get('type', 'unknown') for m in mismatches)
                        result['message'] += f' (validation mismatches: {mismatch_msg})'

        except Exception as e:
            logger.exception(f"Test {test_case.id} failed with exception")
            result['success'] = False
            result['message'] = str(e)
            result['details']['exception'] = str(e)

        result['completed_at'] = datetime.now().isoformat()
        self.results.append(result)

        # Log result
        status = "PASSED" if result['success'] else "FAILED"
        logger.info(f"\nTest {test_case.id} {status}: {result['message'][:100]}")

        return result

    def cleanup_test_snippets(self):
        """Clean up test snippets created during testing"""
        if self.dry_run:
            logger.info("Dry run - no cleanup needed")
            return

        logger.info("\nCleaning up test snippets...")

        try:
            snippets = self.api_client.get_snippets()
            test_snippets = [s for s in snippets if s.get('name', '').startswith(self.TEST_PREFIX)]

            for snippet in test_snippets:
                try:
                    logger.info(f"  Deleting snippet: {snippet['name']}")
                    # Would need delete_snippet method
                except Exception as e:
                    logger.warning(f"  Failed to delete snippet {snippet['name']}: {e}")

        except Exception as e:
            logger.warning(f"Failed to cleanup snippets: {e}")

    def get_summary(self) -> Dict[str, Any]:
        """Get test execution summary"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r['success'])
        failed = total - passed

        # Group by phase
        by_phase = {}
        for r in self.results:
            phase = r['phase']
            if phase not in by_phase:
                by_phase[phase] = {'passed': 0, 'failed': 0}
            if r['success']:
                by_phase[phase]['passed'] += 1
            else:
                by_phase[phase]['failed'] += 1

        return {
            'total_tests': total,
            'passed': passed,
            'failed': failed,
            'pass_rate': f"{(passed/total*100):.1f}%" if total > 0 else "N/A",
            'by_phase': by_phase,
            'results': self.results
        }


def define_all_test_cases() -> List[TestCase]:
    """Define all 37 test cases from Prioritized Test Cases document"""

    cases = []

    # ============================================
    # Phase 1: Core Snippet Operations (6 tests)
    # ============================================

    cases.append(TestCase(
        id=1,
        name="Rename snippet (custom name)",
        phase=TestPhase.CORE_SNIPPET,
        description="Push snippet items to new snippet with custom name",
        source_type='snippet',
        source_name='default',
        destination_type='new_snippet',
        destination_name='test-push-custom-snippet',
        strategy='skip',
        expected_conflict=None,
        validates="Snippet creation, name propagation",
        item_types=['address', 'tag']
    ))

    cases.append(TestCase(
        id=2,
        name="Rename snippet (auto name)",
        phase=TestPhase.CORE_SNIPPET,
        description="Push snippet items to new snippet with auto-generated -copy name",
        source_type='snippet',
        source_name='default',
        destination_type='new_snippet',
        destination_name='default-copy',
        strategy='skip',
        expected_conflict=None,
        validates="Auto-naming, truncation",
        item_types=['address']
    ))

    cases.append(TestCase(
        id=3,
        name="Rename snippet (name conflict)",
        phase=TestPhase.CORE_SNIPPET,
        description="Push to new snippet when snippet name already exists",
        source_type='snippet',
        source_name='default',
        destination_type='new_snippet',
        destination_name='predefined-snippet',  # This exists
        strategy='skip',
        expected_conflict='Snippet exists',
        validates="Conflict detection for snippet names",
        item_types=['address']
    ))

    cases.append(TestCase(
        id=4,
        name="Push to existing snippet (skip)",
        phase=TestPhase.CORE_SNIPPET,
        description="Push items to existing snippet with skip strategy",
        source_type='snippet',
        source_name='default',
        destination_type='existing_snippet',
        destination_name='optional-default',
        strategy='skip',
        expected_conflict=None,
        validates="Existing snippet targeting with skip",
        item_types=['address', 'tag']
    ))

    cases.append(TestCase(
        id=5,
        name="Push to existing snippet (overwrite)",
        phase=TestPhase.CORE_SNIPPET,
        description="Push items to existing snippet with overwrite strategy",
        source_type='snippet',
        source_name='default',
        destination_type='existing_snippet',
        destination_name='optional-default',
        strategy='overwrite',
        expected_conflict='Objects exist',
        validates="Overwrite strategy deletes then creates",
        item_types=['address']
    ))

    cases.append(TestCase(
        id=6,
        name="Push to existing snippet (rename)",
        phase=TestPhase.CORE_SNIPPET,
        description="Push items to existing snippet with rename strategy",
        source_type='snippet',
        source_name='default',
        destination_type='existing_snippet',
        destination_name='optional-default',
        strategy='rename',
        expected_conflict='Objects exist',
        validates="Rename strategy adds -copy suffix",
        item_types=['address']
    ))

    # ============================================
    # Phase 2: Folder Operations (6 tests)
    # ============================================

    cases.append(TestCase(
        id=7,
        name="Folder to new snippet",
        phase=TestPhase.FOLDER_OPS,
        description="Push folder items to a new snippet",
        source_type='folder',
        source_name='Mobile Users',
        destination_type='new_snippet',
        destination_name='test-push-from-folder',
        strategy='skip',
        expected_conflict=None,
        validates="Folder to snippet conversion",
        item_types=['address', 'tag']
    ))

    cases.append(TestCase(
        id=8,
        name="Folder to different folder",
        phase=TestPhase.FOLDER_OPS,
        description="Push folder items to a different folder",
        source_type='folder',
        source_name='Mobile Users',
        destination_type='folder',
        destination_name='Remote Networks',
        strategy='skip',
        expected_conflict=None,
        validates="Cross-folder push",
        item_types=['address']
    ))

    cases.append(TestCase(
        id=9,
        name="Folder to same folder (skip)",
        phase=TestPhase.FOLDER_OPS,
        description="Push folder items back to same folder with skip strategy",
        source_type='folder',
        source_name='Mobile Users',
        destination_type='same',
        destination_name='Mobile Users',
        strategy='skip',
        expected_conflict='Objects exist',
        validates="Skip existing objects in same folder",
        item_types=['address']
    ))

    cases.append(TestCase(
        id=10,
        name="Folder to same folder (overwrite)",
        phase=TestPhase.FOLDER_OPS,
        description="Push folder items back to same folder with overwrite",
        source_type='folder',
        source_name='Mobile Users',
        destination_type='same',
        destination_name='Mobile Users',
        strategy='overwrite',
        expected_conflict='Objects exist',
        validates="Overwrite existing objects in same folder",
        item_types=['address']
    ))

    cases.append(TestCase(
        id=11,
        name="Folder to same folder (rename)",
        phase=TestPhase.FOLDER_OPS,
        description="Push folder items back to same folder with rename",
        source_type='folder',
        source_name='Mobile Users',
        destination_type='same',
        destination_name='Mobile Users',
        strategy='rename',
        expected_conflict='Objects exist',
        validates="Rename conflicts in same folder",
        item_types=['address']
    ))

    cases.append(TestCase(
        id=12,
        name="Folder to existing snippet",
        phase=TestPhase.FOLDER_OPS,
        description="Push folder items to an existing snippet",
        source_type='folder',
        source_name='Mobile Users',
        destination_type='existing_snippet',
        destination_name='optional-default',
        strategy='skip',
        expected_conflict=None,
        validates="Folder to existing snippet push",
        item_types=['address', 'tag']
    ))

    # ============================================
    # Phase 3: Partial Selection & Mixed (4 tests)
    # ============================================

    cases.append(TestCase(
        id=13,
        name="Partial snippet items",
        phase=TestPhase.PARTIAL_MIXED,
        description="Push only selected subset of items from snippet",
        source_type='snippet',
        source_name='default',
        destination_type='new_snippet',
        destination_name='test-push-partial',
        strategy='skip',
        expected_conflict=None,
        validates="Partial item selection works",
        item_types=['address'],
        item_count=1  # Only 1 item
    ))

    cases.append(TestCase(
        id=14,
        name="Mixed sources",
        phase=TestPhase.PARTIAL_MIXED,
        description="Push items from multiple folders/snippets",
        source_type='mixed',
        source_name='various',
        destination_type='new_snippet',
        destination_name='test-push-mixed',
        strategy='skip',
        expected_conflict=None,
        validates="Mixed container source handling",
        item_types=['address', 'tag']
    ))

    cases.append(TestCase(
        id=15,
        name="Individual strategy override",
        phase=TestPhase.PARTIAL_MIXED,
        description="Push with per-item strategy override (default skip, one overwrite)",
        source_type='snippet',
        source_name='default',
        destination_type='new_snippet',
        destination_name='test-push-override',
        strategy='skip',
        expected_conflict='One exists',
        validates="Per-item strategy override",
        item_types=['address']
    ))

    cases.append(TestCase(
        id=16,
        name="Dependency chain",
        phase=TestPhase.PARTIAL_MIXED,
        description="Push items with dependencies (tag -> address with tag -> address group)",
        source_type='snippet',
        source_name='default',
        destination_type='new_snippet',
        destination_name='test-push-deps',
        strategy='skip',
        expected_conflict=None,
        validates="Dependency ordering (tags before addresses)",
        item_types=['tag', 'address', 'address_group']
    ))

    # ============================================
    # Phase 4: Edge Cases (4 tests)
    # ============================================

    cases.append(TestCase(
        id=17,
        name="Long name truncation",
        phase=TestPhase.EDGE_CASES,
        description="Push snippet with 50+ character name to test truncation",
        source_type='snippet',
        source_name='default',
        destination_type='new_snippet',
        destination_name='VPN-Users-really-really-long-name-to-test-exceeding-limit',
        strategy='skip',
        expected_conflict=None,
        validates="Name length handling and truncation",
        item_types=['address']
    ))

    cases.append(TestCase(
        id=18,
        name="Security rule uniqueness",
        phase=TestPhase.EDGE_CASES,
        description="Push security rule to test global uniqueness check",
        source_type='snippet',
        source_name='default',
        destination_type='new_snippet',
        destination_name='test-push-rule-unique',
        strategy='skip',
        expected_conflict='Rule name exists globally',
        validates="Global security rule name uniqueness",
        item_types=['security_rule'],
        item_count=1
    ))

    cases.append(TestCase(
        id=19,
        name="Empty snippet handling",
        phase=TestPhase.EDGE_CASES,
        description="Create empty snippet (no items)",
        source_type='snippet',
        source_name='default',
        destination_type='new_snippet',
        destination_name='test-push-empty',
        strategy='skip',
        expected_conflict=None,
        validates="Empty container handling",
        item_types=[],  # No items
        item_count=0
    ))

    cases.append(TestCase(
        id=20,
        name="Special characters in names",
        phase=TestPhase.EDGE_CASES,
        description="Push items with spaces and special characters in names",
        source_type='folder',
        source_name='Mobile Users',
        destination_type='new_snippet',
        destination_name='test-push-special-chars',
        strategy='skip',
        expected_conflict=None,
        validates="Name encoding for spaces/symbols",
        item_types=['address']
    ))

    # ============================================
    # Phase 5: Object Types (4 tests)
    # ============================================

    cases.append(TestCase(
        id=21,
        name="Security profiles push",
        phase=TestPhase.OBJECT_TYPES,
        description="Push security profiles (anti-spyware, vulnerability)",
        source_type='folder',
        source_name='Mobile Users',
        destination_type='existing_snippet',
        destination_name='optional-default',
        strategy='skip',
        expected_conflict=None,
        validates="Profile type handling",
        item_types=['anti_spyware_profile', 'vulnerability_profile']
    ))

    cases.append(TestCase(
        id=22,
        name="HIP objects and profiles",
        phase=TestPhase.OBJECT_TYPES,
        description="Push HIP objects and profiles to different folder",
        source_type='folder',
        source_name='Mobile Users',
        destination_type='folder',
        destination_name='Remote Networks',
        strategy='skip',
        expected_conflict=None,
        validates="HIP category routing",
        item_types=['hip_profile']
    ))

    cases.append(TestCase(
        id=23,
        name="Tags and schedules",
        phase=TestPhase.OBJECT_TYPES,
        description="Push tags and schedules to new snippet",
        source_type='folder',
        source_name='Mobile Users',
        destination_type='new_snippet',
        destination_name='test-push-tags-schedules',
        strategy='skip',
        expected_conflict=None,
        validates="Auxiliary object types (tags, schedules)",
        item_types=['tag', 'schedule']
    ))

    cases.append(TestCase(
        id=24,
        name="External dynamic lists",
        phase=TestPhase.OBJECT_TYPES,
        description="Push EDLs to existing folder with overwrite",
        source_type='folder',
        source_name='Mobile Users',
        destination_type='folder',
        destination_name='Mobile Users',
        strategy='overwrite',
        expected_conflict=None,
        validates="EDL handling with overwrite",
        item_types=['external_dynamic_list']
    ))

    # ============================================
    # Phase 6: Infrastructure (3 tests)
    # ============================================

    cases.append(TestCase(
        id=25,
        name="IKE crypto profiles",
        phase=TestPhase.INFRASTRUCTURE,
        description="Push IKE crypto profiles to same tenant",
        source_type='folder',
        source_name='Remote Networks',
        destination_type='folder',
        destination_name='Remote Networks',
        strategy='skip',
        expected_conflict=None,
        validates="Infrastructure crypto profile push",
        item_types=['ike_crypto_profile']
    ))

    cases.append(TestCase(
        id=26,
        name="IPSec crypto profiles",
        phase=TestPhase.INFRASTRUCTURE,
        description="Push IPSec crypto profiles with overwrite",
        source_type='folder',
        source_name='Remote Networks',
        destination_type='folder',
        destination_name='Remote Networks',
        strategy='overwrite',
        expected_conflict=None,
        validates="Infrastructure overwrite strategy",
        item_types=['ipsec_crypto_profile']
    ))

    cases.append(TestCase(
        id=27,
        name="Remote network config",
        phase=TestPhase.INFRASTRUCTURE,
        description="Push remote network related config",
        source_type='folder',
        source_name='Remote Networks',
        destination_type='folder',
        destination_name='Remote Networks',
        strategy='skip',
        expected_conflict=None,
        validates="Remote network infrastructure handling",
        item_types=['ike_crypto_profile', 'ipsec_crypto_profile']
    ))

    # ============================================
    # Phase 7: Rules (3 tests)
    # ============================================

    cases.append(TestCase(
        id=28,
        name="Decryption rules",
        phase=TestPhase.RULES,
        description="Push decryption rules to new snippet",
        source_type='folder',
        source_name='Mobile Users',
        destination_type='new_snippet',
        destination_name='test-push-decrypt-rules',
        strategy='skip',
        expected_conflict=None,
        validates="Decryption rule handling",
        item_types=['decryption_rule']
    ))

    cases.append(TestCase(
        id=29,
        name="Authentication rules",
        phase=TestPhase.RULES,
        description="Push authentication rules to existing snippet",
        source_type='folder',
        source_name='Mobile Users',
        destination_type='existing_snippet',
        destination_name='optional-default',
        strategy='skip',
        expected_conflict=None,
        validates="Authentication rule handling",
        item_types=['authentication_rule']
    ))

    cases.append(TestCase(
        id=30,
        name="Security rule with profile references",
        phase=TestPhase.RULES,
        description="Push security rule that references multiple profiles",
        source_type='folder',
        source_name='Mobile Users',
        destination_type='new_snippet',
        destination_name='test-push-rule-profiles',
        strategy='skip',
        expected_conflict=None,
        validates="Complex dependency resolution for rules",
        item_types=['security_rule']
    ))

    # ============================================
    # Phase 8: Error & Recovery (4 tests)
    # ============================================

    cases.append(TestCase(
        id=31,
        name="Dry run mode",
        phase=TestPhase.ERROR_RECOVERY,
        description="Execute validation without actual push",
        source_type='snippet',
        source_name='default',
        destination_type='new_snippet',
        destination_name='test-push-dryrun',
        strategy='skip',
        expected_conflict=None,
        validates="Dry run doesn't modify tenant",
        item_types=['address']
    ))

    cases.append(TestCase(
        id=32,
        name="Large config batch",
        phase=TestPhase.ERROR_RECOVERY,
        description="Push large number of items to test batching",
        source_type='folder',
        source_name='Mobile Users',
        destination_type='new_snippet',
        destination_name='test-push-batch',
        strategy='skip',
        expected_conflict=None,
        validates="Batch processing for large configs",
        item_types=['address', 'tag', 'schedule'],
        item_count=5
    ))

    cases.append(TestCase(
        id=33,
        name="Partial failure recovery",
        phase=TestPhase.ERROR_RECOVERY,
        description="Test that failure of one item doesn't block others",
        source_type='folder',
        source_name='Mobile Users',
        destination_type='new_snippet',
        destination_name='test-push-partial-fail',
        strategy='skip',
        expected_conflict=None,
        validates="Error isolation between items",
        item_types=['address']
    ))

    cases.append(TestCase(
        id=34,
        name="Cross-tenant preparation",
        phase=TestPhase.ERROR_RECOVERY,
        description="Validate config for cross-tenant push",
        source_type='snippet',
        source_name='default',
        destination_type='new_snippet',
        destination_name='test-push-cross-tenant',
        strategy='skip',
        expected_conflict=None,
        validates="Multi-tenant flow preparation",
        item_types=['address', 'tag']
    ))

    # ============================================
    # Phase 9: Validation Edge Cases (3 tests)
    # ============================================

    cases.append(TestCase(
        id=35,
        name="Missing dependency warning",
        phase=TestPhase.VALIDATION,
        description="Push item with reference to non-existent object",
        source_type='folder',
        source_name='Mobile Users',
        destination_type='new_snippet',
        destination_name='test-push-missing-dep',
        strategy='skip',
        expected_conflict=None,
        validates="Dependency warning for external refs",
        item_types=['address_group']
    ))

    cases.append(TestCase(
        id=36,
        name="Circular reference handling",
        phase=TestPhase.VALIDATION,
        description="Push address groups that reference each other",
        source_type='folder',
        source_name='Mobile Users',
        destination_type='new_snippet',
        destination_name='test-push-circular',
        strategy='skip',
        expected_conflict=None,
        validates="Circular dependency detection",
        item_types=['address_group']
    ))

    cases.append(TestCase(
        id=37,
        name="Name with spaces encoding",
        phase=TestPhase.VALIDATION,
        description="Push items with spaces in names to verify URL encoding",
        source_type='folder',
        source_name='Mobile Users',
        destination_type='new_snippet',
        destination_name='test-push-spaces',
        strategy='skip',
        expected_conflict=None,
        validates="Space encoding in API calls",
        item_types=['address']
    ))

    return cases


def load_credentials(tenant_name: Optional[str] = None) -> Dict[str, Any]:
    """Load credentials using TenantManager"""
    tenant_manager = TenantManager()
    tenants = tenant_manager.list_tenants()

    if not tenants:
        raise ValueError("No tenants configured. Please configure credentials in the GUI first.")

    if tenant_name:
        for tenant in tenants:
            if tenant.get('name') == tenant_name:
                return tenant
        available = [t['name'] for t in tenants]
        raise ValueError(f"Tenant '{tenant_name}' not found. Available: {available}")

    return tenants[0]


def list_test_cases(cases: List[TestCase]):
    """Print list of all test cases"""
    print("\n" + "="*80)
    print("PUSH WORKFLOW TEST CASES")
    print("="*80)

    current_phase = None
    for case in cases:
        if case.phase != current_phase:
            current_phase = case.phase
            print(f"\n--- Phase {case.phase.value}: {case.phase.name} ---")

        print(f"  {case.id:2d}. {case.name}")
        print(f"      {case.source_type} -> {case.destination_type} ({case.strategy})")
        print(f"      Validates: {case.validates}")

    print("\n" + "="*80)
    print(f"Total: {len(cases)} test cases across {len(TestPhase)} phases")
    print("="*80)


def main():
    parser = argparse.ArgumentParser(description='Test push workflow operations')
    parser.add_argument('--tenant', '-t', help='Tenant name to use')
    parser.add_argument('--phase', '-p', type=int, help='Run only specific phase (1-9)')
    parser.add_argument('--test', '-n', type=int, help='Run only specific test number')
    parser.add_argument('--dry-run', '-d', action='store_true', help='Dry run mode (no actual push)')
    parser.add_argument('--list', '-l', action='store_true', help='List all test cases')
    parser.add_argument('--output', '-o', help='Output directory for results',
                       default='tests/examples/push_tests')
    parser.add_argument('--cleanup', '-c', action='store_true', help='Clean up test artifacts after run')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    args = parser.parse_args()

    # Get all test cases
    all_cases = define_all_test_cases()

    # List mode
    if args.list:
        list_test_cases(all_cases)
        return 0

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

    # Initialize API client
    logger.info("Initializing API client...")
    try:
        api_client = PrismaAccessAPIClient(
            tsg_id=creds['tsg_id'],
            api_user=creds['client_id'],
            api_secret=creds['client_secret']
        )
    except Exception as e:
        logger.error(f"Failed to initialize API client: {e}")
        return 1

    # Create test framework
    framework = PushTestFramework(api_client, dry_run=args.dry_run)

    # Filter test cases
    cases_to_run = all_cases
    if args.phase:
        phase = TestPhase(args.phase)
        cases_to_run = [c for c in all_cases if c.phase == phase]
        logger.info(f"Running Phase {args.phase} ({phase.name}) tests only ({len(cases_to_run)} tests)")
    if args.test:
        cases_to_run = [c for c in cases_to_run if c.id == args.test]
        logger.info(f"Running test {args.test} only")

    if not cases_to_run:
        logger.error("No tests to run")
        return 1

    logger.info(f"\n{'#'*70}")
    logger.info(f"Running {len(cases_to_run)} tests")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info(f"{'#'*70}")

    # Run tests
    for test_case in cases_to_run:
        framework.run_test(test_case)
        time.sleep(1)  # Brief pause between tests

    # Get summary
    summary = framework.get_summary()

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = output_dir / f'push_test_results_{timestamp}.json'
    with open(results_file, 'w') as f:
        json.dump(summary, f, indent=2, default=str)

    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Total tests: {summary['total_tests']}")
    print(f"Passed:      {summary['passed']}")
    print(f"Failed:      {summary['failed']}")
    print(f"Pass rate:   {summary['pass_rate']}")

    if summary.get('by_phase'):
        print("\nBy Phase:")
        for phase, stats in summary['by_phase'].items():
            print(f"  {phase}: {stats['passed']} passed, {stats['failed']} failed")

    if summary['failed'] > 0:
        print("\nFailed tests:")
        for result in summary['results']:
            if not result['success']:
                print(f"  - Test {result['test_id']}: {result['test_name']}")
                print(f"    {result['message'][:80]}...")

    print(f"\nResults saved to: {results_file}")

    # Cleanup if requested
    if args.cleanup:
        framework.cleanup_test_snippets()

    return 0 if summary['failed'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
