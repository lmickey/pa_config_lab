# Long-Term Roadmap & Future Features

This document tracks features and capabilities planned for future development beyond the current release scope.

---

## Cloud Provider Support

| Feature | Priority | Status | Notes |
|---------|----------|--------|-------|
| Azure deployment | High | In Progress | Current focus for POV workflow |
| AWS deployment | Medium | Future | EC2, VPC, security groups |
| GCP deployment | Low | Future | Compute Engine, VPC |

---

## Firewall Management

| Feature | Priority | Status | Notes |
|---------|----------|--------|-------|
| Direct firewall configuration (standalone) | High | In Progress | POV workflow Tab 4-5 |
| Panorama-managed firewalls | Medium | Future | Push config via Panorama device groups |
| VMware/ESXi deployment | Low | Future | VM-Series on vSphere |
| KVM/Hypervisor deployment | Low | Future | VM-Series on KVM |

---

## Network Infrastructure

| Feature | Priority | Status | Notes |
|---------|----------|--------|-------|
| Service Connection firewalls | High | In Progress | Datacenter site type |
| Remote Network firewalls | High | In Progress | Branch site type |
| Virtual ION (SD-WAN) | Low | Future | Datacenter site SD-WAN deployments |
| Physical appliance support | Low | Future | PA-400/800/3200 series initial config |

---

## Prisma Access Features

| Feature | Priority | Status | Notes |
|---------|----------|--------|-------|
| Mobile Users (GlobalProtect) | High | Planned | POV Use Case |
| Explicit Proxy | High | Planned | POV Use Case |
| ZTNA Connector | High | Planned | POV Use Case |
| Remote Browser Isolation | Medium | Planned | POV Use Case |
| Prisma Access Browser | Medium | Planned | POV Use Case |
| App Acceleration | Low | Planned | POV Use Case |
| ADEM/AIOps | Medium | Planned | POV Use Case |

---

## Integration & Automation

| Feature | Priority | Status | Notes |
|---------|----------|--------|-------|
| Terraform state encryption | High | Planned | Store with config files |
| Azure Key Vault integration | Low | Future | Alternative credential storage |
| CI/CD pipeline templates | Low | Future | GitHub Actions, Azure DevOps |
| API-driven deployments | Low | Future | Headless/scripted deployments |

---

## UI/UX Improvements

| Feature | Priority | Status | Notes |
|---------|----------|--------|-------|
| Deployment progress visualization | Medium | Planned | Real-time terraform output |
| Configuration diff viewer | Low | Future | Compare configs before push |
| Rollback support | Low | Future | Undo last deployment |

---

*Last Updated: 2024*
*Document Version: 1.0*
