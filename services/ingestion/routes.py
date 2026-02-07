import base64
import requests
from typing import Optional
from fastapi import Form, File, UploadFile, HTTPException, APIRouter

from service import _store_and_record
from schema import IngestWebhookRequest, IngestResponse, IngestPullRequest

ingest_router = APIRouter()


@ingest_router.post("/webhook", response_model=IngestResponse)
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


@ingest_router.post("/upload", response_model=IngestResponse)
def ingest_upload(
    file: UploadFile = File(..., description="File to upload (PDF, DOCX, TXT, etc.)"),
    tenant_id: str = Form(..., description="Tenant ID"),
    source: str = Form(..., description="Source identifier"),
    source_id: str = Form(..., description="Unique document ID within source"),
    metadata: Optional[str] = Form(None, description="JSON metadata (optional)"),
):
    """
    Upload file directly via multipart/form-data.
    
    Supports: PDF, DOCX, TXT, MD, HTML files
    
    Example with curl:
        curl -X POST http://localhost:8002/upload \
          -F "file=@document.pdf" \
          -F "tenant_id=company-a" \
          -F "source=uploads" \
          -F "source_id=doc-001"
    """
    # Read file content
    try:
        data = file.file.read()
        if not data:
            raise HTTPException(status_code=400, detail="empty file")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"failed to read file: {e}")
    finally:
        file.file.close()

    # Determine content type
    content_type = file.content_type
    if not content_type:
        # Try to guess from filename
        filename = file.filename or ""
        if filename.endswith(".pdf"):
            content_type = "application/pdf"
        elif filename.endswith(".docx"):
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif filename.endswith(".md"):
            content_type = "text/markdown"
        elif filename.endswith(".html") or filename.endswith(".htm"):
            content_type = "text/html"
        elif filename.endswith(".txt"):
            content_type = "text/plain"
        else:
            content_type = "application/octet-stream"

    # Parse metadata if provided
    import json

    meta_dict = {}
    if metadata:
        try:
            meta_dict = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="invalid metadata JSON")

    # Add filename to metadata
    meta_dict["filename"] = file.filename
    meta_dict["content_type"] = content_type

    return _store_and_record(
        tenant_id=tenant_id,
        source=source,
        source_id=source_id,
        content_type=content_type,
        data=data,
        metadata=meta_dict,
    )


@ingest_router.post("/pull", response_model=IngestResponse)
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
