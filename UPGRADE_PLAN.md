# Prisma Access Comprehensive Configuration Capture - Upgrade Plan

## Executive Summary

This document outlines a significant upgrade to transform the Prisma Access configuration tool from a basic configuration utility into a comprehensive configuration capture, storage, and migration system. The upgrade will enable full configuration extraction from SCM-managed Prisma Access tenants, intelligent default detection, and selective push capabilities to target tenants.

## Current State Analysis

### Existing Capabilities
- **Basic Configuration**: Service Connection setup, basic infrastructure settings
- **Storage Format**: Encrypted pickle files (`*-fwdata.bin`)
- **API Integration**: Basic Prisma Access API calls for Service Connections
- **Configuration Structure**: Simple dictionary with `fwData` and `paData` keys
- **Scope**: Limited to basic POV configurations

### Limitations
- **Limited Scope**: Only captures basic Service Connection and infrastructure settings
- **No Security Policy Support**: Cannot capture security policies, objects, profiles
- **No Folder/Snippet Awareness**: Doesn't handle folder or snippet configurations
- **No Default Detection**: Saves all configuration including defaults
- **No Pull/Push Workflow**: No ability to migrate configurations between tenants
- **Storage Format**: Pickle format not human-readable or easily editable
- **No Testing Framework**: No automated validation or dependency checking

## Upgrade Objectives

### Primary Goals
1. **Comprehensive Configuration Capture**: Extract all configurable elements from Prisma Access SCM tenants
2. **Security Policy Focus**: Full support for security policies in folders and snippets
3. **Default Detection**: Intelligently identify and exclude default configurations
4. **JSON Storage**: Migrate to human-readable JSON format for manual editing capability
5. **Pull/Push Workflow**: Extract from source tenant, push to target tenant
6. **Selective Push Wizard**: Allow users to choose what to push (future enhancement)
7. **Automated Testing**: Validate configurations and dependencies

### Secondary Goals
- Maintain backward compatibility with existing configurations
- Support both SCM and Panorama-managed environments (start with SCM)
- Enable configuration comparison and diff capabilities
- Support configuration versioning

## Architecture Overview

### New Configuration Structure

The configuration will be restructured into a hierarchical JSON format:

```json
{
  "metadata": {
    "version": "2.0",
    "created": "2024-01-01T00:00:00Z",
    "source_tenant": "tsg-1234567890",
    "source_type": "scm",
    "description": "Configuration export from production tenant"
  },
  "infrastructure": {
    "shared_infrastructure_settings": {},
    "mobile_agent": {},
    "service_connections": [],
    "remote_networks": []
  },
  "security_policies": {
    "folders": [
      {
        "name": "Shared",
        "path": "/config/security-policy/folders/Shared",
        "is_default": false,
        "security_rules": [],
        "objects": {
          "address_objects": [],
          "address_groups": [],
          "service_objects": [],
          "service_groups": [],
          "application_filters": [],
          "application_groups": [],
          "application_signatures": [],
          "url_filtering_categories": [],
          "external_dynamic_lists": []
        },
        "profiles": {
          "authentication_profiles": [],
          "security_profiles": {
            "antivirus": [],
            "anti_spyware": [],
            "vulnerability": [],
            "url_filtering": [],
            "file_blocking": [],
            "wildfire": [],
            "data_filtering": []
          },
          "decryption_profiles": {
            "ssl_forward_proxy": [],
            "ssl_inbound_inspection": [],
            "ssl_ssh_proxy": []
          }
        }
      }
    ],
    "snippets": [
      {
        "name": "snippet-name",
        "path": "/config/security-policy/snippets/snippet-name",
        "is_default": false,
        "security_rules": [],
        "objects": {},
        "profiles": {}
      }
    ]
  },
  "authentication": {
    "authentication_profiles": [],
    "authentication_sequences": [],
    "saml_profiles": [],
    "kerberos_profiles": []
  },
  "network": {
    "ike_crypto_profiles": [],
    "ipsec_crypto_profiles": [],
    "ike_gateways": [],
    "ipsec_tunnels": [],
    "service_connections": [],
    "remote_networks": []
  },
  "defaults": {
    "detected_defaults": [],
    "excluded_configs": []
  }
}
```

