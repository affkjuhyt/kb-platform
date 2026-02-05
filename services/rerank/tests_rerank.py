"""
Tests for the reranker service.

These tests verify:
- Basic reranking functionality
- Cross-encoder integration
- Score normalization
- Top-k limiting
- Batch processing
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock


def test_basic_rerank_cosine_similarity():
    """Test that basic rerank uses cosine similarity properly."""
    from app import _basic_rerank

    query = "machine learning neural networks"
    texts = [
        "machine learning is great",
        "neural networks are powerful",
        "machine learning neural networks",
        "something completely different",
    ]

    scores = _basic_rerank(query, texts)

    # Should return scores for all texts
    assert len(scores) == 4
    # All scores should be non-negative
    assert all(s >= 0 for s in scores)
    # Perfect match should have highest score
    assert scores[2] >= max(scores[0], scores[1], scores[3])


def test_basic_rerank_empty_query():
    """Test basic rerank with empty query."""
    from app import _basic_rerank

    scores = _basic_rerank("", ["some text", "another text"])
    assert len(scores) == 2
    assert all(s == 0.0 for s in scores)


def test_basic_rerank_empty_texts():
    """Test basic rerank with empty texts."""
    from app import _basic_rerank

    scores = _basic_rerank("query", [])
    assert scores == []


def test_normalize_scores():
    """Test score normalization to [0, 1]."""
    from app import _normalize_scores

    scores = [10.0, 20.0, 30.0, 40.0]
    normalized = _normalize_scores(scores)

    assert len(normalized) == 4
    assert min(normalized) == 0.0
    assert max(normalized) == 1.0
    # Check relative ordering preserved
    assert normalized[0] < normalized[1] < normalized[2] < normalized[3]


def test_normalize_scores_identical():
    """Test normalization with identical scores."""
    from app import _normalize_scores

    scores = [5.0, 5.0, 5.0]
    normalized = _normalize_scores(scores)

    assert len(normalized) == 3
    assert all(s == 0.5 for s in normalized)


def test_normalize_scores_empty():
    """Test normalization with empty list."""
    from app import _normalize_scores

    scores = []
    normalized = _normalize_scores(scores)
    assert normalized == []


def test_rerank_with_mock_cross_encoder():
    """Test rerank endpoint with mocked cross-encoder."""
    from app import rerank, RerankRequest, Candidate

    # Mock the model
    mock_model = Mock()
    mock_model.predict = Mock(return_value=np.array([0.5, 0.8, 0.3]))

    with (
        patch("app._get_model", return_value=mock_model),
        patch("config.settings.normalize_scores", False),
    ):
        request = RerankRequest(
            query="test query",
            candidates=[
                Candidate(id="1", text="text 1"),
                Candidate(id="2", text="text 2"),
                Candidate(id="3", text="text 3"),
            ],
        )

        response = rerank(request)

        assert len(response.results) == 3
        # Highest score should be first (0.8)
        assert response.results[0].id == "2"
        assert response.results[0].score == pytest.approx(0.8, 0.01)


def test_rerank_empty_candidates():
    """Test rerank with empty candidates list."""
    from app import rerank, RerankRequest

    request = RerankRequest(query="test", candidates=[])
    response = rerank(request)

    assert response.results == []


def test_rerank_top_k_limit():
    """Test that rerank respects top_k limit."""
    from app import rerank, RerankRequest, Candidate

    # Mock model that returns 10 scores
    mock_model = Mock()
    mock_model.predict = Mock(
        return_value=np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
    )

    with (
        patch("app._get_model", return_value=mock_model),
        patch("config.settings.normalize_scores", False),
        patch("config.settings.top_k", 5),
    ):
        request = RerankRequest(
            query="test",
            candidates=[Candidate(id=str(i), text=f"text {i}") for i in range(10)],
        )

        response = rerank(request)

        # Should only return top_k results
        assert len(response.results) == 5
        # Highest scores should be first
        assert response.results[0].id == "9"
        assert response.results[4].id == "5"


def test_rerank_batch_processing():
    """Test that rerank processes large batches correctly."""
    from app import rerank, RerankRequest, Candidate

    mock_model = Mock()
    # Return different scores for different batches
    call_count = [0]

    def mock_predict(pairs):
        call_count[0] += 1
        batch_size = len(pairs)
        return np.array([float(i) for i in range(batch_size)])

    mock_model.predict = mock_predict

    with (
        patch("app._get_model", return_value=mock_model),
        patch("config.settings.max_batch", 5),
        patch("config.settings.normalize_scores", False),
        patch("config.settings.top_k", 20),
    ):
        request = RerankRequest(
            query="test",
            candidates=[Candidate(id=str(i), text=f"text {i}") for i in range(12)],
        )

        response = rerank(request)

        # Should have processed in 3 batches (5, 5, 2)
        assert call_count[0] == 3
        assert len(response.results) == 12


def test_rerank_score_normalization_enabled():
    """Test score normalization when enabled."""
    from app import rerank, RerankRequest, Candidate

    mock_model = Mock()
    mock_model.predict = Mock(return_value=np.array([10.0, 20.0, 30.0]))

    with (
        patch("app._get_model", return_value=mock_model),
        patch("config.settings.normalize_scores", True),
        patch("config.settings.top_k", 10),
    ):
        request = RerankRequest(
            query="test",
            candidates=[
                Candidate(id="1", text="text 1"),
                Candidate(id="2", text="text 2"),
                Candidate(id="3", text="text 3"),
            ],
        )

        response = rerank(request)

        # Scores should be normalized to [0, 1]
        scores = [r.score for r in response.results]
        assert min(scores) == 0.0
        assert max(scores) == 1.0


def test_rerank_fallback_to_basic():
    """Test fallback to basic reranking when model fails."""
    from app import rerank, RerankRequest, Candidate

    with (
        patch("app._get_model", return_value=None),
        patch("config.settings.top_k", 10),
    ):
        request = RerankRequest(
            query="machine learning",
            candidates=[
                Candidate(id="1", text="machine learning is great"),
                Candidate(id="2", text="something else"),
                Candidate(id="3", text="machine learning neural networks"),
            ],
        )

        response = rerank(request)

        # Best match should still be ranked first
        assert response.results[0].id == "3"


def test_rerank_preserves_ids_and_texts():
    """Test that rerank preserves candidate IDs and texts."""
    from app import rerank, RerankRequest, Candidate

    mock_model = Mock()
    mock_model.predict = Mock(return_value=np.array([0.5, 0.5, 0.5]))

    with (
        patch("app._get_model", return_value=mock_model),
        patch("config.settings.normalize_scores", False),
    ):
        candidates = [
            Candidate(id="id_1", text="text one"),
            Candidate(id="id_2", text="text two"),
            Candidate(id="id_3", text="text three"),
        ]
        request = RerankRequest(query="test", candidates=candidates)

        response = rerank(request)

        # Check that IDs and texts are preserved
        result_ids = {r.id for r in response.results}
        result_texts = {r.text for r in response.results}

        assert result_ids == {"id_1", "id_2", "id_3"}
        assert result_texts == {"text one", "text two", "text three"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
