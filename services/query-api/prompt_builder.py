"""
RAG Prompt Builder Module

Builds structured prompts for LLM inference with citations and context.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ContextChunk:
    """A context chunk with citation information."""

    text: str
    doc_id: str
    source: str
    source_id: str
    version: int
    chunk_index: int
    section_path: str
    heading_path: List[str]
    score: float

    def get_citation(self) -> str:
        """Generate a citation string for this chunk."""
        citation_parts = [
            f"[{self.doc_id}]",
            f"Source: {self.source}",
            f"ID: {self.source_id}",
            f"v{self.version}",
        ]
        if self.heading_path:
            citation_parts.append(f"Section: {' > '.join(self.heading_path)}")
        return " | ".join(citation_parts)


class RAGPromptBuilder:
    """Builds RAG prompts with proper context and citations."""

    # System prompt template for RAG
    RAG_SYSTEM_PROMPT = """You are a helpful assistant that answers questions based on the provided context. 
Follow these rules:
1. Answer using ONLY the information from the provided context
2. If the context doesn't contain the answer, say "I don't have enough information to answer this question"
3. Always cite your sources using the citation format [doc_id]
4. Be concise and accurate
5. If multiple sources provide the same information, cite all of them"""

    def __init__(self, max_context_length: int = 4000, citation_format: str = "inline"):
        self.max_context_length = max_context_length
        self.citation_format = citation_format

    def build_prompt(
        self,
        query: str,
        context_chunks: List[ContextChunk],
        include_citations: bool = True,
    ) -> str:
        """
        Build a RAG prompt with context.

        Args:
            query: The user's question
            context_chunks: Retrieved context chunks with citations
            include_citations: Whether to include citation requirements

        Returns:
            Complete prompt for LLM
        """
        # Build context section
        context_parts = []
        total_length = 0

        for i, chunk in enumerate(context_chunks, 1):
            chunk_text = f"\n[Document {i}]\n"
            chunk_text += f"Citation: {chunk.get_citation()}\n"
            chunk_text += f"Content: {chunk.text}\n"

            # Check if adding this chunk would exceed limit
            if total_length + len(chunk_text) > self.max_context_length:
                break

            context_parts.append(chunk_text)
            total_length += len(chunk_text)

        context_str = "".join(context_parts)

        # Build the complete prompt
        prompt_parts = [
            "System:",
            self.RAG_SYSTEM_PROMPT,
            "\n\nContext:",
            context_str if context_parts else "[No relevant context provided]",
            "\n\nQuestion:",
            query,
        ]

        if include_citations:
            prompt_parts.extend(
                [
                    "\n\nInstructions:",
                    "- Provide a clear, accurate answer based on the context above",
                    "- Cite sources using [doc_id] format (e.g., 'According to [doc123], ...')",
                    "- If information comes from multiple documents, cite all relevant ones",
                ]
            )

        return "\n".join(prompt_parts)

    def build_extraction_prompt(
        self,
        query: str,
        context_chunks: List[ContextChunk],
        extraction_schema: Dict[str, Any],
        examples: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Build a prompt for structured data extraction.

        Args:
            query: The extraction query or task description
            context_chunks: Retrieved context chunks
            extraction_schema: JSON schema describing expected output
            examples: Optional few-shot examples

        Returns:
            Complete extraction prompt
        """
        # Build context section
        context_str = self._build_context_section(context_chunks)

        # Build schema description
        schema_desc = self._format_schema(extraction_schema)

        prompt_parts = [
            "System:",
            "You are a data extraction assistant. Extract structured information from the provided context.",
            "\n\nContext:",
            context_str,
            "\n\nExtraction Task:",
            query,
            "\n\nOutput Schema:",
            schema_desc,
        ]

        if examples:
            prompt_parts.extend(
                [
                    "\n\nExamples:",
                    self._format_examples(examples),
                ]
            )

        prompt_parts.extend(
            [
                "\n\nInstructions:",
                "1. Extract information ONLY from the provided context",
                "2. Return valid JSON matching the schema exactly",
                "3. Use null for missing optional fields",
                "4. Do not include any text outside the JSON",
                "5. Ensure all dates are in ISO 8601 format",
            ]
        )

        return "\n".join(prompt_parts)

    def _build_context_section(self, chunks: List[ContextChunk]) -> str:
        """Build the context section from chunks."""
        if not chunks:
            return "[No context provided]"

        parts = []
        for i, chunk in enumerate(chunks, 1):
            parts.append(f"\n--- Context {i} ---")
            parts.append(f"Source: {chunk.source} (v{chunk.version})")
            parts.append(f"Content: {chunk.text[:500]}...")  # Truncate long content

        return "\n".join(parts)

    def _format_schema(self, schema: Dict[str, Any], indent: int = 0) -> str:
        """Format JSON schema in a readable way."""
        lines = []
        prefix = "  " * indent

        if schema.get("type") == "object" and "properties" in schema:
            lines.append(f"{prefix}{{  // {schema.get('description', 'object')}")
            for prop_name, prop_schema in schema["properties"].items():
                required = prop_name in schema.get("required", [])
                req_marker = "*" if required else ""

                if prop_schema.get("type") == "object":
                    lines.append(f'{prefix}  "{prop_name}"{req_marker}: {{')
                    lines.append(self._format_schema(prop_schema, indent + 2))
                    lines.append(f"{prefix}  }}")
                elif prop_schema.get("type") == "array":
                    item_type = prop_schema.get("items", {}).get("type", "any")
                    lines.append(
                        f'{prefix}  "{prop_name}"{req_marker}: [{item_type}]  // {prop_schema.get("description", "")}'
                    )
                else:
                    ptype = prop_schema.get("type", "any")
                    desc = prop_schema.get("description", "")
                    enum = prop_schema.get("enum", [])
                    if enum:
                        desc += f" (one of: {enum})"
                    lines.append(
                        f'{prefix}  "{prop_name}"{req_marker}: {ptype}  // {desc}'
                    )

            lines.append(f"{prefix}}}")

        return "\n".join(lines)

    def _format_examples(self, examples: List[Dict[str, Any]]) -> str:
        """Format few-shot examples."""
        import json

        parts = []
        for i, ex in enumerate(examples, 1):
            parts.append(f"\nExample {i}:")
            parts.append(f"Input: {ex.get('input', '')}")
            parts.append(
                f"Output: {json.dumps(ex.get('output', {}), indent=2, ensure_ascii=False)}"
            )
        return "\n".join(parts)