## Implementation Phases

### Phase 1: Foundation & Infrastructure (Weeks 1-2)

#### 1.1 Branch Creation & Setup
- Create new branch: `feature/comprehensive-config-capture`
- Set up development environment
- Document branching strategy

#### 1.2 Configuration Storage Redesign
**Tasks:**
- Design new JSON schema for comprehensive configuration
- Create migration utility to convert existing pickle files to JSON
- Implement JSON-based save/load functions
- Maintain backward compatibility layer
- Add configuration versioning support

**Files to Create/Modify:**
- `config_schema.py` - JSON schema definitions and validation
- `config_storage.py` - New JSON-based storage functions
- `config_migration.py` - Migration from pickle to JSON
- Update `load_settings.py` to support both formats
- Update `get_settings.py` to use JSON format

#### 1.3 API Client Enhancement
**Tasks:**
- Create comprehensive Prisma Access API client module
- Implement folder traversal and discovery
- Add snippet discovery and retrieval
- Implement pagination handling for large datasets
- Add rate limiting and retry logic
- Create API response caching mechanism

**Files to Create:**
- `prisma_api_client.py` - Enhanced API client
- `api_endpoints.py` - Centralized endpoint definitions
- `api_utils.py` - Helper functions for API operations

### Phase 2: Security Policy Capture (Weeks 3-5)

#### 2.1 Folder Discovery & Enumeration
**Tasks:**
- List all folders in security policy configuration
- Retrieve folder metadata and hierarchy
- Identify folder relationships and inheritance
- Map folder paths to configuration structure

**API Endpoints:**
- `/config/security-policy/folders` - List folders
- `/config/security-policy/folders/{folder}` - Get folder details

#### 2.2 Security Rules Capture
**Tasks:**
- Extract all security rules from each folder
- Capture rule ordering and priority
- Extract rule conditions (source, destination, application, etc.)
- Capture rule actions and logging settings
- Store rule metadata (name, description, tags)

**API Endpoints:**
- `/config/security-policy/security-rules` - List security rules
- `/config/security-policy/security-rules/{id}` - Get rule details

#### 2.3 Objects Capture
**Tasks:**
- Address Objects and Groups
- Service Objects and Groups
- Application Filters, Groups, and Signatures
- URL Filtering Categories
- External Dynamic Lists
- Custom URL Categories
- FQDN Objects

**API Endpoints:**
- `/config/objects/addresses`
- `/config/objects/address-groups`
- `/config/objects/services`
- `/config/objects/service-groups`
- `/config/objects/applications`
- `/config/objects/application-groups`
- `/config/objects/application-filters`
- `/config/objects/url-categories`
- `/config/objects/external-dynamic-lists`
- `/config/objects/fqdn`

#### 2.4 Profiles Capture
**Tasks:**
- Authentication Profiles
- Security Profiles (Antivirus, Anti-Spyware, Vulnerability, URL Filtering, File Blocking, WildFire, Data Filtering)
- Decryption Profiles (SSL Forward Proxy, SSL Inbound Inspection, SSL SSH Proxy)

**API Endpoints:**
- `/config/authentication-profiles`
- `/config/security-profiles/antivirus`
- `/config/security-profiles/anti-spyware`
- `/config/security-profiles/vulnerability`
- `/config/security-profiles/url-filtering`
- `/config/security-profiles/file-blocking`
- `/config/security-profiles/wildfire`
- `/config/security-profiles/data-filtering`
- `/config/decryption-profiles/ssl-forward-proxy`
- `/config/decryption-profiles/ssl-inbound-inspection`

#### 2.5 Snippet Configuration Capture
**Tasks:**
- Discover all snippets
- Extract snippet-specific security rules
- Capture snippet objects and profiles
- Map snippet relationships to folders

