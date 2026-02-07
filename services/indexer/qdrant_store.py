import asyncio
import threading
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from qdrant_client.http.exceptions import UnexpectedResponse

from config import settings


class QdrantConnectionPool:
    _instance: Optional["QdrantConnectionPool"] = None
    _lock: threading.Lock = threading.Lock()
    _async_lock: asyncio.Lock = asyncio.Lock()

    def __init__(self):
        self._client: Optional[QdrantClient] = None
        self._http_client: Optional[QdrantClient] = None
        self._use_grpc = True
        self._initialized = False

    def _initialize_sync(self):
        """Synchronous initialization for non-async contexts."""
        with self._lock:
            if self._initialized:
                return

            try:
                # Try HTTP first (simpler, always works)
                self._http_client = QdrantClient(
                    url=settings.qdrant_url,
                    timeout=30,
                )

                # Try gRPC if available
                grpc_port = getattr(settings, "qdrant_grpc_port", 6334)
                try:
                    self._client = QdrantClient(
                        host="localhost",
                        port=grpc_port,
                        prefer_grpc=True,
                        grpc_timeout=60,
                        max_message_size=104857600,
                    )
                    self._use_grpc = True
                    print(f"✓ Qdrant connected via gRPC (port {grpc_port})")
                except Exception as e:
                    print(f"⚠ gRPC connection failed, using HTTP: {e}")
                    self._client = self._http_client
                    self._use_grpc = False

                self._initialized = True
            except Exception as e:
                print(f"❌ Failed to initialize Qdrant connection: {e}")
                raise

    async def initialize(self):
        """Async initialization."""
        if self._initialized:
            return

        async with self._async_lock:
            if self._initialized:
                return

            # Run sync initialization in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._initialize_sync)

    def get_client(self) -> QdrantClient:
        if not self._initialized:
            self._initialize_sync()
        return self._client

    def get_http_client(self) -> QdrantClient:
        if not self._initialized:
            self._initialize_sync()
        return self._http_client

    @property
    def use_grpc(self) -> bool:
        if not self._initialized:
            self._initialize_sync()
        return self._use_grpc

    async def close(self):
        if self._client:
            self._client.close()
        if self._http_client and self._http_client != self._client:
            self._http_client.close()


_pool = QdrantConnectionPool()


def get_pool() -> QdrantConnectionPool:
    """Get or initialize the Qdrant connection pool (sync version)."""
    if not _pool._initialized:
        _pool._initialize_sync()
    return _pool


async def get_pool_async() -> QdrantConnectionPool:
    """Get or initialize the Qdrant connection pool (async version)."""
    if not _pool._initialized:
        await _pool.initialize()
    return _pool


