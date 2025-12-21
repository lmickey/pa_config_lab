# Prisma Access Configuration Manager - GUI User Guide

**Version:** 1.0.0  
**Framework:** PyQt6  
**Platform:** Cross-platform (Windows, macOS, Linux)

---

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Getting Started](#getting-started)
4. [Features](#features)
5. [User Guide](#user-guide)
6. [Troubleshooting](#troubleshooting)
7. [Keyboard Shortcuts](#keyboard-shortcuts)

---

## Introduction

The Prisma Access Configuration Manager is a comprehensive GUI application for managing Prisma Access configurations. It provides an intuitive interface for pulling configurations from source tenants, viewing and editing them, and pushing to target tenants—all with built-in conflict detection, dependency resolution, and security features.

### Key Features

- **Pull Configurations** - Extract complete configurations from Prisma Access
- **Configuration Viewer** - Browse and search configurations in tree format
- **Push Configurations** - Deploy configurations with conflict resolution
- **Activity Logging** - Track all operations with detailed logs
- **Secure Storage** - NIST-compliant encryption for saved configurations
- **Settings** - Customize API timeouts, rate limits, and UI preferences

---

## Installation

### Prerequisites

- Python 3.9 or higher
- Virtual environment (recommended)

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Launch the Application

```bash
python run_gui.py
```

Or directly:

```bash
python -m gui.main_window
```

---

## Getting Started

### 1. Connect to Prisma Access

1. Launch the application
2. Click **File → Connect** or the "Connect to Prisma Access" button
3. Enter your credentials:
   - **TSG ID**: Your Tenant Service Group ID
   - **API User**: Your API Client ID
   - **API Secret**: Your API Client Secret
4. Optionally check "Remember credentials" (API secret not saved for security)
5. Click **Connect**

The application will authenticate in the background and display connection status.

### 2. Pull Configuration

Once connected:

1. Go to the **Pull** tab or select **Configuration → Pull Configuration**
2. Select which components to pull:
   - Security Policy Folders
   - Configuration Snippets
   - Security Rules
   - Security Objects (addresses, services, etc.)
   - Security Profiles
3. Optionally enable "Filter Default Configurations"
4. Click **Pull Configuration**
5. Monitor progress in the progress bar
6. View results when complete

### 3. View Configuration

1. Go to the **Configuration** tab
2. Browse the configuration tree
3. Click any item to view details in JSON format
4. Use the search box to find specific items
5. Filter by type using the dropdown

### 4. Push Configuration

1. Ensure a configuration is loaded
2. Go to the **Push** tab or select **Configuration → Push Configuration**
3. Choose conflict resolution strategy:
   - **Skip**: Don't push conflicting items
   - **Overwrite**: Replace existing items
   - **Rename**: Create new items with modified names
4. Enable "Dry Run" to simulate without changes (recommended first)
5. Click **Push Configuration**
6. Confirm the operation
7. Monitor progress and view results

### 5. Save/Load Configurations

**Save:**
1. Select **File → Save Configuration**
2. Choose location and filename
3. Configurations are saved as JSON (human-readable)

**Load:**
1. Select **File → Load Configuration**
2. Browse to your JSON file
3. Configuration loads with automatic validation

---

## Features

### Dashboard Tab

**Quick Actions:**
- Connect to Prisma Access
- Load Configuration File

**Status Display:**
- Connection status
- Current configuration info

### Pull Tab

**Components:**
- Selectable configuration items
- Filter defaults option
- Progress tracking
- Results summary

**Features:**
- Background processing (non-blocking UI)
- Detailed statistics
- Error handling

### Configuration Tab

**Tree View:**
- Hierarchical display of all configuration items
- Expandable/collapsible nodes
- Item counts

**Details Pane:**
- JSON format
- Syntax highlighting
- Read-only (editing coming in future version)

**Search & Filter:**
- Search by name
- Filter by type
- Instant results

### Push Tab

**Conflict Resolution:**
- Skip conflicting items
- Overwrite existing items
- Rename to create new items

**Options:**
- Dry run mode
- Validation before push

**Safety:**
- Confirmation dialogs
- Progress tracking
- Detailed results

### Logs Tab

**Features:**
- Real-time activity logging
- Color-coded log levels (Info, Success, Warning, Error)
- Timestamps
- Filter by level
- Export to file
- Clear logs

**Log Retention:**
- Up to 1,000 entries (configurable in settings)

### Settings Dialog

**General:**
- Window state persistence
- Auto-expand tree view
- Auto-validate files
- Backup before overwrite

**API:**
- Request timeout
- Rate limiting
- Cache TTL

**Advanced:**
- Max log entries
- Debug mode
- Max tree items

---

## User Guide

### Workflow Examples

#### Example 1: Clone Configuration Between Tenants

1. **Connect to Source Tenant**
   - File → Connect
   - Enter source tenant credentials

2. **Pull Complete Configuration**
   - Pull tab → Select all components
   - Click Pull Configuration

3. **Save Configuration**
   - File → Save Configuration
   - Save as `source-config.json`

4. **Connect to Target Tenant**
   - File → Connect
   - Enter target tenant credentials

5. **Load Configuration**
   - File → Load Configuration
   - Select `source-config.json`

6. **Push to Target**
   - Push tab → Select conflict strategy
   - Enable Dry Run first
   - Click Push Configuration
   - Review results
   - Run again without Dry Run

#### Example 2: Backup Configuration

1. Connect to tenant
2. Pull all configuration components
3. Enable "Filter Default Configurations"
4. Save to dated file (e.g., `backup-2024-12-20.json`)
5. Export logs for audit trail

#### Example 3: Analyze Configuration

1. Load or pull configuration
2. Configuration → Detect Defaults
3. View filtered results
4. Configuration → Analyze Dependencies
5. Review dependency report

### Tips & Best Practices

**Security:**
- Never share API credentials
- Use "Dry Run" before pushing
- Keep backups of important configurations
- Review conflict detection results carefully

**Performance:**
- Filter defaults to reduce configuration size
- Use search to find items quickly
- Close application to clear cache

**Troubleshooting:**
- Check Logs tab for detailed error messages
- Verify API credentials if connection fails
- Ensure network connectivity to Prisma Access
- Check rate limits if requests fail

---

## Troubleshooting

### Connection Issues

**Problem:** "Authentication failed"

**Solutions:**
- Verify TSG ID, API User, and API Secret
- Check network connectivity
- Ensure API credentials are active
- Check Logs tab for detailed error

**Problem:** "Rate limit exceeded"

**Solutions:**
- Wait 60 seconds before retrying
- Adjust rate limit in Settings
- Reduce pull scope (select fewer components)

### Pull Issues

**Problem:** "Pull operation timed out"

**Solutions:**
- Increase timeout in Settings → API → Request Timeout
- Reduce items being pulled
- Check network stability

**Problem:** "Permission denied"

**Solutions:**
- Verify API credentials have required permissions
- Check folder/tenant access rights

### Push Issues

**Problem:** "Many conflicts detected"

**Solutions:**
- Use "Skip" strategy to avoid conflicts
- Review conflicts in results pane
- Consider "Rename" strategy to create new items
- Use "Overwrite" only if intentional

**Problem:** "Validation failed"

**Solutions:**
- Review configuration in Configuration tab
- Check for missing dependencies
- Run Configuration → Analyze Dependencies

### Application Issues

**Problem:** Application won't start

**Solutions:**
- Verify Python 3.9+ installed
- Activate virtual environment
- Install/reinstall dependencies: `pip install -r requirements.txt`
- Check for PyQt6: `pip install PyQt6`

**Problem:** UI not responding

**Solutions:**
- Wait for background operations to complete
- Check progress indicators
- Restart application if frozen

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | Connect to Prisma Access |
| `Ctrl+O` | Load Configuration |
| `Ctrl+S` | Save Configuration |
| `Ctrl+Q` | Exit Application |
| `Ctrl+P` | Pull Configuration |
| `Ctrl+U` | Push Configuration |
| `F1` | Help/Documentation |

---

## Support

For issues, questions, or feedback:

1. Check the Logs tab for error details
2. Review this documentation
3. Check the `docs/` directory for technical documentation
4. Refer to `TROUBLESHOOTING.md` for detailed solutions

---

## Version History

### Version 1.0.0 (December 2024)
- Initial release
- Complete pull/push workflow
- Configuration viewer
- Activity logging
- Settings dialog
- Security hardening

---

**Built with PyQt6** | **Secure by Design** | **Production Ready**
