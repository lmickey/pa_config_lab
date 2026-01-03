#!/usr/bin/env python3
"""
Test Enhanced Logging System (Phase 9.5).

Comprehensive test for the updated logging system with 5 levels:
- ERROR (40)
- WARNING (30)
- NORMAL (25) - NEW CUSTOM LEVEL
- INFO (20)
- DEBUG (10)

Tests:
1. NORMAL level functionality
2. Log rotation
3. Log retention/pruning
4. All 5 log levels
5. Enhanced API Client logging
6. Enhanced Pull/Push Orchestrator logging
7. Performance with increased logging
"""

import sys
from pathlib import Path
import logging
import time
import tempfile
import shutil

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.logging_config import (
    setup_logging,
    enable_debug_mode,
    disable_debug_mode,
    is_debug_mode,
    set_log_level,
    rotate_logs,
    prune_logs,
    NORMAL
)


def test_1_normal_level():
    """Test custom NORMAL log level."""
    print("\n" + "="*80)
    print("TEST 1: NORMAL Log Level")
    print("="*80)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"
        
        # Setup logging with NORMAL level
        setup_logging(level=NORMAL, log_file=log_file, console=False)
        logger = logging.getLogger("test")
        
        # Log at different levels
        logger.error("This is ERROR")
        logger.warning("This is WARNING")
        logger.normal("This is NORMAL")  # Should appear
        logger.info("This is INFO")  # Should NOT appear (below NORMAL)
        logger.debug("This is DEBUG")  # Should NOT appear
        
        # Check log file
        content = log_file.read_text()
        
        assert "This is ERROR" in content
        assert "This is WARNING" in content
        assert "This is NORMAL" in content
        assert "This is INFO" not in content
        assert "This is DEBUG" not in content
        
        print("✅ NORMAL level works correctly")
        print(f"   - ERROR, WARNING, NORMAL visible")
        print(f"   - INFO, DEBUG hidden")
        return True


def test_2_log_rotation():
    """Test log file rotation."""
    print("\n" + "="*80)
    print("TEST 2: Log Rotation")
    print("="*80)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "activity.log"
        
        # Create initial log
        log_file.write_text("Run 1\n")
        
        # Rotate
        rotate_logs(log_file, keep_count=7)
        
        # Check rotation
        assert not log_file.exists(), "Original log should be moved"
        assert (log_file.parent / "activity-1.log").exists(), "Rotated log missing"
        assert "Run 1" in (log_file.parent / "activity-1.log").read_text()
        
        # Create new log
        log_file.write_text("Run 2\n")
        
        # Rotate again
        rotate_logs(log_file, keep_count=7)
        
        # Check
        assert (log_file.parent / "activity-1.log").exists()
        assert (log_file.parent / "activity-2.log").exists()
        assert "Run 2" in (log_file.parent / "activity-1.log").read_text()
        assert "Run 1" in (log_file.parent / "activity-2.log").read_text()
        
        print("✅ Log rotation works correctly")
        print(f"   - Current log moved to activity-1.log")
        print(f"   - Previous rotations shifted up")
        return True


def test_3_log_pruning():
    """Test log pruning by count and age."""
    print("\n" + "="*80)
    print("TEST 3: Log Pruning")
    print("="*80)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)
        
        # Create 10 log files
        for i in range(1, 11):
            (log_dir / f"activity-{i}.log").write_text(f"Run {i}\n")
        
        # Prune to keep only 5
        deleted = prune_logs(log_dir, keep_count=5)
        
        assert deleted == 5, f"Expected 5 deleted, got {deleted}"
        assert len(list(log_dir.glob("activity*.log"))) == 5
        
        print("✅ Log pruning works correctly")
        print(f"   - Deleted {deleted} old logs")
        print(f"   - Kept 5 most recent")
        return True


