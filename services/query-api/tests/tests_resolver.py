"""
Tests for the conflict resolver.

These tests verify:
- Conflict detection with same source_id, different versions
- Conflict detection with same source_id, different sources
- Resolution rules: authority > lower priority
- Resolution rules: latest > older
- Citation generation
"""

import pytest
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class MockChunk:
    """Mock chunk for testing."""

    doc_id: str
    source_id: str
    source: str
    version: int
    chunk_index: int
    text: str
    section_path: str = ""
    heading_path: Optional[List[str]] = None


def test_detect_no_conflicts():
    """Test detection when no conflicts exist."""
    from resolver import detect_conflicts

    chunks = [
        MockChunk("doc1", "src_1", "api", 1, 0, "text 1"),
        MockChunk("doc2", "src_2", "manual", 1, 0, "text 2"),
    ]

    conflicts = detect_conflicts(chunks)
    assert len(conflicts) == 0


def test_detect_version_conflict():
    """Test detection of version conflicts."""
    from resolver import detect_conflicts

    chunks = [
        MockChunk("doc1", "src_1", "api", 1, 0, "old text"),
        MockChunk("doc1", "src_1", "api", 2, 0, "new text"),
        MockChunk("doc2", "src_2", "manual", 1, 0, "text"),
    ]

    conflicts = detect_conflicts(chunks)
    assert len(conflicts) == 1
    assert conflicts[0].source_id == "src_1"
    assert conflicts[0].resolution == "version_conflict"
    assert len(conflicts[0].conflicting_chunks) == 2


def test_detect_authority_conflict():
    """Test detection of authority conflicts (same version, different sources)."""
    from resolver import detect_conflicts

    chunks = [
        MockChunk("doc1", "src_1", "api", 1, 0, "api text"),
        MockChunk("doc1", "src_1", "manual", 1, 0, "manual text"),
    ]

    conflicts = detect_conflicts(chunks)
    assert len(conflicts) == 1
    assert conflicts[0].resolution == "authority_conflict"


def test_resolve_authority_priority():
    """Test resolution by source authority priority."""
    from resolver import resolve_conflicts

    chunks = [
        MockChunk("doc1", "src_1", "api", 1, 0, "api text"),
        MockChunk("doc1", "src_1", "manual", 1, 0, "manual text"),
    ]

    source_priority = {"manual": 10, "api": 5}
    resolved, conflicts = resolve_conflicts(chunks, source_priority)

    assert len(resolved) == 1
    assert resolved[0].source == "manual"  # Higher priority wins
    assert len(conflicts) == 1
    assert conflicts[0].winner_id == "doc1:0"


def test_resolve_latest_version():
    """Test resolution by latest version when priority is equal."""
    from resolver import resolve_conflicts

    chunks = [
        MockChunk("doc1", "src_1", "api", 1, 0, "old text"),
        MockChunk("doc1", "src_1", "api", 3, 0, "newest text"),
        MockChunk("doc1", "src_1", "api", 2, 0, "middle text"),
    ]

    source_priority = {"api": 5}
    resolved, conflicts = resolve_conflicts(chunks, source_priority)

    assert len(resolved) == 1
    assert resolved[0].version == 3  # Latest version wins


def test_resolve_authority_over_version():
    """Test that authority takes precedence over version."""
    from resolver import resolve_conflicts

    chunks = [
        MockChunk("doc1", "src_1", "api", 5, 0, "api v5"),
        MockChunk("doc1", "src_1", "manual", 1, 0, "manual v1"),
    ]

    source_priority = {"manual": 10, "api": 5}
    resolved, conflicts = resolve_conflicts(chunks, source_priority)

    # Manual has lower version but higher authority
    assert resolved[0].source == "manual"
    assert resolved[0].version == 1


