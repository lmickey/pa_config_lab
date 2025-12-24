# Dependency Validation Test Plan

## Overview
This test plan covers comprehensive dependency validation across all configuration types to ensure the DependencyResolver and push conflict resolution work correctly.

## Test Data Location
`/home/lindsay/Code/pa_config_lab/tests/test_data/dependency_test_config.json`

---

## Dependency Scenarios Covered

### 1. Infrastructure Dependencies (Multi-Level)

#### Scenario 1A: Service Connection Chain
**Selected**: `Service-Connection-AWS` only  
**Expected Dependencies**:
- `IPSec-Tunnel-AWS`
- `IKE-Gateway-AWS`
- `IKE-Crypto-Strong`
- `IPSec-Crypto-Strong`

**Test**: 
```python
def test_service_connection_dependencies():
    selected = {'infrastructure': {'service_connections': [get_item('Service-Connection-AWS')]}}
    resolver = DependencyResolver(selected, full_config)
    required = resolver.find_required_dependencies()
    
    assert 'ipsec_tunnels' in required['infrastructure']
    assert any(t['name'] == 'IPSec-Tunnel-AWS' for t in required['infrastructure']['ipsec_tunnels'])
    assert 'ike_gateways' in required['infrastructure']
    assert any(g['name'] == 'IKE-Gateway-AWS' for g in required['infrastructure']['ike_gateways'])
    assert 'ike_crypto_profiles' in required['infrastructure']
    assert 'ipsec_crypto_profiles' in required['infrastructure']
```

#### Scenario 1B: Multiple Service Connections Sharing Dependencies
**Selected**: `Service-Connection-AWS` + `Service-Connection-Azure`  
**Expected Dependencies**:
- `IPSec-Tunnel-AWS`, `IPSec-Tunnel-Azure`
- `IKE-Gateway-AWS`, `IKE-Gateway-Azure`
- `IKE-Crypto-Strong` (shared by both!)
- `IPSec-Crypto-Strong` (shared by both!)

**Test**: Validate that shared dependencies are deduplicated

#### Scenario 1C: Remote Network Dependencies
**Selected**: `Remote-Network-HQ` only  
**Expected Dependencies**:
- `IPSec-Tunnel-HQ`
- `IKE-Gateway-HQ`
- `IKE-Crypto-AES256`
- `IPSec-Crypto-AES256`

---

### 2. Security Policy Dependencies

#### Scenario 2A: Security Rule with Object Dependencies
**Selected**: `Rule-With-Object-Dependencies` only  
**Expected Dependencies**:
- **Addresses**: `Internal-Network`, `VPN-Users`, `External-Servers`, `Web-Servers`
- **Address Groups**: `Address-Group-1`, `Address-Group-2`
- **Service Group**: `Service-Group-1`
- **Services** (via group): `Custom-TCP-8080`, `Custom-TCP-9000`, `Custom-UDP-5000`
- **Application Group**: `App-Group-1`
- **Security Profile Group**: `Security-Profile-Group-1`
- **Profiles** (via group): `URL-Filter-Profile-1`, `File-Block-Profile-1`, `AV-Profile-1`, `Anti-Spyware-Profile-1`, `Vuln-Profile-1`

**Test**:
```python
def test_security_rule_object_dependencies():
    selected = {
        'folders': [{
            'name': 'Dependency Test Folder',
            'security_rules': [get_rule('Rule-With-Object-Dependencies')]
        }]
    }
    resolver = DependencyResolver(selected, full_config)
    required = resolver.find_required_dependencies()
    
    folder = required['folders'][0]
    assert 'objects' in folder
    assert 'addresses' in folder['objects']
    assert len(folder['objects']['addresses']) >= 4
    assert 'address_groups' in folder['objects']
    assert 'service_groups' in folder['objects']
    assert 'profiles' in folder
    assert 'security_profile_groups' in folder['profiles']
```

#### Scenario 2B: Nested Group Dependencies
**Selected**: `Nested-Address-Group` only  
**Expected Dependencies** (recursive):
- `Address-Group-1` (nested group)
- `VPN-Users`, `Internal-Network` (via Address-Group-1)
- `DMZ-Host-1`, `DMZ-Host-2` (direct members)

**Test**: Validate recursive group expansion

#### Scenario 2C: Security Rule with Authentication Profile
**Selected**: `Rule-With-Auth-Profile` only  
**Expected Dependencies**:
- `URL-Filter-Profile-1`, `File-Block-Profile-1`, `AV-Profile-1`, `Anti-Spyware-Profile-1`, `Vuln-Profile-1`
- `HIP-Profile-Mobile`
- `HIP-Object-Antivirus`, `HIP-Object-Firewall` (via HIP profile)

