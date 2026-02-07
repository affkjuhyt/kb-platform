from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import logging

logger = logging.getLogger("resolver")


@dataclass
class ConflictInfo:
    """Information about a detected conflict."""

    source_id: str
    conflicting_chunks: List[Any]
    resolution: str
    winner_id: Optional[str] = None


def detect_conflicts(chunks) -> List[ConflictInfo]:
    """
    Detect conflicts among chunks with the same source_id but different versions.

    A conflict occurs when:
    - Multiple chunks have the same source_id (same document from different sources)
    - They have different versions or different content
    """
    grouped = defaultdict(list)
    for c in chunks:
        grouped[c.source_id].append(c)

    conflicts = []
    for source_id, items in grouped.items():
        if len(items) > 1:
            # Check if they're actually different
            versions = set(c.version for c in items)
            if len(versions) > 1:
                conflicts.append(
                    ConflictInfo(
                        source_id=source_id,
                        conflicting_chunks=items,
                        resolution="version_conflict",
                    )
                )
            else:
                # Same version but different sources - potential authority conflict
                sources = set(c.source for c in items)
                if len(sources) > 1:
                    conflicts.append(
                        ConflictInfo(
                            source_id=source_id,
                            conflicting_chunks=items,
                            resolution="authority_conflict",
                        )
                    )

    return conflicts


def resolve_conflicts(
    chunks, source_priority: Dict[str, int], log_conflicts: bool = True
) -> Tuple[List[Any], List[ConflictInfo]]:
    """
    Resolve conflicts using rules:
    1. Authority > Lower Priority (based on source_priority)
    2. Latest > Older (based on version number)

    Args:
        chunks: List of chunk objects with source_id, source, version attributes
        source_priority: Dict mapping source names to priority scores (higher = more authoritative)
        log_conflicts: Whether to log detected conflicts

    Returns:
        Tuple of (resolved_chunks, conflict_info)
    """
    # Detect conflicts first
    conflicts = detect_conflicts(chunks)

    # Group by source_id
    grouped = defaultdict(list)
    for c in chunks:
        grouped[c.source_id].append(c)

    resolved = []
    resolved_ids = []

    for source_id, items in grouped.items():
        # Sort by:
        # 1. Source priority (descending - higher authority first)
        # 2. Version (descending - latest first)
        items.sort(
            key=lambda x: (
                source_priority.get(x.source, 0),
                x.version,
            ),
            reverse=True,
        )
        winner = items[0]
        resolved.append(winner)
        resolved_ids.append(f"{winner.doc_id}:{winner.chunk_index}")

        # Update conflict info with winner
        for conflict in conflicts:
            if conflict.source_id == source_id:
                conflict.winner_id = f"{winner.doc_id}:{winner.chunk_index}"

    # Log conflicts if requested
    if log_conflicts and conflicts:
        for c in conflicts:
            logger.warning(
                f"Conflict detected for source_id={c.source_id}: {c.resolution} "
                f"({len(c.conflicting_chunks)} versions). "
                f"Winner: {c.winner_id}"
            )

    return resolved, conflicts


def get_citation(chunk, include_heading: bool = True) -> Dict[str, Any]:
    """
    Generate citation information for a chunk.

    Returns dict with:
    - doc_id
    - source
    - source_id
    - version
    - chunk_index
    - section_path
    - heading_path (if requested)
    """
    citation = {
        "doc_id": chunk.doc_id,
        "source": chunk.source,
        "source_id": chunk.source_id,
        "version": chunk.version,
        "chunk_index": chunk.chunk_index,
        "section_path": chunk.section_path,
    }

    if include_heading:
        citation["heading_path"] = chunk.heading_path

    return citation
