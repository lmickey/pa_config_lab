#!/usr/bin/env python3
"""
Generate Test Fixtures from Production Examples.

This script converts the 223 production examples into organized test fixtures
that can be used for unit testing and integration testing.

Output structure:
    tests/fixtures/
    ├── objects/
    │   ├── address_objects.json
    │   ├── service_groups.json
    │   └── schedules.json
    ├── profiles/
    │   ├── security_profiles.json
    │   └── qos_profiles.json
    ├── policies/
    │   ├── security_rules.json
    │   └── qos_rules.json
    └── infrastructure/
        ├── vpn_configs.json
        └── agent_profiles.json

Usage:
    python scripts/generate_test_fixtures.py
    python scripts/generate_test_fixtures.py --output tests/fixtures
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# Categorize types
OBJECT_TYPES = [
    'tag', 'address_object', 'address_group', 'service_object', 
    'service_group', 'application_object', 'application_group',
    'application_filter', 'schedule'
]

PROFILE_TYPES = [
    'authentication_profile', 'decryption_profile', 'url_filtering_profile',
    'antivirus_profile', 'anti_spyware_profile', 'vulnerability_profile',
    'file_blocking_profile', 'wildfire_profile', 'profile_group',
    'hip_profile', 'hip_object', 'http_header_profile',
    'certificate_profile', 'ocsp_responder', 'scep_profile', 'qos_profile'
]

POLICY_TYPES = [
    'security_rule', 'decryption_rule', 'authentication_rule', 'qos_policy_rule'
]

INFRASTRUCTURE_TYPES = [
    'ike_crypto_profile', 'ipsec_crypto_profile', 'ike_gateway',
    'ipsec_tunnel', 'service_connection', 'agent_profile', 'portal', 'gateway'
]


class FixtureGenerator:
    """Generates test fixtures from production examples"""
    
    def __init__(self, input_dir: Path, output_dir: Path):
        """
        Initialize generator.
        
        Args:
            input_dir: Directory with production examples
            output_dir: Directory to write fixtures
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.stats = {
            'total_examples': 0,
            'by_category': defaultdict(int),
            'by_type': defaultdict(int)
        }
    
    def generate_all(self):
        """Generate all fixture files"""
        print("=" * 70)
        print("TEST FIXTURE GENERATION")
        print("=" * 70)
        print(f"Input: {self.input_dir}")
        print(f"Output: {self.output_dir}")
        print()
        
        # Create output directories
        (self.output_dir / "objects").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "profiles").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "policies").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "infrastructure").mkdir(parents=True, exist_ok=True)
        
        # Generate fixtures by category
        self._generate_category_fixtures("objects", OBJECT_TYPES)
        self._generate_category_fixtures("profiles", PROFILE_TYPES)
        self._generate_category_fixtures("policies", POLICY_TYPES)
        self._generate_category_fixtures("infrastructure", INFRASTRUCTURE_TYPES)
        
        # Generate combined fixture file
        self._generate_combined_fixture()
        
        # Print summary
        self._print_summary()
    
    def _generate_category_fixtures(self, category: str, type_list: List[str]):
        """Generate fixtures for a category"""
        print(f"Generating {category} fixtures...")
        
        category_data = {}
        
        for type_name in type_list:
            type_dir = self.input_dir / type_name
            
            if not type_dir.exists():
                continue
            
            examples = []
            for example_file in sorted(type_dir.glob("*.json")):
                try:
                    with open(example_file, 'r') as f:
                        example_data = json.load(f)
                    examples.append(example_data)
                    self.stats['total_examples'] += 1
                    self.stats['by_type'][type_name] += 1
                except Exception as e:
                    print(f"  ⚠️  Error loading {example_file}: {e}")
            
            if examples:
                # Save individual type fixture
                output_file = self.output_dir / category / f"{type_name}.json"
                with open(output_file, 'w') as f:
                    json.dump(examples, f, indent=2)
                
                category_data[type_name] = examples
                self.stats['by_category'][category] += len(examples)
                print(f"  ✅ {type_name}: {len(examples)} examples → {output_file.name}")
        
        # Save combined category fixture
        if category_data:
            combined_file = self.output_dir / category / f"all_{category}.json"
            with open(combined_file, 'w') as f:
                json.dump(category_data, f, indent=2)
            print(f"  📦 Combined → all_{category}.json")
        
        print()
    
    def _generate_combined_fixture(self):
        """Generate single combined fixture with all examples"""
        print("Generating combined fixture...")
        
        combined = {
            'objects': {},
            'profiles': {},
            'policies': {},
            'infrastructure': {}
        }
        
        # Load all category fixtures
        for category in ['objects', 'profiles', 'policies', 'infrastructure']:
            category_file = self.output_dir / category / f"all_{category}.json"
            if category_file.exists():
                with open(category_file, 'r') as f:
                    combined[category] = json.load(f)
        
        # Save combined fixture
        combined_file = self.output_dir / "all_fixtures.json"
        with open(combined_file, 'w') as f:
            json.dump(combined, f, indent=2)
        
        print(f"  ✅ all_fixtures.json ({self.stats['total_examples']} examples)")
        print()
    
    def _print_summary(self):
        """Print generation summary"""
        print("=" * 70)
        print("FIXTURE GENERATION SUMMARY")
        print("=" * 70)
        print(f"Total examples: {self.stats['total_examples']}")
        print()
        
        print("By Category:")
        for category in sorted(self.stats['by_category'].keys()):
            count = self.stats['by_category'][category]
            print(f"  {category:20s} {count:3d} examples")
        print()
        
        print("By Type (top 10):")
        sorted_types = sorted(self.stats['by_type'].items(), key=lambda x: x[1], reverse=True)
        for type_name, count in sorted_types[:10]:
            print(f"  {type_name:30s} {count:3d} examples")
        
        if len(sorted_types) > 10:
            print(f"  ... and {len(sorted_types) - 10} more types")
        print()
        
        print("Output Structure:")
        print(f"  {self.output_dir}/")
        print(f"    ├── objects/")
        print(f"    │   ├── {len([t for t in OBJECT_TYPES if self.stats['by_type'][t] > 0])} type files")
        print(f"    │   └── all_objects.json")
        print(f"    ├── profiles/")
        print(f"    │   ├── {len([t for t in PROFILE_TYPES if self.stats['by_type'][t] > 0])} type files")
        print(f"    │   └── all_profiles.json")
        print(f"    ├── policies/")
        print(f"    │   ├── {len([t for t in POLICY_TYPES if self.stats['by_type'][t] > 0])} type files")
        print(f"    │   └── all_policies.json")
        print(f"    ├── infrastructure/")
        print(f"    │   ├── {len([t for t in INFRASTRUCTURE_TYPES if self.stats['by_type'][t] > 0])} type files")
        print(f"    │   └── all_infrastructure.json")
        print(f"    └── all_fixtures.json")
        print()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Generate test fixtures from production examples",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--input',
        type=Path,
        default=Path('tests/examples/production/raw'),
        help='Input directory with production examples'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('tests/fixtures'),
        help='Output directory for fixtures'
    )
    
    args = parser.parse_args()
    
    # Validate input
    if not args.input.exists():
        print(f"Error: Input directory not found: {args.input}")
        return 1
    
    # Create generator
    generator = FixtureGenerator(args.input, args.output)
    
    # Generate fixtures
    generator.generate_all()
    
    print("=" * 70)
    print("✅ Fixture generation complete!")
    print()
    print("Next steps:")
    print("  1. Review fixtures in tests/fixtures/")
    print("  2. Generate unit tests from fixtures")
    print("  3. Run pytest to validate tests")
    print("=" * 70)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
