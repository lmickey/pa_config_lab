# Save/Load Configuration Dialogs Implementation Plan

## Overview

Enhance the configuration save/load experience with:
- Friendly naming and descriptions
- Password-based encryption
- Organized file storage in `./saved` folder
- List-based file selection for loading
- Export functionality for sharing configs

---

## 1. Save Configuration Dialog

### UI Elements
```
┌─────────────────────────────────────────────────────────────┐
│  Save Configuration                                     [X] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Configuration Name: [________________________]             │
│                      (Display name shown in GUI)            │
│                                                             │
│  Description:                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                      │   │
│  │                                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ─── Encryption ───────────────────────────────────────    │
│                                                             │
│  Password:         [________________________]               │
│  Confirm Password: [________________________]               │
│                                                             │
│  ⓘ Configuration will be encrypted and saved to:           │
│    ./saved/my-config-name_2026-01-03_001234.pac            │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                              [Cancel]  [Save Configuration] │
└─────────────────────────────────────────────────────────────┘
```

### Behavior
- **Configuration Name**: Required, used for display and filename
- **Description**: Optional, stored in config metadata
- **Password**: Required, used for AES-256 encryption
- **Confirm Password**: Must match password
- **Filename**: Auto-generated: `{sanitized_name}_{timestamp}.pac`
- **Location**: Always saved to `./saved/` folder
- **File Extension**: `.pac` (Prisma Access Configuration)

### Validation
- Name cannot be empty
- Name contains only valid filename characters
- Passwords match
- Password minimum length (8 characters)

---

## 2. Load Configuration Dialog

### UI Elements
```
┌─────────────────────────────────────────────────────────────┐
│  Load Configuration                                     [X] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Saved Configurations:                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Name              │ Date       │ Size   │ Encrypted │   │
│  ├───────────────────┼────────────┼────────┼───────────┤   │
│  │ Production Backup │ 2026-01-03 │ 245 KB │ ✓         │   │
│  │ Dev Environment   │ 2026-01-02 │ 128 KB │ ✓         │   │
│  │ Test Config       │ 2026-01-01 │ 89 KB  │ ✗         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ▼ Advanced Options                                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ [✓] Ignore default configurations                    │   │
│  │ [ ] Validate configuration after loading             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                    [Browse...]  [Cancel]  [Load]            │
└─────────────────────────────────────────────────────────────┘
```

### Password Prompt (shown after selecting encrypted file)
```
┌─────────────────────────────────────────────────────┐
│  Enter Password                                 [X] │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Configuration: Production Backup                   │
│                                                     │
│  Password: [________________________]               │
│                                                     │
│  [ ] Show password                                  │
│                                                     │
├─────────────────────────────────────────────────────┤
│                         [Cancel]  [Decrypt & Load]  │
└─────────────────────────────────────────────────────┘
```

### Behavior
- Lists all `.pac` and `.json` files from `./saved/` folder
- Shows metadata: name, date, size, encryption status
- Double-click or Load button triggers password prompt (if encrypted)
- Advanced Options collapsed by default
- "Browse..." button allows loading from other locations

### Advanced Options
- **Ignore default configurations**: Checked by default
- **Validate configuration after loading**: Optional validation

---

## 3. Export Configuration Dialog

### UI Elements
```
┌─────────────────────────────────────────────────────────────┐
│  Export Configuration                                   [X] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Export Location:                                           │
│  [/home/user/exports/my-config.pac        ] [Browse...]     │
│                                                             │
│  ─── Options ──────────────────────────────────────────    │
│                                                             │
│  [✓] Encrypt exported file                                  │
│                                                             │
│  Password:         [________________________]               │
│  Confirm Password: [________________________]               │
│  (Only required if encryption is enabled)                   │
│                                                             │
│  Format: (○) Encrypted (.pac)  ( ) Plain JSON (.json)       │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                    [Cancel]  [Export]       │
└─────────────────────────────────────────────────────────────┘
```

### Behavior
- User selects export location via file dialog
- Optional encryption with password
- Can export as `.pac` (encrypted) or `.json` (plain)
- Useful for sharing configs or backing up to external location

---

## 4. Encryption Implementation

