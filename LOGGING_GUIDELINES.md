# Logging Guidelines - Prisma Access Configuration Lab

## ⚠️ CRITICAL RULE: NO PRINT STATEMENTS

**NEVER use `print()` statements in this codebase!**

### Why?

1. **Segfaults in GUI**: Print statements in QThread workers cause memory corruption and segfaults
2. **Lost Output**: GUI applications don't have stdout/stderr visible
3. **No Control**: Can't adjust verbosity or filter output
4. **No Persistence**: Output is lost when terminal closes

### What to Use Instead

**ALWAYS use the logging module:**

```python
import logging

logger = logging.getLogger(__name__)

# Use appropriate log levels:
logger.error("Something went wrong")      # Errors only
logger.warning("Recoverable issue")        # Warnings
logger.normal("Operation completed")       # Normal operations (custom level)
logger.info("Detailed step information")   # Info
logger.debug("Raw data for debugging")     # Debug mode only
```

## Log Levels

### 1. ERROR (40)
- **When**: Critical failures that prevent operation
- **Examples**: 
  - API authentication failed
  - Configuration file corrupt
  - Network unreachable
- **Visible**: All log levels

### 2. WARNING (30)
- **When**: Recoverable issues, degraded functionality
- **Examples**:
  - API rate limit approaching
  - Missing optional fields
  - Using fallback behavior
- **Visible**: Warning, Normal, Info, Debug

### 3. NORMAL (25) - Custom Level
- **When**: Summary of operations, high-level progress
- **Examples**:
  - "Pull operation started"
  - "Processed 50 items"
  - "Configuration saved"
- **Visible**: Normal, Info, Debug

### 4. INFO (20)
- **When**: Detailed step-by-step information
- **Examples**:
  - "Fetching security rules from folder 'Mobile Users'"
  - "Validating configuration structure"
  - "Creating backup file"
- **Visible**: Info, Debug

### 5. DEBUG (10)
- **When**: Troubleshooting information (enabled only when needed)
- **Examples**:
  - Raw API request/response
  - Decision-making logic
  - Variable values
  - Stack traces
- **Visible**: Debug only (must enable debug mode)

## Usage Patterns

### Basic Logging
```python
import logging

logger = logging.getLogger(__name__)

def some_function():
    logger.info("Starting some_function")
    
    try:
        result = do_something()
        logger.normal(f"Processed {len(result)} items")
        return result
    except Exception as e:
        logger.error(f"Failed to process: {e}")
        raise
```

### Debug Mode Logging
```python
# This only logs when debug mode is enabled
logger.debug(f"API Request: {method} {url}")
logger.debug(f"Request body: {body}")
logger.debug(f"Response: {response}")
```

### Conditional Logging in Loops
```python
# Don't spam logs - use modulo for progress
for i, item in enumerate(items):
    if i % 10 == 0:
        logger.info(f"Progress: {i}/{len(items)}")
    
    # Only log debug for first few
    if i < 3:
        logger.debug(f"Processing item: {item}")
```

### QThread Workers - CRITICAL
```python
class MyWorker(QThread):
    def run(self):
        # ❌ NEVER DO THIS - causes segfault!
        # print("Starting worker")
        
        # ✅ ALWAYS DO THIS
        logger = logging.getLogger(__name__)
        logger.info("Starting worker")
        
        try:
            result = self.do_work()
            logger.normal("Work completed successfully")
        except Exception as e:
            # ❌ NEVER print errors
            # print(f"Error: {e}")
            
            # ✅ ALWAYS log errors
            logger.error(f"Worker error: {e}")
            import traceback
            logger.debug(traceback.format_exc())
```

## Configuration

### GUI Settings
Users can change log level in **Settings → Advanced → Log Level**:
- Error (fewest entries)
- Warning (recoverable issues)
- Normal (summary operations) - **Default**
- Info (detailed steps)
- Debug (everything, troubleshooting)

### Programmatic Configuration
```python
from config.logging_config import setup_logging, enable_debug_mode, set_log_level
import logging

# Initial setup
setup_logging(
    log_file=Path("logs/activity.log"),
    level=logging.INFO,
    console=False,  # NO console in GUI!
    rotate=True,
    keep_rotations=7
)

# Change level at runtime
set_log_level(logging.DEBUG)

# Enable debug mode (adds debug filter)
enable_debug_mode()
```

## Log Rotation

- **Automatic**: Logs rotate on application start
- **Keep**: 7 rotations by default (activity.log, activity-1.log, ..., activity-7.log)
- **Pruning**: Configurable age/count limits

## Common Mistakes to Avoid

### ❌ Don't Do This
```python
# 1. Print statements (NEVER!)
print("Debug info")
print(f"Error: {e}")

# 2. Console output in GUI
sys.stdout.write("message")
sys.stderr.write("error")

# 3. Logging before logger init
logger.info("Starting")  # If logging not set up, this fails silently

# 4. Exposing sensitive data
logger.info(f"Password: {password}")
logger.debug(f"API Key: {api_key}")

# 5. Excessive logging in loops
for item in items:
    logger.info(f"Processing {item}")  # Spam!
```

### ✅ Do This Instead
```python
# 1. Use logging
logger = logging.getLogger(__name__)
logger.debug("Debug info")
logger.error(f"Error: {e}")

# 2. Logging only (console=False in GUI)
logger.info("message")
logger.error("error")

# 3. Initialize logging first
from config.logging_config import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

# 4. Redact sensitive data
logger.info(f"Password: {'*' * 8}")
logger.debug(f"API Key: {api_key[:8]}...")

# 5. Batch logging
logger.info(f"Processing {len(items)} items")
if items:
    logger.debug(f"First item: {items[0]}")
```

## Enforcement

### Pre-commit Hook (Future)
```bash
# Check for print statements in production code
if grep -rn "^\s*print(" gui/ prisma/ config/; then
    echo "ERROR: print() statements found! Use logging instead."
    exit 1
fi
```

### Code Review Checklist
- ✅ No `print()` statements in gui/, prisma/, config/
- ✅ Appropriate log levels used
- ✅ No sensitive data in logs
- ✅ QThread workers use logging, not print
- ✅ Exception handling includes logging

## Quick Reference

| Purpose | Method | Example |
|---------|--------|---------|
| Fatal error | `logger.error()` | `logger.error("API auth failed")` |
| Recoverable issue | `logger.warning()` | `logger.warning("Rate limit hit")` |
| Operation summary | `logger.normal()` | `logger.normal("Pull complete")` |
| Detailed steps | `logger.info()` | `logger.info("Fetching rules")` |
| Debug details | `logger.debug()` | `logger.debug(f"Response: {r}")` |

## Summary

1. **NEVER** use `print()` - it causes segfaults in GUI!
2. **ALWAYS** use `logging` module
3. **Choose** appropriate log level
4. **Protect** sensitive data
5. **Test** with different log levels

---

**Remember: One `print()` statement can crash the entire GUI! Always use logging!**
