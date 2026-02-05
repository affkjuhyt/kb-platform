from datetime import datetime, UTC
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from config import settings
from db import get_chunks_by_ids, get_db_session
from embedding import embedder_factory
from fusion import rrf_fusion, weighted_fusion
from opensearch_store import OpenSearchStore
from qdrant_store import QdrantStore
import httpx

from rerank import basic_rerank
from resolver import resolve_conflicts, get_citation
from db import get_chunks_by_doc
from prompt_builder import RAGPromptBuilder, ContextChunk, build_rag_query_prompt
from extraction import ExtractionService, validate_extraction_result
from extraction_storage import ExtractionStorageService
from extraction_models import ExtractionJob, ExtractionResult


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


app = FastAPI(title="Query API")


@app.get("/healthz")
def healthz():
    return {"status": "ok", "time": datetime.now(UTC).isoformat()}


@app.post("/search", response_model=SearchResponse)
def search(payload: SearchRequest):
    top_k = payload.top_k or settings.top_k
    embedder = embedder_factory()
    qdrant = QdrantStore()
    opensearch = OpenSearchStore()

    filters = {"tenant_id": payload.tenant_id} if payload.tenant_id else None

    vector = embedder.embed([payload.query])[0]
    v_hits = qdrant.search(vector, limit=settings.vector_k, filters=None)
    v_rank = []
    for hit in v_hits:
        doc_id = hit.payload.get("doc_id")
        chunk_index = hit.payload.get("chunk_index")
        v_rank.append((f"{doc_id}:{chunk_index}", float(hit.score)))

    b_hits = opensearch.bm25_search(payload.query, settings.bm25_k, filters=filters)
    b_rank = []
    for hit in b_hits.get("hits", {}).get("hits", []):
        doc_id = hit["_source"]["doc_id"]
        chunk_index = hit["_source"]["chunk_index"]
        b_rank.append((f"{doc_id}:{chunk_index}", float(hit.get("_score", 0.0))))

    v_scores = {k: s for k, s in v_rank}
    b_scores = {k: s for k, s in b_rank}
    if settings.fusion_method == "weighted":
        fusion_scores = weighted_fusion(v_scores, b_scores)
    else:
        fusion_scores = rrf_fusion([v_rank, b_rank])
    ranked = sorted(fusion_scores.items(), key=lambda x: x[1], reverse=True)
    ranked_ids = ranked[: top_k * 2]

    id_pairs = []
    for item_id, _ in ranked_ids:
        doc_id, chunk_index = item_id.split(":", 1)
        id_pairs.append((doc_id, int(chunk_index)))

    chunk_rows = get_chunks_by_ids(id_pairs)
    chunk_map = {(c.doc_id, c.chunk_index): c for c in chunk_rows}

    candidates = []
    for item_id, score in ranked_ids:
        doc_id, chunk_index = item_id.split(":", 1)
        key = (doc_id, int(chunk_index))
        chunk = chunk_map.get(key)
        if not chunk:
            continue
        candidates.append((chunk, score))

    if settings.rerank_backend == "service":
        top = candidates[: settings.rerank_top_n]
        try:
            resp = httpx.post(
                f"{settings.rerank_url}/rerank",
                json={
                    "query": payload.query,
                    "candidates": [
                        {
                            "id": f"{c.doc_id}:{c.chunk_index}",
                            "text": c.text,
                            "score": s,
                        }
                        for c, s in top
                    ],
                },
                timeout=30,
            )
            resp.raise_for_status()
            reranked = resp.json().get("results", [])
            scores_map = {r["id"]: r["score"] for r in reranked}
            candidates = [
                (c, scores_map.get(f"{c.doc_id}:{c.chunk_index}", s)) for c, s in top
            ] + candidates[settings.rerank_top_n :]
        except Exception:
            texts = [c.text for c, _ in top]
            scores = basic_rerank(payload.query, texts)
            candidates = (
                list(zip([c for c, _ in top], scores))
                + candidates[settings.rerank_top_n :]
            )
    elif settings.rerank_backend == "basic":
        texts = [c.text for c, _ in candidates]
        scores = basic_rerank(payload.query, texts)
        candidates = [(c, s) for (c, _), s in zip(candidates, scores)]

    priority_map = {}
    if settings.source_priority:
        for item in settings.source_priority.split(","):
            if ":" in item:
                key, val = item.split(":", 1)
                try:
                    priority_map[key.strip()] = int(val.strip())
                except ValueError:
                    priority_map[key.strip()] = 0

    resolved, conflicts = resolve_conflicts([c for c, _ in candidates], priority_map)
    resolved_set = {(c.doc_id, c.chunk_index) for c in resolved}

    results = []
    for c, score in candidates:
        if (c.doc_id, c.chunk_index) not in resolved_set:
            continue
        results.append(
            SearchResult(
                doc_id=c.doc_id,
                source=c.source,
                source_id=c.source_id,
                version=c.version,
                chunk_index=c.chunk_index,
                score=float(score),
                text=c.text,
                section_path=c.section_path,
                heading_path=c.heading_path,
                citation=CitationInfo(
                    doc_id=c.doc_id,
                    source=c.source,
                    source_id=c.source_id,
                    version=c.version,
                    chunk_index=c.chunk_index,
                    section_path=c.section_path,
                    heading_path=c.heading_path,
                ),
            )
        )
        if len(results) >= top_k:
            break

    return SearchResponse(query=payload.query, results=results)


