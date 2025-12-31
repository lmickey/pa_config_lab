# Phase 5 Credentials Update

## Summary

Updated Phase 5 integration tests to use the same credentials for source and destination tenants, since all configuration should have been downloaded initially. This means conflict matching should be 100% - all items should be detected as existing.

## Changes Made

### 1. Unified Credentials (`tests/test_integration_phase5.py`)

**Before:**
- Required separate credentials for source and destination
- Used `PRISMA_DEST_TSG_ID`, `PRISMA_DEST_API_USER`, `PRISMA_DEST_API_SECRET`

**After:**
- Uses same credentials for both source and destination
- Uses `PRISMA_TSG_ID`, `PRISMA_API_USER`, `PRISMA_API_SECRET` for both
- Simplified fixture structure

### 2. Updated Fixtures

```python
@pytest.fixture
def api_credentials():
    """Get API credentials (same for source and destination)."""
    # Uses PRISMA_TSG_ID, PRISMA_API_USER, PRISMA_API_SECRET

@pytest.fixture
def source_api_client(api_credentials):
    """Create authenticated source API client (same as destination)."""

@pytest.fixture
def dest_api_client(api_credentials):
    """Create authenticated destination API client (same as source)."""
```

### 3. Updated Tests to Use Pulled Configuration

All Phase 5 tests now:
- Pull configuration from source tenant first
- Use that pulled configuration for push operations
- Expect 100% conflict matching since config came from same tenant

**Updated Tests:**
- `test_validate_configuration` - Uses pulled config
- `test_detect_conflicts` - Uses pulled config, expects conflicts to be detected
- `test_push_configuration_dry_run` - Uses pulled config
- `test_push_statistics` - Uses pulled config

### 4. Conflict Detection Expectations

Since configuration is pulled from the same tenant it's being pushed to:
- **100% conflict matching expected** - All items should be detected as existing
- Conflict detection should identify all items as already present
- This validates that conflict detection works correctly

## Rationale

1. **Real-world scenario**: In practice, you pull config from a tenant and may push it back to the same tenant (for validation, testing, etc.)
2. **100% matching**: Since all config was downloaded initially, everything should match
3. **Simplified setup**: Only need one set of credentials instead of two
4. **Better testing**: Tests actual conflict detection with real data

## Environment Variables

**Required:**
```bash
export PRISMA_TSG_ID="your-tsg-id"
export PRISMA_API_USER="your-api-user"
export PRISMA_API_SECRET="your-api-secret"
```

**No longer needed:**
- ~~PRISMA_DEST_TSG_ID~~
- ~~PRISMA_DEST_API_USER~~
- ~~PRISMA_DEST_API_SECRET~~

## Test Behavior

When tests run with credentials:

1. **Pull Phase**: Configuration is pulled from tenant using `source_api_client`
2. **Conflict Detection**: Same configuration is checked against tenant using `dest_api_client` (same tenant)
3. **Expected Result**: All items should be detected as existing (100% match)
4. **Validation**: Conflict detection correctly identifies that items already exist

## Files Modified

- `tests/test_integration_phase5.py` - Updated all fixtures and tests

## Benefits

1. ✅ Simplified credential management (one set instead of two)
2. ✅ Realistic test scenario (pull from same tenant)
3. ✅ Validates 100% conflict matching works correctly
4. ✅ Tests actual conflict detection with real data
5. ✅ Easier to set up and run
