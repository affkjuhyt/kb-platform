from services.service import _cached_rag
from config import settings
from schema import RAGRequest, RAGResponse
from fastapi import APIRouter, Depends
from utils.security import get_tenant_context, TenantContext

rag_router = APIRouter()


@rag_router.post("/rag", response_model=RAGResponse)
async def rag_query(
    payload: RAGRequest, auth: TenantContext = Depends(get_tenant_context)
):
    """
    Perform RAG-based question answering with citations.
    """
    auth.validate_tenant(payload.tenant_id)
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
