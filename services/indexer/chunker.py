import re
from typing import List

from models import Chunk, Node
from config import settings


def _split_units(text: str) -> List[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    units: List[str] = []
    for para in paragraphs:
        sentences = re.split(r"(?<=[.!?])\s+", para)
        for sent in sentences:
            if sent.strip():
                units.append(sent.strip())
    return units if units else [text.strip()]


def _merge_small(chunks: List[Chunk], min_chars: int) -> List[Chunk]:
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


def chunk_document(root: Node) -> List[Chunk]:
    chunks: List[Chunk] = []
    _walk(root, [], chunks, 0)
    return chunks
