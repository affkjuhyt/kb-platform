from opensearchpy import OpenSearch

from config import settings


class OpenSearchStore:
    def __init__(self):
        self._client = OpenSearch(settings.opensearch_url)
        self._index = settings.opensearch_index

    def ensure_index(self) -> None:
        if self._client.indices.exists(self._index):
            return
        body = {
            "settings": {"index": {"number_of_shards": 1, "number_of_replicas": 0}},
            "mappings": {
                "properties": {
                    "doc_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "source": {"type": "keyword"},
                    "source_id": {"type": "keyword"},
                    "version": {"type": "integer"},
                    "chunk_index": {"type": "integer"},
                    "text": {"type": "text"},
                    "section_path": {"type": "keyword"},
                }
            },
        }
        self._client.indices.create(index=self._index, body=body)

    def index_chunk(self, chunk_id: str, body: dict) -> None:
        self._client.index(index=self._index, id=chunk_id, body=body, refresh=False)