**API Endpoints:**
- `/config/security-policy/snippets` - List snippets
- `/config/security-policy/snippets/{snippet}` - Get snippet details

### Phase 3: Default Configuration Detection (Weeks 6-7)

#### 3.1 Default Configuration Database
**Tasks:**
- Research and document Prisma Access default configurations
- Create database/catalog of default values for all object types
- Identify default security profiles and their settings
- Document default authentication profiles
- Create default rule patterns

**Files to Create:**
- `default_configs.py` - Default configuration database
- `default_detector.py` - Default detection logic

#### 3.2 Detection Logic Implementation
**Tasks:**
- Compare captured configurations against defaults
- Mark configurations as default vs. custom
- Store detection results in configuration file
- Allow user override for default inclusion/exclusion
- Create reporting mechanism for detected defaults

**Detection Strategies:**
- Exact match comparison
- Pattern matching for rules
- Name-based detection (e.g., "default" in name)
- Value-based detection (known default values)

#### 3.3 Configuration Filtering
**Tasks:**
- Implement filtering to exclude defaults from export
- Provide option to include defaults for reference
- Create separate "defaults" section in JSON for documentation
- Generate exclusion list for user review

### Phase 4: Dependency Resolution & Pull Enhancement (Weeks 8-10)

**Note**: Comprehensive pull functionality was completed in Phase 2. This phase focuses on dependency resolution and CLI/GUI integration.

#### 4.1 Dependency Resolution
**Tasks:**
- Map dependencies between configuration objects
- Resolve object references (address groups → addresses)
- Resolve profile references (rules → profiles)
- Create dependency graph for validation
- Ensure all dependencies are captured

**Files to Create:**
- `dependency_resolver.py` - Dependency mapping and resolution
- `dependency_graph.py` - Graph structure for dependencies

#### 4.2 Pull CLI/GUI Integration
**Tasks:**
- Create command-line interface for pull operations
- Add GUI integration for pull functionality (leverage existing pull functions)
- Provide pull progress indicators (already implemented, integrate into CLI/GUI)
- Generate pull reports and summaries (already implemented, format for CLI/GUI)
- Allow selective pull (folders, snippets, object types) (already implemented, expose in CLI/GUI)

**Files to Create:**
- `cli/pull_cli.py` - CLI interface for pull operations
- Update `pa_config_gui.py` - Add pull functionality GUI

#### 4.3 Incremental Pull (Optional)
**Tasks:**
- Implement incremental pull (only changed items since last pull)
- Add change detection mechanism
- Support for delta pulls
- Track pull history/timestamps

**Files to Create:**
- `prisma/pull/incremental_pull.py` - Incremental pull logic

### Phase 5: Push Functionality (Weeks 11-13)

#### 5.1 Push Engine Development
**Tasks:**
- Create push function to deploy configurations to target tenant
- Implement dependency ordering for push operations
- Add conflict detection (existing objects with same name)
- Implement dry-run mode for testing
- Create rollback capability

**Files to Create:**
- `config_push.py` - Main push functionality
- `push_orchestrator.py` - Push orchestration

