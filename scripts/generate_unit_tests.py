#!/usr/bin/env python3
"""
Auto-Generate Unit Tests from Fixtures.

This script generates comprehensive unit tests from the test fixtures,
creating tests for model loading, validation, serialization, and round-trips.

Generated test files:
    tests/models/test_objects_from_fixtures.py
    tests/models/test_profiles_from_fixtures.py
    tests/models/test_policies_from_fixtures.py
    tests/models/test_infrastructure_from_fixtures.py

Usage:
    python scripts/generate_unit_tests.py
    python scripts/generate_unit_tests.py --verbose
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# Map type names to model classes
TYPE_TO_MODEL = {
    # Objects
    'tag': 'Tag',
    'address_object': 'AddressObject',
    'address_group': 'AddressGroup',
    'service_object': 'ServiceObject',
    'service_group': 'ServiceGroup',
    'application_object': 'ApplicationObject',
    'application_group': 'ApplicationGroup',
    'application_filter': 'ApplicationFilter',
    'schedule': 'Schedule',
    
    # Profiles
    'authentication_profile': 'AuthenticationProfile',
    'decryption_profile': 'DecryptionProfile',
    'url_filtering_profile': 'URLFilteringProfile',
    'antivirus_profile': 'AntivirusProfile',
    'anti_spyware_profile': 'AntiSpywareProfile',
    'vulnerability_profile': 'VulnerabilityProfile',
    'file_blocking_profile': 'FileBlockingProfile',
    'wildfire_profile': 'WildfireProfile',
    'profile_group': 'ProfileGroup',
    'hip_profile': 'HIPProfile',
    'hip_object': 'HIPObject',
    'http_header_profile': 'HTTPHeaderProfile',
    'certificate_profile': 'CertificateProfile',
    'ocsp_responder': 'OCSPResponder',
    'scep_profile': 'SCEPProfile',
    'qos_profile': 'QoSProfile',
    
    # Policies
    'security_rule': 'SecurityRule',
    'decryption_rule': 'DecryptionRule',
    'authentication_rule': 'AuthenticationRule',
    'qos_policy_rule': 'QoSPolicyRule',
    
    # Infrastructure
    'ike_crypto_profile': 'IKECryptoProfile',
    'ipsec_crypto_profile': 'IPsecCryptoProfile',
    'ike_gateway': 'IKEGateway',
    'ipsec_tunnel': 'IPsecTunnel',
    'service_connection': 'ServiceConnection',
    'agent_profile': 'AgentProfile',
    'portal': 'Portal',
    'gateway': 'Gateway',
}


# Map category to import modules
CATEGORY_IMPORTS = {
    'objects': 'config.models.objects',
    'profiles': 'config.models.profiles',
    'policies': 'config.models.policies',
    'infrastructure': 'config.models.infrastructure',
}


class TestGenerator:
    """Generates unit tests from fixtures"""
    
    def __init__(self, fixtures_dir: Path, output_dir: Path, verbose: bool = False):
        """
        Initialize generator.
        
        Args:
            fixtures_dir: Directory with test fixtures
            output_dir: Directory to write test files
            verbose: Enable verbose output
        """
        self.fixtures_dir = fixtures_dir
        self.output_dir = output_dir
        self.verbose = verbose
        self.stats = {
            'total_tests': 0,
            'by_category': defaultdict(int),
            'by_type': defaultdict(int)
        }
    
    def generate_all(self):
        """Generate all test files"""
        print("=" * 70)
        print("UNIT TEST GENERATION FROM FIXTURES")
        print("=" * 70)
        print(f"Fixtures: {self.fixtures_dir}")
        print(f"Output: {self.output_dir}")
        print()
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate conftest.py for fixtures
        self._generate_conftest()
        
        # Generate tests by category
        categories = ['objects', 'profiles', 'policies', 'infrastructure']
        for category in categories:
            combined_file = self.fixtures_dir / category / f"all_{category}.json"
            if combined_file.exists():
                self._generate_category_tests(category, combined_file)
        
        # Print summary
        self._print_summary()
    
    def _generate_conftest(self):
        """Generate conftest.py with fixture loaders"""
        print("Generating conftest.py...")
        
        content = '''"""
