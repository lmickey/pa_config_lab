# Cloud Infrastructure Configuration Framework Plan

## Overview

This document outlines the architectural extension to the existing configuration framework to support cloud infrastructure deployments for POV environments. The goal is to create a unified configuration model that can drive both Terraform deployments and device-specific API configurations.

---

## 1. Configuration Hierarchy Extension

### Current Structure
```
Configuration
├── metadata
├── folders/          → SCM folder configurations
├── snippets/         → SCM snippet configurations
└── infrastructure/   → SCM infrastructure (RN, SC, etc.)
```

### Proposed Extended Structure
```
Configuration
├── metadata
├── folders/              → SCM folder configurations
├── snippets/             → SCM snippet configurations
├── infrastructure/       → SCM infrastructure (RN, SC, etc.)
├── cloud/                → NEW: Cloud Infrastructure
│   ├── deployment/       → Terraform deployment settings
│   ├── firewalls/        → Firewall VM configurations (branch/datacenter types)
│   ├── panorama/         → Panorama VM configuration
│   └── supporting_vms/   → Supporting infrastructure VMs
└── workflow_state/       → NEW: Pause/resume state for deployment workflow
```

---

## 2. Naming Conventions

**DECISION:** All resources follow a consistent naming convention.

### 2.1 Resource Group Naming
```
{Customer}-{DeploymentRegion}-{ManagementType}-rg
```

| Component | Description | Examples |
|-----------|-------------|----------|
| Customer | Customer/POV name | `acme`, `contoso` |
| DeploymentRegion | Azure region short name | `eastus`, `westus2`, `centralus` |
| ManagementType | SCM or Panorama managed | `scm`, `pan` |

**Examples:**
- `acme-eastus-scm-rg`
- `contoso-westus2-pan-rg`

### 2.2 System Naming
```
{ResourceGroupName}-{SystemType}
```

| System Type | Format | Examples |
|-------------|--------|----------|
| Firewall (single) | `fw` | `acme-eastus-scm-rg-fw` |
| Firewall (multiple) | `fw1`, `fw2`, etc. | `acme-eastus-scm-rg-fw1`, `acme-eastus-scm-rg-fw2` |
| Panorama | `panorama` | `acme-eastus-pan-rg-panorama` |
| ZTNA Connector | `ztna` | `acme-eastus-scm-rg-ztna` |
| Windows Client VM | `uservm-win` | `acme-eastus-scm-rg-uservm-win` |
| Linux Client VM | `uservm-linux` | `acme-eastus-scm-rg-uservm-linux` |
| Server VM | `server` or `server1` | `acme-eastus-scm-rg-server` |

### 2.3 Network Resource Naming
```
{ResourceGroupName}-{ResourceType}
```

| Resource | Format | Examples |
|----------|--------|----------|
| Virtual Network | `vnet` | `acme-eastus-scm-rg-vnet` |
| Management Subnet | `mgmt-subnet` | `acme-eastus-scm-rg-mgmt-subnet` |
| Untrust Subnet | `untrust-subnet` | `acme-eastus-scm-rg-untrust-subnet` |
| Trust Subnet (shared) | `trust-subnet` | `acme-eastus-scm-rg-trust-subnet` |
| Trust Subnet (branch) | `trust-branch1-subnet` | `acme-eastus-scm-rg-trust-branch1-subnet` |

---

## 3. Cloud Deployment Object (Terraform Settings)

The `cloud.deployment` section contains all settings needed for Terraform to deploy cloud resources.

### 3.1 Schema Definition

