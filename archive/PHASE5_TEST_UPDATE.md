# Phase 5 Test Update - Full Integration Workflow

## Overview

The Phase 5 test has been completely rewritten to perform a **full pull → save → push workflow** that actually exercises the complete system with real tenant API calls.

## Previous Test (Removed)

The previous test only performed unit tests and structure validation:
- ❌ Only tested code structure
- ❌ Didn't actually pull or push configuration
- ❌ Only asked for one set of credentials
- ❌ Completed almost immediately without API calls

## New Test Workflow

The new test performs a complete end-to-end workflow:

### 1. Source Tenant Setup
- Prompts for **source tenant credentials** (TSG ID, Client ID, Client Secret)
- Initializes source API client
- Discovers folders and snippets from source tenant
- **Interactive selection** of folders/snippets to pull (like test_phase4)

### 2. Pull Configuration
- Pulls complete configuration from source tenant
- Includes objects, profiles, rules, snippets
- Shows pull progress and summary

### 3. Save Backup
- Saves configuration to **automated backup file**
- Filename format: `backup_tsg{TSG_ID}_{timestamp}.json`
- Optional encryption with password
- Example: `backup_tsg1570970024_20251220_143022.json`

### 4. Load Backup
- Loads configuration from backup file
- Validates encryption if encrypted
- Displays configuration contents

### 5. Destination Tenant Setup
- Prompts for **destination tenant credentials** (TSG ID, Client ID, Client Secret)
- Initializes destination API client

### 6. Select Items to Push
- Shows what's in the backup file (folders and snippets)
- **Interactive selection** of what to push to destination
- Can select specific folders/snippets or all

### 7. Push Configuration
- Validates configuration before push
- Detects conflicts
- Supports conflict resolution strategies:
  - Skip (don't push conflicting items)
  - Overwrite (replace existing)
  - Rename (create with new name)
- Supports dry-run mode
- Pushes configuration to destination tenant

## Usage

```bash
python3 test_phase5.py
```

### Example Session Flow

```
============================================================
Phase 5: Push Functionality - Full Integration Test
============================================================

This test performs a complete workflow:
  1. Pull configuration from SOURCE tenant
  2. Save configuration to backup file
  3. Push configuration to DESTINATION tenant

You will need credentials for BOTH tenants.

------------------------------------------------------------
SOURCE TENANT (Configuration to Pull)
------------------------------------------------------------
Enter Source TSG ID: 1570970024
Enter Source API Client ID: cursor-dev@1570970024.iam.panserviceaccount.com
Enter Source API Client Secret: ********

Initializing source API client...
  ✓ Source API client initialized

Discovering folders and snippets from source tenant...
  ✓ Found 13 folders and 27 snippets

Available folders:
  1. Mobile Users
  2. Service Connections
  3. Remote Networks
  ...
Enter folder numbers to select (comma-separated, or press Enter for all): 1,2

  ✓ Selected 2 folder(s)

------------------------------------------------------------
PULLING CONFIGURATION FROM SOURCE
------------------------------------------------------------
Pulling configuration from source tenant (TSG: 1570970024)...
[Progress updates...]
  ✓ Configuration pulled successfully

------------------------------------------------------------
SAVING CONFIGURATION BACKUP
------------------------------------------------------------
Saving configuration to: backup_tsg1570970024_20251220_143022.json
Enter password for backup encryption (or press Enter for no encryption): ********
  ✓ Configuration saved to: backup_tsg1570970024_20251220_143022.json

------------------------------------------------------------
LOADING CONFIGURATION FROM BACKUP
------------------------------------------------------------
Loading configuration from: backup_tsg1570970024_20251220_143022.json
Enter password to decrypt backup: ********
  ✓ Configuration loaded successfully

------------------------------------------------------------
CONFIGURATION CONTENTS
------------------------------------------------------------
Folders in backup: 2
  1. Mobile Users
  2. Service Connections

Snippets in backup: 0

------------------------------------------------------------
DESTINATION TENANT (Configuration to Push)
------------------------------------------------------------
Enter Destination TSG ID: 9999999999
Enter Destination API Client ID: cursor-dev@9999999999.iam.panserviceaccount.com
Enter Destination API Client Secret: ********

Initializing destination API client...
  ✓ Destination API client initialized

------------------------------------------------------------
SELECT ITEMS TO PUSH
------------------------------------------------------------
Available folders:
  1. Mobile Users
  2. Service Connections
Enter folder numbers to select (comma-separated, or press Enter for all): 1

  ✓ Selected 1 folder(s) to push

Conflict Resolution Strategy:
  1. Skip (don't push conflicting items)
  2. Overwrite (replace existing)
  3. Rename (create with new name)
Select strategy (1-3, default=1): 1

Perform dry-run first? (y/n, default=y): y

------------------------------------------------------------
PUSHING CONFIGURATION TO DESTINATION
------------------------------------------------------------
Pushing configuration to destination tenant (TSG: 9999999999)...
Mode: DRY RUN
Conflict Strategy: skip
[Progress updates...]
  ✓ Push completed successfully
  ⚠ This was a dry-run - no changes were made

============================================================
WORKFLOW COMPLETE
============================================================
Backup file: backup_tsg1570970024_20251220_143022.json
Source TSG: 1570970024
Destination TSG: 9999999999
Mode: DRY RUN
```

## Key Features

### ✅ Real API Integration
- Actually calls Prisma Access APIs
- Pulls real configuration data
- Validates against real tenants

### ✅ Backup and Restore
- Saves configurations to timestamped backup files
- Can load backups for restoration
- Supports encryption for security

### ✅ Interactive Selection
- Multi-select prompts for folders/snippets
- Shows what's available before selection
- Shows what's in backup before pushing

### ✅ Conflict Detection
- Detects conflicts before pushing
- Multiple resolution strategies
- Dry-run mode for safe testing

### ✅ Complete Workflow
- End-to-end test of pull → save → push
- Validates entire system integration
- Ready for production use

## Benefits

1. **Real Testing**: Actually exercises the full system with real API calls
2. **Backup Capability**: Creates backups that can be restored later
3. **Migration Support**: Can migrate configuration between tenants
4. **Safety**: Dry-run mode prevents accidental changes
5. **Flexibility**: Select what to pull and what to push

## Future Enhancements

- Load existing backup files for restoration
- Compare configurations between tenants
- Incremental push (only changed items)
- Rollback capability after push

---

**Status**: ✅ Complete and Ready for Testing  
**Date**: December 20, 2025
