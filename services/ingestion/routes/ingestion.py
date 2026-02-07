import base64
import requests
from typing import Optional, List
from fastapi import Form, File, UploadFile, HTTPException, APIRouter

from services.ingestion import _store_and_record
from schema.requests import IngestWebhookRequest, IngestResponse, IngestPullRequest

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


@ingest_router.post("/upload", response_model=List[IngestResponse])
def ingest_upload(
    files: List[UploadFile] = File(
        ..., description="Files to upload (PDF, DOCX, TXT, etc.)"
    ),
    tenant_id: str = Form(..., description="Tenant ID"),
    source: str = Form(..., description="Source identifier"),
    source_id: Optional[str] = Form(
        None, description="Unique document ID (defaults to filename if multiple files)"
    ),
    metadata: Optional[str] = Form(None, description="JSON metadata (optional)"),
):
    """
    Upload one or more files directly via multipart/form-data.
    
    Example with curl (multiple files):
        curl -X POST http://localhost:8002/upload \
          -F "files=@doc1.pdf" \
          -F "files=@doc2.txt" \
          -F "tenant_id=company-a" \
          -F "source=uploads"
    """
    responses = []
    import json

    meta_dict = {}
    if metadata:
        try:
            meta_dict = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="invalid metadata JSON")

    for file in files:
        # Read file content
        try:
            data = file.file.read()
            if not data:
                print(f"Skipping empty file: {file.filename}")
                continue
        except Exception as e:
            print(f"Failed to read file {file.filename}: {e}")
            continue
        finally:
            file.file.close()

        # Determine content type
        content_type = file.content_type
        if not content_type:
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

        # Logic for source_id:
        # 1. If multiple files are uploaded, we use the filename as source_id to avoid overwriting.
        # 2. If one file is uploaded and source_id is provided, use it.
        # 3. If no source_id provided, use filename.
        effective_source_id = source_id
        if len(files) > 1 or not source_id:
            effective_source_id = file.filename

        # Copy metadata for this specific file
        file_meta = meta_dict.copy()
        file_meta["filename"] = file.filename
        file_meta["content_type"] = content_type

        resp = _store_and_record(
            tenant_id=tenant_id,
            source=source,
            source_id=effective_source_id,
            content_type=content_type,
            data=data,
            metadata=file_meta,
        )
        responses.append(resp)

    if not responses and files:
        raise HTTPException(
            status_code=400, detail="No files were successfully processed"
        )

    return responses


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
