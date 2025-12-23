# Migration Enhancement Summary

## Problem Statement
Current migration workflow can't:
- ❌ Selectively push parts of a config (all or nothing)
- ❌ Combine parts from different configs
- ❌ Migrate from Tenant A to Tenant B (uses same connection)
- ❌ Save tenant credentials for reuse

## Proposed Solution

### 3 Major Enhancements

#### 1. **Tenant Management System**
- Save list of tenants (TSG, client_id, name, description)
- **Never store client secrets** (security)
- Select from dropdown when connecting
- Reusable across workflows (Pull, Push, POV)

#### 2. **Dual Connection**
- Source tenant for Pull
- Destination tenant for Push
- Independent connections
- Clear status for both

#### 3. **Selective Push**
- Load any config
- Select specific folders to push
- Select components per folder (Objects, Profiles, Rules)
- Select specific snippets
- Push only what's selected

---

## User Workflow

### Before (Current)
1. Connect to Tenant A
2. Pull entire config
3. Push entire config back to Tenant A
4. ❌ Can't select parts
5. ❌ Can't push to different tenant

### After (Enhanced)
1. Connect to "Production Tenant" (from saved list)
2. Pull entire config
3. Load config in Push tab
4. **Select** specific folders/components to push
5. Connect to "Dev Tenant" (different tenant)
6. Push selected items to Dev Tenant
7. Later: Load different config, select different parts, push to same tenant

---

## Key Features

### Tenant Management
```
┌─────────────────────────────┐
│ Saved Tenants               │
├─────────────────────────────┤
│ • Production (TSG: 123...)  │
│ • Dev (TSG: 987...)         │
│ • Customer POC (TSG: 456...)│
│                             │
│ [Add New Tenant]            │
└─────────────────────────────┘
```

### Connection Flow
```
Pull Tab:
  Source: ✓ Connected to "Production"
  
Push Tab:
  Destination: [Connect to Tenant ▼]
               ├─ Dev
               ├─ Customer POC
               └─ [Manual Entry...]
```

### Selective Push
```
Select Items to Push:
  ☑ Mobile Users
    ☑ Objects (145)
    ☑ Profiles (12)
    ☑ Rules (45)
  ☑ Remote Networks
    ☑ Objects (89)
    ☐ Profiles
    ☑ Rules (12)
  ☐ Branch Offices (skip)
  
  ☑ custom-snippet-1
  ☐ best-practice-snippet
  
Summary: 2 folders, 234 objects, 57 rules, 1 snippet
```

---

## Implementation Timeline

### Week 1: Tenant Management
- Days 1-2: Backend (storage, encryption, CRUD)
- Day 3: UI (dialog, add/edit/delete)

### Week 2: Multi-Tenant Connection
- Day 4: Dual connection support
- Day 5: Connection flow and status

### Week 3: Selective Push
- Days 6-7: Selection dialog
- Day 8: Push orchestration

### Week 4: Testing
- Days 9-10: Integration testing, docs

**Total: ~10 days**

---

## Security

### Stored (Encrypted)
- ✅ TSG ID
- ✅ Client ID
- ✅ Tenant name
- ✅ Description

### NOT Stored
- ❌ Client Secret
- ❌ Tokens
- ❌ Any passwords

User enters secret on each connect.

---

## Benefits

### For Users
- ✅ No re-entering credentials
- ✅ Easy tenant switching
- ✅ Selective migrations
- ✅ Mix and match configs
- ✅ True Tenant A → Tenant B migration

### For Future
- ✅ Reusable across workflows (POV, etc.)
- ✅ Foundation for advanced features
- ✅ Tenant comparison
- ✅ Multi-config merging

---

## No Breaking Changes
- ✅ All existing functionality preserved
- ✅ Additive only
- ✅ POV workflow untouched (for now)
- ✅ Can still do simple pull/push

---

## Next Steps

1. **Review this plan**
2. **Approve approach**
3. **Start Week 1: Tenant Management**
4. **Test with your tenants**

Ready to begin implementation?
