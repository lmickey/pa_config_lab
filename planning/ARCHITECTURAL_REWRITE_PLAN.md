# Architectural Rewrite Plan - Object-Oriented Configuration Model

**Date:** January 2, 2026  
**Branch:** main  
**Major Version:** 3.x (rewrite)  
**Purpose:** Migrate from dictionary-based to object-oriented configuration model with improved API architecture

---

## Executive Summary

This document outlines the phased approach to rewrite the configuration system with:

1. **Object-Oriented Model** - ConfigItem base class with specialized subclasses
2. **Simplified API Client** - Each ConfigItem defines its own endpoint
3. **Efficient Bulk Operations** - One query per type for all folders/snippets
4. **Automated Versioning** - Git-based version management
5. **Comprehensive Testing** - Tests and examples for all new models
6. **New Configuration Endpoints** - Add missing API endpoints (Schedules, HTTP Headers, Decryption Rules, etc.)

---

## Design Decisions

### Configuration Model: Option B (Object-Oriented)

**Architecture:**
- Configuration items as objects with properties (ConfigItem base class)
- `folder` and `snippet` properties are mutually exclusive for most items, one must be set
- **EXCEPTION**: Tags can have both `folder` AND `snippet` simultaneously
- Lightweight properties: `has_parent`, `has_child`, `has_dependencies`
- `deleted` flag and `delete_success` status for tracking
- `refresh()` method for individual items with post-action UI prompts (defer UI for now)
- Each ConfigItem subclass defines its `api_endpoint` property
- All API interaction through class instances

### Folder and Snippet Relationship (IMPORTANT)

**Folder Hierarchy:**
- Folders form a hierarchical structure (All → Shared → Remote Networks, Mobile Users, etc.)
- Configuration items in folders inherit the folder context
- Items have `folder` property when directly associated with a folder

**Snippet Associations:**
- Snippets are NOT hierarchical - they can be applied at any folder level(s)
- Snippets can be applied to MULTIPLE folders
- Snippets themselves have a `folder` property indicating where they're applied
- Snippets can be shared across tenants via trust relationships (future workflow)
- Configuration items IN a snippet have `snippet` property instead of `folder`
- **Key Point**: If snippet is not assigned to a folder, its child config objects won't have a `folder` property

**Item Location Logic:**
```python
# Most configuration items:
if item.folder:
    location = f"folder: {item.folder}"
elif item.snippet:
    location = f"snippet: {item.snippet}"

# Tags (special case):
if item.folder and item.snippet:
    location = f"folder: {item.folder}, snippet: {item.snippet}"
elif item.folder:
    location = f"folder: {item.folder}"
elif item.snippet:
    location = f"snippet: {item.snippet}"
```

**Migration Strategy:**
- Migrate away from `prisma/api_endpoints.py` - remove dependencies
- Move generic API interactions to `prisma/api/` (from `prisma/pull/`)
- Workflow-specific components remain in `prisma/pull/` and `prisma/push/`

**Versioning:**
- Format: `<major>.<merge_count>.<commit_count>`
- Major = 3 for rewrite
- Merge count increments only on merges to main
- Commit count increments on every commit
- Dynamic update in main menu

**Deferred Features:**
- `clone()` method - not needed now, add to backlog
- Refresh UI prompts - defer until refresh method is tested

---

## Understanding Configuration Hierarchy

### Folder Hierarchy

```
All (Global)
├── Shared (Prisma Access)
│   ├── Remote Networks
│   ├── Mobile Users
│   ├── Mobile Users Explicit Proxy
│   └── Service Connections
└── [Custom Folders can be added at any level]
```

**Folder Rules:**
- Hierarchical structure with parent-child relationships
- Configuration inherits folder context
- Items in folders have `folder` property set
- Example: `{"name": "web-rule", "folder": "Mobile Users"}`

### Snippet Associations

```
Snippet: "production-snippet"
├── Applied to: ["Mobile Users", "Remote Networks"]  # Can apply to multiple
├── Contains: [Objects, Profiles, Rules, HIP]
└── Shareable: Can be shared across tenants (future)
```

**Snippet Rules:**
- NOT hierarchical - flat structure
- Can be applied to ANY folder(s)
- Can be applied to MULTIPLE folders simultaneously
- Snippets have `folder` property indicating where they're applied
- Configuration items IN snippet have `snippet` property (not `folder`)
- **Important**: If snippet not assigned to folder, child items have NO `folder` property
- Can be shared across tenants via trust relationships (future workflow)

### Tag Exception

Tags are UNIQUE - they can have BOTH `folder` AND `snippet`:

