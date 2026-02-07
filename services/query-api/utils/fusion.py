from typing import Dict, List, Tuple

from config import settings


def rrf_fusion(rankings: List[List[Tuple[str, float]]]) -> Dict[str, float]:
    scores: Dict[str, float] = {}
    k = settings.rrf_k
    for ranking in rankings:
        for rank, (doc_id, _) in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return scores


def _minmax(scores: Dict[str, float]) -> Dict[str, float]:
    if not scores:
        return scores
    values = list(scores.values())
    lo, hi = min(values), max(values)
    if hi == lo:
        return {k: 1.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}


def weighted_fusion(
    vector_scores: Dict[str, float],
    bm25_scores: Dict[str, float],
) -> Dict[str, float]:
    v_norm = _minmax(vector_scores)
    b_norm = _minmax(bm25_scores)
    alpha = settings.vector_weight
    beta = settings.bm25_weight
    keys = set(v_norm) | set(b_norm)
    return {
        k: alpha * v_norm.get(k, 0.0) + beta * b_norm.get(k, 0.0)
        for k in keys
    }
