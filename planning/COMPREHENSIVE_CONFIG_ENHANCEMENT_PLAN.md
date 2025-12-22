# Comprehensive Configuration Capture Enhancement Plan

**Date:** December 21, 2025  
**Branch:** feature/comprehensive-config-capture  
**Purpose:** Enhance Prisma Access configuration capture to include infrastructure settings and restore missing features

---

## Executive Summary

This document outlines the enhancement plan to:
1. **Restore Missing Features** - Identify and restore features from the previous version (e.g., custom applications option)
2. **Add Infrastructure Components** - Extend capture to include Prisma Access infrastructure settings
3. **Maintain Rate Limiting** - Ensure all API interactions respect the 50 requests/minute limit
4. **Update GUI** - Enhance GUI to support new configuration options
5. **Comprehensive Testing** - Create test plan covering all new features

---

## 1. Missing Features Analysis

### 1.1 Custom Applications Feature ✅ (ALREADY IMPLEMENTED)

**Status:** **RESTORED AND FUNCTIONAL**

The custom applications feature was identified as missing but has been **fully implemented** in the current version:

#### Current Implementation:
- **CLI Implementation:** `cli/application_search.py`
  - Interactive search with 3-character minimum
  - Multi-select with visual confirmation
  - Search across all folders
  - Handles duplicates automatically

- **GUI Integration:** `gui/pull_widget.py`
  - Currently NOT exposed in GUI (needs enhancement)
  - Backend support exists via `pull_orchestrator.py`

- **Pull Orchestrator:** `prisma/pull/pull_orchestrator.py`
  - `application_names` parameter in `pull_complete_configuration()`
  - Line 473: Documented as "Optional list of custom application names to capture"
  - Applications excluded from default detection when specified

#### Evidence from Code:
```python
# cli/pull_cli.py (Lines 378-408)
# Ask about custom applications (default to no)
print("CUSTOM APPLICATIONS")
has_custom_apps = input(
    "Do you have any custom applications to capture? (y/n, default=n): "
).strip().lower()

if has_custom_apps == 'y':
    application_names = interactive_application_search(api_client)
```

**Recommendation:** 
- ✅ Feature exists in CLI
- ⚠️ Add to GUI (see Section 4.2)
- ✅ No restoration needed, just document

### 1.2 Other Potentially Missing Features

**Analysis Complete:** No other missing features identified from previous version. The current v2.0 implementation is comprehensive for security policies. The gaps are in **infrastructure components** (next section).

---

## 2. Prisma Access Infrastructure Components (NEW)

### 2.1 Currently Implemented Infrastructure

**From `config_schema_v2.py` (Lines 52-72):**
```python
"infrastructure": {
    "shared_infrastructure_settings": {},  # ✅ Implemented
    "mobile_agent": {},                    # ⚠️ Partial
    "service_connections": [],             # ⚠️ Partial
    "remote_networks": [],                 # ❌ Not implemented
}
```

**From `api_endpoints.py` (Lines 26-33):**
```python
# Infrastructure endpoints (SASE API)
SHARED_INFRASTRUCTURE_SETTINGS = f"{SASE_BASE_URL}/shared-infrastructure-settings"
MOBILE_AGENT_INFRASTRUCTURE = f"{SASE_BASE_URL}/mobile-agent/infrastructure-settings"

# Service Connections and Remote Networks (SASE API)
SERVICE_CONNECTIONS = f"{SASE_BASE_URL}/service-connections"
REMOTE_NETWORKS = f"{SASE_BASE_URL}/remote-networks"
```

**Status:** Endpoints defined but capture not fully implemented.

### 2.2 Missing Infrastructure Components

#### Priority 1: Remote Networks ❌
**Endpoint:** `/sse/config/v1/remote-networks`

**What to Capture:**
- Remote network names and descriptions
- BGP configuration
- IPsec tunnel associations
- Region assignments
- Subnets and CIDR blocks
- License types (FWAAS, GPCS)
- Encryption domains
- Bandwidth allocations
- Secondary WAN connectivity

**API Methods Needed:**
```python
# In api_client.py
def get_all_remote_networks(self, folder: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all remote networks (RN)."""
    
def get_remote_network(self, network_id: str) -> Dict[str, Any]:
    """Get specific remote network by ID."""
```

**Configuration Schema:**
```python
"remote_networks": [
    {
        "id": "rn-12345",
        "name": "Branch-Office-NYC",
        "folder": "Remote Networks",
        "region": "us-east-1",
        "license_type": "FWAAS-500",
        "bgp_peer": {
            "local_ip": "169.254.1.1",
            "peer_ip": "169.254.1.2",
            "secret": "<encrypted>",
            "peer_as": "65001"
        },
        "ipsec_tunnel": "ipsec-tunnel-id",
        "subnets": ["10.10.0.0/16", "10.20.0.0/16"],
        "secondary_wan": {
            "enabled": true,
            "ip_address": "203.0.113.2"
        },
        "protocol": {
            "bgp": {
                "enable": true,
                "local_ip_address": "169.254.1.1/30",
                "peer_ip_address": "169.254.1.2",
                "peer_as": "65001",
                "peering_type": "exchange-v4-over-v4"
            }
        }
    }
]
```

#### Priority 2: IPsec Tunnels ⚠️ (Partial)
**Endpoints:** 
- `/sse/config/v1/ipsec-tunnels` (defined, not fully captured)
- `/sse/config/v1/ike-gateways` (defined, not fully captured)
- `/sse/config/v1/ike-crypto-profiles` (defined, not fully captured)
- `/sse/config/v1/ipsec-crypto-profiles` (defined, not fully captured)

**What to Capture:**
- **IKE Crypto Profiles** - Phase 1 encryption/hash/DH group settings
- **IPsec Crypto Profiles** - Phase 2 encryption/authentication settings
- **IKE Gateways** - Gateway configurations, pre-shared keys, peer IDs
- **IPsec Tunnels** - Tunnel configurations linking gateways to crypto profiles

