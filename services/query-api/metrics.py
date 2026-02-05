"""
Evaluation metrics for the RAG system.

Includes:
- nDCG@k (Normalized Discounted Cumulative Gain)
- Precision@k
- Recall@k
- MAP (Mean Average Precision)
"""

import math
from typing import Dict, List, Tuple


def dcg_at_k(relevances: List[float], k: int) -> float:
    """
    Calculate DCG (Discounted Cumulative Gain) at position k.

    DCG = sum_{i=1}^k (2^rel_i - 1) / log2(i + 1)

    Args:
        relevances: List of relevance scores (0, 1, 2, etc.) in ranked order
        k: Position to calculate DCG at

    Returns:
        DCG score
    """
    if k <= 0 or not relevances:
        return 0.0

    dcg = 0.0
    for i, rel in enumerate(relevances[:k], start=1):
        # Use log2(i + 1) to discount positions
        dcg += (2**rel - 1) / math.log2(i + 1)

    return dcg


def ndcg_at_k(relevances: List[float], k: int) -> float:
    """
    Calculate nDCG (Normalized DCG) at position k.

    nDCG = DCG / IDCG
    where IDCG is the ideal DCG (sorted by relevance)

    Args:
        relevances: List of relevance scores in ranked order
        k: Position to calculate nDCG at

    Returns:
        nDCG score between 0 and 1
    """
    if k <= 0 or not relevances:
        return 0.0

    dcg = dcg_at_k(relevances, k)

    # Calculate ideal DCG (sorted by relevance descending)
    ideal_relevances = sorted(relevances, reverse=True)
    idcg = dcg_at_k(ideal_relevances, k)

    if idcg == 0:
        return 0.0

    return dcg / idcg


def precision_at_k(relevances: List[int], k: int) -> float:
    """
    Calculate Precision@k.

    Precision = (# relevant items in top-k) / k

    Args:
        relevances: List of binary relevance (0 or 1) in ranked order
        k: Position to calculate precision at

    Returns:
        Precision score between 0 and 1
    """
    if k <= 0:
        return 0.0

    top_k = relevances[:k]
    if not top_k:
        return 0.0

    return sum(1 for r in top_k if r > 0) / k


def recall_at_k(relevances: List[int], total_relevant: int, k: int) -> float:
    """
    Calculate Recall@k.

    Recall = (# relevant items in top-k) / (total # relevant items)

    Args:
        relevances: List of binary relevance (0 or 1) in ranked order
        total_relevant: Total number of relevant items in the collection
        k: Position to calculate recall at

    Returns:
        Recall score between 0 and 1
    """
    if total_relevant <= 0:
        return 0.0

    top_k = relevances[:k]
    relevant_in_k = sum(1 for r in top_k if r > 0)

    return relevant_in_k / total_relevant


def average_precision(relevances: List[int]) -> float:
    """
    Calculate Average Precision (AP).

    AP = (1/R) * sum_{i=1}^n Precision@i * rel(i)
    where R is total number of relevant items

    Args:
        relevances: List of binary relevance (0 or 1) in ranked order

    Returns:
        Average precision score
    """
    if not relevances:
        return 0.0

    num_relevant = sum(relevances)
    if num_relevant == 0:
        return 0.0

    ap = 0.0
    num_seen_relevant = 0

    for i, rel in enumerate(relevances, start=1):
        if rel > 0:
            num_seen_relevant += 1
            ap += num_seen_relevant / i

    return ap / num_relevant


def mean_average_precision(relevances_list: List[List[int]]) -> float:
    """
    Calculate Mean Average Precision (MAP) across multiple queries.

    Args:
        relevances_list: List of relevance lists for each query

    Returns:
        MAP score
    """
    if not relevances_list:
        return 0.0

    aps = [average_precision(rel) for rel in relevances_list]
    return sum(aps) / len(aps)


def evaluate_ranking(
    predicted_ranking: List[str],
    ground_truth: Dict[str, float],
    k_values: List[int] = [5, 10],
) -> Dict[str, float]:
    """
    Evaluate a ranking against ground truth.

    Args:
        predicted_ranking: List of document IDs in predicted order
        ground_truth: Dict mapping doc_id to relevance score
        k_values: List of k values to evaluate at

    Returns:
        Dict of metric names to scores
    """
    # Build relevances list
    relevances = [ground_truth.get(doc_id, 0) for doc_id in predicted_ranking]
    total_relevant = sum(1 for rel in ground_truth.values() if rel > 0)

    results = {}

    for k in k_values:
        results[f"ndcg@{k}"] = ndcg_at_k(relevances, k)
        results[f"precision@{k}"] = precision_at_k(
            [1 if r > 0 else 0 for r in relevances], k
        )
        results[f"recall@{k}"] = recall_at_k(
            [1 if r > 0 else 0 for r in relevances], total_relevant, k
        )

    results["map"] = average_precision([1 if r > 0 else 0 for r in relevances])

    return results


# Convenience function for reranker evaluation
def evaluate_reranker_improvement(
    baseline_scores: List[Tuple[str, float]],
    reranked_scores: List[Tuple[str, float]],
    ground_truth: Dict[str, int],
    k: int = 10,
) -> Dict[str, float]:
    """
    Evaluate improvement of reranker over baseline.

    Args:
        baseline_scores: List of (doc_id, score) tuples from baseline ranking
        reranked_scores: List of (doc_id, score) tuples from reranker
        ground_truth: Dict mapping doc_id to binary relevance (0 or 1)
        k: Cutoff for evaluation

    Returns:
        Dict with metrics for both and improvement percentages
    """
    baseline_order = [doc_id for doc_id, _ in baseline_scores]
    reranked_order = [doc_id for doc_id, _ in reranked_scores]

    baseline_metrics = evaluate_ranking(baseline_order, ground_truth, [k])
    reranked_metrics = evaluate_ranking(reranked_order, ground_truth, [k])

    improvement = {}
    for metric in baseline_metrics:
        base = baseline_metrics[metric]
        new = reranked_metrics[metric]
        if base > 0:
            pct_improvement = ((new - base) / base) * 100
        else:
            pct_improvement = 100 if new > 0 else 0
        improvement[f"{metric}_improvement_pct"] = pct_improvement

    return {
        "baseline": baseline_metrics,
        "reranked": reranked_metrics,
        "improvement": improvement,
    }


if __name__ == "__main__":
    # Example usage
    print("Example: Evaluating rankings")

    # Ground truth: which docs are relevant
    ground_truth = {
        "doc1": 3,  # Highly relevant
        "doc2": 2,  # Relevant
        "doc3": 1,  # Somewhat relevant
        "doc4": 0,  # Not relevant
        "doc5": 0,  # Not relevant
    }

    # Predicted ranking (order matters!)
    predicted_ranking = ["doc1", "doc4", "doc2", "doc5", "doc3"]

    metrics = evaluate_ranking(predicted_ranking, ground_truth, k_values=[3, 5])

    print("\nMetrics:")
    for metric, score in metrics.items():
        print(f"  {metric}: {score:.4f}")

    # Example: nDCG@10 calculation
    print("\n\nExample: nDCG@10")
    relevances = [3, 2, 3, 0, 1, 2, 0, 0, 1, 0]
    ndcg_10 = ndcg_at_k(relevances, 10)
    print(f"nDCG@10: {ndcg_10:.4f}")
