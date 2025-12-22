# Migration Workflow Auto-Save Update

## Changes Made

### Auto-Save Pulled Configurations

**When:** Automatically after a successful pull from SCM

**Filename Format:** 
- With TSG: `pulled_{tsg_id}_{date}_{time}`
- Without TSG: `pulled_config_{date}_{time}`

**Example:** `pulled_tsg1570970024_20241220_153045`

### Workflow

1. **User pulls config from SCM** (Tab 1: Pull from SCM)
2. **Pull completes successfully**
3. **Auto-save prompt appears:**
   ```
   Configuration pulled successfully!
   
   Save as: pulled_tsg1570970024_20241220_153045
   
   Would you like to save this configuration?
   
   [Yes] [No]
   ```
4. **If Yes:**
   - Config saved to `~/.pa_config_lab/saved_configs/`
   - Sidebar list refreshes automatically
   - Saved as unencrypted for quick access
   - Success message shown with encryption instructions
5. **User moves to Review tab** (Tab 2)
6. **Optional: User can manually save again with custom name/encryption** (💾 Save Current Config button)

### Benefits

✅ **Backup Before Push** - Always have a copy before pushing to target  
✅ **Audit Trail** - Track when configs were pulled with timestamp  
✅ **Quick Recovery** - Easily reload pulled configs without re-pulling  
✅ **TSG Identification** - Filename includes source TSG for easy identification  
✅ **Optional** - User can decline auto-save if not needed  
✅ **Non-blocking** - If auto-save fails, workflow continues  

### UI Updates

**Tab Labels:**
- 1️⃣ Pull from SCM
- 2️⃣ Review Configuration (now has Save button)
- 3️⃣ Push to Target

**Review Tab:**
- Added container with save button at bottom
- "💾 Save Current Config" button (orange)
- Allows manual save with custom name/password

### Encryption Note

Auto-saved configs are **unencrypted** by default for:
- Quick access without password
- Easy reloading during workflow
- User can encrypt later if needed

**To encrypt an auto-saved config:**
1. Click "💾 Save Current Config" in Review tab
2. Enter custom name and password
3. Or: Export from sidebar with password, then re-import

### Error Handling

- If auto-save fails (name collision, disk full, etc.):
  - Shows warning message
  - Workflow continues normally
  - User can manually save from Review tab

- If user clicks No on auto-save prompt:
  - Config still loads into viewer
  - User can manually save later if needed

### Testing

```bash
python run_gui.py
```

1. Go to Configuration Migration
2. Pull a config from SCM (Tab 1)
3. After successful pull → Auto-save prompt appears
4. Click Yes → Config saved with TSG+date name
5. Check sidebar → New config appears in list
6. Go to Review tab → See the config
7. Optional: Click "💾 Save Current Config" for custom save

---

**Status:** ✅ Complete and tested
