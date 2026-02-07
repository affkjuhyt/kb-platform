"""
Unit Tests for HyDE (Hypothetical Document Embeddings) Module

Tests cover:
- HyDE generation
- Embedding hypothetical documents
- Search integration
- Caching behavior
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import List

import sys

sys.path.insert(0, "/Users/thiennlinh/Documents/New project/services/query-api")

from hyde import (
    HyDEGenerator,
    HyDEEmbedder,
    HyDESearchEngine,
    HypotheticalDocument,
)


class TestHyDEGenerator:
    """Test HyDE document generation."""

    @pytest.fixture
    def generator(self):
        return HyDEGenerator(
            llm_gateway_url="http://localhost:8004",
            max_length=200,
            temperature=0.3,
        )

    @pytest.mark.asyncio
    async def test_generate_hypothetical_success(self, generator):
        """Test successful hypothetical document generation."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "text": "This is a hypothetical answer about machine learning."
        }
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            doc = await generator.generate_hypothetical("What is machine learning?")

        assert isinstance(doc, HypotheticalDocument)
        assert doc.query == "What is machine learning?"
        assert "machine learning" in doc.hypothetical_answer.lower()
        assert doc.embedding == []

    @pytest.mark.asyncio
    async def test_generate_hypothetical_cache_hit(self, generator):
        """Test cache hit returns cached document."""
        cached_doc = HypotheticalDocument(
            query="test query",
            hypothetical_answer="cached answer",
            embedding=[],
        )
        generator._hyde_cache["test_hash"] = cached_doc

        with patch.object(generator, "_generate_hyde_prompt", return_value="prompt"):
            with patch("hashlib.md5") as mock_hash:
                mock_hash.return_value.hexdigest.return_value = "test_hash"
                doc = await generator.generate_hypothetical("test query")

        assert doc == cached_doc

    @pytest.mark.asyncio
    async def test_generate_hypothetical_failure_fallback(self, generator):
        """Test graceful fallback on LLM failure."""
        with patch("httpx.AsyncClient.post", side_effect=Exception("LLM Error")):
            doc = await generator.generate_hypothetical("What is AI?")

        assert isinstance(doc, HypotheticalDocument)
        assert doc.hypothetical_answer == "Answer about What is AI?"

    def test_generate_hyde_prompt(self, generator):
        """Test prompt generation includes query and constraints."""
        prompt = generator._generate_hyde_prompt("Test query")

        assert "Test query" in prompt
        assert "200" in prompt  # max_length
        assert "hypothetical answer" in prompt.lower()

    def test_clear_cache(self, generator):
        """Test cache clearing."""
        generator._hyde_cache["key"] = Mock()
        generator.clear_cache()
        assert len(generator._hyde_cache) == 0


class TestHyDEEmbedder:
    """Test HyDE embedding functionality."""

    @pytest.fixture
    def mock_embedder(self):
        mock = Mock()
        mock.embed.return_value = [[0.1, 0.2, 0.3]]
        return mock

    @pytest.fixture
    def hyde_embedder(self, mock_embedder):
        return HyDEEmbedder(embedder=mock_embedder)

    def test_embed_hypothetical(self, hyde_embedder, mock_embedder):
        """Test embedding a hypothetical document."""
        hyp_doc = HypotheticalDocument(
            query="test",
            hypothetical_answer="This is a test answer",
            embedding=[],
        )

        embedding = hyde_embedder.embed_hypothetical(hyp_doc)

        assert embedding == [0.1, 0.2, 0.3]
        mock_embedder.embed.assert_called_once_with(["This is a test answer"])

    def test_embed_hypothetical_cache_hit(self, hyde_embedder):
        """Test embedding cache hit."""
        hyp_doc = HypotheticalDocument(
            query="test",
            hypothetical_answer="cached text",
            embedding=[],
        )

        # Pre-populate cache
        hyde_embedder._embedding_cache["cache_key"] = [0.9, 0.8, 0.7]

        with patch("hashlib.md5") as mock_hash:
            mock_hash.return_value.hexdigest.return_value = "cache_key"
            embedding = hyde_embedder.embed_hypothetical(hyp_doc)

        assert embedding == [0.9, 0.8, 0.7]

    def test_embed_query_direct(self, hyde_embedder, mock_embedder):
        """Test direct query embedding without hypothetical."""
        embedding = hyde_embedder.embed_query("direct query")

        assert embedding == [0.1, 0.2, 0.3]
        mock_embedder.embed.assert_called_once_with(["direct query"])

    def test_clear_caches(self, hyde_embedder):
        """Test clearing embedding caches."""
        hyde_embedder._embedding_cache["key"] = [0.1, 0.2]
        hyde_embedder.clear_cache()
        assert len(hyde_embedder._embedding_cache) == 0


