import os
import hashlib
import math
import asyncio
from typing import List
from concurrent.futures import ThreadPoolExecutor

from config import settings

# Global singleton instance
_embedder = None

print(
    f"DEBUG: embedding.py module load - PID: {os.getpid()}, Name: {__name__}, Path: {__file__}"
)


class BaseEmbedder:
    def embed(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError

    async def aembed(self, texts: List[str]) -> List[List[float]]:
        return self.embed(texts)


class HashEmbedder(BaseEmbedder):
    def __init__(self, dim: int):
        self.dim = dim

    def embed(self, texts: List[str]) -> List[List[float]]:
        vectors: List[List[float]] = []
        for text in texts:
            vec = [0.0] * self.dim
            for token in text.split():
                h = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
                idx = h % self.dim
                vec[idx] += 1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            vectors.append([v / norm for v in vec])
        return vectors


class SentenceTransformerEmbedder(BaseEmbedder):
    def __init__(
        self, model_name: str, dim: int, batch_size: int = 32, num_workers: int = 4
    ):
        from sentence_transformers import SentenceTransformer

        # Set cache directory
        os.environ.setdefault("TRANSFORMERS_CACHE", "/tmp/transformers_cache")

        print(f"⏳ Loading embedding model: {model_name}... (PID: {os.getpid()})")
        self._model = SentenceTransformer(model_name)
        self._dim = dim
        self._batch_size = batch_size
        self._executor = ThreadPoolExecutor(max_workers=num_workers)
        self._model_name = model_name
        print(f"✓ Embedding model loaded: {model_name} (PID: {os.getpid()})")

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        vectors = self._model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=self._batch_size,
            show_progress_bar=False,
        )
        return [v.tolist() for v in vectors]

    async def aembed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        loop = asyncio.get_event_loop()
        vectors = await loop.run_in_executor(
            self._executor,
            self._model.encode,
            texts,
            self._batch_size,
            True,  # normalize_embeddings
            None,  # device
            False,  # show_progress_bar
        )
        return [v.tolist() for v in vectors]

    def embed_query(self, query: str) -> List[float]:
        """Embed a single query with query-specific prefix for bge/e5 models."""
        if "bge" in self._model_name.lower() or "e5" in self._model_name.lower():
            query = f"query: {query}"
        return self.embed([query])[0]

    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        """Embed documents with document-specific prefix for bge/e5 models."""
        if "bge" in self._model_name.lower() or "e5" in self._model_name.lower():
            documents = [f"passage: {doc}" for doc in documents]
        return self.embed(documents)

    async def aembed_documents(self, documents: List[str]) -> List[List[float]]:
        """Async embed documents with document-specific prefix for bge/e5 models."""
        if "bge" in self._model_name.lower() or "e5" in self._model_name.lower():
            documents = [f"passage: {doc}" for doc in documents]
        return await self.aembed(documents)


class AsyncBatchEmbedder:
    def __init__(
        self,
        embedder: BaseEmbedder,
        max_batch_size: int = 32,
        max_concurrent_batches: int = 4,
    ):
        self._embedder = embedder
        self._max_batch_size = max_batch_size
        self._semaphore = asyncio.Semaphore(max_concurrent_batches)

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if len(texts) <= self._max_batch_size:
            return await self._embedder.aembed(texts)

        results = []
        for i in range(0, len(texts), self._max_batch_size):
            batch = texts[i : i + self._max_batch_size]
            async with self._semaphore:
                batch_results = await self._embedder.aembed(batch)
            results.extend(batch_results)

        return results

    async def embed_with_cache(
        self, texts: List[str], cache: dict
    ) -> List[List[float]]:
        uncached_texts = []
        uncached_indices = []
        cached_results = {}

        for i, text in enumerate(texts):
            text_hash = hashlib.md5(text.encode()).hexdigest()
            if text_hash in cache:
                cached_results[i] = cache[text_hash]
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)

        if uncached_texts:
            embedded = await self.embed(uncached_texts)
            for idx, emb in zip(uncached_indices, embedded):
                text_hash = hashlib.md5(texts[idx].encode()).hexdigest()
                cache[text_hash] = emb
                cached_results[idx] = emb

        return [cached_results[i] for i in range(len(texts))]


class FastEmbedEmbedder(BaseEmbedder):
    """Semantic embedder optimized for CPU using FastEmbed."""

    def __init__(self, model_name: str, dim: int, threads: int = 4):
        try:
            from fastembed import TextEmbedding

            self._dim = dim
            self._model_name = model_name
            # Set cache directory - use HF_HOME as primary
            cache_dir = os.environ.get(
                "HF_HOME",
                os.environ.get("SENTENCE_TRANSFORMERS_HOME", "/tmp/fastembed_cache"),
            )

            print(f"⏳ Loading FastEmbed model: {model_name}... (PID: {os.getpid()})")
            self._model = TextEmbedding(
                model_name=model_name, cache_dir=cache_dir, threads=threads
            )
            self._backend = "fastembed"
            print(f"✓ FastEmbed model loaded: {model_name} (PID: {os.getpid()})")
        except Exception as e:
            print(
                f"⚠ FastEmbed load failed, falling back to SentenceTransformers: {e} (PID: {os.getpid()})"
            )
            from sentence_transformers import SentenceTransformer

            self._model_name = model_name
            self._dim = dim
            cache_dir = os.environ.get(
                "HF_HOME",
                os.environ.get("TRANSFORMERS_CACHE", "/tmp/transformers_cache"),
            )
            self._model = SentenceTransformer(model_name, cache_folder=cache_dir)
            self._backend = "sentence-transformers"
            from concurrent.futures import ThreadPoolExecutor

            self._executor = ThreadPoolExecutor(max_workers=threads)

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if self._backend == "fastembed":
            embeddings = list(self._model.embed(texts))
            return [e.tolist() for e in embeddings]
        else:
            vectors = self._model.encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return [v.tolist() for v in vectors]

    async def aembed(self, texts: List[str]) -> List[List[float]]:
        # FastEmbed is generally fast enough to run in thread, or is already optimized
        return self.embed(texts)

    def embed_query(self, query: str) -> List[float]:
        if "bge" in self._model_name.lower() or "e5" in self._model_name.lower():
            query = f"query: {query}"
        return self.embed([query])[0]

    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        if "bge" in self._model_name.lower() or "e5" in self._model_name.lower():
            documents = [f"passage: {doc}" for doc in documents]
        return self.embed(documents)

    async def aembed_documents(self, documents: List[str]) -> List[List[float]]:
        return self.embed_documents(documents)


def embedder_factory() -> BaseEmbedder:
    global _embedder
    if _embedder is None:
        print(
            f"DEBUG: embedder_factory INITIALIZING new embedder in PID: {os.getpid()}"
        )
        num_workers = getattr(settings, "embedding_num_workers", 4)
        model_name = getattr(
            settings, "embedding_model", "intfloat/multilingual-e5-large"
        )
        _embedder = FastEmbedEmbedder(model_name, settings.embedding_dim, num_workers)
    else:
        print(
            f"DEBUG: embedder_factory returning EXISTING singleton in PID: {os.getpid()}"
        )
    return _embedder


def async_embedder_factory() -> AsyncBatchEmbedder:
    embedder = embedder_factory()
    max_batch_size = getattr(settings, "embedding_batch_size", 32)
    return AsyncBatchEmbedder(embedder, max_batch_size=max_batch_size)
