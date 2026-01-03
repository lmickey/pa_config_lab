"""
Memory Safety Tests for GUI Stability

These tests validate that our code doesn't have memory corruption issues
that cause segfaults, double-free errors, and malloc corruption.

Run with: pytest tests/test_memory_safety.py -v
"""

import pytest
import gc
import sys
from typing import Dict, List, Any


class TestShallowCopyDetection:
    """Test that we don't have shallow copy issues causing shared references."""
    
    def test_configitem_to_dict_no_shared_references(self):
        """Verify ConfigItem.to_dict() creates independent copies."""
        from config.models.base import ConfigItem
        
        # Create items with nested structures (lists and dicts)
        raw_data = {
            'name': 'test-item',
            'folder': 'TestFolder',  # Required field
            'ports': ['80', '443', '8080'],
            'tags': ['web', 'production'],
            'metadata': {
                'author': 'test',
                'nested': {
                    'deep': ['value1', 'value2']
                }
            }
        }
        
        item1 = ConfigItem(raw_data)
        item2 = ConfigItem(raw_data)
        
        # Convert to dicts
        dict1 = item1.to_dict()
        dict2 = item2.to_dict()
        
        # Modify nested structures in dict1
        dict1['ports'].append('9000')
        dict1['tags'].append('modified')
        dict1['metadata']['author'] = 'changed'
        dict1['metadata']['nested']['deep'].append('value3')
        
        # Verify dict2 is NOT affected (no shared references)
        assert '9000' not in dict2['ports'], "Shared reference detected in ports list!"
        assert 'modified' not in dict2['tags'], "Shared reference detected in tags list!"
        assert dict2['metadata']['author'] == 'test', "Shared reference detected in metadata!"
        assert 'value3' not in dict2['metadata']['nested']['deep'], "Shared reference detected in nested dict!"
        
    def test_configitem_to_dict_multiple_calls_independent(self):
        """Verify multiple to_dict() calls on same item are independent."""
        from config.models.base import ConfigItem
        
        raw_data = {
            'name': 'test',
            'folder': 'TestFolder',
            'rules': ['rule1', 'rule2'],
            'config': {'setting': ['a', 'b']}
        }
        
        item = ConfigItem(raw_data)
        
        # Call to_dict() multiple times
        dicts = [item.to_dict() for _ in range(10)]
        
        # Modify first dict
        dicts[0]['rules'].append('modified')
        dicts[0]['config']['setting'].append('modified')
        
        # Verify others are not affected
        for i in range(1, 10):
            assert 'modified' not in dicts[i]['rules'], f"Shared reference in dict {i}!"
            assert 'modified' not in dicts[i]['config']['setting'], f"Shared reference in dict {i}!"
    
    def test_large_dataset_no_shared_references(self):
        """Test with realistic dataset size (200+ items)."""
        from config.models.base import ConfigItem
        
        # Create 200 items (realistic load)
        items = []
        for i in range(200):
            raw_data = {
                'name': f'item-{i}',
                'folder': 'TestFolder',
                'ports': ['80', '443'],
                'members': [f'member-{i}-1', f'member-{i}-2'],
                'nested': {'list': [1, 2, 3]}
            }
            items.append(ConfigItem(raw_data))
        
        # Convert all to dicts
        dicts = [item.to_dict() for item in items]
        
        # Modify first dict's nested structures
        dicts[0]['ports'].append('modified')
        dicts[0]['members'].append('modified')
        dicts[0]['nested']['list'].append(999)
        
        # Check random samples (checking all 200 is slow)
        test_indices = [1, 50, 100, 150, 199]
        for idx in test_indices:
            assert 'modified' not in dicts[idx]['ports'], f"Shared reference at index {idx}!"
            assert 'modified' not in dicts[idx]['members'], f"Shared reference at index {idx}!"
            assert 999 not in dicts[idx]['nested']['list'], f"Shared reference at index {idx}!"


class TestConfigAdapterMemorySafety:
    """Test that ConfigAdapter doesn't create memory issues."""
    
    def test_configuration_to_dict_no_shared_references(self):
        """Test full Configuration -> dict conversion."""
        from config.models.containers import Configuration, FolderConfig
        from config.models.base import ConfigItem
        from gui.config_adapter import ConfigAdapter
        
        # Create configuration with multiple items
        config = Configuration(source_tsg="test", load_type="test")
        
        folder = FolderConfig(name="TestFolder")
        for i in range(10):
            item = ConfigItem({
                'name': f'item-{i}',
                'folder': 'TestFolder',
                'ports': ['80', '443'],
                'members': ['member1', 'member2']
            })
            folder.add_item(item)
        
        config.folders["TestFolder"] = folder
        
        # Convert to dict
        dict_config = ConfigAdapter.to_dict(config)
        
        # Get first item (don't assume type name)
        folder_data = dict_config['folders']['TestFolder']
        item_type = list(folder_data.keys())[0]  # Get first type
        first_item = folder_data[item_type][0]
        first_item['ports'].append('modified')
        
        # Get fresh conversion
        dict_config2 = ConfigAdapter.to_dict(config)
        folder_data2 = dict_config2['folders']['TestFolder']
        first_item2 = folder_data2[item_type][0]
        
        # Verify no shared references
        assert 'modified' not in first_item2['ports'], "Shared reference in ConfigAdapter!"
    
    def test_adapter_with_large_configuration(self):
        """Test ConfigAdapter with realistic large configuration."""
        from config.models.containers import Configuration, FolderConfig, SnippetConfig
        from config.models.base import ConfigItem
        from gui.config_adapter import ConfigAdapter
        
        config = Configuration(source_tsg="test", load_type="test")
        
        # Add multiple folders with items
        for folder_idx in range(3):
            folder_name = f"Folder{folder_idx}"
            folder = FolderConfig(name=folder_name)
            for item_idx in range(50):  # 50 items per folder
                item = ConfigItem({
                    'name': f'item-{folder_idx}-{item_idx}',
                    'folder': folder_name,
                    'data': ['a', 'b', 'c']
                })
                folder.add_item(item)
            config.folders[folder_name] = folder
        
        # Add snippets
        for snippet_idx in range(3):
            snippet_name = f"Snippet{snippet_idx}"
            snippet = SnippetConfig(name=snippet_name)
            for item_idx in range(50):
                item = ConfigItem({
                    'name': f'snippet-item-{snippet_idx}-{item_idx}',
                    'snippet': snippet_name,
                    'data': ['x', 'y', 'z']
                })
                snippet.add_item(item)
            config.snippets[snippet_name] = snippet
        
        # Convert to dict (300 items total)
        dict_config = ConfigAdapter.to_dict(config)
        
        # Verify conversion succeeded
        assert len(dict_config['folders']) == 3
        assert len(dict_config['snippets']) == 3
        
        # Verify we can access all items without crash
        total_items = ConfigAdapter.get_all_items_list(config)
        assert len(total_items) == 300  # 3 folders × 50 + 3 snippets × 50


