import os
from typing import List, Optional

from config import settings

# Lazy load to avoid import time overhead
_embedder: Optional["SentenceTransformerEmbedder"] = None


class SentenceTransformerEmbedder:
    """Semantic embedder using SentenceTransformers."""

    def __init__(self, model_name: str = "BAAI/bge-m3", dim: int = 768):
        from sentence_transformers import SentenceTransformer

        self.dim = dim
        self.model_name = model_name

        # Set cache directory
        cache_dir = os.environ.get("TRANSFORMERS_CACHE", "/tmp/transformers_cache")

        print(f"⏳ Loading embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name, cache_folder=cache_dir)
        print(f"✓ Embedding model loaded: {model_name}")

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        if not texts:
            return []

        # Normalize and encode
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        """Embed a single query with query-specific prefix for bge/e5 models."""
        # BGE and E5 models benefit from "query: " prefix for queries
        if "bge" in self.model_name.lower() or "e5" in self.model_name.lower():
            query = f"query: {query}"

        return self.embed([query])[0]

    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        """Embed documents with document-specific prefix for bge/e5 models."""
        # BGE and E5 models benefit from "passage: " prefix for documents
        if "bge" in self.model_name.lower() or "e5" in self.model_name.lower():
            documents = [f"passage: {doc}" for doc in documents]

        return self.embed(documents)


def embedder_factory() -> SentenceTransformerEmbedder:
    """Get or create the singleton embedder instance."""
    global _embedder

    if _embedder is None:
        # Use environment variable or default model
        model_name = os.environ.get("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
        _embedder = SentenceTransformerEmbedder(
            model_name=model_name,
            dim=settings.embedding_dim,
        )

    return _embedder
