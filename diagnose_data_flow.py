#!/usr/bin/env python3
"""
Diagnostic script to check data flow: Ingestion -> Indexer -> Qdrant

This script checks:
1. Documents in PostgreSQL
2. Documents in MinIO
3. Chunks in Qdrant
4. Indexer consumer status
"""

import sys
import os

sys.path.insert(0, "/Users/thiennlinh/Documents/New project/services/ingestion")
sys.path.insert(0, "/Users/thiennlinh/Documents/New project/services/indexer")

print("=" * 80)
print("DATA FLOW DIAGNOSTIC")
print("Checking: Ingestion -> PostgreSQL -> Indexer -> Qdrant")
print("=" * 80)

# Check 1: PostgreSQL
try:
    print("\n📊 1. Checking PostgreSQL (Documents)...")
    from ingestion.db import get_session
    from ingestion.models import Document
    from sqlalchemy import func

    with get_session() as session:
        doc_count = session.query(func.count(Document.id)).scalar()
        latest_docs = (
            session.query(Document).filter(Document.latest == True).limit(5).all()
        )

        print(f"   ✅ Total documents: {doc_count}")
        print(f"   ✅ Latest documents: {len([d for d in latest_docs])}")

        if latest_docs:
            print("\n   Recent documents:")
            for doc in latest_docs:
                print(
                    f"   - {doc.doc_id} (v{doc.version}): {doc.source}/{doc.source_id}"
                )

        if doc_count == 0:
            print("   ⚠️  WARNING: No documents found in PostgreSQL!")
            print("      Run: curl -X POST http://localhost:8002/webhook ...")
except Exception as e:
    print(f"   ❌ ERROR: {e}")
    print("      Is PostgreSQL running? docker-compose ps")

# Check 2: MinIO
try:
    print("\n📦 2. Checking MinIO (Raw Files)...")
    from ingestion.storage import storage_service_factory

    storage = storage_service_factory()
    client = storage._factory.create_s3_client()

    # List objects
    objects = client.list_objects_v2(Bucket="raw-docs")
    object_count = objects.get("KeyCount", 0)

    print(f"   ✅ Objects in MinIO: {object_count}")

    if object_count > 0:
        print("   Sample objects:")
        for obj in objects.get("Contents", [])[:3]:
            print(f"   - {obj['Key']} ({obj['Size']} bytes)")

    if object_count == 0:
        print("   ⚠️  WARNING: No files in MinIO!")
except Exception as e:
    print(f"   ❌ ERROR: {e}")
    print("      Is MinIO running? docker logs kb-minio")

# Check 3: Qdrant
try:
    print("\n🔍 3. Checking Qdrant (Vector Chunks)...")
    from qdrant_client import QdrantClient
    from indexer.config import settings

    client = QdrantClient(url=settings.qdrant_url)

    # Check collection
    collections = client.get_collections()
    collection_names = [c.name for c in collections.collections]

    print(f"   ✅ Collections: {collection_names}")

    if settings.qdrant_collection in collection_names:
        collection_info = client.get_collection(settings.qdrant_collection)
        vectors_count = collection_info.points_count
        print(
            f"   ✅ Collection '{settings.qdrant_collection}': {vectors_count} vectors"
        )

        if vectors_count == 0:
            print("   ⚠️  WARNING: Collection exists but has no vectors!")
            print("      Indexer consumer might not be processing messages.")
    else:
        print(f"   ❌ ERROR: Collection '{settings.qdrant_collection}' NOT FOUND!")
        print("      Indexer should create this automatically.")
        print("      Or create manually with the indexer service.")
except Exception as e:
    print(f"   ❌ ERROR: {e}")
    print("      Is Qdrant running? docker logs kb-qdrant")

# Check 4: Kafka
try:
    print("\n📨 4. Checking Kafka (Message Queue)...")
    from kafka import KafkaConsumer

    consumer = KafkaConsumer(
        bootstrap_servers="localhost:9092", consumer_timeout_ms=5000
    )

    topics = consumer.topics()
    print(f"   ✅ Available topics: {len(topics)}")

    if "ingestion.events" in topics:
        print("   ✅ Topic 'ingestion.events' exists")
    else:
        print("   ⚠️  WARNING: Topic 'ingestion.events' not found!")

    if "indexer.chunks" in topics:
        print("   ✅ Topic 'indexer.chunks' exists")
    else:
        print("   ⚠️  WARNING: Topic 'indexer.chunks' not found!")

    consumer.close()
except Exception as e:
    print(f"   ❌ ERROR: {e}")
    print("      Is Kafka running? docker logs kb-kafka")

# Check 5: Indexer Consumer
try:
    print("\n⚙️  5. Checking Indexer Consumer...")
    import subprocess

    result = subprocess.run(
        [
            "docker",
            "ps",
            "--filter",
            "name=kb-indexer",
            "--format",
            "{{.Names}}: {{.Status}}",
        ],
        capture_output=True,
        text=True,
    )

    if result.stdout.strip():
        print(f"   ✅ Indexer containers:")
        for line in result.stdout.strip().split("\n"):
            print(f"      {line}")
    else:
        print("   ❌ ERROR: No indexer containers found!")
        print("      Start with: docker-compose up -d indexer indexer-consumer")
except Exception as e:
    print(f"   ⚠️  Could not check Docker: {e}")

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

print("\nData Flow Status:")
print("  1. Ingestion Service  → PostgreSQL (Documents)")
print("  2. PostgreSQL         → MinIO (Raw Files)")
print("  3. Kafka              → Message Queue")
print("  4. Indexer Consumer   → Qdrant (Vectors)")
print("  5. Query API          ← Qdrant (Search)")

print("\nCommon Issues:")
print("  ❌ 'Collection doesn't exist' → Indexer not creating collection")
print("  ❌ 'No vectors' → Indexer consumer not processing messages")
print("  ❌ 'Connection refused' → Service not running")

print("\nQuick Fixes:")
print("  1. Restart indexer: docker-compose restart indexer indexer-consumer")
print("  2. Check logs: docker logs -f kb-indexer-consumer")
print("  3. Manual index: python services/indexer/manual_index.py")

print("\n" + "=" * 80)
