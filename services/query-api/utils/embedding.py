import os
from typing import List, Optional

from config import settings

# Lazy load to avoid import time overhead
_embedder: Optional["SentenceTransformerEmbedder"] = None


class SentenceTransformerEmbedder:
    """Semantic embedder optimized for CPU using FastEmbed."""

    def __init__(
        self, model_name: str = "intfloat/multilingual-e5-large", dim: int = 1024
    ):
        try:
            from fastembed import TextEmbedding

            # Map common HF models to fastembed models if possible
            # intfloat/multilingual-e5-base -> intfloat/multilingual-e5-base
            self.model_name = model_name
            self.dim = dim

            # Set cache directory - use HF_HOME as primary
            cache_dir = os.environ.get(
                "HF_HOME",
                os.environ.get("SENTENCE_TRANSFORMERS_HOME", "/tmp/fastembed_cache"),
            )

            print(f"⏳ Loading FastEmbed model: {model_name}...")
            self.model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)
            self.backend = "fastembed"
            print(f"✓ FastEmbed model loaded: {model_name}")
        except Exception as e:
            print(f"⚠ FastEmbed load failed, falling back to SentenceTransformers: {e}")
            from sentence_transformers import SentenceTransformer

            self.model_name = model_name
            self.dim = dim
            cache_dir = os.environ.get(
                "HF_HOME",
                os.environ.get("TRANSFORMERS_CACHE", "/tmp/transformers_cache"),
            )
            self.model = SentenceTransformer(model_name, cache_folder=cache_dir)
            self.backend = "sentence-transformers"

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        if not texts:
            return []

        if self.backend == "fastembed":
            # fastembed returns a generator
            embeddings = list(self.model.embed(texts))
            return [e.tolist() for e in embeddings]
        else:
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
        model_name = os.environ.get("EMBEDDING_MODEL", "intfloat/multilingual-e5-large")
        _embedder = SentenceTransformerEmbedder(
            model_name=model_name,
            dim=settings.embedding_dim,
        )

    return _embedder
