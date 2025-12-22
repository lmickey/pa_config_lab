# Pull Worker Method Name Fix

## Issue

Pull operation was failing with error:
```
Pull operation failed: 'PullOrchestrator' object has no attribute 'pull_all_configuration'
```

## Root Cause

The `PullWorker` in `gui/workers.py` was calling `orchestrator.pull_all_configuration()`, but the actual method name in `PullOrchestrator` is `pull_complete_configuration()`.

## Fix

Changed `gui/workers.py` line ~55:

**Before:**
```python
self.config = orchestrator.pull_all_configuration(
    include_defaults=not self.filter_defaults,
    include_snippets=self.options.get("snippets", True),
    include_objects=self.options.get("objects", True),
    include_profiles=self.options.get("profiles", True),
)
```

**After:**
```python
self.config = orchestrator.pull_complete_configuration(
    include_defaults=not self.filter_defaults,
    include_snippets=self.options.get("snippets", True),
    include_objects=self.options.get("objects", True),
    include_profiles=self.options.get("profiles", True),
)
```

## Status

✅ Fixed - Method name corrected  
✅ Syntax validated  
✅ GUI launches successfully  

Pull configuration should now work correctly!
