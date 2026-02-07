import time
import logging
from opensearchpy import OpenSearch

from config import settings

logger = logging.getLogger("query-api.opensearch")


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

        start_search = time.perf_counter()
        res = self._client.search(index=self._index, body=body)
        search_time = (time.perf_counter() - start_search) * 1000
        print(f"📡 OpenSearch BM25 search took {search_time:.2f}ms")
        return res