@app.post("/citations", response_model=CitationsResponse)
def citations(payload: CitationsRequest):
    rows = get_chunks_by_doc(payload.doc_id, payload.section_path)
    citations = [
        Citation(
            doc_id=r.doc_id,
            chunk_index=r.chunk_index,
            section_path=r.section_path,
            heading_path=r.heading_path,
            text=r.text,
        )
        for r in rows
    ]
    return CitationsResponse(
        doc_id=payload.doc_id,
        section_path=payload.section_path,
        citations=citations,
    )


# ============================================================================
# RAG Query Endpoints (Phase 6)
# ============================================================================


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


@app.post("/rag", response_model=RAGResponse)
def rag_query(payload: RAGRequest):
    """
    Perform RAG-based question answering with citations.

    1. Searches for relevant context
    2. Builds RAG prompt with citations
    3. Calls LLM Gateway for answer generation
    4. Returns answer with citations
    """
    # Step 1: Search for relevant documents
    search_payload = SearchRequest(
        query=payload.query,
        tenant_id=payload.tenant_id,
        top_k=payload.top_k,
    )
    search_response = search(search_payload)

    if not search_response.results:
        return RAGResponse(
            query=payload.query,
            answer="I don't have enough information to answer this question.",
            citations=[],
            confidence=0.0,
            session_id=payload.session_id,
        )

    # Step 2: Build RAG prompt with context
    prompt = build_rag_query_prompt(
        query=payload.query,
        search_results=[result.dict() for result in search_response.results],
        max_context_length=settings.rag_max_context_length,
    )

    # Step 3: Call LLM Gateway for RAG
    try:
        resp = httpx.post(
            f"{settings.llm_gateway_url}/rag",
            json={
                "query": payload.query,
                "context": prompt,
                "max_tokens": settings.rag_max_tokens,
                "temperature": payload.temperature or settings.rag_default_temperature,
            },
            timeout=120,
        )
        resp.raise_for_status()
        llm_response = resp.json()

        # Build citation objects from search results
        citation_map = {
            f"{r.doc_id}:{r.chunk_index}": RAGCitation(
                doc_id=r.doc_id,
                source=r.source,
                source_id=r.source_id,
                version=r.version,
                section_path=r.section_path,
                heading_path=r.heading_path,
            )
            for r in search_response.results
        }

        # Map LLM citations to full citation objects
        response_citations = []
        for citation_ref in llm_response.get("citations", []):
            # Try to find matching citation
            for key, citation in citation_map.items():
                if citation_ref in key or citation.doc_id in citation_ref:
                    response_citations.append(citation)
                    break

        # Remove duplicates while preserving order
        seen = set()
        unique_citations = []
        for c in response_citations:
            key = (c.doc_id, c.chunk_index)
            if key not in seen:
                seen.add(key)
                unique_citations.append(c)

        return RAGResponse(
            query=payload.query,
            answer=llm_response.get("answer", ""),
            citations=unique_citations,
            confidence=llm_response.get("confidence", 0.0),
            model=llm_response.get("model"),
            session_id=payload.session_id,
        )

    except Exception as e:
        return RAGResponse(
            query=payload.query,
            answer=f"Error generating answer: {str(e)}",
            citations=[],
            confidence=0.0,
            session_id=payload.session_id,
        )


