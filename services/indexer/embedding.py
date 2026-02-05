import hashlib
import math
import asyncio
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor

from config import settings


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

        self._model = SentenceTransformer(model_name)
        self._dim = dim
        self._batch_size = batch_size
        self._executor = ThreadPoolExecutor(max_workers=num_workers)
        self._model_name = model_name

    def embed(self, texts: List[str]) -> List[List[float]]:
        vectors = self._model.encode(
            texts, normalize_embeddings=True, batch_size=self._batch_size
        )
        return [v.tolist() for v in vectors]

    async def aembed(self, texts: List[str]) -> List[List[float]]:
        loop = asyncio.get_event_loop()
        vectors = await loop.run_in_executor(self._executor, self._model.encode, texts)
        return [v.tolist() for v in vectors]


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


def embedder_factory() -> BaseEmbedder:
    if settings.embedding_backend == "sentence-transformers":
        batch_size = getattr(settings, "embedding_batch_size", 32)
        num_workers = getattr(settings, "embedding_num_workers", 4)
        model_name = getattr(
            settings, "embedding_model", "intfloat/multilingual-e5-base"
        )
        return SentenceTransformerEmbedder(
            model_name, settings.embedding_dim, batch_size, num_workers
        )
    return HashEmbedder(settings.embedding_dim)


def async_embedder_factory() -> AsyncBatchEmbedder:
    embedder = embedder_factory()
    max_batch_size = getattr(settings, "embedding_batch_size", 32)
    return AsyncBatchEmbedder(embedder, max_batch_size=max_batch_size)