```json
{
  "name": "Web Security Global",
  "folder": "All",
  "snippet": "Web-Security-Default",
  "color": "Green"
}
```

This allows tags to be:
- Defined at a folder level (visible in that folder)
- Associated with a snippet (travels with the snippet)
- Shared when snippet is shared across tenants

### Configuration Item Location Examples

**Folder-based Address:**
```json
{
  "name": "internal-network",
  "folder": "Mobile Users",
  "ip_netmask": "192.168.1.0/24"
}
```

**Snippet-based Address:**
```json
{
  "name": "dmz-network",
  "snippet": "datacenter-snippet",
  "ip_netmask": "10.100.0.0/24"
}
```

**Tag with Both:**
```json
{
  "name": "production",
  "folder": "All",
  "snippet": "production-snippet",
  "color": "Red"
}
```

**Snippet Definition:**
```json
{
  "name": "production-snippet",
  "folder": "Mobile Users",  // Applied at this folder
  "type": "custom"
}
```

---

## Phase 1: Foundation (COMPLETE ✅)

### Day 1: Base Classes and Versioning ✅

**Status:** COMPLETE - Commits: 28177cb, 46f3aa5, aaf14b3

**Implemented:**

1. **Created `config/models/` package**
   - `__init__.py` - Exports base classes
   - `base.py` - ConfigItem, ObjectItem, PolicyItem, ProfileItem, RuleItem

2. **Base ConfigItem class with:**
   - Properties: `folder`, `snippet` (mutually exclusive validation)
   - Properties: `has_parent`, `has_child`, `has_dependencies`
   - Properties: `deleted`, `delete_success`
   - Methods: `to_dict()`, `from_dict()`, `validate()`, `rename()`
   - Methods: `mark_for_deletion()`, `unmark_for_deletion()`
   - Methods: `create()`, `update()`, `delete()`, `refresh()`
   - Class method: `get()` for fetching from API

3. **Specialized base classes:**
   - `PolicyItem(ConfigItem)` - For policies/rules
   - `ObjectItem(ConfigItem)` - For network objects
   - `ProfileItem(ConfigItem)` - For security profiles
   - `RuleItem(PolicyItem)` - Adds `is_enabled`, `position` properties

4. **Automated versioning (`config/version.py`):**
   - Git-based version calculation
   - Format: `3.<merge_count>.<commit_count>`
   - Fallback to `3.0.0` if git unavailable

5. **Test infrastructure:**
   - `tests/config/models/test_base.py` - 15 tests, all passing
   - Test structure mirrors source code
   - Mock classes for testing (MockAddressObject, MockSecurityRule)

6. **Example configurations:**
   - `tests/examples/` - 22 example JSON files
   - Categories: objects (6), policies (4), profiles (5), infrastructure (7)
   - `tests/examples/loader.py` - Utility for loading examples
   - Documentation: README.md, INDEX.md
   - Test integration: 3 tests using example loader

**Version:** 3.1.137

---

## Phase 2: Object Models (IN PROGRESS)

### Day 2: Create Specific Object Model Classes ✅

**Goal:** Create concrete classes for network objects (addresses, services, applications, tags, etc.)

**Status:** COMPLETE - v3.1.140

**Tasks:**

1. **Create `config/models/objects.py`** ✅
   - `Tag(ConfigItem)` - **SPECIAL**: Can have both folder AND snippet
   - `AddressObject(ObjectItem)` - IP addresses, ranges, FQDNs
   - `AddressGroup(ObjectItem)` - Static and dynamic groups
   - `ServiceObject(ObjectItem)` - TCP/UDP services
   - `ServiceGroup(ObjectItem)` - Service collections
   - `ApplicationObject(ObjectItem)` - Custom applications
   - `ApplicationGroup(ObjectItem)` - Application collections
   - `ApplicationFilter(ObjectItem)` - Application filters
   - `Schedule(ObjectItem)` - Time-based schedules (NEW ENDPOINT)

2. **Implement specific properties per class:** ✅
   - Override `_compute_dependencies()` for each type
   - Override `_validate_specific()` for type-specific validation
   - Add type-specific properties (e.g., `ip_netmask`, `port`, `color`, etc.)
   - **Added base tag methods**: `has_tags` property, `get_tags()` method

3. **API endpoint definitions:**
   - Each class defines its `api_endpoint` class property
   - Each class defines its `item_type` class property

