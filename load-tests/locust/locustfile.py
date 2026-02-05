"""
Locust load testing script for RAG System

Usage:
    locust -f locustfile.py --host=http://localhost:8000

Then open http://localhost:8089 to start the test.
"""

from locust import HttpUser, task, between, events
from locust.runners import MasterRunner
import random
import json
import time
from typing import List


class RAGUser(HttpUser):
    """Simulated user interacting with RAG system."""

    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks

    # Configuration
    api_key = "test-api-key"
    tenant_id = "test-tenant"

    # Test data
    search_queries: List[str] = [
        "machine learning",
        "deep learning",
        "neural networks",
        "natural language processing",
        "artificial intelligence",
        "data science",
        "big data",
        "cloud computing",
        "docker",
        "kubernetes",
        "python programming",
        "software engineering",
        "devops",
        "ci/cd",
        "microservices",
    ]

    rag_questions: List[str] = [
        "What is machine learning?",
        "How does deep learning work?",
        "What are neural networks?",
        "Explain natural language processing",
        "What is artificial intelligence?",
        "How to deploy a model?",
        "What are the best practices for security?",
        "How to optimize performance?",
        "What is the architecture?",
        "How to handle errors?",
    ]

    def on_start(self):
        """Called when a user starts."""
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "X-Tenant-ID": self.tenant_id,
        }

    @task(5)
    def search_documents(self):
        """Simulate document search."""
        query = random.choice(self.search_queries)

        start_time = time.time()
        with self.client.post(
            "/query/search",
            json={
                "query": query,
                "tenant_id": self.tenant_id,
                "top_k": 5,
            },
            headers=self.headers,
            catch_response=True,
            name="search",
        ) as response:
            duration = (time.time() - start_time) * 1000  # ms

            if response.status_code == 200:
                data = response.json()
                if data.get("results"):
                    response.success()
                else:
                    response.failure("No results returned")
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(3)
    def rag_query(self):
        """Simulate RAG query."""
        question = random.choice(self.rag_questions)

        start_time = time.time()
        with self.client.post(
            "/query/rag",
            json={
                "query": question,
                "tenant_id": self.tenant_id,
                "top_k": 5,
            },
            headers=self.headers,
            catch_response=True,
            name="rag_query",
        ) as response:
            duration = (time.time() - start_time) * 1000  # ms

            if response.status_code == 200:
                data = response.json()
                if data.get("answer"):
                    response.success()
                else:
                    response.failure("No answer returned")
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(1)
    def extract_data(self):
        """Simulate data extraction."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "value": {"type": "number"}},
        }

        with self.client.post(
            "/query/extract",
            json={
                "query": "Extract information",
                "tenant_id": self.tenant_id,
                "schema": schema,
                "top_k": 3,
            },
            headers=self.headers,
            catch_response=True,
            name="extract",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(2)
    def health_check(self):
        """Simulate health check."""
        self.client.get("/health", name="health")


class HeavyUser(HttpUser):
    """Heavy user making rapid requests."""

    wait_time = between(0.1, 0.5)  # Very short wait
    weight = 1  # 1 in 10 users will be heavy users

    api_key = "test-api-key"
    tenant_id = "test-tenant"

    def on_start(self):
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "X-Tenant-ID": self.tenant_id,
        }

    @task
    def rapid_search(self):
        """Rapid search requests."""
        queries = ["test", "query", "search"]
        query = random.choice(queries)

        with self.client.post(
            "/query/search",
            json={
                "query": query,
                "tenant_id": self.tenant_id,
                "top_k": 3,
            },
            headers=self.headers,
            catch_response=True,
            name="rapid_search",
        ) as response:
            if response.status_code == 429:  # Rate limited
                response.success()  # Expected behavior
            elif response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")


# Event hooks
@events.request.add_listener
def on_request(
    request_type,
    name,
    response_time,
    response_length,
    response,
    context,
    exception,
    **kwargs,
):
    """Log slow requests."""
    if response_time > 2100:  # 2.1s threshold
        print(f"⚠ Slow request: {name} took {response_time}ms")


@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """Print summary on exit."""
    if isinstance(environment.runner, MasterRunner):
        stats = environment.runner.stats

        print("\n" + "=" * 70)
        print("LOAD TEST SUMMARY")
        print("=" * 70)

        for name in stats.entries.keys():
            entry = stats.entries[name]
            p95 = entry.get_response_time_percentile(0.95)

            print(f"\n{name}:")
            print(f"  Requests: {entry.num_requests}")
            print(f"  Failures: {entry.num_failures}")
            print(f"  p95 Latency: {p95:.0f}ms")
            print(f"  Avg Latency: {entry.avg_response_time:.0f}ms")

            if p95 > 2100:
                print(f"  ⚠ EXCEEDS THRESHOLD (2100ms)")
            else:
                print(f"  ✓ Within threshold")

        print("\n" + "=" * 70)
