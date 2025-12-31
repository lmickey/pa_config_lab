# Coverage Threshold Summary

## Current Implementation

The test suite attempts to dynamically adjust the coverage threshold based on credential availability:

- **70%** when credentials are available (integration tests can run)
- **55%** when credentials are not available (unit tests only)

## How It Works

1. **Credential Detection**: `pytest_configure` hook in `tests/conftest.py` checks for:
   - `PRISMA_TSG_ID`
   - `PRISMA_API_USER`
   - `PRISMA_API_SECRET`

2. **Threshold Adjustment**: Attempts to override `config.option.cov_fail_under` based on credentials

3. **Baseline**: `pytest.ini` sets `--cov-fail-under=55` as default

## Current Status

**Issue**: The coverage plugin (pytest-cov) reads the threshold from `pytest.ini` before `pytest_configure` can modify it. The threshold override in the hook may not take effect.

**Workaround**: The threshold is set to **55%** in `pytest.ini`, which allows tests to pass without credentials. When credentials are available, you can manually override:

```bash
# With credentials - enforce 70% threshold
export PRISMA_TSG_ID="your-tsg-id"
export PRISMA_API_USER="your-api-user"
export PRISMA_API_SECRET="your-api-secret"
pytest tests/ --cov-fail-under=70 -v
```

## Test Results

- **Without credentials**: Tests pass with 55% threshold (current coverage: ~57%)
- **With credentials**: Tests should pass with 70% threshold when integration tests run

## Future Improvement

To properly implement dynamic threshold adjustment, one of these approaches could be used:

1. **Pytest Plugin**: Create a plugin that hooks into coverage plugin initialization
2. **Wrapper Script**: Create a script that sets threshold before running pytest
3. **Environment Variable**: Use an env var that pytest-cov can read (if supported)
4. **Early Hook**: Use `pytest_load_initial_conftests` or similar early hook

For now, the 55% threshold allows tests to pass, and users can manually increase it to 70% when running with credentials.
