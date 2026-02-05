import hashlib
import math
from typing import List

from config import settings


class HashEmbedder:
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


def embedder_factory() -> HashEmbedder:
    return HashEmbedder(settings.embedding_dim)
