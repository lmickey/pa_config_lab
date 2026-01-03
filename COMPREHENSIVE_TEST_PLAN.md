# Comprehensive Test Plan for Memory Safety & GUI Stability

## Overview

This document outlines a comprehensive testing strategy to catch memory corruption, threading issues, and other stability problems **before they cause crashes in production**.

## Test Suite Components

### 1. Unit Tests (`tests/test_memory_safety.py`)

**Run:** `pytest tests/test_memory_safety.py -v`

**What it tests:**
- ✅ ConfigItem.to_dict() doesn't create shared references
- ✅ Multiple to_dict() calls are independent
- ✅ Large datasets (200+ items) don't cause shared references
- ✅ ConfigAdapter doesn't create memory issues
- ✅ Configuration objects clean up properly
- ✅ JSON serialization preserves data
- ✅ Thread-safe concurrent operations

**When to run:**
- Before every commit
- In CI/CD pipeline
- After modifying any serialization code

### 2. Static Analysis (`tests/static_analysis_memory.py`)

**Run:** `python3 tests/static_analysis_memory.py`

**What it finds:**
- ❌ Shallow copy issues (`.copy()` on nested structures)
- ❌ Mutable default arguments (`def func(items=[])`)
- ❌ Class-level mutable attributes
- ❌ Missing safe copy in `to_dict()` methods
- ❌ Thread-unsafe patterns in GUI code
- ❌ Print statements in worker threads

**When to run:**
- Before every commit
- As pre-commit hook
- Weekly code audits

### 3. Integration Tests (Existing)

**Run:** `pytest tests/test_integration_*.py -v`

**What it tests:**
- API client integration
- Pull/push workflows
- Dependency resolution
- Infrastructure capture

### 4. GUI Stability Tests (Manual)

**Use:** `python3 run_gui_debug.py`

**What to test:**

#### Test 1: Small Pull
- 1 folder, all types
- Check for crashes
- Verify logs

#### Test 2: Medium Pull
- 3 folders, ignore defaults
- Check memory usage
- Verify no segfaults

#### Test 3: Full Pull
- All folders, all snippets
- Stress test
- Monitor for leaks

## CI/CD Integration

### Pre-Commit Hook

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash

echo "Running memory safety checks..."

# Run static analysis
python3 tests/static_analysis_memory.py
if [ $? -ne 0 ]; then
    echo "❌ Static analysis found issues!"
    echo "Fix issues before committing."
    exit 1
fi

# Run memory safety tests
pytest tests/test_memory_safety.py -v
if [ $? -ne 0 ]; then
    echo "❌ Memory safety tests failed!"
    exit 1
fi

echo "✅ All checks passed!"
exit 0
```

### GitHub Actions Workflow

Create `.github/workflows/memory-safety.yml`:

```yaml
name: Memory Safety Tests

on: [push, pull_request]

jobs:
  memory-safety:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run static analysis
        run: python3 tests/static_analysis_memory.py
      
      - name: Run memory safety tests
        run: pytest tests/test_memory_safety.py -v
      
      - name: Run integration tests
        run: pytest tests/test_integration_*.py -v
```

## Proactive Issue Detection

### Weekly Code Audit

```bash
#!/bin/bash
# Run comprehensive checks

echo "=== WEEKLY CODE AUDIT ==="
echo ""

# 1. Static analysis
echo "1. Running static analysis..."
python3 tests/static_analysis_memory.py > audit_static.log 2>&1
echo "   Results: audit_static.log"
echo ""

# 2. Find all .copy() usages
echo "2. Finding all .copy() calls..."
grep -rn "\.copy()" --include="*.py" . | grep -v "venv\|test\|deepcopy" > audit_shallow_copies.log
echo "   Results: audit_shallow_copies.log"
echo ""

# 3. Find mutable defaults
echo "3. Finding mutable default arguments..."
grep -rn "def.*=\s*\[" --include="*.py" . | grep -v "venv\|test" > audit_mutable_defaults.log
echo "   Results: audit_mutable_defaults.log"
echo ""

# 4. Find print statements
echo "4. Finding print statements..."
grep -rn "print(" --include="*.py" gui/ prisma/ config/ | grep -v "test" > audit_prints.log
echo "   Results: audit_prints.log"
echo ""

echo "=== AUDIT COMPLETE ==="
echo "Review log files for potential issues."
```

### Performance Monitoring

```python
# tests/test_performance.py

import pytest
import time
import tracemalloc


