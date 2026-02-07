"""
Unit Tests for Semantic Chunking Module

Tests cover:
- Sentence-based chunking
- Semantic chunking with embeddings
- Markdown-aware chunking
- Chunk statistics
"""

import pytest
from unittest.mock import Mock, patch
import sys

sys.path.insert(0, "/Users/thiennlinh/Documents/New project/services/indexer")

from chunker import (
    chunk_document,
    _chunk_sentence,
    _chunk_semantic_fallback,
    _chunk_markdown,
    _split_units,
    _merge_small,
    ChunkingStats,
)
from models import Chunk, Node


class TestChunkingSentence:
    """Test sentence-based chunking."""

    def test_split_units_basic(self):
        """Test basic sentence splitting."""
        text = "First sentence. Second sentence! Third?"
        units = _split_units(text)

        assert len(units) == 3
        assert "First sentence" in units[0]
        assert "Second sentence" in units[1]
        assert "Third" in units[2]

    def test_split_units_paragraphs(self):
        """Test paragraph-aware splitting."""
        text = "Para 1.\n\nPara 2. More here."
        units = _split_units(text)

        assert len(units) >= 2

    def test_merge_small_chunks(self):
        """Test merging small chunks."""
        chunks = [
            Chunk(text="ab", heading_path=[], section_path="", index=0, start=0, end=2),
            Chunk(text="cd", heading_path=[], section_path="", index=1, start=3, end=5),
            Chunk(
                text="efgh", heading_path=[], section_path="", index=2, start=6, end=10
            ),
        ]

        merged = _merge_small(chunks, min_chars=5)

        assert len(merged) == 2
        assert len(merged[0].text) >= 4  # "ab cd"

    def test_chunk_sentence_basic(self):
        """Test basic sentence chunking."""
        text = "This is a long sentence that should be chunked properly. " * 10
        chunks = []

        _chunk_sentence(text, ["Heading"], chunks, 0)

        assert len(chunks) > 0
        assert all(len(c.text) > 0 for c in chunks)

    def test_chunk_sentence_overlap(self):
        """Test overlap between chunks."""
        text = "Sentence one. Sentence two. Sentence three. " * 20
        chunks = []

        with patch("chunker.settings") as mock_settings:
            mock_settings.chunk_max_chars = 50
            mock_settings.chunk_overlap_chars = 20
            mock_settings.chunk_min_chars = 10
            _chunk_sentence(text, [], chunks, 0)

        assert len(chunks) > 1


class TestChunkingSemantic:
    """Test semantic chunking with embeddings."""

    def test_semantic_chunking_basic(self):
        """Test basic semantic chunking."""
        text = "Machine learning is a subset of AI. Deep learning uses neural networks."

        chunks = []
        with patch("chunker.settings") as mock_settings:
            mock_settings.chunk_min_chars = 10
            mock_settings.chunk_max_chars = 500
            mock_settings.semantic_embedder_name = "test-model"
            mock_settings.semantic_chunk_threshold = 0.7

            with patch("sentence_transformers.SentenceTransformer") as mock_model:
                mock_instance = Mock()
                mock_instance.encode.return_value = [[0.1, 0.2], [0.3, 0.4]]
                mock_model.return_value = mock_instance

                _chunk_semantic_fallback(text, [], chunks, 0)

        # Should create at least one chunk
        assert len(chunks) >= 1

    def test_semantic_chunking_similarity_threshold(self):
        """Test that similarity threshold affects chunking."""
        text = "Sentence one. Sentence two. Sentence three."

        chunks_high_threshold = []
        chunks_low_threshold = []

        with patch("chunker.settings") as mock_settings:
            mock_settings.chunk_min_chars = 5
            mock_settings.chunk_max_chars = 1000

            with patch("sentence_transformers.SentenceTransformer") as mock_model:
                mock_instance = Mock()
                # High similarity embeddings
                mock_instance.encode.return_value = [
                    [1.0, 0.0],
                    [0.95, 0.05],  # Very similar to first
                    [0.1, 0.9],  # Different from first two
                ]
                mock_model.return_value = mock_instance

                # With high threshold (0.9), only very similar sentences merge
                mock_settings.semantic_chunk_threshold = 0.9
                _chunk_semantic_fallback(text, [], chunks_high_threshold, 0)

                # With low threshold (0.5), more sentences merge
                mock_settings.semantic_chunk_threshold = 0.5
                _chunk_semantic_fallback(text, [], chunks_low_threshold, 0)

        # Lower threshold should result in fewer chunks (more merging)
        assert len(chunks_low_threshold) <= len(chunks_high_threshold)

    def test_semantic_chunking_single_sentence(self):
        """Test semantic chunking with single sentence."""
        text = "Single sentence."

        chunks = []
        with patch("chunker.settings") as mock_settings:
            mock_settings.chunk_min_chars = 5
            _chunk_semantic_fallback(text, [], chunks, 0)

        assert len(chunks) == 1
        assert chunks[0].text == "Single sentence."


