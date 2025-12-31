# Filtering Issue Analysis

**Issue:** When selecting 1 address object from Mobile Users folder, ALL address objects from that folder show in the push preview.

---

## Data Flow

### Step 1: User Selection (Component Selection Dialog)
User selects:
- 1 address object: "VPN-Users" from Mobile Users folder

### Step 2: Collection (`get_selected_items()`)
Code at lines 468-475 collects ONLY checked items:
```python
if obj_item.checkState(0) == Qt.CheckState.Checked:
    selected_objects[obj_type].append(obj_data.get('data'))
```

Result:
```python
selected_items = {
    'folders': [{
        'name': 'Mobile Users',
        'objects': {
            'address_objects': [
                {'name': 'VPN-Users', ...}  # Only 1 object!
            ]
        }
    }]
}
```

### Step 3: Fetching (ConfigFetchWorker)
Code fetches ALL address objects from Mobile Users:
```python
all_addresses = api_client.get_all_addresses(folder='Mobile Users')
# Returns 500+ objects

# Stores ALL of them
for obj in all_addresses:
    dest_config['objects']['address_objects'][obj['name']] = obj
```

Result:
```python
dest_config = {
    'objects': {
        'address_objects': {
            'VPN-Users': {...},
            'zoom-8': {...},
            'Local Users': {...},
            ... 500+ objects  # ALL objects stored!
        }
    }
}
```

### Step 4: Analysis (`_analyze_and_populate()`)
Code at lines 671-681:
```python
folder_objects = folder.get('objects', {})  # {'address_objects': [{'name': 'VPN-Users'}]}
for obj_type, obj_list in folder_objects.items():
    for obj in obj_list:  # Iterates ONLY selected: ['VPN-Users']
        obj_name = obj.get('name')  # 'VPN-Users'
        if obj_name in dest_objects:  # Checks in ALL 500+ objects
            conflicts.append(...)
```

**This part is CORRECT** - it only analyzes the selected items!

---

## So What's the Problem?

The analysis code is correct - it only iterates through selected items.

**Hypothesis:** The issue might be in how the tree is being populated in the UI, OR there's a different code path that's adding items.

Let me check the tree population code...

Actually, looking at the user's report: "all created items are showing up as being validated even though i didn't select them"

This suggests that when they look at the push preview dialog, they see items they didn't select.

**Possible causes:**
1. The tree widget is showing ALL items from dest_config, not just the ones being analyzed
2. There's a bug in how conflicts/new_items lists are being populated
3. The folder iteration is somehow including items that weren't selected

---

## Next Steps

1. Check how the conflicts/new_items trees are populated
2. Verify that we're only adding items from the conflicts/new_items lists
3. Add debug output to show exactly what's being added to the trees