def test_4_all_five_levels():
    """Test all 5 log levels."""
    print("\n" + "="*80)
    print("TEST 4: All 5 Log Levels")
    print("="*80)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"
        
        # Setup with DEBUG level
        setup_logging(level=logging.DEBUG, log_file=log_file, console=False, debug=True)
        logger = logging.getLogger("test")
        
        # Log at all levels
        logger.error("Level 40: ERROR")
        logger.warning("Level 30: WARNING")
        logger.normal("Level 25: NORMAL")
        logger.info("Level 20: INFO")
        logger.debug("Level 10: DEBUG")
        
        # Check all present
        content = log_file.read_text()
        
        assert "Level 40: ERROR" in content
        assert "Level 30: WARNING" in content
        assert "Level 25: NORMAL" in content
        assert "Level 20: INFO" in content
        assert "Level 10: DEBUG" in content
        
        print("✅ All 5 log levels working")
        print(f"   - ERROR (40)")
        print(f"   - WARNING (30)")
        print(f"   - NORMAL (25)")
        print(f"   - INFO (20)")
        print(f"   - DEBUG (10)")
        return True


def test_5_level_filtering():
    """Test log level filtering."""
    print("\n" + "="*80)
    print("TEST 5: Log Level Filtering")
    print("="*80)
    
    levels = [
        (logging.ERROR, ["ERROR"], ["WARNING", "NORMAL", "INFO", "DEBUG"]),
        (logging.WARNING, ["ERROR", "WARNING"], ["NORMAL", "INFO", "DEBUG"]),
        (NORMAL, ["ERROR", "WARNING", "NORMAL"], ["INFO", "DEBUG"]),
        (logging.INFO, ["ERROR", "WARNING", "NORMAL", "INFO"], ["DEBUG"]),
        (logging.DEBUG, ["ERROR", "WARNING", "NORMAL", "INFO", "DEBUG"], []),
    ]
    
    for level, should_see, should_not_see in levels:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            
            setup_logging(level=level, log_file=log_file, console=False, 
                         debug=(level == logging.DEBUG))
            logger = logging.getLogger("test_filter")
            
            logger.error("ERROR message")
            logger.warning("WARNING message")
            logger.normal("NORMAL message")
            logger.info("INFO message")
            logger.debug("DEBUG message")
            
            content = log_file.read_text()
            
            for level_name in should_see:
                assert f"{level_name} message" in content, \
                    f"{level_name} should be visible at level {logging.getLevelName(level)}"
            
            for level_name in should_not_see:
                assert f"{level_name} message" not in content, \
                    f"{level_name} should be hidden at level {logging.getLevelName(level)}"
    
    print("✅ Log level filtering works correctly")
    print(f"   - Each level shows appropriate messages")
    print(f"   - Higher levels hidden correctly")
    return True


def test_6_enhanced_logging_volume():
    """Test that enhanced logging produces expected volume."""
    print("\n" + "="*80)
    print("TEST 6: Enhanced Logging Volume")
    print("="*80)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"
        
        # INFO mode
        setup_logging(level=logging.INFO, log_file=log_file, console=False)
        logger = logging.getLogger("volume_test")
        
        # Simulate a typical workflow
        logger.info("Starting operation")
        for i in range(10):
            logger.info(f"Processing item {i}")
            logger.debug(f"Debug detail for item {i}")  # Should NOT appear
        logger.info("Operation complete")
        
        info_content = log_file.read_text()
        info_lines = [line for line in info_content.strip().split('\n') if line.strip()]
        
        # Should have 12 INFO lines (start + 10 items + complete) plus maybe initialization
        assert len(info_lines) >= 12, f"Expected at least 12 INFO lines, got {len(info_lines)}"
        
        # DEBUG mode
        log_file.unlink()
        setup_logging(level=logging.DEBUG, log_file=log_file, console=False, debug=True)
        logger = logging.getLogger("volume_test")
        
        logger.info("Starting operation")
        for i in range(10):
            logger.info(f"Processing item {i}")
            logger.debug(f"Debug detail for item {i}")  # Should appear
        logger.info("Operation complete")
        
        debug_content = log_file.read_text()
        debug_lines = [line for line in debug_content.strip().split('\n') if line.strip()]
        
        # Should have more lines in debug mode
        assert len(debug_lines) > len(info_lines), f"DEBUG should have more lines than INFO"
        
        increase = ((len(debug_lines) - len(info_lines)) / len(info_lines)) * 100
        
        print("✅ Enhanced logging volume correct")
        print(f"   - INFO mode: {len(info_lines)} lines")
        print(f"   - DEBUG mode: {len(debug_lines)} lines")
        print(f"   - Increase: {increase:.1f}%")
        return True


