#!/usr/bin/env python3
"""
Phase 5b: Default Detection Verification - Application Analysis

This script analyzes how applications are being classified as default vs custom,
and helps identify issues with the default detection criteria.
"""

import sys
import json
import getpass
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
import re


def load_config_file(filename: str) -> Optional[Dict[str, Any]]:
    """Load configuration from file."""
    from config.storage.json_storage import load_config_json, derive_key
    
    if not Path(filename).exists():
        print(f"  ✗ File not found: {filename}")
        return None
    
    print(f"Loading configuration from: {filename}")
    
    # Detect encryption
    encrypted = None
    try:
        with open(filename, 'rb') as f:
            data = f.read()
        try:
            decoded = data.decode('utf-8').strip()
            if decoded.startswith('{') or decoded.startswith('['):
                try:
                    json.loads(decoded)
                    encrypted = False
                except json.JSONDecodeError:
                    encrypted = True
            else:
                encrypted = True
        except UnicodeDecodeError:
            encrypted = True
    except Exception as e:
        print(f"  ⚠ Warning: Could not determine encryption status: {e}")
        encrypted = None
    
    try:
        cipher = None
        if encrypted:
            decrypt_password = getpass.getpass("Enter password to decrypt backup: ")
            cipher = derive_key(decrypt_password)
            config = load_config_json(filename, cipher=cipher, encrypted=True)
        elif encrypted is False:
            config = load_config_json(filename, cipher=None, encrypted=False)
        else:
            config = load_config_json(filename, cipher=None, encrypted=None)
        
        if not config:
            print("  ✗ Failed to load configuration")
            return None
        
        print("  ✓ Configuration loaded successfully")
        return config
        
    except Exception as e:
        print(f"  ✗ Failed to load configuration: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_current_detection_patterns():
    """Get current default detection patterns for applications."""
    from config.defaults.default_configs import DefaultConfigs
    
    return {
        'application_patterns': DefaultConfigs.DEFAULT_APPLICATION_PATTERNS,
        'object_patterns': DefaultConfigs.DEFAULT_OBJECT_NAME_PATTERNS,
        'address_objects': list(DefaultConfigs.DEFAULT_ADDRESS_OBJECTS),
        'service_objects': list(DefaultConfigs.DEFAULT_SERVICE_OBJECTS)
    }


def test_application_detection(app_name: str, app_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Test if an application would be detected as default."""
    from config.defaults.default_configs import DefaultConfigs
    
    result = {
        'app_name': app_name,
        'is_default': False,
        'matched_pattern': None,
        'matched_reason': None,
        'snippet': None,
        'tested_patterns': []
    }
    
    # Check snippet association first (most reliable indicator)
    if app_data:
        snippet = app_data.get('snippet', '')
        if snippet:
            result['snippet'] = snippet
            snippet_lower = snippet.lower()
            for pattern in DefaultConfigs.DEFAULT_SNIPPET_PATTERNS:
                if pattern not in result['tested_patterns']:
                    result['tested_patterns'].append(f"snippet:{pattern}")
                if re.match(pattern, snippet_lower, re.IGNORECASE):
                    result['is_default'] = True
                    result['matched_pattern'] = pattern
                    result['matched_reason'] = f"Associated with predefined snippet: {snippet}"
                    return result
    
    # Test application-specific patterns
    app_lower = app_name.lower()
    for pattern in DefaultConfigs.DEFAULT_APPLICATION_PATTERNS:
        result['tested_patterns'].append(f"app:{pattern}")
        if re.match(pattern, app_lower, re.IGNORECASE):
            result['is_default'] = True
            result['matched_pattern'] = pattern
            result['matched_reason'] = "Application name pattern match"
            break
    
    # Test general object patterns
    if not result['is_default']:
        for pattern in DefaultConfigs.DEFAULT_OBJECT_NAME_PATTERNS:
            pattern_key = f"object:{pattern}"
            if pattern_key not in result['tested_patterns']:
                result['tested_patterns'].append(pattern_key)
            if re.match(pattern, app_lower, re.IGNORECASE):
                result['is_default'] = True
                result['matched_pattern'] = pattern
                result['matched_reason'] = "Object name pattern match"
                break
    
    return result


def analyze_applications(config: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze all applications in configuration."""
    from config.defaults.default_configs import DefaultConfigs
    
    analysis = {
        'total_applications': 0,
        'marked_default': 0,
        'marked_custom': 0,
        'detected_default': 0,
        'detected_custom': 0,
        'mismatches': [],
        'applications': []
    }
    
    security_policies = config.get('security_policies', {})
    folders = security_policies.get('folders', [])
    
    for folder in folders:
        folder_name = folder.get('name', 'Unknown')
        objects = folder.get('objects', {})
        applications = objects.get('applications', [])
        
        for app in applications:
            app_name = app.get('name', 'Unknown')
            is_default_marked = app.get('is_default', False)
            
            # Test what the detector would say (pass full app data to check snippet)
            detection_result = test_application_detection(app_name, app_data=app)
            is_default_detected = detection_result['is_default']
            
            analysis['total_applications'] += 1
            
            if is_default_marked:
                analysis['marked_default'] += 1
            else:
                analysis['marked_custom'] += 1
            
            if is_default_detected:
                analysis['detected_default'] += 1
            else:
                analysis['detected_custom'] += 1
            
            # Check for mismatch
            if is_default_marked != is_default_detected:
                analysis['mismatches'].append({
                    'folder': folder_name,
                    'app_name': app_name,
                    'marked_as': 'default' if is_default_marked else 'custom',
                    'detected_as': 'default' if is_default_detected else 'custom',
                    'matched_pattern': detection_result.get('matched_pattern'),
                    'matched_reason': detection_result.get('matched_reason'),
                    'snippet': detection_result.get('snippet') or app.get('snippet', '')
                })
            
            analysis['applications'].append({
                'folder': folder_name,
                'app_name': app_name,
                'is_default_marked': is_default_marked,
                'is_default_detected': is_default_detected,
                'matched_pattern': detection_result.get('matched_pattern'),
                'matched_reason': detection_result.get('matched_reason'),
                'snippet': detection_result.get('snippet') or app.get('snippet', ''),
                'all_patterns': detection_result['tested_patterns']
            })
    
    return analysis


def print_detection_criteria():
    """Print current detection criteria."""
    patterns = get_current_detection_patterns()
    
    print("\n" + "=" * 60)
    print("CURRENT DETECTION CRITERIA")
    print("=" * 60)
    
    print("\nApplication Patterns:")
    for i, pattern in enumerate(patterns['application_patterns'], 1):
        print(f"  {i}. {pattern}")
    
    print("\nGeneral Object Patterns:")
    for i, pattern in enumerate(patterns['object_patterns'], 1):
        print(f"  {i}. {pattern}")
    
    print("\nDefault Address Objects:")
    for obj in patterns['address_objects']:
        print(f"  - {obj}")
    
    print("\nDefault Service Objects:")
    for obj in patterns['service_objects']:
        print(f"  - {obj}")
    
    print("\n" + "=" * 60)
    print("DECISION LOGIC:")
    print("=" * 60)
    print("An application is marked as DEFAULT if:")
    print("  1. Name matches any application pattern (case-insensitive)")
    print("  2. OR name matches any general object pattern (case-insensitive)")
    print("\nApplication patterns checked:")
    print("  - Contains 'palo alto'")
    print("  - Starts with 'pan-'")
    print("  - Contains 'predefined'")
    print("  - Contains 'default'")
    print("=" * 60)


def print_analysis_results(analysis: Dict[str, Any]):
    """Print analysis results."""
    print("\n" + "=" * 60)
    print("APPLICATION ANALYSIS RESULTS")
    print("=" * 60)
    
    print(f"\nTotal Applications: {analysis['total_applications']}")
    print(f"\nMarked as Default: {analysis['marked_default']}")
    print(f"Marked as Custom: {analysis['marked_custom']}")
    
    print(f"\nDetected as Default: {analysis['detected_default']}")
    print(f"Detected as Custom: {analysis['detected_custom']}")
    
    if analysis['total_applications'] > 0:
        marked_default_pct = (analysis['marked_default'] / analysis['total_applications']) * 100
        detected_default_pct = (analysis['detected_default'] / analysis['total_applications']) * 100
        
        print(f"\nMarked Default %: {marked_default_pct:.1f}%")
        print(f"Detected Default %: {detected_default_pct:.1f}%")
    
        print(f"\nMismatches: {len(analysis['mismatches'])}")
    
    if analysis['mismatches']:
        print("\n" + "-" * 60)
        print("MISMATCHES (Marked vs Detected)")
        print("-" * 60)
        for mismatch in analysis['mismatches'][:20]:  # Show first 20
            print(f"\nApplication: {mismatch['app_name']}")
            print(f"  Folder: {mismatch['folder']}")
            print(f"  Marked as: {mismatch['marked_as']}")
            print(f"  Detected as: {mismatch['detected_as']}")
            if mismatch.get('snippet'):
                print(f"  Snippet: {mismatch['snippet']}")
            if mismatch.get('matched_pattern'):
                print(f"  Matched pattern: {mismatch['matched_pattern']}")
            if mismatch.get('matched_reason'):
                print(f"  Reason: {mismatch['matched_reason']}")
        
        if len(analysis['mismatches']) > 20:
            print(f"\n  ... and {len(analysis['mismatches']) - 20} more mismatches")
    
    print("=" * 60)


def list_applications_by_status(analysis: Dict[str, Any], status: str = 'custom'):
    """List applications by their marked status."""
    print("\n" + "=" * 60)
    print(f"APPLICATIONS MARKED AS {status.upper()}")
    print("=" * 60)
    
    if status == 'custom':
        apps = [a for a in analysis['applications'] if not a['is_default_marked']]
    else:
        apps = [a for a in analysis['applications'] if a['is_default_marked']]
    
    if not apps:
        print(f"\nNo applications marked as {status}")
        return
    
    print(f"\nFound {len(apps)} applications marked as {status}:")
    
    # Group by folder
    by_folder = {}
    for app in apps:
        folder = app['folder']
        if folder not in by_folder:
            by_folder[folder] = []
        by_folder[folder].append(app)
    
    for folder, folder_apps in by_folder.items():
        print(f"\n[{folder}] ({len(folder_apps)} applications):")
        for app in folder_apps[:30]:  # Show first 30 per folder
            detected_status = "✓ DETECTED as default" if app['is_default_detected'] else "✗ NOT detected as default"
            snippet_info = ""
            if app.get('snippet'):
                snippet_info = f" [Snippet: {app['snippet']}]"
            print(f"  - {app['app_name']} ({detected_status}){snippet_info}")
            if app.get('matched_pattern'):
                print(f"    Pattern: {app['matched_pattern']}")
            if app.get('matched_reason'):
                print(f"    Reason: {app['matched_reason']}")
        
        if len(folder_apps) > 30:
            print(f"  ... and {len(folder_apps) - 30} more")
    
    print("=" * 60)


def suggest_improvements(analysis: Dict[str, Any]):
    """Suggest improvements to detection patterns."""
    print("\n" + "=" * 60)
    print("SUGGESTIONS FOR IMPROVEMENT")
    print("=" * 60)
    
    # Find common patterns in custom-marked apps
    custom_apps = [a for a in analysis['applications'] if not a['is_default_marked']]
    
    if not custom_apps:
        print("\nNo custom applications found - all are marked as default")
        return
    
    # Analyze naming patterns
    common_prefixes = {}
    common_suffixes = {}
    common_words = {}
    
    for app in custom_apps:
        app_name = app['app_name'].lower()
        
        # Check prefixes (first 3-10 chars)
        for length in range(3, min(11, len(app_name))):
            prefix = app_name[:length]
            common_prefixes[prefix] = common_prefixes.get(prefix, 0) + 1
        
        # Check suffixes (last 3-10 chars)
        for length in range(3, min(11, len(app_name))):
            suffix = app_name[-length:]
            common_suffixes[suffix] = common_suffixes.get(suffix, 0) + 1
        
        # Check for common words
        words = app_name.split()
        for word in words:
            if len(word) > 2:
                common_words[word] = common_words.get(word, 0) + 1
    
    # Find most common patterns
    top_prefixes = sorted(common_prefixes.items(), key=lambda x: x[1], reverse=True)[:10]
    top_suffixes = sorted(common_suffixes.items(), key=lambda x: x[1], reverse=True)[:10]
    top_words = sorted(common_words.items(), key=lambda x: x[1], reverse=True)[:20]
    
    print(f"\nAnalyzed {len(custom_apps)} custom-marked applications")
    
    print("\nMost common prefixes:")
    for prefix, count in top_prefixes:
        if count >= 2:  # At least 2 occurrences
            print(f"  '{prefix}...' appears {count} times")
    
    print("\nMost common suffixes:")
    for suffix, count in top_suffixes:
        if count >= 2:
            print(f"  '...{suffix}' appears {count} times")
    
    print("\nMost common words:")
    for word, count in top_words:
        if count >= 2:
            print(f"  '{word}' appears {count} times")
    
    # Check if these look like predefined apps
    print("\n" + "-" * 60)
    print("RECOMMENDATIONS:")
    print("-" * 60)
    print("Many Palo Alto applications are predefined in the App-ID database.")
    print("Consider:")
    print("  1. Most applications from App-ID catalog should be marked as default")
    print("  2. Only custom applications (user-created) should be marked as custom")
    print("  3. Custom apps often have:")
    print("     - User-specific naming conventions")
    print("     - Organization-specific names")
    print("     - Custom application signatures")
    print("  4. Predefined apps typically have:")
    print("     - Standard application names (e.g., 'web-browsing', 'ssl', 'dns')")
    print("     - Vendor names (e.g., 'microsoft-office', 'google-apps')")
    print("     - Protocol names (e.g., 'http', 'https', 'ftp')")
    print("=" * 60)


def main():
    """Main analysis function."""
    print("=" * 60)
    print("Phase 5b: Default Detection Verification - Application Analysis")
    print("=" * 60)
    
    # Get filename
    filename = input("\nEnter configuration filename: ").strip()
    if not filename:
        print("  ✗ No filename provided")
        return 1
    
    # Load configuration
    config = load_config_file(filename)
    if not config:
        return 1
    
    # Show current detection criteria
    print_detection_criteria()
    
    # Analyze applications
    print("\nAnalyzing applications...")
    analysis = analyze_applications(config)
    
    # Print results
    print_analysis_results(analysis)
    
    # Interactive menu
    while True:
        print("\n" + "=" * 60)
        print("ANALYSIS OPTIONS")
        print("=" * 60)
        print("1. List all applications marked as CUSTOM")
        print("2. List all applications marked as DEFAULT")
        print("3. Show mismatches (marked vs detected)")
        print("4. Test specific application name")
        print("5. Suggest pattern improvements")
        print("6. Export analysis to JSON")
        print("7. Exit")
        
        choice = input("\nEnter choice (1-7): ").strip()
        
        if choice == '1':
            list_applications_by_status(analysis, 'custom')
        elif choice == '2':
            list_applications_by_status(analysis, 'default')
        elif choice == '3':
            if analysis['mismatches']:
                print("\n" + "=" * 60)
                print("MISMATCHES DETAIL")
                print("=" * 60)
                for mismatch in analysis['mismatches']:
                    print(f"\nApplication: {mismatch['app_name']}")
                    print(f"  Folder: {mismatch['folder']}")
                    print(f"  Marked as: {mismatch['marked_as']}")
                    print(f"  Detected as: {mismatch['detected_as']}")
                    if mismatch.get('snippet'):
                        print(f"  Snippet: {mismatch['snippet']}")
                    if mismatch.get('matched_pattern'):
                        print(f"  Matched pattern: {mismatch['matched_pattern']}")
                    if mismatch.get('matched_reason'):
                        print(f"  Reason: {mismatch['matched_reason']}")
                print("=" * 60)
            else:
                print("\nNo mismatches found")
        elif choice == '4':
            app_name = input("Enter application name to test: ").strip()
            if app_name:
                # Try to find the app in config to get snippet info
                app_data = None
                security_policies = config.get('security_policies', {})
                folders = security_policies.get('folders', [])
                for folder in folders:
                    objects = folder.get('objects', {})
                    applications = objects.get('applications', [])
                    for app in applications:
                        if app.get('name', '').lower() == app_name.lower():
                            app_data = app
                            break
                    if app_data:
                        break
                
                result = test_application_detection(app_name, app_data=app_data)
                print("\n" + "=" * 60)
                print("DETECTION TEST RESULT")
                print("=" * 60)
                print(f"Application: {app_name}")
                print(f"Detected as: {'DEFAULT' if result['is_default'] else 'CUSTOM'}")
                if result.get('snippet'):
                    print(f"Snippet: {result['snippet']}")
                if result.get('matched_pattern'):
                    print(f"Matched pattern: {result['matched_pattern']}")
                if result.get('matched_reason'):
                    print(f"Reason: {result['matched_reason']}")
                print("\nTested patterns:")
                for pattern in result['tested_patterns']:
                    print(f"  - {pattern}")
                print("=" * 60)
        elif choice == '5':
            suggest_improvements(analysis)
        elif choice == '6':
            output_file = filename.replace('.json', '_analysis.json')
            with open(output_file, 'w') as f:
                json.dump(analysis, f, indent=2)
            print(f"\n✓ Analysis exported to: {output_file}")
        elif choice == '7':
            print("\nExiting...")
            break
        else:
            print("  ✗ Invalid choice")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
