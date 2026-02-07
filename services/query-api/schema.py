from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    tenant_id: Optional[str] = None
    top_k: Optional[int] = None


class CitationInfo(BaseModel):
    doc_id: str
    source: str
    source_id: str
    version: int
    chunk_index: int
    section_path: str
    heading_path: list[str]


class SearchResult(BaseModel):
    doc_id: str
    source: str
    source_id: str
    version: int
    chunk_index: int
    score: float
    text: str
    section_path: str
    heading_path: list[str]
    citation: CitationInfo


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]


class CitationsRequest(BaseModel):
    doc_id: str = Field(..., min_length=1)
    section_path: Optional[str] = None


class Citation(BaseModel):
    doc_id: str
    chunk_index: int
    section_path: str
    heading_path: list[str]
    text: str


class CitationsResponse(BaseModel):
    doc_id: str
    section_path: Optional[str]
    citations: list[Citation]


class RAGRequest(BaseModel):
    query: str = Field(..., min_length=1)
    tenant_id: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    session_id: Optional[str] = None
    temperature: Optional[float] = 0.3


class RAGCitation(BaseModel):
    doc_id: str
    source: str
    source_id: str
    version: int
    section_path: str
    heading_path: List[str]


class RAGResponse(BaseModel):
    query: str
    answer: str
    citations: List[RAGCitation]
    confidence: float
    model: Optional[str] = None
    session_id: Optional[str] = None


class ExtractRequest(BaseModel):
    query: str = Field(..., min_length=1, description="What to extract")
    tenant_id: str = Field(..., min_length=1)
    schema: Dict[str, Any] = Field(..., description="JSON schema for extraction")
    schema_name: Optional[str] = Field(default="custom", description="Schema name/type")
    top_k: int = Field(default=5, ge=1, le=20)
    min_confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class ExtractResult(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]]
    confidence: float
    validation_errors: List[str]
    extraction_id: Optional[str] = None


class ExtractionJobResponse(BaseModel):
    job_id: str
    status: str
    query: str
    schema_name: str
    created_at: datetime
    result_count: int = 0


class EnhancedSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    tenant_id: Optional[str] = None
    top_k: Optional[int] = None
    use_hyde: Optional[bool] = None
    use_decomposition: Optional[bool] = None
    use_cache: Optional[bool] = None


class EnhancedSearchResponse(BaseModel):
    query: str
    results: list
    total: int
    time_ms: int
    cached: bool
    hyde_used: bool
    decomposition_used: bool
    hyde_answer: Optional[str] = None
    sub_queries: Optional[list] = None


class DecomposeRequest(BaseModel):
    query: str = Field(..., min_length=1)


class DecomposeResponse(BaseModel):
    original_query: str
    sub_queries: list
    strategy: str


class HyDESearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    tenant_id: Optional[str] = None
    top_k: Optional[int] = None
