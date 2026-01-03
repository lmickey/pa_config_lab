# Workflow Patterns

This document defines standard patterns and best practices for implementing workflows in the Prisma Access configuration management system.

## Table of Contents

- [Overview](#overview)
- [Workflow Infrastructure](#workflow-infrastructure)
- [Standard Workflow Structure](#standard-workflow-structure)
- [Configuration Management](#configuration-management)
- [Result Tracking](#result-tracking)
- [Error Handling](#error-handling)
- [Default Management](#default-management)
- [State Tracking](#state-tracking)
- [Best Practices](#best-practices)
- [Examples](#examples)

---

## Overview

Workflows are standardized processes for managing Prisma Access configurations. They provide consistent patterns for:

- **Pull operations** - Retrieving configurations from API
- **Push operations** - Deploying configurations to API
- **Validation** - Checking configuration integrity
- **Transformation** - Converting between formats

All workflows follow the same infrastructure and patterns to ensure consistency and maintainability.

---

## Workflow Infrastructure

The workflow infrastructure is provided by the `config.workflows` package:

```python
from config.workflows import (
    WorkflowConfig,      # Configuration settings
    WorkflowResult,      # Result tracking
    WorkflowState,       # State management
    DefaultManager,      # Default item filtering
)
from config.workflows.workflow_utils import (
    validate_configuration,
    filter_defaults,
    resolve_dependencies,
    build_execution_order,
    handle_workflow_error,
)
```

---

## Standard Workflow Structure

All workflows should follow this standard structure:

### 1. Initialize

```python
def execute_workflow(config: WorkflowConfig) -> WorkflowResult:
    """Execute workflow with standard structure."""
    
    # Create result and state
    result = WorkflowResult(operation='my_workflow')
    state = WorkflowState(workflow_id=f'workflow_{datetime.now().timestamp()}', operation='my_workflow')
    
    # Start workflow
    state.start()
    
    try:
        # ... workflow logic ...
        
        # Mark complete
        state.complete()
        result.mark_complete()
        
    except Exception as e:
        state.fail(str(e))
        result.success = False
        logger.error(f"Workflow failed: {e}")
    
    return result
```

### 2. Validate Inputs

```python
# Validate configuration
is_valid, errors = validate_configuration(config)
if not is_valid:
    for error in errors:
        result.add_error(
            item_type='config',
            item_name='workflow_config',
            operation='validate',
            error_type='ValidationError',
            message=error
        )
    return result
```

### 3. Load Configuration

```python
# Apply filters from configuration
allowed_folders = config.get_allowed_folders(all_folders)
allowed_snippets = config.get_allowed_snippets(all_snippets)

# Initialize default manager
default_manager = DefaultManager()
```

### 4. Process Items

```python
# Start operation
state.start_operation('process_items')
state.update_progress(total=len(items))

for item in items:
    # Check if should process
    if not config.should_process_item(item):
        result.items_skipped += 1
        continue
    
    try:
        # Process item
        process_item(item)
        result.items_processed += 1
        state.increment_progress()
        
    except Exception as e:
        # Handle error
        should_continue = handle_workflow_error(e, item, 'process', result, config)
        if not should_continue:
            break

state.complete_operation()
```

### 5. Handle Errors

```python
# Error handling with retry
max_retries = config.max_retries
retry_count = 0

while retry_count < max_retries:
    try:
        # Attempt operation
        result = operation()
        break
    except Exception as e:
        retry_count += 1
        if retry_count >= max_retries:
            handle_workflow_error(e, item, 'operation', result, config)
        else:
            time.sleep(config.retry_delay)
```

### 6. Return Results

```python
# Mark workflow complete
result.mark_complete()

# Print summary
result.print_summary()

# Save report if needed
result.save_to_file('workflow_result.json')

return result
```

---

## Configuration Management

### WorkflowConfig

The `WorkflowConfig` class manages workflow settings:

```python
from config.workflows import WorkflowConfig

# Create with defaults
config = WorkflowConfig()

# Customize settings
config = WorkflowConfig(
    default_folders=['Mobile Users', 'Remote Networks'],
    excluded_folders={'Colo Connect', 'Service Connections'},
    include_defaults=False,
    validate_before_push=True,
    stop_on_error=False,
    max_retries=3,
    batch_size=100,
)

# Load from file
config = WorkflowConfig.load_from_file(Path('workflow_config.json'))

# Save to file
config.save_to_file(Path('workflow_config.json'))
```

### Key Configuration Options

- **Location filters**: `default_folders`, `excluded_folders`, `excluded_snippets`
- **Item filters**: `include_defaults`, `enabled_only`
- **Validation**: `validate_before_push`, `validate_before_pull`
- **Error handling**: `stop_on_error`, `max_retries`, `retry_delay`
- **Performance**: `batch_size`, `parallel`, `max_workers`

---

## Result Tracking

### WorkflowResult

The `WorkflowResult` class tracks workflow outcomes:

```python
from config.workflows import WorkflowResult

# Create result
result = WorkflowResult(operation='pull')

# Track items
result.items_processed += 1
result.items_created += 1
result.items_skipped += 1

# Add errors
result.add_error(
    item_type='address',
    item_name='test-addr',
    operation='validate',
    error_type='ValidationError',
    message='Missing required field: ip_netmask'
)

# Add warnings
result.add_warning(
    item_type='address',
    item_name='test-addr',
    operation='validate',
    warning_type='DeprecationWarning',
    message='Field "type" is deprecated'
)

# Mark complete
result.mark_complete()

# Get summary
summary = result.get_summary()

# Print summary
result.print_summary()

# Save to file
result.save_to_file('result.json')
```

---

## Error Handling

### Standard Error Handling Pattern

```python
from config.workflows.workflow_utils import handle_workflow_error

try:
    # Attempt operation
    process_item(item)
    result.items_processed += 1
    
except Exception as e:
    # Handle error with standard pattern
    should_continue = handle_workflow_error(
        error=e,
        item=item,
        operation='process',
        result=result,
        config=config
    )
    
    if not should_continue:
        # Stop workflow if stop_on_error is True
        break
```

### Custom Error Handling

```python
from prisma.api.errors import (
    ValidationError,
    AuthenticationError,
    RateLimitError,
)

try:
    # Attempt operation
    api_client.create_item(item)
    
except ValidationError as e:
    # Handle validation errors
    result.add_error(
        item_type=item.item_type,
        item_name=item.name,
        operation='create',
        error_type='ValidationError',
        message=str(e),
        details={'validation_errors': e.details}
    )
    
except RateLimitError as e:
    # Handle rate limiting
    logger.warning(f"Rate limited. Retrying after {e.retry_after}s")
    time.sleep(e.retry_after)
    # Retry operation
    
except AuthenticationError as e:
    # Handle auth errors (critical)
    result.success = False
    raise  # Re-raise critical errors
```

---

## Default Management

### DefaultManager

The `DefaultManager` class handles default/system item filtering:

```python
from config.workflows import DefaultManager

# Create manager
default_manager = DefaultManager()

# Check if item is default
if default_manager.is_default(item):
    logger.debug(f"Skipping default item: {item.name}")
    continue

# Filter defaults from list
filtered_items = default_manager.filter_defaults(
    items,
    include_defaults=config.include_defaults
)

# Customize default detection
default_manager.add_default_folder('Custom Defaults')
default_manager.add_default_prefix('myprefix-')
```

---

## State Tracking

### WorkflowState

The `WorkflowState` class tracks workflow execution:

```python
from config.workflows import WorkflowState

# Create state
state = WorkflowState(
    workflow_id='pull_20250102_123456',
    operation='pull'
)

# Start workflow
state.start()

# Track operations
state.start_operation('fetch_items')
# ... do work ...
state.complete_operation()

# Update progress
state.update_progress(
    processed=10,
    total=100,
    current_item='address-1'
)

# Increment progress
state.increment_progress()

# Store intermediate results
state.store_result('folders', folder_list)

# Mark complete
state.complete()

# Get summary
summary = state.get_summary()
state.print_status()
```

---

## Best Practices

### 1. Always Use WorkflowResult

**DO:**
```python
def pull_configs(config: WorkflowConfig) -> WorkflowResult:
    result = WorkflowResult(operation='pull')
    # ... workflow logic ...
    return result
```

**DON'T:**
```python
def pull_configs(config: dict) -> dict:
    # Returns unstructured dict
    return {'success': True, 'count': 10}
```

### 2. Validate Configuration First

**DO:**
```python
is_valid, errors = validate_configuration(config)
if not is_valid:
    # Handle validation errors
    return result
```

**DON'T:**
```python
# Skip validation and fail later
folders = config.get_allowed_folders(all_folders)
```

### 3. Use Structured Error Handling

**DO:**
```python
result.add_error(
    item_type=item.item_type,
    item_name=item.name,
    operation='validate',
    error_type='ValidationError',
    message=str(e)
)
```

**DON'T:**
```python
errors.append(f"Error: {e}")  # Unstructured
```

### 4. Track Progress

**DO:**
```python
state.update_progress(total=len(items))
for item in items:
    # Process item
    state.increment_progress()
```

**DON'T:**
```python
# No progress tracking
for item in items:
    process(item)
```

### 5. Log Appropriately

**DO:**
```python
logger.info(f"Processing {item.item_type} '{item.name}'")
logger.warning(f"Skipped {item.name}: is default")
logger.error(f"Failed to process {item.name}: {e}")
```

**DON'T:**
```python
print(f"Processing {item.name}")  # Use logger instead
```

### 6. Handle Dependencies

**DO:**
```python
from config.workflows.workflow_utils import build_execution_order

# Order items by dependencies
ordered_items = build_execution_order(items, reverse=False)
```

**DON'T:**
```python
# Process in random order, ignore dependencies
for item in items:
    create(item)
```

---

## Examples

### Example 1: Pull Workflow

```python
from config.workflows import WorkflowConfig, WorkflowResult, WorkflowState, DefaultManager
from config.workflows.workflow_utils import validate_configuration, build_execution_order

def pull_workflow(api_client, config: WorkflowConfig) -> WorkflowResult:
    """Pull configurations from API."""
    
    # Initialize
    result = WorkflowResult(operation='pull')
    state = WorkflowState(workflow_id=f'pull_{datetime.now().timestamp()}', operation='pull')
    state.start()
    
    try:
        # Validate configuration
        is_valid, errors = validate_configuration(config)
        if not is_valid:
            for error in errors:
                result.add_error('config', 'workflow_config', 'validate', 'ValidationError', error)
            return result
        
        # Get folders
        folders = api_client.get_folders()
        allowed_folders = config.get_allowed_folders(folders)
        
        # Initialize default manager
        default_manager = DefaultManager()
        
        # Process each folder
        state.start_operation('fetch_items')
        all_items = []
        
        for folder in allowed_folders:
            # Fetch items
            items = api_client.get_items(AddressObject, folder)
            
            # Filter defaults
            items = default_manager.filter_defaults(items, config.include_defaults)
            
            all_items.extend(items)
            result.items_processed += len(items)
        
        state.complete_operation()
        
        # Save results
        state.store_result('items', all_items)
        
        # Mark complete
        state.complete()
        result.mark_complete()
        
    except Exception as e:
        state.fail(str(e))
        result.success = False
        logger.error(f"Pull workflow failed: {e}")
    
    return result
```

### Example 2: Push Workflow

```python
def push_workflow(api_client, items: List[ConfigItem], config: WorkflowConfig) -> WorkflowResult:
    """Push configurations to API."""
    
    # Initialize
    result = WorkflowResult(operation='push')
    state = WorkflowState(workflow_id=f'push_{datetime.now().timestamp()}', operation='push')
    state.start()
    
    try:
        # Order items by dependencies
        ordered_items = build_execution_order(items, reverse=False)
        
        # Process items
        state.start_operation('push_items')
        state.update_progress(total=len(ordered_items))
        
        for item in ordered_items:
            # Validate if configured
            if config.validate_before_push:
                try:
                    item.validate()
                except Exception as e:
                    result.add_error(item.item_type, item.name, 'validate', 'ValidationError', str(e))
                    result.items_skipped += 1
                    continue
            
            # Push item
            try:
                success = api_client.create_item(item)
                if success:
                    result.items_created += 1
                else:
                    result.items_failed += 1
                    
            except Exception as e:
                should_continue = handle_workflow_error(e, item, 'create', result, config)
                if not should_continue:
                    break
            
            state.increment_progress()
        
        state.complete_operation()
        state.complete()
        result.mark_complete()
        
    except Exception as e:
        state.fail(str(e))
        result.success = False
        logger.error(f"Push workflow failed: {e}")
    
    return result
```

### Example 3: Validation Workflow

```python
from config.workflows.workflow_utils import validate_items

def validation_workflow(items: List[ConfigItem], config: WorkflowConfig) -> WorkflowResult:
    """Validate configurations."""
    
    # Initialize
    result = WorkflowResult(operation='validate')
    
    # Validate all items
    valid_items = validate_items(items, result)
    
    # Update counts
    result.items_processed = len(items)
    result.items_failed = len(items) - len(valid_items)
    
    # Mark complete
    result.mark_complete()
    result.print_summary()
    
    return result
```

---

## Summary

Following these workflow patterns ensures:

- **Consistency** across all operations
- **Maintainability** with standardized structure
- **Observability** through result and state tracking
- **Reliability** with proper error handling
- **Flexibility** through configuration

Use the workflow infrastructure and follow these patterns for all new workflow implementations.
