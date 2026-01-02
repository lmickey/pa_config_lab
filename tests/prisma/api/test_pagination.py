"""
Tests for prisma.api.pagination module.

Tests the PaginationHelper class for API pagination handling.
"""

import pytest
from prisma.api.pagination import PaginationHelper


class TestPaginationHelper:
    """Tests for PaginationHelper class"""
    
    def test_default_limit(self):
        """Test default limit is 200"""
        assert PaginationHelper.DEFAULT_LIMIT == 200
        assert PaginationHelper.MAX_LIMIT == 200
    
    def test_get_all_items_single_page(self):
        """Test fetching all items when results fit in one page"""
        # Mock fetch function that returns all items in one page
        def fetch_page(limit, offset):
            return {
                'data': [{'id': i, 'name': f'item-{i}'} for i in range(50)],
                'total': 50,
                'limit': limit,
                'offset': offset
            }
        
        items = PaginationHelper.get_all_items(fetch_page)
        
        assert len(items) == 50
        assert items[0]['id'] == 0
        assert items[49]['id'] == 49
    
    def test_get_all_items_multiple_pages(self):
        """Test fetching all items across multiple pages"""
        # Mock fetch function with pagination
        all_data = [{'id': i, 'name': f'item-{i}'} for i in range(250)]
        
        def fetch_page(limit, offset):
            end = min(offset + limit, len(all_data))
            return {
                'data': all_data[offset:end],
                'total': len(all_data),
                'limit': limit,
                'offset': offset
            }
        
        items = PaginationHelper.get_all_items(fetch_page, limit=100)
        
        assert len(items) == 250
        assert items[0]['id'] == 0
        assert items[249]['id'] == 249
    
    def test_get_all_items_list_response(self):
        """Test handling list responses (not dict)"""
        def fetch_page(limit, offset):
            return [{'id': i} for i in range(10)]
        
        items = PaginationHelper.get_all_items(fetch_page)
        
        assert len(items) == 10
    
    def test_get_all_items_empty_response(self):
        """Test handling empty responses"""
        def fetch_page(limit, offset):
            return {'data': [], 'total': 0}
        
        items = PaginationHelper.get_all_items(fetch_page)
        
        assert len(items) == 0
    
    def test_get_all_items_last_page_partial(self):
        """Test when last page has fewer items than limit"""
        all_data = [{'id': i} for i in range(225)]
        
        def fetch_page(limit, offset):
            end = min(offset + limit, len(all_data))
            return {
                'data': all_data[offset:end],
                'total': len(all_data),
                'limit': limit,
                'offset': offset
            }
        
        items = PaginationHelper.get_all_items(fetch_page, limit=100)
        
        assert len(items) == 225
    
    def test_get_all_items_exceeds_max_limit(self):
        """Test that limits exceeding MAX_LIMIT are capped"""
        def fetch_page(limit, offset):
            # Verify limit was capped to MAX_LIMIT
            assert limit <= PaginationHelper.MAX_LIMIT
            return {
                'data': [{'id': i} for i in range(limit)],
                'total': 300,
                'limit': limit,
                'offset': offset
            }
        
        items = PaginationHelper.get_all_items(fetch_page, limit=300)
        
        # Should use MAX_LIMIT (200) instead of 300
        assert len(items) >= 200
    
    def test_get_items_with_callback(self):
        """Test pagination with progress callback"""
        all_data = [{'id': i} for i in range(150)]
        callback_calls = []
        
        def fetch_page(limit, offset):
            end = min(offset + limit, len(all_data))
            return {
                'data': all_data[offset:end],
                'total': len(all_data),
                'limit': limit,
                'offset': offset
            }
        
        def progress_callback(items, current, total):
            callback_calls.append({'current': current, 'total': total})
        
        items = PaginationHelper.get_items_with_callback(
            fetch_page,
            progress_callback,
            limit=50
        )
        
        assert len(items) == 150
        assert len(callback_calls) == 3  # Called for each page
        assert callback_calls[-1]['current'] == 150
        assert callback_calls[-1]['total'] == 150
    
    def test_get_items_with_callback_error_handling(self):
        """Test that callback errors don't stop pagination"""
        def fetch_page(limit, offset):
            return {
                'data': [{'id': i} for i in range(10)],
                'total': 10,
                'limit': limit,
                'offset': offset
            }
        
        def bad_callback(items, current, total):
            raise ValueError("Callback error")
        
        # Should complete despite callback errors
        items = PaginationHelper.get_items_with_callback(
            fetch_page,
            bad_callback,
            limit=10
        )
        
        assert len(items) == 10
    
    def test_calculate_pages(self):
        """Test page calculation"""
        assert PaginationHelper.calculate_pages(0, 100) == 0
        assert PaginationHelper.calculate_pages(100, 100) == 1
        assert PaginationHelper.calculate_pages(150, 100) == 2
        assert PaginationHelper.calculate_pages(200, 100) == 2
        assert PaginationHelper.calculate_pages(201, 100) == 3
        assert PaginationHelper.calculate_pages(1000, 200) == 5
    
    def test_calculate_pages_edge_cases(self):
        """Test page calculation edge cases"""
        assert PaginationHelper.calculate_pages(0, 0) == 0
        assert PaginationHelper.calculate_pages(100, 0) == 0
        assert PaginationHelper.calculate_pages(1, 1) == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
