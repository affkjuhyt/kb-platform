#!/usr/bin/env python3
"""
Manual Indexing Script

Use this to manually index documents from PostgreSQL into Qdrant
when the indexer consumer is not working properly.

Usage:
    cd /Users/thiennlinh/Documents/New\ project
    python3 services/indexer/manual_index.py

This will:
    1. Read all documents from PostgreSQL
    2. Chunk them
    3. Generate embeddings
    4. Store in Qdrant and OpenSearch
"""

import sys

sys.path.insert(0, "/Users/thiennlinh/Documents/New project/services/ingestion")
sys.path.insert(0, "/Users/thiennlinh/Documents/New project/services/indexer")

import uuid
from tqdm import tqdm


def main():
    print("=" * 80)
    print("MANUAL DOCUMENT INDEXING")
    print("=" * 80)

    # Import modules
    print("\n1. Initializing...")
    try:
        from ingestion.db import get_session
        from ingestion.models import Document
        from ingestion.storage import storage_service_factory
        from indexer.chunker import chunk_document
        from indexer.parsers import parse_content
        from indexer.embedding import embedder_factory
        from indexer.qdrant_store import QdrantStore
        from indexer.opensearch_store import OpenSearchStore
        from indexer.config import settings
        from indexer.db import insert_chunks, init_db

        print("   ✅ Modules loaded")
    except Exception as e:
        print(f"   ❌ Failed to load modules: {e}")
        raise

    # Initialize stores
    print("\n2. Initializing stores...")
    try:
        init_db()
        qdrant = QdrantStore()
        qdrant.ensure_collection_sync()
        opensearch = OpenSearchStore()
        opensearch.ensure_index()
        embedder = embedder_factory()
        storage = storage_service_factory()
        print("   ✅ Stores initialized")
    except Exception as e:
        print(f"   ❌ Failed to initialize stores: {e}")
        raise

    # Get documents
    print("\n3. Reading documents from PostgreSQL...")
    with get_session() as session:
        documents = session.query(Document).filter(Document.latest == True).all()
        print(f"   ✅ Found {len(documents)} documents")

    if not documents:
        print("\n   ⚠️  No documents to index!")
        print("      Ingest some documents first:")
        print(
            '      curl -X POST http://localhost:8002/webhook -H "Content-Type: application/json" -d \'{"tenant_id":"test","source":"manual","source_id":"doc1","content":"test"}\''
        )
        return

    # Process each document
    print(f"\n4. Processing {len(documents)} documents...")
    total_chunks = 0

    for doc in tqdm(documents, desc="Documents"):
        try:
            # Get file from MinIO
            data, content_type = storage.get_object(doc.raw_object_key)

            # Parse
            root = parse_content(data=data, content_type=content_type)

            # Chunk
            chunks = chunk_document(root)

            if not chunks:
                continue

            # Prepare chunk data
            chunk_rows = []
            for c in chunks:
                chunk_rows.append(
                    {
                        "doc_id": str(doc.id),
                        "tenant_id": doc.tenant_id,
                        "source": doc.source,
                        "source_id": doc.source_id,
                        "version": doc.version,
                        "chunk_index": c.index,
                        "text": c.text,
                        "heading_path": c.heading_path,
                        "section_path": c.section_path,
                        "start": c.start,
                        "end": c.end,
                    }
                )

            # Insert to PostgreSQL
            insert_chunks(chunk_rows)

            # Generate embeddings
            texts = [c.text for c in chunks]
            vectors = embedder.embed(texts)

            # Prepare for Qdrant
            ids = [
                str(uuid.uuid5(uuid.NAMESPACE_URL, f"{doc.id}:{i}"))
                for i in range(len(chunks))
            ]
            payloads = [
                {
                    "doc_id": str(doc.id),
                    "tenant_id": doc.tenant_id,
                    "source": doc.source,
                    "source_id": doc.source_id,
                    "version": doc.version,
                    "chunk_index": i,
                    "section_path": c.section_path,
                    "raw_object_key": doc.raw_object_key,
                }
                for i, c in enumerate(chunks)
            ]

            # Upsert to Qdrant
            qdrant.upsert(ids=ids, vectors=vectors, payloads=payloads)

            # Index to OpenSearch
            for i, c in enumerate(chunks):
                opensearch.index_chunk(
                    chunk_id=f"{doc.id}:{i}",
                    body={
                        "doc_id": str(doc.id),
                        "tenant_id": doc.tenant_id,
                        "source": doc.source,
                        "source_id": doc.source_id,
                        "version": doc.version,
                        "chunk_index": i,
                        "text": c.text,
                        "section_path": c.section_path,
                    },
                )

            total_chunks += len(chunks)

        except Exception as e:
            print(f"\n   ❌ Error processing document {doc.id}: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 80)
    print("INDEXING COMPLETE")
    print("=" * 80)
    print(f"\nTotal chunks indexed: {total_chunks}")
    print(f"Total documents: {len(documents)}")
    print("\nYou can now search using:")
    print(
        '  curl http://localhost:8001/search -X POST -H \'Content-Type: application/json\' -d \'{"query":"test","tenant_id":"test"}\''
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