4. **Add test examples:** ⭐ COMPLETE ✅
   - Created in `tests/examples/config/models/objects/`:
     - `tag_minimal.json` - Basic tag ✅
     - `tag_full.json` - Complete tag with comments ✅
     - `tag_with_snippet.json` - Tag with both folder AND snippet ✅
     - `tag_no_color.json` - Tag without color ✅
     - `address_fqdn.json` - FQDN-based address ✅
     - `address_range.json` - IP range address ✅
     - `address_group_dynamic.json` - Dynamic group with filter ✅
     - `address_with_tags.json` - Address demonstrating tags ✅
     - `service_group_minimal.json` - Service group ✅
     - `application_group_minimal.json` - Application group ✅
     - `application_filter_minimal.json` - Application filter ✅
     - `schedule_minimal.json` - Recurring schedule ✅
     - `schedule_non_recurring.json` - Date-specific schedule ✅

5. **Create `tests/config/models/test_objects.py`** ⭐ COMPLETE ✅
   - TestTag: 7 tests (including special folder+snippet case)
   - TestTagSupport: 3 tests (has_tags, get_tags)
   - TestAddressObject: 7 tests
   - TestAddressGroup: 5 tests (static/dynamic, dependencies)
   - TestServiceObject: 5 tests (TCP/UDP, validation)
   - TestServiceGroup: 3 tests
   - TestApplicationObject: 3 tests
   - TestApplicationGroup: 2 tests
   - TestApplicationFilter: 3 tests
   - TestSchedule: 4 tests
   - TestObjectSerialization: 2 tests
   - TestObjectDeletion: 2 tests
   - **Total: 46 tests, all passing** ✅

6. **Update INDEX.md with new examples** ⭐ COMPLETE ✅

**Deliverables:** ✅
- `config/models/objects.py` with 9 classes (8 + Tag) ✅
- 13 new example configurations (exceeded 7+ target) ✅
- `tests/config/models/test_objects.py` with 46 tests (exceeded 20+ target) ✅
- All 61 tests passing (15 base + 46 objects) ✅
- `config/models/base.py` updated with has_tags/get_tags ✅
- 91% code coverage on objects.py ✅

---

### Day 3: Create Profile Model Classes

**Goal:** Create concrete classes for security profiles

**Tasks:**

1. **Create `config/models/profiles.py`**
   - `AuthenticationProfile(ProfileItem)` - SAML, LDAP, etc.
   - `DecryptionProfile(ProfileItem)` - SSL/TLS decryption
   - `URLFilteringProfile(ProfileItem)` - URL category blocking
   - `AntivirusProfile(ProfileItem)` - Virus scanning
   - `AntiSpywareProfile(ProfileItem)` - Spyware protection
   - `VulnerabilityProfile(ProfileItem)` - Vulnerability protection
   - `FileBlockingProfile(ProfileItem)` - File type blocking
   - `WildfireProfile(ProfileItem)` - Wildfire analysis
   - `ProfileGroup(ProfileItem)` - Security profile bundles
   - `HIPProfile(ProfileItem)` - Host Information Profile
   - `HIPObject(ProfileItem)` - HIP match criteria
   - `HTTPHeaderProfile(ProfileItem)` - HTTP header insertion (NEW ENDPOINT)
   - `CertificateProfile(ProfileItem)` - Certificate profiles (NEW ENDPOINT)
   - `OCSPResponder(ProfileItem)` - OCSP responders (NEW ENDPOINT)
   - `SCEPProfile(ProfileItem)` - SCEP profiles (NEW ENDPOINT)
   - `QoSProfile(ProfileItem)` - QoS profiles (NEW ENDPOINT)

2. **Implement profile-specific features:**
   - CIE profile detection and exclusion
   - Default profile handling
   - Profile group member validation

3. **Add test examples:** ⭐ NEW
   - Expand `tests/examples/config/models/profiles/`:
     - `authentication_profile_ldap.json` - LDAP auth
     - `authentication_profile_cie.json` - CIE profile (for testing exclusion)
     - `antivirus_profile_minimal.json`
     - `anti_spyware_profile_minimal.json`
     - `vulnerability_profile_minimal.json`
     - `file_blocking_profile_minimal.json`
     - `wildfire_profile_minimal.json`
     - `profile_group_custom.json` - Non-default group
     - `hip_object_minimal.json` - HIP match criteria
     - `http_header_profile_minimal.json`
     - `certificate_profile_minimal.json`
     - `qos_profile_minimal.json`

4. **Create `tests/config/models/test_profiles.py`** ⭐ NEW
   - Test each profile class
   - Test CIE profile exclusion logic
   - Test profile group member validation
   - Test default profile detection
   - Use example loader

5. **Update INDEX.md** ⭐ NEW

**Deliverables:**
- `config/models/profiles.py` with 16 classes
- 12+ new example configurations
- `tests/config/models/test_profiles.py` with 30+ tests
- All tests passing

---

### Day 4: Create Policy/Rule Model Classes ✅

