from qdrant_client import QdrantClient

from config import settings


class QdrantStore:
    def __init__(self):
        self._client = QdrantClient(url=settings.qdrant_url)
        self._collection = settings.qdrant_collection

    def search(self, vector, limit: int, filters: dict | None = None):
        return self._client.search(
            collection_name=self._collection,
            query_vector=vector,
            limit=limit,
            query_filter=filters,
            with_payload=True,
        )