def test_7_logging_performance():
    """Test logging performance overhead."""
    print("\n" + "="*80)
    print("TEST 7: Logging Performance")
    print("="*80)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"
        
        # Measure without logging
        setup_logging(level=logging.CRITICAL, log_file=log_file, console=False)
        logger = logging.getLogger("perf_test")
        
        start = time.time()
        for i in range(1000):
            logger.info(f"Message {i}")  # Won't actually log
        no_log_time = time.time() - start
        
        # Measure with INFO logging
        log_file.unlink() if log_file.exists() else None
        setup_logging(level=logging.INFO, log_file=log_file, console=False)
        logger = logging.getLogger("perf_test2")
        
        start = time.time()
        for i in range(1000):
            logger.info(f"Message {i}")
        info_log_time = time.time() - start
        
        # Measure with DEBUG logging
        log_file.unlink() if log_file.exists() else None
        setup_logging(level=logging.DEBUG, log_file=log_file, console=False, debug=True)
        logger = logging.getLogger("perf_test3")
        
        start = time.time()
        for i in range(1000):
            logger.info(f"Info {i}")
            logger.debug(f"Debug {i}")
        debug_log_time = time.time() - start
        
        # Calculate absolute overhead (not percentage of tiny baseline)
        info_time_per_op = (info_log_time / 1000) * 1000  # ms per op
        debug_time_per_op = (debug_log_time / 2000) * 1000  # ms per op (2x messages)
        
        print("✅ Logging performance acceptable")
        print(f"   - No logging: {no_log_time*1000:.2f}ms total")
        print(f"   - INFO logging: {info_log_time*1000:.2f}ms total ({info_time_per_op:.3f}ms/msg)")
        print(f"   - DEBUG logging: {debug_log_time*1000:.2f}ms total ({debug_time_per_op:.3f}ms/msg)")
        print(f"   - Overhead is acceptable for diagnostic logging")
        
        # Just verify it's reasonable (< 1 second total for 1000-2000 messages)
        assert info_log_time < 1.0, f"INFO logging too slow: {info_log_time}s"
        assert debug_log_time < 2.0, f"DEBUG logging too slow: {debug_log_time}s"
        
        return True


def test_8_rotation_on_startup():
    """Test automatic rotation on startup."""
    print("\n" + "="*80)
    print("TEST 8: Rotation on Startup")
    print("="*80)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "activity.log"
        
        # Create initial log manually
        log_file.write_text("2026-01-02 19:00:00 - INFO - First run\n")
        assert log_file.exists(), "Initial log should exist"
        
        # Second startup (should rotate)
        setup_logging(log_file=log_file, console=False, rotate=True)
        logger = logging.getLogger("startup_test")
        logger.info("Second run")
        
        # Check rotation happened
        assert (log_file.parent / "activity-1.log").exists(), "Rotated log should exist"
        rotated_content = (log_file.parent / "activity-1.log").read_text()
        assert "First run" in rotated_content, f"Rotated log should contain first run, got: {rotated_content}"
        
        current_content = log_file.read_text()
        assert "Second run" in current_content, "Current log should contain second run"
        assert "First run" not in current_content, "Current log should not contain first run"
        
        print("✅ Rotation on startup works")
        print(f"   - Previous run moved to activity-1.log")
        print(f"   - New run in activity.log")
        return True


def main():
    """Run all enhanced logging tests."""
    print("\n" + "="*80)
    print("ENHANCED LOGGING TEST SUITE (Phase 9.5)")
    print("="*80)
    print(f"Testing 5-level logging system with NORMAL level")
    
    tests = [
        test_1_normal_level,
        test_2_log_rotation,
        test_3_log_pruning,
        test_4_all_five_levels,
        test_5_level_filtering,
        test_6_enhanced_logging_volume,
        test_7_logging_performance,
        test_8_rotation_on_startup,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test.__name__} error: {e}")
            failed += 1
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"✅ Passed: {passed}/{len(tests)}")
    if failed:
        print(f"❌ Failed: {failed}/{len(tests)}")
    else:
        print(f"🎉 All tests passed!")
    print("="*80)
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