```yaml
cloud:
  deployment:
    # Naming Components
    customer_name: "acme"                # Used in resource group naming
    management_type: "scm"               # scm | pan

    # Cloud Provider Settings
    provider: "azure"                    # azure only (AWS/GCP future)
    subscription_id: "xxx-xxx-xxx"
    tenant_id: "xxx-xxx-xxx"
    location: "eastus"

    # Auto-generated from naming convention
    resource_group: null                 # Auto: {customer}-{location}-{mgmt_type}-rg

    # Network Settings
    virtual_network:
      address_space: ["10.100.0.0/16"]
      subnets:
        - name: "mgmt-subnet"
          prefix: "10.100.0.0/24"
          purpose: "management"
        - name: "untrust-subnet"
          prefix: "10.100.1.0/24"
          purpose: "untrust"
          shared: true                   # Shared across all FWs in same region
        - name: "trust-subnet"
          prefix: "10.100.2.0/24"
          purpose: "trust"
          for_firewall: "datacenter"     # Datacenter FW trust
        - name: "trust-branch1-subnet"
          prefix: "10.100.3.0/24"
          purpose: "trust"
          for_firewall: "branch1"        # Branch 1 dedicated trust

    # Common Tags
    tags:
      environment: "pov"
      customer: "acme"
      owner: "se-name"
      expiry: "2024-03-01"

    # State Management (Local, encrypted, stored with config)
    terraform_state:
      backend: "local"
      encrypt: true
      path: null                         # Auto-determined from config save location
```

### 3.2 Fields Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| customer_name | string | Yes | Customer name for resource naming |
| management_type | enum | Yes | `scm` or `pan` |
| provider | enum | Yes | Cloud provider (azure only for v1) |
| subscription_id | string | Yes (Azure) | Azure subscription ID |
| tenant_id | string | Yes (Azure) | Azure AD tenant ID |
| location | string | Yes | Deployment region |
| resource_group | string | Auto | Auto-generated from naming convention |
| virtual_network | object | Yes | VNet configuration with subnets |
| tags | dict | No | Resource tags for all objects |

---

## 4. Credential Management

### 4.1 Credential Strategy

**DECISION:** Users can choose between:
- **Generated secure credentials** (default) - Auto-generated before Terraform runs
- **Custom credentials** - User provides their own credentials in the relevant tabs

### 4.2 UI Flow for Credentials

```
Tab 1 (Tenant Info):
┌─────────────────────────────────────────────────────────┐
│ Firewall Credentials                                     │
│ ○ Use generated secure credentials (recommended)         │
│ ○ Use custom credentials                                 │
│   ├── Username: [________]                              │
│   └── Password: [________]                              │
└─────────────────────────────────────────────────────────┘

Tab 2 (Cloud Resources) - Supporting VMs:
┌─────────────────────────────────────────────────────────┐
│ VM Credentials                                           │
│ ○ Use generated secure credentials (recommended)         │
│ ○ Use custom credentials                                 │
│   ├── Username: [________]                              │
│   └── Password: [________]                              │
└─────────────────────────────────────────────────────────┘
```

### 4.3 Credential Generation Timing

```
User selects "generated" ──► Stored as "generate_on_deploy: true"
                                        │
                                        ▼
Tab 4 (Cloud Deployment) ──► Before Terraform runs:
                              1. Generate secure password
                              2. Store in tenant manager (encrypted)
                              3. Pass to Terraform variables
                              4. Display to user (copy option)
```

### 4.4 Expanded Tenant Manager Schema

```yaml
tenants:
  - name: "Customer POV"
    created_at: "2024-01-15T10:00:00Z"

    # SCM Credentials (existing)
    scm:
      tsg_id: "1234567890"
      client_id: "service-account@xxx.iam"
      client_secret: "encrypted:xxxxx"

    # Firewall Credentials (shared by all firewalls)
    firewall:
      use_generated: true                # Default: true
      auth_type: "password"              # password | api_key | certificate
      username: "admin"                  # Default or custom
      password: "encrypted:xxxxx"        # Generated or custom
      generated_at: null                 # Timestamp if generated
      # Alternative: API key
      api_key: null
      # Alternative: Certificate (for SSH)
      certificate:
        enabled: false
        cert_path: null
        key_path: null

    # Panorama Credentials (single Panorama)
    panorama:
      use_generated: true
      auth_type: "password"
      username: "admin"
      password: "encrypted:xxxxx"
      generated_at: null
      api_key: null
      certificate:
        enabled: false
        cert_path: null
        key_path: null

    # Supporting VM Credentials (auto-generated naming)
    supporting_vms:
      use_generated: true
      # Username: {resource_group}_admin (sanitized)
      username: "acme_eastus_scm_rg_admin"
      password: "encrypted:xxxxx"
      ssh_public_key: null               # Optional for Linux VMs
      generated_at: "2024-01-15T10:00:00Z"
```