Pytest configuration and fixtures for model tests.

This file is auto-generated from production examples.
"""

import pytest
import json
from pathlib import Path


# Fixture directory
FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


def load_fixtures(category: str, type_name: str = None):
    """
    Load fixtures for a category or specific type.
    
    Args:
        category: Category name (objects, profiles, policies, infrastructure)
        type_name: Optional specific type name
    
    Returns:
        List of fixture dictionaries or dict of all types
    """
    if type_name:
        fixture_file = FIXTURE_DIR / category / f"{type_name}.json"
        if fixture_file.exists():
            with open(fixture_file, 'r') as f:
                return json.load(f)
        return []
    else:
        fixture_file = FIXTURE_DIR / category / f"all_{category}.json"
        if fixture_file.exists():
            with open(fixture_file, 'r') as f:
                return json.load(f)
        return {}


# Category fixtures
@pytest.fixture
def all_object_fixtures():
    """Load all object fixtures"""
    return load_fixtures('objects')


@pytest.fixture
def all_profile_fixtures():
    """Load all profile fixtures"""
    return load_fixtures('profiles')


@pytest.fixture
def all_policy_fixtures():
    """Load all policy fixtures"""
    return load_fixtures('policies')


@pytest.fixture
def all_infrastructure_fixtures():
    """Load all infrastructure fixtures"""
    return load_fixtures('infrastructure')


# Individual type fixtures (generated below)
'''
        
        # Add individual type fixtures
        for type_name in TYPE_TO_MODEL.keys():
            clean_name = type_name.replace('_', ' ').title().replace(' ', '')
            content += f'''
@pytest.fixture
def {type_name}_fixtures():
    """Load {type_name} fixtures"""
    # Try each category
    for category in ['objects', 'profiles', 'policies', 'infrastructure']:
        fixtures = load_fixtures(category, '{type_name}')
        if fixtures:
            return fixtures
    return []
'''
        
        output_file = self.output_dir / "conftest.py"
        with open(output_file, 'w') as f:
            f.write(content)
        
        print(f"  ✅ conftest.py")
        print()
    
    def _generate_category_tests(self, category: str, fixture_file: Path):
        """Generate test file for a category"""
        print(f"Generating {category} tests...")
        
        # Load fixtures
        with open(fixture_file, 'r') as f:
            fixtures = json.load(f)
        
        if not fixtures:
            print(f"  ⚠️  No fixtures found")
            return
        
        # Generate test content
        content = self._generate_test_content(category, fixtures)
        
        # Write test file
        output_file = self.output_dir / f"test_{category}_from_fixtures.py"
        with open(output_file, 'w') as f:
            f.write(content)
        
        # Count tests
        test_count = len(fixtures) * 4  # 4 tests per type (load, validate, serialize, round-trip)
        self.stats['total_tests'] += test_count
        self.stats['by_category'][category] = test_count
        
        for type_name, examples in fixtures.items():
            self.stats['by_type'][type_name] = len(examples) * 4
        
        print(f"  ✅ test_{category}_from_fixtures.py ({test_count} tests)")
        print()
    
    def _generate_test_content(self, category: str, fixtures: Dict[str, List[Dict]]) -> str:
        """Generate test file content"""
        
        # Header
        content = f'''"""
Unit tests for {category} models using production fixtures.

