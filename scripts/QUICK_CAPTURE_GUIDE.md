# Quick Capture Command - New Configurations

You've added configurations in two phases:

## Phase 1 - Basic Objects & Profiles
1. ✅ Schedules (4 objects)
2. ✅ Service Groups (4 objects)
3. ❌ URL Filtering Profiles (skipped - API doesn't work)
4. ✅ Antivirus Profiles (combined with WildFire)
5. ✅ WildFire Profiles (combined with Antivirus)

## Phase 2 - QoS, VPN, Mobile Agent
1. ✅ QoS Configuration (profiles + policy rules)
2. ✅ VPN Tunnels (IKE/IPsec crypto, gateways, tunnels)
3. ✅ Mobile User App Configuration (agent profiles)
4. ⏭️ HTTP Header Profiles (skipped - no good use cases)

---

## 🚀 Quick Capture Command - ALL NEW CONFIGS

Capture **all 11 updated types** in 2-3 minutes:

```bash
python scripts/capture_production_examples.py \
  --tenant "SCM Lab" \
  --types \
    schedule \
    service_group \
    antivirus_profile \
    wildfire_profile \
    qos_profile \
    qos_policy_rule \
    ike_crypto_profile \
    ipsec_crypto_profile \
    ike_gateway \
    ipsec_tunnel \
    agent_profile
```

Or use the convenience script:
```bash
bash scripts/quick_capture_all_new.sh
```

---

## 🎯 Quick Capture Command - PHASE 2 ONLY

If you already captured Phase 1, capture just the **7 new Phase 2 types**:

```bash
python scripts/capture_production_examples.py \
  --tenant "SCM Lab" \
  --types \
    qos_profile \
    qos_policy_rule \
    ike_crypto_profile \
    ipsec_crypto_profile \
    ike_gateway \
    ipsec_tunnel \
    agent_profile
```

---

## 📋 What This Does

**Captures only:**
- `schedule` - Your new schedule objects (4)
- `service_group` - Your new service groups (4)
- `antivirus_profile` - Updated/new profiles
- `wildfire_profile` - Updated/new profiles

**Skips:** Everything else you already captured (saves ~18 minutes!)

---

## 📊 Expected Results

**Before:**
- schedule: 0 examples
- service_group: 0 examples
- antivirus_profile: 0 examples
- wildfire_profile: 0 examples

**After:**
- schedule: 4 examples ✅
- service_group: 4 examples ✅
- antivirus_profile: ~2-3 examples ✅
- wildfire_profile: ~2-3 examples ✅

**Total:** ~12-14 new examples in 1-2 minutes!

---

## 💡 Other Useful Commands

### Capture a single type
```bash
python scripts/capture_production_examples.py --type schedule
```

### Capture multiple types
```bash
python scripts/capture_production_examples.py --types tag address_object security_rule
```

### Capture from specific folder only
```bash
python scripts/capture_production_examples.py --types schedule --folder "Mobile Users"
```

### Increase examples per type
```bash
python scripts/capture_production_examples.py --types schedule --max 20
```

---

## 🎯 Full Capture (When You Need It)

If you want to recapture everything (takes ~20 minutes):
```bash
python scripts/capture_production_examples.py --tenant "SCM Lab"
```

---

## ✅ What You Updated

The script now supports:
- `--type <single_type>` - Capture one type
- `--types <type1> <type2> ...` - Capture multiple types (NEW!)
- Filters work across all categories (objects, profiles, policies, infrastructure)
- Much faster for incremental captures!