**Status:** COMPLETE - Commits: 98af385, df1a1b7  
**Version:** v3.1.145

**Scope Clarification:** NAT and PBF rules are only available in on-prem firewall (ngfw-shared) 
configuration, NOT in Prisma Access folder/snippet workflows. These were removed from this phase.
NAT configuration may be added as properties within ServiceConnection infrastructure objects (Day 5).

**Implemented:**

1. **Created `config/models/policies.py`** ✅
   - `SecurityRule(RuleItem)` - Security policy rules (90% coverage)
   - `DecryptionRule(RuleItem)` - Decryption rules (NEW ENDPOINT)
   - `AuthenticationRule(RuleItem)` - Auth rules (NEW ENDPOINT)
   - `QoSPolicyRule(RuleItem)` - QoS rules (NEW ENDPOINT)
   - ❌ ~~`NATRule`~~ - Removed (not applicable to Prisma Access)
   - ❌ ~~`PBFRule`~~ - Removed (not applicable to Prisma Access)

2. **Implemented rule-specific features:** ✅
   - Rule position tracking
   - Rule enablement state
   - Rule move operations (to bottom of rulebase)
   - Dependency extraction from rule fields
   - Smart 'any' value handling in dependency detection
   - Profile group dependency detection

3. **Added test examples:** ✅ (6 examples)
   - `security_rule_allow_apps.json` - Allow collaboration apps
   - `security_rule_deny.json` - Deny high-risk apps
   - `decryption_rule_minimal.json` - Decrypt outbound
   - `decryption_rule_no_decrypt.json` - No-decrypt financial
   - `authentication_rule_minimal.json` - Require SAML auth
   - `qos_rule_minimal.json` - Prioritize voice/video

4. **Created `tests/config/models/test_policies.py`** ✅ (21 tests)
   - TestSecurityRule: 6 tests (zones, dependencies, profile groups, disabled, validation)
   - TestDecryptionRule: 4 tests (decrypt/no-decrypt actions, dependencies, validation)
   - TestAuthenticationRule: 2 tests (creation, dependencies)
   - TestQoSPolicyRule: 2 tests (creation, dependencies)
   - TestRuleProperties: 2 tests (position, enabled state)
   - TestPolicySerialization: 2 tests
   - TestPolicyDeletion: 2 tests
   - TestPolicyWithTags: 1 test

5. **Updated INDEX.md** ✅

**Deliverables:**
- ✅ `config/models/policies.py` with 4 classes (revised from 6)
- ✅ 6 new example configurations (revised from 8+, NAT/PBF removed)
- ✅ `tests/config/models/test_policies.py` with 21 tests (revised from 25+)
- ✅ All tests passing (111 total: 15 base + 46 objects + 29 profiles + 21 policies)
- ✅ 88% code coverage for policies.py

---

### Day 5: Create Infrastructure Model Classes ✅

**Status:** COMPLETE - Commit: 3d32851  
**Version:** v3.1.147

**Scope Note:** ServiceConnection includes NAT configuration properties (hard-coded config,
not rule-based policy from Day 4). All infrastructure items REQUIRE folder, not snippet.

**Implemented:**

1. **Created `config/models/infrastructure.py`** ✅
   - `IKECryptoProfile(ConfigItem)` - Phase 1 crypto (encryption, auth, DH groups)
   - `IPsecCryptoProfile(ConfigItem)` - Phase 2 crypto (ESP settings, PFS)
   - `IKEGateway(ConfigItem)` - IKE peer configuration (depends on IKECryptoProfile)
   - `IPsecTunnel(ConfigItem)` - IPsec tunnel (depends on IKEGateway, IPsecCryptoProfile)
   - `ServiceConnection(ConfigItem)` - Remote networks (depends on IPsecTunnel, includes NAT)
   - `AgentProfile(ConfigItem)` - GlobalProtect agent settings
   - `Portal(ConfigItem)` - GlobalProtect portal (may depend on CertificateProfile)
   - `Gateway(ConfigItem)` - GlobalProtect gateway (may depend on CertificateProfile)

2. **Implemented infrastructure-specific features:** ✅
   - Deep dependency chains (Service Connection → IPsec Tunnel → IKE Gateway → Crypto Profiles)
   - Folder requirement enforced in `__init__` (raises ValueError if snippet without folder)
   - Reference validation in `_validate_specific()` for each class
   - NAT configuration properties: `nat_pool`, `source_nat` in ServiceConnection
   - Override `has_dependencies` property for proper dependency detection in nested configs