---

### 3. Profile Dependencies

#### Scenario 3A: Authentication Profile Dependencies
**Selected**: `LDAP-Auth-Profile` only  
**Expected Dependencies**:
- LDAP Server Profile: `LDAP-Server-Corp` (if exists in config)

**Selected**: `RADIUS-Auth-Profile` only  
**Expected Dependencies**:
- RADIUS Server Profile: `RADIUS-Server-MFA` (if exists)

**Selected**: `SAML-Auth-Profile` only  
**Expected Dependencies**:
- Certificate: `SAML-Signing-Cert` (if exists)

**Test**: Handle missing server profiles gracefully (mark as external dependency)

#### Scenario 3B: Security Profile Group Dependencies
**Selected**: `Security-Profile-Group-1` only  
**Expected Dependencies**:
- All 5 member profiles

---

### 4. HIP Dependencies

#### Scenario 4A: HIP Profile Dependencies
**Selected**: `HIP-Profile-Mobile` only  
**Expected Dependencies**:
- `HIP-Object-Antivirus`
- `HIP-Object-Firewall`

**Test**: Parse HIP match expression ("X and Y")

---

### 5. Cross-Section Dependencies

#### Scenario 5A: Mobile Agent Profile Dependencies
**Selected**: Mobile User config with `Mobile-Agent-Profile-Corp`  
**Expected Dependencies**:
- `LDAP-Auth-Profile` (authentication profile from folder)
- Cascading to LDAP server profile

**Test**: Validate infrastructure → folder cross-references

---

## Push Conflict Resolution Tests

### Scenario 6A: Skip Dependency (Valid)
**Setup**:
- Destination already has: `IKE-Crypto-Strong` (identical config)
- User selects: `Service-Connection-AWS` + all dependencies
- User chooses: **Skip** `IKE-Crypto-Strong`

**Expected**: ✅ Valid - crypto profile exists and matches

**Test**:
```python
def test_skip_existing_identical_dependency():
    conflict_resolutions = {
        'IKE-Crypto-Strong': 'skip'
    }
    validator = DependencyValidator(selected_config, dest_config, conflict_resolutions)
    issues = validator.validate()
    assert len(issues) == 0  # No issues - item exists and is compatible
```

### Scenario 6B: Skip Dependency (Invalid - Missing)
**Setup**:
- Destination does NOT have: `IPSec-Crypto-Strong`
- User selects: `Service-Connection-AWS` + all dependencies
- User chooses: **Skip** `IPSec-Crypto-Strong`

**Expected**: ❌ Error - cannot skip a dependency that doesn't exist at destination

**Test**:
```python
def test_skip_missing_dependency():
    conflict_resolutions = {
        'IPSec-Crypto-Strong': 'skip'
    }
    validator = DependencyValidator(selected_config, dest_config, conflict_resolutions)
    issues = validator.validate()
    assert len(issues) > 0
    assert any('IPSec-Crypto-Strong' in issue and 'missing' in issue.lower() for issue in issues)
```

### Scenario 6C: Skip Dependency (Invalid - Different Config)
**Setup**:
- Destination has: `IKE-Crypto-Strong` but with DIFFERENT settings (e.g., SHA1 instead of SHA256)
- User selects: `Service-Connection-AWS` + all dependencies
- User chooses: **Skip** `IKE-Crypto-Strong`

**Expected**: ⚠️ Warning - crypto profile exists but config differs (may cause issues)

---

### Scenario 7A: Rename Dependency
**Setup**:
- User selects: `Service-Connection-AWS` + all dependencies
- Destination has conflicting: `IPSec-Crypto-Strong` (different config)
- User chooses: **Rename** `IPSec-Crypto-Strong` → `IPSec-Crypto-Strong-NEW`

**Expected**: 
- `IPSec-Tunnel-AWS` config must be rewritten to reference `IPSec-Crypto-Strong-NEW`
- All dependent items are notified of name change

**Test**:
```python
def test_rename_dependency_updates_references():
    conflict_resolutions = {
        'IPSec-Crypto-Strong': 'rename'
    }
    renamed_items = {
        'IPSec-Crypto-Strong': 'IPSec-Crypto-Strong-NEW'
    }
    
    orchestrator = SelectivePushOrchestrator(api_client, progress_callback)
    updated_config = orchestrator._rewrite_references(selected_config, renamed_items)
    
    tunnel = next(t for t in updated_config['infrastructure']['ipsec_tunnels'] if t['name'] == 'IPSec-Tunnel-AWS')
    assert tunnel['auto_key']['ipsec_crypto_profile'] == 'IPSec-Crypto-Strong-NEW'
```

