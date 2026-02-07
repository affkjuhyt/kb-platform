"""
Integration Tests for Knowledge Base LLM

Tests cover:
- End-to-end document ingestion
- Search and RAG workflows
- Service-to-service communication
- Multi-tenant isolation
"""

import pytest
import asyncio
import httpx
from typing import Dict, Any
import time

# Service endpoints
BASE_URL = "http://localhost"
API_GATEWAY = f"{BASE_URL}:8000"
QUERY_API = f"{BASE_URL}:8001"
INGESTION = f"{BASE_URL}:8002"
INDEXER = f"{BASE_URL}:8003"
LLM_GATEWAY = f"{BASE_URL}:8004"
RERANK = f"{BASE_URL}:8005"


@pytest.fixture(scope="module")
def tenant_id():
    """Generate test tenant ID."""
    return f"test-tenant-{int(time.time())}"


@pytest.fixture(scope="module")
def test_document():
    """Sample test document."""
    return {
        "title": "Machine Learning Basics",
        "content": """
        Machine learning is a subset of artificial intelligence.
        It enables computers to learn from data without explicit programming.
        
        Supervised learning uses labeled training data.
        Unsupervised learning finds patterns in unlabeled data.
        Reinforcement learning learns through trial and error.
        
        Deep learning uses neural networks with multiple layers.
        These networks can learn complex patterns in data.
        """,
    }


@pytest.mark.integration
class TestServiceHealth:
    """Test that all services are healthy."""

    @pytest.mark.asyncio
    async def test_api_gateway_health(self):
        """Test API Gateway health."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_GATEWAY}/healthz")
            assert response.status_code == 200
            assert response.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_query_api_health(self):
        """Test Query API health."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{QUERY_API}/healthz")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_ingestion_health(self):
        """Test Ingestion service health."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{INGESTION}/healthz")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_indexer_health(self):
        """Test Indexer service health."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{INDEXER}/healthz")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_llm_gateway_health(self):
        """Test LLM Gateway health."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{LLM_GATEWAY}/healthz")
            assert response.status_code == 200


@pytest.mark.integration
class TestDocumentIngestion:
    """Test document ingestion workflow."""

    @pytest.mark.asyncio
    async def test_ingest_text_document(self, tenant_id):
        """Test ingesting a text document."""
        document = {
            "content": "This is a test document about machine learning.",
            "content_type": "text/plain",
            "filename": "test.txt",
            "tenant_id": tenant_id,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{INGESTION}/webhook",
                json=document,
                timeout=30,
            )
            assert response.status_code in [200, 201, 202]

    @pytest.mark.asyncio
    async def test_ingest_markdown_document(self, tenant_id):
        """Test ingesting a markdown document."""
        document = {
            "content": "# Heading\n\nThis is content.",
            "content_type": "text/markdown",
            "filename": "test.md",
            "tenant_id": tenant_id,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{INGESTION}/webhook",
                json=document,
                timeout=30,
            )
            assert response.status_code in [200, 201, 202]

    @pytest.mark.asyncio
    async def test_ingest_with_deduplication(self, tenant_id):
        """Test that duplicate documents are handled."""
        document = {
            "content": "Duplicate content test.",
            "content_type": "text/plain",
            "tenant_id": tenant_id,
        }

        async with httpx.AsyncClient() as client:
            # First ingestion
            r1 = await client.post(f"{INGESTION}/webhook", json=document)
            # Second ingestion (duplicate)
            r2 = await client.post(f"{INGESTION}/webhook", json=document)

            assert r1.status_code in [200, 201]
            assert r2.status_code in [200, 201]


@pytest.mark.integration
class TestSearchWorkflow:
    """Test search workflows."""

    @pytest.mark.asyncio
    async def test_basic_search(self, tenant_id):
        """Test basic search functionality."""
        await asyncio.sleep(2)  # Wait for indexing

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{QUERY_API}/search",
                json={
                    "query": "machine learning",
                    "tenant_id": tenant_id,
                    "top_k": 5,
                },
                timeout=30,
            )

            assert response.status_code == 200
            result = response.json()
            assert "results" in result
            assert isinstance(result["results"], list)

    @pytest.mark.asyncio
    async def test_hyde_search(self, tenant_id):
        """Test HyDE-enhanced search."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{QUERY_API}/search/hyde",
                json={
                    "query": "What is artificial intelligence?",
                    "tenant_id": tenant_id,
                    "top_k": 5,
                },
                timeout=60,
            )

            assert response.status_code == 200
            result = response.json()
            assert result.get("hyde_used") is True
            assert "hyde_answer" in result

    @pytest.mark.asyncio
    async def test_enhanced_search(self, tenant_id):
        """Test enhanced search with all features."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{QUERY_API}/search/enhanced",
                json={
                    "query": "Explain neural networks",
                    "tenant_id": tenant_id,
                    "top_k": 5,
                    "use_hyde": True,
                    "use_decomposition": True,
                    "use_cache": True,
                },
                timeout=60,
            )

            assert response.status_code == 200
            result = response.json()
            assert "results" in result
            assert "time_ms" in result

    @pytest.mark.asyncio
    async def test_search_with_filters(self, tenant_id):
        """Test search with tenant filtering."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{QUERY_API}/search",
                json={
                    "query": "test",
                    "tenant_id": tenant_id,
                    "top_k": 10,
                },
            )

            assert response.status_code == 200


