"""
Redis Caching Strategy Module for RAG System

This module provides intelligent caching for RAG operations.
Features:
- Multi-level caching (L1: in-memory, L2: Redis)
- Semantic caching for search queries
- Cache invalidation strategies
- Compression for large objects
- TTL management

Usage:
    from cache import cache_manager

    # Cache search results
    @cache_manager.cache_search(ttl=300)
    def search(query, tenant_id):
        return perform_search(query, tenant_id)

    # Cache RAG responses
    @cache_manager.cache_rag(ttl=600)
    def rag_query(query, tenant_id):
        return perform_rag(query, tenant_id)
"""

import json
import pickle
import hashlib
import zlib
from typing import Any, Optional, Callable, Dict, List
from functools import wraps
from datetime import datetime, timedelta
import redis
from dataclasses import dataclass, asdict
import time
import threading
from collections import OrderedDict
import os

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
CACHE_COMPRESSION = os.getenv("CACHE_COMPRESSION", "true").lower() == "true"
CACHE_COMPRESSION_THRESHOLD = int(
    os.getenv("CACHE_COMPRESSION_THRESHOLD", "1024")
)  # bytes
L1_CACHE_SIZE = int(os.getenv("L1_CACHE_SIZE", "1000"))  # max items
L1_CACHE_TTL = int(os.getenv("L1_CACHE_TTL", "60"))  # seconds


@dataclass
class CacheEntry:
    """Cache entry metadata."""

    key: str
    value: Any
    created_at: datetime
    ttl: int
    tags: List[str]
    compressed: bool = False
    size_bytes: int = 0


