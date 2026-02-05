"""
Pytest configuration cho E2E tests
"""

import pytest
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def base_urls():
    """Return base URLs for all services"""
    return {
        "gateway": "http://localhost:8000",
        "ingestion": "http://localhost:8001",
        "indexer": "http://localhost:8002",
        "query": "http://localhost:8003",
        "llm": "http://localhost:8004",
        "rerank": "http://localhost:8005",
    }


# Skip markers cho tests chậm
def pytest_addoption(parser):
    parser.addoption(
        "--run-slow", action="store_true", default=False, help="run slow tests"
    )


# Fixture để check slow option
@pytest.fixture
def run_slow(request):
    return request.config.getoption("--run-slow")
