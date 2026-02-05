from pydantic import BaseModel, Field


class ChunkPayload(BaseModel):
    doc_id: str
    tenant_id: str
    source: str
    source_id: str
    version: int
    raw_object_key: str
    content_type: str
    chunk_index: int
    text: str
    heading_path: list[str] = Field(default_factory=list)
    section_path: str
    start: int
    end: int
    schema_version: int = 1


class ChunkBatch(BaseModel):
    doc_id: str
    tenant_id: str
    source: str
    source_id: str
    version: int
    raw_object_key: str
    content_type: str
    schema_version: int = 1
    chunks: list[ChunkPayload]
