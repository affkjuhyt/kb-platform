from datetime import datetime, UTC
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import sys

sys.path.insert(0, "/Users/thiennlinh/Documents/New project/shared")
from cache import (
    cache_manager,
    cache_search,
    cache_rag,
    cache_extraction,
    invalidate_tenant_cache,
)

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
from qdrant_store import init_qdrant, close_qdrant
from contextlib import asynccontextmanager


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ===== Startup =====
    print("🚀 Starting Query API...")

    # Initialize Qdrant
    await init_qdrant()
    print("✅ Qdrant pool initialized")

    # Ensure collection exists
    try:
        qdrant = QdrantStore()
        # Try a dummy search to trigger collection creation if needed
        from qdrant_client.http.models import Distance, VectorParams

        http_client = qdrant._get_http_client()
        try:
            collections = http_client.get_collections()
            if not any(
                c.name == settings.qdrant_collection for c in collections.collections
            ):
                print(
                    f"⚠️ Collection '{settings.qdrant_collection}' not found, creating..."
                )
                http_client.create_collection(
                    collection_name=settings.qdrant_collection,
                    vectors_config=VectorParams(
                        size=settings.embedding_dim, distance=Distance.COSINE
                    ),
                )
                print(f"✅ Created collection: {settings.qdrant_collection}")
            else:
                print(f"✅ Collection exists: {settings.qdrant_collection}")
        except Exception as e:
            print(f"⚠️ Could not verify collection: {e}")
    except Exception as e:
        print(f"⚠️ Could not ensure collection: {e}")

    print("✅ Query API startup complete")

    yield

    # ===== Shutdown =====
    print("🛑 Shutting down Query API...")
    await close_qdrant()
    print("✅ Query API shutdown complete")
    print("🧹 Qdrant pool closed")


app = FastAPI(title="Query API", lifespan=lifespan)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "time": datetime.now(UTC).isoformat()}


@app.get("/cache/stats")
def cache_stats():
    """Get cache statistics."""
    if not settings.cache_enabled:
        return {"enabled": False}
    return cache_manager.get_stats()


@app.post("/cache/invalidate")
def invalidate_cache(tenant_id: Optional[str] = None):
    """Invalidate cache for a tenant or all."""
    if not settings.cache_enabled:
        return {"message": "Cache disabled"}
    if tenant_id:
        invalidate_tenant_cache(tenant_id)
    else:
        cache_manager.clear_all()
    return {"message": "Cache invalidated"}


def _perform_search(payload: SearchRequest) -> SearchResponse:
    """Internal search logic without caching."""
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
        texts = [c.text for c in candidates]
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


@cache_search(ttl=300)
def _cached_search(query: str, tenant_id: str, top_k: int = 10):
    """Cached search wrapper."""
    payload = SearchRequest(query=query, tenant_id=tenant_id or "default", top_k=top_k)
    return _perform_search(payload)


@app.post("/search", response_model=SearchResponse)
def search(payload: SearchRequest):
    if not settings.cache_enabled:
        return _perform_search(payload)
    top_k = payload.top_k or 10
    return _cached_search(payload.query, payload.tenant_id or "default", top_k)


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


@cache_rag(ttl=600)
def _cached_rag(query: str, tenant_id: str, top_k: int, temperature: float):
    """Cached RAG wrapper for LLM responses."""
    search_payload = SearchRequest(query=query, tenant_id=tenant_id, top_k=top_k)
    search_response = _perform_search(search_payload)

    if not search_response.results:
        return RAGResponse(
            query=query,
            answer="I don't have enough information to answer this question.",
            citations=[],
            confidence=0.0,
        )

    prompt = build_rag_query_prompt(
        query=query,
        search_results=[result.dict() for result in search_response.results],
        max_context_length=settings.rag_max_context_length,
    )

    resp = httpx.post(
        f"{settings.llm_gateway_url}/rag",
        json={
            "query": query,
            "context": prompt,
            "max_tokens": settings.rag_max_tokens,
            "temperature": temperature,
        },
        timeout=120,
    )
    resp.raise_for_status()
    llm_response = resp.json()

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

    response_citations = []
    for citation_ref in llm_response.get("citations", []):
        for key, citation in citation_map.items():
            if citation_ref in key or citation.doc_id in citation_ref:
                response_citations.append(citation)
                break

    seen = set()
    unique_citations = []
    for c in response_citations:
        key = (c.doc_id, c.chunk_index)
        if key not in seen:
            seen.add(key)
            unique_citations.append(c)

    return RAGResponse(
        query=query,
        answer=llm_response.get("answer", ""),
        citations=unique_citations,
        confidence=llm_response.get("confidence", 0.0),
        model=llm_response.get("model"),
    )


@app.post("/rag", response_model=RAGResponse)
def rag_query(payload: RAGRequest):
    """
    Perform RAG-based question answering with citations.

    1. Searches for relevant context
    2. Builds RAG prompt with citations
    3. Calls LLM Gateway for answer generation
    4. Returns answer with citations
    """
    temperature = payload.temperature or settings.rag_default_temperature

    if not settings.cache_enabled:
        return _cached_rag(payload.query, payload.tenant_id, payload.top_k, temperature)

    try:
        return _cached_rag(payload.query, payload.tenant_id, payload.top_k, temperature)
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


