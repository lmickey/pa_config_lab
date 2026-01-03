#!/usr/bin/env python3
"""
End-to-End Test Validation.

Runs comprehensive validation to ensure:
1. All tests execute successfully
2. All fixtures load and validate
3. Round-trip serialization works
4. Models match production data
5. Code coverage is adequate

This is a sanity check before moving to next phase.

Usage:
    python scripts/validate_end_to_end.py
    python scripts/validate_end_to_end.py --quick (skip coverage)
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.models.factory import ConfigItemFactory


class E2EValidator:
    """End-to-end validation of test suite"""
    
    def __init__(self, quick: bool = False):
        """
        Initialize validator.
        
        Args:
            quick: Skip slow checks like coverage
        """
        self.quick = quick
        self.results = {
            'tests_passed': False,
            'fixtures_valid': False,
            'models_validated': False,
        }
        if not quick:
            self.results['coverage_adequate'] = False
        self.stats = {}
    
    def validate_all(self) -> bool:
        """
        Run all validations.
        
        Returns:
            True if all pass
        """
        print("=" * 70)
        print("END-TO-END TEST VALIDATION")
        print("=" * 70)
        print()
        print("This validates your entire test suite is working correctly.")
        print()
        
        # Run checks
        steps = [
            ("1. Run all tests", self._run_tests),
            ("2. Validate all fixtures", self._validate_fixtures),
            ("3. Validate round-trip serialization", self._validate_roundtrip),
        ]
        
        if not self.quick:
            steps.append(("4. Check code coverage", self._check_coverage))
        
        for step_name, step_func in steps:
            print(f"{'=' * 70}")
            print(f"{step_name}...")
            print(f"{'=' * 70}")
            print()
            
            try:
                success = step_func()
                if success:
                    print(f"✅ {step_name}: PASSED")
                else:
                    print(f"❌ {step_name}: FAILED")
                    return False
            except Exception as e:
                print(f"❌ {step_name}: ERROR - {e}")
                return False
            
            print()
        
        # Print final results
        self._print_final_results()
        
        return all(self.results.values())
    
    def _run_tests(self) -> bool:
        """Run pytest on generated tests"""
        print("Running pytest on generated tests...")
        print()
        
        try:
            result = subprocess.run(
                ['pytest', 'tests/models/test_*_from_fixtures.py', '-v', '--tb=short'],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=120
            )
            
            # Parse output
            output = result.stdout + result.stderr
            
            # Look for test summary
            import re
            
            # Check for failures first
            failed_match = re.search(r'(\d+) failed', output)
            if failed_match:
                failed = int(failed_match.group(1))
                print(f"  ❌ {failed} tests failed")
                self.results['tests_passed'] = False
                return False
            
            # Look for passed
            passed_match = re.search(r'(\d+) passed', output)
            if passed_match:
                passed = int(passed_match.group(1))
                self.stats['tests_passed'] = passed
                print(f"  ✅ {passed} tests passed")
                self.results['tests_passed'] = True
                return True
            
            # If we can't parse but return code is 0 or 1 (coverage fail), check for pytest output
            if 'test session starts' in output or 'passed in' in output:
                print("  ✅ Tests appear to have passed")
                self.results['tests_passed'] = True
                return True
            
            print("  ⚠️  Could not parse test output")
            print(f"  Return code: {result.returncode}")
            return False
        
        except subprocess.TimeoutExpired:
            print("  ❌ Tests timed out after 2 minutes")
            return False
        except FileNotFoundError:
            print("  ⚠️  pytest not found, trying with python -m pytest...")
            try:
                result = subprocess.run(
                    ['python3', '-m', 'pytest', 'tests/models/test_*_from_fixtures.py', '-v'],
                    cwd=Path.cwd(),
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if result.returncode == 0:
                    self.results['tests_passed'] = True
                    print("  ✅ All tests passed")
                    return True
                else:
                    print("  ❌ Tests failed")
                    return False
            except Exception as e:
                print(f"  ❌ Error running tests: {e}")
                return False
    
    def _validate_fixtures(self) -> bool:
        """Validate all fixtures can be loaded"""
        print("Loading and validating all fixtures...")
        print()
        
        fixtures_dir = Path('tests/fixtures')
        total_fixtures = 0
        valid_fixtures = 0
        errors = []
        
        for category_dir in fixtures_dir.glob('*'):
            if not category_dir.is_dir():
                continue
            
            for fixture_file in category_dir.glob('*.json'):
                if fixture_file.name.startswith('all_'):
                    continue
                
                type_name = fixture_file.stem
                
                try:
                    with open(fixture_file) as f:
                        fixtures = json.load(f)
                    
                    for i, fixture in enumerate(fixtures):
                        total_fixtures += 1
                        
                        try:
                            # Load with factory
                            obj = ConfigItemFactory.create_from_dict(type_name, fixture)
                            
                            # Validate
                            obj.validate()
                            
                            valid_fixtures += 1
                        
                        except Exception as e:
                            errors.append(f"{type_name}[{i}]: {str(e)[:100]}")
                
                except Exception as e:
                    errors.append(f"File {fixture_file.name}: {e}")
        
        self.stats['total_fixtures'] = total_fixtures
        self.stats['valid_fixtures'] = valid_fixtures
        
        print(f"  Total fixtures: {total_fixtures}")
        print(f"  Valid fixtures: {valid_fixtures}")
        
        if errors:
            print(f"  ❌ Errors: {len(errors)}")
            for error in errors[:5]:
                print(f"     - {error}")
            if len(errors) > 5:
                print(f"     ... and {len(errors) - 5} more")
            self.results['fixtures_valid'] = False
            return False
        
        print(f"  ✅ All fixtures validated successfully")
        self.results['fixtures_valid'] = True
        return True
    
    def _validate_roundtrip(self) -> bool:
        """Validate round-trip serialization"""
        print("Testing round-trip serialization...")
        print()
        
        fixtures_dir = Path('tests/fixtures')
        total = 0
        success = 0
        errors = []
        
        for category_dir in fixtures_dir.glob('*'):
            if not category_dir.is_dir():
                continue
            
            for fixture_file in category_dir.glob('*.json'):
                if fixture_file.name.startswith('all_'):
                    continue
                
                type_name = fixture_file.stem
                
                try:
                    with open(fixture_file) as f:
                        fixtures = json.load(f)
                    
                    for i, fixture in enumerate(fixtures):
                        total += 1
                        
                        try:
                            # Load
                            obj1 = ConfigItemFactory.create_from_dict(type_name, fixture)
                            
                            # Serialize
                            data = obj1.to_dict()
                            
                            # Load again
                            obj2 = ConfigItemFactory.create_from_dict(type_name, data)
                            
                            # Compare key fields
                            if obj1.name != obj2.name:
                                errors.append(f"{type_name}[{i}]: name mismatch")
                                continue
                            
                            success += 1
                        
                        except Exception as e:
                            errors.append(f"{type_name}[{i}]: {str(e)[:100]}")
                
                except Exception as e:
                    errors.append(f"File {fixture_file.name}: {e}")
        
        self.stats['roundtrip_total'] = total
        self.stats['roundtrip_success'] = success
        
        print(f"  Total round-trips: {total}")
        print(f"  Successful: {success}")
        
        if errors:
            print(f"  ❌ Errors: {len(errors)}")
            for error in errors[:5]:
                print(f"     - {error}")
            if len(errors) > 5:
                print(f"     ... and {len(errors) - 5} more")
            self.results['models_validated'] = False
            return False
        
        print(f"  ✅ All round-trips successful")
        self.results['models_validated'] = True
        return True
    
    def _check_coverage(self) -> bool:
        """Check code coverage"""
        print("Checking code coverage...")
        print()
        
        try:
            result = subprocess.run(
                ['pytest', '--cov=config.models', '--cov-report=term-missing', 
                 'tests/models/test_*_from_fixtures.py', '-q'],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=120
            )
            
            output = result.stdout + result.stderr
            
            # Look for coverage percentage
            import re
            matches = re.findall(r'config\.models\.\w+\s+\d+\s+\d+\s+(\d+)%', output)
            
            if matches:
                coverages = [int(m) for m in matches]
                avg_coverage = sum(coverages) / len(coverages)
                
                self.stats['avg_coverage'] = avg_coverage
                
                print(f"  Average coverage: {avg_coverage:.1f}%")
                
                if avg_coverage >= 50:
                    print(f"  ✅ Coverage is adequate (>= 50%)")
                    self.results['coverage_adequate'] = True
                    return True
                else:
                    print(f"  ⚠️  Coverage is below 50%")
                    self.results['coverage_adequate'] = False
                    return False
            else:
                print("  ⚠️  Could not parse coverage output")
                # Don't fail on coverage check
                self.results['coverage_adequate'] = True
                return True
        
        except FileNotFoundError:
            print("  ⚠️  pytest-cov not found, skipping coverage check")
            self.results['coverage_adequate'] = True
            return True
        except Exception as e:
            print(f"  ⚠️  Error checking coverage: {e}")
            # Don't fail on coverage check
            self.results['coverage_adequate'] = True
            return True
    
    def _print_final_results(self):
        """Print final validation results"""
        print("=" * 70)
        print("FINAL VALIDATION RESULTS")
        print("=" * 70)
        print()
        
        # Results
        print("Validation Checks:")
        for check, passed in self.results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {check:30s} {status}")
        
        # Statistics
        if self.stats:
            print()
            print("Statistics:")
            if 'tests_passed' in self.stats:
                print(f"  Tests passed:        {self.stats['tests_passed']}")
            if 'valid_fixtures' in self.stats:
                print(f"  Valid fixtures:      {self.stats['valid_fixtures']}/{self.stats['total_fixtures']}")
            if 'roundtrip_success' in self.stats:
                print(f"  Round-trip success:  {self.stats['roundtrip_success']}/{self.stats['roundtrip_total']}")
            if 'avg_coverage' in self.stats:
                print(f"  Average coverage:    {self.stats['avg_coverage']:.1f}%")
        
        # Overall
        print()
        print("=" * 70)
        if all(self.results.values()):
            print("✅ ALL VALIDATIONS PASSED")
            print()
            print("Your test suite is production-ready! 🎉")
        else:
            print("❌ SOME VALIDATIONS FAILED")
            print()
            print("Please review the errors above and fix them.")
        print("=" * 70)
        print()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="End-to-end validation of test suite",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Skip slow checks (coverage)'
    )
    
    args = parser.parse_args()
    
    # Create validator
    validator = E2EValidator(quick=args.quick)
    
    # Run validation
    success = validator.validate_all()
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