### Technology
- **Algorithm**: AES-256-GCM (authenticated encryption)
- **Key Derivation**: PBKDF2 with SHA-256, 100,000 iterations
- **Library**: `cryptography` (already commonly used)

### File Format (.pac)
```json
{
  "format": "pac_encrypted_v1",
  "encryption": {
    "algorithm": "AES-256-GCM",
    "kdf": "PBKDF2-SHA256",
    "iterations": 100000,
    "salt": "<base64_encoded_salt>",
    "nonce": "<base64_encoded_nonce>",
    "tag": "<base64_encoded_auth_tag>"
  },
  "metadata": {
    "name": "My Configuration",
    "description": "Production backup",
    "created_at": "2026-01-03T12:34:56",
    "version": "1.0"
  },
  "data": "<base64_encoded_encrypted_data>"
}
```

### Encryption Utility Functions
```python
# config/utils/encryption.py

def encrypt_config(config_data: dict, password: str, metadata: dict) -> dict:
    """Encrypt configuration data with password."""
    
def decrypt_config(encrypted_data: dict, password: str) -> dict:
    """Decrypt configuration data with password."""
    
def is_encrypted(file_path: str) -> bool:
    """Check if a file is encrypted."""
    
def get_metadata(file_path: str) -> dict:
    """Get metadata from encrypted or plain config file."""
```

---

## 5. File Structure

### Saved Folder
```
./saved/
├── production-backup_2026-01-03_123456.pac
├── dev-environment_2026-01-02_094532.pac
├── test-config_2026-01-01_161234.json
└── .index.json  (optional: cached metadata for fast listing)
```

### Filename Convention
```
{sanitized_name}_{date}_{time}.{ext}

Examples:
- production-backup_2026-01-03_123456.pac
- my-config_2026-01-03_094532.pac
```

### Sanitization Rules
- Replace spaces with hyphens
- Remove special characters
- Convert to lowercase
- Limit length to 50 characters

---

## 6. Menu Updates

### File Menu (Updated)
```
File
├── Save Configuration...     Ctrl+S     → SaveConfigDialog
├── Load Configuration...     Ctrl+O     → LoadConfigDialog
├── ─────────────────────
├── Export Configuration...   Ctrl+E     → ExportConfigDialog
├── ─────────────────────
├── Recent Configurations     →
│   ├── Production Backup (2026-01-03)
│   ├── Dev Environment (2026-01-02)
│   └── Clear Recent
├── ─────────────────────
└── Exit                      Ctrl+Q
```

---

## 7. Implementation Order

### Phase 1: Core Infrastructure
1. Create `config/utils/encryption.py` with encrypt/decrypt functions
2. Create `./saved` folder on startup if not exists
3. Add filename generation utilities

### Phase 2: Save Dialog
4. Create `gui/dialogs/save_config_dialog.py`
5. Implement validation and encryption
6. Connect to main window menu

### Phase 3: Load Dialog
7. Create `gui/dialogs/load_config_dialog.py`
8. Create `gui/dialogs/password_dialog.py`
9. Implement file listing and metadata display
10. Connect to main window menu

### Phase 4: Export Dialog
11. Create `gui/dialogs/export_config_dialog.py`
12. Connect to main window menu

### Phase 5: Polish
13. Add error handling and user feedback
14. Update config metadata storage
15. Test all workflows

---

## 8. Dependencies

### Required Package
```
cryptography>=41.0.0
```

Add to requirements.txt if not present.

---

## 9. Security Considerations

- Passwords never stored, only used for key derivation
- Salt is randomly generated per encryption
- Authentication tag prevents tampering
- Memory cleared after use where possible
- Warn user about weak passwords

---

## 10. Error Handling

### Save Errors
- Invalid name → Show validation message
- Password mismatch → Show error, clear confirm field
- Weak password → Show warning, allow override
- Disk full → Show error with details
- Permission denied → Show error with path

### Load Errors
- Wrong password → "Incorrect password" (max 3 attempts)
- Corrupted file → "File appears corrupted"
- Missing file → Remove from list, show message
- Incompatible version → "Config version not supported"

### Export Errors
- Permission denied → Show error with path
- File exists → Prompt for overwrite
- Invalid path → Show validation message