This file is auto-generated from production examples.
Tests cover:
- Model instantiation from real configs
- Validation
- Serialization
- Round-trip (load -> serialize -> load)
"""

import pytest
from {CATEGORY_IMPORTS[category]} import *


class Test{category.title()}FromFixtures:
    """{category.title()} model tests using production fixtures"""
    
'''
        
        # Generate tests for each type
        for type_name, examples in sorted(fixtures.items()):
            if type_name not in TYPE_TO_MODEL:
                continue
            
            model_class = TYPE_TO_MODEL[type_name]
            example_count = len(examples)
            
            content += f'''
    # ========== {type_name.upper()} Tests ==========
    
    def test_{type_name}_load_all(self, {type_name}_fixtures):
        """Test all {type_name} examples can be loaded from fixtures"""
        assert len({type_name}_fixtures) == {example_count}, "Expected {example_count} fixtures"
        
        for i, fixture in enumerate({type_name}_fixtures):
            # Load model
            obj = {model_class}.from_dict(fixture)
            
            # Basic assertions
            assert obj is not None, f"Failed to load fixture {{i}}"
            assert obj.name, f"Fixture {{i}} has no name"
            assert hasattr(obj, 'folder') or hasattr(obj, 'snippet'), f"Fixture {{i}} missing location"
    
    def test_{type_name}_validate_all(self, {type_name}_fixtures):
        """Test all {type_name} examples pass validation"""
        for i, fixture in enumerate({type_name}_fixtures):
            obj = {model_class}.from_dict(fixture)
            
            # Should not raise
            try:
                obj.validate()
            except Exception as e:
                pytest.fail(f"Fixture {{i}} validation failed: {{e}}")
    
    def test_{type_name}_serialize_all(self, {type_name}_fixtures):
        """Test all {type_name} examples can be serialized"""
        for i, fixture in enumerate({type_name}_fixtures):
            obj = {model_class}.from_dict(fixture)
            
            # Serialize
            data = obj.to_dict()
            
            # Basic checks
            assert isinstance(data, dict), f"Fixture {{i}} serialization not a dict"
            assert 'name' in data, f"Fixture {{i}} serialization missing name"
            assert data['name'] == fixture['name'], f"Fixture {{i}} name mismatch"
    
    def test_{type_name}_roundtrip_all(self, {type_name}_fixtures):
        """Test all {type_name} examples survive round-trip serialization"""
        for i, fixture in enumerate({type_name}_fixtures):
            # Load
            obj1 = {model_class}.from_dict(fixture)
            
            # Serialize
            data = obj1.to_dict()
            
            # Load again
            obj2 = {model_class}.from_dict(data)
            
            # Compare key fields
            assert obj1.name == obj2.name, f"Fixture {{i}} name mismatch after round-trip"
            if hasattr(obj1, 'folder'):
                assert obj1.folder == obj2.folder, f"Fixture {{i}} folder mismatch"
            if hasattr(obj1, 'snippet'):
                assert obj1.snippet == obj2.snippet, f"Fixture {{i}} snippet mismatch"
'''
        
        return content
    
    def _print_summary(self):
        """Print generation summary"""
        print("=" * 70)
        print("TEST GENERATION SUMMARY")
        print("=" * 70)
        print(f"Total tests generated: {self.stats['total_tests']}")
        print()
        
        print("By Category:")
        for category in sorted(self.stats['by_category'].keys()):
            count = self.stats['by_category'][category]
            print(f"  {category:20s} {count:3d} tests")
        print()
        
        print("By Type (top 15):")
        sorted_types = sorted(self.stats['by_type'].items(), key=lambda x: x[1], reverse=True)
        for type_name, count in sorted_types[:15]:
            print(f"  {type_name:30s} {count:3d} tests")
        
        if len(sorted_types) > 15:
            print(f"  ... and {len(sorted_types) - 15} more types")
        print()
        
        print("Generated Files:")
        print(f"  {self.output_dir}/")
        print(f"    ├── conftest.py (fixture loaders)")
        print(f"    ├── test_objects_from_fixtures.py")
        print(f"    ├── test_profiles_from_fixtures.py")
        print(f"    ├── test_policies_from_fixtures.py")
        print(f"    └── test_infrastructure_from_fixtures.py")
        print()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Auto-generate unit tests from fixtures",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--fixtures',
        type=Path,
        default=Path('tests/fixtures'),
        help='Fixtures directory'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('tests/models'),
        help='Output directory for tests'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Validate fixtures directory
    if not args.fixtures.exists():
        print(f"Error: Fixtures directory not found: {args.fixtures}")
        return 1
    
    # Create generator
    generator = TestGenerator(args.fixtures, args.output, args.verbose)
    
    # Generate tests
    generator.generate_all()
    
    print("=" * 70)
    print("✅ Test generation complete!")
    print()
    print("Next steps:")
    print("  1. Review generated tests in tests/models/")
    print("  2. Run tests: pytest tests/models/test_*_from_fixtures.py -v")
    print("  3. Check coverage: pytest --cov=config.models tests/models/")
    print("=" * 70)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
