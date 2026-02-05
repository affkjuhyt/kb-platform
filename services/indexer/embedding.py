import hashlib
import math
from typing import List

from config import settings


class BaseEmbedder:
    def embed(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError


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
    def __init__(self, model_name: str, dim: int):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self._dim = dim

    def embed(self, texts: List[str]) -> List[List[float]]:
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vectors]


_def_model = "intfloat/multilingual-e5-base"


def embedder_factory() -> BaseEmbedder:
    if settings.embedding_backend == "sentence-transformers":
        model_name = getattr(settings, "embedding_model", _def_model)
        return SentenceTransformerEmbedder(model_name, settings.embedding_dim)
    return HashEmbedder(settings.embedding_dim)