class QdrantStore:
    def __init__(self, use_grpc: bool = None):
        self._use_grpc = use_grpc
        # Ensure pool is initialized
        if not _pool._initialized:
            _pool._initialize_sync()

    def _get_client(self) -> QdrantClient:
        return _pool.get_client()

    def _get_http_client(self) -> QdrantClient:
        return _pool.get_http_client()

    def ensure_collection_sync(self) -> None:
        """Synchronous version for non-async contexts."""
        client = self._get_http_client()
        try:
            collections = client.get_collections()
            if any(
                c.name == settings.qdrant_collection for c in collections.collections
            ):
                return
        except UnexpectedResponse:
            pass
        except Exception as e:
            print(f"⚠ Warning checking collections: {e}")

        try:
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

    async def ensure_collection(self) -> None:
        """Async version."""
        self.ensure_collection_sync()

    def upsert(
        self,
        ids: List[str],
        vectors: List[List[float]],
        payloads: List[dict],
        batch_size: int = 100,
    ) -> None:
        client = self._get_client()
        total = len(ids)

        for i in range(0, total, batch_size):
            batch_ids = ids[i : i + batch_size]
            batch_vectors = vectors[i : i + batch_size]
            batch_payloads = payloads[i : i + batch_size]

            points = [
                PointStruct(id=bid, vector=bvec, payload=bpayload)
                for bid, bvec, bpayload in zip(batch_ids, batch_vectors, batch_payloads)
            ]

            def _do_upsert(c):
                if self._use_grpc if self._use_grpc is not None else _pool.use_grpc:
                    try:
                        c.upsert(
                            collection_name=settings.qdrant_collection,
                            points=points,
                            wait=True,
                        )
                    except Exception as e:
                        print(f"⚠ gRPC upsert failed, falling back to HTTP: {e}")
                        self._get_http_client().upsert(
                            collection_name=settings.qdrant_collection,
                            points=points,
                            wait=True,
                        )
                else:
                    self._get_http_client().upsert(
                        collection_name=settings.qdrant_collection,
                        points=points,
                        wait=True,
                    )

            try:
                _do_upsert(client)
            except Exception as e:
                # If 404/UnexpectedResponse, the collection might have been deleted
                if "404" in str(e) or "Not Found" in str(e):
                    print(
                        f"⚠️ Collection {settings.qdrant_collection} not found during upsert. Recreating..."
                    )
                    self.ensure_collection_sync()
                    _do_upsert(client)
                else:
                    raise

    async def async_upsert(
        self,
        ids: List[str],
        vectors: List[List[float]],
        payloads: List[dict],
        batch_size: int = 100,
        max_concurrent: int = 4,
    ) -> None:
        semaphore = asyncio.Semaphore(max_concurrent)
        total = len(ids)

        async def upsert_batch(start: int):
            end = min(start + batch_size, total)
            batch_ids = ids[start:end]
            batch_vectors = vectors[start:end]
            batch_payloads = payloads[start:end]

            points = [
                PointStruct(id=bid, vector=bvec, payload=bpayload)
                for bid, bvec, bpayload in zip(batch_ids, batch_vectors, batch_payloads)
            ]

            async with semaphore:
                try:
                    self._get_client().upsert(
                        collection_name=settings.qdrant_collection,
                        points=points,
                        wait=False,
                    )
                except Exception as e:
                    print(f"⚠ Async upsert failed: {e}, retrying with HTTP")
                    self._get_http_client().upsert(
                        collection_name=settings.qdrant_collection,
                        points=points,
                        wait=True,
                    )

        tasks = [upsert_batch(i) for i in range(0, total, batch_size)]
        await asyncio.gather(*tasks)


class AsyncQdrantStore:
    def __init__(self, pool: QdrantConnectionPool = None):
        self._pool = pool or _pool

    async def search(
        self, vector: List[float], limit: int, filters: dict = None
    ) -> List:
        client = self._pool.get_client()
        try:
            results = client.search(
                collection_name=settings.qdrant_collection,
                query_vector=vector,
                limit=limit,
                query_filter=filters,
                with_payload=True,
            )
            return results
        except Exception as e:
            print(f"⚠ gRPC search failed: {e}, falling back to HTTP")
            return self._pool.get_http_client().search(
                collection_name=settings.qdrant_collection,
                query_vector=vector,
                limit=limit,
                query_filter=filters,
                with_payload=True,
            )

    async def batch_search(
        self, queries: List[List[float]], limit: int, filters: List[dict] = None
    ) -> List[List]:
        client = self._pool.get_client()
        try:
            results = client.search_batch(
                collection_name=settings.qdrant_collection,
                query_vectors=queries,
                limit=limit,
                query_filters=filters,
                with_payload=True,
            )
            return results
        except Exception as e:
            print(f"⚠ gRPC batch search failed: {e}")
            return [
                self.search(q, limit, f if filters else None)
                for q, f in zip(queries, filters or [])
            ]

    async def upsert(
        self,
        ids: List[str],
        vectors: List[List[float]],
        payloads: List[dict],
        batch_size: int = 100,
    ) -> None:
        client = self._pool.get_http_client()
        total = len(ids)

        for i in range(0, total, batch_size):
            batch_ids = ids[i : i + batch_size]
            batch_vectors = vectors[i : i + batch_size]
            batch_payloads = payloads[i : i + batch_size]

            points = [
                PointStruct(id=bid, vector=bvec, payload=bpayload)
                for bid, bvec, bpayload in zip(batch_ids, batch_vectors, batch_payloads)
            ]

            client.upsert(
                collection_name=settings.qdrant_collection, points=points, wait=True
            )

    async def delete_points(self, ids: List[str]) -> None:
        client = self._pool.get_client()
        try:
            client.delete(
                collection_name=settings.qdrant_collection,
                points_selector=ids,
                wait=True,
            )
        except Exception as e:
            print(f"⚠ gRPC delete failed: {e}")
            self._pool.get_http_client().delete(
                collection_name=settings.qdrant_collection,
                points_selector=ids,
                wait=True,
            )
