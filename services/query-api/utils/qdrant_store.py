import asyncio
from typing import List, Optional
from dataclasses import dataclass

import httpx
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Filter,
    FieldCondition,
    MatchValue,
    Distance,
    VectorParams,
)

from config import settings


@dataclass
class ScoredPoint:
    """Compatible result object for search results."""

    id: str
    score: float
    payload: dict


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

            # Force HTTP mode for compatibility with Qdrant server v1.9.1
            # The gRPC API in client v1.16.2 is not compatible with server v1.9.1
            self._client = QdrantClient(
                url=settings.qdrant_url,
                timeout=60,
                prefer_grpc=False,
            )
            self._http_client = self._client
            self._use_grpc = False
            print(f"✓ Qdrant connected via HTTP ({settings.qdrant_url})")

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

    def _ensure_initialized(self):
        """Lazily initialize the pool synchronously if not already done."""
        if _pool._client is None:
            # Force HTTP mode for compatibility with Qdrant server v1.9.1
            # The gRPC API in client v1.16.2 is not compatible with server v1.9.1
            _pool._client = QdrantClient(
                url=settings.qdrant_url,
                timeout=60,
                prefer_grpc=False,
            )
            _pool._http_client = _pool._client
            _pool._use_grpc = False
            print(f"✓ Qdrant lazy-initialized via HTTP ({settings.qdrant_url})")

    def _get_client(self) -> QdrantClient:
        self._ensure_initialized()
        return _pool._client

    def _get_http_client(self) -> QdrantClient:
        self._ensure_initialized()
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
        """Search using direct HTTP REST API for Qdrant v1.9.1 compatibility."""
        self._ensure_initialized()

        # Build request body for Qdrant v1.9.1 REST API
        body = {
            "vector": vector if isinstance(vector, list) else vector.tolist(),
            "limit": limit,
            "with_payload": True,
        }

        # Add filter if provided
        if filters:
            must_conditions = []
            for key, value in filters.items():
                if isinstance(value, list):
                    for v in value:
                        must_conditions.append({"key": key, "match": {"value": v}})
                else:
                    must_conditions.append({"key": key, "match": {"value": value}})
            if must_conditions:
                body["filter"] = {"must": must_conditions}

        # Make direct HTTP request to Qdrant REST API
        url = f"{settings.qdrant_url}/collections/{settings.qdrant_collection}/points/search"

        try:
            response = httpx.post(url, json=body, timeout=60)
            response.raise_for_status()
            data = response.json()

            # Convert response to ScoredPoint objects
            results = []
            for hit in data.get("result", []):
                results.append(
                    ScoredPoint(
                        id=str(hit.get("id", "")),
                        score=float(hit.get("score", 0.0)),
                        payload=hit.get("payload", {}),
                    )
                )
            return results
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                client = self._get_client()
                self._ensure_collection_exists(client)
                # Retry
                response = httpx.post(url, json=body, timeout=60)
                response.raise_for_status()
                data = response.json()
                results = []
                for hit in data.get("result", []):
                    results.append(
                        ScoredPoint(
                            id=str(hit.get("id", "")),
                            score=float(hit.get("score", 0.0)),
                            payload=hit.get("payload", {}),
                        )
                    )
                return results
            raise
        except Exception as e:
            print(f"⚠ Search failed: {e}")
            raise

    async def async_search(self, vector: List[float], limit: int, filters: dict = None):
        self._ensure_initialized()
        client = _pool.get_client()
        qdrant_filter = self._build_filter(filters)

        try:
            results = await asyncio.to_thread(
                client.query_points,
                collection_name=settings.qdrant_collection,
                query=vector,
                limit=limit,
                query_filter=qdrant_filter,
                with_payload=True,
            )
            return results.points
        except Exception as e:
            print(f"⚠ Async search failed: {e}")
            raise

    async def batch_search(
        self, queries: List[List[float]], limit: int, filters: List[dict] = None
    ) -> List[List]:
        """Batch search using individual query_points calls."""
        self._ensure_initialized()
        results = []
        for query, filter_dict in zip(queries, filters or [None] * len(queries)):
            result = await self.async_search(query, limit, filter_dict)
            results.append(result)
        return results


async def init_qdrant():
    await _pool.initialize()


async def close_qdrant():
    await _pool.close()
