# Model Validation & Testing Plan - Using Production Examples

**Date:** January 2, 2026  
**Status:** Ready to Begin  
**Context:** We have 223 production examples captured from SCM Lab

---

## 🎯 Objectives

Use the 223 captured production examples to:
1. **Validate Models** - Find missing properties, fix validation issues
2. **Create Test Cases** - Build comprehensive test suite
3. **Enhance API Client** - Handle real-world edge cases

---

## Phase 1: Model Validation Against Production Data ⭐

### 1.1: Audit Captured Examples vs Models

**Goal:** Identify gaps between real configs and our models

**Tasks:**
- [ ] Create validation script that loads all 223 examples
- [ ] Try to instantiate model classes from each example
- [ ] Capture validation errors, missing fields, type mismatches
- [ ] Generate comprehensive report

**Script:** `scripts/validate_models_against_examples.py`

**Expected Output:**
```
Model Validation Report
=======================
Total examples: 223
Successfully loaded: 180 (81%)
Failed to load: 43 (19%)

Issues by type:
  - Missing properties: 25 cases
  - Type mismatches: 12 cases
  - Validation errors: 6 cases
  
Critical issues:
  1. schedule: 'schedule_type' structure doesn't match
  2. service_group: Missing 'tag' property
  3. ipsec_tunnel: 'anti_replay' validation too strict
  ...
```

### 1.2: Fix Model Issues

**Goal:** Update models based on validation report

**Process:**
1. Review each issue
2. Check SCM API documentation for correct schema
3. Update model classes in `config/models/`
4. Re-run validation until 95%+ success rate

**Priority Order:**
1. **Critical types** (10 examples each): schedule, service_group, security rules, profiles
2. **Medium types** (3-9 examples): VPN configs, QoS, agent profiles
3. **Low types** (1-2 examples): crypto profiles, certificates

### 1.3: Create Property Discovery Report

**Goal:** Document all properties found in prod vs what we modeled

**Script:** `scripts/discover_properties.py`

**Output:** `tests/examples/production/property_analysis.md`

**Content:**
- Complete field inventory per type
- Properties we're missing
- Properties we have but never seen in prod
- Optional vs required field analysis

---

## Phase 2: Test Case Generation from Examples 🧪

### 2.1: Create Test Fixtures

**Goal:** Convert production examples into test fixtures

**Structure:**
```
tests/fixtures/
├── objects/
│   ├── address_objects.json        (10 examples)
│   ├── service_groups.json         (10 examples)
│   └── schedules.json               (10 examples)
├── profiles/
│   ├── security_profiles.json      (50 examples)
│   └── qos_profiles.json           (2 examples)
├── policies/
│   ├── security_rules.json         (10 examples)
│   └── qos_rules.json              (10 examples)
└── infrastructure/
    ├── vpn_configs.json            (15 examples)
    └── agent_profiles.json         (3 examples)
```

**Script:** `scripts/generate_test_fixtures.py`

### 2.2: Generate Model Tests

**Goal:** Auto-generate unit tests from fixtures

**Files to Create:**
- `tests/models/test_objects_from_fixtures.py`
- `tests/models/test_profiles_from_fixtures.py`
- `tests/models/test_policies_from_fixtures.py`
- `tests/models/test_infrastructure_from_fixtures.py`

**Test Pattern:**
```python
def test_address_object_from_prod_example_1(address_object_fixture_1):
    """Test address object can be loaded from real prod config"""
    obj = AddressObject.from_dict(address_object_fixture_1)
    assert obj.name == "trust-network"
    assert obj.folder == "Mobile Users"
    assert obj.to_dict() == address_object_fixture_1  # Round-trip test

def test_all_address_objects_load(address_object_fixtures):
    """Test all 10 prod address objects can be loaded"""
    for fixture in address_object_fixtures:
        obj = AddressObject.from_dict(fixture)
        assert obj is not None
        assert obj.validate() is True
```

### 2.3: Generate API Client Tests

**Goal:** Create integration tests using real examples

**Files to Create:**
- `tests/api/test_api_client_with_fixtures.py`
- `tests/api/test_api_response_parsing.py`

**Test Pattern:**
```python
def test_parse_schedule_response(schedule_fixture):
    """Test API client can parse real schedule response"""
    # Mock API response with real prod data
    mock_response = {"data": [schedule_fixture]}
    
    # Test client parsing
    schedules = client._parse_response(mock_response, Schedule)
    assert len(schedules) == 1
    assert schedules[0].name == schedule_fixture["name"]

def test_all_object_types_parse(all_fixtures):
    """Test client can parse all 28 prod object types"""
    for type_name, fixtures in all_fixtures.items():
        model_class = get_model_class(type_name)
        for fixture in fixtures:
            obj = model_class.from_dict(fixture)
            assert obj is not None
```

### 2.4: Create Validation Tests

**Goal:** Test model validation with real edge cases

**File:** `tests/models/test_validation_edge_cases.py`

