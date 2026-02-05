import base64
from datetime import datetime, UTC
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from chunker import chunk_document
from parsers import parse_content
from schemas import ChunkPayload

app = FastAPI(title="Indexer Service")


class ParseRequest(BaseModel):
    content_type: str = "text/plain"
    filename: Optional[str] = None
    content: Optional[str] = None
    content_base64: Optional[str] = None


class ChunkResponse(BaseModel):
    chunks: list[ChunkPayload]


@app.get("/healthz")
def healthz():
    return {"status": "ok", "time": datetime.now(UTC).isoformat()}


@app.post("/chunk", response_model=ChunkResponse)
def chunk(payload: ParseRequest):
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

    root = parse_content(
        data=data,
        content_type=payload.content_type,
        filename=payload.filename,
    )

    chunks = chunk_document(root)
    return ChunkResponse(
        chunks=[
            ChunkPayload(
                doc_id="local",
                tenant_id="local",
                source="local",
                source_id="local",
                version=1,
                raw_object_key="local",
                content_type=payload.content_type,
                chunk_index=c.index,
                text=c.text,
                heading_path=c.heading_path,
                section_path=c.section_path,
                start=c.start,
                end=c.end,
                schema_version=1,
            )
            for c in chunks
        ]
    )
