"""
Load Tests for Knowledge Base LLM

Tests cover:
- Search performance under load
- RAG query performance
- HyDE performance overhead
- Query decomposition performance
- Throughput and latency metrics
"""

import asyncio
import time
import statistics
from typing import List, Dict
from dataclasses import dataclass
import concurrent.futures
import random

# Try to import pytest, fallback to simple testing if not available
try:
    import pytest

    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False
    print("pytest not available, using simple test runner")


@dataclass
class PerformanceMetrics:
    """Performance test metrics."""

    operation: str
    requests: int
    total_time: float
    min_latency: float
    max_latency: float
    avg_latency: float
    p50_latency: float
    p95_latency: float
    p99_latency: float
    throughput: float  # requests per second

    def to_dict(self) -> Dict:
        return {
            "operation": self.operation,
            "requests": self.requests,
            "total_time_sec": round(self.total_time, 2),
            "min_latency_ms": round(self.min_latency * 1000, 2),
            "max_latency_ms": round(self.max_latency * 1000, 2),
            "avg_latency_ms": round(self.avg_latency * 1000, 2),
            "p50_latency_ms": round(self.p50_latency * 1000, 2),
            "p95_latency_ms": round(self.p95_latency * 1000, 2),
            "p99_latency_ms": round(self.p99_latency * 1000, 2),
            "throughput_rps": round(self.throughput, 2),
        }


class MockSearchClient:
    """Mock client for load testing without actual services."""

    def __init__(self, base_latency: float = 0.1):
        self.base_latency = base_latency

    async def search(self, query: str, **kwargs) -> Dict:
        """Simulate search with variable latency."""
        # Simulate latency with some randomness
        latency = self.base_latency * (0.8 + random.random() * 0.4)
        await asyncio.sleep(latency)
        return {"results": [], "time_ms": latency * 1000}

    async def search_hyde(self, query: str, **kwargs) -> Dict:
        """Simulate HyDE search (slower due to LLM call)."""
        # HyDE adds ~200-500ms for hypothetical document generation
        latency = self.base_latency + 0.3 + random.random() * 0.2
        await asyncio.sleep(latency)
        return {"results": [], "hyde_used": True, "time_ms": latency * 1000}

    async def search_decomposed(self, query: str, **kwargs) -> Dict:
        """Simulate query decomposition search (slower due to multiple queries)."""
        # Decomposition adds latency for LLM call + parallel searches
        latency = self.base_latency + 0.4 + random.random() * 0.3
        await asyncio.sleep(latency)
        return {"results": [], "decomposition_used": True, "time_ms": latency * 1000}


class LoadTester:
    """Load testing utility."""

    def __init__(self, client: MockSearchClient):
        self.client = client

    async def _run_single_request(self, operation: str, query: str) -> float:
        """Run a single request and return latency."""
        start = time.time()

        if operation == "search":
            await self.client.search(query)
        elif operation == "hyde":
            await self.client.search_hyde(query)
        elif operation == "decomposition":
            await self.client.search_decomposed(query)

        return time.time() - start

    async def run_load_test(
        self,
        operation: str,
        queries: List[str],
        concurrency: int = 10,
    ) -> PerformanceMetrics:
        """Run load test with specified concurrency."""
        print(f"\nRunning {operation} load test...")
        print(f"Requests: {len(queries)}, Concurrency: {concurrency}")

        start_time = time.time()
        latencies: List[float] = []

        semaphore = asyncio.Semaphore(concurrency)

        async def bounded_request(query: str):
            async with semaphore:
                latency = await self._run_single_request(operation, query)
                latencies.append(latency)

        # Run all requests
        tasks = [bounded_request(q) for q in queries]
        await asyncio.gather(*tasks)

        total_time = time.time() - start_time

        # Calculate metrics
        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)

        metrics = PerformanceMetrics(
            operation=operation,
            requests=len(queries),
            total_time=total_time,
            min_latency=min(latencies),
            max_latency=max(latencies),
            avg_latency=statistics.mean(latencies),
            p50_latency=sorted_latencies[int(n * 0.5)],
            p95_latency=sorted_latencies[int(n * 0.95)],
            p99_latency=sorted_latencies[int(n * 0.99)] if n >= 100 else max(latencies),
            throughput=len(queries) / total_time,
        )

        return metrics


