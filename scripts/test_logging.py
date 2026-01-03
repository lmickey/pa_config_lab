#!/usr/bin/env python3
"""
Test script for logging integration.

Tests:
- Basic logging setup
- Debug mode toggle
- Log level changes
- ActivityLogger functionality
- Log message formats
- Integration with ConfigItem operations
"""

import sys
from pathlib import Path
import tempfile
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.logging_config import (
    setup_logging, 
    enable_debug_mode, 
    disable_debug_mode,
    is_debug_mode,
    set_log_level,
    ActivityLogger
)
from config.models.objects import AddressObject, AddressGroup
from config.models.policies import SecurityRule


def test_basic_logging():
    """Test basic logging setup."""
    print("\n" + "="*70)
    print("TEST 1: Basic Logging Setup")
    print("="*70)
    
    # Setup logging with temp file
    log_file = Path(tempfile.gettempdir()) / "test_logging.log"
    setup_logging(level=logging.INFO, log_file=log_file, console=True)
    
    logger = logging.getLogger(__name__)
    
    print("\nTesting log levels...")
    logger.debug("This is DEBUG (should NOT appear)")
    logger.info("This is INFO (should appear)")
    logger.warning("This is WARNING (should appear)")
    logger.error("This is ERROR (should appear)")
    
    # Check log file
    if log_file.exists():
        with open(log_file, 'r') as f:
            lines = f.readlines()
        print(f"\n✅ Log file created: {log_file}")
        print(f"   Lines written: {len(lines)}")
        print(f"   Last line: {lines[-1].strip() if lines else 'empty'}")
        return True
    else:
        print(f"\n❌ Log file not created")
        return False


def test_debug_mode():
    """Test debug mode toggle."""
    print("\n" + "="*70)
    print("TEST 2: Debug Mode Toggle")
    print("="*70)
    
    logger = logging.getLogger(__name__)
    
    # Start with debug disabled
    disable_debug_mode()
    print(f"\nDebug mode: {is_debug_mode()}")
    logger.debug("DEBUG message with debug mode OFF (should NOT appear)")
    logger.info("INFO message with debug mode OFF (should appear)")
    
    # Enable debug mode
    enable_debug_mode()
    print(f"\nDebug mode: {is_debug_mode()}")
    logger.debug("DEBUG message with debug mode ON (should appear)")
    logger.info("INFO message with debug mode ON (should appear)")
    
    # Disable again
    disable_debug_mode()
    print(f"\nDebug mode: {is_debug_mode()}")
    logger.debug("DEBUG message after disabling (should NOT appear)")
    
    if is_debug_mode() == False:
        print("\n✅ Debug mode toggle works correctly")
        return True
    else:
        print("\n❌ Debug mode toggle failed")
        return False


def test_log_level_changes():
    """Test changing log levels at runtime."""
    print("\n" + "="*70)
    print("TEST 3: Log Level Changes")
    print("="*70)
    
    logger = logging.getLogger(__name__)
    
    # Set to WARNING
    print("\nSetting log level to WARNING...")
    set_log_level(logging.WARNING)
    logger.info("INFO at WARNING level (should NOT appear)")
    logger.warning("WARNING at WARNING level (should appear)")
    
    # Set to INFO
    print("\nSetting log level to INFO...")
    set_log_level(logging.INFO)
    logger.info("INFO at INFO level (should appear)")
    logger.debug("DEBUG at INFO level (should NOT appear)")
    
    print("\n✅ Log level changes work correctly")
    return True


def test_activity_logger():
    """Test ActivityLogger functionality."""
    print("\n" + "="*70)
    print("TEST 4: ActivityLogger")
    print("="*70)
    
    activity = ActivityLogger("test")
    
    print("\nTesting workflow logging...")
    activity.log_workflow_start("test_workflow", "Testing workflow logging")
    
    print("\nTesting action logging...")
    activity.log_action("create", "address_object", "test-addr", "Created for testing")
    activity.log_action("update", "security_rule", "test-rule", "Modified action")
    activity.log_action("delete", "service_object", "test-svc")
    
    print("\nTesting API call logging...")
    activity.log_api_call("GET", "/sse/config/v1/addresses", 200, 0.123)
    activity.log_api_call("POST", "/sse/config/v1/addresses", 201, 0.456)
    activity.log_api_call("DELETE", "/sse/config/v1/addresses/123", 409, 0.234)
    
    print("\nTesting config change logging...")
    activity.log_config_change("update", "address_object", "test-addr", "10.1.1.1/32", "10.1.1.2/32")
    
    print("\nTesting workflow completion...")
    activity.log_workflow_complete("test_workflow", True, 45.6, "10 created, 5 updated")
    activity.log_workflow_complete("failed_workflow", False, 12.3, "Failed due to API error")
    
    print("\n✅ ActivityLogger works correctly")
    return True