**Examples:**
- Test schedule with non-recurring time window
- Test service group with mix of built-in and custom services
- Test security rule with all optional fields
- Test VPN config with minimal vs maximal settings

---

## Phase 3: API Client Enhancement 🔧

### 3.1: Identify API Client Issues

**Goal:** Find issues when parsing real production data

**Tasks:**
- [ ] Run API client against all fixtures
- [ ] Check for parsing errors
- [ ] Check for missing field handling
- [ ] Check for type conversion issues
- [ ] Document all issues

**Script:** `scripts/audit_api_client_parsing.py`

### 3.2: Fix API Client Parsing

**Goal:** Handle all edge cases found in production

**Focus Areas:**
1. **Null handling** - Some fields might be null vs missing
2. **Type coercion** - String vs int vs bool variations
3. **Nested structures** - Complex objects like schedule_type
4. **Default values** - Built-in objects with both folder and snippet
5. **Error messages** - Better error context for debugging

**Files to Update:**
- `prisma/api_client.py` - Core parsing logic
- `config/models/base.py` - Base model validation
- `config/models/factory.py` - Factory pattern handling

### 3.3: Add Better Error Handling

**Goal:** Improve error messages and recovery

**Enhancements:**
```python
# Before
raise ValueError("Cannot set both folder and snippet")

# After
raise ValueError(
    f"Cannot set both folder and snippet for {self.name}. "
    f"Found folder='{self.folder}' and snippet='{self.snippet}'. "
    f"This usually indicates a predefined object from Palo Alto Networks. "
    f"Raw config: {self.raw_config}"
)
```

### 3.4: Add Response Validation

**Goal:** Validate API responses match expected schema

**New Feature:** Response validator that checks:
- Required fields are present
- Types match expectations  
- Enums have valid values
- References are valid

**File:** `prisma/response_validator.py` (NEW)

### 3.5: Performance Optimization

**Goal:** Optimize based on real data patterns

**Opportunities:**
- Batch processing for multiple objects
- Caching for repeated lookups
- Lazy loading for large configs
- Memory efficiency for 200+ items

---

## Implementation Order (Recommended)

### Week 1: Model Validation (Priority 1)
**Days 1-2:**
- [ ] Create validation script
- [ ] Run against all 223 examples
- [ ] Generate validation report

**Days 3-5:**
- [ ] Fix critical model issues (schedules, service groups)
- [ ] Fix medium model issues (VPN, QoS)
- [ ] Re-validate until 95%+ success

**Day 6:**
- [ ] Create property discovery report
- [ ] Document findings
- [ ] Update model documentation

**Deliverable:** All models handle 95%+ of production examples

### Week 2: Test Generation (Priority 2)
**Days 1-2:**
- [ ] Generate test fixtures from examples
- [ ] Organize fixtures by type
- [ ] Create fixture loading utilities

**Days 3-5:**
- [ ] Generate model unit tests
- [ ] Generate API client tests
- [ ] Generate validation tests
- [ ] Run all tests, fix failures

**Day 6:**
- [ ] Review test coverage
- [ ] Add missing test cases
- [ ] Document test structure

**Deliverable:** Comprehensive test suite using real prod data

### Week 3: API Client Enhancement (Priority 3)
**Days 1-2:**
- [ ] Audit API client parsing
- [ ] Identify all issues
- [ ] Prioritize fixes

**Days 3-4:**
- [ ] Fix parsing issues
- [ ] Improve error handling
- [ ] Add response validation

**Days 5-6:**
- [ ] Performance optimization
- [ ] Integration testing
- [ ] Documentation updates

**Deliverable:** Robust API client handling all prod scenarios

---

## Success Metrics

### Model Validation
- ✅ 95%+ of examples load successfully
- ✅ All critical properties discovered
- ✅ Zero crashes on real data
- ✅ Validation errors are actionable

### Test Coverage
- ✅ 200+ tests generated from fixtures
- ✅ 90%+ code coverage on models
- ✅ 85%+ code coverage on API client
- ✅ All 28 types have test cases

### API Client
- ✅ Handles all real-world edge cases
- ✅ Better error messages (with context)
- ✅ Response validation implemented
- ✅ Performance optimized for large configs

---

## Quick Start - First Steps

**Right now, let's start with Phase 1.1:**

1. Create validation script
2. Run against your 223 examples
3. See what breaks
4. Fix the models

**Command to run:**
```bash
python scripts/validate_models_against_examples.py \
  --input tests/examples/production/raw \
  --output tests/examples/production/validation_report.md
```

This will give us a clear picture of what needs fixing!

---

## Related Work (Can be parallel)

While doing model validation, we can also:
- ❌ Skip GUI enhancements (save for later)
- ❌ Skip documentation (save for later)  
- ❌ Skip infrastructure GUI (save for later)
- ✅ Do minimal API endpoint fixes if needed
- ✅ Do schema updates if needed

---

**Ready to start with Phase 1.1 - Model Validation Script?** 🚀
