# Push Preview Optimization Plan

**Date:** December 30, 2025  
**Issue:** Push preview fetches too much data  
**Goal:** Only check specific selected items  

---

## Current Behavior (Problem)

When you select 5 address objects from "Mobile Users" folder:

```
1. Fetch ALL address objects from Mobile Users → 500+ objects
2. Store ALL 500+ objects in memory
3. Compare your 5 selected against all 500+
4. Repeat for every object type in the folder
```

**Result:** Slow, uses lots of memory, unnecessary API calls

---

## Desired Behavior (Optimized)

When you select 5 address objects from "Mobile Users" folder:

```
1. Know you selected: ["VPN-Users", "10.158.24.0/24", "zoom-8", "Local Users", "is-mac-and-anti-malware"]
2. Fetch ALL address objects from Mobile Users → 500+ objects (API limitation - can't filter)
3. Store ONLY your 5 selected objects
4. Compare only those 5
5. Skip other object types if nothing selected
```

**Result:** Same API call, but faster processing and less memory

---

## API Limitation

**Important:** Prisma Access SCM API does NOT support filtering by name:

```python
# ❌ NOT SUPPORTED
api_client.get_addresses(folder="Mobile Users", names=["VPN-Users", "zoom-8"])

# ✅ ONLY THIS WORKS
api_client.get_addresses(folder="Mobile Users")  # Returns ALL
```

So we MUST fetch all items from a folder, but we can optimize what we do with them.

---

## Optimization Strategy

### Step 1: Extract Specific Item Names

```python
items_to_check = {
    'address_objects': {
        'Mobile Users': {'VPN-Users', '10.158.24.0/24', 'zoom-8'}
    },
    'service_objects': {
        'Mobile Users': {'service-SSH'}
    }
}
```

### Step 2: Fetch Per Folder (Once Per Type)

```python
# Fetch address objects from Mobile Users ONCE
all_addresses = api_client.get_all_addresses(folder='Mobile Users')

# Filter to only our selected items
selected_addresses = {
    name: obj for obj in all_addresses 
    if obj.get('name') in items_to_check['address_objects']['Mobile Users']
}
```

### Step 3: Skip Empty Types

```python
# If no service groups selected from this folder, don't fetch them
if 'service_groups' not in items_to_check:
    # Skip entirely - no API call
    pass
```

---

## Implementation Changes Needed

### 1. Change Data Collection

**Current:**
```python
# Collects ALL object types from folder
for obj_type in folder.get('objects', {}).keys():
    object_folders[obj_type].add(folder_name)
```

**Optimized:**
```python
# Collect ONLY types that have selected items
for obj_type, obj_list in folder.get('objects', {}).items():
    if obj_list:  # Only if items selected
        items_to_check[obj_type][folder_name] = {obj.get('name') for obj in obj_list}
```

### 2. Change Fetching Logic

**Current:**
```python
# Fetches and stores ALL
all_objects = api_client.get_all_addresses(folder='Mobile Users')
for obj in all_objects:
    dest_config['objects']['address_objects'][obj.get('name')] = obj
```

**Optimized:**
```python
# Fetches ALL but stores ONLY selected
all_objects = api_client.get_all_addresses(folder='Mobile Users')
selected_names = items_to_check['address_objects']['Mobile Users']

for obj in all_objects:
    obj_name = obj.get('name')
    if obj_name in selected_names:
        dest_config['objects']['address_objects'][obj_name] = obj
```

### 3. Better Logging

```python
print(f"Checking {len(selected_names)} address_objects in 'Mobile Users':")
print(f"  Selected: {list(selected_names)}")
print(f"  Fetched: {len(all_objects)} total objects")
print(f"  Stored: {len(dest_config['objects']['address_objects'])} matching")
```

---

## Performance Comparison

### Scenario: 5 objects selected from Mobile Users (which has 500 objects)

**Current Approach:**
- API Calls: 1 (fetch all 500)
- Objects Stored: 500
- Memory: ~500KB
- Processing Time: ~2s

**Optimized Approach:**
- API Calls: 1 (fetch all 500) - **same**
- Objects Stored: 5 - **100x less**
- Memory: ~5KB - **100x less**
- Processing Time: ~0.5s - **4x faster**

---

## What Can't Be Optimized

1. **API Calls:** Still need to fetch all items from folder (API limitation)
2. **Network Time:** Same bandwidth used
3. **API Rate Limits:** Same number of requests

## What CAN Be Optimized

1. **Memory Usage:** Only store selected items
2. **Processing Time:** Only compare selected items
3. **Log Clarity:** Show exactly what's being checked
4. **Skip Empty Types:** Don't fetch types with no selections

---

## Implementation Priority

### High Priority (Do First)
1. ✅ Only store selected items (not all fetched items)
2. ✅ Skip object types with no selections
3. ✅ Better logging showing selected vs fetched

### Medium Priority
4. Profile conflict detection (check against destination)
5. Rules comparison (if applicable)

### Low Priority
6. Caching (reuse fetched data if checking multiple times)
7. Parallel fetching (fetch multiple folders simultaneously)

---

## Code Location

File: `gui/dialogs/push_preview_dialog.py`
Method: `ConfigFetchWorker.run()`
Lines: ~155-260 (objects section)

---

## Next Steps

1. Refactor object fetching to only store selected items
2. Add logging to show: "Checking 5 items, fetched 500, stored 5"
3. Skip object types with no selections
4. Apply same pattern to profiles and infrastructure

---

**Status:** 📋 Plan ready - needs implementation