---

## 5. Firewall Objects

### 5.1 Design Principle: Unified Objects with Deployment-Aware Methods

**DECISION:** Configuration objects contain all methods for CRUD operations and dependency resolution. The deployment target (SCM vs Firewall API vs Panorama API) is determined by the object's parent/association, and the object uses the appropriate connection method based on that context.

```
ConfigItem (base)
├── Methods: create(), update(), delete(), get_dependencies()
├── Property: deployment_target (determined by parent)
└── Serializers: to_scm_json(), to_firewall_xml(), to_panorama_xml()
```

### 5.2 Firewall Types and Network Architecture

**DECISION:**
- Each firewall type gets appropriate subnets
- Branch firewalls get **dedicated trust subnets**
- All firewalls in same region can **share untrust subnet**

| Type | Purpose | Trust Subnet | Untrust Subnet |
|------|---------|--------------|----------------|
| `datacenter` | Service Connection | Shared datacenter trust | Shared |
| `branch` | Remote Network | **Dedicated per branch** | Shared (same region) |

### 5.3 Firewall Schema

```yaml
cloud:
  firewalls:
    - name: null                         # Auto: {rg}-fw or {rg}-fw1
      type: "datacenter"                 # datacenter | branch
      role: "service_connection"         # Derived from type

      # VM Deployment Settings
      vm_settings:
        size: "Standard_DS3_v2"
        image:
          publisher: "paloaltonetworks"
          offer: "vmseries-flex"
          sku: "byol"
          version: "latest"
        availability_zone: "1"

      # Network Interfaces (auto-assigned to subnets)
      interfaces:
        - name: "management"
          subnet: "mgmt-subnet"
          public_ip: true
        - name: "ethernet1/1"
          subnet: "untrust-subnet"       # Shared
          public_ip: true
        - name: "ethernet1/2"
          subnet: "trust-subnet"         # Datacenter trust (shared)
          public_ip: false

      # Credentials: Reference to tenant manager
      credentials_ref: "firewall"

      # Configuration (reuses folder schema)
      configuration:
        device:
          hostname: null                 # Auto from system name
          timezone: "US/Pacific"
          dns_primary: "8.8.8.8"
          dns_secondary: "8.8.4.4"
          ntp_primary: "time.google.com"
        # ... zones, interfaces, objects, policies

    - name: null                         # Auto: {rg}-fw2
      type: "branch"
      role: "remote_network"

      vm_settings:
        size: "Standard_DS3_v2"
        # ...

      interfaces:
        - name: "management"
          subnet: "mgmt-subnet"
          public_ip: true
        - name: "ethernet1/1"
          subnet: "untrust-subnet"       # Shared with other FWs
          public_ip: true
        - name: "ethernet1/2"
          subnet: "trust-branch1-subnet" # DEDICATED branch trust
          public_ip: false

      credentials_ref: "firewall"        # Same creds as datacenter FW
      # ...
```

### 5.4 Subnet Auto-Generation for Multiple Branches

When user adds multiple branch firewalls, subnets are auto-generated:

```yaml
# User adds 2 branch firewalls in same region
# System auto-generates:

virtual_network:
  subnets:
    - name: "mgmt-subnet"
      prefix: "10.100.0.0/24"
      purpose: "management"
    - name: "untrust-subnet"
      prefix: "10.100.1.0/24"
      purpose: "untrust"
      shared: true
    - name: "trust-subnet"
      prefix: "10.100.2.0/24"
      purpose: "trust"
      for_firewall: "datacenter"
    - name: "trust-branch1-subnet"       # Auto-added
      prefix: "10.100.3.0/24"
      purpose: "trust"
      for_firewall: "branch1"
    - name: "trust-branch2-subnet"       # Auto-added
      prefix: "10.100.4.0/24"
      purpose: "trust"
      for_firewall: "branch2"
```

### 5.5 Object Reuse Strategy

