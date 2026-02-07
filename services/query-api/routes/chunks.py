from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from db import get_chunks_by_source_id
from utils.security import get_tenant_context, TenantContext

router = APIRouter(prefix="/chunks", tags=["chunks"])


class ChunkInfo(BaseModel):
    chunk_index: int
    text: str
    heading_path: List[str]
    section_path: str
    start: int
    end: int
    created_at: Optional[str] = None


class SourceChunksResponse(BaseModel):
    tenant_id: str
    source: str
    source_id: str
    version: int
    doc_id: Optional[str] = None
    raw_object_key: Optional[str] = None
    content_type: Optional[str] = None
    total_chunks: int
    chunks: List[ChunkInfo]


@router.get(
    "/source/{tenant_id}/{source}/{source_id}", response_model=SourceChunksResponse
)
def get_chunks_by_source(
    tenant_id: str,
    source: str,
    source_id: str,
    version: Optional[int] = Query(
        None, description="Specific version (default: latest)"
    ),
    auth: TenantContext = Depends(get_tenant_context),
):
    """
    Get all chunks for a specific source_id.

    This endpoint retrieves all chunks that were created from a specific document
    identified by tenant_id + source + source_id.

    Example:
        GET /chunks/source/acme-corp/uploads/contract-001
        GET /chunks/source/acme-corp/uploads/contract-001?version=2
    """
    auth.validate_tenant(tenant_id)
    chunks = get_chunks_by_source_id(tenant_id, source, source_id, version)

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail=f"No chunks found for source_id '{source_id}' in source '{source}' (tenant: {tenant_id})",
        )

    # Get metadata from first chunk (all chunks have same metadata)
    first_chunk = chunks[0]

    return SourceChunksResponse(
        tenant_id=tenant_id,
        source=source,
        source_id=source_id,
        version=first_chunk.version,
        doc_id=first_chunk.doc_id,
        raw_object_key=first_chunk.raw_object_key,
        content_type=first_chunk.content_type,
        total_chunks=len(chunks),
        chunks=[
            ChunkInfo(
                chunk_index=c.chunk_index,
                text=c.text,
                heading_path=c.heading_path,
                section_path=c.section_path,
                start=c.start,
                end=c.end,
                created_at=c.created_at.isoformat() if c.created_at else None,
            )
            for c in chunks
        ],
    )


class SourceTextResponse(BaseModel):
    tenant_id: str
    source: str
    source_id: str
    version: int
    total_chunks: int
    full_text: str


@router.get(
    "/source/{tenant_id}/{source}/{source_id}/text", response_model=SourceTextResponse
)
def get_source_text(
    tenant_id: str,
    source: str,
    source_id: str,
    version: Optional[int] = Query(
        None, description="Specific version (default: latest)"
    ),
    auth: TenantContext = Depends(get_tenant_context),
):
    """
    Get full text content for a specific source_id (all chunks concatenated).

    Example:
        GET /chunks/source/acme-corp/uploads/contract-001/text
    """
    auth.validate_tenant(tenant_id)
    chunks = get_chunks_by_source_id(tenant_id, source, source_id, version)

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail=f"No chunks found for source_id '{source_id}' in source '{source}' (tenant: {tenant_id})",
        )

    # The chunks are already sorted by chunk_index from the database query.
    full_text = "\n\n".join([c.text for c in chunks])

    return SourceTextResponse(
        tenant_id=tenant_id,
        source=source,
        source_id=source_id,
        version=chunks[0].version,
        total_chunks=len(chunks),
        full_text=full_text,
    )
