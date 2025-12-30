# Selective Push Orchestrator - Implementation Plan

**Date:** 2024-12-30  
**Status:** 🚀 IN PROGRESS

---

## Overview

Implement the core push functionality that takes selected configuration items and pushes them to a destination Prisma Access tenant via the SCM API.

---

## Goals

1. **Push selected items** to destination tenant
2. **Handle conflict resolution** (SKIP/OVERWRITE/RENAME)
3. **Track success/failures** for each item
4. **Provide detailed results** for user feedback
5. **Handle errors gracefully** without failing entire push

---

## Architecture

### Class: `SelectivePushOrchestrator`

**Location:** `prisma/push/selective_push_orchestrator.py`

**Responsibilities:**
- Accept selected items and destination client
- Apply conflict resolution strategy
- Push items in correct order (dependencies first)
- Track results per item
- Return comprehensive push report

---

## Push Order (Dependencies)

Items must be pushed in this order to satisfy dependencies:

1. **Folders** (if creating new folders)
2. **Objects** (addresses, services, etc.)
3. **Profiles** (security profiles, auth profiles, etc.)
4. **HIP Objects & Profiles**
5. **Infrastructure** (crypto profiles, gateways, tunnels, etc.)
6. **Security Rules** (reference objects/profiles)
7. **Snippets** (reference everything)

---

## Conflict Resolution Strategies

### SKIP
- Check if item exists in destination
- If exists, skip (don't push)
- Track as "skipped"

### OVERWRITE
- Check if item exists in destination
- If exists, update via PUT/PATCH
- If doesn't exist, create via POST
- Track as "updated" or "created"

### RENAME
- Check if item exists in destination
- If exists, append suffix (e.g., "_imported", "_1")
- Create with new name via POST
- Track as "created (renamed)"

---

## API Methods Needed

### Folders
- `POST /config/security/v1/folders` - Create folder
- `PUT /config/security/v1/folders/{id}` - Update folder

### Objects
- `POST /config/objects/v1/addresses` - Create address
- `PUT /config/objects/v1/addresses/{id}` - Update address
- (Similar for all object types)

### Security Rules
- `POST /config/security/v1/security-rules` - Create rule
- `PUT /config/security/v1/security-rules/{id}` - Update rule

### Infrastructure
- `POST /config/network/v1/remote-networks` - Create remote network
- `PUT /config/network/v1/remote-networks/{id}` - Update remote network
- (Similar for all infrastructure types)

---

## Data Structures

### Input: Selected Items

```python
selected_items = {
    'folders': [
        {
            'name': 'Mobile Users',
            'folder': 'Mobile Users',
            'objects': {
                'address_objects': [
                    {'name': 'VPN-Users', 'folder': 'Mobile Users', ...}
                ]
            },
            'security_rules': [
                {'name': 'Allow-VPN', 'folder': 'Mobile Users', ...}
            ]
        }
    ],
    'snippets': [
        {'name': 'Global-Security-Snippet', ...}
    ],
    'infrastructure': {
        'remote_networks': [
            {'name': 'Branch-Office-1', 'folder': 'Remote Networks', ...}
        ]
    }
}
```

### Output: Push Results

```python
results = {
    'summary': {
        'total': 50,
        'created': 30,
        'updated': 10,
        'skipped': 8,
        'failed': 2,
        'renamed': 0
    },
    'details': [
        {
            'type': 'address_object',
            'name': 'VPN-Users',
            'folder': 'Mobile Users',
            'action': 'created',
            'status': 'success',
            'message': 'Created successfully'
        },
        {
            'type': 'security_rule',
            'name': 'Allow-VPN',
            'folder': 'Mobile Users',
            'action': 'skipped',
            'status': 'success',
            'message': 'Already exists, skipped per conflict resolution'
        },
        {
            'type': 'remote_network',
            'name': 'Branch-Office-1',
            'folder': 'Remote Networks',
            'action': 'created',
            'status': 'failed',
            'message': 'API Error: Invalid BGP configuration',
            'error': {...}
        }
    ],
    'errors': [
        {
            'type': 'remote_network',
            'name': 'Branch-Office-1',
            'error': 'API Error: Invalid BGP configuration'
        }
    ]
}
```

---

## Implementation Steps

### Phase 1: Basic Structure ✅
1. Create `SelectivePushOrchestrator` class
2. Add `__init__` method (accept api_client, conflict_resolution)
3. Add `push_configuration` method (main entry point)
4. Add result tracking structures

### Phase 2: Folder Pushing
1. Implement `_push_folders` method
2. Handle folder creation
3. Handle conflict resolution for folders
4. Track results

### Phase 3: Object Pushing
1. Implement `_push_objects` method
2. Iterate through object types
3. Handle conflict resolution
4. Track results per object

### Phase 4: Infrastructure Pushing
1. Implement `_push_infrastructure` method
2. Handle all infrastructure types
3. Handle conflict resolution
4. Track results

### Phase 5: Rules & Snippets
1. Implement `_push_security_rules` method
2. Implement `_push_snippets` method
3. Handle conflict resolution
4. Track results

### Phase 6: Error Handling
1. Add try/except for each item
2. Continue on error (don't fail entire push)
3. Collect error details
4. Return comprehensive error report

---

## API Client Methods Needed

We'll need to add POST/PUT methods to `api_client.py`:

### Folders
- `create_folder(folder_data)` - POST
- `update_folder(folder_id, folder_data)` - PUT

### Objects
- `create_address(address_data, folder)` - POST
- `update_address(address_id, address_data)` - PUT
- (Similar for all object types)

### Security Rules
- `create_security_rule(rule_data, folder)` - POST
- `update_security_rule(rule_id, rule_data)` - PUT

### Infrastructure
- `create_remote_network(network_data, folder)` - POST
- `update_remote_network(network_id, network_data)` - PUT
- (Similar for all infrastructure types)

---

## Progress Tracking

The orchestrator will emit progress signals:

```python
# Progress callback signature
def progress_callback(message: str, current: int, total: int):
    pass

# Example usage
progress_callback("Pushing address objects...", 5, 50)
progress_callback("Pushing security rules...", 25, 50)
```

---

## Testing Strategy

### Unit Tests
- Test each push method independently
- Mock API client responses
- Test conflict resolution logic
- Test error handling

### Integration Tests
- Test with real API (test tenant)
- Test full push flow
- Test all conflict resolution modes
- Test error scenarios

---

## Next Actions

1. Create `prisma/push/` directory
2. Create `selective_push_orchestrator.py`
3. Implement basic structure
4. Add folder pushing
5. Add object pushing
6. Add infrastructure pushing
7. Add rules/snippets pushing
8. Add error handling
9. Test with real API

---

**Ready to start coding!** 🚀

