#!/usr/bin/env python3
"""
Model Validation Script - Test all production examples against models.

This script loads all captured production examples and attempts to instantiate
model classes from them. It reports successes, failures, missing properties,
and validation issues.

Usage:
    python scripts/validate_models_against_examples.py
    python scripts/validate_models_against_examples.py --verbose
    python scripts/validate_models_against_examples.py --type schedule
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict
import traceback

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.models.factory import ConfigItemFactory
from config.models.objects import *
from config.models.profiles import *
from config.models.policies import *
from config.models.infrastructure import *


# Map type names to model classes
TYPE_TO_MODEL = {
    # Objects
    'tag': Tag,
    'address_object': AddressObject,
    'address_group': AddressGroup,
    'service_object': ServiceObject,
    'service_group': ServiceGroup,
    'application_object': ApplicationObject,
    'application_group': ApplicationGroup,
    'application_filter': ApplicationFilter,
    'schedule': Schedule,
    
    # Profiles
    'authentication_profile': AuthenticationProfile,
    'decryption_profile': DecryptionProfile,
    'url_filtering_profile': URLFilteringProfile,
    'antivirus_profile': AntivirusProfile,
    'anti_spyware_profile': AntiSpywareProfile,
    'vulnerability_profile': VulnerabilityProfile,
    'file_blocking_profile': FileBlockingProfile,
    'wildfire_profile': WildfireProfile,
    'profile_group': ProfileGroup,
    'hip_profile': HIPProfile,
    'hip_object': HIPObject,
    'http_header_profile': HTTPHeaderProfile,
    'certificate_profile': CertificateProfile,
    'ocsp_responder': OCSPResponder,
    'scep_profile': SCEPProfile,
    'qos_profile': QoSProfile,
    
    # Policies
    'security_rule': SecurityRule,
    'decryption_rule': DecryptionRule,
    'authentication_rule': AuthenticationRule,
    'qos_policy_rule': QoSPolicyRule,
    
    # Infrastructure
    'ike_crypto_profile': IKECryptoProfile,
    'ipsec_crypto_profile': IPsecCryptoProfile,
    'ike_gateway': IKEGateway,
    'ipsec_tunnel': IPsecTunnel,
    'service_connection': ServiceConnection,
    'agent_profile': AgentProfile,
    'portal': Portal,
    'gateway': Gateway,
}


class ModelValidator:
    """Validates production examples against model classes"""
    
    def __init__(self, examples_dir: Path, verbose: bool = False):
        """
        Initialize validator.
        
        Args:
            examples_dir: Directory containing production examples
            verbose: Enable verbose output
        """
        self.examples_dir = examples_dir
        self.verbose = verbose
        self.results = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'by_type': defaultdict(lambda: {
                'total': 0,
                'success': 0,
                'failed': 0,
                'errors': [],
                'missing_properties': set(),
                'extra_properties': set(),
                'validation_errors': []
            })
        }
    
    def validate_all(self, filter_type: str = None) -> Dict[str, Any]:
        """
        Validate all examples.
        
        Args:
            filter_type: Optional type filter (e.g., 'schedule')
        
        Returns:
            Validation results dictionary
        """
        print("=" * 70)
        print("MODEL VALIDATION - Production Examples")
        print("=" * 70)
        print(f"Examples directory: {self.examples_dir}")
        if filter_type:
            print(f"Filter: {filter_type}")
        print()
        
        # Iterate through type directories
        for type_dir in sorted(self.examples_dir.iterdir()):
            if not type_dir.is_dir():
                continue
            
            type_name = type_dir.name
            
            # Skip if filtering and doesn't match
            if filter_type and type_name != filter_type:
                continue
            
            # Check if we have a model for this type
            if type_name not in TYPE_TO_MODEL:
                if self.verbose:
                    print(f"⚠️  {type_name}: No model class defined (skipping)")
                continue
            
            model_class = TYPE_TO_MODEL[type_name]
            
            # Validate examples for this type
            self._validate_type(type_name, type_dir, model_class)
        
        return self.results
    
    def _validate_type(self, type_name: str, type_dir: Path, model_class: type):
        """Validate all examples for a specific type"""
        print(f"Validating {type_name}...", end=" ", flush=True)
        
        example_files = list(type_dir.glob("*.json"))
        
        if not example_files:
            print("⚠️  No examples found")
            return
        
        type_results = self.results['by_type'][type_name]
        
        for example_file in example_files:
            self.results['total'] += 1
            type_results['total'] += 1
            
            try:
                # Load example
                with open(example_file, 'r') as f:
                    example_data = json.load(f)
                
                # Try to instantiate model
                obj = model_class.from_dict(example_data)
                
                # Try to validate
                obj.validate()
                
                # Try round-trip
                obj_dict = obj.to_dict()
                
                # Check for missing properties (in prod but not in model)
                prod_keys = set(example_data.keys())
                model_keys = set(obj_dict.keys())
                missing = prod_keys - model_keys
                extra = model_keys - prod_keys
                
                if missing:
                    type_results['missing_properties'].update(missing)
                if extra:
                    type_results['extra_properties'].update(extra)
                
                # Success!
                self.results['success'] += 1
                type_results['success'] += 1
                
                if self.verbose:
                    print(f"  ✅ {example_file.name}")
                    if missing:
                        print(f"     Missing in model: {missing}")
                    if extra:
                        print(f"     Extra in model: {extra}")
                
            except Exception as e:
                # Failure
                self.results['failed'] += 1
                type_results['failed'] += 1
                
                error_info = {
                    'file': example_file.name,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'traceback': traceback.format_exc() if self.verbose else None
                }
                
                type_results['errors'].append(error_info)
                
                if self.verbose:
                    print(f"  ❌ {example_file.name}")
                    print(f"     Error: {e}")
                    if "validation" in str(e).lower():
                        type_results['validation_errors'].append(error_info)
        
        # Print summary for this type
        success_rate = (type_results['success'] / type_results['total'] * 100) if type_results['total'] > 0 else 0
        
        if type_results['failed'] == 0:
            print(f"✅ {type_results['success']}/{type_results['total']} (100%)")
        else:
            print(f"⚠️  {type_results['success']}/{type_results['total']} ({success_rate:.1f}%)")
    
    def print_summary(self):
        """Print validation summary"""
        print()
        print("=" * 70)
        print("VALIDATION SUMMARY")
        print("=" * 70)
        
        # Overall stats
        success_rate = (self.results['success'] / self.results['total'] * 100) if self.results['total'] > 0 else 0
        
        print(f"Total examples: {self.results['total']}")
        print(f"Successfully loaded: {self.results['success']} ({success_rate:.1f}%)")
        print(f"Failed to load: {self.results['failed']} ({100-success_rate:.1f}%)")
        print()
        
        # By type
        print("Results by Type:")
        print("-" * 70)
        
        for type_name in sorted(self.results['by_type'].keys()):
            type_results = self.results['by_type'][type_name]
            success = type_results['success']
            total = type_results['total']
            failed = type_results['failed']
            success_rate = (success / total * 100) if total > 0 else 0
            
            status = "✅" if failed == 0 else "⚠️" if success_rate >= 80 else "❌"
            
            print(f"  {status} {type_name:30s} {success:3d}/{total:3d} ({success_rate:5.1f}%)")
            
            # Show missing properties
            if type_results['missing_properties']:
                print(f"      Missing properties: {', '.join(sorted(type_results['missing_properties']))}")
            
            # Show validation errors count
            if type_results['validation_errors']:
                print(f"      Validation errors: {len(type_results['validation_errors'])}")
        
        print()
        
        # Critical issues
        critical_types = [
            type_name for type_name, results in self.results['by_type'].items()
            if results['failed'] > 0 and results['total'] >= 5
        ]
        
        if critical_types:
            print("Critical Issues (types with 5+ examples and failures):")
            print("-" * 70)
            for type_name in critical_types:
                type_results = self.results['by_type'][type_name]
                print(f"  ❌ {type_name}: {type_results['failed']} failures")
                
                # Show first 3 errors
                for error in type_results['errors'][:3]:
                    print(f"      - {error['file']}: {error['error_type']}: {error['error']}")
                
                if len(type_results['errors']) > 3:
                    print(f"      ... and {len(type_results['errors']) - 3} more errors")
            print()
        
        # Missing properties summary
        types_with_missing = [
            (type_name, results) for type_name, results in self.results['by_type'].items()
            if results['missing_properties']
        ]
        
        if types_with_missing:
            print("Missing Properties (in production but not in models):")
            print("-" * 70)
            for type_name, results in types_with_missing:
                print(f"  {type_name}:")
                for prop in sorted(results['missing_properties']):
                    print(f"    - {prop}")
            print()
    
    def save_report(self, output_file: Path):
        """Save detailed report to file"""
        print(f"Saving detailed report to: {output_file}")
        
        report = {
            'summary': {
                'total': self.results['total'],
                'success': self.results['success'],
                'failed': self.results['failed'],
                'success_rate': (self.results['success'] / self.results['total'] * 100) if self.results['total'] > 0 else 0
            },
            'by_type': {}
        }
        
        # Convert defaultdict and sets to regular dict/lists for JSON
        for type_name, type_results in self.results['by_type'].items():
            report['by_type'][type_name] = {
                'total': type_results['total'],
                'success': type_results['success'],
                'failed': type_results['failed'],
                'success_rate': (type_results['success'] / type_results['total'] * 100) if type_results['total'] > 0 else 0,
                'missing_properties': sorted(list(type_results['missing_properties'])),
                'extra_properties': sorted(list(type_results['extra_properties'])),
                'validation_errors': type_results['validation_errors'],
                'errors': type_results['errors']
            }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"✅ Report saved: {output_file}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Validate production examples against model classes",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--input',
        type=Path,
        default=Path('tests/examples/production/raw'),
        help='Input directory with production examples (default: tests/examples/production/raw)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('tests/examples/production/validation_report.json'),
        help='Output file for detailed report (default: tests/examples/production/validation_report.json)'
    )
    parser.add_argument(
        '--type',
        help='Filter by specific type (e.g., schedule)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Validate input directory
    if not args.input.exists():
        print(f"Error: Input directory not found: {args.input}")
        return 1
    
    # Create validator
    validator = ModelValidator(args.input, args.verbose)
    
    # Run validation
    results = validator.validate_all(filter_type=args.type)
    
    # Print summary
    validator.print_summary()
    
    # Save report
    args.output.parent.mkdir(parents=True, exist_ok=True)
    validator.save_report(args.output)
    
    print()
    print("=" * 70)
    
    # Exit code based on success rate
    success_rate = (results['success'] / results['total'] * 100) if results['total'] > 0 else 0
    
    if success_rate >= 95:
        print("✅ EXCELLENT: 95%+ success rate!")
        return 0
    elif success_rate >= 80:
        print("⚠️  GOOD: 80%+ success rate, but needs improvement")
        return 0
    else:
        print("❌ NEEDS WORK: <80% success rate")
        return 1


if __name__ == '__main__':
    sys.exit(main())
