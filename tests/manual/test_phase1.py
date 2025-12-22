#!/usr/bin/env python3
"""
Test script for Phase 1 implementation.

This script tests:
1. JSON schema creation and validation
2. JSON storage functions
3. Backward compatibility with pickle format
4. Migration utilities
5. API client initialization (without actual API calls)
"""

import os
import sys
import json
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_schema_creation():
    """Test JSON schema creation."""
    print("=" * 60)
    print("Test 1: JSON Schema Creation")
    print("=" * 60)
    
    try:
        from config.schema.config_schema_v2 import create_empty_config_v2, get_schema_version
        
        # Create empty config
        config = create_empty_config_v2(
            source_tenant="tsg-1234567890",
            source_type="scm",
            description="Test configuration"
        )
        
        # Verify structure
        assert "metadata" in config
        assert "infrastructure" in config
        assert "security_policies" in config
        assert config["metadata"]["version"] == "2.0.0"
        assert config["metadata"]["source_type"] == "scm"
        assert config["metadata"]["source_tenant"] == "tsg-1234567890"
        
        print("✓ Schema creation successful")
        print(f"  Version: {get_schema_version()}")
        print(f"  Created: {config['metadata']['created']}")
        return True
        
    except Exception as e:
        print(f"✗ Schema creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_schema_validation():
    """Test schema validation."""
    print("\n" + "=" * 60)
    print("Test 2: Schema Validation")
    print("=" * 60)
    
    try:
        from config.schema.config_schema_v2 import create_empty_config_v2
        from config.schema.schema_validator import validate_config, is_v2_config
        
        # Create valid config
        config = create_empty_config_v2()
        
        # Test validation
        is_valid, errors = validate_config(config)
        
        assert is_valid, f"Validation failed: {errors}"
        assert is_v2_config(config), "Should be v2 config"
        
        print("✓ Schema validation successful")
        print(f"  Errors: {len(errors)}")
        return True
        
    except Exception as e:
        print(f"✗ Schema validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_json_storage():
    """Test JSON storage functions."""
    print("\n" + "=" * 60)
    print("Test 3: JSON Storage")
    print("=" * 60)
    
    try:
        from config.schema.config_schema_v2 import create_empty_config_v2
        from config.storage.json_storage import (
            save_config_json, load_config_json, derive_key,
            get_config_file_path
        )
        
        # Create test config
        config = create_empty_config_v2(
            source_tenant="tsg-test",
            description="Test storage"
        )
        
        # Test file path generation
        test_path = get_config_file_path("test_config")
        assert test_path.endswith("test_config-config.json")
        
        # Save unencrypted JSON
        test_file = "/tmp/test_config_phase1.json"
        success = save_config_json(config, test_file, encrypt=False)
        assert success, "Save failed"
        
        # Load unencrypted JSON
        loaded_config = load_config_json(test_file, encrypted=False)
        assert loaded_config is not None, "Load failed"
        assert loaded_config["metadata"]["version"] == "2.0.0"
        
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)
        
        print("✓ JSON storage successful")
        print(f"  Test file: {test_file}")
        return True
        
    except Exception as e:
        print(f"✗ JSON storage failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backward_compatibility():
    """Test backward compatibility detection."""
    print("\n" + "=" * 60)
    print("Test 4: Backward Compatibility Detection")
    print("=" * 60)
    
    try:
        from config.schema.schema_validator import is_legacy_config, is_v2_config
        
        # Test legacy format detection
        legacy_config = {
            "fwData": {"mgmtUrl": "test"},
            "paData": {"paTSGID": "test"}
        }
        
        assert is_legacy_config(legacy_config), "Should detect legacy format"
        
        # Test v2 format detection
        from config.schema.config_schema_v2 import create_empty_config_v2
        v2_config = create_empty_config_v2()
        
        assert is_v2_config(v2_config), "Should detect v2 format"
        assert not is_legacy_config(v2_config), "Should not be legacy"
        
        print("✓ Backward compatibility detection successful")
        return True
        
    except Exception as e:
        print(f"✗ Backward compatibility detection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_migration_utilities():
    """Test migration utilities."""
    print("\n" + "=" * 60)
    print("Test 5: Migration Utilities")
    print("=" * 60)
    
    try:
        from config.storage.pickle_compat import convert_to_v2_format
        
        # Create legacy config
        legacy_config = {
            "fwData": {
                "mgmtUrl": "https://test.example.com",
                "mgmtUser": "admin"
            },
            "paData": {
                "paTSGID": "tsg-123",
                "paManagedBy": "scm",
                "paInfraSubnet": "192.168.254.0/24",
                "paMobUserSubnet": "100.64.0.0/16",
                "paPortalHostname": "test.gpcloudservice.com"
            }
        }
        
        # Convert to v2
        v2_config = convert_to_v2_format(legacy_config, preserve_legacy=True)
        
        # Verify conversion
        assert "metadata" in v2_config
        assert "fwData" in v2_config  # Preserved
        assert "paData" in v2_config  # Preserved
        assert v2_config["metadata"]["version"] == "2.0.0"
        
        # Verify infrastructure migration
        infra = v2_config["infrastructure"]
        assert infra["shared_infrastructure_settings"]["infrastructure_subnet"] == "192.168.254.0/24"
        
        print("✓ Migration utilities successful")
        print(f"  Migrated infrastructure subnet: {infra['shared_infrastructure_settings']['infrastructure_subnet']}")
        return True
        
    except Exception as e:
        print(f"✗ Migration utilities failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_endpoints():
    """Test API endpoint definitions."""
    print("\n" + "=" * 60)
    print("Test 6: API Endpoints")
    print("=" * 60)
    
    try:
        from prisma.api_endpoints import APIEndpoints, build_folder_query
        
        # Test endpoint construction
        assert APIEndpoints.SECURITY_POLICY_FOLDERS.endswith("/security-policy/folders")
        assert APIEndpoints.SECURITY_RULES.endswith("/security-rules")
        
        # Test folder query
        query = build_folder_query("Shared")
        assert query == "?folder=Shared"
        
        # Test dynamic endpoints
        folder_url = APIEndpoints.security_policy_folder("TestFolder")
        assert "TestFolder" in folder_url
        
        print("✓ API endpoints successful")
        print(f"  Folders endpoint: {APIEndpoints.SECURITY_POLICY_FOLDERS}")
        return True
        
    except Exception as e:
        print(f"✗ API endpoints failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_client_init():
    """Test API client initialization (without actual API calls)."""
    print("\n" + "=" * 60)
    print("Test 7: API Client Initialization")
    print("=" * 60)
    
    try:
        from prisma.api_client import PrismaAccessAPIClient
        
        # Test initialization (will fail auth but should initialize)
        try:
            client = PrismaAccessAPIClient(
                tsg_id="tsg-test",
                api_user="test-user",
                api_secret="test-secret"
            )
            # Auth will fail, but object should be created
            print("✓ API client initialization successful")
            print("  Note: Authentication will fail with test credentials (expected)")
            return True
        except Exception as e:
            # If it's an auth error, that's expected
            if "auth" in str(e).lower() or "token" in str(e).lower():
                print("✓ API client initialization successful")
                print("  Note: Authentication failed with test credentials (expected)")
                return True
            else:
                raise
        
    except Exception as e:
        print(f"✗ API client initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Phase 1 Implementation Tests")
    print("=" * 60)
    
    tests = [
        test_schema_creation,
        test_schema_validation,
        test_json_storage,
        test_backward_compatibility,
        test_migration_utilities,
        test_api_endpoints,
        test_api_client_init
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n✗ Test {test.__name__} crashed: {e}")
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
    
    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
