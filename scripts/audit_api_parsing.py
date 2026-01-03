#!/usr/bin/env python3
"""
API Client Parsing Audit.

Tests the API client's parsing logic with real production fixtures to:
1. Simulate API responses
2. Test parsing with both factory and direct methods
3. Compare input vs output for data integrity
4. Identify parsing failures, data loss, or transformations

Usage:
    python scripts/audit_api_parsing.py
    python scripts/audit_api_parsing.py --verbose
    python scripts/audit_api_parsing.py --type address_object
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict
from datetime import datetime
import copy

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.models.factory import ConfigItemFactory


class APIParsingAuditor:
    """Audits API client parsing with production fixtures"""
    
    def __init__(self, fixtures_dir: Path, verbose: bool = False):
        """
        Initialize auditor.
        
        Args:
            fixtures_dir: Directory with test fixtures
            verbose: Enable verbose output
        """
        self.fixtures_dir = fixtures_dir
        self.verbose = verbose
        self.results = {
            'total_fixtures': 0,
            'successful_parses': 0,
            'failed_parses': 0,
            'by_type': defaultdict(lambda: {
                'total': 0,
                'success': 0,
                'failures': []
            })
        }
        self.issues = {
            'parsing_failures': [],
            'missing_fields': defaultdict(set),
            'extra_fields': defaultdict(set),
            'type_mismatches': [],
            'value_changes': []
        }
    
    def audit_all(self, filter_type: Optional[str] = None) -> bool:
        """
        Audit all fixtures.
        
        Args:
            filter_type: Optional type to filter by
        
        Returns:
            True if all pass
        """
        print("=" * 70)
        print("API CLIENT PARSING AUDIT")
        print("=" * 70)
        print(f"Fixtures: {self.fixtures_dir}")
        if filter_type:
            print(f"Filter: {filter_type} only")
        print()
        
        # Process fixtures by category
        for category_dir in sorted(self.fixtures_dir.glob('*')):
            if not category_dir.is_dir():
                continue
            
            print(f"\n{'=' * 70}")
            print(f"Testing {category_dir.name.upper()}")
            print(f"{'=' * 70}\n")
            
            for fixture_file in sorted(category_dir.glob('*.json')):
                if fixture_file.name.startswith('all_'):
                    continue
                
                type_name = fixture_file.stem
                
                # Apply filter
                if filter_type and type_name != filter_type:
                    continue
                
                self._audit_type(type_name, fixture_file)
        
        # Print results
        self._print_summary()
        
        return self.results['failed_parses'] == 0
    
    def _audit_type(self, type_name: str, fixture_file: Path):
        """Audit a specific type"""
        print(f"Testing {type_name}...", end=" ")
        
        try:
            with open(fixture_file) as f:
                fixtures = json.load(f)
            
            if not fixtures:
                print("⚠️  No fixtures")
                return
            
            # Test each fixture
            successes = 0
            for i, fixture in enumerate(fixtures):
                self.results['total_fixtures'] += 1
                self.results['by_type'][type_name]['total'] += 1
                
                # Test parsing
                success, issues = self._test_parse_fixture(type_name, fixture, i)
                
                if success:
                    successes += 1
                    self.results['successful_parses'] += 1
                    self.results['by_type'][type_name]['success'] += 1
                else:
                    self.results['failed_parses'] += 1
                    self.results['by_type'][type_name]['failures'].append({
                        'index': i,
                        'name': fixture.get('name', 'unknown'),
                        'issues': issues
                    })
            
            # Print result
            total = len(fixtures)
            if successes == total:
                print(f"✅ {successes}/{total}")
            else:
                print(f"❌ {successes}/{total} (see details below)")
                
                # Show failures if not too many
                if self.verbose or len(fixtures) - successes <= 5:
                    for failure in self.results['by_type'][type_name]['failures']:
                        print(f"  ❌ [{failure['index']}] {failure['name']}: {failure['issues']}")
        
        except Exception as e:
            print(f"❌ Error: {e}")
            self.results['by_type'][type_name]['failures'].append({
                'index': -1,
                'name': 'file_load_error',
                'issues': str(e)
            })
    
    def _test_parse_fixture(self, type_name: str, fixture: Dict, index: int) -> Tuple[bool, List[str]]:
        """
        Test parsing a single fixture.
        
        Returns:
            (success, list_of_issues)
        """
        issues = []
        
        try:
            # 1. Simulate API response format
            # Most SCM API responses have data in a 'data' array
            api_response = {'data': [copy.deepcopy(fixture)]}
            raw_item = api_response['data'][0]
            
            # 2. Test parsing with factory (how get_items works with use_factory=True)
            try:
                parsed_obj = ConfigItemFactory.create_from_dict(type_name, raw_item)
            except Exception as e:
                issues.append(f"Factory parsing failed: {e}")
                return False, issues
            
            # 3. Validate the parsed object
            try:
                parsed_obj.validate()
            except Exception as e:
                issues.append(f"Validation failed: {e}")
                # Don't return False - validation issues are warnings not parsing failures
            
            # 4. Test serialization round-trip
            try:
                serialized = parsed_obj.to_dict()
            except Exception as e:
                issues.append(f"Serialization failed: {e}")
                return False, issues
            
            # 5. Compare fields (input vs output)
            field_issues = self._compare_fields(type_name, fixture, serialized, index)
            if field_issues:
                issues.extend(field_issues)
            
            # Success if no critical issues
            return len(issues) == 0, issues
        
        except Exception as e:
            issues.append(f"Unexpected error: {e}")
            return False, issues
    
    def _compare_fields(self, type_name: str, original: Dict, parsed: Dict, index: int) -> List[str]:
        """Compare original fixture with parsed/serialized output"""
        issues = []
        
        # Get field sets
        orig_fields = set(original.keys())
        parsed_fields = set(parsed.keys())
        
        # Check for missing fields
        missing = orig_fields - parsed_fields
        if missing:
            for field in missing:
                self.issues['missing_fields'][type_name].add(field)
                if self.verbose:
                    issues.append(f"Missing field: {field}")
        
        # Check for extra fields
        extra = parsed_fields - orig_fields
        if extra:
            for field in extra:
                # Ignore 'id' as we added it in models
                if field != 'id':
                    self.issues['extra_fields'][type_name].add(field)
                    if self.verbose:
                        issues.append(f"Extra field: {field}")
        
        # Check for value changes in common fields
        common_fields = orig_fields & parsed_fields
        for field in common_fields:
            orig_val = original[field]
            parsed_val = parsed[field]
            
            # Compare (handle None specially)
            if orig_val != parsed_val:
                # Check if it's a type mismatch
                if type(orig_val) != type(parsed_val):
                    self.issues['type_mismatches'].append({
                        'type': type_name,
                        'index': index,
                        'field': field,
                        'orig_type': type(orig_val).__name__,
                        'parsed_type': type(parsed_val).__name__
                    })
                    if self.verbose:
                        issues.append(
                            f"Type mismatch in '{field}': "
                            f"{type(orig_val).__name__} -> {type(parsed_val).__name__}"
                        )
                else:
                    # Value changed but type same
                    self.issues['value_changes'].append({
                        'type': type_name,
                        'index': index,
                        'field': field,
                        'original': orig_val,
                        'parsed': parsed_val
                    })
                    if self.verbose:
                        issues.append(
                            f"Value changed in '{field}': {orig_val} -> {parsed_val}"
                        )
        
        return issues
    
    def _print_summary(self):
        """Print audit summary"""
        print()
        print("=" * 70)
        print("PARSING AUDIT SUMMARY")
        print("=" * 70)
        print()
        
        # Overall stats
        total = self.results['total_fixtures']
        success = self.results['successful_parses']
        failed = self.results['failed_parses']
        success_rate = (success / total * 100) if total > 0 else 0
        
        print("Overall Results:")
        print(f"  Total fixtures:      {total}")
        print(f"  Successful parses:   {success}")
        print(f"  Failed parses:       {failed}")
        print(f"  Success rate:        {success_rate:.1f}%")
        print()
        
        # By type
        if self.results['by_type']:
            print("By Type:")
            for type_name in sorted(self.results['by_type'].keys()):
                stats = self.results['by_type'][type_name]
                rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
                status = "✅" if stats['success'] == stats['total'] else "❌"
                print(f"  {status} {type_name:30s} {stats['success']}/{stats['total']} ({rate:.0f}%)")
        print()
        
        # Issues summary
        print("Issues Found:")
        
        if self.issues['missing_fields']:
            print(f"\n  Missing Fields (by type):")
            for type_name in sorted(self.issues['missing_fields'].keys()):
                fields = sorted(self.issues['missing_fields'][type_name])
                print(f"    {type_name}: {', '.join(fields)}")
        
        if self.issues['extra_fields']:
            print(f"\n  Extra Fields (by type):")
            for type_name in sorted(self.issues['extra_fields'].keys()):
                fields = sorted(self.issues['extra_fields'][type_name])
                print(f"    {type_name}: {', '.join(fields)}")
        
        if self.issues['type_mismatches']:
            print(f"\n  Type Mismatches: {len(self.issues['type_mismatches'])}")
            if self.verbose and len(self.issues['type_mismatches']) <= 10:
                for issue in self.issues['type_mismatches'][:10]:
                    print(f"    {issue['type']}[{issue['index']}].{issue['field']}: "
                          f"{issue['orig_type']} -> {issue['parsed_type']}")
        
        if self.issues['value_changes']:
            print(f"\n  Value Changes: {len(self.issues['value_changes'])}")
            if self.verbose and len(self.issues['value_changes']) <= 10:
                for issue in self.issues['value_changes'][:10]:
                    print(f"    {issue['type']}[{issue['index']}].{issue['field']}")
        
        if not any([
            self.issues['missing_fields'],
            self.issues['extra_fields'],
            self.issues['type_mismatches'],
            self.issues['value_changes']
        ]):
            print("  ✅ None! Perfect parsing.")
        
        print()
        
        # Assessment
        print("=" * 70)
        if success_rate == 100 and not any([
            self.issues['missing_fields'],
            self.issues['extra_fields'],
            self.issues['type_mismatches']
        ]):
            print("✅ ASSESSMENT: PERFECT PARSING")
            print()
            print("The API client parses all fixtures correctly with no data loss!")
        elif success_rate >= 95:
            print("✅ ASSESSMENT: EXCELLENT PARSING")
            print()
            print("Minor issues found but overall parsing is very good.")
        elif success_rate >= 90:
            print("⚠️  ASSESSMENT: GOOD PARSING")
            print()
            print("Some issues need attention but most parsing works.")
        else:
            print("❌ ASSESSMENT: NEEDS IMPROVEMENT")
            print()
            print("Significant parsing issues found - see details above.")
        print("=" * 70)
        print()
    
    def save_report(self, output_file: Path):
        """Save detailed report to JSON"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_fixtures': self.results['total_fixtures'],
                'successful_parses': self.results['successful_parses'],
                'failed_parses': self.results['failed_parses'],
                'success_rate': (
                    self.results['successful_parses'] / self.results['total_fixtures'] * 100
                    if self.results['total_fixtures'] > 0 else 0
                )
            },
            'by_type': dict(self.results['by_type']),
            'issues': {
                'missing_fields': {k: list(v) for k, v in self.issues['missing_fields'].items()},
                'extra_fields': {k: list(v) for k, v in self.issues['extra_fields'].items()},
                'type_mismatches': self.issues['type_mismatches'],
                'value_changes': self.issues['value_changes'][:100]  # Limit to first 100
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Detailed report saved to: {output_file}")


def main():
    """Main entry point"""
    from datetime import datetime
    
    parser = argparse.ArgumentParser(
        description="Audit API client parsing with production fixtures",
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
        default=Path('tests/api_parsing_audit_report.json'),
        help='Output report file'
    )
    parser.add_argument(
        '--type',
        help='Filter to specific type'
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
    
    # Create auditor
    auditor = APIParsingAuditor(args.fixtures, args.verbose)
    
    # Run audit
    success = auditor.audit_all(filter_type=args.type)
    
    # Save report
    auditor.save_report(args.output)
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
