import hashlib
import uuid
from typing import Any

from db import get_latest_doc, insert_document, mark_latest_false
from schema import IngestResponse
from utils.kafka import event_publisher_factory
from utils.storage import storage_service_factory


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _store_and_record(
    *,
    tenant_id: str,
    source: str,
    source_id: str,
    content_type: str,
    data: bytes,
    metadata: dict[str, Any],
) -> IngestResponse:
    content_hash = _hash_bytes(data)

    latest = get_latest_doc(tenant_id, source, source_id)
    if latest and latest[1] == content_hash:
        return IngestResponse(
            doc_id=str(latest[0]),
            version=int(latest[2]),
            duplicate=True,
            raw_object_key="",
        )

    version = 1 if not latest else int(latest[2]) + 1

    raw_object_key = f"{tenant_id}/{source}/{source_id}/{uuid.uuid4()}"
    storage_service_factory().put_raw_object(raw_object_key, data, content_type)

    if latest:
        mark_latest_false(tenant_id, source, source_id)

    doc_id = insert_document(
        tenant_id=tenant_id,
        source=source,
        source_id=source_id,
        content_hash=content_hash,
        version=version,
        raw_object_key=raw_object_key,
        content_type=content_type,
        metadata=metadata,
    )

    event_publisher_factory().publish(
        {
            "doc_id": str(doc_id),
            "tenant_id": tenant_id,
            "source": source,
            "source_id": source_id,
            "version": version,
            "raw_object_key": raw_object_key,
        }
    )

    return IngestResponse(
        doc_id=str(doc_id),
        version=version,
        duplicate=False,
        raw_object_key=raw_object_key,
    )