# ============================================================================
# Extraction Endpoints (Phase 6)
# ============================================================================


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


@app.post("/extract", response_model=ExtractResult)
def extract_data(payload: ExtractRequest):
    """
    Extract structured data from documents based on query and schema.

    1. Searches for relevant context
    2. Performs structured extraction
    3. Validates against schema
    4. Returns extracted data with confidence score
    """
    extraction_service = ExtractionService()

    result = extraction_service.extract_from_search(
        query=payload.query,
        tenant_id=payload.tenant_id,
        extraction_schema=payload.schema,
        top_k=payload.top_k,
        min_confidence=payload.min_confidence,
    )

    return ExtractResult(
        success=result.success,
        data=result.data,
        confidence=result.confidence,
        validation_errors=result.validation_errors,
    )


@app.post("/extract/jobs", response_model=ExtractionJobResponse)
def create_extraction_job(
    payload: ExtractRequest,
    db: Session = Depends(get_db_session),
):
    """
    Create an extraction job and save results to database.
    """
    storage_service = ExtractionStorageService(db)

    # Create job
    job = storage_service.create_job(
        tenant_id=payload.tenant_id,
        query=payload.query,
        schema_definition=payload.schema,
        schema_name=payload.schema_name,
        top_k=payload.top_k,
        min_confidence=payload.min_confidence,
    )

    # Update status to processing
    storage_service.update_job_status(job.id, "processing")

    try:
        # Perform extraction
        extraction_service = ExtractionService()
        result = extraction_service.extract_from_search(
            query=payload.query,
            tenant_id=payload.tenant_id,
            extraction_schema=payload.schema,
            top_k=payload.top_k,
            min_confidence=payload.min_confidence,
        )

        # Save result
        storage_service.save_result(
            job_id=job.id,
            data=result.data,
            confidence=result.confidence,
            is_valid=result.success and len(result.validation_errors) == 0,
            validation_errors=result.validation_errors,
            raw_response=result.raw_response,
        )

        # Update job status
        if result.success:
            storage_service.update_job_status(job.id, "completed")
        else:
            storage_service.update_job_status(
                job.id, "failed", error_message="; ".join(result.validation_errors)
            )

        return ExtractionJobResponse(
            job_id=str(job.id),
            status="completed" if result.success else "failed",
            query=job.query,
            schema_name=job.schema_name,
            created_at=job.created_at,
            result_count=1 if result.data else 0,
        )

    except Exception as e:
        storage_service.update_job_status(job.id, "failed", error_message=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/extract/jobs/{job_id}")
def get_extraction_job(
    job_id: str,
    db: Session = Depends(get_db_session),
):
    """Get extraction job details and results."""
    from uuid import UUID

    storage_service = ExtractionStorageService(db)
    job = storage_service.get_job(UUID(job_id))

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    results = storage_service.get_job_results(UUID(job_id))

    return {
        "job": {
            "id": str(job.id),
            "tenant_id": job.tenant_id,
            "query": job.query,
            "schema_name": job.schema_name,
            "status": job.status,
            "created_at": job.created_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        },
        "results": [
            {
                "id": str(r.id),
                "data": r.data,
                "confidence": r.confidence,
                "is_valid": r.is_valid,
                "validation_errors": r.validation_errors,
                "created_at": r.created_at.isoformat(),
            }
            for r in results
        ],
    }


@app.get("/extract/jobs")
def list_extraction_jobs(
    tenant_id: str,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db_session),
):
    """List extraction jobs for a tenant."""
    storage_service = ExtractionStorageService(db)
    jobs = storage_service.list_jobs(tenant_id, status, limit, offset)

    return {
        "jobs": [
            {
                "id": str(job.id),
                "query": job.query,
                "schema_name": job.schema_name,
                "status": job.status,
                "created_at": job.created_at.isoformat(),
            }
            for job in jobs
        ],
        "total": len(jobs),
    }


@app.get("/extract/stats")
def get_extraction_stats(
    tenant_id: str,
    days: int = 30,
    db: Session = Depends(get_db_session),
):
    """Get extraction statistics for a tenant."""
    storage_service = ExtractionStorageService(db)
    stats = storage_service.get_extraction_stats(tenant_id, days)

    return stats
