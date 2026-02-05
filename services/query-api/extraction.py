"""
Extraction Service - Prompt-to-Raw extraction with storage.

This module provides:
- Prompt building for extraction tasks
- LLM invocation for structured extraction
- Validation and confidence scoring
- Database storage of extracted data
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

import httpx

from config import settings
from prompt_builder import RAGPromptBuilder, ContextChunk

logger = logging.getLogger("extraction")


@dataclass
class ExtractionResult:
    """Result of an extraction operation."""

    success: bool
    data: Optional[Dict[str, Any]]
    confidence: float
    validation_errors: List[str]
    extraction_id: Optional[str] = None
    raw_response: Optional[str] = None


class ExtractionService:
    """Service for extracting structured data from documents."""

    def __init__(
        self,
        llm_gateway_url: Optional[str] = None,
        query_api_url: Optional[str] = None,
    ):
        self.llm_gateway_url = llm_gateway_url or settings.llm_gateway_url
        self.query_api_url = query_api_url or settings.query_api_url
        self.prompt_builder = RAGPromptBuilder()

    def extract_from_search(
        self,
        query: str,
        tenant_id: str,
        extraction_schema: Dict[str, Any],
        top_k: int = 5,
        min_confidence: float = 0.7,
    ) -> ExtractionResult:
        """
        Extract structured data by first searching for relevant context,
        then extracting from that context.

        Args:
            query: The extraction query/question
            tenant_id: Tenant ID for multi-tenancy
            extraction_schema: JSON schema defining expected output
            top_k: Number of search results to retrieve
            min_confidence: Minimum confidence threshold

        Returns:
            ExtractionResult with data and metadata
        """
        try:
            # Step 1: Search for relevant context
            search_results = self._search_context(query, tenant_id, top_k)

            if not search_results:
                return ExtractionResult(
                    success=False,
                    data=None,
                    confidence=0.0,
                    validation_errors=["No relevant context found"],
                )

            # Step 2: Build extraction prompt
            chunks = self._convert_to_chunks(search_results)
            prompt = self.prompt_builder.build_extraction_prompt(
                query=query,
                context_chunks=chunks,
                extraction_schema=extraction_schema,
            )

            # Step 3: Extract structured data
            extraction_result = self._call_extraction_endpoint(
                prompt=prompt,
                schema=extraction_schema,
            )

            # Step 4: Check confidence threshold
            if extraction_result.confidence < min_confidence:
                logger.warning(
                    f"Extraction confidence {extraction_result.confidence:.2f} "
                    f"below threshold {min_confidence}"
                )
                extraction_result.success = False

            return extraction_result

        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return ExtractionResult(
                success=False,
                data=None,
                confidence=0.0,
                validation_errors=[str(e)],
            )

    def extract_from_text(
        self,
        text: str,
        extraction_task: str,
        extraction_schema: Dict[str, Any],
        min_confidence: float = 0.7,
    ) -> ExtractionResult:
        """
        Extract structured data directly from provided text.

        Args:
            text: Source text to extract from
            extraction_task: Description of what to extract
            extraction_schema: JSON schema defining expected output
            min_confidence: Minimum confidence threshold

        Returns:
            ExtractionResult with data and metadata
        """
        try:
            # Build prompt with text as context
            prompt = f"""Context:
{text}

Extraction Task: {extraction_task}

Extract the information and return as JSON."""

            # Call extraction endpoint
            extraction_result = self._call_extraction_endpoint(
                prompt=prompt,
                schema=extraction_schema,
            )

            # Check confidence threshold
            if extraction_result.confidence < min_confidence:
                extraction_result.success = False

            return extraction_result

        except Exception as e:
            logger.error(f"Extraction from text failed: {e}")
            return ExtractionResult(
                success=False,
                data=None,
                confidence=0.0,
                validation_errors=[str(e)],
            )

    def _search_context(
        self,
        query: str,
        tenant_id: str,
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """Search for relevant context chunks."""
        url = f"{self.query_api_url}/search"

        payload = {
            "query": query,
            "tenant_id": tenant_id,
            "top_k": top_k,
        }

        try:
            resp = httpx.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data.get("results", [])
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def _convert_to_chunks(
        self, search_results: List[Dict[str, Any]]
    ) -> List[ContextChunk]:
        """Convert search results to ContextChunk objects."""
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
        return chunks

    def _call_extraction_endpoint(
        self,
        prompt: str,
        schema: Dict[str, Any],
    ) -> ExtractionResult:
        """Call the LLM Gateway extraction endpoint."""
        url = f"{self.llm_gateway_url}/extract"

        payload = {
            "prompt": prompt,
            "schema": schema,
            "max_tokens": 1024,
            "temperature": 0.1,
        }

        try:
            resp = httpx.post(url, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()

            return ExtractionResult(
                success=data.get("confidence", 0) >= 0.7
                and len(data.get("validation_errors", [])) == 0,
                data=data.get("data"),
                confidence=data.get("confidence", 0.0),
                validation_errors=data.get("validation_errors", []),
                raw_response=data.get("raw_text"),
            )

        except Exception as e:
            logger.error(f"Extraction endpoint call failed: {e}")
            return ExtractionResult(
                success=False,
                data=None,
                confidence=0.0,
                validation_errors=[f"LLM Gateway error: {str(e)}"],
            )


def validate_extraction_result(
    result: ExtractionResult,
    required_fields: Optional[List[str]] = None,
    min_confidence: float = 0.7,
) -> Dict[str, Any]:
    """
    Validate an extraction result against requirements.

    Args:
        result: The extraction result to validate
        required_fields: List of required field names
        min_confidence: Minimum confidence threshold

    Returns:
        Validation report
    """
    report = {
        "is_valid": True,
        "confidence_ok": result.confidence >= min_confidence,
        "has_data": result.data is not None,
        "validation_errors": result.validation_errors,
        "missing_fields": [],
    }

    # Check confidence
    if not report["confidence_ok"]:
        report["is_valid"] = False

    # Check data exists
    if not report["has_data"]:
        report["is_valid"] = False
        report["missing_fields"] = required_fields or []
        return report

    # Check required fields
    if required_fields:
        for field in required_fields:
            if field not in result.data or result.data[field] is None:
                report["missing_fields"].append(field)

        if report["missing_fields"]:
            report["is_valid"] = False

    # Check validation errors
    if result.validation_errors:
        report["is_valid"] = False

    return report


if __name__ == "__main__":
    # Example usage
    print("Extraction Service Example")
    print("=" * 60)

    # Sample extraction schema for person information
    person_schema = {
        "type": "object",
        "description": "Person information",
        "properties": {
            "name": {"type": "string", "description": "Full name of the person"},
            "age": {"type": "integer", "description": "Age in years"},
            "email": {"type": "string", "description": "Email address"},
            "department": {"type": "string", "description": "Department name"},
            "skills": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of skills",
            },
        },
        "required": ["name", "email"],
    }

    # Sample text
    sample_text = """
    John Doe is a senior software engineer at TechCorp. He is 32 years old and specializes in 
    Python, machine learning, and cloud architecture. You can reach him at john.doe@techcorp.com.
    He works in the Engineering department.
    """

    print("\nSchema:")
    print(json.dumps(person_schema, indent=2))

    print("\nSample Text:")
    print(sample_text)

    # This would normally call the LLM
    print("\nTo extract data, initialize the service and call extract_from_text()")
    print(
        "ExtractionService().extract_from_text(sample_text, 'Extract person info', person_schema)"
    )