| Object Type | Source Schema | Firewall Method | SCM Method |
|-------------|---------------|-----------------|------------|
| addresses | `config/models/objects.py` | `to_firewall_xml()` | `to_scm_json()` |
| address_groups | `config/models/objects.py` | `to_firewall_xml()` | `to_scm_json()` |
| services | `config/models/objects.py` | `to_firewall_xml()` | `to_scm_json()` |
| service_groups | `config/models/objects.py` | `to_firewall_xml()` | `to_scm_json()` |
| security_rules | `config/models/security.py` | `to_firewall_xml()` | `to_scm_json()` |
| nat_rules | `config/models/security.py` | `to_firewall_xml()` | `to_scm_json()` |
| profiles | `config/models/profiles.py` | `to_firewall_xml()` | `to_scm_json()` |

### 5.6 Firewall-Specific Objects (Not in SCM)

| Object Type | Description | Notes |
|-------------|-------------|-------|
| device_settings | Hostname, DNS, NTP, timezone | Firewall only |
| zones | Security zones | Firewall config differs from SCM |
| interfaces | Layer 3 interfaces | Firewall only |
| virtual_routers | Routing configuration | Firewall only |
| ike_gateways | IKE gateway config | Firewall XML version |
| ipsec_tunnels | IPSec tunnel config | Firewall XML version |

---

## 6. Panorama Object

### 6.1 Panorama Purpose

**DECISION:** Panorama deployment is for initial setup only. Managing firewalls via Panorama is a future feature. Licensing is user responsibility with workflow pause/resume support.

### 6.2 Panorama Schema

```yaml
cloud:
  panorama:
    name: null                           # Auto: {rg}-panorama

    vm_settings:
      size: "Standard_DS4_v2"
      image:
        publisher: "paloaltonetworks"
        offer: "panorama"
        sku: "byol"
        version: "latest"

    interface:
      subnet: "mgmt-subnet"
      public_ip: true

    credentials_ref: "panorama"

    licensing:
      status: "pending"                  # pending | licensed | skipped
      licensed_at: null
      plugins_installed: false

    configuration:
      device:
        hostname: null                   # Auto from system name
        timezone: "US/Pacific"
        dns_primary: "8.8.8.8"
        ntp_primary: "time.google.com"

      plugins:
        - name: "cloud_services"
          version: "latest"

      # FUTURE: Device groups and templates
      device_groups: []
      templates: []

      # Prisma Access Plugin (mirrors SCM infrastructure)
      prisma_access:
        service_connections: []
        remote_networks: []
        mobile_users:
          portals: []
          gateways: []
```

### 6.3 Licensing Workflow

```
Deployment Flow:
1. Terraform deploys Panorama VM
2. Initial device settings configured
3. PAUSE - User licenses Panorama manually
4. User marks licensing complete in UI
5. RESUME - Install plugins, push configuration
6. Complete
```

---

## 7. Supporting VMs

### 7.1 Supporting VM Schema

```yaml
cloud:
  supporting_vms:
    servers:
      - name: null                       # Auto: {rg}-server or {rg}-server1
        vm_settings:
          size: "Standard_B2s"
          os: "linux"
          image:
            publisher: "Canonical"
            offer: "0001-com-ubuntu-server-jammy"
            sku: "22_04-lts"
        interface:
          subnet: "trust-subnet"
          private_ip: "10.100.2.10"
        services:
          - type: "web_server"
            port: 80
          - type: "ssh"
            port: 22

    clients:
      - name: null                       # Auto: {rg}-uservm-win
        vm_settings:
          size: "Standard_B2s"
          os: "windows"
          image:
            publisher: "MicrosoftWindowsDesktop"
            offer: "Windows-11"
            sku: "win11-22h2-pro"
        interface:
          subnet: "trust-subnet"
          private_ip: "10.100.2.20"
        globalprotect:
          install: true
          portal: "gp.prismaaccess.com"

      - name: null                       # Auto: {rg}-uservm-linux
        vm_settings:
          size: "Standard_B2s"
          os: "linux"
          image:
            publisher: "Canonical"
            offer: "0001-com-ubuntu-server-jammy"
            sku: "22_04-lts"
        interface:
          subnet: "trust-subnet"
          private_ip: "10.100.2.21"

    ztna_connectors:
      - name: null                       # Auto: {rg}-ztna
        vm_settings:
          size: "Standard_B2s"
          os: "linux"
          image:
            publisher: "paloaltonetworks"
            offer: "ztna-connector"
            sku: "byol"
        interface:
          subnet: "trust-subnet"
          private_ip: "10.100.2.30"
        # No additional config - managed via Prisma Access
```

