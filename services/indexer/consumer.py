import logging
import time
from kafka.errors import NoBrokersAvailable

from chunker import chunk_document
from config import settings
from db import init_db, insert_chunks
from embedding import embedder_factory
from opensearch_store import OpenSearchStore
from qdrant_store import QdrantStore
from kafka_client import consumer_factory, publisher_factory
from parsers import parse_content
from schemas import ChunkBatch, ChunkPayload
from storage import storage_service_factory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("indexer-consumer")


def _chunk_metrics(chunks: list[ChunkPayload]) -> dict:
    if not chunks:
        return {"count": 0, "avg_len": 0, "max_len": 0}
    lengths = [len(c.text) for c in chunks]
    return {
        "count": len(lengths),
        "avg_len": int(sum(lengths) / len(lengths)),
        "max_len": max(lengths),
    }


def process_event(event: dict) -> ChunkBatch:
    storage = storage_service_factory()
    data, content_type = storage.get_object(event["raw_object_key"])

    root = parse_content(
        data=data,
        content_type=content_type,
        filename=None,
    )
    chunks = chunk_document(root)

    chunk_payloads = [
        ChunkPayload(
            doc_id=event["doc_id"],
            tenant_id=event["tenant_id"],
            source=event["source"],
            source_id=event["source_id"],
            version=int(event["version"]),
            raw_object_key=event["raw_object_key"],
            content_type=content_type,
            chunk_index=c.index,
            text=c.text,
            heading_path=c.heading_path,
            section_path=c.section_path,
            start=c.start,
            end=c.end,
            schema_version=settings.chunk_schema_version,
        )
        for c in chunks
    ]

    return ChunkBatch(
        doc_id=event["doc_id"],
        tenant_id=event["tenant_id"],
        source=event["source"],
        source_id=event["source_id"],
        version=int(event["version"]),
        raw_object_key=event["raw_object_key"],
        content_type=content_type,
        schema_version=settings.chunk_schema_version,
        chunks=chunk_payloads,
    )


def _create_consumer_with_retry(max_attempts: int = 30, sleep_seconds: float = 2.0):
    for attempt in range(1, max_attempts + 1):
        try:
            return consumer_factory().create_consumer()
        except NoBrokersAvailable:
            logger.warning(
                "Kafka not ready (attempt %s/%s), retrying...", attempt, max_attempts
            )
            time.sleep(sleep_seconds)
    raise NoBrokersAvailable()


def main() -> None:
    init_db()
    qdrant = QdrantStore()
    qdrant.ensure_collection_sync()  # Use sync version
    opensearch = OpenSearchStore()
    opensearch.ensure_index()
    embedder = embedder_factory()

    consumer = _create_consumer_with_retry()
    publisher = publisher_factory()

    logger.info("Indexer consumer started")
    for message in consumer:
        event = message.value
        try:
            batch = process_event(event)
            publisher.publish(batch.model_dump())
            chunk_rows = [c.model_dump() for c in batch.chunks]
            inserted = insert_chunks(chunk_rows)

            texts = [c.text for c in batch.chunks]
            vectors = embedder.embed_documents(texts)
            import uuid

            # deterministic UUIDs per chunk for Qdrant
            ids = [
                str(uuid.uuid5(uuid.NAMESPACE_URL, f"{batch.doc_id}:{c.chunk_index}"))
                for c in batch.chunks
            ]
            payloads = [
                {
                    "doc_id": c.doc_id,
                    "tenant_id": c.tenant_id,
                    "source": c.source,
                    "source_id": c.source_id,
                    "version": c.version,
                    "chunk_index": c.chunk_index,
                    "section_path": c.section_path,
                    "raw_object_key": c.raw_object_key,
                }
                for c in batch.chunks
            ]
            qdrant.upsert(ids=ids, vectors=vectors, payloads=payloads)

            for c in batch.chunks:
                opensearch.index_chunk(
                    chunk_id=f"{batch.doc_id}:{c.chunk_index}",
                    body={
                        "doc_id": c.doc_id,
                        "tenant_id": c.tenant_id,
                        "source": c.source,
                        "source_id": c.source_id,
                        "version": c.version,
                        "chunk_index": c.chunk_index,
                        "text": c.text,
                        "section_path": c.section_path,
                    },
                )
            metrics = _chunk_metrics(batch.chunks)
            logger.info(
                "Processed doc_id=%s chunks=%s inserted=%s avg_len=%s max_len=%s",
                batch.doc_id,
                metrics["count"],
                inserted,
                metrics["avg_len"],
                metrics["max_len"],
            )
        except Exception as exc:
            logger.exception("Failed processing event: %s", exc)


if __name__ == "__main__":
    main()