def generate_test_queries(count: int) -> List[str]:
    """Generate test queries."""
    templates = [
        "What is {topic}?",
        "How does {topic} work?",
        "Explain {topic} in detail",
        "What are the benefits of {topic}?",
        "Compare {topic} and {topic2}",
        "Best practices for {topic}",
        "Common issues with {topic}",
        "How to implement {topic}",
    ]

    topics = [
        "machine learning",
        "deep learning",
        "neural networks",
        "natural language processing",
        "computer vision",
        "reinforcement learning",
        "supervised learning",
        "unsupervised learning",
        "transformers",
        "BERT",
        "GPT",
        "CNN",
        "RNN",
        "LSTM",
        "attention mechanism",
    ]

    queries = []
    for i in range(count):
        template = random.choice(templates)
        topic = random.choice(topics)
        topic2 = random.choice(topics)
        query = template.format(topic=topic, topic2=topic2)
        queries.append(query)

    return queries


async def run_all_load_tests():
    """Run comprehensive load tests."""
    print("=" * 80)
    print("KNOWLEDGE BASE LLM - LOAD TESTS")
    print("=" * 80)

    client = MockSearchClient(base_latency=0.1)
    tester = LoadTester(client)

    # Generate test queries
    queries = generate_test_queries(count=100)

    # Test 1: Basic Search
    search_metrics = await tester.run_load_test(
        operation="search",
        queries=queries,
        concurrency=10,
    )

    # Test 2: HyDE Search
    hyde_metrics = await tester.run_load_test(
        operation="hyde",
        queries=queries,
        concurrency=10,
    )

    # Test 3: Query Decomposition Search
    decomp_metrics = await tester.run_load_test(
        operation="decomposition",
        queries=queries,
        concurrency=5,  # Lower concurrency due to higher latency
    )

    # Print results
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)

    all_metrics = [search_metrics, hyde_metrics, decomp_metrics]

    for metrics in all_metrics:
        print(f"\n{metrics.operation.upper()}:")
        for key, value in metrics.to_dict().items():
            if key != "operation":
                print(f"  {key}: {value}")

    # Comparison
    print("\n" + "=" * 80)
    print("PERFORMANCE COMPARISON")
    print("=" * 80)

    print(f"\nHyDE Overhead:")
    hyde_overhead = ((hyde_metrics.avg_latency / search_metrics.avg_latency) - 1) * 100
    print(f"  {hyde_overhead:.1f}% slower than basic search")

    print(f"\nDecomposition Overhead:")
    decomp_overhead = (
        (decomp_metrics.avg_latency / search_metrics.avg_latency) - 1
    ) * 100
    print(f"  {decomp_overhead:.1f}% slower than basic search")

    print(f"\nThroughput Comparison:")
    print(f"  Basic Search:     {search_metrics.throughput:.1f} req/s")
    print(f"  HyDE Search:      {hyde_metrics.throughput:.1f} req/s")
    print(f"  Decomposition:    {decomp_metrics.throughput:.1f} req/s")

    # Performance thresholds
    print("\n" + "=" * 80)
    print("PERFORMANCE VALIDATION")
    print("=" * 80)

    passed = True

    # Check p95 latency thresholds
    if search_metrics.p95_latency > 0.5:  # 500ms
        print(
            f"❌ Basic search p95 latency too high: {search_metrics.p95_latency * 1000:.0f}ms"
        )
        passed = False
    else:
        print(
            f"✅ Basic search p95 latency OK: {search_metrics.p95_latency * 1000:.0f}ms"
        )

    if hyde_metrics.p95_latency > 1.0:  # 1000ms
        print(
            f"❌ HyDE search p95 latency too high: {hyde_metrics.p95_latency * 1000:.0f}ms"
        )
        passed = False
    else:
        print(f"✅ HyDE search p95 latency OK: {hyde_metrics.p95_latency * 1000:.0f}ms")

    if decomp_metrics.p95_latency > 1.5:  # 1500ms
        print(
            f"❌ Decomposition p95 latency too high: {decomp_metrics.p95_latency * 1000:.0f}ms"
        )
        passed = False
    else:
        print(
            f"✅ Decomposition p95 latency OK: {decomp_metrics.p95_latency * 1000:.0f}ms"
        )

    # Check throughput
    if search_metrics.throughput < 50:  # 50 req/s
        print(
            f"❌ Basic search throughput too low: {search_metrics.throughput:.1f} req/s"
        )
        passed = False
    else:
        print(f"✅ Basic search throughput OK: {search_metrics.throughput:.1f} req/s")

    print("\n" + "=" * 80)
    if passed:
        print("✅ ALL PERFORMANCE TESTS PASSED")
    else:
        print("❌ SOME PERFORMANCE TESTS FAILED")
    print("=" * 80)

    return all_metrics