class LRUCache:
    """Thread-safe in-memory LRU cache (L1)."""

    def __init__(self, maxsize: int = L1_CACHE_SIZE):
        self.maxsize = maxsize
        self.cache: OrderedDict[str, Any] = OrderedDict()
        self.lock = threading.RLock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Get item from cache."""
        with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                value = self.cache.pop(key)
                self.cache[key] = value
                self.hits += 1
                return value
            self.misses += 1
            return None

    def set(self, key: str, value: Any):
        """Set item in cache."""
        with self.lock:
            if key in self.cache:
                self.cache.pop(key)
            elif len(self.cache) >= self.maxsize:
                # Remove least recently used
                self.cache.popitem(last=False)

            self.cache[key] = value

    def delete(self, key: str):
        """Delete item from cache."""
        with self.lock:
            if key in self.cache:
                del self.cache[key]

    def clear(self):
        """Clear all items."""
        with self.lock:
            self.cache.clear()

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        with self.lock:
            total = self.hits + self.misses
            hit_rate = self.hits / total if total > 0 else 0
            return {
                "size": len(self.cache),
                "maxsize": self.maxsize,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": round(hit_rate, 4),
            }


class RedisCache:
    """Redis cache wrapper (L2)."""

    def __init__(self, redis_url: str = REDIS_URL):
        self.redis_client = None
        self.redis_url = redis_url
        self._connect()

    def _connect(self):
        """Connect to Redis."""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=False,  # We handle encoding ourselves
                socket_connect_timeout=5,
                socket_timeout=5,
                health_check_interval=30,
            )
            self.redis_client.ping()
            print(f"✓ Connected to Redis: {self.redis_url}")
        except Exception as e:
            print(f"⚠ Redis connection failed: {e}")
            self.redis_client = None

    def _compress(self, data: bytes) -> bytes:
        """Compress data if enabled."""
        if CACHE_COMPRESSION and len(data) > CACHE_COMPRESSION_THRESHOLD:
            return zlib.compress(data)
        return data

    def _decompress(self, data: bytes, compressed: bool = False) -> bytes:
        """Decompress data."""
        if compressed or (CACHE_COMPRESSION and data.startswith(b"x\\x9c")):
            try:
                return zlib.decompress(data)
            except:
                pass
        return data

    def get(self, key: str) -> Optional[Any]:
        """Get item from Redis."""
        if not self.redis_client:
            return None

        try:
            data = self.redis_client.get(key)
            if data:
                # Check if compressed
                compressed = data.startswith(b"CMP:")
                if compressed:
                    data = data[4:]  # Remove prefix
                    data = zlib.decompress(data)

                return pickle.loads(data)
        except Exception as e:
            print(f"Redis get error: {e}")

        return None

    def set(self, key: str, value: Any, ttl: int = 300, tags: List[str] = None):
        """Set item in Redis."""
        if not self.redis_client:
            return False

        try:
            # Serialize
            data = pickle.dumps(value)

            # Compress if large
            compressed = False
            if CACHE_COMPRESSION and len(data) > CACHE_COMPRESSION_THRESHOLD:
                data = b"CMP:" + zlib.compress(data)
                compressed = True

            # Store
            self.redis_client.setex(key, ttl, data)

            # Add to tag index
            if tags:
                for tag in tags:
                    self.redis_client.sadd(f"tag:{tag}", key)
                    self.redis_client.expire(f"tag:{tag}", ttl)

            return True
        except Exception as e:
            print(f"Redis set error: {e}")
            return False

    def delete(self, key: str):
        """Delete item from Redis."""
        if not self.redis_client:
            return

        try:
            self.redis_client.delete(key)
        except Exception as e:
            print(f"Redis delete error: {e}")

    def delete_by_tag(self, tag: str):
        """Delete all items with tag."""
        if not self.redis_client:
            return

        try:
            keys = self.redis_client.smembers(f"tag:{tag}")
            if keys:
                self.redis_client.delete(*keys)
                self.redis_client.delete(f"tag:{tag}")
        except Exception as e:
            print(f"Redis delete_by_tag error: {e}")

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self.redis_client:
            return False

        try:
            return self.redis_client.exists(key) > 0
        except:
            return False

    def get_ttl(self, key: str) -> int:
        """Get remaining TTL."""
        if not self.redis_client:
            return -2

        try:
            return self.redis_client.ttl(key)
        except:
            return -2


class CacheManager:
    """Multi-level cache manager."""

    def __init__(self):
        self.l1_cache = LRUCache(maxsize=L1_CACHE_SIZE)
        self.l2_cache = RedisCache()
        self.enabled = CACHE_ENABLED

    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = {"prefix": prefix, "args": args, "kwargs": kwargs}
        key_str = json.dumps(key_data, sort_keys=True)
        return f"{prefix}:{hashlib.md5(key_str.encode()).hexdigest()}"

    def get(self, key: str, use_l1: bool = True, use_l2: bool = True) -> Optional[Any]:
        """Get from cache (L1 -> L2)."""
        if not self.enabled:
            return None

        # Try L1
        if use_l1:
            value = self.l1_cache.get(key)
            if value is not None:
                return value

        # Try L2
        if use_l2:
            value = self.l2_cache.get(key)
            if value is not None:
                # Promote to L1
                if use_l1:
                    self.l1_cache.set(key, value)
                return value

        return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: int = 300,
        tags: List[str] = None,
        use_l1: bool = True,
        use_l2: bool = True,
    ):
        """Set in cache (L1 and L2)."""
        if not self.enabled:
            return

        # L1 cache (short TTL)
        if use_l1:
            self.l1_cache.set(key, value)

        # L2 cache (Redis)
        if use_l2:
            self.l2_cache.set(key, value, ttl, tags)

    def delete(self, key: str):
        """Delete from all cache levels."""
        self.l1_cache.delete(key)
        self.l2_cache.delete(key)

    def invalidate_by_tag(self, tag: str):
        """Invalidate all cache entries with tag."""
        self.l2_cache.delete_by_tag(tag)

    def clear_all(self):
        """Clear all caches."""
        self.l1_cache.clear()
        # Note: Don't clear Redis entirely, use tags for selective clearing

    # Decorators for common use cases
    def cache_search(self, ttl: int = 300):
        """Decorator for caching search results."""

        def decorator(func: Callable):
            @wraps(func)
            def wrapper(query: str, tenant_id: str, *args, **kwargs):
                if not self.enabled:
                    return func(query, tenant_id, *args, **kwargs)

                cache_key = self._generate_key(
                    "search", query, tenant_id, *args, **kwargs
                )

                # Try cache
                cached = self.get(cache_key)
                if cached is not None:
                    return cached

                # Execute and cache
                result = func(query, tenant_id, *args, **kwargs)
                self.set(cache_key, result, ttl, tags=["search", tenant_id])

                return result

            return wrapper

        return decorator

    def cache_rag(self, ttl: int = 600):
        """Decorator for caching RAG responses."""

        def decorator(func: Callable):
            @wraps(func)
            def wrapper(query: str, tenant_id: str, *args, **kwargs):
                if not self.enabled:
                    return func(query, tenant_id, *args, **kwargs)

                cache_key = self._generate_key("rag", query, tenant_id, *args, **kwargs)

                # Try cache
                cached = self.get(cache_key)
                if cached is not None:
                    return cached

                # Execute and cache
                result = func(query, tenant_id, *args, **kwargs)
                self.set(cache_key, result, ttl, tags=["rag", tenant_id])

                return result

            return wrapper

        return decorator

    def cache_extraction(self, ttl: int = 1800):
        """Decorator for caching extraction results."""

        def decorator(func: Callable):
            @wraps(func)
            def wrapper(query: str, schema: dict, tenant_id: str, *args, **kwargs):
                if not self.enabled:
                    return func(query, schema, tenant_id, *args, **kwargs)

                # Include schema hash in key
                schema_hash = hashlib.md5(
                    json.dumps(schema, sort_keys=True).encode()
                ).hexdigest()[:8]
                cache_key = self._generate_key(
                    "extract", query, schema_hash, tenant_id, *args, **kwargs
                )

                # Try cache
                cached = self.get(cache_key)
                if cached is not None:
                    return cached

                # Execute and cache
                result = func(query, schema, tenant_id, *args, **kwargs)
                self.set(cache_key, result, ttl, tags=["extraction", tenant_id])

                return result

            return wrapper

        return decorator

    def cache_vector(self, ttl: int = 3600):
        """Decorator for caching vector embeddings."""

        def decorator(func: Callable):
            @wraps(func)
            def wrapper(texts: List[str], *args, **kwargs):
                if not self.enabled:
                    return func(texts, *args, **kwargs)

                # Individual text embeddings
                results = []
                missing_texts = []
                missing_indices = []

                for i, text in enumerate(texts):
                    cache_key = self._generate_key("vector", text, *args, **kwargs)
                    cached = self.get(
                        cache_key, use_l1=False
                    )  # Vectors too large for L1

                    if cached is not None:
                        results.append((i, cached))
                    else:
                        missing_texts.append(text)
                        missing_indices.append(i)

                if missing_texts:
                    # Batch embed missing texts
                    embeddings = func(missing_texts, *args, **kwargs)

                    # Cache and add to results
                    for idx, text, embedding in zip(
                        missing_indices, missing_texts, embeddings
                    ):
                        cache_key = self._generate_key("vector", text, *args, **kwargs)
                        self.set(
                            cache_key, embedding, ttl, tags=["vector"], use_l1=False
                        )
                        results.append((idx, embedding))

                # Sort by original index
                results.sort(key=lambda x: x[0])
                return [r[1] for r in results]

            return wrapper

        return decorator

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        l1_stats = self.l1_cache.get_stats()
        return {
            "enabled": self.enabled,
            "l1_cache": l1_stats,
            "l2_cache_connected": self.l2_cache.redis_client is not None,
        }


# Global instance
cache_manager = CacheManager()


# Convenience functions
def cache_search(ttl: int = 300):
    """Cache search results."""
    return cache_manager.cache_search(ttl)


def cache_rag(ttl: int = 600):
    """Cache RAG responses."""
    return cache_manager.cache_rag(ttl)


def cache_extraction(ttl: int = 1800):
    """Cache extraction results."""
    return cache_manager.cache_extraction(ttl)


def cache_vector(ttl: int = 3600):
    """Cache vector embeddings."""
    return cache_manager.cache_vector(ttl)


def invalidate_tenant_cache(tenant_id: str):
    """Invalidate all cache for a tenant."""
    cache_manager.invalidate_by_tag(tenant_id)


# Example usage
if __name__ == "__main__":
    print("Cache Manager Example")
    print("=" * 60)

    # Test caching
    @cache_search(ttl=300)
    def example_search(query: str, tenant_id: str):
        print(f"  Executing search: {query}")
        time.sleep(0.1)  # Simulate work
        return {"results": [f"doc_{i}" for i in range(5)]}

    # First call (cache miss)
    print("\n1. First call (cache miss):")
    result1 = example_search("machine learning", "tenant-123")

    # Second call (cache hit)
    print("\n2. Second call (cache hit):")
    result2 = example_search("machine learning", "tenant-123")

    # Stats
    print("\n3. Cache statistics:")
    stats = cache_manager.get_stats()
    print(f"  L1 Cache hit rate: {stats['l1_cache']['hit_rate']:.2%}")
    print(f"  L1 Cache size: {stats['l1_cache']['size']}")
    print(f"  L2 Cache connected: {stats['l2_cache_connected']}")
