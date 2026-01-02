#!/usr/bin/env python3
"""
Capture production configuration examples from a Prisma Access tenant.

This script connects to a production (or lab) tenant and captures
real-world configuration examples for all modeled types. These examples
are used to:
- Validate model implementations
- Discover missing properties
- Create comprehensive test cases
- Document real-world usage patterns

Usage:
    python scripts/capture_production_examples.py --tenant "Lab Tenant"
    python scripts/capture_production_examples.py --all-types
    python scripts/capture_production_examples.py --type address_object --folder "Mobile Users"
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.tenant_manager import TenantManager
from prisma.api_client import PrismaAccessAPIClient
from config.models.factory import ConfigItemFactory
from config.models.objects import *
from config.models.profiles import *
from config.models.policies import *
from config.models.infrastructure import *


class ProductionExampleCapture:
    """Captures production configuration examples"""
    
    # Define all types we want to capture
    OBJECT_TYPES = [
        ('tag', Tag),
        ('address_object', AddressObject),
        ('address_group', AddressGroup),
        ('service_object', ServiceObject),
        ('service_group', ServiceGroup),
        ('application_object', ApplicationObject),
        ('application_group', ApplicationGroup),
        ('application_filter', ApplicationFilter),
        ('schedule', Schedule),
    ]
    
    PROFILE_TYPES = [
        ('authentication_profile', AuthenticationProfile),
        ('decryption_profile', DecryptionProfile),
        ('url_filtering_profile', URLFilteringProfile),
        ('antivirus_profile', AntivirusProfile),
        ('anti_spyware_profile', AntiSpywareProfile),
        ('vulnerability_profile', VulnerabilityProfile),
        ('file_blocking_profile', FileBlockingProfile),
        ('wildfire_profile', WildfireProfile),
        ('profile_group', ProfileGroup),
        ('hip_profile', HIPProfile),
        ('hip_object', HIPObject),
        ('http_header_profile', HTTPHeaderProfile),
        ('certificate_profile', CertificateProfile),
        ('ocsp_responder', OCSPResponder),
        ('scep_profile', SCEPProfile),
        ('qos_profile', QoSProfile),
    ]
    
    POLICY_TYPES = [
        ('security_rule', SecurityRule),
        ('decryption_rule', DecryptionRule),
        ('authentication_rule', AuthenticationRule),
        ('qos_policy_rule', QoSPolicyRule),
    ]
    
    INFRASTRUCTURE_TYPES = [
        ('ike_crypto_profile', IKECryptoProfile),
        ('ipsec_crypto_profile', IPsecCryptoProfile),
        ('ike_gateway', IKEGateway),
        ('ipsec_tunnel', IPsecTunnel),
        ('service_connection', ServiceConnection),
        ('agent_profile', AgentProfile),
        ('portal', Portal),
        ('gateway', Gateway),
    ]
    
    def __init__(self, api_client: PrismaAccessAPIClient, output_dir: Path):
        """
        Initialize capture.
        
        Args:
            api_client: Authenticated API client
            output_dir: Directory to save captured examples
        """
        self.client = api_client
        self.output_dir = output_dir
        self.raw_dir = output_dir / "raw"
        self.stats = {
            'total_captured': 0,
            'by_type': {},
            'by_location': {},
            'errors': []
        }
    
    def capture_all(
        self,
        folders: Optional[List[str]] = None,
        snippets: Optional[List[str]] = None,
        max_per_type: int = 10
    ):
        """
        Capture examples for all types.
        
        Args:
            folders: List of folders to capture from (None = all)
            snippets: List of snippets to capture from (None = all)
            max_per_type: Maximum examples per type
        """
        print("=" * 60)
        print("PRODUCTION EXAMPLE CAPTURE")
        print("=" * 60)
        print(f"Output directory: {self.output_dir}")
        print(f"Max per type: {max_per_type}")
        print()
        
        # Get folders and snippets if not specified
        if folders is None:
            folders = self._get_folders()
        if snippets is None:
            snippets = self._get_snippets()
        
        print(f"Folders: {len(folders)}")
        print(f"Snippets: {len(snippets)}")
        print()
        
        # Capture objects
        print("Capturing Objects...")
        for item_type, item_class in self.OBJECT_TYPES:
            self._capture_type(item_type, item_class, folders, snippets, max_per_type, "objects")
        
        # Capture profiles
        print("\nCapturing Profiles...")
        for item_type, item_class in self.PROFILE_TYPES:
            self._capture_type(item_type, item_class, folders, snippets, max_per_type, "profiles")
        
        # Capture policies
        print("\nCapturing Policies...")
        for item_type, item_class in self.POLICY_TYPES:
            self._capture_type(item_type, item_class, folders, snippets, max_per_type, "policies")
        
        # Capture infrastructure
        print("\nCapturing Infrastructure...")
        for item_type, item_class in self.INFRASTRUCTURE_TYPES:
            self._capture_type(item_type, item_class, folders, None, max_per_type, "infrastructure")
        
        # Print summary
        self._print_summary()
    
    def _get_folders(self) -> List[str]:
        """Get list of folders from tenant"""
        try:
            response = self.client.get_security_policy_folders()
            folders = [f['name'] for f in response if 'name' in f]
            return folders
        except Exception as e:
            print(f"Warning: Could not fetch folders: {e}")
            return ['Mobile Users', 'Remote Networks', 'Shared']
    
    def _get_snippets(self) -> List[str]:
        """Get list of snippets from tenant"""
        try:
            response = self.client.get_security_policy_snippets()
            snippets = [s['name'] for s in response if 'name' in s]
            return snippets
        except Exception as e:
            print(f"Warning: Could not fetch snippets: {e}")
            return []
    
    def _capture_type(
        self,
        item_type: str,
        item_class: type,
        folders: List[str],
        snippets: Optional[List[str]],
        max_per_type: int,
        category: str
    ):
        """Capture examples for a specific type"""
        print(f"  {item_type}...", end=" ", flush=True)
        
        captured_count = 0
        all_items = []
        
        try:
            # Capture from folders
            for folder in folders:
                if captured_count >= max_per_type:
                    break
                
                try:
                    items = self.client.get_items(item_class, folder, is_snippet=False, use_factory=False)
                    
                    for item in items:
                        if captured_count >= max_per_type:
                            break
                        
                        # Save raw config
                        self._save_raw(item.raw_config, item_type, item.name, folder, False)
                        all_items.append(item.raw_config)
                        captured_count += 1
                    
                except Exception as e:
                    self.stats['errors'].append(f"{item_type}/{folder}: {e}")
            
            # Capture from snippets
            if snippets:
                for snippet in snippets:
                    if captured_count >= max_per_type:
                        break
                    
                    try:
                        items = self.client.get_items(item_class, snippet, is_snippet=True, use_factory=False)
                        
                        for item in items:
                            if captured_count >= max_per_type:
                                break
                            
                            # Save raw config
                            self._save_raw(item.raw_config, item_type, item.name, snippet, True)
                            all_items.append(item.raw_config)
                            captured_count += 1
                        
                    except Exception as e:
                        self.stats['errors'].append(f"{item_type}/{snippet}: {e}")
            
            # Update stats
            self.stats['total_captured'] += captured_count
            self.stats['by_type'][item_type] = captured_count
            
            print(f"✓ {captured_count} captured")
            
        except Exception as e:
            print(f"✗ Error: {e}")
            self.stats['errors'].append(f"{item_type}: {e}")
    
    def _save_raw(
        self,
        config: Dict[str, Any],
        item_type: str,
        name: str,
        location: str,
        is_snippet: bool
    ):
        """Save raw configuration to file"""
        # Create directory structure
        type_dir = self.raw_dir / item_type
        type_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename (sanitize name)
        safe_name = name.replace('/', '_').replace(' ', '_')
        safe_location = location.replace('/', '_').replace(' ', '_')
        loc_type = "snippet" if is_snippet else "folder"
        filename = f"{safe_name}_{loc_type}_{safe_location}.json"
        
        # Save file
        filepath = type_dir / filename
        with open(filepath, 'w') as f:
            json.dump(config, f, indent=2)
    
    def _print_summary(self):
        """Print capture summary"""
        print()
        print("=" * 60)
        print("CAPTURE SUMMARY")
        print("=" * 60)
        print(f"Total items captured: {self.stats['total_captured']}")
        print()
        
        print("By Type:")
        for item_type, count in sorted(self.stats['by_type'].items()):
            print(f"  {item_type}: {count}")
        
        if self.stats['errors']:
            print()
            print(f"Errors: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:10]:  # Show first 10
                print(f"  - {error}")
            if len(self.stats['errors']) > 10:
                print(f"  ... and {len(self.stats['errors']) - 10} more")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Capture production configuration examples",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Capture from saved tenant
  python scripts/capture_production_examples.py --tenant "Lab Tenant"
  
  # Capture specific type
  python scripts/capture_production_examples.py --type address_object
  
  # Capture with custom limit
  python scripts/capture_production_examples.py --max 20
        """
    )
    
    parser.add_argument(
        '--tenant',
        help='Saved tenant name to connect to'
    )
    parser.add_argument(
        '--type',
        help='Specific type to capture (e.g., address_object)'
    )
    parser.add_argument(
        '--folder',
        help='Specific folder to capture from'
    )
    parser.add_argument(
        '--max',
        type=int,
        default=10,
        help='Maximum examples per type (default: 10)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('tests/examples/production'),
        help='Output directory (default: tests/examples/production)'
    )
    
    args = parser.parse_args()
    
    # Get tenant credentials
    if args.tenant:
        manager = TenantManager()
        tenant = manager.get_tenant_by_name(args.tenant)
        if not tenant:
            print(f"Error: Tenant '{args.tenant}' not found")
            return 1
        
        # Decrypt credentials
        from config.storage.crypto_utils import decrypt_data, load_cipher
        cipher = load_cipher()
        tsg_id = decrypt_data(tenant['tsg_id'], cipher).decode()
        api_user = decrypt_data(tenant['api_user'], cipher).decode()
        api_secret = decrypt_data(tenant['api_secret'], cipher).decode()
    else:
        print("Error: --tenant is required")
        print("Available tenants:")
        manager = TenantManager()
        for t in manager.list_tenants():
            print(f"  - {t['name']}")
        return 1
    
    # Connect to API
    print(f"Connecting to tenant: {args.tenant}")
    try:
        client = PrismaAccessAPIClient(tsg_id, api_user, api_secret)
        print("✓ Connected successfully")
        print()
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return 1
    
    # Create capture instance
    capture = ProductionExampleCapture(client, args.output)
    
    # Capture examples
    folders = [args.folder] if args.folder else None
    capture.capture_all(folders=folders, max_per_type=args.max)
    
    print()
    print("✓ Capture complete!")
    print(f"Raw examples saved to: {capture.raw_dir}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