def test_resolve_multiple_groups():
    """Test resolution with multiple conflict groups."""
    from resolver import resolve_conflicts

    chunks = [
        MockChunk("doc1", "src_1", "api", 1, 0, "text 1a"),
        MockChunk("doc1", "src_1", "api", 2, 0, "text 1b"),
        MockChunk("doc2", "src_2", "manual", 1, 0, "text 2a"),
        MockChunk("doc2", "src_2", "manual", 3, 0, "text 2b"),
    ]

    source_priority = {"manual": 10, "api": 5}
    resolved, conflicts = resolve_conflicts(chunks, source_priority)

    assert len(resolved) == 2
    assert len(conflicts) == 2  # One conflict per group


def test_resolve_no_conflicts():
    """Test resolution when no conflicts exist."""
    from resolver import resolve_conflicts

    chunks = [
        MockChunk("doc1", "src_1", "api", 1, 0, "text 1"),
        MockChunk("doc2", "src_2", "manual", 1, 0, "text 2"),
    ]

    source_priority = {"manual": 10, "api": 5}
    resolved, conflicts = resolve_conflicts(chunks, source_priority)

    assert len(resolved) == 2
    assert len(conflicts) == 0


def test_resolve_empty_list():
    """Test resolution with empty chunk list."""
    from resolver import resolve_conflicts

    resolved, conflicts = resolve_conflicts([], {})

    assert len(resolved) == 0
    assert len(conflicts) == 0


def test_resolve_unknown_source_priority():
    """Test resolution when source priority is unknown."""
    from resolver import resolve_conflicts

    chunks = [
        MockChunk("doc1", "src_1", "unknown", 1, 0, "text"),
        MockChunk("doc1", "src_1", "api", 2, 0, "api text"),
    ]

    source_priority = {"api": 5}  # "unknown" not in priority map
    resolved, conflicts = resolve_conflicts(chunks, source_priority)

    # api has priority 5, unknown has priority 0
    assert resolved[0].source == "api"


def test_get_citation_basic():
    """Test citation generation."""
    from resolver import get_citation

    chunk = MockChunk(
        doc_id="doc1",
        source_id="src_1",
        source="api",
        version=2,
        chunk_index=5,
        text="chunk text",
        section_path="section/a/b",
        heading_path=["Header 1", "Header 2"],
    )

    citation = get_citation(chunk)

    assert citation["doc_id"] == "doc1"
    assert citation["source"] == "api"
    assert citation["source_id"] == "src_1"
    assert citation["version"] == 2
    assert citation["chunk_index"] == 5
    assert citation["section_path"] == "section/a/b"
    assert citation["heading_path"] == ["Header 1", "Header 2"]


def test_get_citation_no_heading():
    """Test citation generation without heading."""
    from resolver import get_citation

    chunk = MockChunk(
        doc_id="doc1",
        source_id="src_1",
        source="api",
        version=1,
        chunk_index=0,
        text="text",
        section_path="section",
        heading_path=None,
    )

    citation = get_citation(chunk, include_heading=False)

    assert "heading_path" not in citation
    assert citation["doc_id"] == "doc1"


def test_conflict_logging(caplog):
    """Test that conflicts are logged properly."""
    import logging
    from resolver import resolve_conflicts

    chunks = [
        MockChunk("doc1", "src_1", "api", 1, 0, "old"),
        MockChunk("doc1", "src_1", "api", 2, 0, "new"),
    ]

    with caplog.at_level(logging.WARNING):
        resolved, conflicts = resolve_conflicts(chunks, {}, log_conflicts=True)

    assert len(conflicts) == 1
    assert "Conflict detected" in caplog.text
    assert "src_1" in caplog.text


def test_conflict_logging_disabled(caplog):
    """Test that conflicts are not logged when disabled."""
    import logging
    from resolver import resolve_conflicts

    chunks = [
        MockChunk("doc1", "src_1", "api", 1, 0, "old"),
        MockChunk("doc1", "src_1", "api", 2, 0, "new"),
    ]

    with caplog.at_level(logging.WARNING):
        resolved, conflicts = resolve_conflicts(chunks, {}, log_conflicts=False)

    assert len(conflicts) == 1
    assert "Conflict detected" not in caplog.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
