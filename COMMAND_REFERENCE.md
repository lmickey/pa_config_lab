# Quick Command Reference - Memory Safety Testing

## 🚀 Quick Commands

### Before Every Commit (30 seconds)

```bash
./check_memory_safety.sh
```

Or manually:

```bash
# Quick critical issues only (10 sec)
python3 tests/static_analysis_memory.py | grep CRITICAL

# Full memory safety tests (30 sec)
pytest tests/test_memory_safety.py -v --no-cov
```

---

## 🧪 Testing Commands

### Automated Tests

```bash
# All memory safety tests
pytest tests/test_memory_safety.py -v --no-cov

# Single test
pytest tests/test_memory_safety.py::TestShallowCopyDetection::test_configitem_to_dict_no_shared_references -v

# All tests (full suite)
pytest tests/ -v --no-cov
```

### Static Analysis

```bash
# Full analysis
python3 tests/static_analysis_memory.py

# Critical only
python3 tests/static_analysis_memory.py | grep CRITICAL

# High priority
python3 tests/static_analysis_memory.py | grep -E "(CRITICAL|HIGH)"

# Summary only
python3 tests/static_analysis_memory.py | tail -20
```

### GUI Testing

```bash
# Debug mode (with crash diagnostics)
python3 run_gui_debug.py

# Normal mode
python3 run_gui.py

# Check logs
tail -50 logs/activity.log
cat logs/gui_crashes.log
```

---

## 🔍 Code Scanning

### Find Shallow Copies

```bash
# In your code
grep -rn "\.copy()" config/ gui/ prisma/ | grep -v "venv\|test\|deepcopy"

# Show context
grep -rn -B2 -A2 "\.copy()" config/ gui/ prisma/ | grep -v "venv\|test\|deepcopy"
```

### Find Print Statements

```bash
# In GUI/workers
grep -rn "print(" gui/ | grep -v "test\|#"

# In all code
grep -rn "^\s*print(" . --include="*.py" | grep -v "venv\|test"
```

### Find Mutable Defaults

```bash
# List default arguments
grep -rn "def.*=\s*\[" --include="*.py" . | grep -v "venv\|test"

# Dict defaults
grep -rn "def.*=\s*\{" --include="*.py" . | grep -v "venv\|test"
```

### Find to_dict Methods

```bash
# All to_dict implementations
grep -rn "def to_dict" --include="*.py" . | grep -v "venv\|test"

# Check if they use safe copy
grep -rn -A5 "def to_dict" config/ gui/ prisma/ | grep -E "(json\.loads|deepcopy)"
```

---

## 📊 Log Analysis

### Activity Logs

```bash
# Latest log
tail -50 logs/activity.log

# Errors only
grep ERROR logs/activity.log

# Warnings
grep WARNING logs/activity.log

# Debug entries (if debug enabled)
grep DEBUG logs/activity.log

# Follow live
tail -f logs/activity.log
```

### Crash Logs

```bash
# View crash log
cat logs/gui_crashes.log

# Last crash
tail -100 logs/gui_crashes.log

# Search for specific error
grep "double free" logs/gui_crashes.log
grep "segfault" logs/gui_crashes.log
```

---

## 🎯 Performance Testing

### Memory Usage

```python
# Add to test file
import tracemalloc

tracemalloc.start()
# ... your code ...
current, peak = tracemalloc.get_traced_memory()
print(f"Current: {current / 1024 / 1024:.2f} MB")
print(f"Peak: {peak / 1024 / 1024:.2f} MB")
tracemalloc.stop()
```

### Timing

```python
import time

start = time.time()
# ... your code ...
duration = time.time() - start
print(f"Duration: {duration:.2f}s")
```

---

## 🔧 Development Workflow

### Option A: Quick (for small changes)

```bash
python3 tests/static_analysis_memory.py | grep CRITICAL
# If clean, commit
```

### Option B: Standard (before commit)

```bash
./check_memory_safety.sh
# If passes, commit
```

### Option C: Thorough (before PR)

```bash
# All automated tests
pytest tests/ -v --no-cov

# Manual GUI test
python3 run_gui_debug.py
# Do a config pull
# Check logs/activity.log

# If all pass, create PR
```

---

## 📚 Documentation Quick Access

```bash
# Test strategy
cat TEST_INFRASTRUCTURE_SUMMARY.md

# Quick guide
cat QUICK_TEST_GUIDE.md

# Root cause analysis
cat SHALLOW_COPY_BUG.md

# Complete plan
cat COMPREHENSIVE_TEST_PLAN.md
```

---

## 🎯 Troubleshooting

### GUI Crashes

```bash
# Run in debug mode
python3 run_gui_debug.py

# Check crash log
cat logs/gui_crashes.log

# Check activity log
tail -100 logs/activity.log
```

### Test Failures

```bash
# Run single test with full output
pytest tests/test_memory_safety.py::TestName::test_name -v -s

# Show full traceback
pytest tests/test_memory_safety.py --tb=long

# Show stdout
pytest tests/test_memory_safety.py -v -s
```

### Static Analysis Issues

```bash
# Show only critical
python3 tests/static_analysis_memory.py | grep -A10 CRITICAL

# Check specific file
grep -rn "\.copy()" path/to/file.py
```

---

## ⚡ One-Liners

```bash
# Quick memory check
python3 tests/static_analysis_memory.py | grep CRITICAL && pytest tests/test_memory_safety.py -v --no-cov

# Find all shallow copies in config/
grep -rn "\.copy()" config/ | grep -v "deepcopy\|json\.loads"

# Count print statements in GUI
grep -r "print(" gui/ | grep -v "#\|test" | wc -l

# Find recent errors in logs
tail -1000 logs/activity.log | grep ERROR

# GUI memory usage (while running)
ps aux | grep python | grep gui

# Quick test count
pytest tests/test_memory_safety.py --collect-only | grep "test session starts" -A2
```

---

## 🎉 Success Indicators

### All Green ✅

```bash
./check_memory_safety.sh
# Output: ✅ ALL CHECKS PASSED - SAFE TO COMMIT!
```

### GUI Running Stable ✅

- No segfaults after 10 consecutive pulls
- Memory usage stable (<500MB)
- No errors in logs/activity.log
- Clean logs/gui_crashes.log

---

**TL;DR:** Run `./check_memory_safety.sh` before committing!

