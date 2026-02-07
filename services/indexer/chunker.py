"""
Document Chunking Module

Supports multiple chunking strategies:
1. sentence: Original sentence-based splitting
2. semantic: Semantic similarity-based splitting using embeddings
3. markdown: Split on markdown headers preserving structure
"""

import re
from typing import List

from models import Chunk, Node
from config import settings


def _split_units(text: str) -> List[str]:
    """Split text into sentence units."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    units: List[str] = []
    for para in paragraphs:
        sentences = re.split(r"(?<=[.!?])\s+", para)
        for sent in sentences:
            if sent.strip():
                units.append(sent.strip())
    return units if units else [text.strip()]


def _merge_small(chunks: List[Chunk], min_chars: int) -> List[Chunk]:
    """Merge small chunks to meet minimum size."""
    if not chunks:
        return chunks
    merged: List[Chunk] = []
    buffer = None
    for chunk in chunks:
        if buffer is None:
            buffer = chunk
            continue
        if len(buffer.text) < min_chars:
            buffer.text = f"{buffer.text} {chunk.text}".strip()
            buffer.end = chunk.end
        else:
            merged.append(buffer)
            buffer = chunk
    if buffer is not None:
        merged.append(buffer)
    return merged


def _walk(node: Node, heading_path: List[str], chunks: List[Chunk], index: int) -> int:
    """Walk the document tree and chunk each node."""
    path = heading_path + [node.heading] if node.heading else heading_path
    text = node.text.strip()

    if text:
        index = _chunk_text(text, path, chunks, index)

    for child in node.children:
        index = _walk(child, path, chunks, index)

    return index


def _chunk_text(
    text: str, heading_path: List[str], chunks: List[Chunk], index: int
) -> int:
    """Chunk text using the configured method."""
    method = getattr(settings, "chunk_method", "sentence")

    if method == "semantic":
        return _chunk_semantic(text, heading_path, chunks, index)
    elif method == "markdown":
        return _chunk_markdown(text, heading_path, chunks, index)
    else:
        return _chunk_sentence(text, heading_path, chunks, index)


def _chunk_sentence(
    text: str, heading_path: List[str], chunks: List[Chunk], index: int
) -> int:
    """Original sentence-based chunking."""
    max_chars = settings.chunk_max_chars
    overlap = settings.chunk_overlap_chars
    min_chars = settings.chunk_min_chars

    units = _split_units(text)
    current = ""
    cursor = 0
    local_chunks: List[Chunk] = []

    for unit in units:
        if not current:
            current = unit
        elif len(current) + 1 + len(unit) <= max_chars:
            current = f"{current} {unit}"
        else:
            end = cursor + len(current)
            local_chunks.append(
                Chunk(
                    text=current.strip(),
                    heading_path=heading_path,
                    section_path=" > ".join(heading_path),
                    index=0,
                    start=cursor,
                    end=end,
                )
            )
            cursor = max(end - overlap, 0)
            current = unit

    if current:
        end = cursor + len(current)
        local_chunks.append(
            Chunk(
                text=current.strip(),
                heading_path=heading_path,
                section_path=" > ".join(heading_path),
                index=0,
                start=cursor,
                end=end,
            )
        )

    local_chunks = _merge_small(local_chunks, min_chars)
    for chunk in local_chunks:
        chunk.index = index
        chunks.append(chunk)
        index += 1

    return index


def _chunk_semantic(
    text: str, heading_path: List[str], chunks: List[Chunk], index: int
) -> int:
    """
    Semantic chunking using FastEmbed for breakpoint detection.
    Faster and more consistent with our embedding infrastructure.
    """
    try:
        from embedding import embedder_factory

        embedder = embedder_factory()

        # Split into sentences first
        sentences = _split_units(text)
        if len(sentences) <= 1:
            return _chunk_sentence(text, heading_path, chunks, index)

        # Get embeddings for each sentence to find breakpoints
        embeddings = embedder.embed(sentences)

        import numpy as np

        def cosine_sim(v1, v2):
            return float(
                np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8)
            )

        threshold = getattr(settings, "semantic_chunk_threshold", 0.7)
        max_chars = settings.chunk_max_chars

        current_sentences = [sentences[0]]
        for i in range(1, len(sentences)):
            # Compare current sentence with the pool of sentences in the current chunk
            # or just the previous one for efficiency. Here we use previous one for speed.
            sim = cosine_sim(embeddings[i - 1], embeddings[i])

            combined_len = (
                sum(len(s) for s in current_sentences) + len(sentences[i]) + 1
            )

            # Break if similarity is low OR chunk gets too large
            if sim < threshold or combined_len > max_chars:
                chunk_text = " ".join(current_sentences).strip()
                if len(chunk_text) >= settings.chunk_min_chars:
                    chunks.append(
                        Chunk(
                            text=chunk_text,
                            heading_path=heading_path,
                            section_path=" > ".join(heading_path),
                            index=index,
                            start=0,
                            end=len(chunk_text),
                        )
                    )
                    index += 1
                current_sentences = [sentences[i]]
            else:
                current_sentences.append(sentences[i])

        # Add last piece
        if current_sentences:
            chunk_text = " ".join(current_sentences).strip()
            if len(chunk_text) >= settings.chunk_min_chars:
                chunks.append(
                    Chunk(
                        text=chunk_text,
                        heading_path=heading_path,
                        section_path=" > ".join(heading_path),
                        index=index,
                        start=0,
                        end=len(chunk_text),
                    )
                )
                index += 1
        return index

    except Exception as e:
        print(f"Semantic chunking failed: {e}, falling back to sentence chunking")
        return _chunk_sentence(text, heading_path, chunks, index)


def _chunk_semantic_fallback(
    text: str, heading_path: List[str], chunks: List[Chunk], index: int
) -> int:
    """
    Embedding-based semantic chunking (fallback).

    Groups sentences based on cosine similarity of their embeddings.
    """
    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return _chunk_sentence(text, heading_path, chunks, index)

    embedder_name = getattr(
        settings, "semantic_embedder_name", settings.embedding_model
    )
    embedder = SentenceTransformer(embedder_name)

    sentences = _split_units(text)

    if len(sentences) <= 1:
        if len(text) >= settings.chunk_min_chars:
            chunks.append(
                Chunk(
                    text=text.strip(),
                    heading_path=heading_path,
                    section_path=" > ".join(heading_path),
                    index=index,
                    start=0,
                    end=len(text),
                )
            )
            index += 1
        return index

    embeddings = embedder.encode(sentences)

    threshold = getattr(settings, "semantic_chunk_threshold", 0.7)

    def cosine_sim(v1, v2):
        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8))

    current_chunk = [sentences[0]]
    current_embedding = embeddings[0]

    for i in range(1, len(sentences)):
        similarity = cosine_sim(current_embedding, embeddings[i])
        combined = " ".join(current_chunk) + " " + sentences[i]

        if similarity >= threshold and len(combined) <= settings.chunk_max_chars:
            current_chunk.append(sentences[i])
            current_embedding = (
                current_embedding * (len(current_chunk) - 1) + embeddings[i]
            ) / len(current_chunk)
        else:
            if len(" ".join(current_chunk)) >= settings.chunk_min_chars:
                chunks.append(
                    Chunk(
                        text=" ".join(current_chunk),
                        heading_path=heading_path,
                        section_path=" > ".join(heading_path),
                        index=index,
                        start=0,
                        end=len(" ".join(current_chunk)),
                    )
                )
                index += 1
            current_chunk = [sentences[i]]
            current_embedding = embeddings[i]

    if current_chunk and len(" ".join(current_chunk)) >= settings.chunk_min_chars:
        chunks.append(
            Chunk(
                text=" ".join(current_chunk),
                heading_path=heading_path,
                section_path=" > ".join(heading_path),
                index=index,
                start=0,
                end=len(" ".join(current_chunk)),
            )
        )
        index += 1

    return index


def _chunk_markdown(
    text: str, heading_path: List[str], chunks: List[Chunk], index: int
) -> int:
    """
    Markdown-aware chunking.

    Splits on markdown headers while maintaining structure.
    """
    try:
        from langchain.text_splitter import MarkdownHeaderTextSplitter
    except ImportError:
        return _chunk_sentence(text, heading_path, chunks, index)

    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "H1"),
            ("##", "H2"),
            ("###", "H3"),
            ("####", "H4"),
        ]
    )

    md_header_splits = markdown_splitter.split_text(text)

    for split in md_header_splits:
        content = split.page_content.strip()
        metadata = split.metadata

        chunk_heading_path = heading_path + [
            metadata.get("H1", ""),
            metadata.get("H2", ""),
            metadata.get("H3", ""),
            metadata.get("H4", ""),
        ]
        chunk_heading_path = [h for h in chunk_heading_path if h]

        if content and len(content) >= settings.chunk_min_chars:
            chunks.append(
                Chunk(
                    text=content,
                    heading_path=chunk_heading_path,
                    section_path=" > ".join(chunk_heading_path),
                    index=index,
                    start=0,
                    end=len(content),
                )
            )
            index += 1

    return index


def chunk_document(root: Node) -> List[Chunk]:
    """Main entry point for document chunking."""
    chunks: List[Chunk] = []
    _walk(root, [], chunks, 0)
    return chunks


class ChunkingStats:
    """Statistics for chunking operations."""

    def __init__(self):
        self.total_documents = 0
        self.total_chunks = 0
        self.avg_chunk_size = 0
        self.method_used = "sentence"

    def update(self, doc_size: int, num_chunks: int):
        self.total_documents += 1
        self.total_chunks += num_chunks
        if self.total_chunks > 0:
            self.avg_chunk_size = (
                self.avg_chunk_size * (self.total_documents - 1)
                + doc_size // num_chunks
            ) / self.total_documents

    def get_stats(self) -> dict:
        return {
            "documents": self.total_documents,
            "chunks": self.total_chunks,
            "avg_chunk_size": round(self.avg_chunk_size, 2),
            "method": self.method_used,
        }


_stats = ChunkingStats()


def get_chunking_stats() -> dict:
    """Get chunking statistics."""
    return _stats.get_stats()
