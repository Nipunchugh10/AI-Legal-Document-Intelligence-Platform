"""
In-Memory Fast LRU / TTL Cache Module
-------------------------------------
High-performance in-memory cache with Time-To-Live (TTL) expiration and LRU eviction.
Optimizes repeated fetches for contract analyses, knowledge base queries, and parsed structures.

Day 43 — Performance Optimization
"""

import time
import threading
from typing import Any, Optional, Tuple
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)


class InMemoryLRUTTLCache:
    """Thread-safe LRU cache with per-item TTL expiration."""

    def __init__(self, max_size: int = 1000, default_ttl_seconds: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl_seconds
        # Stores key -> (value, expire_timestamp)
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                return None
            val, expire_time = self._cache[key]
            if time.time() > expire_time:
                del self._cache[key]
                return None
            # Move to end to mark as recently used
            self._cache.move_to_end(key)
            return val

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expire_time = time.time() + ttl
        with self._lock:
            if key in self._cache:
                del self._cache[key]
            elif len(self._cache) >= self.max_size:
                # Evict oldest item (first item in OrderedDict)
                self._cache.popitem(last=False)
            self._cache[key] = (value, expire_time)

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> None:
        with self._lock:
            keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_remove:
                del self._cache[k]

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._cache)


# Global singleton instance for memory cache
memory_cache = InMemoryLRUTTLCache(max_size=1000, default_ttl_seconds=300)
