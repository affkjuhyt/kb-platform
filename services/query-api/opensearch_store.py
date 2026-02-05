from opensearchpy import OpenSearch

from config import settings


class OpenSearchStore:
    def __init__(self):
        self._client = OpenSearch(settings.opensearch_url)
        self._index = settings.opensearch_index

    def bm25_search(self, query: str, k: int, filters: dict | None = None):
        must = [{"match": {"text": query}}]
        if filters:
            for key, value in filters.items():
                must.append({"term": {key: value}})
        body = {"size": k, "query": {"bool": {"must": must}}}
        return self._client.search(index=self._index, body=body)
