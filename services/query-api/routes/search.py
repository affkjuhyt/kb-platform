from schema import HyDESearchRequest
from db import get_chunks_by_doc
from services.service import _cached_search, _perform_search
from schema import (
    DecomposeRequest,
    DecomposeResponse,
    EnhancedSearchRequest,
    EnhancedSearchResponse,
    Citation,
    CitationsRequest,
    CitationsResponse,
    SearchRequest,
    SearchResponse,
)
from config import settings
from fastapi import APIRouter
from utils.hyde import HyDESearchEngine, HyDEGenerator, HyDEEmbedder
from utils.embedding import embedder_factory
from utils.qdrant_store import QdrantStore
from utils.opensearch_store import OpenSearchStore
from utils.query_decomposition import QueryDecomposer
from utils.enhanced_search import get_enhanced_search_engine

search_router = APIRouter()


@search_router.post("/search", response_model=SearchResponse)
def search(payload: SearchRequest):
    if not settings.cache_enabled:
        return _perform_search(payload)
    top_k = payload.top_k or 10
    return _cached_search(payload.query, payload.tenant_id or "default", top_k)


@search_router.post("/citations", response_model=CitationsResponse)
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


@search_router.post("/search/enhanced", response_model=EnhancedSearchResponse)
async def enhanced_search(payload: EnhancedSearchRequest):
    """Perform enhanced search with HyDE and query decomposition."""
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


@search_router.post("/search/hyde")
async def hyde_search(payload: HyDESearchRequest):
    """Search using HyDE (Hypothetical Document Embeddings)."""
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


@search_router.post("/query/decompose", response_model=DecomposeResponse)
async def decompose_query(payload: DecomposeRequest):
    """Decompose a complex query into simpler sub-queries."""
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