---

## 8. Workflow State (Pause/Resume)

### 8.1 Workflow State Storage

**DECISION:** Workflow state stored in config file. On load, prompt user to resume where they left off.

### 8.2 Workflow State Schema

```yaml
workflow_state:
  current_phase: "terraform_complete"    # Phase identifier
  last_updated: "2024-01-15T14:30:00Z"

  phases:
    config_complete:
      status: "complete"
      completed_at: "2024-01-15T10:00:00Z"

    terraform_running:
      status: "complete"
      started_at: "2024-01-15T10:05:00Z"
      completed_at: "2024-01-15T10:15:00Z"

    terraform_complete:
      status: "complete"
      completed_at: "2024-01-15T10:15:00Z"
      outputs:
        firewall_mgmt_ips: ["52.x.x.x"]
        panorama_mgmt_ip: "52.x.x.x"

    licensing_pending:
      status: "in_progress"              # PAUSED HERE
      started_at: "2024-01-15T10:15:00Z"
      awaiting: ["panorama_license"]

    firewall_config:
      status: "pending"

    panorama_config:
      status: "pending"

    scm_config:
      status: "pending"

    complete:
      status: "pending"

  # User can add notes
  notes: "Waiting for customer to provide Panorama license"
```

### 8.3 Resume Prompt on Load

```
┌─────────────────────────────────────────────────────────────┐
│  Resume Previous Deployment?                                 │
│                                                              │
│  This configuration has an incomplete deployment:            │
│                                                              │
│  ✓ Configuration saved                                       │
│  ✓ Terraform deployment complete                             │
│  ⏸ Licensing pending (Panorama)                              │
│  ○ Firewall configuration                                    │
│  ○ Panorama configuration                                    │
│  ○ SCM configuration                                         │
│                                                              │
│  Last updated: Jan 15, 2024 2:30 PM                         │
│  Note: "Waiting for customer to provide Panorama license"   │
│                                                              │
│  [Resume Deployment]  [Start Fresh]  [View Config Only]     │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. Architectural Decisions Summary

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | Object class design | Unified objects with deployment-aware methods | Objects contain all CRUD + dependencies; deployment target from parent context |
| 2 | Credential storage | Expanded Tenant Manager with generate option | Default: generated before TF runs; supports password/API key/certificate |
| 3 | Terraform state | Local, encrypted, with config | Simple, portable, secure |
| 4 | Licensing | User responsibility with pause/resume | Workflow saves state; user licenses manually; resume to complete |
| 5 | Multiple firewalls | Yes, typed as branch/datacenter | Branch→dedicated trust; Datacenter→shared trust; same untrust if same region |
| 6 | Cloud providers | Azure only for v1 | AWS/GCP/VMware/ION on roadmap |
| 7 | Naming convention | Consistent {customer}-{region}-{type}-rg pattern | Predictable, readable, sortable |
| 8 | Workflow state | Stored in config file | Enables resume prompt on load |

---

## 10. Existing Terraform Reference

### 10.1 Reference Repository

**Source:** [jshively37/pa_azure_lab_automation](https://github.com/jshively37/pa_azure_lab_automation)

This existing Terraform codebase provides a proven foundation for Azure deployments and should be used as the starting point for Phase 4.

### 10.2 What Already Exists (Can Reuse/Adapt)

| Component | File | Status | Notes |
|-----------|------|--------|-------|
| Azure provider config | `provider.tf` | ✅ Reuse | Standard Azure provider setup |
| VNet + Subnets | `azure_networking.tf` | ✅ Adapt | 4 subnets (/26 each), NSG, route tables |
| Firewall VM | `pa_vm.tf` | ✅ Adapt | vmseries-flex BYOL, 3 NICs |
| Panorama VM | `panorama.tf` | ✅ Reuse | Conditional with `count`, BYOL |
| Ubuntu jumpbox | `ubuntu.tf` | ✅ Reuse | Ubuntu 22.04 LTS Gen2 |
| Windows jumpbox | `windows.tf` | ✅ Reuse | Windows desktop VM |
| Outputs | `outputs.tf` | ✅ Adapt | FQDNs, IPs, interface names |
| Role-based CIDR | `variables.tf` | ✅ Adapt | rn/sc/pan → branch/datacenter |

### 10.3 What Needs to Be Extended

| Enhancement | Description | Complexity |
|-------------|-------------|------------|
| Dynamic naming | `{customer}-{region}-{type}-rg` pattern | Low |
| Multiple firewalls | Support branch + datacenter in same deployment | Medium |
| Per-branch trust subnets | Auto-generate trust-branch{n}-subnet | Medium |
| ZTNA Connector VM | New VM type (PA image) | Low |
| Jinja2 templates | Convert static .tf to .tf.j2 templates | Medium |
| Config integration | Generate from CloudConfig model | Medium |
| Credential injection | Pass generated creds to TF vars | Low |
| State encryption | Encrypt tfstate file | Medium |

### 10.4 Existing Patterns to Follow

```hcl
# Naming pattern (from existing code)
local.slug_name = "${var.role}-${random_id.this.hex}"

