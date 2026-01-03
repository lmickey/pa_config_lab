# Recommended Lab Configurations for Better Test Coverage

Based on your current capture, here are configurations to add to your SCM Lab tenant to improve test coverage and use cases.

---

## 🔴 HIGH PRIORITY - Missing Completely (0 examples)

### 1. **Schedule Objects** ⭐ HIGH VALUE
**Current:** 0 examples  
**Why needed:** Schedules are commonly used in security rules for time-based policies

**What to create:**
- [ ] **Business-Hours** - Mon-Fri 8am-6pm
- [ ] **After-Hours** - Mon-Fri 6pm-8am + weekends
- [ ] **Maintenance-Window** - Sunday 2am-4am
- [ ] **Peak-Hours** - Mon-Fri 9am-11am, 1pm-4pm

**Use cases:** Time-based security rules, maintenance windows, backup schedules

---

### 2. **Service Groups** ⭐ HIGH VALUE
**Current:** 0 examples (but you have 11 service objects!)  
**Why needed:** Groups simplify rule management

**What to create:**
- [ ] **Web-Services** - Group: http, https
- [ ] **Email-Services** - Group: smtp, pop3, imap
- [ ] **Remote-Access** - Group: ssh, rdp, vnc
- [ ] **Database-Services** - Group: mysql, postgresql, mssql

**Use cases:** Security rules, application visibility

---

### 3. **URL Filtering Profiles** ⭐ MEDIUM VALUE
**Current:** 0 examples  
**Why needed:** Core security feature for web protection

**What to create:**
- [ ] **Standard-URL-Filtering** - Block high-risk categories, alert on medium
- [ ] **Strict-URL-Filtering** - Block high+medium risk categories
- [ ] **Allow-All-URL-Filtering** - Log-only mode for testing

**Use cases:** Web security policies, content filtering

---

### 4. **Antivirus Profiles** ⭐ MEDIUM VALUE
**Current:** 0 examples  
**Why needed:** Core security feature for malware protection

**What to create:**
- [ ] **Standard-AV** - Block on all protocols
- [ ] **Alert-Only-AV** - Alert mode for testing
- [ ] **Best-Practice-AV** - Following Palo Alto best practices

**Use cases:** Security profiles, threat prevention

---

### 5. **WildFire Profiles** ⭐ MEDIUM VALUE
**Current:** 0 examples  
**Why needed:** Advanced threat detection

**What to create:**
- [ ] **Standard-WildFire** - Forward all file types
- [ ] **Selective-WildFire** - Forward PE, APK, PDF, Office docs only

**Use cases:** Advanced threat detection, file analysis

---

### 6. **Application Objects (Custom)** ⭐ LOW VALUE
**Current:** 0 examples (uses built-in only)  
**Why needed:** For custom/internal applications

**What to create:**
- [ ] **Internal-App-1** - Custom signature for internal web app
- [ ] **Legacy-Database** - Custom ports for legacy systems

**Note:** Most environments use built-in apps, so low priority

---

### 7. **SCEP Profiles** ⭐ LOW VALUE
**Current:** 0 examples  
**Why needed:** Certificate enrollment automation

**What to create:**
- [ ] **Internal-CA-SCEP** - SCEP profile for internal CA

**Note:** Advanced feature, lower priority for testing

---

### 8. **OCSP Responders** ⭐ LOW VALUE
**Current:** 0 examples  
**Why needed:** Certificate validation

**What to create:**
- [ ] **Public-OCSP** - Public OCSP responder URL

**Note:** Advanced PKI feature, lower priority

---

## 🟡 MEDIUM PRIORITY - Limited Examples (1-5)

### 9. **QoS Profiles** ⭐ MEDIUM VALUE
**Current:** 1 example  
**Why needed:** Traffic prioritization

**What to create:**
- [ ] **Voice-QoS** - Prioritize VoIP traffic
- [ ] **Video-QoS** - Prioritize video conferencing
- [ ] **Bulk-Data-QoS** - Deprioritize bulk transfers

**Use cases:** Network performance, application prioritization

---

### 10. **HTTP Header Profiles** ⭐ MEDIUM VALUE
**Current:** 5 examples  
**Why needed:** Header manipulation for security/compliance

**What to create:**
- [ ] **Remove-Server-Header** - Strip server identification
- [ ] **Add-Security-Headers** - Add HSTS, CSP headers
- [ ] **Custom-Headers** - Add custom tracking/routing headers

**Use cases:** Security hardening, application routing

---

### 11. **VPN Infrastructure** ⭐ HIGH VALUE
**Current:** 2 IKE gateways, 2 IPsec tunnels, 2 crypto profiles each  
**Why needed:** Site-to-site VPN testing

**What to create:**
- [ ] **IKE-Gateway-Aggressive** - Aggressive mode gateway (less common)
- [ ] **IKE-Gateway-PSK** - Pre-shared key authentication
- [ ] **IPsec-Tunnel-Split** - Split tunnel configuration
- [ ] **IPsec-Tunnel-Route-Based** - Route-based VPN
- [ ] **Custom-IKE-Crypto** - Non-default crypto settings
- [ ] **Custom-IPsec-Crypto** - Non-default crypto settings

