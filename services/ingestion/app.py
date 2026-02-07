import base64
import hashlib
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, UTC
from typing import Any, Optional

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from config import settings
from db import get_latest_doc, insert_document, mark_latest_false
from kafka_client import event_publisher_factory
from migrations import run_migrations
from storage import storage_service_factory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingestion")


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting up ingestion service...")

    # Run database migrations
    try:
        logger.info("Running database migrations...")
        run_migrations()
        logger.info("✓ Database migrations completed")
    except Exception as e:
        logger.error(f"✗ Database migration failed: {e}")
        logger.warning(
            "Continuing without migrations - database might not be properly set up"
        )

    # Ensure MinIO bucket exists
    try:
        logger.info("Ensuring MinIO bucket exists...")
        storage_service_factory().ensure_bucket()
        logger.info("✓ MinIO bucket ready")
    except Exception as e:
        logger.error(f"✗ MinIO connection failed: {e}")
        logger.warning("MinIO not available - file storage will not work")
        logger.info("Make sure MinIO is running: docker-compose up -d minio")

    logger.info("✓ Ingestion service startup complete")
    yield

    logger.info("Shutting down ingestion service...")


app = FastAPI(title="Ingestion Service", lifespan=lifespan)


class IngestWebhookRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    source_id: str = Field(..., min_length=1)
    content_type: str = "text/plain"
    content: Optional[str] = None
    content_base64: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestPullRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    source_id: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    content_type: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestResponse(BaseModel):
    doc_id: str
    version: int
    duplicate: bool
    raw_object_key: str


@app.get("/healthz")
def healthz():
    return {"status": "ok", "time": datetime.now(UTC).isoformat()}


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


@app.post("/webhook", response_model=IngestResponse)
def ingest_webhook(payload: IngestWebhookRequest):
    if not payload.content and not payload.content_base64:
        raise HTTPException(
            status_code=400, detail="content or content_base64 required"
        )

    if payload.content_base64:
        try:
            data = base64.b64decode(payload.content_base64)
        except Exception:
            raise HTTPException(status_code=400, detail="invalid content_base64")
    else:
        data = payload.content.encode("utf-8")

    return _store_and_record(
        tenant_id=payload.tenant_id,
        source=payload.source,
        source_id=payload.source_id,
        content_type=payload.content_type,
        data=data,
        metadata=payload.metadata,
    )


@app.post("/pull", response_model=IngestResponse)
def ingest_pull(payload: IngestPullRequest):
    try:
        resp = requests.get(payload.url, timeout=30)
        resp.raise_for_status()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"failed to fetch url: {exc}")

    content_type = payload.content_type or resp.headers.get(
        "content-type", "application/octet-stream"
    )

    return _store_and_record(
        tenant_id=payload.tenant_id,
        source=payload.source,
        source_id=payload.source_id,
        content_type=content_type,
        data=resp.content,
        metadata=payload.metadata,
    )