**Configuration Schema:**
```python
"network": {
    "ike_crypto_profiles": [
        {
            "id": "profile-id",
            "name": "IKE-AES256-SHA256-DH14",
            "folder": "Remote Networks",
            "encryption": ["aes-256-cbc"],
            "authentication": ["sha256"],
            "dh_group": ["group14"]
        }
    ],
    "ipsec_crypto_profiles": [
        {
            "id": "profile-id",
            "name": "IPsec-AES256-SHA256",
            "folder": "Remote Networks",
            "esp": {
                "encryption": ["aes-256-cbc"],
                "authentication": ["sha256"]
            },
            "lifetime": {"hours": 8}
        }
    ],
    "ike_gateways": [
        {
            "id": "gateway-id",
            "name": "IKE-GW-Branch",
            "folder": "Remote Networks",
            "authentication": {
                "pre_shared_key": "<encrypted>"
            },
            "peer_address": {
                "ip": "198.51.100.1"
            },
            "protocol": {
                "ikev2": {
                    "ike_crypto_profile": "IKE-AES256-SHA256-DH14"
                }
            }
        }
    ],
    "ipsec_tunnels": [
        {
            "id": "tunnel-id",
            "name": "IPsec-Branch-NYC",
            "folder": "Remote Networks",
            "auto_key": {
                "ike_gateway": [{"name": "IKE-GW-Branch"}],
                "ipsec_crypto_profile": "IPsec-AES256-SHA256"
            },
            "tunnel_monitor": {
                "enable": true,
                "destination_ip": "10.10.1.1"
            }
        }
    ]
}
```

#### Priority 3: Service Connections ⚠️ (Partial)
**Endpoint:** `/sse/config/v1/service-connections`

**Current Status:** Endpoint defined, basic capture may exist but needs enhancement.

**What to Capture:**
- Service Connection names and regions
- BGP configuration for SC
- IPsec tunnel configurations (to on-prem)
- Backup service connections
- Route advertisement settings
- QoS profiles

**Configuration Schema:**
```python
"service_connections": [
    {
        "id": "sc-12345",
        "name": "SC-DataCenter-Primary",
        "folder": "Service Connections",
        "region": "us-east-1",
        "bgp_peer": {
            "local_ip": "169.254.2.1/30",
            "peer_ip": "169.254.2.2",
            "peer_as": "65002",
            "secret": "<encrypted>"
        },
        "ipsec_tunnel": "ipsec-tunnel-id",
        "backup_SC": "sc-67890",
        "qos_profile": "qos-profile-id",
        "onboarding_type": "classic"
    }
]
```

#### Priority 4: Mobile User Infrastructure ❌
**Endpoints:**
- `/sse/config/v1/mobile-agent/infrastructure-settings` (defined)
- Possible additional endpoints for mobile user configs

**What to Capture:**
- **GlobalProtect Gateway Configurations**
  - Gateway names and addresses
  - Authentication profiles
  - Tunnel mode vs split tunnel settings
  - Client configurations

- **GlobalProtect Portal Configurations**
  - Portal names and addresses
  - Authentication methods
  - Client download configurations

- **Mobile User Regions**
  - Enabled regions for mobile users
  - Regional gateway assignments
  - Preferred/backup gateway configurations

- **Mobile User Subnets**
  - IP pool assignments per region
  - DNS server assignments
  - WINS server assignments (if applicable)

**Configuration Schema:**
```python
"mobile_users": {
    "infrastructure_settings": {
        "gp_gateways": [
            {
                "name": "GP-Gateway-US-East",
                "region": "us-east-1",
                "address": "gp-us-east.company.com",
                "authentication_profile": "auth-profile-id",
                "tunnel_mode": "full-tunnel",
                "client_settings": {
                    "dns_servers": ["8.8.8.8", "8.8.4.4"],
                    "wins_servers": [],
                    "ip_pool": "10.100.0.0/16"
                }
            }
        ],
        "gp_portals": [
            {
                "name": "GP-Portal-Main",
                "address": "portal.company.com",
                "authentication_profile": "auth-profile-id",
                "client_configs": {
                    "windows": "config-id",
                    "mac": "config-id",
                    "linux": "config-id"
                }
            }
        ]
    },
    "regions": [
        {
            "name": "us-east-1",
            "enabled": true,
            "gateway": "GP-Gateway-US-East",
            "backup_gateway": "GP-Gateway-US-West"
        }
    ],
    "ip_pools": [
        {
            "name": "Mobile-Users-Pool",
            "region": "us-east-1",
            "subnets": ["10.100.0.0/16", "10.101.0.0/16"]
        }
    ]
}
```

#### Priority 5: HIP Objects and Profiles ❌
**Endpoints:** (Need to identify from Prisma Access API docs)
- Likely: `/sse/config/v1/hip-objects`
- Likely: `/sse/config/v1/hip-profiles`

**What to Capture:**
- **HIP Objects** - Host Information Profile match criteria
  - Operating system checks
  - Disk encryption requirements
  - Firewall status checks
  - Antivirus status checks
  - Patch management checks
  - Custom criteria

- **HIP Profiles** - Collections of HIP objects for enforcement
  - Profile names
  - Match conditions (AND/OR logic)
  - Associated HIP objects
  - Action on match/no-match

**Configuration Schema:**
```python
"hip": {
    "hip_objects": [
        {
            "id": "hip-obj-1",
            "name": "Windows-10-Encrypted",
            "folder": "Mobile Users",
            "criteria": {
                "os": {
                    "contains": "Microsoft Windows 10"
                },
                "disk_encryption": {
                    "is_installed": true,
                    "encrypted_locations": [
                        {"name": "C:", "encryption_state": "encrypted"}
                    ]
                }
            }
        }
    ],
    "hip_profiles": [
        {
            "id": "hip-profile-1",
            "name": "Corporate-Compliance",
            "folder": "Mobile Users",
            "match": "all",  # or "any"
            "hip_objects": [
                "Windows-10-Encrypted",
                "Antivirus-Current",
                "Firewall-Enabled"
            ]
        }
    ]
}
```

#### Priority 6: Regions and Subnets Configuration ❌

**Endpoints:** (May be part of infrastructure settings)
- Possibly: `/sse/config/v1/regions`
- Embedded in mobile-agent settings