def build_rag_query_prompt(
    query: str, search_results: List[Dict[str, Any]], max_context_length: int = 4000
) -> str:
    """
    Convenience function to build a RAG prompt from search results.

    Args:
        query: User's question
        search_results: Results from search endpoint
        max_context_length: Maximum context length

    Returns:
        Complete prompt string
    """
    builder = RAGPromptBuilder(max_context_length=max_context_length)

    # Convert search results to ContextChunk objects
    chunks = []
    for result in search_results:
        chunk = ContextChunk(
            text=result.get("text", ""),
            doc_id=result.get("doc_id", ""),
            source=result.get("source", ""),
            source_id=result.get("source_id", ""),
            version=result.get("version", 1),
            chunk_index=result.get("chunk_index", 0),
            section_path=result.get("section_path", ""),
            heading_path=result.get("heading_path", []),
            score=result.get("score", 0.0),
        )
        chunks.append(chunk)

    return builder.build_prompt(query, chunks, include_citations=True)


if __name__ == "__main__":
    # Example usage
    builder = RAGPromptBuilder()

    # Sample context chunks
    chunks = [
        ContextChunk(
            text="The company was founded in 2010 by John Doe.",
            doc_id="doc001",
            source="confluence",
            source_id="about_company",
            version=3,
            chunk_index=0,
            section_path="company/about",
            heading_path=["About Us", "History"],
            score=0.95,
        ),
        ContextChunk(
            text="Our headquarters are located in San Francisco, California.",
            doc_id="doc002",
            source="manual",
            source_id="contact_info",
            version=2,
            chunk_index=0,
            section_path="contact/address",
            heading_path=["Contact", "Address"],
            score=0.88,
        ),
    ]

    query = "When was the company founded and where is it located?"
    prompt = builder.build_prompt(query, chunks)

    print("=" * 80)
    print("RAG PROMPT EXAMPLE")
    print("=" * 80)
    print(prompt)
    print("=" * 80)
