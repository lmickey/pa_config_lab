# Troubleshooting Guide

## Common Issues and Solutions

### Authentication Issues

#### Problem: Authentication Fails

**Symptoms:**
- `Authentication failed: 401`
- `Authentication error: Network error`
- Token is None after authentication

**Solutions:**

1. **Verify Credentials**
   ```python
   # Check environment variables
   import os
   print("TSG ID:", os.getenv("PRISMA_TSG_ID"))
   print("API User:", os.getenv("PRISMA_API_USER"))
   # API Secret should be set but not printed
   ```

2. **Check API Client Permissions**
   - Verify API client has required scopes
   - Ensure TSG ID matches the tenant
   - Check API client is not expired

3. **Network Connectivity**
   ```bash
   # Test connectivity to auth endpoint
   curl -v https://auth.apps.paloaltonetworks.com/oauth2/access_token
   ```

#### Problem: Token Expires Quickly

**Symptoms:**
- Frequent re-authentication
- `Failed to authenticate` errors

**Solutions:**

- Tokens expire in 15 minutes
- System automatically refreshes 1 minute before expiration
- If issues persist, check system clock synchronization

### Pull Issues

#### Problem: No Folders Discovered

**Symptoms:**
- Empty folder list
- `No folders available` errors

**Solutions:**

1. **Check Permissions**
   ```python
   # Try listing folders directly
   folders = client.get_security_policy_folders()
   print(f"Found {len(folders)} folders")
   ```

2. **Check Folder Access**
   - Verify API client has security policy read permissions
   - Some folders may require specific permissions

3. **Use Alternative Discovery**
   ```python
   # Try discovering via objects endpoint
   from prisma.pull.folder_capture import FolderCapture
   folder_capture = FolderCapture(client)
   folders = folder_capture.discover_folders()
   ```

#### Problem: Empty Configuration Pulled

**Symptoms:**
- Configuration structure exists but no data
- Zero counts in pull statistics

**Solutions:**

1. **Check Folder Contents**
   ```python
   # Verify folder has content
   rules = client.get_all_security_rules(folder="Shared")
   print(f"Rules in Shared: {len(rules)}")
   ```

2. **Check Default Filtering**
   ```python
   # Include defaults if needed
   config = pull_configuration(
       client,
       include_defaults=True  # Include default folders
   )
   ```

3. **Verify Folder Name**
   - Folder names are case-sensitive
   - Check exact folder name spelling
   - Use `list_folders_for_capture()` to see available folders

#### Problem: Missing Dependencies

**Symptoms:**
- Validation errors about missing dependencies
- Rules reference non-existent objects

**Solutions:**

1. **Check Parent Dependencies**
   ```python
   # Parent dependencies are tracked separately
   folder_config = config["security_policies"]["folders"][0]
   parent_deps = folder_config.get("parent_dependencies", {})
   print("Parent dependencies:", parent_deps)
   ```

2. **Pull Parent Folders**
   ```python
   # Pull parent folder to get dependencies
   config = pull_configuration(
       client,
       folder_names=["Parent Folder", "Child Folder"]
   )
   ```

3. **Validate Dependencies**
   ```python
   from prisma.dependencies.dependency_resolver import DependencyResolver
   resolver = DependencyResolver()
   validation = resolver.validate_dependencies(config)
   if not validation["valid"]:
       print("Missing:", validation["missing_dependencies"])
   ```

### Push Issues

#### Problem: Validation Failures

**Symptoms:**
- `Validation failed` errors
- Push returns `success: False`

**Solutions:**

1. **Check Schema Compliance**
   ```python
   from config.schema.schema_validator import validate_config
   is_valid, errors = validate_config(config)
   if not is_valid:
       for error in errors:
           print(f"Schema error: {error}")
   ```

2. **Fix Required Fields**
   - Ensure all required fields are present
   - Check folder `name` and `path` fields
   - Verify `metadata.version` is "2.0.0"

3. **Check Infrastructure Field**
   ```python
   # Ensure infrastructure field exists
   if "infrastructure" not in config:
       config["infrastructure"] = {}
   ```

#### Problem: Conflict Detection Issues

**Symptoms:**
- Conflicts not detected when expected
- 100% conflict matching when pushing to same tenant

**Solutions:**

1. **Expected Behavior**
   - Pushing to same tenant should detect 100% conflicts
   - All items should be detected as existing
   - This is correct behavior

2. **Check Conflict Strategy**
   ```python
   # Use SKIP strategy to avoid overwriting
   result = push_configuration(
       client,
       config,
       conflict_strategy=ConflictResolution.SKIP
   )
   ```

