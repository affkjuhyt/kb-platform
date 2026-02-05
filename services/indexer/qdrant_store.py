from typing import List

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct

from config import settings


class QdrantStore:
    def __init__(self):
        self._client = QdrantClient(url=settings.qdrant_url)
        self._collection = settings.qdrant_collection

    def ensure_collection(self) -> None:
        collections = self._client.get_collections().collections
        if any(c.name == self._collection for c in collections):
            return

        self._client.create_collection(
            collection_name=self._collection,
            vectors_config=VectorParams(
                size=settings.embedding_dim, distance=Distance.COSINE
            ),
        )

    def upsert(
        self, ids: List[str], vectors: List[List[float]], payloads: List[dict]
    ) -> None:
        points = [
            PointStruct(id=ids[i], vector=vectors[i], payload=payloads[i])
            for i in range(len(ids))
        ]
        self._client.upsert(collection_name=self._collection, points=points)