# Subnet calculation (from existing code)
subnets = cidrsubnets(var.role_default_cidrs[var.role], 2, 2, 2, 2)
# Results in 4x /26 subnets from a /22

# Conditional resource (from existing code)
count = var.create_panorama ? 1 : 0

# Static IP assignment (from existing code)
private_ip_address = cidrhost(azurerm_subnet.trust.address_prefixes[0], 5)
```

### 10.5 Image References (from existing code)

```hcl
# Firewall
source_image_reference {
  publisher = "paloaltonetworks"
  offer     = "vmseries-flex"
  sku       = "byol"
  version   = "latest"
}

# Panorama
source_image_reference {
  publisher = "paloaltonetworks"
  offer     = "panorama"
  sku       = "byol"
  version   = "latest"
}

# Ubuntu
source_image_reference {
  publisher = "Canonical"
  offer     = "0001-com-ubuntu-server-jammy"
  sku       = "22_04-lts-gen2"
  version   = "latest"
}
```

---

## 11. Implementation Phases

### Phase 1: Core Framework Extension
**Goal:** Extend the existing configuration model to support cloud hierarchy

| Task | Description | Files Affected |
|------|-------------|----------------|
| 1.1 | Create `CloudConfig` container class | `config/models/containers.py` |
| 1.2 | Create `CloudDeployment` model with naming logic | `config/models/cloud/deployment.py` |
| 1.3 | Create `CloudFirewall` model | `config/models/cloud/firewall.py` |
| 1.4 | Create `CloudPanorama` model | `config/models/cloud/panorama.py` |
| 1.5 | Create `SupportingVM` models | `config/models/cloud/supporting_vms.py` |
| 1.6 | Create `WorkflowState` model | `config/models/cloud/workflow_state.py` |
| 1.7 | Update `Configuration` to include `cloud` and `workflow_state` | `config/models/containers.py` |
| 1.8 | Update `ConfigItemFactory` for cloud types | `config/models/factory.py` |

### Phase 2: Tenant Manager Extension
**Goal:** Expand credential management for all device types

| Task | Description | Files Affected |
|------|-------------|----------------|
| 2.1 | Add firewall credential schema with generate option | `config/tenant_manager.py` |
| 2.2 | Add Panorama credential schema with generate option | `config/tenant_manager.py` |
| 2.3 | Add supporting VM credential auto-generation | `config/tenant_manager.py` |
| 2.4 | Add certificate/SSH key auth support | `config/tenant_manager.py` |
| 2.5 | Add secure password generator | `config/tenant_manager.py` |
| 2.6 | Update tenant settings UI with credential options | `gui/settings_widget.py` |

### Phase 3: Object Serialization
**Goal:** Add deployment-specific serialization methods to existing objects

| Task | Description | Files Affected |
|------|-------------|----------------|
| 3.1 | Add `to_firewall_xml()` to address objects | `config/models/objects.py` |
| 3.2 | Add `to_firewall_xml()` to service objects | `config/models/objects.py` |
| 3.3 | Add `to_firewall_xml()` to security rules | `config/models/security.py` |
| 3.4 | Add `to_firewall_xml()` to NAT rules | `config/models/security.py` |
| 3.5 | Add `to_firewall_xml()` to profiles | `config/models/profiles.py` |
| 3.6 | Create firewall-specific objects (zones, interfaces, etc.) | `config/models/cloud/firewall_objects.py` |

### Phase 4: Terraform Integration (Adapt from Reference Repo)
**Goal:** Adapt existing Terraform from `pa_azure_lab_automation` and integrate with config framework

**Reference:** https://github.com/jshively37/pa_azure_lab_automation

| Task | Description | Source | Files Affected |
|------|-------------|--------|----------------|
| 4.1 | Fork/copy reference Terraform to project | Reference repo | `terraform/azure/` |
| 4.2 | Create naming utility functions | New | `terraform/naming.py` |
| 4.3 | Convert `azure_networking.tf` to Jinja2 template | Adapt existing | `terraform/templates/azure/networking.tf.j2` |
| 4.4 | Extend networking for multiple branch subnets | Adapt existing | `terraform/templates/azure/networking.tf.j2` |
| 4.5 | Convert `pa_vm.tf` to support multiple firewalls | Adapt existing | `terraform/templates/azure/firewall.tf.j2` |
| 4.6 | Convert `panorama.tf` to Jinja2 template | Adapt existing | `terraform/templates/azure/panorama.tf.j2` |
| 4.7 | Convert `ubuntu.tf` / `windows.tf` to templates | Adapt existing | `terraform/templates/azure/supporting.tf.j2` |
| 4.8 | Add ZTNA Connector VM template | New | `terraform/templates/azure/ztna.tf.j2` |
| 4.9 | Update `variables.tf` for new naming/multi-fw | Adapt existing | `terraform/templates/azure/variables.tf.j2` |
| 4.10 | Update `outputs.tf` for multi-firewall outputs | Adapt existing | `terraform/templates/azure/outputs.tf.j2` |
| 4.11 | Create `TerraformGenerator` class | New | `terraform/generator.py` |
| 4.12 | State encryption integration | New | `terraform/state_manager.py` |
| 4.13 | Credential injection before TF run | New | `terraform/generator.py` |

### Phase 5: Deployment APIs
**Goal:** Implement deployment to firewall and Panorama APIs

| Task | Description | Files Affected |
|------|-------------|----------------|
| 5.1 | Create `FirewallAPIClient` class | `firewall/api_client.py` |
| 5.2 | Create firewall push orchestrator | `firewall/push/orchestrator.py` |
| 5.3 | Create `PanoramaAPIClient` class | `panorama/api_client.py` |
| 5.4 | Create Panorama push orchestrator | `panorama/push/orchestrator.py` |
| 5.5 | Implement workflow state manager | `deployment/workflow_state.py` |
| 5.6 | Unified deployment coordinator | `deployment/coordinator.py` |

### Phase 6: GUI Integration
**Goal:** Connect POV workflow tabs to new configuration framework

| Task | Description | Files Affected |
|------|-------------|----------------|
| 6.1 | Tab 1 - Credential choice UI (generated vs custom) | `gui/workflows/pov_workflow.py` |
| 6.2 | Tab 2 dialogs → CloudDeployment model | `gui/dialogs/cloud/` |
| 6.3 | Tab 3 dialogs → Use case templates | `gui/dialogs/use_cases/` |
| 6.4 | Tab 4 → Terraform generation & deployment | `gui/workflows/pov_workflow.py` |
| 6.5 | Tab 5 → Configuration deployment with pause/resume | `gui/workflows/pov_workflow.py` |
| 6.6 | Resume prompt dialog on config load | `gui/dialogs/resume_workflow_dialog.py` |
| 6.7 | Settings → Expanded credential management | `gui/settings_widget.py` |

---

## 12. File Structure (Proposed)

```
config/
├── models/
│   ├── base.py                    # ConfigItem with serialization methods
│   ├── containers.py              # Add CloudConfig, WorkflowState containers
│   ├── factory.py                 # Update for cloud types
│   ├── objects.py                 # Add to_firewall_xml() methods
│   ├── security.py                # Add to_firewall_xml() methods
│   ├── profiles.py                # Add to_firewall_xml() methods
│   └── cloud/                     # NEW: Cloud infrastructure models
│       ├── __init__.py
│       ├── deployment.py          # CloudDeployment model + naming logic
│       ├── firewall.py            # CloudFirewall model
│       ├── firewall_objects.py    # Zones, interfaces, virtual routers
│       ├── panorama.py            # CloudPanorama model
│       ├── supporting_vms.py      # SupportingVM models
│       └── workflow_state.py      # WorkflowState model
├── tenant_manager.py              # EXTEND: Add firewall/panorama/vm creds