3. **Added test examples:** ✅ (15 examples, exceeded 8+ target)
   - `ike_crypto_profile_minimal.json`, `ike_crypto_profile_strong.json`
   - `ipsec_crypto_profile_minimal.json`, `ipsec_crypto_profile_pfs.json`
   - `ike_gateway_minimal.json`, `ike_gateway_certificate.json`
   - `ipsec_tunnel_minimal.json`, `ipsec_tunnel_full.json`
   - `service_connection_minimal.json`, `service_connection_with_bgp.json`, `service_connection_with_nat.json`
   - `agent_profile_minimal.json`, `agent_profile_always_on.json`
   - `portal_minimal.json`, `gateway_minimal.json`

4. **Created `tests/config/models/test_infrastructure.py`** ✅ (39 tests)
   - TestIKECryptoProfile: 4 tests (creation, strong crypto, folder requirement, validation)
   - TestIPsecCryptoProfile: 4 tests (creation, PFS, folder requirement, validation)
   - TestIKEGateway: 5 tests (minimal/cert, dependencies, folder requirement, validation)
   - TestIPsecTunnel: 5 tests (minimal/full, dependencies, folder requirement, validation)
   - TestServiceConnection: 7 tests (minimal/BGP/NAT, dependencies, backup SC, folder requirement)
   - TestAgentProfile: 4 tests (minimal/always-on, folder requirement, validation)
   - TestPortal: 3 tests (creation, folder requirement, cert profile dependency)
   - TestGateway: 3 tests (creation, folder requirement, cert profile dependency)
   - TestInfrastructureDependencyChains: 1 test (full dependency chain validation)
   - TestInfrastructureSerialization: 1 test
   - TestInfrastructureDeletion: 2 tests

5. **Updated INDEX.md** ✅

**Deliverables:**
- ✅ `config/models/infrastructure.py` with 8 classes
- ✅ 15 new example configurations (exceeded 8+ target)
- ✅ `tests/config/models/test_infrastructure.py` with 39 tests (exceeded 25+ target)
- ✅ All 150 tests passing (15 base + 46 objects + 29 profiles + 21 policies + 39 infrastructure)
- ✅ Total examples: 67

---

## Phase 3: Container Classes

### Day 6: Create Container Classes

**Goal:** Create classes to organize configuration items (FolderConfig, SnippetConfig, Configuration)

**Tasks:**

1. **Create `config/models/containers.py`**
   - `FolderConfig` - Represents a folder and its contents
   - `SnippetConfig` - Represents a snippet and its contents
   - `Configuration` - Top-level container for entire config

2. **Implement container features:**
   - Add/remove items
   - Query items by name, type, location
   - Filter items (by default status, enabled/disabled, etc.)
   - Bulk operations (mark all for deletion, validate all)
   - Dependency resolution across containers

3. **Add test examples:** ⭐ NEW
   - Create `tests/examples/config/containers/`:
     - `folder_mobile_users.json` - Complete folder with items
     - `folder_remote_networks.json` - Folder with infrastructure
     - `snippet_production.json` - Complete snippet
     - `configuration_minimal.json` - Full config with folders/snippets

4. **Create `tests/config/models/test_containers.py`** ⭐ NEW
   - Test FolderConfig creation and manipulation
   - Test SnippetConfig creation and manipulation
   - Test Configuration aggregation
   - Test querying across containers
   - Test bulk operations
   - Use example loader

5. **Update INDEX.md** ⭐ NEW

**Deliverables:**
- `config/models/containers.py` with 3 classes
- 4+ new example configurations
- `tests/config/models/test_containers.py` with 30+ tests
- All tests passing

---

## Phase 4: Factory and Utilities

### Day 7: Create Factory Pattern

**Goal:** Create factory for instantiating correct ConfigItem subclasses from raw data

**Tasks:**

1. **Create `config/models/factory.py`**
   - `ConfigItemFactory` class
   - Method: `create_from_dict(item_type, raw_config)` → ConfigItem
   - Method: `create_from_api_response(endpoint, response)` → List[ConfigItem]
   - Auto-detection of item type from data structure
   - Registration system for new item types

2. **Add test scenarios:** ⭐ NEW
   - Create `tests/examples/config/factory/`:
     - `api_response_addresses.json` - API list response
     - `api_response_security_rules.json`
     - `api_response_with_defaults.json` - Mix of default/custom
     - `unknown_item_type.json` - For error handling testing

3. **Create `tests/config/models/test_factory.py`** ⭐ NEW
   - Test factory with all object types
   - Test auto-detection logic
   - Test API response parsing
   - Test error handling for unknown types
   - Use example loader

4. **Update INDEX.md** ⭐ NEW

**Deliverables:**
- `config/models/factory.py`
- 4+ new example configurations
- `tests/config/models/test_factory.py` with 20+ tests
- All tests passing

