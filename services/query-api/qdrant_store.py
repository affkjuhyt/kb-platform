import asyncio
from typing import List, Optional
from contextlib import asynccontextmanager

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Filter,
    FieldCondition,
    MatchValue,
    Distance,
    VectorParams,
)
from qdrant_client.http.exceptions import UnexpectedResponse

from config import settings


class QdrantConnectionPool:
    _instance: Optional["QdrantConnectionPool"] = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __init__(self):
        self._client: Optional[QdrantClient] = None
        self._http_client: Optional[QdrantClient] = None
        self._use_grpc: bool = True

    async def initialize(self):
        async with self._lock:
            if self._client is not None:
                return

            grpc_port = getattr(settings, "qdrant_grpc_port", 6334)

            try:
                self._client = QdrantClient(
                    host="localhost",
                    port=grpc_port,
                    prefer_grpc=True,
                    grpc_timeout=60,
                    max_message_size=104857600,
                )
                self._http_client = QdrantClient(
                    url=settings.qdrant_url,
                    timeout=30,
                )
                self._use_grpc = True
                print(f"✓ Qdrant connected via gRPC (port {grpc_port})")
            except Exception as e:
                print(f"⚠ gRPC connection failed, falling back to HTTP: {e}")
                self._client = QdrantClient(url=settings.qdrant_url, timeout=30)
                self._http_client = self._client
                self._use_grpc = False

    def get_client(self) -> QdrantClient:
        return self._client

    def get_http_client(self) -> QdrantClient:
        return self._http_client

    @property
    def use_grpc(self) -> bool:
        return self._use_grpc

    async def close(self):
        if self._client:
            self._client.close()
        if self._http_client and self._http_client != self._client:
            self._http_client.close()


_pool = QdrantConnectionPool()


async def get_pool() -> QdrantConnectionPool:
    if _pool._client is None:
        await _pool.initialize()
    return _pool


class QdrantStore:
    def __init__(self, use_grpc: bool = None):
        self._use_grpc = use_grpc

    def _get_client(self) -> QdrantClient:
        if _pool._client is None:
            raise RuntimeError("Qdrant pool not initialized. Call init_qdrant() first.")
        return _pool._client

    def _get_http_client(self) -> QdrantClient:
        if _pool._http_client is None:
            raise RuntimeError("Qdrant pool not initialized. Call init_qdrant() first.")
        return _pool._http_client

    def _build_filter(self, filters: dict = None):
        if not filters:
            return None

        must_conditions = []
        for key, value in filters.items():
            if isinstance(value, list):
                for v in value:
                    must_conditions.append(
                        FieldCondition(key=key, match=MatchValue(value=v))
                    )
            else:
                must_conditions.append(
                    FieldCondition(key=key, match=MatchValue(value=value))
                )

        return Filter(must=must_conditions) if must_conditions else None

    def _ensure_collection_exists(self, client: QdrantClient) -> None:
        """Create collection if it doesn't exist."""
        try:
            collections = client.get_collections()
            if any(
                c.name == settings.qdrant_collection for c in collections.collections
            ):
                return
        except Exception:
            pass

        try:
            print(f"⚠ Collection '{settings.qdrant_collection}' not found, creating...")
            client.create_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=VectorParams(
                    size=settings.embedding_dim, distance=Distance.COSINE
                ),
            )
            print(f"✓ Created collection: {settings.qdrant_collection}")
        except Exception as e:
            print(f"❌ Failed to create collection: {e}")
            raise

    def search(self, vector, limit: int, filters: dict = None):
        client = self._get_client()
        qdrant_filter = self._build_filter(filters)

        try:
            if self._use_grpc if self._use_grpc is not None else _pool.use_grpc:
                return client.search(
                    collection_name=settings.qdrant_collection,
                    query_vector=vector,
                    limit=limit,
                    query_filter=qdrant_filter,
                    with_payload=True,
                )
        except UnexpectedResponse as e:
            if "doesn't exist" in str(e):
                print(f"⚠ Collection not found, attempting to create...")
                self._ensure_collection_exists(client)
                # Retry search
                return client.search(
                    collection_name=settings.qdrant_collection,
                    query_vector=vector,
                    limit=limit,
                    query_filter=qdrant_filter,
                    with_payload=True,
                )
            raise
        except Exception as e:
            print(f"⚠ gRPC search failed: {e}, falling back to HTTP")

        # HTTP fallback
        http_client = self._get_http_client()
        try:
            return http_client.search(
                collection_name=settings.qdrant_collection,
                query_vector=vector,
                limit=limit,
                query_filter=qdrant_filter,
                with_payload=True,
            )
        except UnexpectedResponse as e:
            if "doesn't exist" in str(e):
                print(f"⚠ Collection not found, attempting to create...")
                self._ensure_collection_exists(http_client)
                # Retry search
                return http_client.search(
                    collection_name=settings.qdrant_collection,
                    query_vector=vector,
                    limit=limit,
                    query_filter=qdrant_filter,
                    with_payload=True,
                )
            raise

    async def async_search(self, vector: List[float], limit: int, filters: dict = None):
        client = _pool.get_client()
        qdrant_filter = self._build_filter(filters)

        try:
            results = await asyncio.to_thread(
                client.search,
                collection_name=settings.qdrant_collection,
                query_vector=vector,
                limit=limit,
                query_filter=qdrant_filter,
                with_payload=True,
            )
            return results
        except Exception as e:
            print(f"⚠ Async search failed: {e}")
            return self._get_http_client().search(
                collection_name=settings.qdrant_collection,
                query_vector=vector,
                limit=limit,
                query_filter=qdrant_filter,
                with_payload=True,
            )

    async def batch_search(
        self, queries: List[List[float]], limit: int, filters: List[dict] = None
    ) -> List[List]:
        client = _pool.get_client()

        try:
            if _pool.use_grpc:
                qdrant_filters = [
                    self._build_filter(f) for f in (filters or [None] * len(queries))
                ]
                results = client.search_batch(
                    collection_name=settings.qdrant_collection,
                    query_vectors=queries,
                    limit=limit,
                    query_filters=qdrant_filters,
                    with_payload=True,
                )
                return results
        except Exception as e:
            print(f"⚠ gRPC batch search failed: {e}")

        results = []
        for query, filter_dict in zip(queries, filters or [None] * len(queries)):
            result = await self.async_search(query, limit, filter_dict)
            results.append(result)
        return results


async def init_qdrant():
    await _pool.initialize()


async def close_qdrant():
    await _pool.close()
