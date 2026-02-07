from config import settings
from utils.cache import cache_manager, invalidate_tenant_cache
from fastapi import APIRouter
from typing import Optional

cache_router = APIRouter()


@cache_router.get("/cache/stats")
def cache_stats():
    """Get cache statistics."""
    if not settings.cache_enabled:
        return {"enabled": False}
    return cache_manager.get_stats()


@cache_router.post("/cache/invalidate")
def invalidate_cache(tenant_id: Optional[str] = None):
    """Invalidate cache for a tenant or all."""
    if not settings.cache_enabled:
        return {"message": "Cache disabled"}
    if tenant_id:
        invalidate_tenant_cache(tenant_id)
    else:
        cache_manager.clear_all()
    return {"message": "Cache invalidated"}


@cache_router.get("/cache/query/stats")
async def query_cache_stats():
    """Get query cache statistics."""
    from enhanced_search import get_query_cache

    cache = await get_query_cache()
    return cache.get_stats()


@cache_router.post("/cache/query/warm")
async def warm_cache(queries: list):
    """Warm the query cache with common queries."""
    from enhanced_search import get_enhanced_search_engine

    engine = await get_enhanced_search_engine()
    await engine.warm_cache(queries)

    return {"message": f"Warmed cache with {len(queries)} queries"}


@cache_router.post("/cache/query/invalidate")
async def invalidate_query_cache(tenant_id: str = None):
    """Invalidate query cache for a tenant or all."""
    from enhanced_search import get_query_cache

    cache = await get_query_cache()

    if tenant_id:
        await cache.invalidate_tenant(tenant_id)
        return {"message": f"Invalidated cache for tenant: {tenant_id}"}

    await cache.clear_all()
    return {"message": "Invalidated all query cache"}