class TestHyDESearchEngine:
    """Test HyDE search integration."""

    @pytest.fixture
    def mock_stores(self):
        qdrant = Mock()
        qdrant.search.return_value = [
            Mock(payload={"doc_id": "doc1", "chunk_index": 0}, score=0.95),
            Mock(payload={"doc_id": "doc2", "chunk_index": 1}, score=0.90),
        ]

        opensearch = Mock()
        opensearch.bm25_search.return_value = {
            "hits": {
                "hits": [
                    {"_source": {"doc_id": "doc1", "chunk_index": 0}, "_score": 0.85},
                ]
            }
        }

        return qdrant, opensearch

    @pytest.fixture
    def mock_hyde_components(self):
        generator = Mock()
        generator.generate_hypothetical = AsyncMock(
            return_value=Mock(
                query="test",
                hypothetical_answer="hypothetical",
                embedding=[],
            )
        )

        embedder = Mock()
        embedder.embed_query.return_value = [0.1, 0.2, 0.3]

        return generator, embedder

    @pytest.mark.asyncio
    async def test_search_with_hyde(self, mock_stores, mock_hyde_components):
        """Test search with HyDE enabled."""
        qdrant, opensearch = mock_stores
        generator, embedder = mock_hyde_components

        engine = HyDESearchEngine(
            hyde_generator=generator,
            hyde_embedder=embedder,
            qdrant_store=qdrant,
            opensearch_store=opensearch,
        )

        results, hyp_doc = await engine.search(
            query="What is AI?",
            tenant_id="tenant-1",
            top_k=5,
            use_hyde=True,
        )

        assert len(results) > 0
        assert hyp_doc is not None
        generator.generate_hypothetical.assert_called_once()
        embedder.embed_query.assert_called_once()
        qdrant.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_without_hyde(self, mock_stores, mock_hyde_components):
        """Test search without HyDE (normal search)."""
        qdrant, opensearch = mock_stores
        generator, embedder = mock_hyde_components

        engine = HyDESearchEngine(
            hyde_generator=generator,
            hyde_embedder=embedder,
            qdrant_store=qdrant,
            opensearch_store=opensearch,
        )

        results, hyp_doc = await engine.search(
            query="What is AI?",
            use_hyde=False,
        )

        assert len(results) > 0
        assert hyp_doc is None
        generator.generate_hypothetical.assert_not_called()

    def test_merge_results(self, mock_stores):
        """Test result merging from vector and BM25."""
        qdrant, opensearch = mock_stores

        engine = HyDESearchEngine(
            qdrant_store=qdrant,
            opensearch_store=opensearch,
        )

        vector_results = [
            Mock(payload={"doc_id": "doc1", "chunk_index": 0}, score=0.95),
        ]
        bm25_results = {
            "hits": {
                "hits": [
                    {"_source": {"doc_id": "doc1", "chunk_index": 0}, "_score": 0.85},
                    {"_source": {"doc_id": "doc2", "chunk_index": 1}, "_score": 0.80},
                ]
            }
        }

        merged = engine._merge_results(vector_results, bm25_results, top_k=3)

        assert len(merged) > 0
        assert all("id" in r and "score" in r for r in merged)

    def test_clear_caches(self, mock_hyde_components):
        """Test clearing all caches."""
        generator, embedder = mock_hyde_components

        engine = HyDESearchEngine(
            hyde_generator=generator,
            hyde_embedder=embedder,
        )

        engine.clear_caches()

        generator.clear_cache.assert_called_once()
        embedder.clear_cache.assert_called_once()


class TestHyDEIntegration:
    """Integration tests for HyDE workflow."""

    @pytest.mark.asyncio
    async def test_end_to_end_hyde_workflow(self):
        """Test complete HyDE workflow from query to results."""
        # This would test the complete flow with mocked external services
        pass

    @pytest.mark.asyncio
    async def test_hyde_performance_vs_baseline(self):
        """Compare HyDE search performance vs regular search."""
        # Would measure latency and quality metrics
        pass


class TestHyDEEmbeddingCaching:
    """Test embedding caching behavior."""

    def test_cache_key_consistency(self):
        """Test that same text produces same cache key."""
        embedder = HyDEEmbedder()

        hyp_doc1 = HypotheticalDocument(
            query="q1",
            hypothetical_answer="same text",
            embedding=[],
        )
        hyp_doc2 = HypotheticalDocument(
            query="q2",
            hypothetical_answer="same text",
            embedding=[],
        )

        with patch.object(embedder, "_get_embedder") as mock_get:
            mock_embedder = Mock()
            mock_embedder.embed.return_value = [[1.0, 2.0]]
            mock_get.return_value = mock_embedder

            # First call
            embedder.embed_hypothetical(hyp_doc1)
            # Second call with same text should use cache
            embedder.embed_hypothetical(hyp_doc2)

            # Should only call embed once due to caching
            assert mock_embedder.embed.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