**Use cases:** Site-to-site VPN, remote access VPN

---

### 12. **Agent Profiles** ⭐ MEDIUM VALUE
**Current:** 1 example  
**Why needed:** GlobalProtect configuration

**What to create:**
- [ ] **Contractor-Agent** - Limited access profile
- [ ] **Admin-Agent** - Full access profile
- [ ] **Regional-Agent** - Location-specific profile

**Use cases:** GlobalProtect deployment, user segmentation

---

## 🟢 LOW PRIORITY - Good Coverage (6-10+ examples)

These types already have good coverage:
- ✅ **Address Objects** (10) - Excellent
- ✅ **Address Groups** (6) - Good (but create service groups!)
- ✅ **Tags** (10) - Excellent
- ✅ **Security Rules** (10) - Excellent
- ✅ **All other profiles** (10 each) - Excellent

---

## 📋 Suggested Configuration Scenarios

### Scenario 1: **Complete Web Security Stack** ⭐ RECOMMENDED
Create a full web security configuration:
1. URL Filtering Profile (Standard)
2. Antivirus Profile (Standard)
3. WildFire Profile (Standard)
4. Anti-Spyware Profile (already have)
5. Vulnerability Profile (already have)
6. Security Rule using all profiles
7. Schedule for after-hours testing

**Why:** Tests complete security profile integration

---

### Scenario 2: **Multi-Site VPN** ⭐ RECOMMENDED
Create additional VPN configurations:
1. 2-3 more IKE Gateways (different auth methods)
2. 2-3 more IPsec Tunnels (different routing modes)
3. Custom crypto profiles
4. Address objects for remote sites

**Why:** Tests VPN configuration variety

---

### Scenario 3: **Time-Based Access Control** ⭐ RECOMMENDED
Create time-based policies:
1. Business-Hours schedule
2. After-Hours schedule
3. Security rules using schedules
4. Different profiles for different times

**Why:** Tests schedule integration with policies

---

### Scenario 4: **Service-Based Segmentation**
Create service-based groups and rules:
1. Web-Services group
2. Email-Services group
3. Remote-Access group
4. Security rules per service group

**Why:** Tests service group usage patterns

---

## 🎯 Priority Action Plan

### Phase 1: High-Value Quick Wins (30 minutes)
1. ✅ Create 3-4 schedules (business hours, after hours, maintenance)
2. ✅ Create 3-4 service groups from existing service objects
3. ✅ Create 1 URL filtering profile
4. ✅ Create 1 antivirus profile
5. ✅ Create 1 WildFire profile

**Result:** Adds 10-12 new examples covering major gaps

---

### Phase 2: Security Profiles (20 minutes)
1. ✅ Create 2 more URL filtering profiles (variations)
2. ✅ Create 2 more antivirus profiles (variations)
3. ✅ Create 1 more WildFire profile
4. ✅ Update 1-2 security rules to use new profiles

**Result:** Complete security profile coverage

---

### Phase 3: VPN Expansion (30 minutes)
1. ✅ Create 2-3 more IKE crypto profiles (different algorithms)
2. ✅ Create 2-3 more IPsec crypto profiles (different algorithms)
3. ✅ Create 2-3 more IKE gateways (PSK, different modes)
4. ✅ Create 2-3 more IPsec tunnels (different types)

**Result:** Comprehensive VPN configuration examples

---

### Phase 4: Advanced Features (20 minutes)
1. ✅ Create 2-3 more QoS profiles
2. ✅ Create 2-3 more HTTP header profiles
3. ✅ Create 2-3 more agent profiles
4. ✅ Create 1 SCEP profile (if CA available)

**Result:** Advanced feature coverage

---

## 📊 Expected Outcome

After completing Phase 1-3:
- **Current:** 198 examples across 26 types
- **Expected:** ~250-280 examples across 32+ types
- **Coverage:** ~90% of common configuration patterns

---

## 🚫 What NOT to Create

**Don't waste time on:**
- ❌ Hundreds of address objects (10 is enough for testing)
- ❌ Custom applications (built-in apps are fine)
- ❌ Dozens of security rules (10 is enough for patterns)
- ❌ Production-specific configs (service connections, etc.)
- ❌ Gateway/Portal configs (API endpoints don't work)

---

## 💡 Testing Value

**Why this matters:**
- 🔍 Find missing properties in models
- ✅ Validate API client behavior
- 🧪 Create realistic test scenarios
- 📚 Document real-world usage patterns
- 🐛 Discover edge cases and bugs

---

## 🎬 Next Steps

1. Review Phase 1 configurations (quick wins)
2. Create those configs in SCM Lab UI
3. Rerun capture script: `python scripts/capture_production_examples.py --tenant "SCM Lab"`
4. Compare before/after coverage

**Estimated time for Phase 1:** 30 minutes  
**Estimated value:** High - fills major gaps in test coverage