# Pytest-compatible tests
if HAS_PYTEST:

    @pytest.mark.load
    class TestLoadBasicSearch:
        """Load tests for basic search."""

        @pytest.mark.asyncio
        async def test_search_throughput(self):
            """Test basic search throughput."""
            client = MockSearchClient(base_latency=0.1)
            tester = LoadTester(client)
            queries = generate_test_queries(50)

            metrics = await tester.run_load_test("search", queries, concurrency=10)

            assert metrics.throughput >= 50  # At least 50 req/s
            assert metrics.p95_latency <= 0.5  # P95 under 500ms

        @pytest.mark.asyncio
        async def test_search_concurrent_users(self):
            """Test search with many concurrent users."""
            client = MockSearchClient(base_latency=0.1)
            tester = LoadTester(client)
            queries = generate_test_queries(100)

            metrics = await tester.run_load_test("search", queries, concurrency=20)

            assert metrics.avg_latency <= 0.3  # Avg under 300ms

    @pytest.mark.load
    class TestLoadHyDE:
        """Load tests for HyDE search."""

        @pytest.mark.asyncio
        async def test_hyde_performance(self):
            """Test HyDE search performance."""
            client = MockSearchClient(base_latency=0.1)
            tester = LoadTester(client)
            queries = generate_test_queries(50)

            metrics = await tester.run_load_test("hyde", queries, concurrency=10)

            # HyDE should be slower but still reasonable
            assert metrics.throughput >= 20  # At least 20 req/s
            assert metrics.p95_latency <= 1.0  # P95 under 1000ms

        @pytest.mark.asyncio
        async def test_hyde_overhead(self):
            """Test HyDE overhead compared to basic search."""
            client = MockSearchClient(base_latency=0.1)
            tester = LoadTester(client)
            queries = generate_test_queries(30)

            basic_metrics = await tester.run_load_test("search", queries, concurrency=5)
            hyde_metrics = await tester.run_load_test("hyde", queries, concurrency=5)

            overhead = (
                (hyde_metrics.avg_latency / basic_metrics.avg_latency) - 1
            ) * 100
            assert overhead <= 300  # HyDE should be less than 300% slower

    @pytest.mark.load
    class TestLoadDecomposition:
        """Load tests for query decomposition."""

        @pytest.mark.asyncio
        async def test_decomposition_performance(self):
            """Test decomposition search performance."""
            client = MockSearchClient(base_latency=0.1)
            tester = LoadTester(client)
            queries = generate_test_queries(30)

            metrics = await tester.run_load_test(
                "decomposition", queries, concurrency=5
            )

            # Decomposition is slower but should still be acceptable
            assert metrics.throughput >= 10  # At least 10 req/s
            assert metrics.p95_latency <= 1.5  # P95 under 1500ms

    @pytest.mark.load
    class TestLoadStress:
        """Stress tests."""

        @pytest.mark.asyncio
        async def test_stress_search(self):
            """Stress test with high load."""
            client = MockSearchClient(base_latency=0.1)
            tester = LoadTester(client)
            queries = generate_test_queries(200)

            metrics = await tester.run_load_test("search", queries, concurrency=50)

            # Should handle high concurrency
            assert metrics.throughput >= 40
            assert metrics.p99_latency <= 2.0  # P99 under 2s even under stress


if __name__ == "__main__":
    if HAS_PYTEST:
        pytest.main([__file__, "-v", "-m", "load"])
    else:
        # Run without pytest
        asyncio.run(run_all_load_tests())
