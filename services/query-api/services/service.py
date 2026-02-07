import asyncio
import httpx

from utils.prompt_builder import build_rag_query_prompt
from schema import RAGCitation, RAGResponse, CitationInfo, SearchResult
from utils.cache import cache_rag, cache_search
from utils.resolver import resolve_conflicts
from utils.rerank import basic_rerank
from db import get_chunks_by_ids
from utils.fusion import rrf_fusion, weighted_fusion
from utils.opensearch_store import OpenSearchStore
from utils.qdrant_store import QdrantStore
from utils.embedding import embedder_factory
from config import settings
from schema import SearchResponse, SearchRequest


async def _perform_search(payload: SearchRequest) -> SearchResponse:
    """Internal search logic without caching."""
    top_k = payload.top_k or settings.top_k
    embedder = embedder_factory()
    qdrant = QdrantStore()
    opensearch = OpenSearchStore()

    filters = {"tenant_id": payload.tenant_id} if payload.tenant_id else None

    vector = embedder.embed_query(payload.query)

    v_task = asyncio.to_thread(qdrant.search, vector, settings.vector_k, filters)
    b_task = asyncio.to_thread(
        opensearch.bm25_search, payload.query, settings.bm25_k, filters
    )

    v_hits, b_hits = await asyncio.gather(v_task, b_task)
    v_rank = []

    for hit in v_hits:
        doc_id = hit.payload.get("doc_id")
        chunk_index = hit.payload.get("chunk_index")
        v_rank.append((f"{doc_id}:{chunk_index}", float(hit.score)))

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
async def _cached_search(query: str, tenant_id: str, top_k: int = 10):
    """Cached search wrapper."""
    payload = SearchRequest(query=query, tenant_id=tenant_id or "default", top_k=top_k)
    return await _perform_search(payload)


# ============================================================================
# RAG Query Endpoints (Phase 6)
# ============================================================================
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
