"""
Pagination utilities for Prisma Access SCM API.

Handles pagination logic for API requests that return large result sets.
"""

from typing import Dict, Any, List, Callable, Optional
import logging

logger = logging.getLogger(__name__)


class PaginationHelper:
    """
    Helper class for handling paginated API responses.
    
    The Prisma Access API uses limit/offset pagination with a max limit of 200.
    """
    
    DEFAULT_LIMIT = 200
    MAX_LIMIT = 200
    
    @staticmethod
    def get_all_items(
        fetch_function: Callable[[int, int], Dict[str, Any]],
        limit: int = DEFAULT_LIMIT
    ) -> List[Dict[str, Any]]:
        """
        Fetch all items from a paginated endpoint.
        
        Args:
            fetch_function: Function that takes (limit, offset) and returns API response
            limit: Number of items per page (default: 200, max: 200)
            
        Returns:
            List of all items from all pages
            
        Example:
            >>> def fetch_page(limit, offset):
            ...     return client._make_request("GET", f"/endpoint?limit={limit}&offset={offset}")
            >>> all_items = PaginationHelper.get_all_items(fetch_page)
        """
        if limit > PaginationHelper.MAX_LIMIT:
            logger.warning(f"Limit {limit} exceeds max {PaginationHelper.MAX_LIMIT}, using max")
            limit = PaginationHelper.MAX_LIMIT
        
        all_items = []
        offset = 0
        total = None
        
        while True:
            try:
                response = fetch_function(limit, offset)
                
                # Extract items from response
                if isinstance(response, dict):
                    items = response.get('data', [])
                    total = response.get('total', 0)
                elif isinstance(response, list):
                    items = response
                    total = len(items)
                else:
                    logger.error(f"Unexpected response type: {type(response)}")
                    break
                
                if not items:
                    break
                
                all_items.extend(items)
                logger.debug(f"Fetched {len(items)} items (offset={offset}, total={total})")
                
                # Check if we've fetched all items
                if total and len(all_items) >= total:
                    break
                
                # Check if we got fewer items than requested (last page)
                if len(items) < limit:
                    break
                
                offset += len(items)
                
            except Exception as e:
                logger.error(f"Error fetching page at offset {offset}: {e}")
                break
        
        logger.info(f"Fetched total of {len(all_items)} items across {offset // limit + 1} pages")
        return all_items
    
    @staticmethod
    def get_items_with_callback(
        fetch_function: Callable[[int, int], Dict[str, Any]],
        callback: Callable[[List[Dict[str, Any]], int, int], None],
        limit: int = DEFAULT_LIMIT
    ) -> List[Dict[str, Any]]:
        """
        Fetch all items with a callback for each page.
        
        Useful for progress tracking or processing items as they're fetched.
        
        Args:
            fetch_function: Function that takes (limit, offset) and returns API response
            callback: Function called after each page: callback(items, current_count, total)
            limit: Number of items per page
            
        Returns:
            List of all items from all pages
            
        Example:
            >>> def progress_callback(items, current, total):
            ...     print(f"Fetched {current}/{total} items")
            >>> all_items = PaginationHelper.get_items_with_callback(fetch_page, progress_callback)
        """
        if limit > PaginationHelper.MAX_LIMIT:
            limit = PaginationHelper.MAX_LIMIT
        
        all_items = []
        offset = 0
        total = None
        
        while True:
            try:
                response = fetch_function(limit, offset)
                
                # Extract items from response
                if isinstance(response, dict):
                    items = response.get('data', [])
                    total = response.get('total', 0)
                elif isinstance(response, list):
                    items = response
                    total = len(items)
                else:
                    break
                
                if not items:
                    break
                
                all_items.extend(items)
                
                # Call progress callback
                if callback:
                    try:
                        callback(items, len(all_items), total or len(all_items))
                    except Exception as e:
                        logger.warning(f"Error in progress callback: {e}")
                
                # Check if done
                if total and len(all_items) >= total:
                    break
                
                if len(items) < limit:
                    break
                
                offset += len(items)
                
            except Exception as e:
                logger.error(f"Error fetching page at offset {offset}: {e}")
                break
        
        return all_items
    
    @staticmethod
    def calculate_pages(total: int, limit: int = DEFAULT_LIMIT) -> int:
        """
        Calculate number of pages needed for total items.
        
        Args:
            total: Total number of items
            limit: Items per page
            
        Returns:
            Number of pages needed
        """
        if limit <= 0:
            return 0
        return (total + limit - 1) // limit  # Ceiling division