**What to Capture:**
- **Enabled Regions** - List of active Prisma Access regions
- **Region-Specific Settings**
  - Compute locations
  - IP address pools
  - Service IP addresses
  - Egress IP addresses

- **Subnet Assignments** - Per-service subnet allocations
  - Mobile Users subnet per region
  - Remote Networks subnet per region
  - Service Connection subnet per region

**Configuration Schema:**
```python
"regions": {
    "enabled_regions": [
        {
            "name": "us-east-1",
            "location": "US East (N. Virginia)",
            "enabled_services": ["mobile_users", "remote_networks", "service_connections"],
            "ip_pools": {
                "mobile_users": "10.100.0.0/16",
                "remote_networks": "10.200.0.0/16",
                "service_connections": "10.50.0.0/16"
            },
            "service_ips": {
                "portal": ["1.2.3.4"],
                "gateway": ["1.2.3.5", "1.2.3.6"]
            },
            "egress_ips": ["1.2.3.10", "1.2.3.11"]
        }
    ]
}
```

### 2.3 Infrastructure Capture Priority Matrix

| Component | Priority | Complexity | API Support | User Value |
|-----------|----------|------------|-------------|------------|
| Remote Networks | **P1** | High | ✅ Yes | Very High |
| IPsec Tunnels | **P1** | High | ✅ Yes | Very High |
| Service Connections | **P2** | Medium | ✅ Yes | High |
| Mobile User Infrastructure | **P2** | High | ⚠️ Partial | High |
| HIP Objects/Profiles | **P3** | Medium | ❓ Unknown | Medium |
| Regions & Subnets | **P3** | Low | ⚠️ Partial | Medium |

---

## 3. API Rate Limiting Strategy

### 3.1 Current Rate Limiting Implementation

**Location:** `prisma/api_utils.py` (Lines 19-108)

**Current Features:**
- Thread-safe `RateLimiter` class
- Default: 100 requests per 60 seconds
- Per-endpoint limits supported
- Automatic waiting with logging

**Current Client Config:**
```python
# From api_client.py (Line 62-82)
def __init__(
    self,
    tsg_id: str,
    api_user: str,
    api_secret: str,
    rate_limit: int = 100,  # ← Current default
    cache_ttl: int = 300,
):
    self.rate_limiter = RateLimiter(max_requests=rate_limit, time_window=60)
```

### 3.2 Enhanced Rate Limiting for Infrastructure Pull

**Requirement:** Cap at 50 requests/minute to avoid triggering API delays

**Implementation Strategy:**

#### Option 1: Global Limit Reduction (Simple)
```python
# Change default in api_client.py __init__
rate_limit: int = 50,  # ← Reduced from 100

# User requirement: 50 req/min globally
```

**Pros:**
- Simple, one-line change
- Ensures compliance across all API calls
- No risk of exceeding limits

**Cons:**
- May slow down operations unnecessarily
- Doesn't optimize for burst scenarios

#### Option 2: Endpoint-Specific Limits (Optimal)
```python
# In pull_orchestrator.py or api_client.py initialization
rate_limiter.set_endpoint_limit("/remote-networks", 10, 60)
rate_limiter.set_endpoint_limit("/ipsec-tunnels", 10, 60)
rate_limiter.set_endpoint_limit("/service-connections", 10, 60)
rate_limiter.set_endpoint_limit("/security-rules", 20, 60)
# Total: ~50 requests/minute across endpoints
```

**Pros:**
- Optimizes throughput for different endpoint types
- Can prioritize critical endpoints
- More sophisticated rate management

**Cons:**
- Requires configuration and tuning
- More complex to test

#### Option 3: Adaptive Rate Limiting with Buffer (Recommended)
```python
# Configuration
GLOBAL_RATE_LIMIT = 50  # Max 50 req/min
SAFETY_BUFFER = 0.9     # Use only 90% of limit (45 req/min)

# In api_client.py
def __init__(self, ..., rate_limit: int = 45, ...):  # ← 90% of 50
    self.rate_limiter = RateLimiter(max_requests=rate_limit, time_window=60)
    
# Also add endpoint-specific sub-limits
self.rate_limiter.set_endpoint_limit("/security-rules", 15, 60)
self.rate_limiter.set_endpoint_limit("/addresses", 10, 60)
self.rate_limiter.set_endpoint_limit("/remote-networks", 10, 60)
```

**Pros:**
- Safety buffer prevents accidental limit hits
- Endpoint-specific optimization
- Balances safety with performance

**Cons:**
- Slightly slower than absolute max
- **Recommended approach** ✅

### 3.3 Rate Limiting During Infrastructure Pull

**Pull Operation Flow:**
1. **Folders** (1-5 requests depending on folder count)
2. **Security Rules** per folder (5-50 requests)
3. **Objects** per folder (10-100 requests)
4. **Profiles** per folder (5-30 requests)
5. **Infrastructure** (NEW - 20-50 requests)
   - Remote Networks: 1-10 requests
   - IPsec Tunnels: 1-5 requests
   - IKE Gateways: 1-5 requests
   - Service Connections: 1-10 requests
   - Mobile User Settings: 1-10 requests

**Total Estimated Requests:**
- **Small Config:** ~50-100 requests (2-3 minutes at 50 req/min)
- **Medium Config:** ~200-500 requests (5-10 minutes at 50 req/min)
- **Large Config:** ~1000+ requests (20+ minutes at 50 req/min)

**Rate Limiting Enhancements:**

```python
# In pull_orchestrator.py - Add rate limit tracking
class PullOrchestrator:
    def __init__(self, api_client, detect_defaults=True):
        # ... existing code ...
        self.api_call_count = 0
        self.start_time = None
        
    def _track_api_call(self):
        """Track API calls for rate limiting stats."""
        self.api_call_count += 1
        if self.api_call_count % 10 == 0:
            elapsed = time.time() - self.start_time
            rate = (self.api_call_count / elapsed) * 60  # calls per minute
            self._report_progress(
                f"API calls: {self.api_call_count} ({rate:.1f} req/min)", 
                self.api_call_count, 
                0
            )
```

### 3.4 Rate Limiting Configuration in GUI

