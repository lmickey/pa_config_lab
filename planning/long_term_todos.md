# Long-Term TODO List

This document tracks larger features and improvements that require significant planning and implementation effort.

---

## High Priority

### 1. Review Defaults for All Configuration Options
**Status:** Not Started  
**Complexity:** High  
**Estimated Effort:** Multi-session

#### Description
Create a comprehensive system for identifying default configurations across all Prisma Access object types. Many configurations come pre-populated with defaults that shouldn't be migrated or may conflict with target tenant settings.

#### Steps
1. **Create Default Identification Script**
   - Build a script to pull configuration from a live tenant
   - Pull one section/component type at a time
   - Output configurations in a format that allows manual review
   - Include ability to mark/tag items as defaults

2. **Manual Default Analysis**
   - For each configuration type, identify patterns that indicate defaults:
     - Name-based (e.g., "default", "predefined", specific naming patterns)
     - Property-based (e.g., `is_default: true`, `type: predefined`)
     - Combination indicators (name + specific property values)
   - Document findings for each object type

3. **Update Configuration Classes**
   - Add `is_default()` method or property to each ConfigItem subclass
   - Implement default detection logic based on analysis findings
   - Add `DEFAULT_PATTERNS` or similar class attributes for criteria

4. **Integration**
   - Update `DefaultManager` class with new detection logic
   - Add filtering options in pull/push workflows
   - Update UI to show/hide defaults with clear indicators

#### Object Types to Review
- [ ] Address Objects
- [ ] Address Groups
- [ ] Service Objects
- [ ] Service Groups
- [ ] Application Groups
- [ ] Application Filters
- [ ] Tags
- [ ] Schedules
- [ ] External Dynamic Lists
- [ ] Custom URL Categories
- [ ] Anti-Spyware Profiles
- [ ] Vulnerability Profiles
- [ ] File Blocking Profiles
- [ ] WildFire Profiles
- [ ] DNS Security Profiles
- [ ] Decryption Profiles
- [ ] HTTP Header Profiles
- [ ] Certificate Profiles
- [ ] HIP Objects
- [ ] HIP Profiles
- [ ] Security Rules
- [ ] Decryption Rules
- [ ] Authentication Rules
- [ ] QoS Policy Rules

#### Notes
- Some defaults are tenant-specific (created during onboarding)
- Some defaults are global Palo Alto Networks predefined items
- Need to handle "modified defaults" - items that started as defaults but were customized

---

## Medium Priority

### 2. Push Workflow Implementation
**Status:** In Progress  
**Complexity:** High

Complete the push workflow with validation, preview, and conflict resolution.

### 3. Configuration Comparison Tool
**Status:** Not Started  
**Complexity:** Medium

Add ability to compare two configurations side-by-side, highlighting differences.

### 4. Bulk Operations
**Status:** Not Started  
**Complexity:** Medium

Support for bulk rename, bulk delete, bulk modify operations on configuration items.

### 5. Configuration Templates
**Status:** Not Started  
**Complexity:** Medium

Save and apply configuration templates for common setups.

---

## Low Priority

### 6. Export to Other Formats
**Status:** Not Started  
**Complexity:** Low

Export configuration to CSV, Excel, or other formats for documentation.

### 7. Audit Trail
**Status:** Not Started  
**Complexity:** Medium

Track all changes made through the tool with timestamps and user info.

### 8. Scheduled Operations
**Status:** Not Started  
**Complexity:** Medium

Schedule pull/push operations to run at specific times.

---

## Completed

- [x] Pull Tab Redesign (2026-01-05)
- [x] Custom Applications Support (2026-01-05)
- [x] Connection Status Updates (2026-01-05)
- [x] Smart Config Viewer Expansion (2026-01-05)
- [x] Dynamic Version Display (2026-01-05)

---

*Last Updated: 2026-01-05*
