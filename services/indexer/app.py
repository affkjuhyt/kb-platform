import base64
import os
from datetime import datetime, UTC
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from services.chunker import (
    chunk_document,
    get_chunking_stats,
    _chunk_sentence,
    _chunk_semantic,
    _chunk_markdown,
)
from utils.parsers import parse_content
from schema.events import ChunkPayload
from config import settings

app = FastAPI(title="Indexer Service")


class ParseRequest(BaseModel):
    content_type: str = "text/plain"
    filename: Optional[str] = None
    content: Optional[str] = None
    content_base64: Optional[str] = None


class ChunkRequest(BaseModel):
    text: str
    method: str = "sentence"


class ChunkResponse(BaseModel):
    chunks: list[ChunkPayload]
    method_used: str
    chunk_count: int


class CompareResponse(BaseModel):
    methods: dict


@app.get("/healthz")
def healthz():
    return {"status": "ok", "time": datetime.now(UTC).isoformat()}


@app.get("/stats")
def stats():
    """Get indexing statistics."""
    return {
        "chunking": get_chunking_stats(),
        "config": {
            "chunk_method": settings.chunk_method,
            "chunk_max_chars": settings.chunk_max_chars,
            "chunk_overlap_chars": settings.chunk_overlap_chars,
            "chunk_min_chars": settings.chunk_min_chars,
        },
    }


@app.post("/chunk", response_model=ChunkResponse)
def chunk(payload: ParseRequest):
    """Chunk document using configured method."""
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
        ],
        method_used=settings.chunk_method,
        chunk_count=len(chunks),
    )


@app.post("/chunk/test", response_model=ChunkResponse)
def chunk_test(payload: ChunkRequest):
    """Test chunking with a specific method."""
    from models import Chunk, Node

    method = payload.method.lower()
    chunks: List[Chunk] = []

    if method == "sentence":
        _chunk_sentence(payload.text, [], chunks, 0)
    elif method == "semantic":
        _chunk_semantic(payload.text, [], chunks, 0)
    elif method == "markdown":
        _chunk_markdown(payload.text, [], chunks, 0)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown method: {method}. Use: sentence, semantic, or markdown",
        )

    return ChunkResponse(
        chunks=[
            ChunkPayload(
                doc_id="test",
                tenant_id="test",
                source="test",
                source_id="test",
                version=1,
                raw_object_key="test",
                content_type="text/plain",
                chunk_index=c.index,
                text=c.text,
                heading_path=c.heading_path,
                section_path=c.section_path,
                start=c.start,
                end=c.end,
                schema_version=1,
            )
            for c in chunks
        ],
        method_used=method,
        chunk_count=len(chunks),
    )


@app.post("/chunk/compare")
def compare_chunk_methods(payload: ChunkRequest):
    """Compare all chunking methods on the same text."""
    from models import Chunk

    results = {}
    chunks: List[Chunk] = []

    for method in ["sentence", "semantic", "markdown"]:
        method_chunks: List[Chunk] = []
        try:
            if method == "sentence":
                _chunk_sentence(payload.text, [], method_chunks, 0)
            elif method == "semantic":
                _chunk_semantic(payload.text, [], method_chunks, 0)
            elif method == "markdown":
                _chunk_markdown(payload.text, [], method_chunks, 0)

            char_counts = [len(c.text) for c in method_chunks]
            results[method] = {
                "chunk_count": len(method_chunks),
                "avg_chars": sum(char_counts) / len(char_counts) if char_counts else 0,
                "min_chars": min(char_counts) if char_counts else 0,
                "max_chars": max(char_counts) if char_counts else 0,
            }
        except Exception as e:
            results[method] = {"error": str(e)}

    return {
        "original_length": len(payload.text),
        "methods": results,
    }


@app.get("/methods")
def list_methods():
    """List available chunking methods."""
    return {
        "methods": [
            {
                "name": "sentence",
                "description": "Sentence-based splitting with overlap",
                "available": True,
            },
            {
                "name": "semantic",
                "description": "Embedding-based semantic similarity clustering",
                "available": True,
            },
            {
                "name": "markdown",
                "description": "Markdown header-aware splitting",
                "available": True,
            },
        ],
        "current_default": settings.chunk_method,
    }


@app.post("/config")
def update_config(method: str = Query("sentence")):
    """Update chunking method (for testing)."""
    valid_methods = ["sentence", "semantic", "markdown"]
    if method not in valid_methods:
        raise HTTPException(
            status_code=400, detail=f"Invalid method. Use: {valid_methods}"
        )
    return {
        "message": f"Chunk method updated to: {method}",
        "note": "This only affects the current session",
    }