**Add to Settings Dialog** (`gui/settings_dialog.py`):

```python
# Update rate_limit_spin range
self.rate_limit_spin.setRange(10, 100)  # Allow 10-100
self.rate_limit_spin.setValue(50)       # Default to 50
self.rate_limit_spin.setSuffix(" requests/minute")

# Add warning label
rate_warning = QLabel("⚠️ Prisma Access API limit: 100 req/min\nRecommended: 50 req/min to avoid delays")
rate_warning.setStyleSheet("color: orange; font-size: 10px;")
rate_layout.addRow("", rate_warning)
```

**Add to Pull Widget Progress Display:**
```python
# Show real-time rate
self.rate_label = QLabel("API rate: 0 req/min")
progress_layout.addWidget(self.rate_label)

# Update during pull
def update_rate_display(calls, elapsed):
    rate = (calls / elapsed) * 60
    self.rate_label.setText(f"API rate: {rate:.1f} req/min")
    if rate > 50:
        self.rate_label.setStyleSheet("color: orange;")
    else:
        self.rate_label.setStyleSheet("color: green;")
```

---

## 4. GUI Enhancements

### 4.1 Current GUI State (`gui/pull_widget.py`)

**Existing Options:**
- ✅ Security Policy Folders
- ✅ Configuration Snippets
- ✅ Security Rules
- ✅ Security Objects
- ✅ Security Profiles
- ✅ Filter Default Configurations (advanced)

**Missing:**
- ❌ Custom Applications selection
- ❌ Infrastructure components (remote networks, tunnels, mobile users)

### 4.2 Proposed GUI Enhancements

#### Enhancement 1: Add Custom Applications Section

**Location:** `gui/pull_widget.py` - Add to options_group

```python
# After self.profiles_check
self.applications_check = QCheckBox("Custom Applications")
self.applications_check.setChecked(False)
self.applications_check.setToolTip(
    "Select custom applications to capture (rarely needed - most apps are predefined)"
)
self.applications_check.stateChanged.connect(self._on_applications_toggle)
options_layout.addWidget(self.applications_check)

# Add button to search for applications (initially disabled)
self.applications_btn = QPushButton("Select Applications...")
self.applications_btn.setEnabled(False)
self.applications_btn.clicked.connect(self._select_applications)
options_layout.addWidget(self.applications_btn)

# Add label showing selected count
self.applications_label = QLabel("No applications selected")
self.applications_label.setStyleSheet("color: gray; font-size: 10px; margin-left: 20px;")
options_layout.addWidget(self.applications_label)

# Store selected apps
self.selected_applications = []

def _on_applications_toggle(self, state):
    """Enable/disable applications button."""
    self.applications_btn.setEnabled(state == Qt.CheckState.Checked)
    if state != Qt.CheckState.Checked:
        self.selected_applications = []
        self.applications_label.setText("No applications selected")

def _select_applications(self):
    """Open application selection dialog."""
    from gui.dialogs.application_selector import ApplicationSelectorDialog
    
    dialog = ApplicationSelectorDialog(self.api_client, self)
    if dialog.exec():
        self.selected_applications = dialog.get_selected_applications()
        count = len(self.selected_applications)
        self.applications_label.setText(
            f"{count} application{'s' if count != 1 else ''} selected"
        )
        self.applications_label.setStyleSheet("color: green; font-size: 10px;")
```

**New Dialog:** `gui/dialogs/application_selector.py`
```python
"""Application selector dialog for custom applications."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QListWidget, QLabel, QDialogButtonBox
)
from PyQt6.QtCore import Qt

class ApplicationSelectorDialog(QDialog):
    """Dialog for searching and selecting custom applications."""
    
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.selected_apps = []
        self._init_ui()
        
    def _init_ui(self):
        self.setWindowTitle("Select Custom Applications")
        self.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # Instructions
        info = QLabel(
            "Search for custom applications by name (minimum 3 characters).\n"
            "Note: Most applications are predefined. Only select user-created applications."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # Search box
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search applications...")
        self.search_input.textChanged.connect(self._on_search)
        search_layout.addWidget(self.search_input)
        
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self._perform_search)
        search_layout.addWidget(self.search_btn)
        layout.addLayout(search_layout)
        
        # Results list
        self.results_list = QListWidget()
        self.results_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        layout.addWidget(self.results_list)
        
        # Selected apps list
        selected_label = QLabel("Selected Applications:")
        layout.addWidget(selected_label)
        
        self.selected_list = QListWidget()
        self.selected_list.setMaximumHeight(100)
        layout.addWidget(self.selected_list)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add Selected →")
        self.add_btn.clicked.connect(self._add_selected)
        btn_layout.addWidget(self.add_btn)
        
        self.remove_btn = QPushButton("← Remove")
        self.remove_btn.clicked.connect(self._remove_selected)
        btn_layout.addWidget(self.remove_btn)
        layout.addLayout(btn_layout)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def _perform_search(self):
        """Search for applications."""
        search_term = self.search_input.text().strip()
        if len(search_term) < 3:
            return
            
        # Use application_search module
        from cli.application_search import search_applications
        
        matches = search_applications(self.api_client, search_term)
        
        self.results_list.clear()
        for app in matches:
            self.results_list.addItem(app.get("name", "Unknown"))
    
    def _add_selected(self):
        """Add selected items to final selection."""
        for item in self.results_list.selectedItems():
            app_name = item.text()
            if app_name not in self.selected_apps:
                self.selected_apps.append(app_name)
                self.selected_list.addItem(app_name)
    
    def _remove_selected(self):
        """Remove selected items."""
        for item in self.selected_list.selectedItems():
            self.selected_apps.remove(item.text())
            self.selected_list.takeItem(self.selected_list.row(item))
    
    def get_selected_applications(self):
        """Get list of selected application names."""
        return self.selected_apps
```

#### Enhancement 2: Add Infrastructure Components Section

**Location:** `gui/pull_widget.py` - Add new group after options_group

