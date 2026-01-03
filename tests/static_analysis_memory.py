"""
Static Code Analysis for Memory Safety Issues

This script proactively scans the codebase for patterns that can cause
memory corruption, segfaults, and other stability issues.

Run with: python3 tests/static_analysis_memory.py
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict


class MemorySafetyAnalyzer:
    """Analyze code for memory safety issues."""
    
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.issues: List[Dict] = []
        
    def scan_all(self):
        """Run all checks."""
        print("="*80)
        print("MEMORY SAFETY STATIC ANALYSIS")
        print("="*80)
        print()
        
        self.check_shallow_copies()
        self.check_mutable_defaults()
        self.check_class_level_mutables()
        self.check_missing_deepcopy()
        self.check_thread_unsafe_patterns()
        
        self.print_report()
        
        return len(self.issues)
    
    def check_shallow_copies(self):
        """Find shallow copy patterns that could cause shared references."""
        print("🔍 Checking for shallow copy issues...")
        
        patterns = [
            (r'\.copy\(\)', 'dict.copy() or list.copy() - potential shallow copy'),
            (r'= \w+\.copy\(\)', 'Assignment from .copy() - check if nested'),
        ]
        
        for py_file in self.root_dir.rglob('*.py'):
            # Skip test files, archives, and venv
            if any(skip in str(py_file) for skip in ['test', 'archive', 'venv', '.venv', 'site-packages']):
                continue
                
            with open(py_file, 'r') as f:
                lines = f.readlines()
                
            for line_num, line in enumerate(lines, 1):
                # Skip if it's already using deepcopy
                if 'deepcopy' in line:
                    continue
                # Skip if it's JSON serialization (safe)
                if 'json.loads(json.dumps' in line:
                    continue
                    
                for pattern, description in patterns:
                    if re.search(pattern, line):
                        # Check if the copied object might have nested structures
                        if any(keyword in line.lower() for keyword in ['config', 'data', 'raw', 'dict']):
                            self.issues.append({
                                'severity': 'HIGH',
                                'type': 'SHALLOW_COPY',
                                'file': str(py_file),
                                'line': line_num,
                                'code': line.strip(),
                                'description': description
                            })
    
    def check_mutable_defaults(self):
        """Find mutable default arguments."""
        print("🔍 Checking for mutable default arguments...")
        
        for py_file in self.root_dir.rglob('*.py'):
            if any(skip in str(py_file) for skip in ['test', 'archive', 'venv', '.venv', 'site-packages']):
                continue
                
            with open(py_file, 'r') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                # Look for function definitions with list/dict defaults
                if re.search(r'def\s+\w+\([^)]*=\s*\[', line):
                    self.issues.append({
                        'severity': 'MEDIUM',
                        'type': 'MUTABLE_DEFAULT',
                        'file': str(py_file),
                        'line': line_num,
                        'code': line.strip(),
                        'description': 'Mutable list default argument'
                    })
                elif re.search(r'def\s+\w+\([^)]*=\s*\{', line):
                    self.issues.append({
                        'severity': 'MEDIUM',
                        'type': 'MUTABLE_DEFAULT',
                        'file': str(py_file),
                        'line': line_num,
                        'code': line.strip(),
                        'description': 'Mutable dict default argument'
                    })
    
    def check_class_level_mutables(self):
        """Find class-level mutable attributes."""
        print("🔍 Checking for class-level mutable attributes...")
        
        for py_file in self.root_dir.rglob('*.py'):
            if any(skip in str(py_file) for skip in ['test', 'archive', 'venv', '.venv', 'site-packages']):
                continue
                
            with open(py_file, 'r') as f:
                content = f.read()
                lines = content.split('\n')
            
            in_class = False
            class_indent = 0
            
            for line_num, line in enumerate(lines, 1):
                # Track if we're in a class definition
                if re.match(r'^class\s+\w+', line):
                    in_class = True
                    class_indent = len(line) - len(line.lstrip())
                elif in_class and line.strip() and not line.strip().startswith('#'):
                    current_indent = len(line) - len(line.lstrip())
                    if current_indent <= class_indent:
                        in_class = False
                
                # Check for class-level mutable assignments
                if in_class and re.search(r'^\s+\w+\s*=\s*\[', line):
                    if 'def ' not in line:  # Not inside a method
                        self.issues.append({
                            'severity': 'HIGH',
                            'type': 'CLASS_MUTABLE',
                            'file': str(py_file),
                            'line': line_num,
                            'code': line.strip(),
                            'description': 'Class-level mutable list (shared between instances)'
                        })
                elif in_class and re.search(r'^\s+\w+\s*=\s*\{', line):
                    if 'def ' not in line:
                        self.issues.append({
                            'severity': 'HIGH',
                            'type': 'CLASS_MUTABLE',
                            'file': str(py_file),
                            'line': line_num,
                            'code': line.strip(),
                            'description': 'Class-level mutable dict (shared between instances)'
                        })
    
    def check_missing_deepcopy(self):
        """Find places where deepcopy might be needed."""
        print("🔍 Checking for missing deepcopy in critical areas...")
        
        for py_file in self.root_dir.rglob('*.py'):
            if any(skip in str(py_file) for skip in ['test', 'archive', 'venv', '.venv', 'site-packages']):
                continue
            
            with open(py_file, 'r') as f:
                content = f.read()
                
            # Look for to_dict methods without deepcopy or JSON
            if 'def to_dict' in content:
                # Check if it uses safe copying
                if 'json.loads(json.dumps' not in content and 'copy.deepcopy' not in content:
                    # Find line number
                    lines = content.split('\n')
                    for line_num, line in enumerate(lines, 1):
                        if 'def to_dict' in line:
                            self.issues.append({
                                'severity': 'CRITICAL',
                                'type': 'MISSING_SAFE_COPY',
                                'file': str(py_file),
                                'line': line_num,
                                'code': line.strip(),
                                'description': 'to_dict() without safe copying (json or deepcopy)'
                            })
    
    def check_thread_unsafe_patterns(self):
        """Find patterns that are not thread-safe."""
        print("🔍 Checking for thread-unsafe patterns...")
        
        unsafe_patterns = [
            (r'worker\.finished\.connect\([^,)]+\)(?!.*QueuedConnection)', 
             'Worker signal without QueuedConnection'),
            (r'print\(', 'print() statement (use logging in workers)'),
        ]
        
        for py_file in self.root_dir.rglob('*.py'):
            # Only check GUI files for thread safety
            if 'gui' not in str(py_file):
                continue
            if any(skip in str(py_file) for skip in ['test', 'archive', 'venv', '.venv', 'site-packages']):
                continue
                
            with open(py_file, 'r') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                for pattern, description in unsafe_patterns:
                    if re.search(pattern, line):
                        # Special handling for print
                        if 'print(' in line and 'logger' not in line:
                            self.issues.append({
                                'severity': 'HIGH',
                                'type': 'THREAD_UNSAFE',
                                'file': str(py_file),
                                'line': line_num,
                                'code': line.strip(),
                                'description': description
                            })
    
    def print_report(self):
        """Print analysis report."""
        print()
        print("="*80)
        print("ANALYSIS RESULTS")
        print("="*80)
        print()
        
        if not self.issues:
            print("✅ No memory safety issues found!")
            return
        
        # Group by severity
        by_severity = {'CRITICAL': [], 'HIGH': [], 'MEDIUM': [], 'LOW': []}
        for issue in self.issues:
            by_severity[issue['severity']].append(issue)
        
        # Print by severity
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            issues = by_severity[severity]
            if not issues:
                continue
                
            print(f"\n{'='*80}")
            print(f"{severity} ISSUES ({len(issues)})")
            print(f"{'='*80}\n")
            
            for issue in issues:
                print(f"📍 {issue['file']}:{issue['line']}")
                print(f"   Type: {issue['type']}")
                print(f"   Code: {issue['code']}")
                print(f"   Issue: {issue['description']}")
                print()
        
        # Summary
        print("="*80)
        print("SUMMARY")
        print("="*80)
        total = len(self.issues)
        print(f"Total issues found: {total}")
        print(f"  Critical: {len(by_severity['CRITICAL'])}")
        print(f"  High: {len(by_severity['HIGH'])}")
        print(f"  Medium: {len(by_severity['MEDIUM'])}")
        print(f"  Low: {len(by_severity['LOW'])}")
        print()
        
        if by_severity['CRITICAL']:
            print("⚠️  CRITICAL issues require immediate attention!")
            print("   These can cause memory corruption and crashes.")
        
        if by_severity['HIGH']:
            print("⚠️  HIGH priority issues should be fixed soon.")
            print("   These can cause instability and bugs.")


def main():
    """Run static analysis."""
    # Get project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    analyzer = MemorySafetyAnalyzer(project_root)
    issue_count = analyzer.scan_all()
    
    # Exit with error code if issues found
    if issue_count > 0:
        print(f"\n❌ Found {issue_count} potential issues.")
        print("   Review and fix before committing.")
        sys.exit(1)
    else:
        print("\n✅ All checks passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
