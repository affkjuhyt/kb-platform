"""
Unit Tests for Enhanced Search Module

Tests cover:
- Query caching
- Enhanced search engine
- Cache statistics
- Cache warming
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

import sys

sys.path.insert(0, "/Users/thiennlinh/Documents/New project/services/query-api")

from enhanced_search import (
    QueryCache,
    EnhancedSearchEngine,
    CacheStats,
)


class TestQueryCache:
    """Test query caching functionality."""

    @pytest.fixture
    def cache(self):
        return QueryCache(
            redis_url="redis://localhost:6379/0",
            ttl=3600,
            max_size=1000,
            enable_l1=True,
        )

    def test_normalize_query(self, cache):
        """Test query normalization."""
        assert cache._normalize_query("  What is AI?  ") == "what is ai?"
        assert cache._normalize_query("Multiple   spaces") == "multiple spaces"

    def test_generate_key(self, cache):
        """Test cache key generation."""
        key1 = cache._generate_key("test query", "tenant-1")
        key2 = cache._generate_key("test query", "tenant-1")
        key3 = cache._generate_key("test query", "tenant-2")

        assert key1 == key2  # Same query + tenant = same key
        assert key1 != key3  # Different tenant = different key

    @pytest.mark.asyncio
    async def test_l1_cache_hit(self, cache):
        """Test L1 (memory) cache hit."""
        result = {"data": "test result"}
        key = cache._generate_key("query", "tenant")

        cache._l1_cache[key] = result
        cache._l1_ttl[key] = datetime.now() + timedelta(seconds=3600)

        cached = await cache.get("query", "tenant")

        assert cached == result
        assert cache._stats.hits == 1
        assert cache._stats.misses == 0

    @pytest.mark.asyncio
    async def test_l1_cache_expired(self, cache):
        """Test expired L1 cache entry."""
        result = {"data": "expired"}
        key = cache._generate_key("query", "tenant")

        cache._l1_cache[key] = result
        cache._l1_ttl[key] = datetime.now() - timedelta(seconds=1)  # Expired

        cached = await cache.get("query", "tenant")

        assert cached is None
        assert cache._stats.misses == 1

    @pytest.mark.asyncio
    async def test_cache_set_l1(self, cache):
        """Test setting cache in L1."""
        result = {"data": "new result"}

        await cache.set("query", result, "tenant")

        key = cache._generate_key("query", "tenant")
        assert key in cache._l1_cache
        assert cache._l1_cache[key] == result

    @pytest.mark.asyncio
    async def test_cache_set_lru_eviction(self, cache):
        """Test LRU eviction when cache is full."""
        cache.max_size = 2

        await cache.set("q1", {"d": 1}, "t")
        await cache.set("q2", {"d": 2}, "t")
        await cache.set("q3", {"d": 3}, "t")  # Should evict q1

        assert len(cache._l1_cache) == 2

    @pytest.mark.asyncio
    async def test_delete(self, cache):
        """Test cache deletion."""
        result = {"data": "test"}
        await cache.set("query", result, "tenant")

        await cache.delete("query", "tenant")

        key = cache._generate_key("query", "tenant")
        assert key not in cache._l1_cache

    @pytest.mark.asyncio
    async def test_invalidate_tenant(self, cache):
        """Test tenant cache invalidation."""
        await cache.set("q1", {"d": 1}, "tenant-1")
        await cache.set("q2", {"d": 2}, "tenant-1")
        await cache.set("q3", {"d": 3}, "tenant-2")

        await cache.invalidate_tenant("tenant-1")

        # tenant-1 entries should be removed
        assert await cache.get("q1", "tenant-1") is None
        assert await cache.get("q2", "tenant-1") is None
        # tenant-2 entry should remain
        assert await cache.get("q3", "tenant-2") is not None

    @pytest.mark.asyncio
    async def test_clear_all(self, cache):
        """Test clearing all cache."""
        await cache.set("q1", {"d": 1}, "t1")
        await cache.set("q2", {"d": 2}, "t2")

        await cache.clear_all()

        assert len(cache._l1_cache) == 0
        assert await cache.get("q1", "t1") is None

    def test_get_stats(self, cache):
        """Test cache statistics."""
        cache._stats.hits = 80
        cache._stats.misses = 20

        stats = cache.get_stats()

        assert stats["hits"] == 80
        assert stats["misses"] == 20
        assert stats["hit_rate"] == "80.00%"
        assert stats["l1_size"] == 0


class TestCacheStats:
    """Test cache statistics calculations."""

    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        stats = CacheStats(hits=75, misses=25, max_size=1000)

        assert stats.hit_rate == 0.75

    def test_hit_rate_zero_total(self):
        """Test hit rate with no operations."""
        stats = CacheStats(hits=0, misses=0, max_size=1000)

        assert stats.hit_rate == 0.0


class TestEnhancedSearchEngine:
    """Test enhanced search engine."""

    @pytest.fixture
    def mock_components(self):
        cache = Mock(spec=QueryCache)
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()

        qdrant = Mock()
        opensearch = Mock()
        embedder = Mock()

        return cache, qdrant, opensearch, embedder

    @pytest.mark.asyncio
    async def test_search_with_cache_hit(self, mock_components):
        """Test search returns cached result."""
        cache, qdrant, opensearch, embedder = mock_components

        cached_result = {
            "query": "test",
            "results": [{"id": "doc1"}],
            "cached": False,
        }
        cache.get = AsyncMock(return_value=cached_result)

        engine = EnhancedSearchEngine(cache=cache)

        result = await engine.search("test query", tenant_id="t1")

        assert result["cached"] is True
        assert result["results"] == [{"id": "doc1"}]

    @pytest.mark.asyncio
    async def test_search_without_cache(self, mock_components):
        """Test search without cache hit."""
        cache, qdrant, opensearch, embedder = mock_components

        qdrant.search.return_value = [
            Mock(payload={"doc_id": "doc1", "chunk_index": 0}, score=0.95),
        ]
        opensearch.bm25_search.return_value = {"hits": {"hits": []}}
        embedder.embed.return_value = [[0.1, 0.2, 0.3]]

        engine = EnhancedSearchEngine(
            qdrant_store=qdrant,
            opensearch_store=opensearch,
            embedder=embedder,
            cache=cache,
        )

        with patch("enhanced_search.get_chunks_by_ids") as mock_get:
            mock_get.return_value = [
                Mock(
                    doc_id="doc1",
                    chunk_index=0,
                    text="test",
                    source="s",
                    section_path="p",
                ),
            ]
            result = await engine.search("test", tenant_id="t1")

        assert result["cached"] is False
        assert result["query"] == "test"
        cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_with_hyde(self, mock_components):
        """Test search with HyDE enabled."""
        cache, qdrant, opensearch, embedder = mock_components

        hyde_engine = Mock()
        hyde_engine.search = AsyncMock(
            return_value=(
                [{"id": "doc1:0", "score": 0.95}],
                Mock(hypothetical_answer="Hypothetical answer"),
            )
        )

        engine = EnhancedSearchEngine(
            qdrant_store=qdrant,
            opensearch_store=opensearch,
            embedder=embedder,
            cache=cache,
            hyde_engine=hyde_engine,
        )

        with patch("enhanced_search.get_chunks_by_ids") as mock_get:
            mock_get.return_value = [
                Mock(
                    doc_id="doc1",
                    chunk_index=0,
                    text="test",
                    source="s",
                    section_path="p",
                ),
            ]
            result = await engine.search("test", use_hyde=True)

        assert result["hyde_used"] is True
        assert "hyde_answer" in result

    @pytest.mark.asyncio
    async def test_search_with_decomposition(self, mock_components):
        """Test search with decomposition enabled."""
        cache, qdrant, opensearch, embedder = mock_components

        decomp_engine = Mock()
        decomp_engine.search = AsyncMock(
            return_value=(
                [{"id": "doc1:0", "score": 0.95}],
                Mock(sub_queries=[Mock(id=0, query="sub1")]),
            )
        )

        engine = EnhancedSearchEngine(
            qdrant_store=qdrant,
            opensearch_store=opensearch,
            embedder=embedder,
            cache=cache,
            decomposition_engine=decomp_engine,
        )

        with patch("enhanced_search.get_chunks_by_ids") as mock_get:
            mock_get.return_value = [
                Mock(
                    doc_id="doc1",
                    chunk_index=0,
                    text="test",
                    source="s",
                    section_path="p",
                ),
            ]
            result = await engine.search("test", use_decomposition=True)

        assert result["decomposition_used"] is True
        assert "sub_queries" in result

    def test_generate_key(self):
        """Test key generation with modifiers."""
        engine = EnhancedSearchEngine()

        key1 = engine._generate_key("query", "tenant", True, False)
        key2 = engine._generate_key("query", "tenant", False, True)
        key3 = engine._generate_key("query", "tenant", False, False)

        assert key1 != key2  # Different HyDE setting
        assert key2 != key3  # Different decomposition setting

    @pytest.mark.asyncio
    async def test_warm_cache(self, mock_components):
        """Test cache warming."""
        cache, qdrant, opensearch, embedder = mock_components

        qdrant.search.return_value = []
        opensearch.bm25_search.return_value = {"hits": {"hits": []}}
        embedder.embed.return_value = [[0.1]]

        engine = EnhancedSearchEngine(
            qdrant_store=qdrant,
            opensearch_store=opensearch,
            embedder=embedder,
            cache=cache,
        )

        queries = [
            {"query": "q1", "tenant_id": "t1"},
            {"query": "q2", "tenant_id": "t2", "top_k": 5},
        ]

        with patch("enhanced_search.get_chunks_by_ids") as mock_get:
            mock_get.return_value = []
            await engine.warm_cache(queries)

        # Should have searched each query
        assert cache.set.call_count == 2


class TestEnhancedSearchIntegration:
    """Integration tests for enhanced search."""

    @pytest.mark.asyncio
    async def test_search_performance(self):
        """Test search completes within acceptable time."""
        import time

        engine = EnhancedSearchEngine()

        # Mock all external calls
        with patch.object(engine, "_basic_search") as mock_search:
            mock_search.return_value = [{"id": "doc1:0", "score": 0.9}]
            with patch("enhanced_search.get_chunks_by_ids") as mock_get:
                mock_get.return_value = []

                start = time.time()
                await engine.search("test", use_cache=False)
                elapsed = time.time() - start

                assert elapsed < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