```python
# Infrastructure options group (NEW)
infra_group = QGroupBox("Infrastructure Components")
infra_layout = QVBoxLayout()

self.remote_networks_check = QCheckBox("Remote Networks")
self.remote_networks_check.setChecked(True)
self.remote_networks_check.setToolTip(
    "Pull remote network configurations (branches, data centers)"
)
infra_layout.addWidget(self.remote_networks_check)

self.service_connections_check = QCheckBox("Service Connections")
self.service_connections_check.setChecked(True)
self.service_connections_check.setToolTip(
    "Pull service connection configurations (on-prem connectivity)"
)
infra_layout.addWidget(self.service_connections_check)

self.ipsec_tunnels_check = QCheckBox("IPsec Tunnels & Crypto")
self.ipsec_tunnels_check.setChecked(True)
self.ipsec_tunnels_check.setToolTip(
    "Pull IPsec tunnel configs, IKE gateways, and crypto profiles"
)
infra_layout.addWidget(self.ipsec_tunnels_check)

self.mobile_users_check = QCheckBox("Mobile User Infrastructure")
self.mobile_users_check.setChecked(True)
self.mobile_users_check.setToolTip(
    "Pull GlobalProtect gateway/portal configs and mobile user settings"
)
infra_layout.addWidget(self.mobile_users_check)

self.hip_check = QCheckBox("HIP Objects & Profiles")
self.hip_check.setChecked(True)
self.hip_check.setToolTip(
    "Pull Host Information Profile (HIP) objects and profiles"
)
infra_layout.addWidget(self.hip_check)

self.regions_check = QCheckBox("Regions & Subnets")
self.regions_check.setChecked(True)
self.regions_check.setToolTip(
    "Pull enabled regions and subnet allocations"
)
infra_layout.addWidget(self.regions_check)

infra_group.setLayout(infra_layout)
scroll_layout.addWidget(infra_group)
```

#### Enhancement 3: Update _start_pull() Method

```python
def _start_pull(self):
    """Start the pull operation."""
    if not self.api_client:
        QMessageBox.warning(self, "Error", "Not connected to Prisma Access")
        return
    
    # Gather options
    options = {
        # Existing options
        "include_snippets": self.snippets_check.isChecked(),
        "include_objects": self.objects_check.isChecked(),
        "include_profiles": self.profiles_check.isChecked(),
        "detect_defaults": self.filter_defaults_check.isChecked(),
        
        # NEW: Custom applications
        "application_names": self.selected_applications if self.applications_check.isChecked() else None,
        
        # NEW: Infrastructure options
        "include_remote_networks": self.remote_networks_check.isChecked(),
        "include_service_connections": self.service_connections_check.isChecked(),
        "include_ipsec_tunnels": self.ipsec_tunnels_check.isChecked(),
        "include_mobile_users": self.mobile_users_check.isChecked(),
        "include_hip": self.hip_check.isChecked(),
        "include_regions": self.regions_check.isChecked(),
    }
    
    # Start worker thread with updated options
    self.worker = PullWorker(self.api_client, options)
    # ... rest of existing code ...
```

### 4.3 GUI Update Summary

**Files to Modify:**
1. ✅ `gui/pull_widget.py` - Add checkboxes and application selector
2. ✅ `gui/dialogs/application_selector.py` - NEW dialog for app selection
3. ✅ `gui/workers.py` - Update PullWorker to handle new options
4. ✅ `gui/settings_dialog.py` - Update rate limit default and warnings

**Visual Mockup:**