def test_large_config_performance():
    """Test that large config conversions don't leak memory."""
    from config.models.containers import Configuration, FolderConfig
    from config.models.base import ConfigItem
    from gui.config_adapter import ConfigAdapter
    
    tracemalloc.start()
    
    # Create large configuration
    config = Configuration(source_tsg="test", load_type="test")
    for folder_idx in range(10):
        folder = FolderConfig(name=f"Folder{folder_idx}")
        for item_idx in range(100):  # 1000 items total
            item = ConfigItem({
                'name': f'item-{folder_idx}-{item_idx}',
                'data': ['a', 'b', 'c'] * 10  # Nested lists
            })
            folder.add_item(item)
        config.folders[f"Folder{folder_idx}"] = folder
    
    # Measure conversion time
    start = time.time()
    dict_config = ConfigAdapter.to_dict(config)
    duration = time.time() - start
    
    # Check performance
    assert duration < 2.0, f"Conversion took {duration}s (>2s)"
    
    # Check memory
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    # Peak should be < 50MB
    assert peak < 50 * 1024 * 1024, f"Peak memory {peak / 1024 / 1024}MB (>50MB)"
```

## Known Issues & Fixes

### Issue Tracker

| Issue | Severity | Status | Fix |
|-------|----------|--------|-----|
| Shallow copy in ConfigItem.to_dict() | CRITICAL | ✅ Fixed | JSON serialization |
| Print statements in workers | HIGH | ✅ Fixed | Replaced with logging |
| QTimer cross-thread access | HIGH | ✅ Fixed | QueuedConnection |
| Worker thread cleanup | HIGH | ✅ Fixed | deleteLater() |
| Deep copy of Configuration | HIGH | ✅ Fixed | Removed deep copy |

### Remaining Issues (From Static Analysis)

See `tests/static_analysis_memory.py` output for current issues.

**Priority fixes:**
1. ConfigAdapter.to_dict() - uses dict comprehension, might need JSON
2. Workflow to_dict() methods - need safe copy implementation
3. Shallow copies in pull modules - need review

## Testing Checklist

### Before Every Commit

- [ ] Run static analysis: `python3 tests/static_analysis_memory.py`
- [ ] Run memory tests: `pytest tests/test_memory_safety.py -v`
- [ ] No new shallow copies added
- [ ] No new print statements in GUI/workers
- [ ] All new to_dict() methods use JSON serialization

### Before Release

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Static analysis clean (or issues documented)
- [ ] GUI stress test (1000+ items)
- [ ] Memory profiling shows no leaks
- [ ] No crashes in 10+ full pulls

### After Bug Fix

- [ ] Add test that reproduces the bug
- [ ] Verify test fails before fix
- [ ] Verify test passes after fix
- [ ] Add to static analysis if pattern-based
- [ ] Document in KNOWN_ISSUES.md

## Quick Commands

```bash
# Run all tests
pytest tests/ -v

# Run only memory safety
pytest tests/test_memory_safety.py -v

# Run static analysis
python3 tests/static_analysis_memory.py

# Run GUI in debug mode
python3 run_gui_debug.py

# Check for shallow copies
grep -rn "\.copy()" --include="*.py" config/ gui/ prisma/ | grep -v "venv\|test\|deepcopy"

# Check for print statements
grep -rn "print(" --include="*.py" gui/ prisma/ config/ | grep -v "test\|#"

# Run performance test
pytest tests/test_performance.py -v -s
```

## Continuous Improvement

### Monthly Review

1. Review all static analysis warnings
2. Update tests for new patterns
3. Add tests for recent bugs
4. Profile memory usage trends
5. Update this document

### Metrics to Track

- Number of static analysis issues (goal: decrease over time)
- Test coverage (goal: >80% for critical paths)
- GUI crash rate (goal: 0 crashes/week)
- Memory usage trends (goal: stable)
- Test execution time (goal: <5 min)

## Resources

- `SHALLOW_COPY_BUG.md` - Deep dive on shallow copy issue
- `GUI_STABILITY_REVIEW.md` - All stability fixes
- `LOGGING_GUIDELINES.md` - Logging best practices
- `TESTING_WORKFLOW.md` - Manual testing procedures

## Success Criteria

✅ **Stable Release** when:
1. All automated tests pass
2. Static analysis shows 0 critical issues
3. Manual GUI testing: 10 consecutive pulls without crash
4. Memory usage stays below 500MB
5. No segfaults in normal operation

---

**Last Updated:** 2026-01-02
**Test Suite Version:** 1.0
**Status:** Active