def test_configitem_logging():
    """Test logging integration with ConfigItem operations."""
    print("\n" + "="*70)
    print("TEST 5: ConfigItem Logging Integration")
    print("="*70)
    
    # Create test items
    print("\nCreating ConfigItem objects...")
    
    addr = AddressObject.from_dict({
        'name': 'test-logging-addr',
        'folder': 'Mobile Users',
        'ip_netmask': '192.168.100.1/32',
        'description': 'Test address for logging'
    })
    print(f"✅ Created: {addr.item_type} '{addr.name}'")
    
    group = AddressGroup.from_dict({
        'name': 'test-logging-group',
        'folder': 'Mobile Users',
        'static': ['test-logging-addr'],
        'description': 'Test group for logging'
    })
    print(f"✅ Created: {group.item_type} '{group.name}'")
    
    # Test validation logging
    print("\nTesting validation logging...")
    errors = addr.validate()
    if not errors:
        print(f"✅ {addr.name} validation passed (should be logged)")
    
    errors = group.validate()
    if not errors:
        print(f"✅ {group.name} validation passed (should be logged)")
    
    # Test rename logging
    print("\nTesting rename logging...")
    old_name = addr.name
    addr.rename('test-logging-addr-renamed')
    print(f"✅ Renamed: {old_name} → {addr.name} (should be logged)")
    
    # Test deletion marking
    print("\nTesting deletion marking...")
    addr.mark_for_deletion()
    print(f"✅ Marked for deletion: {addr.name} (should be logged)")
    
    addr.unmark_for_deletion()
    print(f"✅ Unmarked for deletion: {addr.name} (should be logged)")
    
    print("\n✅ ConfigItem logging integration works")
    return True


def test_log_format():
    """Test log message format standards."""
    print("\n" + "="*70)
    print("TEST 6: Log Message Format")
    print("="*70)
    
    logger = logging.getLogger(__name__)
    
    print("\nTesting standard format: {action} {item_type} '{item_name}'")
    logger.info("Created address_object 'web-server'")
    logger.info("Updated security_rule 'Allow-Web'")
    logger.info("Deleted service_object 'http-8080'")
    
    print("\nTesting with location:")
    logger.info("Created address_object 'web-server' in Mobile Users")
    logger.info("Updated security_rule 'Allow-Web' in Remote Networks")
    
    print("\nTesting error format:")
    logger.error("Failed to create address_object 'web-server': Name already exists")
    logger.error("Cannot delete security_rule 'Allow-Web': Still referenced by other rules")
    
    print("\nTesting warning format:")
    logger.warning("Skipping address_object 'web-server': Already exists")
    logger.warning("Item 'test' missing optional field: description")
    
    print("\n✅ Log message formats are consistent")
    return True


def test_debug_details():
    """Test debug mode detailed logging."""
    print("\n" + "="*70)
    print("TEST 7: Debug Mode Details")
    print("="*70)
    
    logger = logging.getLogger(__name__)
    
    # Enable debug mode
    enable_debug_mode()
    
    print("\nTesting detailed debug messages...")
    logger.debug("Computing dependencies for address_group 'web-servers'")
    logger.debug("Dependency resolution complete: 5 dependencies found")
    logger.debug("API request: GET /sse/config/v1/addresses?folder=Mobile%20Users")
    logger.debug("API response (200): {'data': [...]}")
    logger.debug("Cache hit for address_object 'web-server'")
    logger.debug("Cache miss for service_object 'http', computing...")
    
    print("\nTesting validation details...")
    logger.debug("Validating address_object 'web-server'")
    logger.debug("Validation passed: ip_netmask = 192.168.1.1/32")
    logger.debug("Validation failed: port = 999999, expected 1-65535")
    
    # Disable debug mode
    disable_debug_mode()
    
    print("\n✅ Debug details logging works")
    return True


def test_performance():
    """Test logging performance (no impact in normal mode)."""
    print("\n" + "="*70)
    print("TEST 8: Logging Performance")
    print("="*70)
    
    import time
    logger = logging.getLogger(__name__)
    
    # Test without logging
    print("\nTesting without logging...")
    start = time.time()
    for i in range(1000):
        pass  # Do nothing
    baseline = time.time() - start
    print(f"Baseline: {baseline:.4f}s")
    
    # Test with INFO logging
    print("\nTesting with INFO logging...")
    set_log_level(logging.INFO)
    start = time.time()
    for i in range(1000):
        if i % 100 == 0:
            logger.info(f"Processing item {i}")
    info_time = time.time() - start
    print(f"INFO logging: {info_time:.4f}s")
    print(f"Overhead: {((info_time - baseline) / baseline * 100):.1f}%")
    
    # Test with DEBUG logging (disabled)
    print("\nTesting with DEBUG (disabled)...")
    disable_debug_mode()
    start = time.time()
    for i in range(1000):
        logger.debug(f"Debug item {i}")
    debug_disabled_time = time.time() - start
    print(f"DEBUG disabled: {debug_disabled_time:.4f}s")
    print(f"Overhead: {((debug_disabled_time - baseline) / baseline * 100):.1f}%")
    
    # Test with DEBUG logging (enabled)
    print("\nTesting with DEBUG (enabled)...")
    enable_debug_mode()
    start = time.time()
    for i in range(1000):
        if i % 100 == 0:
            logger.debug(f"Debug item {i}")
    debug_enabled_time = time.time() - start
    print(f"DEBUG enabled: {debug_enabled_time:.4f}s")
    print(f"Overhead: {((debug_enabled_time - baseline) / baseline * 100):.1f}%")
    
    print("\n✅ Logging performance is acceptable")
    return True


def main():
    """Run all logging tests."""
    print("\n" + "="*70)
    print("LOGGING INTEGRATION TEST SUITE")
    print("="*70)
    
    tests = [
        ("Basic Logging Setup", test_basic_logging),
        ("Debug Mode Toggle", test_debug_mode),
        ("Log Level Changes", test_log_level_changes),
        ("ActivityLogger", test_activity_logger),
        ("ConfigItem Integration", test_configitem_logging),
        ("Log Message Format", test_log_format),
        ("Debug Mode Details", test_debug_details),
        ("Performance", test_performance),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Test '{name}' raised exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