---

## Phase 5: API Integration

### Day 8-9: Refactor API Client

**Goal:** Simplify API client to work with ConfigItem objects

**Tasks:**

1. **Move generic API code:**
   - Create `prisma/api/` directory
   - Move generic helpers from `prisma/pull/` to `prisma/api/`
   - Keep workflow-specific code in `prisma/pull/` and `prisma/push/`

2. **Update API client:**
   - Add methods that work with ConfigItem objects
   - `create_item(item: ConfigItem) -> bool`
   - `update_item(item: ConfigItem) -> bool`
   - `delete_item(item: ConfigItem) -> bool`
   - `get_items(item_class: Type[ConfigItem], location: str, is_snippet: bool) -> List[ConfigItem]`

3. **Deprecate `api_endpoints.py`:**
   - Move all endpoint definitions to respective ConfigItem classes
   - Update all imports
   - Remove file

4. **Add test scenarios:** ⭐ NEW
   - Create `tests/examples/api/`:
     - `create_response_success.json`
     - `create_response_error.json`
     - `update_response_success.json`
     - `delete_response_409_conflict.json`
     - `get_response_paginated.json`

5. **Create `tests/prisma/api/test_api_client.py`** ⭐ NEW
   - Test API client methods with ConfigItem objects
   - Mock API responses
   - Test error handling
   - Test pagination
   - Use example loader

6. **Update INDEX.md** ⭐ NEW

**Deliverables:**
- `prisma/api/` directory created
- `prisma/api_client.py` updated
- `prisma/api_endpoints.py` removed
- 5+ new test response examples
- `tests/prisma/api/test_api_client.py` with 25+ tests
- All imports updated

---

## Phase 6: Bulk Operations & Optimization

### Day 10-11: Efficient Bulk Capture

**Goal:** Rewrite pull orchestrator to use bulk queries (one per type for all folders/snippets)

**Tasks:**

1. **Rewrite pull orchestrator:**
   - Build folder/snippet hierarchy first
   - Bulk capture all items of each type (one query per type)
   - Distribute items to folders/snippets based on their `folder`/`snippet` field
   - Use ConfigItemFactory to instantiate objects
   - Leave infrastructure capture unchanged (already optimized)

2. **Add new configuration endpoints:** ⭐ VERIFY EXAMPLES COVER NEW TYPES
   - Schedules: `https://api.sase.paloaltonetworks.com/sse/config/v1/schedules`
   - HTTP Header Profiles: `https://api.sase.paloaltonetworks.com/sse/config/v1/http-header-profiles`
   - Decryption Rules: `https://api.sase.paloaltonetworks.com/sse/config/v1/decryption-rules`
   - Authentication Rules: `https://api.sase.paloaltonetworks.com/sse/config/v1/authentication-rules`
   - QoS Rules: `https://api.sase.paloaltonetworks.com/sse/config/v1/qos-policy-rules`
   - QoS Profiles: `https://api.sase.paloaltonetworks.com/sse/config/v1/qos-profiles`
   - Certificate Profiles: `https://api.sase.paloaltonetworks.com/sse/config/v1/certificate-profiles`
   - OCSP: `https://api.sase.paloaltonetworks.com/sse/config/v1/ocsp-responder`
   - SCEP: `https://api.sase.paloaltonetworks.com/sse/config/v1/scep-profiles`
   - URL Categories: `https://api.sase.paloaltonetworks.com/sse/config/v1/url-categories`
   - Local Users: `https://api.sase.paloaltonetworks.com/sse/config/v1/local-users`
   - User Groups: `https://api.sase.paloaltonetworks.com/sse/config/v1/local-user-groups`

3. **Verify example coverage:** ⭐ NEW
   - Review `tests/examples/config/models/` for all new endpoint types
   - Add missing examples as needed
   - Ensure minimal + full examples for each new type

4. **Update tests:** ⭐ NEW
   - Update existing pull tests to work with object model
   - Test bulk capture efficiency
   - Test distribution to correct folders/snippets
   - Verify all new endpoints are captured

**Deliverables:**
- Rewritten `prisma/pull/pull_orchestrator.py`
- All new endpoints implemented
- Example coverage verified for all types
- Updated tests

---

## Phase 7: Push Operations

### Day 12-13: Update Push Orchestrator

**Goal:** Update push operations to work with ConfigItem objects

**Tasks:**

1. **Update push orchestrator:**
   - Work with ConfigItem objects instead of dictionaries
   - Use ConfigItem.create(), .update(), .delete() methods
   - Use ConfigItem.has_dependencies property
   - Leverage renamed items with updated references
   - Implement proper dependency-aware deletion (top-down)
   - Implement proper creation (bottom-up)