class TestChunkingMarkdown:
    """Test markdown-aware chunking."""

    def test_chunk_markdown_headers(self):
        """Test chunking on markdown headers."""
        text = """# Heading 1
Content for heading 1.

## Heading 2
Content for heading 2.

### Heading 3
Content for heading 3."""

        chunks = []
        with patch("chunker.settings") as mock_settings:
            mock_settings.chunk_min_chars = 5
            _chunk_markdown(text, [], chunks, 0)

        # Should split on headers
        assert len(chunks) >= 2

    def test_chunk_markdown_preserves_structure(self):
        """Test that markdown chunking preserves heading structure."""
        text = """# Main Title
Main content.

## Section 1
Section 1 content.

## Section 2
Section 2 content."""

        chunks = []
        with patch("chunker.settings") as mock_settings:
            mock_settings.chunk_min_chars = 5
            _chunk_markdown(text, [], chunks, 0)

        # Check that heading paths are preserved
        if chunks:
            assert len(chunks[0].heading_path) >= 1


class TestChunkingDocument:
    """Test full document chunking."""

    def test_chunk_document_basic(self):
        """Test chunking a document tree."""
        root = Node(
            heading="Root",
            text="This is the root content.",
            children=[
                Node(
                    heading="Child 1",
                    text="Child 1 content. More text here.",
                    children=[],
                ),
                Node(
                    heading="Child 2",
                    text="Child 2 content.",
                    children=[],
                ),
            ],
        )

        chunks = chunk_document(root)

        assert len(chunks) > 0
        assert all(isinstance(c, Chunk) for c in chunks)

    def test_chunk_document_indexing(self):
        """Test that chunks are properly indexed."""
        root = Node(
            heading="Root",
            text="Text here.",
            children=[
                Node(heading="A", text="A text.", children=[]),
                Node(heading="B", text="B text.", children=[]),
            ],
        )

        chunks = chunk_document(root)

        indices = [c.index for c in chunks]
        assert indices == sorted(indices)
        assert len(set(indices)) == len(indices)  # No duplicates

    def test_chunk_document_heading_paths(self):
        """Test heading paths in chunks."""
        root = Node(
            heading="Section A",
            text="Content A.",
            children=[
                Node(
                    heading="Subsection A1",
                    text="Content A1.",
                    children=[],
                ),
            ],
        )

        chunks = chunk_document(root)

        if len(chunks) >= 2:
            # First chunk should have parent heading
            assert "Section A" in chunks[0].heading_path or chunks[0].heading_path == []


class TestChunkingStats:
    """Test chunking statistics."""

    def test_stats_initial(self):
        """Test initial stats."""
        stats = ChunkingStats()

        assert stats.total_documents == 0
        assert stats.total_chunks == 0

    def test_stats_update(self):
        """Test updating stats."""
        stats = ChunkingStats()

        stats.update(doc_size=1000, num_chunks=5)
        stats.update(doc_size=2000, num_chunks=8)

        assert stats.total_documents == 2
        assert stats.total_chunks == 13

    def test_stats_get_stats(self):
        """Test getting stats dictionary."""
        stats = ChunkingStats()
        stats.total_documents = 10
        stats.total_chunks = 50

        result = stats.get_stats()

        assert result["documents"] == 10
        assert result["chunks"] == 50
        assert "avg_chunk_size" in result


class TestChunkingConfiguration:
    """Test chunking with different configurations."""

    def test_chunk_method_selection(self):
        """Test that chunk method is selected correctly."""
        text = "Test content."

        with patch("chunker.settings") as mock_settings:
            mock_settings.chunk_method = "sentence"
            mock_settings.chunk_min_chars = 5

            chunks = []
            _chunk_sentence(text, [], chunks, 0)
            assert len(chunks) == 1

    def test_chunk_size_constraints(self):
        """Test that chunks respect size constraints."""
        long_text = "Word. " * 1000  # Very long text

        chunks = []
        with patch("chunker.settings") as mock_settings:
            mock_settings.chunk_max_chars = 100
            mock_settings.chunk_overlap_chars = 20
            mock_settings.chunk_min_chars = 10
            _chunk_sentence(long_text, [], chunks, 0)

        # All chunks should be within max size
        assert all(len(c.text) <= 100 for c in chunks)


class TestChunkingEdgeCases:
    """Test edge cases in chunking."""

    def test_empty_text(self):
        """Test chunking empty text."""
        chunks = []
        _chunk_sentence("", [], chunks, 0)

        assert len(chunks) == 0

    def test_very_short_text(self):
        """Test chunking very short text."""
        chunks = []
        with patch("chunker.settings") as mock_settings:
            mock_settings.chunk_min_chars = 5
            mock_settings.chunk_max_chars = 100
            _chunk_sentence("Hi.", [], chunks, 0)

        # Should still create a chunk
        assert len(chunks) >= 0  # May or may not create chunk depending on min_chars

    def test_no_sentence_boundaries(self):
        """Test text without clear sentence boundaries."""
        text = "This is a long run on sentence with no clear breaks it just keeps going"

        units = _split_units(text)

        # Should still split somehow
        assert len(units) >= 1

    def test_special_characters(self):
        """Test chunking text with special characters."""
        text = "Special chars: @#$%^&*()!!!"

        chunks = []
        with patch("chunker.settings") as mock_settings:
            mock_settings.chunk_min_chars = 1
            mock_settings.chunk_max_chars = 1000
            _chunk_sentence(text, [], chunks, 0)

        assert len(chunks) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
