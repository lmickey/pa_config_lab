# GUI Quick Start Guide

## Launching the Application

```bash
# From project root
python run_gui.py

# Or activate venv first
source venv/bin/activate
python run_gui.py
```

---

## Workflow 1: POV Configuration

### Goal
Configure a new POV (Proof of Value) environment for Prisma Access.

### Steps

**1. Select Workflow**
- Click **"🔧 POV Configuration"** in the left sidebar

**2. Load Configuration**
- Click **"Browse..."** button
- Select your configuration file:
  - JSON config file (`.json`)
  - Legacy encrypted file (`.bin`)
- Click **"Load Configuration"**
- Enter password if using encrypted file

**3. Review Configuration**
- Automatically switches to **"2. Review"** tab
- Verify firewall settings:
  - Management IP
  - Interface configuration
  - Zone configuration
- Verify Prisma Access settings:
  - TSG ID
  - Region
  - Service connection details

**4. Configure Firewall**
- Switch to **"3. Firewall"** tab
- Select options to configure:
  - ✅ Zones (trust/untrust)
  - ✅ Interfaces
  - ✅ Routes
  - ✅ Address Objects
  - ✅ Security Policies
  - ✅ NTP/DNS
- Click **"Configure Firewall"**
- Confirm in dialog
- Monitor progress bar

**5. Configure Prisma Access**
- Switch to **"4. Prisma Access"** tab
- Select options:
  - ✅ IKE Crypto Profile
  - ✅ IPSec Crypto Profile
  - ✅ IKE Gateway
  - ✅ IPSec Tunnel
  - ✅ Service Connection
- Click **"Configure Prisma Access"**
- Confirm in dialog
- Monitor progress bar

**6. Complete**
- Click **"✓ Complete POV Setup"**
- Review completion message

---

## Workflow 2: Configuration Migration

### Goal
Pull configuration from source tenant and push to target tenant.

### Steps

**1. Select Workflow**
- Click **"🔄 Configuration Migration"** in the left sidebar

**2. Connect to Source Tenant**
- Click **"File" → "Connect to API..."**
- Enter source credentials:
  - TSG ID
  - API User (Client ID)
  - API Secret (Client Secret)
- Click **"Connect"**
- Wait for authentication

**3. Pull Configuration**
- In **"1. Pull Configuration"** tab
- Select components to pull:
  - ✅ Folders
  - ✅ Snippets
  - ✅ Security Rules
  - ✅ Objects (addresses, services, apps)
  - ✅ Profiles
- Optional: ✅ **"Filter out defaults"**
- Click **"Pull Configuration"**
- Monitor progress

**4. View & Analyze**
- Automatically switches to **"2. View & Analyze"** tab
- Browse configuration tree:
  - Expand folders
  - Click items to view details
- Use search to find specific items
- Use filter dropdown to show specific types

**5. Connect to Target Tenant**
- Click **"File" → "Connect to API..."**
- Enter target tenant credentials
- Click **"Connect"**

**6. Push Configuration**
- Switch to **"3. Push Configuration"** tab
- Select conflict resolution:
  - ⚪ Skip - Skip conflicting items
  - ⚪ Overwrite - Replace existing items
  - ⚪ Rename - Create new with suffix
- Options:
  - ✅ **"Dry Run"** (recommended first time)
  - ✅ **"Validate configuration"**
- Click **"Push Configuration"**
- Review results
- If dry run successful, uncheck and push for real

---

## Navigation Tips

### Sidebar
- **🏠 Home** - Dashboard and workflow selection
- **🔧 POV Configuration** - Set up new environments
- **🔄 Configuration Migration** - Pull/push between tenants
- **📊 Logs & Monitoring** - View all activity logs

### Connection Status
- Shows at bottom of sidebar
- **Gray** = Not connected
- **Green** = Connected to tenant

### Logs Tab
- Real-time activity logging
- Filter by level (Info, Success, Warning, Error)
- Export logs to file
- Clear logs

### Settings
- **File → Settings**
- General preferences
- API timeouts and rate limits
- Debug mode
- Max log entries

---

## Keyboard Shortcuts

- **Ctrl+N** - Connect to API
- **Ctrl+O** - Load Configuration (Migration workflow)
- **Ctrl+S** - Save Configuration (Migration workflow)
- **Ctrl+P** - Pull Configuration (Migration workflow)
- **Ctrl+U** - Push Configuration (Migration workflow)
- **Ctrl+Q** - Exit
- **F1** - Documentation

---

## Troubleshooting

### "Not Connected" Error
**Problem:** Trying to pull/push without API connection  
**Solution:** Click "File → Connect to API..." and enter credentials

### "No Configuration Loaded" Error (POV)
**Problem:** Trying to configure without loading config  
**Solution:** Go to "1. Load" tab and load a configuration file

### "No Configuration Loaded" Error (Migration)
**Problem:** Trying to push without pulling first  
**Solution:** Pull configuration from source tenant first

### Connection Timeout
**Problem:** API connection fails  
**Solution:** 
- Verify credentials
- Check network connection
- Increase timeout in Settings

### Slow Performance
**Problem:** Large configurations load slowly  
**Solution:**
- Use "Filter out defaults" when pulling
- Increase max tree items in Settings
- Close other applications

---

## Best Practices

### POV Configuration
1. Always **review** configuration before applying
2. Test firewall connectivity before configuring
3. Verify Prisma Access API access first
4. Keep configuration backups

### Configuration Migration
1. Always use **"Dry Run"** first
2. Start with **"Skip"** conflict resolution for first attempt
3. Review logs after each operation
4. Export logs for documentation
5. Test on non-production tenants first

### General
- Keep application settings backed up
- Use encrypted configuration files
- Export logs regularly
- Test in lab before production

---

## Need Help?

- **Documentation:** `docs/GUI_USER_GUIDE.md`
- **Troubleshooting:** `TROUBLESHOOTING.md`
- **Architecture:** `GUI_RESTRUCTURE_COMPLETE.md`
- **Full Guide:** `GUI_MULTI_WORKFLOW_COMPLETE.md`

---

**Enjoy using the Prisma Access Configuration Manager!** 🎉
