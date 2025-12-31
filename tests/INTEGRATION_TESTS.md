# Integration Tests

This directory contains integration tests that use real API responses when credentials are available. These tests are converted from the phase test scripts (`test_phase1.py` through `test_phase5.py`) and integrated into the pytest framework.

## Overview

The integration tests are organized by phase:

- **`test_integration_phase1.py`** - Schema, Storage, and API Client tests
- **`test_integration_phase2.py`** - Pull Functionality tests
- **`test_integration_phase3.py`** - Default Configuration Detection tests
- **`test_integration_phase4.py`** - Dependency Resolution tests
- **`test_integration_phase5.py`** - Push Functionality tests

## Running Integration Tests

### Prerequisites

Integration tests require API credentials. They will automatically skip if credentials are not provided.

### Setting Up Credentials

Set environment variables for API credentials:

```bash
# For Phase 1-4 tests (source tenant)
export PRISMA_TSG_ID="your-tsg-id"
export PRISMA_API_USER="your-api-client-id"
export PRISMA_API_SECRET="your-api-client-secret"

# For Phase 5 tests (destination tenant - optional)
export PRISMA_DEST_TSG_ID="destination-tsg-id"
export PRISMA_DEST_API_USER="destination-api-client-id"
export PRISMA_DEST_API_SECRET="destination-api-client-secret"
```

### Running Tests

#### Run All Integration Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run all integration tests
pytest tests/test_integration_*.py -v

# Or use marker
pytest -m integration -v
```

#### Run Specific Phase Tests

```bash
# Phase 1 tests
pytest tests/test_integration_phase1.py -v

# Phase 2 tests
pytest tests/test_integration_phase2.py -v

# Phase 3 tests
pytest tests/test_integration_phase3.py -v

# Phase 4 tests
pytest tests/test_integration_phase4.py -v

# Phase 5 tests
pytest tests/test_integration_phase5.py -v

# Or use phase markers
pytest -m phase1 -v
pytest -m phase2 -v
pytest -m phase3 -v
pytest -m phase4 -v
pytest -m phase5 -v
```

#### Run Without Credentials (Skip Integration Tests)

```bash
# Run only unit/mock tests
pytest tests/ -v -m "not integration"

# Or exclude integration tests
pytest tests/ -v --ignore=tests/test_integration_*.py
```

## Test Structure

### Phase 1: Schema, Storage, and API Client

Tests:
- Schema creation and validation
- JSON storage functions
- Backward compatibility with pickle format
- API client initialization and authentication
- Basic API operations (folders, rules, addresses)

**Credentials Required:** Source tenant credentials

### Phase 2: Pull Functionality

Tests:
- Folder capture
- Rule capture
- Object capture (addresses, groups)
- Profile capture
- Snippet capture
- Pull orchestrator
- Full configuration pull

**Credentials Required:** Source tenant credentials

### Phase 3: Default Configuration Detection

Tests:
- Default configuration database
- Default detector functionality
- Default filtering
- Integration with pull functionality

**Credentials Required:** Source tenant credentials (optional)

### Phase 4: Dependency Resolution

Tests:
- Dependency graph creation
- Dependency resolver functionality
- Dependency validation
- Integration with pull functionality

**Credentials Required:** Source tenant credentials (optional)

### Phase 5: Push Functionality

Tests:
- Push validation
- Conflict detection
- Push orchestrator
- Full pull → push workflow

**Credentials Required:** 
- Source tenant credentials (for pull)
- Destination tenant credentials (for push)

## Test Behavior

### Automatic Skipping

Integration tests automatically skip if:
- Required environment variables are not set
- API authentication fails
- Required resources (folders, etc.) are not available

### Dry Run Mode

Phase 5 push tests use `dry_run=True` by default to avoid making actual changes. To test actual pushes, modify the test code or use the original phase test scripts.

## Comparison with Original Phase Tests

The original phase test scripts (`test_phase1.py` through `test_phase5.py`) are still available in the root directory. They:

- Use interactive prompts for credentials
- Provide more detailed output
- Can be run standalone
- Are useful for manual testing

The pytest integration tests:

- Use environment variables for credentials
- Integrate with pytest framework
- Can be run in CI/CD pipelines
- Provide structured test results
- Support test markers and filtering

## Running Both Test Suites

You can run both the pytest unit tests and integration tests:

```bash
# Run all tests (unit + integration)
pytest tests/ -v

# Run only unit tests (mocked)
pytest tests/ -v -m "not integration"

# Run only integration tests (real API)
pytest tests/ -v -m integration
```

## Coverage

Integration tests help improve code coverage by exercising:
- Real API client code paths
- Actual data structures returned by APIs
- Error handling with real API responses
- End-to-end workflows

Note: Integration tests may have lower coverage reporting due to skipping when credentials aren't available.

## Troubleshooting

### Tests Skip Unexpectedly

- Check that environment variables are set correctly
- Verify API credentials are valid
- Check that the tenant has the required resources (folders, etc.)

### Authentication Failures

- Verify TSG ID, API User, and API Secret are correct
- Check API client permissions
- Ensure network connectivity to Prisma Access API

### Missing Resources

Some tests may skip if the tenant doesn't have:
- Security policy folders
- Rules, objects, or profiles
- Required permissions

This is expected behavior - tests gracefully skip when resources aren't available.

## CI/CD Integration

For CI/CD pipelines:

1. Set credentials as secrets/environment variables
2. Run integration tests conditionally (e.g., on specific branches)
3. Use `--maxfail=1` to fail fast on errors
4. Consider using `--tb=short` for concise output

Example:
```bash
pytest tests/test_integration_*.py -v --maxfail=1 --tb=short
```