3. **Review Conflicts**
   ```python
   from prisma.push.conflict_resolver import ConflictResolver
   resolver = ConflictResolver()
   conflicts = resolver.detect_conflicts(config, client)
   print(f"Conflicts: {conflicts['conflict_count']}")
   ```

#### Problem: Push Fails with Errors

**Symptoms:**
- `Push failed` messages
- Errors in push statistics

**Solutions:**

1. **Check Error Details**
   ```python
   result = push_configuration(client, config)
   if not result.get("success"):
       errors = result.get("stats", {}).get("errors", [])
       for error in errors:
           print(f"Error: {error['message']}")
   ```

2. **Validate Before Push**
   ```python
   from prisma.push.push_validator import PushValidator
   validator = PushValidator()
   validation = validator.validate_configuration(config, client)
   if not validation.get("valid"):
       # Fix validation errors first
   ```

3. **Check API Permissions**
   - Verify API client has write permissions
   - Some operations may require admin permissions

### Storage Issues

#### Problem: Cannot Load Configuration

**Symptoms:**
- `File not found` errors
- Decryption failures

**Solutions:**

1. **Check File Path**
   ```python
   import os
   filepath = "backup.json"
   if not os.path.exists(filepath):
       print(f"File not found: {filepath}")
   ```

2. **Check Encryption**
   ```python
   # Try unencrypted first
   config = load_config_json("backup.json", encrypted=False)
   
   # If encrypted, provide cipher
   from config.storage.json_storage import derive_key
   cipher = derive_key("your-password")
   config = load_config_json("backup.json", cipher=cipher, encrypted=True)
   ```

3. **Format Detection**
   ```python
   from config.storage.pickle_compat import detect_config_format
   format_type = detect_config_format("backup.bin")
   print(f"Format: {format_type}")
   ```

#### Problem: Schema Validation Errors

**Symptoms:**
- `Validation failed` errors
- Schema mismatch errors

**Solutions:**

1. **Check Schema Version**
   ```python
   from config.schema.schema_validator import check_schema_version
   version = check_schema_version(config)
   print(f"Config version: {version}")
   ```

2. **Fix Structure Issues**
   - Ensure `decryption_profiles` is object, not list
   - Check all required fields are present
   - Verify folder structure matches schema

3. **Use Schema Validator**
   ```python
   from config.schema.schema_validator import validate_config
   is_valid, errors = validate_config(config)
   for error in errors:
       print(f"Error: {error}")
   ```

### Testing Issues

#### Problem: Tests Skip Unexpectedly

**Symptoms:**
- Integration tests skip
- `pytest.skip` messages

**Solutions:**

1. **Check Credentials**
   ```bash
   # Verify environment variables are set
   echo $PRISMA_TSG_ID
   echo $PRISMA_API_USER
   # PRISMA_API_SECRET should be set but not echoed
   ```

2. **Check Authentication**
   ```python
   # Test authentication manually
   from prisma.api_client import PrismaAccessAPIClient
   client = PrismaAccessAPIClient(...)
   if client.authenticate():
       print("Authentication successful")
   ```

3. **Check Resources**
   - Verify tenant has folders/rules/objects
   - Some tests skip if resources aren't available

#### Problem: Coverage Below Threshold

**Symptoms:**
- `Coverage failure` errors
- Tests pass but coverage fails

**Solutions:**

1. **Run Integration Tests**
   ```bash
   # Set credentials and run integration tests
   export PRISMA_TSG_ID="..."
   export PRISMA_API_USER="..."
   export PRISMA_API_SECRET="..."
   pytest tests/ -m integration
   ```

2. **Adjust Threshold**
   ```bash
   # Override threshold manually
   pytest tests/ --cov-fail-under=55
   ```

3. **Check Coverage Report**
   ```bash
   # Generate HTML report
   pytest tests/ --cov --cov-report=html
   # Open htmlcov/index.html
   ```

## Getting Help

### Check Logs

Error logs are stored in:
- `prisma/error_logger.py` - Centralized error logging
- Check error log files for detailed error information

### Debug Mode

Enable verbose output:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `Authentication failed: 401` | Invalid credentials | Check TSG ID, API user, API secret |
| `No folders available` | No permissions or empty tenant | Check API permissions, verify tenant has folders |
| `Validation failed` | Schema mismatch | Fix configuration structure, check required fields |
| `Conflicts detected` | Items already exist | Use conflict resolution strategy |
| `Missing dependencies` | Referenced items don't exist | Pull parent folders, check dependencies |

## See Also

- [Comprehensive Configuration Guide](README_COMPREHENSIVE_CONFIG.md)
- [Pull & Push Guide](PULL_PUSH_GUIDE.md)
- [API Reference](API_REFERENCE.md)
