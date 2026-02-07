from services.service import _cached_rag
from config import settings
from schema import RAGRequest, RAGResponse
from fastapi import APIRouter

rag_router = APIRouter()


@rag_router.post("/rag", response_model=RAGResponse)
async def rag_query(payload: RAGRequest):
    """
    Perform RAG-based question answering with citations.

    1. Searches for relevant context
    2. Builds RAG prompt with citations
    3. Calls LLM Gateway for answer generation
    4. Returns answer with citations
    """
    temperature = payload.temperature or settings.rag_default_temperature

    if not settings.cache_enabled:
        return await _cached_rag(
            payload.query, payload.tenant_id, payload.top_k, temperature
        )

    try:
        return await _cached_rag(
            payload.query, payload.tenant_id, payload.top_k, temperature
        )
    except Exception as e:
        return RAGResponse(
            query=payload.query,
            answer=f"Error generating answer: {str(e)}",
            citations=[],
            confidence=0.0,
            session_id=payload.session_id,
        )