#### 5.2 Conflict Resolution
**Tasks:**
- Detect conflicts (existing objects, rules, profiles)
- Provide conflict resolution options:
  - Skip (don't push)
  - Overwrite (replace existing)
  - Rename (create with new name)
  - Merge (combine configurations)
- Create conflict report for user review

**Files to Create:**
- `conflict_resolver.py` - Conflict detection and resolution

#### 5.3 Push Validation
**Tasks:**
- Validate configuration before push
- Check for missing dependencies
- Verify object references are valid
- Validate API permissions
- Pre-flight checks for push operations

**Files to Create:**
- `push_validator.py` - Pre-push validation

#### 5.4 Basic Push Wizard (Initial Implementation)
**Tasks:**
- Create simple wizard for push operations
- Allow selection of folders to push
- Allow selection of object types to push
- Provide summary before push
- Confirm push operation

**Files to Create:**
- `push_wizard.py` - Basic push wizard (CLI)
- Update GUI for push wizard (future)

### Phase 6: Testing Framework (Weeks 14-16)

#### 6.1 Test Infrastructure
**Tasks:**
- Set up testing framework (pytest recommended)
- Create test fixtures for API mocking
- Create test data generators
- Set up CI/CD pipeline integration

**Files to Create:**
- `tests/` directory structure
- `tests/conftest.py` - Test fixtures
- `tests/test_config_schema.py` - Schema validation tests
- `tests/test_api_client.py` - API client tests

#### 6.2 Configuration Field Testing
**Tasks:**
- Create tests for all configuration fields
- Test field validation and constraints
- Test field dependencies
- Test edge cases and boundary conditions
- Create test coverage reports

**Test Categories:**
- Unit tests for individual functions
- Integration tests for API interactions
- Validation tests for configuration schemas
- Dependency resolution tests

#### 6.3 Dependency Validation Tests
**Tasks:**
- Test dependency resolution logic
- Test circular dependency detection
- Test missing dependency detection
- Test dependency ordering for push
- Test dependency graph construction

**Files to Create:**
- `tests/test_dependencies.py` - Dependency tests
- `tests/test_dependency_resolver.py` - Resolver tests

#### 6.4 End-to-End Testing
**Tasks:**
- Create end-to-end pull tests
- Create end-to-end push tests
- Test full workflow (pull → modify → push)
- Test error scenarios and recovery
- Performance testing for large configurations

**Files to Create:**
- `tests/test_pull_e2e.py` - End-to-end pull tests
- `tests/test_push_e2e.py` - End-to-end push tests
- `tests/test_workflow.py` - Full workflow tests

### Phase 7: Documentation & Polish (Weeks 17-18)

#### 7.1 Documentation
**Tasks:**
- Update README with new capabilities
- Create user guide for pull/push operations
- Document JSON schema structure
- Create API reference documentation
- Add troubleshooting guide

**Files to Create/Update:**
- `README_COMPREHENSIVE_CONFIG.md` - New feature documentation
- `PULL_PUSH_GUIDE.md` - User guide
- `JSON_SCHEMA.md` - Schema documentation
- Update `README.md` - Add references to new features

#### 7.2 Code Quality
**Tasks:**
- Code review and refactoring
- Add comprehensive docstrings
- Improve error messages
- Add logging throughout
- Performance optimization

#### 7.3 Migration Guide
**Tasks:**
- Create migration guide from old format
- Provide migration scripts
- Document breaking changes
- Create compatibility layer documentation

## Technical Specifications

### Prisma Access API Endpoints Required

#### Security Policy Endpoints
```
GET  /sse/config/v1/security-policy/folders
GET  /sse/config/v1/security-policy/folders/{folder}
GET  /sse/config/v1/security-policy/security-rules?folder={folder}
GET  /sse/config/v1/security-policy/security-rules/{id}
GET  /sse/config/v1/security-policy/snippets
GET  /sse/config/v1/security-policy/snippets/{snippet}
```

#### Object Endpoints
```
GET  /sse/config/v1/addresses?folder={folder}
GET  /sse/config/v1/address-groups?folder={folder}
GET  /sse/config/v1/services?folder={folder}
GET  /sse/config/v1/service-groups?folder={folder}
GET  /sse/config/v1/applications?folder={folder}
GET  /sse/config/v1/application-groups?folder={folder}
GET  /sse/config/v1/application-filters?folder={folder}
GET  /sse/config/v1/url-categories?folder={folder}
GET  /sse/config/v1/external-dynamic-lists?folder={folder}
GET  /sse/config/v1/fqdn?folder={folder}
```

#### Profile Endpoints
```
GET  /sse/config/v1/authentication-profiles?folder={folder}
GET  /sse/config/v1/security-profiles/antivirus?folder={folder}
GET  /sse/config/v1/security-profiles/anti-spyware?folder={folder}
GET  /sse/config/v1/security-profiles/vulnerability?folder={folder}
GET  /sse/config/v1/security-profiles/url-filtering?folder={folder}
GET  /sse/config/v1/security-profiles/file-blocking?folder={folder}
GET  /sse/config/v1/security-profiles/wildfire?folder={folder}
GET  /sse/config/v1/security-profiles/data-filtering?folder={folder}
GET  /sse/config/v1/decryption-profiles/ssl-forward-proxy?folder={folder}
GET  /sse/config/v1/decryption-profiles/ssl-inbound-inspection?folder={folder}
```

### JSON Schema Structure

The configuration will use JSON Schema for validation. Key sections:

1. **Metadata**: Version, timestamps, source information
2. **Infrastructure**: Shared settings, mobile agent, service connections
3. **Security Policies**: Folders and snippets with rules, objects, profiles
4. **Authentication**: Authentication-related configurations
5. **Network**: Network-related configurations
6. **Defaults**: Detected defaults and exclusions

### Default Configuration Detection

Default configurations will be identified through:
1. **Name Patterns**: Objects with "default" in name
2. **Value Matching**: Comparison against known default values
3. **Rule Patterns**: Security rules matching default patterns
4. **Profile Matching**: Security profiles matching default settings

### Dependency Mapping

Dependencies to track:
- Security Rules → Address Objects/Groups
- Security Rules → Service Objects/Groups
- Security Rules → Applications
- Security Rules → Security Profiles
- Security Rules → Authentication Profiles
- Address Groups → Address Objects
- Service Groups → Service Objects
- Application Groups → Applications

## File Structure

```
pa_config_lab/
├── config/
│   ├── schema/
│   │   ├── __init__.py
│   │   ├── config_schema_v2.py      # JSON schema definitions
│   │   └── schema_validator.py      # Schema validation
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── json_storage.py          # JSON save/load functions
│   │   ├── pickle_compat.py         # Backward compatibility
│   │   └── config_migration.py      # Migration utilities
│   └── defaults/
│       ├── __init__.py
│       ├── default_configs.py       # Default configuration database
│       └── default_detector.py      # Default detection logic
├── prisma/
│   ├── __init__.py
│   ├── api_client.py                 # Enhanced API client
│   ├── api_endpoints.py              # Endpoint definitions
│   ├── api_utils.py                  # API utilities
│   ├── pull/
│   │   ├── __init__.py
│   │   ├── config_pull.py            # Main pull functionality
│   │   ├── pull_orchestrator.py      # Pull orchestration
│   │   ├── folder_capture.py         # Folder capture
│   │   ├── snippet_capture.py        # Snippet capture
│   │   ├── rule_capture.py           # Security rule capture
│   │   ├── object_capture.py         # Object capture
│   │   └── profile_capture.py        # Profile capture
│   ├── push/
│   │   ├── __init__.py
│   │   ├── config_push.py            # Main push functionality
│   │   ├── push_orchestrator.py      # Push orchestration
│   │   ├── conflict_resolver.py     # Conflict resolution
│   │   └── push_validator.py         # Pre-push validation
│   └── dependencies/
│       ├── __init__.py
│       ├── dependency_resolver.py    # Dependency resolution
│       ├── dependency_graph.py       # Dependency graph
│       └── dependency_validator.py   # Dependency validation
├── cli/
│   ├── __init__.py
│   ├── pull_cli.py                   # Pull CLI interface
│   ├── push_cli.py                   # Push CLI interface
│   └── push_wizard.py                # Push wizard
├── tests/
│   ├── __init__.py
│   ├── conftest.py                   # Test fixtures
│   ├── test_config_schema.py
│   ├── test_api_client.py
│   ├── test_dependencies.py
│   ├── test_pull_e2e.py
│   ├── test_push_e2e.py
│   └── test_workflow.py
├── docs/
│   ├── README_COMPREHENSIVE_CONFIG.md
│   ├── PULL_PUSH_GUIDE.md
│   ├── JSON_SCHEMA.md
│   └── MIGRATION_GUIDE.md
└── [existing files...]
```

## Testing Strategy

### Unit Testing
- Test individual functions and classes
- Mock API responses
- Test error handling
- Target: 80%+ code coverage

### Integration Testing
- Test API client with mock server
- Test configuration storage/retrieval
- Test dependency resolution
- Test default detection

### End-to-End Testing
- Full pull workflow
- Full push workflow
- Configuration migration
- Error recovery scenarios

### Validation Testing
- JSON schema validation
- Dependency validation
- Configuration completeness
- Default detection accuracy

## Risk Mitigation

### Technical Risks
1. **API Rate Limiting**: Implement rate limiting and retry logic
2. **Large Configurations**: Implement pagination and streaming
3. **API Changes**: Version API endpoints and handle deprecations
4. **Data Loss**: Implement backup before push operations

### Operational Risks
1. **Push Failures**: Implement rollback mechanism
2. **Configuration Conflicts**: Provide clear conflict resolution
3. **Missing Dependencies**: Validate before push
4. **Default Detection Errors**: Allow manual override

## Success Criteria

### Phase 1 Success
- ✅ JSON storage implemented and tested
- ✅ Migration from pickle to JSON working
- ✅ Enhanced API client functional

### Phase 2 Success
- ✅ All security policy elements captured
- ✅ Folders and snippets fully supported
- ✅ Objects and profiles captured correctly

### Phase 3 Success
- ✅ Default detection accuracy > 95%
- ✅ Default exclusion working correctly
- ✅ User override functionality working

### Phase 4 Success
- ✅ Complete pull functionality working
- ✅ All dependencies resolved correctly
- ✅ Pull reports accurate and useful

### Phase 5 Success
- ✅ Push functionality working
- ✅ Conflict resolution functional
- ✅ Push validation preventing errors
- ✅ Basic wizard operational

### Phase 6 Success
- ✅ Test coverage > 80%
- ✅ All critical paths tested
- ✅ Dependency validation working
- ✅ E2E tests passing

### Overall Success
- ✅ Can pull complete configuration from source tenant
- ✅ Can push configuration to target tenant
- ✅ Default configurations excluded appropriately
- ✅ All dependencies validated
- ✅ JSON format human-readable and editable
- ✅ Comprehensive test suite in place

## Future Enhancements (Post-MVP)

1. **Advanced Push Wizard**: GUI-based wizard with visual selection
2. **Configuration Comparison**: Diff between configurations
3. **Configuration Templates**: Reusable configuration templates
4. **Scheduled Pulls**: Automated periodic configuration pulls
5. **Change Tracking**: Track configuration changes over time
6. **Multi-Tenant Support**: Manage multiple tenant configurations
7. **Configuration Analytics**: Analyze configuration patterns
8. **Panorama Support**: Extend to Panorama-managed environments
9. **Configuration Validation Rules**: Custom validation rules
10. **Export Formats**: Support for other formats (YAML, XML)

## Timeline Summary

- **Weeks 1-2**: Foundation & Infrastructure
- **Weeks 3-5**: Security Policy Capture
- **Weeks 6-7**: Default Configuration Detection
- **Weeks 8-10**: Pull Functionality
- **Weeks 11-13**: Push Functionality
- **Weeks 14-16**: Testing Framework
- **Weeks 17-18**: Documentation & Polish

**Total Estimated Duration**: 18 weeks (4.5 months)

## Next Steps

1. **Review and Approve Plan**: Review this plan with stakeholders
2. **Create Branch**: Create `feature/comprehensive-config-capture` branch
3. **Set Up Development Environment**: Prepare development tools and environment
4. **Begin Phase 1**: Start with foundation and infrastructure work
5. **Regular Reviews**: Weekly progress reviews and adjustments

## Notes

- This plan focuses on SCM-managed environments first
- Panorama support will be added in a future phase
- The JSON format allows for manual editing if needed
- Testing framework is integrated throughout, not an afterthought
- Backward compatibility is maintained for existing configurations
