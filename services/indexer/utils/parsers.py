import re
from io import BytesIO
from typing import Optional

from bs4 import BeautifulSoup
from pypdf import PdfReader
from docx import Document as DocxDocument

from models import Node


def parse_text(content: str) -> Node:
    return Node(heading="document", level=0, text=content)


def parse_markdown(content: str) -> Node:
    root = Node(heading="document", level=0, text="")
    stack = [root]

    for line in content.splitlines():
        match = re.match(r"^(#{1,6})\s+(.*)", line)
        if match:
            level = len(match.group(1))
            heading = match.group(2).strip()
            node = Node(heading=heading, level=level, text="")
            while stack and stack[-1].level >= level:
                stack.pop()
            stack[-1].add_child(node)
            stack.append(node)
        else:
            stack[-1].text += line + "\n"

    return root


def parse_html(content: str) -> Node:
    soup = BeautifulSoup(content, "html.parser")
    root = Node(heading="document", level=0, text="")
    stack = [root]

    for elem in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li"]):
        if elem.name.startswith("h"):
            level = int(elem.name[1])
            heading = elem.get_text(strip=True) or f"section-{level}"
            node = Node(heading=heading, level=level, text="")
            while stack and stack[-1].level >= level:
                stack.pop()
            stack[-1].add_child(node)
            stack.append(node)
        else:
            text = elem.get_text(" ", strip=True)
            if text:
                stack[-1].text += text + "\n"

    return root


def parse_pdf(data: bytes) -> Node:
    try:
        reader = PdfReader(BytesIO(data))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return parse_text("\n".join(parts))
    except Exception:
        return parse_text(data.decode("utf-8", errors="ignore"))


def parse_docx(data: bytes) -> Node:
    try:
        doc = DocxDocument(BytesIO(data))
        parts = [p.text for p in doc.paragraphs if p.text]
        return parse_text("\n".join(parts))
    except Exception:
        return parse_text(data.decode("utf-8", errors="ignore"))


def parse_content(
    *,
    data: bytes,
    content_type: str,
    filename: Optional[str] = None,
) -> Node:
    ct = (content_type or "").lower()

    if "text/markdown" in ct or (filename and filename.endswith(".md")):
        return parse_markdown(data.decode("utf-8", errors="ignore"))
    if "text/html" in ct or (filename and filename.endswith(".html")):
        return parse_html(data.decode("utf-8", errors="ignore"))
    if "application/pdf" in ct or (filename and filename.endswith(".pdf")):
        return parse_pdf(data)
    if "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in ct or (
        filename and filename.endswith(".docx")
    ):
        return parse_docx(data)

    return parse_text(data.decode("utf-8", errors="ignore"))