### Scenario 7B: Rename with Multiple Dependents
**Setup**:
- User selects: `Address-Group-1`, `Address-Group-2`, `Rule-With-Object-Dependencies`
- Both groups reference `VPN-Users`
- User renames: `VPN-Users` → `VPN-Users-NEW`

**Expected**:
- Both `Address-Group-1` and `Address-Group-2` updated to reference `VPN-Users-NEW`
- Rule still references groups (no change needed)

---

### Scenario 8A: Overwrite with Correct Order
**Setup**:
- User selects: `Service-Connection-AWS` + all dependencies
- All items exist at destination (different configs)
- User chooses: **Overwrite** all

**Expected**: Push in topological order (dependencies first):
1. `IKE-Crypto-Strong`, `IPSec-Crypto-Strong`
2. `IKE-Gateway-AWS`
3. `IPSec-Tunnel-AWS`
4. `Service-Connection-AWS`

**Test**:
```python
def test_overwrite_respects_dependency_order():
    resolver = DependencyResolver(selected_config, selected_config)
    graph = resolver.build_dependency_graph()
    push_order = graph.get_topological_order()
    
    # Crypto profiles should be pushed before gateways
    crypto_idx = push_order.index('IKE-Crypto-Strong')
    gateway_idx = push_order.index('IKE-Gateway-AWS')
    assert crypto_idx < gateway_idx
    
    # Gateways before tunnels
    tunnel_idx = push_order.index('IPSec-Tunnel-AWS')
    assert gateway_idx < tunnel_idx
    
    # Tunnels before service connections
    sc_idx = push_order.index('Service-Connection-AWS')
    assert tunnel_idx < sc_idx
```

---

### Scenario 9: CIE Detection (Unpushable)
**Setup**:
- User selects: Authentication profile with `method.cloud` (Cloud Identity Engine)

**Expected**: ❌ Profile greyed out, unselectable, error message

**Test**: Already implemented in `_uses_cie()`

---

## Test Implementation Priority

### Phase 1: Enhance DependencyResolver (Current)
- [ ] 1. Add address group → addresses resolution
- [ ] 2. Add service group → services resolution
- [ ] 3. Add security rule → objects resolution
- [ ] 4. Add security rule → profile resolution
- [ ] 5. Add profile group → profiles resolution
- [ ] 6. Add HIP profile → HIP objects resolution
- [ ] 7. Add nested group resolution (recursive)

### Phase 2: Add Dependency Validation for Push
- [ ] 1. Create `DependencyValidator` class
- [ ] 2. Implement `validate_skip()` - check if skipped items exist at destination
- [ ] 3. Implement `validate_rename()` - generate rename map
- [ ] 4. Implement `_rewrite_references()` in orchestrator
- [ ] 5. Add topological sort validation

### Phase 3: Unit Tests
- [ ] 1. Create `tests/test_dependency_resolver_advanced.py`
- [ ] 2. Test each scenario from above
- [ ] 3. Add performance test (1000+ objects)

### Phase 4: Integration Tests
- [ ] 1. Full workflow: Select → Validate → Push
- [ ] 2. Test with real API (destination tenant)
- [ ] 3. Rollback on error

---

## Test Execution Checklist

### Manual Testing Steps
1. Load `dependency_test_config.json` into Review tab
2. Navigate to Select Components tab
3. For each scenario above:
   - Select only the primary item
   - Click "Continue to Push"
   - Verify dependency dialog shows expected items
   - Accept dependencies
   - Verify summary shows all items
4. Test conflict resolution:
   - Connect to destination tenant
   - Preview push
   - Try different skip/rename/overwrite combinations
   - Verify warnings/errors appear correctly

### Automated Testing
```bash
# Run dependency tests
pytest tests/test_dependency_resolver_advanced.py -v

# Run with coverage
pytest tests/test_dependency_resolver_advanced.py --cov=prisma/dependencies --cov-report=html
```

---

## Success Criteria
- ✅ All 9 scenario categories pass
- ✅ No missing dependencies
- ✅ No extra/incorrect dependencies
- ✅ Topological order respected
- ✅ Reference rewriting works for all types
- ✅ CIE detection works
- ✅ UI shows clear dependency information
- ✅ Conflict resolution prevents invalid operations

---

## Known Limitations (Document)
1. **External Dependencies**: Server profiles, certificates not in config cannot be validated
2. **Application Dependencies**: Built-in applications (ssl, web-browsing) not checked
3. **Dynamic Groups**: Groups with dynamic filters not expanded
4. **Partial Configs**: If source config is incomplete, dependency resolution may be incomplete