2. **Add scenarios for testing:** ⭐ NEW
   - Create `tests/examples/push_scenarios/`:
     - `overwrite_with_dependencies.json` - Item + dependencies to overwrite
     - `rename_with_references.json` - Item that's referenced by others
     - `conflict_409_reference.json` - Deletion blocked by reference
     - `skip_parent_skip_children.json` - Parent skip cascades
     - `create_rule_position_bottom.json` - Security rule positioning

3. **Create `tests/prisma/push/test_push_orchestrator.py`** ⭐ NEW
   - Test push with SKIP strategy
   - Test push with OVERWRITE strategy
   - Test push with RENAME strategy
   - Test dependency-aware deletion
   - Test reference updates on rename
   - Test error handling (409 conflicts, 400 errors)
   - Test rule positioning
   - Use example loader

4. **Update INDEX.md** ⭐ NEW

**Deliverables:**
- Updated `prisma/push/selective_push_orchestrator.py`
- 5+ new push scenario examples
- `tests/prisma/push/test_push_orchestrator.py` with 30+ tests
- All tests passing

---

## Phase 7.5: Production Example Capture & Analysis

### Day 13.5: Capture Real-World Examples

**Goal:** Pull production configurations to create comprehensive test examples and validate model implementation

**Why This Phase:**
- All model classes are complete (objects, policies, profiles, infrastructure)
- Factory pattern is implemented
- Before GUI integration, we validate with real data
- Identify any missing properties or edge cases
- Create comprehensive test suite with production data

**Tasks:**

1. **Create/repurpose capture script:**
   - Create `scripts/capture_production_examples.py`
   - Use existing API client and pull orchestrator
   - Connect to production tenant (or lab tenant with production-like config)
   - Capture all configuration types we've modeled
   - Save raw API responses to `tests/examples/production/raw/`

2. **Analyze captured configurations:** ⭐ NEW
   - Create `scripts/analyze_config_properties.py`
   - Parse all captured configurations
   - Identify property types for each config item:
     - **String properties**: name, description, comments
     - **Number properties**: risk, port, position, timeout
     - **Boolean properties**: disabled, enabled, source_nat
     - **List properties**: members, tag, source, destination
     - **Dict properties**: protocol, bgp_peer, ssl_protocol_settings
     - **Reference properties**: profile_group, ike_gateway, authentication_profile
   - Document required vs optional fields
   - Identify common patterns and edge cases
   - Generate property type matrix for each model class

3. **Create sanitized production examples:** ⭐ NEW
   - Create `scripts/sanitize_examples.py`
   - Process raw captures and sanitize:
     - Replace real IPs with RFC 5737 test IPs (203.0.113.x, 198.51.100.x)
     - Replace real FQDNs with example.com/example.net
     - Replace passwords/secrets with "********"
     - Replace real names with generic names
     - Keep structure and relationships intact
   - Save to `tests/examples/production/`
   - Organize by type: objects/, policies/, profiles/, infrastructure/

4. **Validate models against production data:** ⭐ NEW
   - Create `scripts/validate_production_models.py`
   - Load production examples through ConfigItemFactory
   - Validate each item using ConfigItem.validate()
   - Test serialization/deserialization (to_dict/from_dict)
   - Identify any validation failures
   - Document missing properties or unsupported patterns

5. **Create comprehensive production test suite:** ⭐ NEW
   - Create `tests/config/models/test_production_examples.py`
   - Parametrized tests using all production examples
   - Test each example can be loaded
   - Test validation passes
   - Test serialization roundtrip
   - Test dependency detection
   - Test all property accessors
   - Document any failures or limitations

6. **Update models based on findings:** ⭐ NEW
   - Add missing properties discovered in production data
   - Add validation rules for discovered patterns
   - Update property accessors for new fields
   - Add edge case handling
   - Update documentation with production patterns

7. **Document property types:** ⭐ NEW
   - Create `docs/PROPERTY_TYPES.md`
   - Matrix of all configuration types and their properties
   - Type annotations for each property (str, int, bool, List[str], Dict, etc.)
   - Required vs optional indicators
   - Default values where applicable
   - Example values from production
   - Relationship indicators (references other config items)

**Deliverables:**
- `scripts/capture_production_examples.py` - Capture script
- `scripts/analyze_config_properties.py` - Property analysis
- `scripts/sanitize_examples.py` - Sanitization script
- `scripts/validate_production_models.py` - Validation script
- `tests/examples/production/` - Sanitized production examples (20-50 files)
- `tests/examples/production/raw/` - Raw API responses (for reference)
- `tests/config/models/test_production_examples.py` - Production test suite
- `docs/PROPERTY_TYPES.md` - Property type documentation
- Updated model classes with discovered properties
- Test results showing compatibility with production data

