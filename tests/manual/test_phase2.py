#!/usr/bin/env python3
"""
Test script for Phase 2 implementation.

This script tests:
1. Folder capture functionality
2. Rule capture functionality
3. Object capture functionality
4. Profile capture functionality
5. Snippet capture functionality
6. Pull orchestration

Can be run against a real Prisma Access tenant by providing credentials.
"""

import os
import sys
import getpass
from datetime import datetime
from io import StringIO

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TeeOutput:
    """Tee output to both console and file."""
    def __init__(self, file_path):
        self.file_path = file_path
        self.file = open(file_path, 'w', encoding='utf-8')
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        
    def write(self, text):
        self.stdout.write(text)
        self.file.write(text)
        self.file.flush()
        
    def flush(self):
        self.stdout.flush()
        self.file.flush()
        
    def close(self):
        self.file.close()
        sys.stdout = self.stdout
        sys.stderr = self.stderr


def setup_output_file():
    """Set up output file with timestamp."""
    timestamp = datetime.now().strftime("%H.%M.%S-%m.%d.%Y")
    filename = f"Phase 2 Implementation Test-{timestamp}.txt"
    filepath = os.path.join(os.getcwd(), filename)
    
    tee = TeeOutput(filepath)
    sys.stdout = tee
    sys.stderr = tee
    
    return tee, filepath


def get_credentials():
    """
    Prompt user for Prisma Access credentials.
    
    Returns:
        Tuple of (tsg_id, api_user, api_secret) or (None, None, None) if skipped
    """
    print("\n" + "=" * 60)
    print("Prisma Access Credentials")
    print("=" * 60)
    print("Enter credentials to test against a real tenant.")
    print("Press Enter to skip and run structure tests only.")
    print("\nNote: For testing, use tenant tsg: 1570970024")
    print("      Use 'Mobile Users' folder for security policy testing.\n")
    
    use_real = input("Test against real tenant? (y/n): ").strip().lower()
    
    if use_real != 'y':
        print("Skipping real tenant tests. Running structure tests only.\n")
        return None, None, None
    
    tsg_id = input("Enter TSG ID: ").strip()
    if not tsg_id:
        print("TSG ID is required. Skipping real tenant tests.\n")
        return None, None, None
    
    api_user = input("Enter API Client ID: ").strip()
    if not api_user:
        print("API Client ID is required. Skipping real tenant tests.\n")
        return None, None, None
    
    api_secret = getpass.getpass("Enter API Client Secret: ").strip()
    if not api_secret:
        print("API Client Secret is required. Skipping real tenant tests.\n")
        return None, None, None
    
    print("\nCredentials provided. Testing against real tenant...\n")
    return tsg_id, api_user, api_secret


def select_test_folder(folders):
    """
    Select the best folder for testing security policies.
    
    Prefers folders with actual security policy content over infrastructure folders.
    Priority: Mobile Users > Access Agent > GlobalProtect > Prisma Access > other folders > Service Connections
    
    Args:
        folders: List of folder dictionaries OR list of folder name strings
        
    Returns:
        Best folder name for testing, or None if no folders available
    """
    if not folders:
        return None
    
    # Handle both list of dicts and list of strings
    if isinstance(folders[0], dict):
        folder_names = [f.get('name', '') if isinstance(f, dict) else str(f) for f in folders]
    else:
        folder_names = [str(f) for f in folders]
    
    # Priority order for test folders - Mobile Users is preferred for testing
    preferred_folders = [
        'Mobile Users',  # Preferred folder for testing (has actual security policies)
        'Access Agent',
        'GlobalProtect',
        'Prisma Access',
        'Explicit Proxy',
        'Mobile User Container'
    ]
    
    # Find first preferred folder
    for preferred in preferred_folders:
        for folder_name in folder_names:
            if preferred.lower() in folder_name.lower():
                return folder_name
    
    # Avoid Service Connections and Remote Networks (infrastructure only)
    avoid_folders = ['Service Connections', 'Remote Networks']
    for folder_name in folder_names:
        if folder_name not in avoid_folders:
            return folder_name
    
    # Last resort: use first folder
    return folder_names[0] if folder_names else None


