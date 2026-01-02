"""
Caching utilities for Prisma Access SCM API.

Provides simple in-memory caching to reduce redundant API calls.
"""

from typing import Dict, Any, Optional, Tuple
import time
import logging

logger = logging.getLogger(__name__)


class APICache:
    """
    Simple in-memory cache for API responses.
    
    Uses URL as cache key with optional TTL (time-to-live).
    """
    
    def __init__(self, ttl: int = 300):
        """
        Initialize cache.
        
        Args:
            ttl: Time-to-live in seconds (default: 300 = 5 minutes)
        """
        self.ttl = ttl
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._enabled = True
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if not expired.
        
        Args:
            key: Cache key (typically URL)
            
        Returns:
            Cached value or None if not found/expired
        """
        if not self._enabled:
            return None
        
        if key not in self._cache:
            return None
        
        value, timestamp = self._cache[key]
        
        # Check if expired
        if time.time() - timestamp > self.ttl:
            logger.debug(f"Cache expired for key: {key}")
            del self._cache[key]
            return None
        
        logger.debug(f"Cache hit for key: {key}")
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Store value in cache with current timestamp.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        if not self._enabled:
            return
        
        self._cache[key] = (value, time.time())
        logger.debug(f"Cached value for key: {key}")
    
    def delete(self, key: str) -> None:
        """
        Delete value from cache.
        
        Args:
            key: Cache key to delete
        """
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Deleted cache key: {key}")
    
    def clear(self) -> None:
        """Clear all cached values"""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cleared {count} cached items")
    
    def enable(self) -> None:
        """Enable caching"""
        self._enabled = True
        logger.debug("Cache enabled")
    
    def disable(self) -> None:
        """Disable caching (will not store or retrieve)"""
        self._enabled = False
        logger.debug("Cache disabled")
    
    def is_enabled(self) -> bool:
        """Check if caching is enabled"""
        return self._enabled
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache stats
        """
        now = time.time()
        expired = 0
        valid = 0
        
        for key, (value, timestamp) in self._cache.items():
            if now - timestamp > self.ttl:
                expired += 1
            else:
                valid += 1
        
        return {
            'total_entries': len(self._cache),
            'valid_entries': valid,
            'expired_entries': expired,
            'ttl': self.ttl,
            'enabled': self._enabled
        }
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        now = time.time()
        expired_keys = []
        
        for key, (value, timestamp) in self._cache.items():
            if now - timestamp > self.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def __len__(self) -> int:
        """Get number of cached items"""
        return len(self._cache)
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists and is not expired"""
        return self.get(key) is not None
