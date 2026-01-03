#!/usr/bin/env python3
"""
Logging Classification Report.

Analyzes and reports on:
- All log statements in the codebase
- Classification by level (DEBUG, INFO, WARNING, ERROR)
- What debug mode adds vs normal mode
- Coverage by module
"""

import sys
from pathlib import Path
import re
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))


def analyze_file(file_path: Path) -> dict:
    """Analyze logging statements in a file."""
    results = {
        'DEBUG': [],
        'INFO': [],
        'WARNING': [],
        'ERROR': [],
        'total': 0
    }
    
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        for line_num, line in enumerate(lines, 1):
            # Look for logger.debug/info/warning/error
            if 'logger.debug(' in line:
                results['DEBUG'].append((line_num, line.strip()))
                results['total'] += 1
            elif 'logger.info(' in line:
                results['INFO'].append((line_num, line.strip()))
                results['total'] += 1
            elif 'logger.warning(' in line:
                results['WARNING'].append((line_num, line.strip()))
                results['total'] += 1
            elif 'logger.error(' in line:
                results['ERROR'].append((line_num, line.strip()))
                results['total'] += 1
    
    except Exception as e:
        pass
    
    return results


def main():
    """Generate logging classification report."""
    print("\n" + "="*80)
    print("LOGGING CLASSIFICATION REPORT")
    print("="*80)
    
    # Files to analyze
    files_to_analyze = [
        ('Base Classes', 'config/models/base.py'),
        ('Objects', 'config/models/objects.py'),
        ('Profiles', 'config/models/profiles.py'),
        ('Policies', 'config/models/policies.py'),
        ('Infrastructure', 'config/models/infrastructure.py'),
        ('Containers', 'config/models/containers.py'),
        ('Factory', 'config/models/factory.py'),
        ('Pull Orchestrator', 'prisma/pull/pull_orchestrator.py'),
        ('Push Orchestrator V2', 'prisma/push/push_orchestrator_v2.py'),
        ('API Client', 'prisma/api_client.py'),
        ('Workflow Utils', 'config/workflows/workflow_utils.py'),
    ]
    
    all_results = {}
    totals = defaultdict(int)
    
    base_path = Path(__file__).parent.parent
    
    for name, rel_path in files_to_analyze:
        file_path = base_path / rel_path
        if file_path.exists():
            results = analyze_file(file_path)
            all_results[name] = results
            
            for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
                totals[level] += len(results[level])
            totals['total'] += results['total']
    
    # Summary by level
    print("\n" + "="*80)
    print("SUMMARY BY LOG LEVEL")
    print("="*80)
    
    print(f"\n{'Level':<15} {'Count':<10} {'Percentage':<12} {'Visibility'}")
    print("-" * 80)
    
    if totals['total'] > 0:
        print(f"{'DEBUG':<15} {totals['DEBUG']:<10} {totals['DEBUG']/totals['total']*100:>6.1f}%      Debug mode only")
        print(f"{'INFO':<15} {totals['INFO']:<10} {totals['INFO']/totals['total']*100:>6.1f}%      Always visible")
        print(f"{'WARNING':<15} {totals['WARNING']:<10} {totals['WARNING']/totals['total']*100:>6.1f}%      Always visible")
        print(f"{'ERROR':<15} {totals['ERROR']:<10} {totals['ERROR']/totals['total']*100:>6.1f}%      Always visible")
        print("-" * 80)
        print(f"{'TOTAL':<15} {totals['total']:<10}")
    
    # Normal mode vs Debug mode
    normal_mode_count = totals['INFO'] + totals['WARNING'] + totals['ERROR']
    debug_mode_count = totals['total']
    
    print(f"\n{'Mode':<20} {'Messages':<15} {'Description'}")
    print("-" * 80)
    print(f"{'Normal Mode':<20} {normal_mode_count:<15} INFO/WARNING/ERROR only")
    print(f"{'Debug Mode':<20} {debug_mode_count:<15} All levels including DEBUG")
    print(f"{'Debug Addition':<20} {totals['DEBUG']:<15} {totals['DEBUG']/debug_mode_count*100:.1f}% more messages")
    
    # Coverage by module
    print("\n" + "="*80)
    print("COVERAGE BY MODULE")
    print("="*80)
    
    print(f"\n{'Module':<30} {'Total':<8} {'DEBUG':<8} {'INFO':<8} {'WARN':<8} {'ERROR':<8}")
    print("-" * 80)
    
    for name, results in sorted(all_results.items(), key=lambda x: x[1]['total'], reverse=True):
        if results['total'] > 0:
            print(f"{name:<30} {results['total']:<8} "
                  f"{len(results['DEBUG']):<8} "
                  f"{len(results['INFO']):<8} "
                  f"{len(results['WARNING']):<8} "
                  f"{len(results['ERROR']):<8}")
    
    # Detailed breakdown of DEBUG messages
    print("\n" + "="*80)
    print("DEBUG MODE ADDITIONS (What You Get in Debug Mode)")
    print("="*80)
    
    debug_categories = {
        'Dependency Resolution': [],
        'Validation Details': [],
        'API Operations': [],
        'Cache Operations': [],
        'Progress Tracking': [],
        'Data Processing': [],
        'Other': []
    }
    
    # Categorize debug messages
    for name, results in all_results.items():
        for line_num, line in results['DEBUG']:
            line_lower = line.lower()
            
            if any(word in line_lower for word in ['depend', 'reference', 'order']):
                debug_categories['Dependency Resolution'].append((name, line_num, line))
            elif any(word in line_lower for word in ['validat', 'check', 'verify']):
                debug_categories['Validation Details'].append((name, line_num, line))
            elif any(word in line_lower for word in ['api', 'request', 'response', 'endpoint']):
                debug_categories['API Operations'].append((name, line_num, line))
            elif any(word in line_lower for word in ['cache', 'hit', 'miss']):
                debug_categories['Cache Operations'].append((name, line_num, line))
            elif any(word in line_lower for word in ['progress', 'processing', 'complete']):
                debug_categories['Progress Tracking'].append((name, line_num, line))
            elif any(word in line_lower for word in ['comput', 'generat', 'creat', 'updat']):
                debug_categories['Data Processing'].append((name, line_num, line))
            else:
                debug_categories['Other'].append((name, line_num, line))
    
    for category, messages in debug_categories.items():
        if messages:
            print(f"\n{category}: {len(messages)} messages")
            print("-" * 80)
            # Show first 3 examples
            for name, line_num, line in messages[:3]:
                # Extract just the log message
                match = re.search(r'logger\.debug\((.*)\)', line)
                if match:
                    msg = match.group(1)
                    # Truncate if too long
                    if len(msg) > 60:
                        msg = msg[:57] + "..."
                    print(f"  [{name}:{line_num}] {msg}")
            if len(messages) > 3:
                print(f"  ... and {len(messages) - 3} more")
    
    # Recommendations
    print("\n" + "="*80)
    print("LOGGING CLASSIFICATION ANALYSIS")
    print("="*80)
    
    print("\n✅ NORMAL MODE (INFO/WARNING/ERROR):")
    print("   Messages visible in production:")
    print(f"   • {totals['INFO']} INFO messages - Normal operations")
    print(f"   • {totals['WARNING']} WARNING messages - Recoverable issues")
    print(f"   • {totals['ERROR']} ERROR messages - Failures")
    print(f"   • Total: {normal_mode_count} messages in typical workflows")
    
    print("\n✅ DEBUG MODE (+DEBUG):")
    print("   Additional diagnostic information:")
    print(f"   • {totals['DEBUG']} DEBUG messages added")
    print(f"   • {totals['DEBUG']/debug_mode_count*100:.1f}% increase in log volume")
    print("   • Includes detailed operation traces")
    print("   • Useful for troubleshooting")
    
    # When to use each level
    print("\n" + "="*80)
    print("WHEN TO USE EACH LOG LEVEL")
    print("="*80)
    
    print("\nERROR - Operation failures that prevent completion:")
    print("  • API calls that fail")
    print("  • Missing required data")
    print("  • Validation failures that block operations")
    print("  • Examples from codebase:")
    for name, results in list(all_results.items())[:2]:
        for line_num, line in results['ERROR'][:2]:
            match = re.search(r'logger\.error\((.*)\)', line)
            if match:
                print(f"    {match.group(1)[:70]}")
    
    print("\nWARNING - Recoverable issues, items skipped:")
    print("  • Items skipped due to conflicts")
    print("  • Optional validation warnings")
    print("  • Default items excluded")
    print("  • Examples from codebase:")
    for name, results in list(all_results.items())[:2]:
        for line_num, line in results['WARNING'][:2]:
            match = re.search(r'logger\.warning\((.*)\)', line)
            if match:
                print(f"    {match.group(1)[:70]}")
    
    print("\nINFO - Normal operations, state changes:")
    print("  • Successful create/update/delete")
    print("  • Workflow start/complete")
    print("  • Major state changes")
    print("  • Examples from codebase:")
    for name, results in list(all_results.items())[:2]:
        for line_num, line in results['INFO'][:2]:
            match = re.search(r'logger\.info\((.*)\)', line)
            if match:
                print(f"    {match.group(1)[:70]}")
    
    print("\nDEBUG - Detailed diagnostics (debug mode only):")
    print("  • Dependency resolution details")
    print("  • Validation step-by-step")
    print("  • API request/response bodies")
    print("  • Cache operations")
    print("  • Examples from codebase:")
    for name, results in list(all_results.items())[:2]:
        for line_num, line in results['DEBUG'][:2]:
            match = re.search(r'logger\.debug\((.*)\)', line)
            if match:
                print(f"    {match.group(1)[:70]}")
    
    print("\n" + "="*80)
    print("REPORT COMPLETE")
    print("="*80)
    print(f"\nAnalyzed {len(all_results)} modules")
    print(f"Found {totals['total']} log statements")
    print(f"Normal mode: {normal_mode_count} messages ({normal_mode_count/totals['total']*100:.1f}%)")
    print(f"Debug mode adds: {totals['DEBUG']} messages ({totals['DEBUG']/totals['total']*100:.1f}%)")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
