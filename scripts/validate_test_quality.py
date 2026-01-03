#!/usr/bin/env python3
"""
Test Quality Validator.

Validates that:
1. All production examples have corresponding test fixtures
2. All fixtures are used in tests
3. Tests actually verify model behavior (not just pass/fail)
4. Coverage includes key model features
5. Edge cases are represented in fixtures

Usage:
    python scripts/validate_test_quality.py
    python scripts/validate_test_quality.py --verbose
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Any, Tuple
from collections import defaultdict
import ast

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.models.factory import ConfigItemFactory


class TestQualityValidator:
    """Validates test quality and completeness"""
    
    def __init__(self, 
                 examples_dir: Path,
                 fixtures_dir: Path, 
                 tests_dir: Path,
                 verbose: bool = False):
        """
        Initialize validator.
        
        Args:
            examples_dir: Directory with raw production examples
            fixtures_dir: Directory with test fixtures
            tests_dir: Directory with test files
            verbose: Enable verbose output
        """
        self.examples_dir = examples_dir
        self.fixtures_dir = fixtures_dir
        self.tests_dir = tests_dir
        self.verbose = verbose
        self.issues = []
        self.warnings = []
        self.stats = {
            'examples': 0,
            'fixtures': 0,
            'tests': 0,
            'assertions': 0,
            'edge_cases': 0
        }
    
    def validate_all(self) -> bool:
        """
        Run all validation checks.
        
        Returns:
            True if all validations pass
        """
        print("=" * 70)
        print("TEST QUALITY VALIDATION")
        print("=" * 70)
        print(f"Examples: {self.examples_dir}")
        print(f"Fixtures: {self.fixtures_dir}")
        print(f"Tests: {self.tests_dir}")
        print()
        
        # Run validations
        print("Running validation checks...")
        print()
        
        self._validate_example_to_fixture_mapping()
        self._validate_fixture_to_test_mapping()
        self._validate_test_assertions()
        self._validate_edge_cases()
        self._validate_model_features()
        self._validate_fixture_quality()
        
        # Print results
        self._print_results()
        
        return len(self.issues) == 0
    
    def _validate_example_to_fixture_mapping(self):
        """Validate all examples are captured in fixtures"""
        print("✓ Checking example → fixture mapping...")
        
        # Count raw examples
        example_types = defaultdict(int)
        for type_dir in self.examples_dir.glob('*'):
            if type_dir.is_dir():
                count = len(list(type_dir.glob('*.json')))
                if count > 0:
                    example_types[type_dir.name] = count
                    self.stats['examples'] += count
        
        # Count fixtures
        fixture_types = defaultdict(int)
        for category_dir in self.fixtures_dir.glob('*'):
            if category_dir.is_dir():
                for fixture_file in category_dir.glob('*.json'):
                    if fixture_file.name.startswith('all_'):
                        continue
                    type_name = fixture_file.stem
                    with open(fixture_file) as f:
                        fixtures = json.load(f)
                        fixture_types[type_name] = len(fixtures)
                        self.stats['fixtures'] += len(fixtures)
        
        # Compare
        for type_name, example_count in example_types.items():
            fixture_count = fixture_types.get(type_name, 0)
            if fixture_count < example_count:
                self.issues.append(
                    f"Type '{type_name}': {example_count} examples but only "
                    f"{fixture_count} fixtures"
                )
            elif fixture_count > example_count:
                self.warnings.append(
                    f"Type '{type_name}': {fixture_count} fixtures but only "
                    f"{example_count} examples (expected)"
                )
        
        # Check for fixture types with no examples
        for type_name, fixture_count in fixture_types.items():
            if type_name not in example_types and fixture_count > 0:
                self.warnings.append(
                    f"Type '{type_name}': {fixture_count} fixtures but no raw examples"
                )
        
        if self.verbose:
            print(f"  Examples: {self.stats['examples']}")
            print(f"  Fixtures: {self.stats['fixtures']}")
    
    def _validate_fixture_to_test_mapping(self):
        """Validate all fixtures are tested"""
        print("✓ Checking fixture → test mapping...")
        
        # Get all fixture types
        fixture_types = set()
        for category_dir in self.fixtures_dir.glob('*'):
            if category_dir.is_dir():
                for fixture_file in category_dir.glob('*.json'):
                    if not fixture_file.name.startswith('all_'):
                        fixture_types.add(fixture_file.stem)
        
        # Get all tested types
        tested_types = set()
        for test_file in self.tests_dir.glob('test_*_from_fixtures.py'):
            with open(test_file) as f:
                content = f.read()
                # Look for test method names like test_address_object_*
                import re
                methods = re.findall(r'def test_(\w+)_(?:load|validate|serialize|roundtrip)', content)
                tested_types.update(methods)
                
                # Count test methods
                test_count = len(re.findall(r'def test_\w+', content))
                self.stats['tests'] += test_count
        
        # Compare
        for fixture_type in fixture_types:
            if fixture_type not in tested_types:
                self.issues.append(
                    f"Fixture type '{fixture_type}' has no tests"
                )
        
        for tested_type in tested_types:
            if tested_type not in fixture_types:
                self.warnings.append(
                    f"Test type '{tested_type}' has no fixtures"
                )
        
        if self.verbose:
            print(f"  Fixture types: {len(fixture_types)}")
            print(f"  Tested types: {len(tested_types)}")
            print(f"  Test methods: {self.stats['tests']}")
    
    def _validate_test_assertions(self):
        """Validate tests have meaningful assertions"""
        print("✓ Checking test assertions...")
        
        weak_tests = []
        for test_file in self.tests_dir.glob('test_*_from_fixtures.py'):
            with open(test_file) as f:
                content = f.read()
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                        # Count assertions
                        assertions = [n for n in ast.walk(node) 
                                     if isinstance(n, ast.Assert) or
                                     (isinstance(n, ast.Expr) and 
                                      isinstance(n.value, ast.Call) and
                                      isinstance(n.value.func, ast.Attribute) and
                                      n.value.func.attr in ['fail', 'raises'])]
                        
                        self.stats['assertions'] += len(assertions)
                        
                        if len(assertions) < 2:
                            weak_tests.append(f"{test_file.name}::{node.name}")
        
        if weak_tests:
            self.warnings.append(
                f"{len(weak_tests)} tests have < 2 assertions (may be too simple)"
            )
            if self.verbose:
                for test in weak_tests[:5]:
                    print(f"    - {test}")
                if len(weak_tests) > 5:
                    print(f"    ... and {len(weak_tests) - 5} more")
        
        if self.verbose:
            print(f"  Total assertions: {self.stats['assertions']}")
            print(f"  Avg per test: {self.stats['assertions'] / max(self.stats['tests'], 1):.1f}")
    
    def _validate_edge_cases(self):
        """Validate edge cases are represented"""
        print("✓ Checking edge case coverage...")
        
        edge_cases_found = {
            'empty_lists': 0,
            'max_length_strings': 0,
            'special_characters': 0,
            'optional_fields': 0,
            'multiple_containers': 0
        }
        
        # Check fixtures for edge cases
        for category_dir in self.fixtures_dir.glob('*'):
            if category_dir.is_dir():
                for fixture_file in category_dir.glob('*.json'):
                    if fixture_file.name.startswith('all_'):
                        continue
                    
                    with open(fixture_file) as f:
                        fixtures = json.load(f)
                        
                        for fixture in fixtures:
                            # Check for empty lists
                            if self._has_empty_lists(fixture):
                                edge_cases_found['empty_lists'] += 1
                            
                            # Check for long strings
                            if self._has_long_strings(fixture):
                                edge_cases_found['max_length_strings'] += 1
                            
                            # Check for special characters
                            if self._has_special_chars(fixture):
                                edge_cases_found['special_characters'] += 1
                            
                            # Check for optional fields
                            if self._has_description(fixture):
                                edge_cases_found['optional_fields'] += 1
                            
                            # Check for multiple container types
                            containers = sum([
                                1 for k in ['folder', 'snippet', 'device']
                                if k in fixture and fixture[k]
                            ])
                            if containers > 1:
                                edge_cases_found['multiple_containers'] += 1
        
        self.stats['edge_cases'] = sum(edge_cases_found.values())
        
        # Report findings
        if edge_cases_found['multiple_containers'] > 0:
            self.warnings.append(
                f"Found {edge_cases_found['multiple_containers']} fixtures with multiple "
                f"containers (folder+snippet) - these are valuable edge cases!"
            )
        
        if self.verbose:
            print(f"  Edge cases found:")
            for case_type, count in edge_cases_found.items():
                if count > 0:
                    print(f"    - {case_type}: {count}")
    
    def _validate_model_features(self):
        """Validate fixtures cover key model features"""
        print("✓ Checking model feature coverage...")
        
        feature_coverage = defaultdict(set)
        
        # Analyze fixtures
        for category_dir in self.fixtures_dir.glob('*'):
            if category_dir.is_dir():
                for fixture_file in category_dir.glob('*.json'):
                    if fixture_file.name.startswith('all_'):
                        continue
                    
                    type_name = fixture_file.stem
                    
                    with open(fixture_file) as f:
                        fixtures = json.load(f)
                        
                        for fixture in fixtures:
                            # Track which features are used
                            if 'folder' in fixture:
                                feature_coverage[type_name].add('folder')
                            if 'snippet' in fixture:
                                feature_coverage[type_name].add('snippet')
                            if 'description' in fixture:
                                feature_coverage[type_name].add('description')
                            if 'tag' in fixture:
                                feature_coverage[type_name].add('tags')
        
        # Check for types with limited coverage
        for type_name, features in feature_coverage.items():
            if 'folder' not in features and 'snippet' not in features:
                self.issues.append(
                    f"Type '{type_name}': No container examples (folder/snippet)"
                )
        
        if self.verbose:
            print(f"  Types analyzed: {len(feature_coverage)}")
    
    def _validate_fixture_quality(self):
        """Validate fixture data quality"""
        print("✓ Checking fixture quality...")
        
        quality_issues = []
        
        for category_dir in self.fixtures_dir.glob('*'):
            if category_dir.is_dir():
                for fixture_file in category_dir.glob('*.json'):
                    if fixture_file.name.startswith('all_'):
                        continue
                    
                    type_name = fixture_file.stem
                    
                    try:
                        with open(fixture_file) as f:
                            fixtures = json.load(f)
                        
                        # Check each fixture can be loaded by model
                        for i, fixture in enumerate(fixtures):
                            try:
                                # Try to instantiate with factory
                                obj = ConfigItemFactory.create_from_dict(type_name, fixture)
                                
                                # Try to validate
                                obj.validate()
                                
                                # Try to serialize
                                data = obj.to_dict()
                                
                                # Basic checks
                                if 'name' not in data:
                                    quality_issues.append(
                                        f"{type_name}[{i}]: Missing 'name' in serialized output"
                                    )
                                
                            except Exception as e:
                                quality_issues.append(
                                    f"{type_name}[{i}]: Failed to load/validate: {e}"
                                )
                    
                    except Exception as e:
                        self.issues.append(
                            f"Failed to load fixture file {fixture_file.name}: {e}"
                        )
        
        if quality_issues:
            self.issues.extend(quality_issues[:10])  # Limit to first 10
            if len(quality_issues) > 10:
                self.warnings.append(
                    f"...and {len(quality_issues) - 10} more quality issues"
                )
    
    def _has_empty_lists(self, data: Dict) -> bool:
        """Check if data contains empty lists"""
        if isinstance(data, dict):
            return any(
                v == [] or self._has_empty_lists(v)
                for v in data.values()
            )
        elif isinstance(data, list):
            return len(data) == 0 or any(self._has_empty_lists(item) for item in data)
        return False
    
    def _has_long_strings(self, data: Dict, threshold: int = 100) -> bool:
        """Check if data contains long strings"""
        if isinstance(data, dict):
            return any(self._has_long_strings(v, threshold) for v in data.values())
        elif isinstance(data, list):
            return any(self._has_long_strings(item, threshold) for item in data)
        elif isinstance(data, str):
            return len(data) > threshold
        return False
    
    def _has_special_chars(self, data: Dict) -> bool:
        """Check if data contains special characters"""
        special = set('!@#$%^&*(){}[]|\\:;"\'<>,.?/~`')
        if isinstance(data, dict):
            return any(self._has_special_chars(v) for v in data.values())
        elif isinstance(data, list):
            return any(self._has_special_chars(item) for item in data)
        elif isinstance(data, str):
            return any(c in special for c in data)
        return False
    
    def _has_description(self, data: Dict) -> bool:
        """Check if data has a description field"""
        return isinstance(data, dict) and 'description' in data and data['description']
    
    def _print_results(self):
        """Print validation results"""
        print()
        print("=" * 70)
        print("VALIDATION RESULTS")
        print("=" * 70)
        
        # Statistics
        print()
        print("📊 Statistics:")
        print(f"  Raw examples:     {self.stats['examples']}")
        print(f"  Test fixtures:    {self.stats['fixtures']}")
        print(f"  Test methods:     {self.stats['tests']}")
        print(f"  Assertions:       {self.stats['assertions']}")
        print(f"  Edge cases:       {self.stats['edge_cases']}")
        
        if self.stats['tests'] > 0:
            print(f"  Assertions/test:  {self.stats['assertions'] / self.stats['tests']:.1f}")
        
        # Issues
        print()
        if self.issues:
            print(f"❌ Issues Found: {len(self.issues)}")
            print()
            for issue in self.issues:
                print(f"  ❌ {issue}")
        else:
            print("✅ No Critical Issues Found!")
        
        # Warnings
        print()
        if self.warnings:
            print(f"⚠️  Warnings: {len(self.warnings)}")
            print()
            for warning in self.warnings:
                print(f"  ⚠️  {warning}")
        else:
            print("✅ No Warnings!")
        
        # Overall assessment
        print()
        print("=" * 70)
        if not self.issues and len(self.warnings) <= 5:
            print("✅ TEST QUALITY: EXCELLENT")
            print()
            print("Your test suite is comprehensive and well-structured!")
        elif not self.issues:
            print("✅ TEST QUALITY: GOOD")
            print()
            print("Minor warnings but no critical issues.")
        else:
            print("⚠️  TEST QUALITY: NEEDS ATTENTION")
            print()
            print("Please address the issues above.")
        print("=" * 70)
        print()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Validate test quality and completeness",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--examples',
        type=Path,
        default=Path('tests/examples/production/raw'),
        help='Raw examples directory'
    )
    parser.add_argument(
        '--fixtures',
        type=Path,
        default=Path('tests/fixtures'),
        help='Fixtures directory'
    )
    parser.add_argument(
        '--tests',
        type=Path,
        default=Path('tests/models'),
        help='Tests directory'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Validate directories exist
    for dir_path, name in [
        (args.examples, 'Examples'),
        (args.fixtures, 'Fixtures'),
        (args.tests, 'Tests')
    ]:
        if not dir_path.exists():
            print(f"Error: {name} directory not found: {dir_path}")
            return 1
    
    # Create validator
    validator = TestQualityValidator(
        args.examples,
        args.fixtures,
        args.tests,
        args.verbose
    )
    
    # Run validation
    success = validator.validate_all()
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
