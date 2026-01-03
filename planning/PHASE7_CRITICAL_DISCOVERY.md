# Phase 7 - Critical Discovery

## Issue: Bulk Query Approach Won't Work

### What We Learned

After fixing the API endpoint issues and testing, we discovered that **Prisma Access API requires folder/snippet parameters** for most configuration endpoints.

**Error from API:**
```
"Folder undefined doesn't exist. Please create it before running the command"
```

This means we **CANNOT** do a single bulk query like:
```
GET /sse/config/v1/addresses  (fetch ALL addresses)
```

Instead, we MUST specify a folder:
```
GET /sse/config/v1/addresses?folder=Mobile%20Users
```

### Impact

The original Phase 7 goal was to reduce API calls from N×M to M+1 by:
- 1 query for folders
- 1 query per type (bulk fetch all items)
- Distribute to folders based on item's folder field

**This is NOT possible** with Prisma Access API design.

### Reality

We're back to the original approach:
- 1 query for folders (works!)
- For each folder, query each type
- Result: Still N folders × M types = N×M API calls

### Options

1. **Accept the limitation** - The old orchestrator approach was correct for this API
2. **Hybrid approach** - Bulk fetch types that don't require folders (infrastructure)
3. **Caching layer** - Cache folder results to reduce calls across operations
4. **Parallel requests** - Make folder queries in parallel to improve speed

### Bugs Fixed Today

✅ Folders endpoint URL (Strata API vs SASE API)  
✅ Snippets endpoint URL  
✅ ConfigItemFactory.get_model_class() method  
✅ Test script credential loading  
✅ Error handling improvements  

### Recommendation

**Revert to folder-by-folder approach** with these improvements from Phase 5-7:
- ✅ Structured error handling
- ✅ Workflow infrastructure 
- ✅ ConfigItem objects
- ✅ Default filtering
- ✅ Progress tracking

The bulk query optimization simply isn't compatible with Prisma Access API design.

---

**Status:** Architecture lesson learned. Need to adjust approach based on API constraints.
