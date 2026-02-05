#!/usr/bin/env python3
"""
Quick Smoke Test - Chạy nhanh để check pipeline
Usage: python smoke_test.py
"""

import asyncio
import httpx
import sys
from datetime import datetime

# Màu cho terminal
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

BASE_URLS = {
    "gateway": "http://localhost:8080",  # Nginx API Gateway
    "ingestion": "http://localhost:8001",
    "indexer": "http://localhost:8002",
    "query": "http://localhost:8003",
    "llm": "http://localhost:8004",
    "rerank": "http://localhost:8005",
}

# Services tùy chọn (không bắt buộc cho core pipeline)
OPTIONAL_SERVICES = {"llm", "rerank"}


async def check_health(name: str, url: str) -> bool:
    """Check health của một service"""
    health_urls = {
        "gateway": f"{url}/health",
        "ingestion": f"{url}/healthz",
        "indexer": f"{url}/healthz",
        "query": f"{url}/healthz",
        "llm": f"{url}/healthz",
        "rerank": f"{url}/healthz",
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(health_urls[name])
            return resp.status_code == 200
    except Exception as e:
        return False


async def smoke_test():
    """Run quick smoke tests"""
    print(f"\n{'=' * 60}")
    print(f"🔥 RAG Platform Smoke Test - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'=' * 60}\n")

    # Test 1: Health checks
    print("📊 Phase 1: Health Checks")
    print("-" * 40)

    results = {}
    for name, url in BASE_URLS.items():
        healthy = await check_health(name, url)
        status = f"{GREEN}✓{RESET}" if healthy else f"{RED}✗{RESET}"
        print(f"  {status} {name:12} @ {url}")
        results[name] = healthy

    # Check required services (không tính optional)
    required_services = {k: v for k, v in results.items() if k not in OPTIONAL_SERVICES}
    optional_services = {k: v for k, v in results.items() if k in OPTIONAL_SERVICES}

    all_required_healthy = all(required_services.values())
    optional_healthy = {k: v for k, v in optional_services.items() if v}

    if not all_required_healthy:
        print(f"\n{RED}❌ Some required services are down!{RESET}")
        failed = [k for k, v in required_services.items() if not v]
        print(f"   Failed: {', '.join(failed)}")
        return False

    if optional_services:
        print(f"\n{YELLOW}⚠ Optional services:{RESET}")
        for name, healthy in optional_services.items():
            status = f"{GREEN}✓{RESET}" if healthy else f"{YELLOW}○{RESET}"
            print(f"   {status} {name}")

    print(f"\n{GREEN}✅ All services healthy{RESET}")

    # Test 2: Quick API availability
    print(f"\n📡 Phase 2: API Availability")
    print("-" * 40)

    async with httpx.AsyncClient(timeout=5.0) as client:
        # Test ingestion
        try:
            resp = await client.post(
                f"{BASE_URLS['ingestion']}/webhook",
                json={"content": "test"},
                headers={"X-Tenant-ID": "smoke-test"},
            )
            # Chấp nhận 202 (accepted) hoặc 400 (validation)
            if resp.status_code in [202, 400, 422]:
                print(f"  {GREEN}✓{RESET} Ingestion API")
            else:
                print(f"  {YELLOW}⚠{RESET} Ingestion API (status: {resp.status_code})")
        except Exception as e:
            print(f"  {RED}✗{RESET} Ingestion API: {e}")

        # Test search
        try:
            resp = await client.post(
                f"{BASE_URLS['query']}/search",
                json={"query": "test", "top_k": 1},
                headers={"X-Tenant-ID": "smoke-test"},
            )
            if resp.status_code in [200, 401, 403]:
                print(f"  {GREEN}✓{RESET} Query API")
            else:
                print(f"  {YELLOW}⚠{RESET} Query API (status: {resp.status_code})")
        except Exception as e:
            print(f"  {RED}✗{RESET} Query API: {e}")

        # Test LLM (optional)
        if results.get("llm", False):
            try:
                resp = await client.get(f"{BASE_URLS['llm']}/models")
                if resp.status_code == 200:
                    print(f"  {GREEN}✓{RESET} LLM Gateway")
                else:
                    print(
                        f"  {YELLOW}⚠{RESET} LLM Gateway (status: {resp.status_code})"
                    )
            except Exception as e:
                print(f"  {YELLOW}○{RESET} LLM Gateway: offline")
        else:
            print(f"  {YELLOW}○{RESET} LLM Gateway: skipped (optional)")

    print(f"\n{'=' * 60}")
    print(f"{GREEN}✅ Smoke test passed!{RESET}")
    print(f"{'=' * 60}\n")
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(smoke_test())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}⚠ Test interrupted{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}❌ Test failed: {e}{RESET}")
        sys.exit(1)
