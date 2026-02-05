from datetime import datetime, UTC
from typing import List
import logging

from fastapi import FastAPI
from pydantic import BaseModel, Field

from config import settings

logger = logging.getLogger("rerank")


class Candidate(BaseModel):
    id: str
    text: str
    score: float | None = None


class RerankRequest(BaseModel):
    query: str = Field(..., min_length=1)
    candidates: List[Candidate]


class RerankResponse(BaseModel):
    results: List[Candidate]


app = FastAPI(title="Rerank Service")


@app.get("/healthz")
def healthz():
    return {"status": "ok", "time": datetime.now(UTC).isoformat()}


_cross_encoder = None
_failed = False


def _get_model():
    global _cross_encoder, _failed
    if _failed:
        return None
    if _cross_encoder is None:
        try:
            from sentence_transformers import CrossEncoder

            _cross_encoder = CrossEncoder(settings.model, device=settings.device)
        except Exception as exc:
            logger.warning("Failed to load cross-encoder: %s", exc)
            _failed = True
            return None
    return _cross_encoder


def _basic_rerank(query: str, texts: List[str]) -> List[float]:
    """Basic lexical reranking using term overlap with TF-IDF weighting."""
    import math

    q_terms = query.lower().split()
    q_term_freq = {}
    for term in q_terms:
        q_term_freq[term] = q_term_freq.get(term, 0) + 1

    scores = []
    for text in texts:
        t_terms = text.lower().split()
        t_term_freq = {}
        for term in t_terms:
            t_term_freq[term] = t_term_freq.get(term, 0) + 1

        # Calculate cosine similarity
        dot_product = 0
        for term, q_freq in q_term_freq.items():
            if term in t_term_freq:
                # Simple TF weighting
                dot_product += q_freq * t_term_freq[term]

        q_norm = math.sqrt(sum(f * f for f in q_term_freq.values()))
        t_norm = math.sqrt(sum(f * f for f in t_term_freq.values()))

        if q_norm == 0 or t_norm == 0:
            scores.append(0.0)
        else:
            scores.append(dot_product / (q_norm * t_norm))

    return scores


def _normalize_scores(scores: List[float]) -> List[float]:
    """Normalize scores to [0, 1] range using min-max normalization."""
    if not scores:
        return scores

    min_score = min(scores)
    max_score = max(scores)

    if max_score == min_score:
        return [0.5 for _ in scores]

    return [(s - min_score) / (max_score - min_score) for s in scores]


@app.post("/rerank", response_model=RerankResponse)
def rerank(payload: RerankRequest):
    """Rerank candidates using cross-encoder with top-k selection."""
    if not payload.candidates:
        return RerankResponse(results=[])

    texts = [c.text for c in payload.candidates]
    model = _get_model()

    # Score computation
    if model is None:
        logger.info("Using basic reranking (cross-encoder unavailable)")
        scores = _basic_rerank(payload.query, texts)
    else:
        logger.info(f"Using cross-encoder: {settings.model}")
        # Process in batches if needed
        scores = []
        for i in range(0, len(texts), settings.max_batch):
            batch_texts = texts[i : i + settings.max_batch]
            pairs = [(payload.query, t) for t in batch_texts]
            batch_scores = model.predict(pairs)
            scores.extend(batch_scores)

    # Normalize scores if enabled
    if settings.normalize_scores:
        scores = _normalize_scores(scores)

    # Build results with scores
    results = [
        Candidate(
            id=payload.candidates[i].id,
            text=payload.candidates[i].text,
            score=float(scores[i]),
        )
        for i in range(len(payload.candidates))
    ]

    # Sort by score descending
    results.sort(key=lambda x: x.score or 0.0, reverse=True)

    # Return top-k only
    top_results = results[: settings.top_k]

    logger.info(
        f"Reranked {len(payload.candidates)} candidates, "
        f"returning top {len(top_results)}"
    )

    return RerankResponse(results=top_results)