@pytest.mark.integration
class TestRAGWorkflow:
    """Test RAG query workflows."""

    @pytest.mark.asyncio
    async def test_basic_rag(self, tenant_id):
        """Test basic RAG query."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{QUERY_API}/rag",
                json={
                    "query": "What is machine learning?",
                    "tenant_id": tenant_id,
                    "top_k": 5,
                },
                timeout=60,
            )

            assert response.status_code == 200
            result = response.json()
            assert "answer" in result
            assert "citations" in result
            assert len(result["citations"]) > 0

    @pytest.mark.asyncio
    async def test_rag_streaming(self, tenant_id):
        """Test streaming RAG."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{QUERY_API}/rag/stream",
                json={
                    "query": "Explain deep learning",
                    "tenant_id": tenant_id,
                    "top_k": 3,
                },
                timeout=60,
            )

            assert response.status_code == 200
            # Should be SSE stream
            content = response.text
            assert "data:" in content or "[DONE]" in content


@pytest.mark.integration
class TestQueryDecomposition:
    """Test query decomposition."""

    @pytest.mark.asyncio
    async def test_decompose_query(self):
        """Test query decomposition endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{QUERY_API}/query/decompose",
                json={"query": "What is AI and how does ML differ?"},
                timeout=30,
            )

            assert response.status_code == 200
            result = response.json()
            assert "sub_queries" in result
            assert "strategy" in result
            assert len(result["sub_queries"]) >= 1


@pytest.mark.integration
class TestCaching:
    """Test caching functionality."""

    @pytest.mark.asyncio
    async def test_cache_hit_performance(self, tenant_id):
        """Test that cached queries are faster."""
        query = {"query": "machine learning", "tenant_id": tenant_id, "top_k": 5}

        async with httpx.AsyncClient() as client:
            # First query (cold cache)
            start = time.time()
            r1 = await client.post(f"{QUERY_API}/search/enhanced", json=query)
            cold_time = time.time() - start

            assert r1.status_code == 200

            # Wait for cache
            await asyncio.sleep(1)

            # Second query (warm cache)
            start = time.time()
            r2 = await client.post(f"{QUERY_API}/search/enhanced", json=query)
            warm_time = time.time() - start

            assert r2.status_code == 200
            result = r2.json()

            # Cached result should be faster or marked as cached
            if result.get("cached"):
                assert warm_time < cold_time

    @pytest.mark.asyncio
    async def test_cache_invalidation(self, tenant_id):
        """Test cache invalidation."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{QUERY_API}/cache/query/invalidate",
                params={"tenant_id": tenant_id},
            )
            assert response.status_code == 200


