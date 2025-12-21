# Comprehensive Configuration Capture - Quick Reference

## Overview
Transform the Prisma Access configuration tool into a comprehensive capture, storage, and migration system for SCM-managed Prisma Access tenants.

## Key Features

### 1. Comprehensive Configuration Capture
- **Security Policies**: Full capture of security rules from folders and snippets
- **Objects**: Address objects/groups, service objects/groups, applications, URL categories, EDLs
- **Profiles**: Authentication profiles, security profiles (AV, AS, Vulnerability, URL Filtering, etc.), decryption profiles
- **Infrastructure**: Service connections, remote networks, mobile agent settings

### 2. Default Configuration Detection
- Automatically identify default configurations
- Exclude defaults from exports (configurable)
- Document detected defaults for reference

### 3. JSON Storage Format
- Human-readable JSON format (replaces pickle)
- Enables manual editing if needed
- Versioned schema for future compatibility
- Migration path from existing pickle files

### 4. Pull/Push Workflow
- **Pull**: Extract complete configuration from source SCM tenant
- **Push**: Deploy configuration to target SCM tenant
- **Selective Push**: Choose what to push (future wizard)
- **Validation**: Pre-push dependency and conflict checking

### 5. Automated Testing
- Comprehensive test suite for all configuration fields
- Dependency validation tests
- End-to-end workflow tests
- Target: 80%+ code coverage

## Implementation Phases

| Phase | Duration | Focus |
|-------|----------|-------|
| Phase 1 | Weeks 1-2 | Foundation & Infrastructure (JSON storage, API client) |
| Phase 2 | Weeks 3-5 | Security Policy Capture (folders, snippets, rules, objects, profiles) |
| Phase 3 | Weeks 6-7 | Default Configuration Detection |
| Phase 4 | Weeks 8-10 | Pull Functionality |
| Phase 5 | Weeks 11-13 | Push Functionality |
| Phase 6 | Weeks 14-16 | Testing Framework |
| Phase 7 | Weeks 17-18 | Documentation & Polish |

**Total: 18 weeks (4.5 months)**

## New Configuration Structure

```json
{
  "metadata": { "version", "created", "source_tenant", "source_type" },
  "infrastructure": { "shared_infrastructure_settings", "mobile_agent", "service_connections" },
  "security_policies": {
    "folders": [ { "name", "security_rules", "objects", "profiles" } ],
    "snippets": [ { "name", "security_rules", "objects", "profiles" } ]
  },
  "authentication": { "authentication_profiles", "saml_profiles" },
  "network": { "ike_crypto_profiles", "ipsec_crypto_profiles", "ike_gateways" },
  "defaults": { "detected_defaults", "excluded_configs" }
}
```

## Key API Endpoints

### Security Policy
- `/security-policy/folders` - List and get folders
- `/security-policy/security-rules` - Security rules
- `/security-policy/snippets` - Snippets

### Objects
- `/addresses`, `/address-groups`
- `/services`, `/service-groups`
- `/applications`, `/application-groups`
- `/url-categories`, `/external-dynamic-lists`

### Profiles
- `/authentication-profiles`
- `/security-profiles/{type}` (antivirus, anti-spyware, vulnerability, etc.)
- `/decryption-profiles/{type}`

## New File Structure

```
pa_config_lab/
├── config/
│   ├── schema/          # JSON schema definitions
│   ├── storage/         # JSON storage functions
│   └── defaults/        # Default detection
├── prisma/
│   ├── api_client.py    # Enhanced API client
│   ├── pull/            # Pull functionality
│   ├── push/            # Push functionality
│   └── dependencies/    # Dependency resolution
├── cli/                 # CLI interfaces
├── tests/               # Test suite
└── docs/                # Documentation
```

## Dependencies to Track

- Security Rules → Address Objects/Groups
- Security Rules → Service Objects/Groups
- Security Rules → Applications
- Security Rules → Security Profiles
- Security Rules → Authentication Profiles
- Address Groups → Address Objects
- Service Groups → Service Objects
- Application Groups → Applications

## Success Criteria

✅ Pull complete configuration from source tenant  
✅ Push configuration to target tenant  
✅ Default configurations excluded appropriately  
✅ All dependencies validated  
✅ JSON format human-readable and editable  
✅ Comprehensive test suite in place  

## Branch Strategy

- **Branch**: `feature/comprehensive-config-capture`
- **Base**: `main`
- **Merge Strategy**: Feature branch, merge after completion and testing

## Next Steps

1. Review `UPGRADE_PLAN.md` for detailed specifications
2. Begin Phase 1: Foundation & Infrastructure
3. Set up development environment
4. Create initial JSON schema
5. Implement API client enhancements

## Notes

- Focus on SCM-managed environments first
- Panorama support in future phase
- Maintain backward compatibility with existing configs
- Testing integrated throughout development
