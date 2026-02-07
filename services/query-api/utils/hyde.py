"""
HyDE (Hypothetical Document Embeddings) Implementation

HyDE improves search quality by:
1. Generating a hypothetical answer document
2. Embedding the hypothetical document
3. Using the embedding for similarity search

Reference: https://arxiv.org/abs/2212.10496
"""

import hashlib
import httpx
from typing import List, Tuple, Dict
from dataclasses import dataclass

from config import settings


@dataclass
class HypotheticalDocument:
    """A hypothetical document generated for a query."""

    query: str
    hypothetical_answer: str
    embedding: List[float]


class HyDEGenerator:
    """Generates hypothetical documents for queries using LLM."""

    def __init__(
        self,
        llm_gateway_url: str = None,
        max_length: int = None,
        temperature: float = None,
    ):
        self.llm_gateway_url = llm_gateway_url or settings.llm_gateway_url
        self.max_length = max_length or settings.hyde_max_length
        self.temperature = temperature or settings.hyde_temperature
        self._hyde_cache: Dict[str, HypotheticalDocument] = {}

    def _generate_hyde_prompt(self, query: str) -> str:
        """Generate the prompt for creating a hypothetical document."""
        return f"""Write a brief, detailed hypothetical answer to the question.
Your answer should sound like a passage from a knowledge base article.

Question: {query}

Write a 2-3 paragraph answer as if you are a documentation assistant. 
Be specific and include details that would be relevant to this question.
Keep your answer under {self.max_length} words.

Hypothetical Answer:"""

    async def generate_hypothetical(
        self, query: str, use_cache: bool = True
    ) -> HypotheticalDocument:
        """
        Generate a hypothetical document for a query.

        Args:
            query: The user's search query
            use_cache: Whether to use cached results

        Returns:
            HypotheticalDocument with the generated answer
        """
        cache_key = hashlib.md5(query.encode()).hexdigest()

        if use_cache and cache_key in self._hyde_cache:
            return self._hyde_cache[cache_key]

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.llm_gateway_url}/generate",
                    json={
                        "prompt": self._generate_hyde_prompt(query),
                        "max_tokens": self.max_length * 4,
                        "temperature": self.temperature,
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                hypothetical_answer = data.get("text", "").strip()

        except Exception as e:
            print(f"HyDE generation failed: {e}")
            hypothetical_answer = f"Answer about {query}"

        doc = HypotheticalDocument(
            query=query,
            hypothetical_answer=hypothetical_answer,
            embedding=[],
        )

        self._hyde_cache[cache_key] = doc
        return doc

    def clear_cache(self):
        """Clear the HyDE cache."""
        self._hyde_cache.clear()


class HyDEEmbedder:
    """Embeds hypothetical documents using the embedder."""

    def __init__(self, embedder=None):
        self._embedder = embedder
        self._embedding_cache: Dict[str, List[float]] = {}

    def _get_embedder(self):
        """Get or create the embedder."""
        if self._embedder is None:
            from embedding import embedder_factory

            self._embedder = embedder_factory()
        return self._embedder

    def embed_hypothetical(
        self, hypothetical: HypotheticalDocument, use_cache: bool = True
    ) -> List[float]:
        """
        Generate embedding for a hypothetical document.

        Args:
            hypothetical: The hypothetical document to embed
            use_cache: Whether to use cached embeddings

        Returns:
            Embedding vector
        """
        cache_key = hashlib.md5(hypothetical.hypothetical_answer.encode()).hexdigest()

        if use_cache and cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        embedder = self._get_embedder()
        embeddings = embedder.embed([hypothetical.hypothetical_answer])
        embedding = embeddings[0]

        self._embedding_cache[cache_key] = embedding
        return embedding

    def embed_query(
        self,
        query: str,
        hypothetical: HypotheticalDocument = None,
        use_cache: bool = True,
    ) -> List[float]:
        """
        Embed either a hypothetical document or the original query.

        Args:
            query: Original query
            hypothetical: Pre-generated hypothetical document
            use_cache: Whether to use cached embeddings

        Returns:
            Embedding vector
        """
        if hypothetical:
            return self.embed_hypothetical(hypothetical, use_cache)

        cache_key = hashlib.md5(query.encode()).hexdigest()

        if use_cache and cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        embedder = self._get_embedder()
        embeddings = embedder.embed([query])
        embedding = embeddings[0]

        self._embedding_cache[cache_key] = embedding
        return embedding

    def clear_cache(self):
        """Clear all caches."""
        self._embedding_cache.clear()


class HyDESearchEngine:
    """
    Search engine that uses HyDE for improved search quality.

    Flow:
    1. Generate hypothetical document for query
    2. Embed hypothetical document
    3. Search using HyDE embedding
    4. Rerank results
    """

    def __init__(
        self,
        hyde_generator: HyDEGenerator = None,
        hyde_embedder: HyDEEmbedder = None,
        qdrant_store=None,
        opensearch_store=None,
    ):
        self.hyde_generator = hyde_generator or HyDEGenerator()
        self.hyde_embedder = hyde_embedder or HyDEEmbedder()
        self.qdrant = qdrant_store
        self.opensearch = opensearch_store

    def configure_stores(self, qdrant_store, opensearch_store):
        """Configure the vector and BM25 stores."""
        self.qdrant = qdrant_store
        self.opensearch = opensearch_store

    async def search(
        self,
        query: str,
        tenant_id: str = None,
        top_k: int = 10,
        use_hyde: bool = None,
        filters: dict = None,
    ) -> Tuple[List[dict], HypotheticalDocument]:
        """
        Perform HyDE-enhanced search.

        Args:
            query: Search query
            tenant_id: Tenant ID for filtering
            top_k: Number of results
            use_hyde: Override HyDE setting
            filters: Additional filters

        Returns:
            Tuple of (search_results, hypothetical_document)
        """
        use_hyde = use_hyde if use_hyde is not None else settings.hyde_enabled

        if filters is None:
            filters = {}
        if tenant_id:
            filters["tenant_id"] = tenant_id

        hypothetical = None
        embedding = None

        if use_hyde:
            hypothetical = await self.hyde_generator.generate_hypothetical(query)
            embedding = self.hyde_embedder.embed_query(query, hypothetical)
        else:
            embedding = self.hyde_embedder.embed_query(query)

        vector_results = []
        if self.qdrant:
            vector_results = self.qdrant.search(
                vector=embedding,
                limit=top_k * 2,
                filters=filters if filters else None,
            )

        bm25_results = []
        if self.opensearch:
            bm25_results = self.opensearch.bm25_search(
                query=query,
                k=top_k * 2,
                filters=filters,
            )

        results = self._merge_results(vector_results, bm25_results, top_k)

        return results, hypothetical

    def _merge_results(
        self, vector_results: List, bm25_results: List, top_k: int
    ) -> List[dict]:
        """Merge vector and BM25 search results."""
        from fusion import rrf_fusion

        v_rank = []
        for hit in vector_results:
            doc_id = hit.payload.get("doc_id")
            chunk_index = hit.payload.get("chunk_index")
            v_rank.append((f"{doc_id}:{chunk_index}", float(hit.score)))

        b_rank = []
        for hit in bm25_results.get("hits", {}).get("hits", []):
            doc_id = hit["_source"]["doc_id"]
            chunk_index = hit["_source"]["chunk_index"]
            b_rank.append((f"{doc_id}:{chunk_index}", float(hit.get("_score", 0.0))))

        v_scores = {k: s for k, s in v_rank}
        b_scores = {k: s for k, s in b_rank}

        if settings.fusion_method == "weighted":
            from fusion import weighted_fusion

            fusion_scores = weighted_fusion(v_scores, b_scores)
        else:
            fusion_scores = rrf_fusion([v_rank, b_rank])

        ranked = sorted(fusion_scores.items(), key=lambda x: x[1], reverse=True)
        return [{"id": item_id, "score": score} for item_id, score in ranked[:top_k]]

    def clear_caches(self):
        """Clear all internal caches."""
        self.hyde_generator.clear_cache()
        self.hyde_embedder.clear_cache()
