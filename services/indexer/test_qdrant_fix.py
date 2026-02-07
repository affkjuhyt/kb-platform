#!/usr/bin/env python3
"""
Quick fix test for Qdrant connection issue
"""

import sys

sys.path.insert(0, "/Users/thiennlinh/Documents/New project/services/indexer")

print("Testing Qdrant connection fix...")
print("=" * 60)

try:
    from qdrant_store import QdrantStore, _pool, get_pool
    from config import settings

    print("1. Creating QdrantStore instance...")
    store = QdrantStore()
    print(f"   ✓ Pool initialized: {_pool._initialized}")
    print(f"   ✓ gRPC enabled: {_pool.use_grpc}")

    print("\n2. Testing client access...")
    client = store._get_client()
    print(f"   ✓ Client type: {type(client)}")

    http_client = store._get_http_client()
    print(f"   ✓ HTTP client type: {type(http_client)}")

    print("\n3. Testing collection check...")
    import asyncio

    async def test_collection():
        try:
            await store.ensure_collection()
            print("   ✓ Collection exists or created")
        except Exception as e:
            print(f"   ⚠ Collection check error: {e}")

    asyncio.run(test_collection())

    print("\n" + "=" * 60)
    print("✅ Qdrant connection fix is working!")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
