# Dynamic Coverage Threshold

## Overview

The test suite dynamically adjusts the coverage threshold based on whether API credentials are available:

- **70%** when credentials are available (integration tests can run)
- **55%** when credentials are not available (unit tests only)

## How It Works

The `pytest_configure` hook in `tests/conftest.py` checks for API credentials and adjusts the coverage threshold accordingly.

## Current Status

The coverage threshold adjustment is implemented, but pytest-cov reads the threshold from `pytest.ini` before the hook can modify it. The threshold is set to **55%** in `pytest.ini` as a baseline.

## Manual Override

If you have credentials and want to enforce a 70% threshold, you can override it:

```bash
# With credentials
export PRISMA_TSG_ID="your-tsg-id"
export PRISMA_API_USER="your-api-user"
export PRISMA_API_SECRET="your-api-secret"

# Run with explicit threshold
pytest tests/ --cov-fail-under=70 -v
```

## Future Improvement

A better solution would be to:
1. Use a pytest plugin that hooks into coverage plugin initialization
2. Or modify pytest.ini programmatically before pytest runs
3. Or use an environment variable that pytest-cov can read

For now, the threshold is set to 55% to allow tests to pass without credentials, and can be manually increased to 70% when credentials are available.