```
┌──────────────────────────────────────────────────────┐
│ Pull Configuration                                    │
├──────────────────────────────────────────────────────┤
│ Select which components to retrieve                   │
│                                                       │
│ ┌─ Configuration Components ──────────────────────┐  │
│ │ ☑ Security Policy Folders                       │  │
│ │ ☑ Configuration Snippets                        │  │
│ │ ☑ Security Rules                                │  │
│ │ ☑ Security Objects                              │  │
│ │ ☑ Security Profiles                             │  │
│ │ ☐ Custom Applications  [Select Applications...] │  │
│ │   No applications selected                       │  │
│ └─────────────────────────────────────────────────┘  │
│                                                       │
│ ┌─ Infrastructure Components ─────────────────────┐  │
│ │ ☑ Remote Networks                               │  │
│ │ ☑ Service Connections                           │  │
│ │ ☑ IPsec Tunnels & Crypto                        │  │
│ │ ☑ Mobile User Infrastructure                    │  │
│ │ ☑ HIP Objects & Profiles                        │  │
│ │ ☑ Regions & Subnets                             │  │
│ └─────────────────────────────────────────────────┘  │
│                                                       │
│ ┌─ Advanced Options ──────────────────────────────┐  │
│ │ ☐ Filter Default Configurations                 │  │
│ └─────────────────────────────────────────────────┘  │
│                                                       │
│        [Select All] [Select None]   [Pull Config]    │
│                                                       │
│ ┌─ Progress ──────────────────────────────────────┐  │
│ │ Connected to tsg-123456 - Ready to pull         │  │
│ │ API rate: 0 req/min                             │  │
│ │ [████████░░░░░░░░░░░░░░░░░░░░] 35%              │  │
│ └─────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

---

## 5. Implementation Plan

### Phase 1: Foundation & API Endpoints (Week 1)

**Tasks:**
1. ✅ Update `prisma/api_endpoints.py` to confirm all infrastructure endpoints
2. ✅ Add new API methods to `prisma/api_client.py`:
   - `get_all_remote_networks()`
   - `get_remote_network(network_id)`
   - `get_all_ipsec_tunnels()`
   - `get_all_ike_gateways()`
   - `get_all_ike_crypto_profiles()`
   - `get_all_ipsec_crypto_profiles()`
   - `get_mobile_user_infrastructure()`
   - `get_hip_objects()`
   - `get_hip_profiles()`
   - `get_enabled_regions()`

3. ✅ Update rate limiter default to 50 req/min with safety buffer (45 req/min)
4. ✅ Add rate limit tracking to pull_orchestrator

**Deliverables:**
- Updated `api_client.py` with new methods
- Updated `api_endpoints.py` with confirmed endpoints
- Rate limiting configured for 50 req/min

### Phase 2: Infrastructure Capture Modules (Week 2)

**Tasks:**
1. ✅ Create `prisma/pull/infrastructure_capture.py` module
   - `capture_remote_networks()`
   - `capture_service_connections()`
   - `capture_ipsec_tunnels()`
   - `capture_ike_gateways()`
   - `capture_crypto_profiles()`
   - `capture_mobile_user_infrastructure()`
   - `capture_hip_objects_and_profiles()`
   - `capture_regions_and_subnets()`

2. ✅ Update `config_schema_v2.py` to include infrastructure sections
3. ✅ Update `pull_orchestrator.py` to integrate infrastructure capture

**Deliverables:**
- New `infrastructure_capture.py` module
- Updated schema with infrastructure sections
- Integrated infrastructure pull in orchestrator

### Phase 3: GUI Enhancements (Week 3)

**Tasks:**
1. ✅ Create `gui/dialogs/application_selector.py` dialog
2. ✅ Update `gui/pull_widget.py`:
   - Add custom applications section
   - Add infrastructure components section
   - Update _start_pull() method
3. ✅ Update `gui/workers.py` to handle new options
4. ✅ Update `gui/settings_dialog.py` for rate limit settings
5. ✅ Test GUI with all new options

**Deliverables:**
- Application selector dialog
- Enhanced pull widget with all options
- Updated worker thread
- Functional GUI for infrastructure pull

### Phase 4: Testing Framework (Week 4)

**Tasks:**
1. ✅ Create `tests/test_infrastructure_capture.py`
   - Test each infrastructure capture function
   - Test rate limiting during infrastructure pull
   - Test API error handling

2. ✅ Update existing tests to include infrastructure:
   - `tests/test_pull_e2e.py` - Add infrastructure pull tests
   - `tests/test_api_client.py` - Add new API method tests

3. ✅ Create integration test for full workflow:
   - Pull with infrastructure components
   - Verify rate limiting stays under 50 req/min
   - Verify data integrity

4. ✅ Test custom applications feature in both CLI and GUI

**Deliverables:**
- `test_infrastructure_capture.py` with comprehensive tests
- Updated integration tests
- Full end-to-end test with infrastructure components
- Custom applications test coverage

### Phase 5: Documentation & Polish (Week 5)

**Tasks:**
1. ✅ Update `docs/PULL_PUSH_GUIDE.md` with infrastructure components
2. ✅ Update `docs/API_REFERENCE.md` with new API methods
3. ✅ Update `docs/JSON_SCHEMA.md` with infrastructure schema
4. ✅ Update `docs/GUI_USER_GUIDE.md` with new GUI options
5. ✅ Create `docs/INFRASTRUCTURE_GUIDE.md` specifically for infrastructure components
6. ✅ Update `README.md` with infrastructure capture feature

**Deliverables:**
- Complete documentation for infrastructure capture
- Updated user guides
- Infrastructure-specific guide

---

## 6. Comprehensive Test Plan

### 6.1 Unit Tests

#### Test Suite: Infrastructure Capture
**File:** `tests/test_infrastructure_capture.py`

```python
class TestRemoteNetworkCapture:
    def test_capture_remote_networks(self, mock_api_client):
        """Test remote network capture."""
        
    def test_capture_remote_network_with_bgp(self, mock_api_client):
        """Test remote network with BGP config."""
        
    def test_capture_remote_network_no_results(self, mock_api_client):
        """Test handling of no remote networks."""

class TestIPsecTunnelCapture:
    def test_capture_ipsec_tunnels(self, mock_api_client):
        """Test IPsec tunnel capture."""
        
    def test_capture_ike_gateways(self, mock_api_client):
        """Test IKE gateway capture."""
        
    def test_capture_crypto_profiles(self, mock_api_client):
        """Test crypto profile capture."""

class TestMobileUserCapture:
    def test_capture_mobile_user_infrastructure(self, mock_api_client):
        """Test mobile user infrastructure capture."""
        
    def test_capture_gp_gateways(self, mock_api_client):
        """Test GlobalProtect gateway capture."""
        
    def test_capture_gp_portals(self, mock_api_client):
        """Test GlobalProtect portal capture."""

class TestHIPCapture:
    def test_capture_hip_objects(self, mock_api_client):
        """Test HIP object capture."""
        
    def test_capture_hip_profiles(self, mock_api_client):
        """Test HIP profile capture."""
        
    def test_hip_profile_with_objects(self, mock_api_client):
        """Test HIP profile references to objects."""

class TestRegionCapture:
    def test_capture_regions(self, mock_api_client):
        """Test region capture."""
        
    def test_capture_subnets(self, mock_api_client):
        """Test subnet allocation capture."""
```

#### Test Suite: Rate Limiting
**File:** `tests/test_rate_limiting.py`

```python
class TestRateLimitingInfrastructure:
    def test_rate_limit_during_infrastructure_pull(self, mock_api_client):
        """Verify rate limiting during infrastructure pull."""
        # Pull all infrastructure components
        # Verify rate stays under 50 req/min
        
    def test_rate_limit_tracking(self, mock_api_client):
        """Test rate limit tracking and reporting."""
        
    def test_rate_limit_per_endpoint(self, mock_api_client):
        """Test per-endpoint rate limiting."""
        
    def test_rate_limit_with_safety_buffer(self, mock_api_client):
        """Verify 90% safety buffer (45 req/min max)."""
```

#### Test Suite: Custom Applications
**File:** `tests/test_custom_applications.py`

```python
class TestCustomApplications:
    def test_application_search(self, mock_api_client):
        """Test application search functionality."""
        
    def test_application_selection(self, mock_api_client):
        """Test application selection."""
        
    def test_pull_with_custom_applications(self, mock_api_client):
        """Test pull with custom applications specified."""
        
    def test_no_custom_applications(self, mock_api_client):
        """Test pull without custom applications (default)."""
```

### 6.2 Integration Tests

#### Test Suite: End-to-End Infrastructure Pull
**File:** `tests/test_e2e_infrastructure.py`

```python
class TestE2EInfrastructurePull:
    def test_full_infrastructure_pull(self, live_api_client):
        """Test complete infrastructure pull."""
        # Pull all infrastructure components
        # Verify all components captured
        # Verify schema compliance
        # Verify rate limiting
        
    def test_selective_infrastructure_pull(self, live_api_client):
        """Test selective infrastructure component pull."""
        # Pull only remote networks and tunnels
        # Verify correct components captured
        
    def test_infrastructure_with_security_policies(self, live_api_client):
        """Test combined pull of security policies and infrastructure."""
        # Full pull with both security and infrastructure
        # Verify integration
