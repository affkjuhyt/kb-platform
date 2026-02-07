"""
Unit Tests for Query Decomposition Module

Tests cover:
- Query decomposition logic
- Sub-query generation
- Multi-query search
- Result merging
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

import sys

sys.path.insert(0, "/Users/thiennlinh/Documents/New project/services/query-api")

from query_decomposition import (
    QueryDecomposer,
    MultiQuerySearchEngine,
    DecompositionStrategy,
    SubQuery,
    DecomposedQuery,
)


class TestQueryDecomposer:
    """Test query decomposition logic."""

    @pytest.fixture
    def decomposer(self):
        return QueryDecomposer(
            llm_gateway_url="http://localhost:8004",
            max_subqueries=3,
        )

    @pytest.mark.asyncio
    async def test_decompose_simple_query(self, decomposer):
        """Test decomposition of simple query."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "text": """{
                "sub_queries": [
                    {"query": "What is AI?", "intent": "definition", "keywords": ["AI"], "is_primary": true}
                ],
                "strategy": "single"
            }"""
        }
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            result = await decomposer.decompose("What is AI?")

        assert isinstance(result, DecomposedQuery)
        assert result.original_query == "What is AI?"
        assert len(result.sub_queries) == 1
        assert result.sub_queries[0].intent == "definition"

    @pytest.mark.asyncio
    async def test_decompose_complex_query(self, decomposer):
        """Test decomposition of complex multi-intent query."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "text": """{
                "sub_queries": [
                    {"query": "What is machine learning?", "intent": "definition", "keywords": ["ML"], "is_primary": true},
                    {"query": "How does deep learning work?", "intent": "mechanism", "keywords": ["DL"], "is_primary": false}
                ],
                "strategy": "parallel"
            }"""
        }
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            result = await decomposer.decompose("Explain ML and DL")

        assert len(result.sub_queries) == 2
        assert result.strategy == DecompositionStrategy.PARALLEL
        assert any(sq.is_primary for sq in result.sub_queries)

    @pytest.mark.asyncio
    async def test_decompose_cache_hit(self, decomposer):
        """Test cache hit returns cached decomposition."""
        cached_result = DecomposedQuery(
            original_query="cached query",
            sub_queries=[SubQuery(0, "sub", "intent", ["kw"], True)],
            strategy=DecompositionStrategy.SINGLE,
        )
        decomposer._decomposition_cache["cached_hash"] = cached_result

        with patch("hashlib.md5") as mock_hash:
            mock_hash.return_value.hexdigest.return_value = "cached_hash"
            result = await decomposer.decompose("cached query")

        assert result == cached_result

    @pytest.mark.asyncio
    async def test_decompose_failure_fallback(self, decomposer):
        """Test graceful fallback on LLM failure."""
        with patch("httpx.AsyncClient.post", side_effect=Exception("LLM Error")):
            result = await decomposer.decompose("What is AI?")

        assert isinstance(result, DecomposedQuery)
        assert len(result.sub_queries) == 1
        assert result.sub_queries[0].query == "What is AI?"

    def test_decompose_simple_rule_based(self, decomposer):
        """Test simple rule-based decomposition without LLM."""
        result = decomposer.decompose_simple("Simple query")

        assert result.strategy == DecompositionStrategy.SINGLE
        assert len(result.sub_queries) == 1
        assert result.sub_queries[0].query == "Simple query"

    def test_decompose_simple_complex_detection(self, decomposer):
        """Test detection of complex queries in simple mode."""
        complex_query = (
            "Explain the difference between machine learning and deep learning"
        )
        result = decomposer.decompose_simple(complex_query)

        assert result.strategy == DecompositionStrategy.PARALLEL

    def test_clear_cache(self, decomposer):
        """Test cache clearing."""
        decomposer._decomposition_cache["key"] = Mock()
        decomposer.clear_cache()
        assert len(decomposer._decomposition_cache) == 0


class TestMultiQuerySearchEngine:
    """Test multi-query search functionality."""

    @pytest.fixture
    def mock_decomposer(self):
        decomposer = Mock()
        decomposer.decompose = AsyncMock(
            return_value=DecomposedQuery(
                original_query="test",
                sub_queries=[
                    SubQuery(0, "sub1", "intent1", ["kw1"], True),
                    SubQuery(1, "sub2", "intent2", ["kw2"], False),
                ],
                strategy=DecompositionStrategy.PARALLEL,
            )
        )
        return decomposer

    @pytest.fixture
    def mock_search_engine(self):
        engine = Mock()
        engine.search = Mock(
            return_value=[
                {"id": "doc1:0", "score": 0.95},
                {"id": "doc2:1", "score": 0.90},
            ]
        )
        return engine

    @pytest.mark.asyncio
    async def test_search_with_decomposition(self, mock_decomposer, mock_search_engine):
        """Test search with query decomposition enabled."""
        engine = MultiQuerySearchEngine(
            decomposer=mock_decomposer,
            search_engine=mock_search_engine,
        )

        results, decomposed = await engine.search(
            query="Complex query",
            tenant_id="tenant-1",
            top_k=5,
            use_decomposition=True,
        )

        assert decomposed is not None
        assert len(decomposed.sub_queries) == 2
        assert mock_search_engine.search.call_count == 2  # Once per sub-query

    @pytest.mark.asyncio
    async def test_search_without_decomposition(
        self, mock_decomposer, mock_search_engine
    ):
        """Test search without decomposition."""
        engine = MultiQuerySearchEngine(
            decomposer=mock_decomposer,
            search_engine=mock_search_engine,
        )

        results, decomposed = await engine.search(
            query="Simple query",
            use_decomposition=False,
        )

        # Should use simple decomposition (single query)
        assert len(decomposed.sub_queries) == 1

    @pytest.mark.asyncio
    async def test_search_subquery(self, mock_search_engine):
        """Test individual sub-query search."""
        engine = MultiQuerySearchEngine(search_engine=mock_search_engine)

        results = await engine._search_subquery(
            sub_query="test query",
            filters={"tenant_id": "t1"},
            top_k=5,
        )

        assert len(results) == 2
        mock_search_engine.search.assert_called_once()

    def test_merge_subquery_results(self):
        """Test merging results from multiple sub-queries."""
        engine = MultiQuerySearchEngine()

        all_results = [
            {"id": "doc1:0", "score": 0.95, "_sub_query_id": 0, "_is_primary": True},
            {"id": "doc1:0", "score": 0.90, "_sub_query_id": 1, "_is_primary": False},
            {"id": "doc2:1", "score": 0.85, "_sub_query_id": 0, "_is_primary": False},
        ]

        decomposed = DecomposedQuery(
            original_query="test",
            sub_queries=[
                SubQuery(0, "q1", "i1", [], True),
                SubQuery(1, "q2", "i2", [], False),
            ],
            strategy=DecompositionStrategy.PARALLEL,
        )

        merged = engine._merge_subquery_results(
            all_results, top_k=5, decomposed=decomposed
        )

        # doc1:0 appears in both sub-queries, should get bonus
        assert len(merged) > 0

    def test_merge_bonus_for_multi_match(self):
        """Test that documents matching multiple sub-queries get bonus."""
        engine = MultiQuerySearchEngine()

        all_results = [
            {"id": "doc1:0", "score": 0.90, "_sub_query_id": 0, "_is_primary": True},
            {"id": "doc1:0", "score": 0.85, "_sub_query_id": 1, "_is_primary": False},
            {"id": "doc2:1", "score": 0.80, "_sub_query_id": 0, "_is_primary": False},
        ]

        decomposed = DecomposedQuery(
            original_query="test",
            sub_queries=[
                SubQuery(0, "q1", "i1", [], True),
                SubQuery(1, "q2", "i2", [], False),
            ],
            strategy=DecompositionStrategy.PARALLEL,
        )

        merged = engine._merge_subquery_results(
            all_results, top_k=3, decomposed=decomposed
        )

        # doc1:0 should have higher score than doc2:1 due to multi-match bonus
        doc1_score = next(r["score"] for r in merged if r["id"] == "doc1:0")
        doc2_score = next(r["score"] for r in merged if r["id"] == "doc2:1")
        assert doc1_score > doc2_score

    def test_clear_caches(self, mock_decomposer):
        """Test clearing all caches."""
        engine = MultiQuerySearchEngine(decomposer=mock_decomposer)
        engine._results_cache["key"] = []

        engine.clear_caches()

        mock_decomposer.clear_cache.assert_called_once()
        assert len(engine._results_cache) == 0


class TestDecompositionStrategies:
    """Test different decomposition strategies."""

    def test_single_strategy(self):
        """Test SINGLE strategy."""
        result = DecomposedQuery(
            original_query="test",
            sub_queries=[SubQuery(0, "q", "i", [], True)],
            strategy=DecompositionStrategy.SINGLE,
        )
        assert result.strategy == DecompositionStrategy.SINGLE

    def test_parallel_strategy(self):
        """Test PARALLEL strategy."""
        result = DecomposedQuery(
            original_query="test",
            sub_queries=[
                SubQuery(0, "q1", "i1", [], True),
                SubQuery(1, "q2", "i2", [], False),
            ],
            strategy=DecompositionStrategy.PARALLEL,
        )
        assert result.strategy == DecompositionStrategy.PARALLEL


class TestSubQueryStructure:
    """Test SubQuery data structure."""

    def test_subquery_creation(self):
        """Test SubQuery dataclass."""
        sq = SubQuery(
            id=1,
            query="What is ML?",
            intent="definition",
            keywords=["machine learning", "ML"],
            is_primary=True,
        )

        assert sq.id == 1
        assert sq.query == "What is ML?"
        assert sq.intent == "definition"
        assert "ML" in sq.keywords
        assert sq.is_primary is True


class TestDecompositionPerformance:
    """Performance tests for decomposition."""

    @pytest.mark.asyncio
    async def test_decomposition_latency(self):
        """Test that decomposition completes within acceptable time."""
        decomposer = QueryDecomposer()

        mock_response = Mock()
        mock_response.json.return_value = {
            "text": '{"sub_queries": [], "strategy": "single"}'
        }
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            import time

            start = time.time()
            await decomposer.decompose("Test query")
            elapsed = time.time() - start

            assert elapsed < 1.0  # Should complete within 1 second


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