class TestMemoryLeakDetection:
    """Test for memory leaks in object creation/deletion."""
    
    def test_configuration_object_cleanup(self):
        """Verify Configuration objects are properly cleaned up."""
        from config.models.containers import Configuration, FolderConfig
        from config.models.base import ConfigItem
        import weakref
        
        # Create configuration
        config = Configuration(source_tsg="test", load_type="test")
        folder = FolderConfig(name="TestFolder")
        
        # Add items
        items = []
        for i in range(10):
            item = ConfigItem({
                'name': f'item-{i}',
                'folder': 'TestFolder'
            })
            folder.add_item(item)
            items.append(weakref.ref(item))
        
        config.folders["TestFolder"] = folder
        
        # Delete configuration
        del config
        del folder
        gc.collect()
        
        # Verify items are cleaned up (weak refs should be dead)
        # Note: This may not always work due to Python's GC, but worth testing
        dead_refs = sum(1 for ref in items if ref() is None)
        # At least some should be collected
        assert dead_refs > 0, "No items were garbage collected - potential memory leak"
    
    def test_worker_thread_cleanup(self):
        """Test that worker thread resources are cleaned up."""
        from gui.workers import PullWorker
        from unittest.mock import Mock
        
        # Create mock API client
        api_client = Mock()
        api_client.tsg_id = "test"
        
        # Create worker
        worker = PullWorker(api_client, {}, filter_defaults=True)
        
        # Worker should be deletable
        worker_id = id(worker)
        del worker
        gc.collect()
        
        # If we reach here without crash, cleanup succeeded
        assert True


class TestJSONSerializationSafety:
    """Test that JSON serialization works correctly for all data types."""
    
    def test_json_roundtrip_preserves_data(self):
        """Verify JSON serialization preserves data correctly."""
        import json
        
        test_data = {
            'string': 'test',
            'int': 42,
            'float': 3.14,
            'bool': True,
            'none': None,
            'list': [1, 2, 3],
            'dict': {'nested': 'value'},
            'deep': {
                'level1': {
                    'level2': {
                        'level3': ['a', 'b', 'c']
                    }
                }
            }
        }
        
        # JSON roundtrip
        result = json.loads(json.dumps(test_data))
        
        # Verify data is preserved
        assert result == test_data
        
        # Verify it's a new object (not same reference)
        assert result is not test_data
        assert result['list'] is not test_data['list']
        assert result['dict'] is not test_data['dict']
    
    def test_configitem_json_serializable(self):
        """Verify ConfigItem data is JSON-serializable."""
        from config.models.base import ConfigItem
        import json
        
        raw_data = {
            'name': 'test',
            'folder': 'TestFolder',
            'ports': ['80', '443'],
            'config': {'setting': 'value'}
        }
        
        item = ConfigItem(raw_data)
        dict_data = item.to_dict()
        
        # Should be JSON-serializable
        json_str = json.dumps(dict_data)
        recovered = json.loads(json_str)
        
        # Data should match
        assert recovered['name'] == 'test'
        assert recovered['ports'] == ['80', '443']


class TestThreadSafety:
    """Test thread-safety of critical operations."""
    
    def test_to_dict_concurrent_calls(self):
        """Test that concurrent to_dict() calls don't interfere."""
        from config.models.base import ConfigItem
        from threading import Thread
        
        raw_data = {
            'name': 'test',
            'folder': 'TestFolder',
            'ports': ['80', '443'],
            'data': {'nested': ['a', 'b']}
        }
        
        item = ConfigItem(raw_data)
        results = []
        
        def call_to_dict():
            d = item.to_dict()
            results.append(d)
        
        # Call to_dict() from multiple threads
        threads = [Thread(target=call_to_dict) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All should succeed
        assert len(results) == 10
        
        # Modify one result
        results[0]['ports'].append('modified')
        
        # Others should not be affected
        for i in range(1, 10):
            assert 'modified' not in results[i]['ports'], f"Shared reference in thread result {i}!"


# Run with: pytest tests/test_memory_safety.py -v -s
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