terraform/                          # NEW: Terraform generation
├── __init__.py
├── naming.py                      # Naming convention utilities
├── generator.py                   # TerraformGenerator class
├── state_manager.py               # Encrypted state management
└── templates/
    └── azure/
        ├── main.tf.j2
        ├── variables.tf.j2
        ├── outputs.tf.j2
        ├── network.tf.j2          # VNet + dynamic subnets
        ├── firewall/
        │   ├── main.tf.j2
        │   └── variables.tf.j2
        ├── panorama/
        │   └── ...
        └── supporting/
            ├── server.tf.j2
            ├── client.tf.j2
            └── ztna_connector.tf.j2

firewall/                          # NEW: Firewall API integration
├── __init__.py
├── api_client.py                  # FirewallAPIClient (XML API)
└── push/
    └── orchestrator.py            # Firewall push logic

panorama/                          # NEW: Panorama API integration
├── __init__.py
├── api_client.py                  # PanoramaAPIClient (XML API)
└── push/
    └── orchestrator.py            # Panorama push logic

deployment/                        # NEW: Unified deployment
├── __init__.py
├── coordinator.py                 # Orchestrates TF + API deployments
└── workflow_state.py              # Pause/resume state management

gui/
├── dialogs/
│   ├── cloud/                     # NEW: Cloud config dialogs
│   │   └── ...
│   ├── use_cases/                 # NEW: Use case dialogs
│   │   └── ...
│   └── resume_workflow_dialog.py  # NEW: Resume prompt
```

---

## 13. Dependencies & Prerequisites

| Dependency | Purpose | Required For | Notes |
|------------|---------|--------------|-------|
| `pan-os-python` | Firewall/Panorama XML API | Phase 5 | Official Palo Alto SDK |
| `azure-identity` | Azure authentication | Phase 4 | For Terraform Azure provider |
| `Jinja2` | Terraform templates | Phase 4 | Template rendering |
| `subprocess` | Execute Terraform | Phase 4 | Built-in Python |
| `cryptography` | State encryption | Phase 4 | Already in use for config encryption |
| `secrets` | Password generation | Phase 2 | Built-in Python |

---

## 14. Next Steps

1. **Review this updated plan** - Confirm all decisions captured correctly
2. **Detail Phase 1** - Create detailed specs for CloudConfig models
3. **Detail Phase 2** - Design tenant manager schema extension
4. **Share Panorama setup doc** - Incorporate licensing/plugin steps
5. **Prototype** - Build minimal CloudDeployment + naming utilities
6. **Iterate** - Expand based on implementation learnings

---

## 15. Related Documents

- [ROADMAP_FUTURE.md](ROADMAP_FUTURE.md) - Long-term feature roadmap
- [API_REFERENCE.md](API_REFERENCE.md) - Existing SCM API documentation
- Panorama Setup Guide (Google Doc - to be shared)

---

*Document Version: 1.3*
*Last Updated: 2024*
*Status: DRAFT - Decisions Captured, Reference Terraform Identified*
