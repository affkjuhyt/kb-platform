from parsers import parse_markdown
from chunker import chunk_document


def test_markdown_chunking_has_paths():
    md = """# Title\nIntro text.\n## Section A\nDetails A.\n## Section B\nDetails B."""
    root = parse_markdown(md)
    chunks = chunk_document(root)
    assert len(chunks) >= 2
    assert all(c.section_path for c in chunks)


def test_chunk_sizes_respect_min():
    md = """# Title\nShort.\n\n## Section A\nThis is a longer paragraph. It should be merged if too small."""
    root = parse_markdown(md)
    chunks = chunk_document(root)
    assert all(len(c.text) >= 1 for c in chunks)
