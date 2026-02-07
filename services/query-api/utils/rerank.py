from typing import List, Tuple
import logging
import time

from config import settings

logger = logging.getLogger("query-api.rerank")


def basic_rerank(query: str, texts: List[str]) -> List[float]:
    start = time.perf_counter()
    q_terms = set(query.lower().split())
    scores = []
    for text in texts:
        t_terms = set(text.lower().split())
        overlap = len(q_terms & t_terms)
        scores.append(float(overlap))
    duration = (time.perf_counter() - start) * 1000
    print(f"🧠 Basic rerank took {duration:.2f}ms for {len(texts)} texts")
    return scores


logger = logging.getLogger("rerank")
_cross_encoder = None
_cross_encoder_failed = False


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