**Success Criteria:**
- At least 20 production examples captured
- All examples successfully sanitized
- 90%+ of production examples validate successfully
- All discovered property types documented
- Any incompatibilities documented with workarounds

---

## Phase 8: Migration & Cleanup

### Day 14.5: Migrate Existing Code

**Goal:** Update all existing code to use new object model (after production validation)

**Tasks:**

1. **Update GUI components:**
   - `gui/config_viewer.py` - Display ConfigItem objects
   - `gui/push_widget.py` - Work with ConfigItem selection
   - `gui/pull_widget.py` - Display pull progress with objects

2. **Update dependency resolver:**
   - Work with ConfigItem objects
   - Use ConfigItem.has_dependencies property
   - Use ConfigItem.get_dependencies() method

3. **Update default detector:**
   - Work with ConfigItem objects
   - Use ConfigItem.is_default flag

4. **Update schema validator:**
   - Validate ConfigItem objects
   - Use ConfigItem.validate() method

5. **Update storage:**
   - Serialize ConfigItem objects using .to_dict()
   - Deserialize using ConfigItemFactory

6. **Run integration tests:** ⭐ NEW
   - Test complete pull workflow
   - Test complete push workflow
   - Test complete POV workflow
   - Verify GUI displays correctly
   - Test with production tenant (if available)

**Deliverables:**
- All GUI components updated
- All utility modules updated
- Integration tests passing
- No references to old dictionary-based model

---

### Day 15.5: Final Testing & Documentation

**Goal:** Comprehensive testing and documentation with production validation

**Tasks:**

1. **Run full test suite:**
   - Unit tests: All model classes
   - Integration tests: Full workflows
   - Performance tests: Bulk operations
   - GUI tests: All workflows

2. **Update documentation:**
   - Update README with new architecture
   - Document all ConfigItem classes
   - Document factory usage
   - Document migration guide from v2.0

3. **Performance validation:**
   - Compare API call count (old vs new)
   - Verify bulk operations are efficient
   - Profile memory usage

4. **Validate with production examples:**
   - Use examples captured in Phase 7.5
   - Run production test suite
   - Verify all workflows with real data
   - Document any remaining incompatibilities

**Deliverables:**
- Complete test coverage report
- Updated documentation
- Performance report
- Production validation report
- Final compatibility matrix

---

## Testing Strategy Summary

### Test Types:

1. **Unit Tests** (`tests/config/models/`)
   - Test each ConfigItem class in isolation
   - Test properties, methods, validation
   - Use example loader for realistic data

2. **Integration Tests** (`tests/prisma/`)
   - Test API interactions
   - Test pull orchestrator
   - Test push orchestrator
   - Test dependency resolution

3. **GUI Tests** (`tests/gui/`)
   - Test component rendering
   - Test user interactions
   - Test workflow completion

4. **Example Coverage**
   - Minimal examples (required fields only)
   - Full examples (all optional fields)
   - Edge cases (defaults, disabled, dependencies)
   - Production examples (sanitized real data)

### Example Organization:

```
tests/examples/
├── config/models/
│   ├── objects/          # Object examples
│   ├── policies/         # Policy examples
│   ├── profiles/         # Profile examples
│   ├── infrastructure/   # Infrastructure examples
│   └── INDEX.md          # Quick reference
├── containers/           # Container examples
├── factory/              # Factory test data
├── api/                  # API response examples
├── push_scenarios/       # Push operation scenarios
├── production/           # Sanitized production data
├── loader.py             # Example loading utility
└── README.md             # Documentation
```

---

## Success Criteria

- ✅ All ConfigItem classes implemented
- ✅ All tests passing (target: 200+ tests)
- ✅ Example coverage for all item types
- ✅ API calls reduced (bulk operations)
- ✅ No references to old dictionary model
- ✅ Documentation complete
- ✅ Version: 3.2.x or higher
- ✅ Production validation successful

---

## Current Status

**Phase:** 1 - Foundation  
**Day:** 1 (Complete ✅)  
**Version:** 3.1.137  
**Next:** Day 2 - Object Models

**Completed:**
- ✅ Base ConfigItem class
- ✅ Specialized base classes (ObjectItem, PolicyItem, ProfileItem, RuleItem)
- ✅ Automated versioning
- ✅ Test infrastructure
- ✅ Example configurations (22 files)
- ✅ Example loader utility

**Ready for:** Day 2 - Create Specific Object Model Classes