# ============================================================================
# Enhanced Search Endpoints (HyDE, Query Decomposition, Advanced Caching)
# ============================================================================


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


@app.post("/search/enhanced", response_model=EnhancedSearchResponse)
async def enhanced_search(payload: EnhancedSearchRequest):
    """Perform enhanced search with HyDE and query decomposition."""
    from enhanced_search import get_enhanced_search_engine

    engine = await get_enhanced_search_engine()

    result = await engine.search(
        query=payload.query,
        tenant_id=payload.tenant_id,
        top_k=payload.top_k or settings.top_k,
        use_cache=payload.use_cache,
        use_hyde=payload.use_hyde,
        use_decomposition=payload.use_decomposition,
    )

    return EnhancedSearchResponse(**result)


class HyDESearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    tenant_id: Optional[str] = None
    top_k: Optional[int] = None


@app.post("/search/hyde")
async def hyde_search(payload: HyDESearchRequest):
    """Search using HyDE (Hypothetical Document Embeddings)."""
    from hyde import HyDESearchEngine, HyDEGenerator, HyDEEmbedder
    from embedding import embedder_factory
    from qdrant_store import QdrantStore
    from opensearch_store import OpenSearchStore

    qdrant = QdrantStore()
    opensearch = OpenSearchStore()
    embedder = embedder_factory()

    hyde_generator = HyDEGenerator()
    hyde_embedder = HyDEEmbedder(embedder)

    engine = HyDESearchEngine(
        hyde_generator=hyde_generator,
        hyde_embedder=hyde_embedder,
        qdrant_store=qdrant,
        opensearch_store=opensearch,
    )

    results, hyde_doc = await engine.search(
        query=payload.query,
        tenant_id=payload.tenant_id,
        top_k=payload.top_k or settings.top_k,
        use_hyde=True,
    )

    return {
        "query": payload.query,
        "hyde_answer": hyde_doc.hypothetical_answer if hyde_doc else None,
        "results": results,
        "hyde_used": True,
    }


class DecomposeRequest(BaseModel):
    query: str = Field(..., min_length=1)


class DecomposeResponse(BaseModel):
    original_query: str
    sub_queries: list
    strategy: str


@app.post("/query/decompose", response_model=DecomposeResponse)
async def decompose_query(payload: DecomposeRequest):
    """Decompose a complex query into simpler sub-queries."""
    from query_decomposition import QueryDecomposer

    decomposer = QueryDecomposer()
    result = await decomposer.decompose(payload.query)

    return DecomposeResponse(
        original_query=result.original_query,
        sub_queries=[
            {
                "id": sq.id,
                "query": sq.query,
                "intent": sq.intent,
                "keywords": sq.keywords,
                "is_primary": sq.is_primary,
            }
            for sq in result.sub_queries
        ],
        strategy=result.strategy.value,
    )


@app.get("/cache/query/stats")
async def query_cache_stats():
    """Get query cache statistics."""
    from enhanced_search import get_query_cache

    cache = await get_query_cache()
    return cache.get_stats()


@app.post("/cache/query/warm")
async def warm_cache(queries: list):
    """Warm the query cache with common queries."""
    from enhanced_search import get_enhanced_search_engine

    engine = await get_enhanced_search_engine()
    await engine.warm_cache(queries)

    return {"message": f"Warmed cache with {len(queries)} queries"}


@app.post("/cache/query/invalidate")
async def invalidate_query_cache(tenant_id: str = None):
    """Invalidate query cache for a tenant or all."""
    from enhanced_search import get_query_cache

    cache = await get_query_cache()

    if tenant_id:
        await cache.invalidate_tenant(tenant_id)
        return {"message": f"Invalidated cache for tenant: {tenant_id}"}

    await cache.clear_all()
    return {"message": "Invalidated all query cache"}


@app.get("/features")
def list_features():
    """List available search features and their status."""
    return {
        "features": {
            "basic_search": True,
            "hybrid_search": True,
            "rag_query": True,
            "structured_extraction": True,
            "caching": {
                "enabled": settings.cache_enabled,
                "l1_cache": True,
                "l2_redis": True,
            },
            "hyde": {
                "enabled": settings.hyde_enabled,
                "description": "Hypothetical Document Embeddings for improved recall",
            },
            "query_decomposition": {
                "enabled": settings.query_decomposition_enabled,
                "description": "Break complex queries into sub-queries",
            },
            "streaming": False,
            "multi_llm": True,
        },
        "settings": {
            "hyde_enabled": settings.hyde_enabled,
            "query_decomposition_enabled": settings.query_decomposition_enabled,
            "cache_enabled": settings.cache_enabled,
            "query_cache_ttl": settings.query_cache_ttl,
        },
    }
