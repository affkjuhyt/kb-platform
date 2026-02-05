"""
End-to-End Pipeline Tests for RAG Platform
Test toàn bộ luồng: Ingestion → Indexing → Search → RAG
"""

import pytest
import httpx
import asyncio
import uuid
from datetime import datetime
import time

# Service URLs
GATEWAY_URL = "http://localhost:8080"  # Nginx API Gateway
INGESTION_URL = "http://localhost:8001"
INDEXER_URL = "http://localhost:8002"
QUERY_URL = "http://localhost:8003"
LLM_URL = "http://localhost:8004"
RERANK_URL = "http://localhost:8005"

# Optional services (không bắt buộc cho core pipeline)
OPTIONAL_SERVICES = {"llm", "rerank"}


class TestPipeline:
    """Test toàn bộ pipeline end-to-end"""

    @pytest.fixture
    async def client(self):
        """Async HTTP client"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            yield client

    @pytest.fixture
    def test_tenant(self):
        """Generate unique tenant ID cho mỗi test"""
        return f"test-tenant-{uuid.uuid4().hex[:8]}"

    @pytest.mark.asyncio
    async def test_health_all_services(self, client):
        """Test 1: Tất cả services đều healthy"""
        services = {
            "gateway": f"{GATEWAY_URL}/health",
            "ingestion": f"{INGESTION_URL}/healthz",
            "indexer": f"{INDEXER_URL}/healthz",
            "query": f"{QUERY_URL}/healthz",
            "llm": f"{LLM_URL}/healthz",
            "rerank": f"{RERANK_URL}/healthz",
        }

        results = {}
        for name, url in services.items():
            try:
                resp = await client.get(url)
                results[name] = resp.status_code == 200
                print(f"  ✓ {name}: {resp.status_code}")
            except Exception as e:
                results[name] = False
                print(f"  ✗ {name}: {e}")

        failed = [k for k, v in results.items() if not v]
        assert not failed, f"Services failed health check: {failed}"

    @pytest.mark.asyncio
    async def test_full_document_pipeline(self, client, test_tenant):
        """Test 2: Full flow - Ingest → Index → Search → RAG"""
        print(f"\n🏃 Test Pipeline cho tenant: {test_tenant}")

        # Step 1: Ingest document
        print("  Step 1: Ingesting document...")
        doc_content = f"""
        # Test Document - {test_tenant}
        
        ## Giới thiệu
        Đây là tài liệu test cho hệ thống RAG.
        Nội dung này sẽ được index và searchable.
        
        ## Thông tin quan trọng
        - Tenant: {test_tenant}
        - Created: {datetime.now().isoformat()}
        - Type: Test Document
        
        ## Nội dung mẫu
        Hệ thống RAG (Retrieval-Augmented Generation) kết hợp 
        retrieval và generation để tạo câu trả lởi chính xác.
        """

        ingest_payload = {
            "content": doc_content,
            "metadata": {
                "tenant_id": test_tenant,
                "title": f"Test Doc - {test_tenant}",
                "source": "e2e-test",
                "doc_type": "text",
            },
        }

        try:
            resp = await client.post(
                f"{INGESTION_URL}/webhook",
                json=ingest_payload,
                headers={"X-Tenant-ID": test_tenant},
            )
            assert resp.status_code == 202, f"Ingest failed: {resp.text}"
            doc_id = resp.json().get("document_id")
            print(f"  ✓ Document ingested: {doc_id}")
        except Exception as e:
            pytest.fail(f"Ingestion failed: {e}")

        # Step 2: Wait cho indexing (đơn giản hóa - sleep)
        print("  Step 2: Waiting for indexing...")
        await asyncio.sleep(2)

        # Step 3: Search
        print("  Step 3: Testing search...")
        search_payload = {
            "query": f"RAG tenant {test_tenant}",
            "top_k": 5,
            "filters": {"tenant_id": test_tenant},
        }

        try:
            resp = await client.post(
                f"{QUERY_URL}/search",
                json=search_payload,
                headers={"X-Tenant-ID": test_tenant},
            )
            assert resp.status_code == 200, f"Search failed: {resp.text}"
            results = resp.json()
            assert len(results.get("results", [])) > 0, "No search results"
            print(f"  ✓ Search returned {len(results['results'])} results")
        except Exception as e:
            pytest.fail(f"Search failed: {e}")

        # Step 4: RAG Query
        print("  Step 4: Testing RAG...")
        rag_payload = {"query": f"What is RAG and tenant {test_tenant}?", "top_k": 3}

        try:
            resp = await client.post(
                f"{QUERY_URL}/rag",
                json=rag_payload,
                headers={"X-Tenant-ID": test_tenant},
            )
            assert resp.status_code == 200, f"RAG failed: {resp.text}"
            result = resp.json()
            assert "answer" in result, "No answer in RAG response"
            assert "citations" in result, "No citations in RAG response"
            print(
                f"  ✓ RAG returned answer with {len(result.get('citations', []))} citations"
            )
        except Exception as e:
            pytest.fail(f"RAG failed: {e}")

        print(f"  ✅ Pipeline test passed for {test_tenant}")

    @pytest.mark.asyncio
    async def test_extraction_pipeline(self, client, test_tenant):
        """Test 3: Structured data extraction"""
        print(f"\n🔍 Test Extraction cho tenant: {test_tenant}")

        # Ingest document có structured data
        doc_content = f"""
        Hợp đồng số: HD-{test_tenant}-001
        Ngày ký: 2024-01-15
        Bên A: Công ty ABC
        Bên B: Công ty XYZ
        Giá trị: 1.000.000.000 VNĐ
        Thờ hạn: 12 tháng
        """

        ingest_payload = {
            "content": doc_content,
            "metadata": {
                "tenant_id": test_tenant,
                "title": f"Contract {test_tenant}",
                "source": "e2e-test",
            },
        }

        await client.post(
            f"{INGESTION_URL}/webhook",
            json=ingest_payload,
            headers={"X-Tenant-ID": test_tenant},
        )

        await asyncio.sleep(2)

        # Extract structured data
        extract_payload = {
            "query": "Trích xuất thông tin hợp đồng",
            "schema": {
                "contract_number": {"type": "string"},
                "date": {"type": "string"},
                "party_a": {"type": "string"},
                "party_b": {"type": "string"},
                "value": {"type": "string"},
                "duration": {"type": "string"},
            },
        }

        resp = await client.post(
            f"{QUERY_URL}/extract",
            json=extract_payload,
            headers={"X-Tenant-ID": test_tenant},
        )

        assert resp.status_code == 200
        result = resp.json()
        assert "data" in result
        print(f"  ✓ Extracted data: {result['data']}")

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, client):
        """Test 4: Tenant isolation - data không leak giữa tenants"""
        print("\n🔒 Test Tenant Isolation")

        tenant_a = f"tenant-a-{uuid.uuid4().hex[:8]}"
        tenant_b = f"tenant-b-{uuid.uuid4().hex[:8]}"

        # Tenant A ingest
        await client.post(
            f"{INGESTION_URL}/webhook",
            json={
                "content": f"Secret data for {tenant_a}",
                "metadata": {"tenant_id": tenant_a, "title": "Secret A"},
            },
            headers={"X-Tenant-ID": tenant_a},
        )

        # Tenant B ingest
        await client.post(
            f"{INGESTION_URL}/webhook",
            json={
                "content": f"Secret data for {tenant_b}",
                "metadata": {"tenant_id": tenant_b, "title": "Secret B"},
            },
            headers={"X-Tenant-ID": tenant_b},
        )

        await asyncio.sleep(2)

        # Tenant A search - chỉ thấy data của A
        resp_a = await client.post(
            f"{QUERY_URL}/search",
            json={"query": "Secret data", "top_k": 10},
            headers={"X-Tenant-ID": tenant_a},
        )

        results_a = resp_a.json().get("results", [])
        for r in results_a:
            assert tenant_b not in str(r), f"Tenant A thấy data của Tenant B!"

        # Tenant B search - chỉ thấy data của B
        resp_b = await client.post(
            f"{QUERY_URL}/search",
            json={"query": "Secret data", "top_k": 10},
            headers={"X-Tenant-ID": tenant_b},
        )

        results_b = resp_b.json().get("results", [])
        for r in results_b:
            assert tenant_a not in str(r), f"Tenant B thấy data của Tenant A!"

        print(f"  ✓ Tenant isolation verified")


class TestAPI:
    """Quick API tests cho development"""

    @pytest.mark.asyncio
    async def test_all_endpoints_available(self):
        """Smoke test - tất cả endpoints đều response"""
        async with httpx.AsyncClient(timeout=5.0) as client:
            tests = [
                ("GET", f"{GATEWAY_URL}/health"),
                ("GET", f"{INGESTION_URL}/healthz"),
                ("POST", f"{INGESTION_URL}/webhook"),
                ("GET", f"{QUERY_URL}/healthz"),
                ("POST", f"{QUERY_URL}/search"),
                ("GET", f"{LLM_URL}/healthz"),
                ("GET", f"{RERANK_URL}/healthz"),
            ]

            for method, url in tests:
                try:
                    if method == "GET":
                        resp = await client.get(url)
                    else:
                        resp = await client.post(url, json={})
                    # Chấp nhận cả 200 và 400 (validation error)
                    assert resp.status_code in [200, 400, 401, 403, 422]
                    print(f"  ✓ {method} {url}")
                except Exception as e:
                    pytest.fail(f"{method} {url} failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