```

### 6.3 GUI Tests

#### Test Suite: GUI Infrastructure Options
**File:** `tests/test_gui_infrastructure.py`

```python
class TestGUIInfrastructureOptions:
    def test_infrastructure_checkboxes_present(self, qtbot):
        """Verify infrastructure checkboxes are present."""
        
    def test_infrastructure_selection(self, qtbot):
        """Test selecting infrastructure components."""
        
    def test_application_selector_dialog(self, qtbot):
        """Test custom application selector dialog."""
        
    def test_pull_with_infrastructure(self, qtbot, mock_api_client):
        """Test GUI pull with infrastructure options."""
```

### 6.4 Performance Tests

#### Test Suite: Performance and Rate Limiting
**File:** `tests/test_performance_infrastructure.py`

```python
class TestPerformance:
    def test_large_config_pull_performance(self, mock_api_client):
        """Test pull performance with large configuration."""
        # Mock large config (100+ remote networks, 200+ tunnels)
        # Verify completion time
        # Verify rate limiting compliance
        
    def test_rate_limit_compliance_large_pull(self, mock_api_client):
        """Verify rate limiting during large pull operations."""
        # Track API calls over time
        # Verify never exceeds 50 req/min
```

### 6.5 Test Coverage Goals

| Component | Unit Tests | Integration Tests | GUI Tests | Target Coverage |
|-----------|------------|-------------------|-----------|-----------------|
| Remote Networks | 10+ | 3+ | 2+ | 85% |
| IPsec Tunnels | 8+ | 3+ | 2+ | 85% |
| Service Connections | 6+ | 2+ | 2+ | 80% |
| Mobile Users | 8+ | 2+ | 2+ | 80% |
| HIP Objects/Profiles | 6+ | 2+ | 2+ | 80% |
| Regions/Subnets | 4+ | 2+ | 2+ | 75% |
| Custom Applications | 6+ | 2+ | 3+ | 90% |
| Rate Limiting | 8+ | 4+ | 1+ | 95% |
| **Total** | **56+** | **20+** | **16+** | **85%** |

### 6.6 Test Execution Plan

**Phase 1: Unit Tests**
```bash
# Test individual capture modules
pytest tests/test_infrastructure_capture.py -v
pytest tests/test_custom_applications.py -v
pytest tests/test_rate_limiting.py -v
```

**Phase 2: Integration Tests**
```bash
# Test end-to-end workflows
pytest tests/test_e2e_infrastructure.py -v
pytest tests/test_pull_e2e.py -v --infrastructure
```

**Phase 3: GUI Tests**
```bash
# Test GUI components
pytest tests/test_gui_infrastructure.py -v
pytest tests/test_gui_application_selector.py -v
```

**Phase 4: Performance Tests**
```bash
# Test performance and rate limiting
pytest tests/test_performance_infrastructure.py -v --slow
```

**Phase 5: Full Regression**
```bash
# Run all tests
pytest tests/ -v --cov=prisma --cov=gui --cov=config
```

---

## 7. Risk Assessment & Mitigation

### 7.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| API endpoint changes | Medium | High | Version API calls, add error handling |
| Rate limit violations | Low | Medium | Implement 90% safety buffer (45 req/min) |
| Large config timeouts | Medium | Medium | Implement pagination, progress tracking |
| GUI performance issues | Low | Low | Use worker threads, async operations |
| Schema compatibility | Low | High | Maintain backward compatibility layer |
| Missing API documentation | Medium | Medium | Test against live API, handle unknowns gracefully |

### 7.2 Mitigation Strategies

#### Strategy 1: API Endpoint Validation
```python
# Add to api_client.py
def validate_endpoint_availability(self, endpoint: str) -> bool:
    """Check if endpoint is available before using."""
    try:
        response = self.make_request("GET", endpoint, params={"limit": 1})
        return True
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            logging.warning(f"Endpoint not available: {endpoint}")
            return False
        raise
```

#### Strategy 2: Graceful Degradation
```python
# In infrastructure_capture.py
def capture_remote_networks(self):
    """Capture remote networks with graceful error handling."""
    try:
        networks = self.api_client.get_all_remote_networks()
        return networks
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            logging.warning("Remote Networks endpoint not available, skipping...")
            return []
        raise
```

#### Strategy 3: Rate Limit Buffer
```python
# Use 90% of max rate (45 req/min instead of 50 req/min)
RATE_LIMIT_MAX = 50
RATE_LIMIT_BUFFER = 0.9
EFFECTIVE_RATE = int(RATE_LIMIT_MAX * RATE_LIMIT_BUFFER)  # 45