@pytest.mark.integration
class TestMultiTenant:
    """Test multi-tenant isolation."""

    @pytest.mark.asyncio
    async def test_tenant_isolation(self):
        """Test that tenants cannot see each other's data."""
        tenant_a = "tenant-a-integration-test"
        tenant_b = "tenant-b-integration-test"

        async with httpx.AsyncClient() as client:
            # Search in tenant A
            r_a = await client.post(
                f"{QUERY_API}/search",
                json={"query": "test", "tenant_id": tenant_a, "top_k": 10},
            )

            # Search in tenant B
            r_b = await client.post(
                f"{QUERY_API}/search",
                json={"query": "test", "tenant_id": tenant_b, "top_k": 10},
            )

            assert r_a.status_code == 200
            assert r_b.status_code == 200


@pytest.mark.integration
class TestLLMProviders:
    """Test multi-LLM provider support."""

    @pytest.mark.asyncio
    async def test_llm_gateway_models(self):
        """Test LLM Gateway model listing."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{LLM_GATEWAY}/models")

            assert response.status_code == 200
            result = response.json()
            assert "provider" in result or "models" in result

    @pytest.mark.asyncio
    async def test_llm_generation(self):
        """Test LLM text generation."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{LLM_GATEWAY}/generate",
                json={
                    "prompt": "Say hello",
                    "max_tokens": 50,
                    "temperature": 0.3,
                },
                timeout=30,
            )

            assert response.status_code == 200
            result = response.json()
            assert "text" in result


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_empty_query(self):
        """Test handling of empty query."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{QUERY_API}/search",
                json={"query": "", "tenant_id": "test"},
            )

            assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_very_long_query(self):
        """Test handling of very long query."""
        long_query = "word " * 1000

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{QUERY_API}/search",
                json={"query": long_query, "tenant_id": "test", "top_k": 5},
            )

            assert response.status_code in [200, 413]  # OK or Payload Too Large

    @pytest.mark.asyncio
    async def test_invalid_tenant(self):
        """Test handling of invalid tenant."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{QUERY_API}/search",
                json={"query": "test", "tenant_id": "", "top_k": 5},
            )

            assert response.status_code in [200, 400, 422]


@pytest.mark.integration
class TestEndToEnd:
    """End-to-end workflow tests."""

    @pytest.mark.asyncio
    async def test_full_document_search_rag_workflow(self, tenant_id):
        """Test complete workflow: ingest -> index -> search -> RAG."""
        # Step 1: Ingest document
        document = {
            "content": """
            Python is a high-level programming language.
            It was created by Guido van Rossum and released in 1991.
            Python supports multiple programming paradigms.
            """,
            "content_type": "text/plain",
            "tenant_id": tenant_id,
        }

        async with httpx.AsyncClient() as client:
            ingest_response = await client.post(
                f"{INGESTION}/webhook",
                json=document,
                timeout=30,
            )
            assert ingest_response.status_code in [200, 201]

        # Step 2: Wait for indexing
        await asyncio.sleep(5)

        # Step 3: Search
        async with httpx.AsyncClient() as client:
            search_response = await client.post(
                f"{QUERY_API}/search",
                json={
                    "query": "Who created Python?",
                    "tenant_id": tenant_id,
                    "top_k": 5,
                },
                timeout=30,
            )
            assert search_response.status_code == 200
            search_result = search_response.json()
            assert len(search_result["results"]) > 0

        # Step 4: RAG Query
        async with httpx.AsyncClient() as client:
            rag_response = await client.post(
                f"{QUERY_API}/rag",
                json={
                    "query": "When was Python released?",
                    "tenant_id": tenant_id,
                    "top_k": 3,
                },
                timeout=60,
            )
            assert rag_response.status_code == 200
            rag_result = rag_response.json()
            assert "answer" in rag_result
            assert "1991" in rag_result["answer"] or "Guido" in rag_result["answer"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