def test_folder_capture(api_client=None):
    """Test folder capture."""
    print("=" * 60)
    print("Test 1: Folder Capture")
    print("=" * 60)
    
    try:
        from prisma.pull.folder_capture import FolderCapture, capture_folders
        
        # Test module structure
        assert hasattr(FolderCapture, 'discover_folders')
        assert hasattr(FolderCapture, 'get_folder_details')
        assert hasattr(FolderCapture, 'get_folder_hierarchy')
        print("✓ Folder capture module structure correct")
        
        # Test against real tenant if API client provided
        if api_client:
            print("\n  Testing against real tenant...")
            folder_capture = FolderCapture(api_client)
            
            try:
                # Discover folders
                folders = folder_capture.discover_folders()
                
                if len(folders) == 0:
                    print(f"  ✗ FAILED: No folders discovered (expected at least 4-5 default folders)")
                    print("    Expected folders: Service Connections, Remote Networks, Mobile User Container,")
                    print("    Mobile Users, Access Agent/GlobalProtect, Explicit Proxy")
                    return False
                
                print(f"  ✓ Discovered {len(folders)} folders")
                
                # Show all folders
                for folder in folders:
                    print(f"    - {folder.get('name', 'Unknown')} (default: {folder.get('is_default', False)})")
                
                # Select best test folder
                test_folder = select_test_folder(folders)
                if test_folder:
                    print(f"\n  Selected test folder: {test_folder}")
                    print(f"    (This folder will be used for subsequent tests)")
                
                # Verify expected folders exist
                folder_names = [f.get('name', '').lower() for f in folders]
                expected_folders = ['service connections', 'remote networks', 'mobile user container']
                missing_folders = [ef for ef in expected_folders if not any(ef in fn for fn in folder_names)]
                
                if missing_folders:
                    print(f"  ⚠ WARNING: Missing expected folders: {', '.join(missing_folders)}")
                
                # Test folder hierarchy
                hierarchy = folder_capture.get_folder_hierarchy()
                print(f"  ✓ Built folder hierarchy ({len(hierarchy)} folders)")
                
                # Test listing folders
                folder_list = folder_capture.list_folders_for_capture(include_defaults=False)
                print(f"  ✓ Listed {len(folder_list)} non-default folders for capture")
                
            except Exception as e:
                print(f"  ✗ FAILED: Error discovering folders: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Folder capture test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rule_capture(api_client=None):
    """Test rule capture."""
    print("\n" + "=" * 60)
    print("Test 3: Rule Capture")
    print("=" * 60)
    
    try:
        from prisma.pull.rule_capture import RuleCapture, capture_rules_from_folder
        
        # Test module structure
        assert hasattr(RuleCapture, 'capture_rules_from_folder')
        assert hasattr(RuleCapture, 'capture_rules_from_snippet')
        assert hasattr(RuleCapture, 'capture_all_rules')
        print("✓ Rule capture module structure correct")
        
        # Test against real tenant if API client provided
        if api_client:
            try:
                print("\n  Testing against real tenant...")
                rule_capture = RuleCapture(api_client)
                
                # Get a folder to test with
                from prisma.pull.folder_capture import FolderCapture
                folder_capture = FolderCapture(api_client)
                folders = folder_capture.discover_folders()
                
                if not folders:
                    print("  ✗ FAILED: No folders available for testing")
                    return False
                
                # Select best test folder (prefer Mobile Users over Service Connections)
                test_folder = select_test_folder(folders)
                if not test_folder:
                    print("  ✗ FAILED: Could not select test folder")
                    return False
                
                print(f"  Testing with folder: {test_folder}")
                
                # Capture rules with detailed error handling
                try:
                    rules = rule_capture.capture_rules_from_folder(test_folder)
                except Exception as capture_error:
                    print(f"  ✗ FAILED: Error capturing rules from folder {test_folder}")
                    print(f"    Error type: {type(capture_error).__name__}")
                    print(f"    Error message: {str(capture_error)}")
                    import traceback
                    print("\n    Full traceback:")
                    traceback.print_exc()
                    return False
                
                rule_count = len(rules) if rules else 0
                print(f"  ✓ Captured {rule_count} rules from {test_folder}")
                
                # Validation: Mobile Users folder should always have rules
                if rule_count == 0:
                    print(f"\n  ✗ FAILED: No rules captured from folder '{test_folder}'")
                    print(f"    Expected: At least 1 rule (Mobile Users folder should contain security rules)")
                    print(f"    Actual: 0 rules")
                    print(f"\n    This indicates:")
                    print(f"    - The API call may have failed silently")
                    print(f"    - The folder may not contain security rules (unexpected)")
                    print(f"    - There may be an issue with rule capture logic")
                    return False
                
                # Show rule details
                print(f"\n  Rule capture validation:")
                print(f"    ✓ Successfully captured {rule_count} rule(s)")
                
                # Show first rule details
                if rules:
                    first_rule = rules[0]
                    print(f"\n  Example rule details:")
                    print(f"    Name: {first_rule.get('name', 'Unknown')}")
                    print(f"    Action: {first_rule.get('action', 'Unknown')}")
                    print(f"    Position: {first_rule.get('position', 'Unknown')}")
                    print(f"    Source: {first_rule.get('source', 'Unknown')}")
                    print(f"    Destination: {first_rule.get('destination', 'Unknown')}")
                    
                    # Validate rule structure
                    required_fields = ['name', 'action']
                    missing_fields = [field for field in required_fields if field not in first_rule]
                    if missing_fields:
                        print(f"\n  ⚠ WARNING: Rule missing required fields: {missing_fields}")
                
            except Exception as e:
                print(f"  ✗ FAILED: Real tenant test error: {e}")
                print(f"    Error type: {type(e).__name__}")
                import traceback
                print("\n    Full traceback:")
                traceback.print_exc()
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Rule capture test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_object_capture(api_client=None):
    """Test object capture."""
    print("\n" + "=" * 60)
    print("Test 4: Object Capture")
    print("=" * 60)
    
    try:
        from prisma.pull.object_capture import ObjectCapture, capture_objects_from_folder
        
        # Test module structure
        assert hasattr(ObjectCapture, 'capture_addresses')
        assert hasattr(ObjectCapture, 'capture_address_groups')
        assert hasattr(ObjectCapture, 'capture_services')
        assert hasattr(ObjectCapture, 'capture_all_objects')
        print("✓ Object capture module structure correct")
        
        # Test against real tenant if API client provided
        if api_client:
            try:
                print("\n  Testing against real tenant...")
                object_capture = ObjectCapture(api_client)
                
                # Get a folder to test with
                from prisma.pull.folder_capture import FolderCapture
                folder_capture = FolderCapture(api_client)
                folders = folder_capture.discover_folders()
                
                if not folders:
                    print("  ✗ FAILED: No folders available for testing")
                    return False
                
                # Select best test folder (prefer Mobile Users over Service Connections)
                test_folder = select_test_folder(folders)
                if not test_folder:
                    print("  ✗ FAILED: Could not select test folder")
                    return False
                
                print(f"  Testing with folder: {test_folder}")
                
                # Capture addresses with detailed error handling
                try:
                    addresses = object_capture.capture_addresses(folder=test_folder)
                    address_count = len(addresses) if addresses else 0
                    print(f"  ✓ Captured {address_count} address objects")
                except Exception as capture_error:
                    print(f"  ✗ FAILED: Error capturing addresses from folder {test_folder}")
                    print(f"    Error type: {type(capture_error).__name__}")
                    print(f"    Error message: {str(capture_error)}")
                    from prisma.error_logger import error_logger
                    error_logger.log_capture_error(
                        "capture_addresses",
                        test_folder,
                        capture_error
                    )
                    import traceback
                    print("\n    Full traceback:")
                    traceback.print_exc()
                    return False
                
                # Capture address groups with detailed error handling
                try:
                    address_groups = object_capture.capture_address_groups(folder=test_folder)
                    group_count = len(address_groups) if address_groups else 0
                    print(f"  ✓ Captured {group_count} address groups")
                except Exception as capture_error:
                    print(f"  ✗ FAILED: Error capturing address groups from folder {test_folder}")
                    print(f"    Error type: {type(capture_error).__name__}")
                    print(f"    Error message: {str(capture_error)}")
                    from prisma.error_logger import error_logger
                    error_logger.log_capture_error(
                        "capture_address_groups",
                        test_folder,
                        capture_error
                    )
                    import traceback
                    print("\n    Full traceback:")
                    traceback.print_exc()
                    return False
                
                # Capture all objects with detailed error handling
                try:
                    all_objects = object_capture.capture_all_objects(folder=test_folder)
                    total = sum(len(objs) for objs in all_objects.values()) if all_objects else 0
                    print(f"  ✓ Captured {total} total objects")
                    
                    # Show breakdown
                    if all_objects:
                        print(f"\n  Object capture breakdown:")
                        for obj_type, objs in all_objects.items():
                            count = len(objs) if objs else 0
                            print(f"    {obj_type}: {count}")
                        
                        # Show example object if available
                        for obj_type, objs in all_objects.items():
                            if objs and len(objs) > 0:
                                example = objs[0]
                                print(f"\n  Example {obj_type} object:")
                                print(f"    Name: {example.get('name', 'Unknown')}")
                                print(f"    Type: {example.get('type', 'Unknown')}")
                                if 'description' in example:
                                    print(f"    Description: {example.get('description', 'N/A')}")
                                break
                
                except Exception as capture_error:
                    print(f"  ✗ FAILED: Error capturing all objects from folder {test_folder}")
                    print(f"    Error type: {type(capture_error).__name__}")
                    print(f"    Error message: {str(capture_error)}")
                    from prisma.error_logger import error_logger
                    error_logger.log_capture_error(
                        "capture_all_objects",
                        test_folder,
                        capture_error
                    )
                    import traceback
                    print("\n    Full traceback:")
                    traceback.print_exc()
                    return False
                
            except Exception as e:
                print(f"  ✗ FAILED: Real tenant test error: {e}")
                print(f"    Error type: {type(e).__name__}")
                from prisma.error_logger import error_logger
                error_logger.log_capture_error(
                    "test_object_capture",
                    "test execution",
                    e
                )
                import traceback
                print("\n    Full traceback:")
                traceback.print_exc()
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Object capture test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_profile_capture(api_client=None):
    """Test profile capture."""
    print("\n" + "=" * 60)
    print("Test 5: Profile Capture")
    print("=" * 60)
    
    try:
        from prisma.pull.profile_capture import ProfileCapture, capture_profiles_from_folder
        
        # Test module structure
        assert hasattr(ProfileCapture, 'capture_authentication_profiles')
        assert hasattr(ProfileCapture, 'capture_security_profiles')
        assert hasattr(ProfileCapture, 'capture_all_profiles')
        print("✓ Profile capture module structure correct")
        
        # Test against real tenant if API client provided
        if api_client:
            try:
                print("\n  Testing against real tenant...")
                profile_capture = ProfileCapture(api_client)
                
                # Get a folder to test with
                from prisma.pull.folder_capture import FolderCapture
                folder_capture = FolderCapture(api_client)
                folders = folder_capture.discover_folders()
                
                if not folders:
                    print("  ✗ FAILED: No folders available for testing")
                    return False
                
                # Select best test folder (prefer Mobile Users over Service Connections)
                test_folder = select_test_folder(folders)
                if not test_folder:
                    print("  ✗ FAILED: Could not select test folder")
                    return False
                
                print(f"  Testing with folder: {test_folder}")
                
                # Capture authentication profiles with detailed error handling
                try:
                    auth_profiles = profile_capture.capture_authentication_profiles(folder=test_folder)
                    auth_count = len(auth_profiles) if auth_profiles else 0
                    print(f"  ✓ Captured {auth_count} authentication profiles")
                    
                    if auth_profiles and len(auth_profiles) > 0:
                        example = auth_profiles[0]
                        print(f"\n  Example authentication profile:")
                        print(f"    Name: {example.get('name', 'Unknown')}")
                        print(f"    Type: {example.get('type', 'Unknown')}")
                except Exception as capture_error:
                    print(f"  ✗ FAILED: Error capturing authentication profiles from folder {test_folder}")
                    print(f"    Error type: {type(capture_error).__name__}")
                    print(f"    Error message: {str(capture_error)}")
                    from prisma.error_logger import error_logger
                    error_logger.log_capture_error(
                        "capture_authentication_profiles",
                        test_folder,
                        capture_error
                    )
                    import traceback
                    print("\n    Full traceback:")
                    traceback.print_exc()
                    return False
                
                # Capture all profiles with detailed error handling
                try:
                    all_profiles = profile_capture.capture_all_profiles(folder=test_folder)
                    auth_count = len(all_profiles.get('authentication_profiles', [])) if all_profiles else 0
                    sec_count = sum(len(profs) for profs in all_profiles.get('security_profiles', {}).values()) if all_profiles else 0
                    # Decryption profiles is now a list, not a dict
                    dec_profiles = all_profiles.get('decryption_profiles', []) if all_profiles else []
                    dec_count = len(dec_profiles) if isinstance(dec_profiles, list) else sum(len(profs) for profs in dec_profiles.values())
                    
                    print(f"\n  Profile capture validation:")
                    print(f"    ✓ Authentication profiles: {auth_count}")
                    print(f"    ✓ Security profiles: {sec_count}")
                    print(f"    ✓ Decryption profiles: {dec_count}")
                    print(f"    ✓ Total profiles: {auth_count + sec_count + dec_count}")
                    
                    # Validation: Security profiles should always exist (at least default best practice profiles)
                    # Only check the profile types marked "include in test" from Master-API-Entpoint-List.txt
                    if sec_count == 0:
                        from prisma.api_endpoints import APIEndpoints, SASE_BASE_URL
                        print(f"\n  ✗ FAILED: No security profiles captured from folder '{test_folder}'")
                        print(f"    Expected: At least 1 security profile (default best practice profiles should exist)")
                        print(f"    Actual: 0 security profiles")
                        print(f"\n    Security profiles should be available at:")
                        encoded_folder = test_folder.replace(' ', '%20')
                        print(f"    - Anti-spyware: {SASE_BASE_URL}/anti-spyware-profiles?folder={encoded_folder}")
                        print(f"    - DNS Security: {SASE_BASE_URL}/dns-security-profiles?folder={encoded_folder}")
                        print(f"    - File Blocking: {SASE_BASE_URL}/file-blocking-profiles?folder={encoded_folder}")
                        print(f"    - HTTP Header: {SASE_BASE_URL}/http-header-profiles?folder={encoded_folder}")
                        print(f"    - Profile Groups: {SASE_BASE_URL}/profile-groups?folder={encoded_folder}")
                        print(f"    - URL Access: {SASE_BASE_URL}/url-access-profiles?folder={encoded_folder}")
                        print(f"    - Vulnerability Protection: {SASE_BASE_URL}/vulnerability-protection-profiles?folder={encoded_folder}")
                        print(f"    - WildFire Anti-Virus: {SASE_BASE_URL}/wildfire-anti-virus-profiles?folder={encoded_folder}")
                        print(f"\n    Decryption profiles:")
                        print(f"    - Decryption: {SASE_BASE_URL}/decryption-profiles?folder={encoded_folder}")
                        print(f"\n    This indicates:")
                        print(f"    - Security profile capture may not be implemented correctly")
                        print(f"    - API endpoint may be incorrect")
                        print(f"    - Folder may not have security profiles configured")
                        from prisma.error_logger import error_logger
                        encoded_folder = test_folder.replace(' ', '%20')
                        error_logger.log_capture_error(
                            "capture_all_profiles",
                            test_folder,
                            Exception("No security profiles found - expected at least default best practice profiles"),
                            {
                                "security_profile_count": 0,
                                "expected_minimum": 1,
                                "api_urls": [
                                    f"{SASE_BASE_URL}/anti-spyware-profiles?folder={encoded_folder}",
                                    f"{SASE_BASE_URL}/dns-security-profiles?folder={encoded_folder}",
                                    f"{SASE_BASE_URL}/file-blocking-profiles?folder={encoded_folder}",
                                    f"{SASE_BASE_URL}/http-header-profiles?folder={encoded_folder}",
                                    f"{SASE_BASE_URL}/profile-groups?folder={encoded_folder}",
                                    f"{SASE_BASE_URL}/url-access-profiles?folder={encoded_folder}",
                                    f"{SASE_BASE_URL}/vulnerability-protection-profiles?folder={encoded_folder}",
                                    f"{SASE_BASE_URL}/wildfire-anti-virus-profiles?folder={encoded_folder}",
                                    f"{SASE_BASE_URL}/decryption-profiles?folder={encoded_folder}"
                                ]
                            }
                        )
                        return False
                    
                    # Show breakdown of security profiles
                    if all_profiles and all_profiles.get('security_profiles'):
                        print(f"\n  Security profile breakdown:")
                        for profile_type, profs in all_profiles['security_profiles'].items():
                            count = len(profs) if profs else 0
                            if count > 0:
                                print(f"    {profile_type}: {count}")
                
                except Exception as capture_error:
                    print(f"  ✗ FAILED: Error capturing all profiles from folder {test_folder}")
                    print(f"    Error type: {type(capture_error).__name__}")
                    print(f"    Error message: {str(capture_error)}")
                    from prisma.error_logger import error_logger
                    error_logger.log_capture_error(
                        "capture_all_profiles",
                        test_folder,
                        capture_error
                    )
                    import traceback
                    print("\n    Full traceback:")
                    traceback.print_exc()
                    return False
                
            except Exception as e:
                print(f"  ✗ FAILED: Real tenant test error: {e}")
                print(f"    Error type: {type(e).__name__}")
                from prisma.error_logger import error_logger
                error_logger.log_capture_error(
                    "test_profile_capture",
                    "test execution",
                    e
                )
                import traceback
                print("\n    Full traceback:")
                traceback.print_exc()
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Profile capture test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_snippet_capture(api_client=None):
    """Test snippet capture."""
    print("\n" + "=" * 60)
    print("Test 2: Snippet Capture")
    print("=" * 60)
    
    try:
        from prisma.pull.snippet_capture import SnippetCapture, capture_snippets
        
        # Test module structure
        assert hasattr(SnippetCapture, 'discover_snippets')
        assert hasattr(SnippetCapture, 'capture_snippet_configuration')
        assert hasattr(SnippetCapture, 'capture_all_snippets')
        print("✓ Snippet capture module structure correct")
        
        # Test against real tenant if API client provided
        if api_client:
            try:
                print("\n  Testing against real tenant...")
                snippet_capture = SnippetCapture(api_client)
                
                # Discover snippets with detailed error handling
                try:
                    snippets = snippet_capture.discover_snippets()
                    snippet_count = len(snippets) if snippets else 0
                    print(f"  ✓ Discovered {snippet_count} snippets")
                    
                    if snippets:
                        print(f"\n  Snippet discovery validation:")
                        print(f"    ✓ Successfully discovered {snippet_count} snippet(s)")
                        print(f"\n  Discovered snippets:")
                        for snippet in snippets[:5]:  # Show up to 5
                            name = snippet.get('name', 'Unknown')
                            snippet_type = snippet.get('type', 'Unknown')
                            print(f"    - {name} (type: {snippet_type})")
                        if len(snippets) > 5:
                            print(f"    ... and {len(snippets) - 5} more")
                    else:
                        print(f"\n  Note: No snippets discovered (this may be normal for some tenants)")
                
                except Exception as capture_error:
                    print(f"  ✗ FAILED: Error discovering snippets")
                    print(f"    Error type: {type(capture_error).__name__}")
                    print(f"    Error message: {str(capture_error)}")
                    from prisma.error_logger import error_logger
                    error_logger.log_capture_error(
                        "discover_snippets",
                        "snippet discovery",
                        capture_error
                    )
                    import traceback
                    print("\n    Full traceback:")
                    traceback.print_exc()
                    return False
                
            except Exception as e:
                print(f"  ✗ FAILED: Real tenant test error: {e}")
                print(f"    Error type: {type(e).__name__}")
                from prisma.error_logger import error_logger
                error_logger.log_capture_error(
                    "test_snippet_capture",
                    "test execution",
                    e
                )
                import traceback
                print("\n    Full traceback:")
                traceback.print_exc()
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Snippet capture test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pull_orchestrator(api_client=None):
    """Test pull orchestrator."""
    print("\n" + "=" * 60)
    print("Test 6: Pull Orchestrator")
    print("=" * 60)
    
    try:
        from prisma.pull.pull_orchestrator import PullOrchestrator
        
        # Test module structure
        assert hasattr(PullOrchestrator, 'pull_folder_configuration')
        assert hasattr(PullOrchestrator, 'pull_all_folders')
        assert hasattr(PullOrchestrator, 'pull_complete_configuration')
        assert hasattr(PullOrchestrator, 'set_progress_callback')
        print("✓ Pull orchestrator module structure correct")
        
        # Test against real tenant if API client provided
        if api_client:
            try:
                print("\n  Testing against real tenant...")
                orchestrator = PullOrchestrator(api_client)
                
                # Set progress callback
                def progress_callback(message, current, total):
                    if total > 0:
                        print(f"    [{current}/{total}] {message}")
                    else:
                        print(f"    {message}")
                
                orchestrator.set_progress_callback(progress_callback)
                
                # Get a folder to test with
                from prisma.pull.folder_capture import FolderCapture
                folder_capture = FolderCapture(api_client)
                folders = folder_capture.list_folders_for_capture(include_defaults=False)
                
                if not folders:
                    print("  ✗ FAILED: No folders available for testing")
                    return False
                
                # Select best test folder (prefer Mobile Users over Service Connections)
                test_folder = select_test_folder(folders)
                if not test_folder:
                    print("  ✗ FAILED: Could not select test folder")
                    return False
                
                print(f"  Testing pull with folder: {test_folder}")
                
                # Pull folder configuration with detailed error handling
                try:
                    folder_config = orchestrator.pull_folder_configuration(
                        test_folder,
                        include_objects=True,
                        include_profiles=True
                    )
                    
                    if not folder_config:
                        print(f"  ✗ FAILED: No configuration returned for folder {test_folder}")
                        return False
                    
                    # Also capture snippets (snippets are global, not folder-specific)
                    print(f"    [4/4] Capturing snippets")
                    try:
                        snippets = orchestrator.pull_snippets()
                        snippets_count = len(snippets) if snippets else 0
                        print(f"    ✓ Captured {snippets_count} snippets")
                    except Exception as snippet_error:
                        print(f"    ⚠ WARNING: Error capturing snippets: {snippet_error}")
                        snippets_count = 0
                    
                    # Validate configuration structure
                    rules_count = len(folder_config.get('security_rules', []))
                    
                    # Count objects correctly - objects is a dict with lists as values
                    objects_dict = folder_config.get('objects', {})
                    objects_count = sum(len(objs) for objs in objects_dict.values()) if isinstance(objects_dict, dict) else 0
                    
                    # Count profiles correctly - profiles is a dict with lists/dicts as values
                    profiles_dict = folder_config.get('profiles', {})
                    auth_profiles = profiles_dict.get('authentication_profiles', [])
                    security_profiles = profiles_dict.get('security_profiles', {})
                    decryption_profiles = profiles_dict.get('decryption_profiles', [])
                    
                    auth_count = len(auth_profiles) if isinstance(auth_profiles, list) else 0
                    sec_count = sum(len(profs) for profs in security_profiles.values()) if isinstance(security_profiles, dict) else 0
                    # Decryption profiles is now a list, not a dict
                    dec_count = len(decryption_profiles) if isinstance(decryption_profiles, list) else (sum(len(profs) for profs in decryption_profiles.values()) if isinstance(decryption_profiles, dict) else 0)
                    profiles_count = auth_count + sec_count + dec_count
                    
                    print(f"\n  Pull configuration validation:")
                    print(f"    ✓ Folder: {test_folder}")
                    print(f"    ✓ Security rules: {rules_count}")
                    print(f"    ✓ Objects: {objects_count}")
                    print(f"    ✓ Profiles: {profiles_count} (Auth: {auth_count}, Security: {sec_count}, Decryption: {dec_count})")
                    print(f"    ✓ Snippets: {snippets_count}")
                    
                    # Validate counts match what we expect from earlier tests
                    # Expected: 22 rules, 211 objects, 32 profiles (5 auth + 24 security + 3 decryption), 27 snippets
                    expected_rules = 22
                    expected_objects = 211
                    expected_profiles = 32
                    expected_snippets = 27
                    
                    validation_failed = False
                    
                    if rules_count != expected_rules:
                        print(f"\n  ✗ FAILED: Rule count mismatch")
                        print(f"    Expected: {expected_rules} (from Test 3)")
                        print(f"    Actual: {rules_count}")
                        validation_failed = True
                    
                    if objects_count != expected_objects:
                        print(f"\n  ✗ FAILED: Object count mismatch")
                        print(f"    Expected: {expected_objects} (from Test 4)")
                        print(f"    Actual: {objects_count}")
                        print(f"    This indicates objects were not captured correctly by the orchestrator")
                        validation_failed = True
                    
                    if profiles_count != expected_profiles:
                        print(f"\n  ✗ FAILED: Profile count mismatch")
                        print(f"    Expected: {expected_profiles} (from Test 5: 5 auth + 24 security + 3 decryption)")
                        print(f"    Actual: {profiles_count} (Auth: {auth_count}, Security: {sec_count}, Decryption: {dec_count})")
                        print(f"    This indicates profiles were not captured correctly by the orchestrator")
                        validation_failed = True
                    
                    if snippets_count != expected_snippets:
                        print(f"\n  ✗ FAILED: Snippet count mismatch")
                        print(f"    Expected: {expected_snippets} (from Test 2)")
                        print(f"    Actual: {snippets_count}")
                        print(f"    This indicates snippets were not captured correctly by the orchestrator")
                        validation_failed = True
                    
                    if validation_failed:
                        print(f"\n  ✗ FAILED: Configuration counts do not match expected values")
                        print(f"    The orchestrator may not be capturing data correctly")
                        return False
                    
                    # Get pull report
                    report = orchestrator.get_pull_report()
                    if not report:
                        print(f"  ⚠ WARNING: No pull report generated")
                    else:
                        stats = report.get('stats', {})
                        print(f"\n  Pull report:")
                        print(f"    Folders captured: {stats.get('folders_captured', 0)}")
                        print(f"    Rules captured: {stats.get('rules_captured', 0)}")
                        print(f"    Objects captured: {stats.get('objects_captured', 0)}")
                        print(f"    Profiles captured: {stats.get('profiles_captured', 0)}")
                        print(f"    Snippets captured: {stats.get('snippets_captured', 0)}")
                        
                        # Validate pull report stats match what we captured
                        if stats.get('snippets_captured', 0) != snippets_count:
                            print(f"\n  ⚠ WARNING: Pull report snippet count ({stats.get('snippets_captured', 0)}) doesn't match captured count ({snippets_count})")
                        
                        # Check for errors in pull
                        errors = stats.get('errors', [])
                        if errors:
                            print(f"\n  ⚠ WARNING: {len(errors)} errors occurred during pull:")
                            for error in errors[:5]:  # Show first 5 errors
                                print(f"    - {error.get('message', 'Unknown error')}")
                            if len(errors) > 5:
                                print(f"    ... and {len(errors) - 5} more errors")
                
                except Exception as capture_error:
                    print(f"  ✗ FAILED: Error pulling folder configuration for {test_folder}")
                    print(f"    Error type: {type(capture_error).__name__}")
                    print(f"    Error message: {str(capture_error)}")
                    from prisma.error_logger import error_logger
                    error_logger.log_capture_error(
                        "pull_folder_configuration",
                        test_folder,
                        capture_error
                    )
                    import traceback
                    print("\n    Full traceback:")
                    traceback.print_exc()
                    return False
                
            except Exception as e:
                print(f"  ✗ FAILED: Real tenant test error: {e}")
                print(f"    Error type: {type(e).__name__}")
                from prisma.error_logger import error_logger
                error_logger.log_capture_error(
                    "test_pull_orchestrator",
                    "test execution",
                    e
                )
                import traceback
                print("\n    Full traceback:")
                traceback.print_exc()
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Pull orchestrator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_pull(api_client=None):
    """Test config pull."""
    print("\n" + "=" * 60)
    print("Test 7: Config Pull")
    print("=" * 60)
    
    try:
        from prisma.pull.config_pull import (
            pull_configuration,
            pull_folders_only,
            pull_snippets_only
        )
        
        # Test function signatures exist
        assert callable(pull_configuration)
        assert callable(pull_folders_only)
        assert callable(pull_snippets_only)
        print("✓ Config pull module structure correct")
        
        # Test against real tenant if API client provided
        if api_client:
            try:
                print("\n  Testing against real tenant...")
                
                # Test pull_configuration (full pull with all components)
                print("  Testing pull_configuration (full pull)...")
                from prisma.pull.folder_capture import FolderCapture
                folder_capture = FolderCapture(api_client)
                folders = folder_capture.list_folders_for_capture(include_defaults=False)
                
                if not folders:
                    print("  ✗ FAILED: No folders available for testing")
                    return False
                
                # Select best test folder (prefer Mobile Users)
                test_folder = select_test_folder(folders)
                if not test_folder:
                    print("  ✗ FAILED: Could not select test folder")
                    return False
                
                test_folders = [test_folder]
                print(f"  Pulling configuration for folder: {test_folder}")
                
                # Pull full configuration with detailed error handling
                try:
                    config = pull_configuration(
                        api_client,
                        folder_names=test_folders,
                        include_defaults=False,
                        include_snippets=True,
                        include_objects=True,
                        include_profiles=True,
                        save_to_file=None  # Don't save during test
                    )
                    
                    if not config:
                        print("  ✗ FAILED: No configuration returned")
                        return False
                    
                    # Extract folder configuration from the full config
                    security_policies = config.get('security_policies', {})
                    folders_list = security_policies.get('folders', [])
                    
                    if not folders_list:
                        print("  ✗ FAILED: No folders in configuration")
                        return False
                    
                    # Get the first (and only) folder config
                    folder_config = folders_list[0]
                    folder_name = folder_config.get('name', 'Unknown')
                    rules_count = len(folder_config.get('security_rules', []))
                    
                    # Count objects correctly
                    objects_dict = folder_config.get('objects', {})
                    objects_count = sum(len(objs) for objs in objects_dict.values()) if isinstance(objects_dict, dict) else 0
                    
                    # Count profiles correctly
                    profiles_dict = folder_config.get('profiles', {})
                    auth_profiles = profiles_dict.get('authentication_profiles', [])
                    security_profiles = profiles_dict.get('security_profiles', {})
                    decryption_profiles = profiles_dict.get('decryption_profiles', [])
                    
                    auth_count = len(auth_profiles) if isinstance(auth_profiles, list) else 0
                    sec_count = sum(len(profs) for profs in security_profiles.values()) if isinstance(security_profiles, dict) else 0
                    dec_count = len(decryption_profiles) if isinstance(decryption_profiles, list) else (sum(len(profs) for profs in decryption_profiles.values()) if isinstance(decryption_profiles, dict) else 0)
                    profiles_count = auth_count + sec_count + dec_count
                    
                    # Count snippets
                    snippets_list = security_policies.get('snippets', [])
                    snippets_count = len(snippets_list) if isinstance(snippets_list, list) else 0
                    
                    print(f"\n  Config pull validation:")
                    print(f"    ✓ Successfully pulled configuration for folder: {folder_name}")
                    
                    print(f"\n  Configuration details:")
                    print(f"    Folder: {folder_name}")
                    print(f"    Security rules: {rules_count}")
                    print(f"    Objects: {objects_count}")
                    print(f"    Profiles: {profiles_count} (Auth: {auth_count}, Security: {sec_count}, Decryption: {dec_count})")
                    print(f"    Snippets: {snippets_count}")
                    
                    # Validate counts match expected values from earlier tests
                    expected_rules = 22
                    expected_objects = 211
                    expected_profiles = 32
                    expected_snippets = 27
                    
                    validation_failed = False
                    
                    if rules_count != expected_rules:
                        print(f"\n  ✗ FAILED: Rule count mismatch")
                        print(f"    Expected: {expected_rules} (from Test 3)")
                        print(f"    Actual: {rules_count}")
                        validation_failed = True
                    
                    if objects_count != expected_objects:
                        print(f"\n  ✗ FAILED: Object count mismatch")
                        print(f"    Expected: {expected_objects} (from Test 4)")
                        print(f"    Actual: {objects_count}")
                        validation_failed = True
                    
                    if profiles_count != expected_profiles:
                        print(f"\n  ✗ FAILED: Profile count mismatch")
                        print(f"    Expected: {expected_profiles} (from Test 5)")
                        print(f"    Actual: {profiles_count}")
                        validation_failed = True
                    
                    if snippets_count != expected_snippets:
                        print(f"\n  ✗ FAILED: Snippet count mismatch")
                        print(f"    Expected: {expected_snippets} (from Test 2)")
                        print(f"    Actual: {snippets_count}")
                        validation_failed = True
                    
                    if validation_failed:
                        print(f"\n  ✗ FAILED: Configuration counts do not match expected values")
                        return False
                    
                    print(f"\n  ✓ All configuration counts match expected values")
                
                except Exception as capture_error:
                    print(f"  ✗ FAILED: Error pulling folder configurations")
                    print(f"    Error type: {type(capture_error).__name__}")
                    print(f"    Error message: {str(capture_error)}")
                    from prisma.error_logger import error_logger
                    error_logger.log_capture_error(
                        "pull_folders_only",
                        str(test_folders),
                        capture_error
                    )
                    import traceback
                    print("\n    Full traceback:")
                    traceback.print_exc()
                    return False
                
            except Exception as e:
                print(f"  ✗ FAILED: Real tenant test error: {e}")
                print(f"    Error type: {type(e).__name__}")
                from prisma.error_logger import error_logger
                error_logger.log_capture_error(
                    "test_config_pull",
                    "test execution",
                    e
                )
                import traceback
                print("\n    Full traceback:")
                traceback.print_exc()
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Config pull test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration(api_client=None):
    """Test integration between modules."""
    print("\n" + "=" * 60)
    print("Test 8: Module Integration")
    print("=" * 60)
    
    try:
        # Test that all modules can be imported together
        from prisma.pull.folder_capture import FolderCapture
        from prisma.pull.rule_capture import RuleCapture
        from prisma.pull.object_capture import ObjectCapture
        from prisma.pull.profile_capture import ProfileCapture
        from prisma.pull.snippet_capture import SnippetCapture
        from prisma.pull.pull_orchestrator import PullOrchestrator
        from prisma.pull.config_pull import pull_configuration
        
        print("✓ All modules integrate correctly")
        
        # Test that orchestrator uses all capture modules
        if api_client:
            try:
                print("\n  Testing orchestrator integration...")
                orchestrator = PullOrchestrator(api_client)
                
                # Verify all capture modules are initialized
                modules_to_check = [
                    ('folder_capture', 'FolderCapture'),
                    ('rule_capture', 'RuleCapture'),
                    ('object_capture', 'ObjectCapture'),
                    ('profile_capture', 'ProfileCapture'),
                    ('snippet_capture', 'SnippetCapture')
                ]
                
                print(f"\n  Module integration validation:")
                all_valid = True
                
                # Check that all modules are initialized
                for attr_name, module_name in modules_to_check:
                    module = getattr(orchestrator, attr_name, None)
                    if module is None:
                        print(f"    ✗ {module_name} not initialized")
                        all_valid = False
                    else:
                        # Verify module has API client reference (integration check)
                        if not hasattr(module, 'api_client'):
                            print(f"    ✗ {module_name} missing api_client attribute")
                            all_valid = False
                        elif module.api_client is not api_client:
                            print(f"    ✗ {module_name} has different API client instance")
                            all_valid = False
                        else:
                            print(f"    ✓ {module_name} initialized and connected to API client")
                
                if not all_valid:
                    print(f"\n  ✗ FAILED: Module integration validation failed")
                    return False
                
                # Verify orchestrator has expected methods
                expected_methods = [
                    'pull_folder_configuration',
                    'pull_all_folders',
                    'pull_snippets',
                    'pull_complete_configuration',
                    'get_pull_report'
                ]
                
                missing_methods = []
                for method_name in expected_methods:
                    if not hasattr(orchestrator, method_name):
                        missing_methods.append(method_name)
                
                if missing_methods:
                    print(f"\n  ✗ FAILED: Orchestrator missing methods: {', '.join(missing_methods)}")
                    return False
                
                print(f"\n  ✓ All capture modules initialized and integrated correctly")
                print(f"  ✓ Orchestrator has all expected methods")
                
            except Exception as e:
                print(f"  ✗ FAILED: Integration test error: {e}")
                print(f"    Error type: {type(e).__name__}")
                from prisma.error_logger import error_logger
                error_logger.log_capture_error(
                    "test_integration",
                    "module integration",
                    e
                )
                import traceback
                print("\n    Full traceback:")
                traceback.print_exc()
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    # Set up output file
    tee, output_file = setup_output_file()
    
    # Initialize error logger
    from prisma.error_logger import error_logger
    error_logger.start_run("Phase 2 Implementation Tests")
    
    try:
        print("\n" + "=" * 60)
        print("Phase 2 Implementation Tests")
        print("=" * 60)
        print(f"\nOutput will be saved to: {os.path.basename(output_file)}")
        print(f"Error log will be saved to: {error_logger.get_log_path()}\n")
        
        # Get credentials
        tsg_id, api_user, api_secret = get_credentials()
        
        # Create API client if credentials provided
        api_client = None
        if tsg_id and api_user and api_secret:
            try:
                from prisma.api_client import PrismaAccessAPIClient
                print("Initializing API client...")
                api_client = PrismaAccessAPIClient(
                    tsg_id=tsg_id,
                    api_user=api_user,
                    api_secret=api_secret
                )
                print("✓ API client initialized successfully\n")
            except Exception as e:
                print(f"⚠ Failed to initialize API client: {e}")
                print("Continuing with structure tests only...\n")
                api_client = None
        
        # All tests enabled with full validation
        # Note: Snippet test moved to position 2 (after folders) since snippets and folders are equivalent containers
        tests = [
            (test_folder_capture, api_client),
            (test_snippet_capture, api_client),  # Moved to test 2 - snippets and folders are equivalent
            (test_rule_capture, api_client),      # Now test 3
            (test_object_capture, api_client),    # Now test 4
            (test_profile_capture, api_client),   # Now test 5
            (test_pull_orchestrator, api_client), # Now test 6
            (test_config_pull, api_client),       # Now test 7
            (test_integration, api_client)        # Now test 8
        ]
        
        results = []
        for test_func, client in tests:
            try:
                result = test_func(client)
                results.append(result)
                if not result:
                    print(f"\n⚠ Test {test_func.__name__} returned False")
            except Exception as e:
                print(f"\n✗ Test {test_func.__name__} crashed: {e}")
                import traceback
                traceback.print_exc()
                results.append(False)
        
        # Summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        passed = sum(results)
        total = len(results)
        print(f"Passed: {passed}/{total}")
        
        if api_client:
            print("\nNote: Tests were run against a real tenant")
        else:
            print("\nNote: Tests were run in structure-only mode (no real API calls)")
        
        # End error logging session
        summary = f"Tests: {passed}/{total} passed"
        error_logger.end_run(summary)
        
        # Check if there are errors in the log
        try:
            error_log_content = error_logger.read_log()
            has_errors = "API ERROR" in error_log_content or "CAPTURE ERROR" in error_log_content
        except Exception:
            error_log_content = ""
            has_errors = False
        
        if passed == total:
            print("\n✓ All tests passed!")
            print(f"\nFull test output saved to: {os.path.basename(output_file)}")
            if has_errors:
                print(f"\n⚠ Note: Some errors were logged to: {error_logger.get_log_path()}")
                print("  (Errors may have been handled gracefully)")
            return 0
        else:
            print(f"\n✗ {total - passed} test(s) failed")
            print(f"\nFull test output saved to: {os.path.basename(output_file)}")
            if has_errors:
                print(f"\n📋 Detailed error log available at: {error_logger.get_log_path()}")
                print("\n" + "=" * 60)
                print("Error Log Summary")
                print("=" * 60)
                # Show last few lines of error log
                log_lines = error_log_content.split('\n')
                if len(log_lines) > 50:
                    print("(Showing last 50 lines of error log)\n")
                    for line in log_lines[-50:]:
                        print(line)
                else:
                    print(error_log_content)
            return 1
    finally:
        tee.close()


if __name__ == "__main__":
    sys.exit(main())