api_client = PrismaAccessAPIClient(
    tsg_id=tsg_id,
    api_user=api_user,
    api_secret=api_secret,
    rate_limit=EFFECTIVE_RATE  # 45 req/min
)
```

---

## 8. Success Criteria

### 8.1 Feature Completion

- ✅ Custom applications feature documented and accessible in CLI
- [ ] Custom applications feature added to GUI
- [ ] Remote Networks capture implemented and tested
- [ ] IPsec Tunnels capture implemented and tested
- [ ] Service Connections capture enhanced and tested
- [ ] Mobile User Infrastructure capture implemented and tested
- [ ] HIP Objects/Profiles capture implemented and tested
- [ ] Regions/Subnets capture implemented and tested
- [ ] Rate limiting configured for 50 req/min (45 req/min with buffer)
- [ ] GUI enhancements completed and tested
- [ ] Comprehensive test suite passing (85%+ coverage)

### 8.2 Quality Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Test Coverage | 85% | ~70% | 🟡 |
| Unit Tests | 56+ | TBD | ⚪ |
| Integration Tests | 20+ | TBD | ⚪ |
| GUI Tests | 16+ | TBD | ⚪ |
| Rate Limit Compliance | 100% | N/A | ⚪ |
| API Error Handling | 100% | ~90% | 🟢 |
| Documentation Complete | 100% | ~95% | 🟢 |

### 8.3 User Acceptance Criteria

1. **Custom Applications:**
   - ✅ CLI: User can search and select custom applications
   - [ ] GUI: User can open dialog, search, and select custom applications
   - [ ] Selected applications are included in pulled configuration

2. **Infrastructure Components:**
   - [ ] User can select which infrastructure components to pull
   - [ ] Remote networks are captured with complete configuration
   - [ ] IPsec tunnels and crypto profiles are captured
   - [ ] Service connections are captured with BGP settings
   - [ ] Mobile user infrastructure is captured
   - [ ] HIP objects and profiles are captured
   - [ ] Regions and subnets are captured

3. **Rate Limiting:**
   - [ ] Pull operations never exceed 50 req/min
   - [ ] Rate limiting is transparent to user (no manual intervention)
   - [ ] Progress display shows current API rate
   - [ ] GUI settings allow rate limit configuration

4. **User Experience:**
   - [ ] GUI is intuitive and clearly organized
   - [ ] Progress tracking works for all components
   - [ ] Error messages are helpful and actionable
   - [ ] Documentation is clear and complete

---

## 9. Timeline

### Week 1: Foundation (Dec 22-28)
- **Days 1-2:** Update API client with infrastructure methods
- **Days 3-4:** Update endpoints and rate limiting
- **Days 5-7:** Test API methods against live tenant

### Week 2: Infrastructure Capture (Dec 29 - Jan 4)
- **Days 1-3:** Implement infrastructure_capture.py module
- **Days 4-5:** Update schema and orchestrator
- **Days 6-7:** Unit testing infrastructure capture

### Week 3: GUI Enhancements (Jan 5-11)
- **Days 1-2:** Create application selector dialog
- **Days 3-4:** Update pull widget with new options
- **Days 5-6:** Update workers and settings
- **Day 7:** Integration testing GUI

### Week 4: Testing (Jan 12-18)
- **Days 1-3:** Create comprehensive test suite
- **Days 4-5:** Integration and E2E testing
- **Days 6-7:** Performance and rate limit testing

### Week 5: Documentation (Jan 19-25)
- **Days 1-3:** Update all documentation
- **Days 4-5:** Create infrastructure guide
- **Days 6-7:** Final review and polish

**Total: 5 weeks (35 days)**

---

## 10. Next Steps

### Immediate Actions (Next 48 Hours)

1. **Review and Approve Plan**
   - [ ] Review this comprehensive plan
   - [ ] Approve scope and timeline
   - [ ] Identify any missing requirements

2. **Begin Week 1 Implementation**
   - [ ] Update `api_endpoints.py` with infrastructure endpoints
   - [ ] Begin implementing API methods in `api_client.py`
   - [ ] Test against live Prisma Access tenant to confirm endpoints

3. **Set Up Testing Environment**
   - [ ] Prepare test tenant with infrastructure configured
   - [ ] Document test data setup
   - [ ] Create mock data for unit tests

### Development Workflow

1. **Feature Branch:** All work in `feature/comprehensive-config-capture`
2. **Commits:** Frequent, atomic commits with clear messages
3. **Testing:** Test each component before moving to next
4. **Documentation:** Update docs as features are completed
5. **Code Review:** Self-review before considering complete

---

## Appendix A: API Endpoint Reference

### Infrastructure Endpoints

```python
# Remote Networks
GET /sse/config/v1/remote-networks
GET /sse/config/v1/remote-networks/{id}
POST /sse/config/v1/remote-networks
PUT /sse/config/v1/remote-networks/{id}
DELETE /sse/config/v1/remote-networks/{id}

# Service Connections
GET /sse/config/v1/service-connections
GET /sse/config/v1/service-connections/{id}
POST /sse/config/v1/service-connections
PUT /sse/config/v1/service-connections/{id}
DELETE /sse/config/v1/service-connections/{id}

# IPsec Tunnels
GET /sse/config/v1/ipsec-tunnels
GET /sse/config/v1/ipsec-tunnels/{id}

# IKE Gateways
GET /sse/config/v1/ike-gateways
GET /sse/config/v1/ike-gateways/{id}

# IKE Crypto Profiles
GET /sse/config/v1/ike-crypto-profiles
GET /sse/config/v1/ike-crypto-profiles/{id}

# IPsec Crypto Profiles
GET /sse/config/v1/ipsec-crypto-profiles
GET /sse/config/v1/ipsec-crypto-profiles/{id}

# Mobile Agent Infrastructure
GET /sse/config/v1/mobile-agent/infrastructure-settings

# HIP Objects (endpoints TBD - need to verify)
GET /sse/config/v1/hip-objects
GET /sse/config/v1/hip-profiles

# Regions (may be part of infrastructure-settings)
GET /sse/config/v1/regions
```

---

## Appendix B: Configuration Schema Extensions

### Complete Infrastructure Schema

```python
"infrastructure": {
    "shared_infrastructure_settings": {
        # Existing settings
    },
    "mobile_agent": {
        # Existing mobile agent config
    },
    "service_connections": [
        # Service connection objects
    ],
    "remote_networks": [
        # Remote network objects (NEW)
    ]
},
"network": {
    "ike_crypto_profiles": [],     # NEW details
    "ipsec_crypto_profiles": [],   # NEW details
    "ike_gateways": [],            # NEW details
    "ipsec_tunnels": [],           # NEW details
    "service_connections": [],     # Duplicate from infrastructure for network context
    "remote_networks": []          # Duplicate from infrastructure for network context
},
"mobile_users": {                  # NEW section
    "infrastructure_settings": {},
    "gp_gateways": [],
    "gp_portals": [],
    "regions": [],
    "ip_pools": []
},
"hip": {                           # NEW section
    "hip_objects": [],
    "hip_profiles": []
},
"regions": {                       # NEW section
    "enabled_regions": [],
    "subnet_allocations": {}
}
```

---

## Document Change Log

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-12-21 | 1.0 | Initial comprehensive plan created | AI Assistant |

---

**End of Document**
