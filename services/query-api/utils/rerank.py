"""
Reranking utilities for query-api.
Supports both local FlashRank and basic fallback reranking.
"""

from typing import List, Tuple
import logging
import time
import os

from config import settings

logger = logging.getLogger("query-api.rerank")

# Global reranker instances (lazy loaded)
_flashrank_ranker = None
_flashrank_failed = False

_cross_encoder = None
_cross_encoder_failed = False


def get_local_reranker():
    """Get or initialize the local FlashRank reranker."""
    global _flashrank_ranker, _flashrank_failed

    if _flashrank_failed:
        return None

    if _flashrank_ranker is None:
        try:
            from flashrank import Ranker

            cache_dir = os.getenv("HF_HOME", "/models/hf")
            model_name = getattr(
                settings, "rerank_model_local", "ms-marco-MiniLM-L-12-v2"
            )
            _flashrank_ranker = Ranker(model_name=model_name, cache_dir=cache_dir)
            logger.info(f"✓ FlashRank Ranker ({model_name}) loaded locally")
        except Exception as exc:
            logger.warning(f"Failed to load FlashRank locally: {exc}")
            _flashrank_failed = True
            return None

    return _flashrank_ranker


def rerank_local(
    query: str, candidates: List[Tuple[any, float]]
) -> List[Tuple[any, float]]:
    """
    Rerank candidates using local FlashRank model.

    Args:
        query: Search query
        candidates: List of (chunk, score) tuples

    Returns:
        Reranked list of (chunk, score) tuples
    """
    ranker = get_local_reranker()
    if ranker is None:
        logger.warning("FlashRank not available, returning original candidates")
        return candidates

    # Prepare passages for FlashRank
    passages = [
        {
            "id": i,
            "text": chunk.text,
        }
        for i, (chunk, _) in enumerate(candidates)
    ]

    # Rerank
    results = ranker.rerank(query, passages)

    # Map back to original candidates with new scores
    reranked = []
    for result in results:
        idx = result["id"]
        chunk, _ = candidates[idx]
        reranked.append((chunk, result["score"]))

    logger.info(
        f"Reranked {len(candidates)} candidates locally, returning top {len(reranked)}"
    )
    return reranked


def basic_rerank(query: str, texts: List[str]) -> List[float]:
    """
    Basic fallback reranking using simple text matching.

    Args:
        query: Search query
        texts: List of text chunks

    Returns:
        List of scores
    """
    start = time.perf_counter()
    query_lower = query.lower()
    query_terms = set(query_lower.split())

    scores = []
    for text in texts:
        text_lower = text.lower()
        # Simple scoring: count matching terms
        matches = sum(1 for term in query_terms if term in text_lower)
        # Normalize by query length
        score = matches / len(query_terms) if query_terms else 0.0
        scores.append(score)
    duration = (time.perf_counter() - start) * 1000
    print(f"🧠 Basic rerank took {duration:.2f}ms for {len(texts)} texts")
    return scores


def _get_cross_encoder():
    global _cross_encoder, _cross_encoder_failed
    if _cross_encoder_failed:
        return None
    if _cross_encoder is None:
        try:
            from sentence_transformers import CrossEncoder

            _cross_encoder = CrossEncoder(settings.rerank_model, device="cpu")
        except Exception as exc:
            logger.warning("Failed to load cross-encoder: %s", exc)
            _cross_encoder_failed = True
            return None
    return _cross_encoder


def cross_encoder_rerank(query: str, texts: List[str]) -> List[float]:
    start = time.perf_counter()
    model = _get_cross_encoder()
    if model is None:
        return basic_rerank(query, texts)
    pairs: List[Tuple[str, str]] = [(query, t) for t in texts]
    scores = model.predict(pairs)
    duration = (time.perf_counter() - start) * 1000
    logger.info(
        "🧠 Cross-encoder rerank took %.2fms for %d texts", duration, len(texts)
    )
    return [float(s) for s in scores]
