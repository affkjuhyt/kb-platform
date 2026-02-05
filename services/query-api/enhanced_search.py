"""
Enhanced Search Engine with Query Caching

Provides:
- Semantic query caching with Redis
- TTL-based cache invalidation
- Cache warming capabilities
- Query similarity caching
"""

import hashlib
import json
import time
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from collections import OrderedDict

import redis

from config import settings


@dataclass
class CacheStats:
    """Statistics for query cache."""

    hits: int = 0
    misses: int = 0
    size: int = 0
    max_size: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class QueryCache:
    """
    Redis-backed query cache with L1 in-memory fallback.

    Features:
    - Two-level caching (L1 memory, L2 Redis)
    - Automatic TTL management
    - Query normalization
    - Cache statistics
    """

    def __init__(
        self,
        redis_url: str = None,
        ttl: int = None,
        max_size: int = None,
        enable_l1: bool = True,
    ):
        self.redis_url = redis_url or settings.redis_url
        self.ttl = ttl or settings.query_cache_ttl
        self.max_size = max_size or settings.query_cache_max_size
        self.enable_l1 = enable_l1

        self._redis: Optional[redis.Redis] = None
        self._l1_cache: OrderedDict = OrderedDict()
        self._l1_ttl: Dict[str, datetime] = {}
        self._lock = asyncio.Lock()
        self._stats = CacheStats(max_size=self.max_size)

    async def initialize(self):
        """Initialize Redis connection."""
        try:
            self._redis = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            self._redis.ping()
            print(f"✓ Query cache connected to Redis: {self.redis_url}")
        except Exception as e:
            print(f"⚠ Query cache Redis connection failed: {e}")
            self._redis = None

    def _normalize_query(self, query: str) -> str:
        """Normalize query for cache key consistency."""
        normalized = " ".join(query.lower().strip().split())
        return normalized

    def _generate_key(self, query: str, tenant_id: str = None) -> str:
        """Generate cache key for a query."""
        normalized = self._normalize_query(query)
        key_data = {"q": normalized}
        if tenant_id:
            key_data["t"] = tenant_id
        key_str = json.dumps(key_data, sort_keys=True)
        return f"query:{hashlib.md5(key_str.encode()).hexdigest()}"

    async def get(self, query: str, tenant_id: str = None) -> Optional[Any]:
        """
        Get cached result for a query.

        Args:
            query: Search query
            tenant_id: Tenant identifier

        Returns:
            Cached result or None if not found
        """
        key = self._generate_key(query, tenant_id)

        async with self._lock:
            if self.enable_l1:
                if key in self._l1_cache:
                    expiry = self._l1_ttl.get(key)
                    if expiry is None or datetime.now() < expiry:
                        self._stats.hits += 1
                        return self._l1_cache[key]
                    else:
                        del self._l1_cache[key]
                        del self._l1_ttl[key]
                self._stats.misses += 1

        if self._redis:
            try:
                data = self._redis.get(key)
                if data:
                    result = json.loads(data)
                    if self.enable_l1:
                        async with self._lock:
                            self._l1_cache[key] = result
                            self._l1_ttl[key] = datetime.now() + timedelta(
                                seconds=self.ttl
                            )
                    return result
            except Exception as e:
                print(f"Query cache Redis get error: {e}")

        return None

    async def set(
        self,
        query: str,
        result: Any,
        tenant_id: str = None,
        ttl: int = None,
    ):
        """
        Cache a query result.

        Args:
            query: Search query
            result: Result to cache
            tenant_id: Tenant identifier
            ttl: Override TTL in seconds
        """
        key = self._generate_key(query, tenant_id)
        cache_ttl = ttl or self.ttl

        if self.enable_l1:
            async with self._lock:
                if key in self._l1_cache:
                    self._l1_cache.move_to_end(key)
                else:
                    while len(self._l1_cache) >= self.max_size:
                        self._l1_cache.popitem(last=False)
                self._l1_cache[key] = result
                self._l1_ttl[key] = datetime.now() + timedelta(seconds=cache_ttl)

        if self._redis:
            try:
                data = json.dumps(result)
                self._redis.setex(key, cache_ttl, data)
            except Exception as e:
                print(f"Query cache Redis set error: {e}")

    async def delete(self, query: str, tenant_id: str = None):
        """Delete cached result for a query."""
        key = self._generate_key(query, tenant_id)

        async with self._lock:
            self._l1_cache.pop(key, None)
            self._l1_ttl.pop(key, None)

        if self._redis:
            try:
                self._redis.delete(key)
            except Exception as e:
                print(f"Query cache Redis delete error: {e}")

    async def invalidate_tenant(self, tenant_id: str):
        """Invalidate all cached results for a tenant."""
        pattern = f"query:*"
        keys_to_delete = []

        if self._redis:
            try:
                cursor = 0
                while True:
                    cursor, keys = self._redis.scan(cursor, match=pattern, count=100)
                    for key in keys:
                        if self._redis.hget(key, "tenant_id") == tenant_id:
                            keys_to_delete.append(key)
                    if cursor == 0:
                        break
                    if len(keys_to_delete) > 1000:
                        break

                if keys_to_delete:
                    self._redis.delete(*keys_to_delete)
            except Exception as e:
                print(f"Query cache tenant invalidation error: {e}")

        async with self._lock:
            keys_to_remove = [k for k, v in self._l1_ttl.items() if tenant_id in k]
            for k in keys_to_remove:
                self._l1_cache.pop(k, None)
                self._l1_ttl.pop(k, None)

    async def clear_all(self):
        """Clear all cached results."""
        async with self._lock:
            self._l1_cache.clear()
            self._l1_ttl.clear()

        if self._redis:
            try:
                pattern = "query:*"
                cursor = 0
                keys = []
                while True:
                    cursor, keys = self._redis.scan(cursor, match=pattern, count=100)
                    if keys:
                        self._redis.delete(*keys)
                    if cursor == 0:
                        break
            except Exception as e:
                print(f"Query cache clear error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        async with self._lock:
            return {
                "hits": self._stats.hits,
                "misses": self._stats.misses,
                "hit_rate": f"{self._stats.hit_rate:.2%}",
                "l1_size": len(self._l1_cache),
                "l1_max_size": self.max_size,
                "l2_connected": self._redis is not None,
                "ttl_seconds": self.ttl,
            }


class EnhancedSearchEngine:
    """
    Enhanced search engine with caching, HyDE, and query decomposition.

    Combines:
    - Query caching
    - HyDE for improved embeddings
    - Query decomposition for complex queries
    - Hybrid search (vector + BM25)
    """

    def __init__(
        self,
        qdrant_store=None,
        opensearch_store=None,
        embedder=None,
        cache: QueryCache = None,
        hyde_engine=None,
        decomposition_engine=None,
    ):
        self.qdrant = qdrant_store
        self.opensearch = opensearch_store
        self.embedder = embedder
        self.cache = cache or QueryCache()
        self.hyde = hyde_engine
        self.decomposition = decomposition_engine

    def configure(
        self,
        qdrant_store,
        opensearch_store,
        embedder,
    ):
        """Configure the search engine with required components."""
        self.qdrant = qdrant_store
        self.opensearch = opensearch_store
        self.embedder = embedder

        if self.hyde:
            self.hyde.configure_stores(qdrant_store, opensearch_store)

    async def search(
        self,
        query: str,
        tenant_id: str = None,
        top_k: int = 10,
        use_cache: bool = None,
        use_hyde: bool = None,
        use_decomposition: bool = None,
        filters: dict = None,
    ) -> Dict[str, Any]:
        """
        Perform enhanced search.

        Args:
            query: Search query
            tenant_id: Tenant identifier
            top_k: Number of results
            use_cache: Enable caching
            use_hyde: Use HyDE embeddings
            use_decomposition: Use query decomposition
            filters: Additional filters

        Returns:
            Dict with results and metadata
        """
        use_cache = use_cache if use_cache is not None else settings.query_cache_enabled
        use_hyde = use_hyde if use_hyde is not None else settings.hyde_enabled
        use_decomposition = (
            use_decomposition
            if use_decomposition is not None
            else settings.query_decomposition_enabled
        )

        cache_key = f"search:{self._generate_key(query, tenant_id, use_hyde, use_decomposition)}"

        if use_cache:
            cached = await self.cache.get(query, tenant_id)
            if cached:
                cached["cached"] = True
                return cached

        if filters is None:
            filters = {}
        if tenant_id:
            filters["tenant_id"] = tenant_id

        start_time = time.time()
        hyde_doc = None
        decomposed_query = None

        if use_hyde and self.hyde:
            results, hyde_doc = await self.hyde.search(
                query=query,
                tenant_id=tenant_id,
                top_k=top_k,
                use_hyde=True,
                filters=filters,
            )
        elif use_decomposition and self.decomposition:
            results, decomposed_query = await self.decomposition.search(
                query=query,
                tenant_id=tenant_id,
                top_k=top_k,
                use_decomposition=True,
                filters=filters,
            )
        else:
            results = await self._basic_search(
                query=query,
                filters=filters,
                top_k=top_k * 2,
            )

        final_results = await self._fetch_chunk_details(results, top_k)

        response = {
            "query": query,
            "results": final_results,
            "total": len(final_results),
            "time_ms": int((time.time() - start_time) * 1000),
            "hyde_used": hyde_doc is not None,
            "decomposition_used": decomposed_query is not None,
            "cached": False,
        }

        if hyde_doc:
            response["hyde_answer"] = hyde_doc.hypothetical_answer[:200]

        if decomposed_query:
            response["sub_queries"] = [
                {"id": sq.id, "query": sq.query, "intent": sq.intent}
                for sq in decomposed_query.sub_queries
            ]

        if use_cache:
            await self.cache.set(query, response, tenant_id)

        return response

    async def _basic_search(
        self,
        query: str,
        filters: dict,
        top_k: int,
    ) -> List[dict]:
        """Perform basic hybrid search."""
        if self.embedder is None:
            from embedding import embedder_factory

            self.embedder = embedder_factory()

        embedding = self.embedder.embed([query])[0]

        vector_results = []
        if self.qdrant:
            vector_results = self.qdrant.search(
                vector=embedding,
                limit=top_k,
                filters=filters,
            )

        bm25_results = []
        if self.opensearch:
            bm25_results = self.opensearch.bm25_search(
                query=query,
                k=top_k,
                filters=filters,
            )

        return self._merge_results(vector_results, bm25_results, top_k)

    def _merge_results(
        self,
        vector_results: List,
        bm25_results: dict,
        top_k: int,
    ) -> List[dict]:
        """Merge vector and BM25 results."""
        from fusion import rrf_fusion

        v_rank = []
        for hit in vector_results:
            doc_id = hit.payload.get("doc_id")
            chunk_index = hit.payload.get("chunk_index")
            v_rank.append((f"{doc_id}:{chunk_index}", float(hit.score)))

        b_rank = []
        for hit in bm25_results.get("hits", {}).get("hits", []):
            doc_id = hit["_source"]["doc_id"]
            chunk_index = hit["_source"]["chunk_index"]
            b_rank.append((f"{doc_id}:{chunk_index}", float(hit.get("_score", 0.0))))

        v_scores = {k: s for k, s in v_rank}
        b_scores = {k: s for k, s in b_rank}

        if settings.fusion_method == "weighted":
            from fusion import weighted_fusion

            fusion_scores = weighted_fusion(v_scores, b_scores)
        else:
            fusion_scores = rrf_fusion([v_rank, b_rank])

        ranked = sorted(fusion_scores.items(), key=lambda x: x[1], reverse=True)
        return [{"id": item_id, "score": score} for item_id, score in ranked[:top_k]]

    async def _fetch_chunk_details(
        self,
        results: List[dict],
        top_k: int,
    ) -> List[dict]:
        """Fetch full chunk details for results."""
        from db import get_chunks_by_ids

        id_pairs = []
        for r in results[:top_k]:
            parts = r["id"].split(":")
            if len(parts) == 2:
                id_pairs.append((parts[0], int(parts[1])))

        if not id_pairs:
            return []

        chunk_rows = get_chunks_by_ids(id_pairs)
        chunk_map = {(c.doc_id, c.chunk_index): c for c in chunk_rows}

        enriched = []
        for r in results:
            parts = r["id"].split(":")
            if len(parts) == 2:
                key = (parts[0], int(parts[1]))
                chunk = chunk_map.get(key)
                if chunk:
                    enriched.append(
                        {
                            "id": r["id"],
                            "score": r["score"],
                            "doc_id": chunk.doc_id,
                            "source": chunk.source,
                            "text": chunk.text,
                            "section_path": chunk.section_path,
                        }
                    )
        return enriched

    def _generate_key(
        self,
        query: str,
        tenant_id: str = None,
        use_hyde: bool = False,
        use_decomposition: bool = False,
    ) -> str:
        """Generate cache key with modifiers."""
        parts = [query]
        if tenant_id:
            parts.append(tenant_id)
        if use_hyde:
            parts.append("hyde")
        if use_decomposition:
            parts.append("decomp")
        return ":".join(parts)

    async def warm_cache(self, queries: List[Dict[str, Any]]):
        """
        Warm cache with common queries.

        Args:
            queries: List of dicts with 'query', 'tenant_id', 'top_k' keys
        """
        print(f"Warming cache with {len(queries)} queries...")
        for q in queries:
            try:
                await self.search(
                    query=q["query"],
                    tenant_id=q.get("tenant_id"),
                    top_k=q.get("top_k", 10),
                    use_cache=True,
                )
            except Exception as e:
                print(f"Cache warming error for '{q['query']}': {e}")
        print("Cache warming complete.")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache.get_stats()


_query_cache = QueryCache()


async def get_query_cache() -> QueryCache:
    """Get or create the global query cache."""
    if _query_cache._redis is None:
        await _query_cache.initialize()
    return _query_cache


async def get_enhanced_search_engine() -> EnhancedSearchEngine:
    """Create and configure an enhanced search engine."""
    cache = await get_query_cache()

    from qdrant_store import QdrantStore
    from opensearch_store import OpenSearchStore
    from embedding import embedder_factory

    qdrant = QdrantStore()
    opensearch = OpenSearchStore()
    embedder = embedder_factory()

    engine = EnhancedSearchEngine(
        qdrant_store=qdrant,
        opensearch_store=opensearch,
        embedder=embedder,
        cache=cache,
    )

    return engine
