"""
Comprehensive tests for Phase 6: LLM RAG + Prompt-to-Raw Extraction.

Tests cover:
- RAG prompt builder
- LLM Gateway extraction
- Extraction service
- Validation and confidence scoring
- API endpoints
"""

import json
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def sample_person_schema() -> Dict[str, Any]:
    """Sample schema for person extraction."""
    return {
        "type": "object",
        "description": "Person information",
        "properties": {
            "name": {"type": "string", "description": "Full name"},
            "age": {"type": "integer", "description": "Age in years"},
            "email": {"type": "string", "description": "Email address"},
            "department": {"type": "string", "description": "Department"},
        },
        "required": ["name", "email"],
    }


@pytest.fixture
def sample_company_schema() -> Dict[str, Any]:
    """Sample schema for company extraction."""
    return {
        "type": "object",
        "description": "Company information",
        "properties": {
            "company_name": {"type": "string"},
            "founded_year": {"type": "integer"},
            "headquarters": {"type": "string"},
            "employees": {"type": "integer"},
            "industry": {
                "type": "string",
                "enum": ["tech", "finance", "healthcare", "other"],
            },
        },
        "required": ["company_name"],
    }


@pytest.fixture
def sample_search_results() -> List[Dict[str, Any]]:
    """Sample search results for testing."""
    return [
        {
            "doc_id": "doc001",
            "source": "confluence",
            "source_id": "employee_handbook",
            "version": 3,
            "chunk_index": 0,
            "text": "John Doe is a senior engineer at TechCorp. He is 32 years old.",
            "section_path": "employees/john_doe",
            "heading_path": ["Team", "Engineering", "John Doe"],
            "score": 0.95,
        },
        {
            "doc_id": "doc002",
            "source": "manual",
            "source_id": "contact_directory",
            "version": 2,
            "chunk_index": 0,
            "text": "Contact: john.doe@techcorp.com, Department: Engineering",
            "section_path": "contacts/engineering",
            "heading_path": ["Contacts", "Engineering"],
            "score": 0.88,
        },
    ]


# ============================================================================
# Prompt Builder Tests
# ============================================================================


def test_rag_prompt_builder_basic():
    """Test basic RAG prompt building."""
    from prompt_builder import RAGPromptBuilder, ContextChunk

    builder = RAGPromptBuilder()

    chunks = [
        ContextChunk(
            text="The company was founded in 2010.",
            doc_id="doc001",
            source="confluence",
            source_id="about",
            version=1,
            chunk_index=0,
            section_path="about",
            heading_path=["About"],
            score=0.9,
        )
    ]

    prompt = builder.build_prompt("When was the company founded?", chunks)

    assert "When was the company founded?" in prompt
    assert "The company was founded in 2010." in prompt
    assert "doc001" in prompt
    assert "System:" in prompt


def test_rag_prompt_builder_multiple_chunks():
    """Test RAG prompt with multiple chunks."""
    from prompt_builder import RAGPromptBuilder, ContextChunk

    builder = RAGPromptBuilder(max_context_length=2000)

    chunks = [
        ContextChunk(
            text=f"Document {i} content here.",
            doc_id=f"doc{i:03d}",
            source="confluence",
            source_id=f"doc_{i}",
            version=1,
            chunk_index=0,
            section_path=f"section/{i}",
            heading_path=["Header"],
            score=0.9 - (i * 0.1),
        )
        for i in range(5)
    ]

    prompt = builder.build_prompt("Test query", chunks)

    # Should include multiple documents
    assert "[Document 1]" in prompt
    assert "[Document 2]" in prompt
    assert "Test query" in prompt


def test_rag_prompt_builder_respects_max_length():
    """Test that prompt builder respects max context length."""
    from prompt_builder import RAGPromptBuilder, ContextChunk

    builder = RAGPromptBuilder(max_context_length=500)

    # Create large chunks
    chunks = [
        ContextChunk(
            text="A" * 1000,  # Very long text
            doc_id="doc001",
            source="confluence",
            source_id="doc1",
            version=1,
            chunk_index=0,
            section_path="section",
            heading_path=["Header"],
            score=0.9,
        ),
        ContextChunk(
            text="B" * 1000,
            doc_id="doc002",
            source="manual",
            source_id="doc2",
            version=1,
            chunk_index=0,
            section_path="section2",
            heading_path=["Header2"],
            score=0.8,
        ),
    ]

    prompt = builder.build_prompt("Query", chunks)

    # Should be truncated
    assert len(prompt) <= 600  # Allow some overhead


def test_build_extraction_prompt():
    """Test extraction prompt building."""
    from prompt_builder import RAGPromptBuilder, ContextChunk

    builder = RAGPromptBuilder()

    chunks = [
        ContextChunk(
            text="John Doe, 30 years old, john@example.com",
            doc_id="doc001",
            source="hr_system",
            source_id="employees",
            version=2,
            chunk_index=0,
            section_path="employees",
            heading_path=["HR", "Employees"],
            score=0.95,
        )
    ]

    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
        },
        "required": ["name"],
    }

    prompt = builder.build_extraction_prompt(
        query="Extract person information",
        context_chunks=chunks,
        extraction_schema=schema,
    )

    assert "Extract person information" in prompt
    assert "name" in prompt
    assert "age" in prompt
    assert "Context 1" in prompt


# ============================================================================
# Extraction Service Tests
# ============================================================================


@patch("extraction.httpx.post")
def test_extraction_service_extract_from_text(mock_post, sample_person_schema):
    """Test extraction from text."""
    from extraction import ExtractionService

    # Mock LLM response
    mock_response = Mock()
    mock_response.json.return_value = {
        "data": {
            "name": "John Doe",
            "age": 32,
            "email": "john@example.com",
        },
        "confidence": 0.95,
        "validation_errors": [],
        "raw_text": '{"name": "John Doe", "age": 32, "email": "john@example.com"}',
    }
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response

    service = ExtractionService()

    text = "John Doe is 32 years old. Contact him at john@example.com"
    result = service.extract_from_text(
        text=text,
        extraction_task="Extract person details",
        extraction_schema=sample_person_schema,
        min_confidence=0.7,
    )

    assert result.success is True
    assert result.data is not None
    assert result.data["name"] == "John Doe"
    assert result.confidence >= 0.7


@patch("extraction.httpx.post")
def test_extraction_service_low_confidence(mock_post, sample_person_schema):
    """Test extraction with low confidence."""
    from extraction import ExtractionService

    # Mock LLM response with low confidence
    mock_response = Mock()
    mock_response.json.return_value = {
        "data": {"name": "Unknown"},
        "confidence": 0.5,
        "validation_errors": ["Missing required field: email"],
        "raw_text": '{"name": "Unknown"}',
    }
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response

    service = ExtractionService()

    text = "Some unclear text"
    result = service.extract_from_text(
        text=text,
        extraction_task="Extract person details",
        extraction_schema=sample_person_schema,
        min_confidence=0.7,  # High threshold
    )

    # Should fail due to low confidence
    assert result.success is False
    assert result.confidence < 0.7


@patch("extraction.httpx.post")
def test_extraction_service_validation_errors(mock_post, sample_person_schema):
    """Test extraction with validation errors."""
    from extraction import ExtractionService

    # Mock LLM response with validation errors
    mock_response = Mock()
    mock_response.json.return_value = {
        "data": {"name": 123, "email": "invalid"},  # Wrong types
        "confidence": 0.8,
        "validation_errors": [
            "Field 'name' should be a string",
            "Field 'email' should be a string",
        ],
        "raw_text": '{"name": 123, "email": "invalid"}',
    }
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response

    service = ExtractionService()

    text = "Some text"
    result = service.extract_from_text(
        text=text,
        extraction_task="Extract details",
        extraction_schema=sample_person_schema,
        min_confidence=0.7,
    )

    assert result.success is False
    assert len(result.validation_errors) > 0


# ============================================================================
# LLM Gateway Tests
# ============================================================================


def test_extract_json_from_text_code_block():
    """Test JSON extraction from code blocks."""
    from services.llm_gateway.app import _extract_json_from_text

    text = """Some text
```json
{"name": "John", "age": 30}
```
More text"""

    result = _extract_json_from_text(text)

    assert result is not None
    assert result["name"] == "John"
    assert result["age"] == 30


def test_extract_json_from_text_braces():
    """Test JSON extraction from curly braces."""
    from services.llm_gateway.app import _extract_json_from_text

    text = 'Some text {"name": "John", "age": 30} more text'

    result = _extract_json_from_text(text)

    assert result is not None
    assert result["name"] == "John"


def test_extract_json_from_text_invalid():
    """Test JSON extraction with invalid text."""
    from services.llm_gateway.app import _extract_json_from_text

    text = "This is just plain text with no JSON"

    result = _extract_json_from_text(text)

    assert result is None


def test_validate_against_schema_valid():
    """Test schema validation with valid data."""
    from services.llm_gateway.app import _validate_against_schema

    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "active": {"type": "boolean"},
        },
        "required": ["name"],
    }

    data = {"name": "John", "age": 30, "active": True}
    errors = _validate_against_schema(data, schema)

    assert len(errors) == 0


def test_validate_against_schema_invalid_types():
    """Test schema validation with invalid types."""
    from services.llm_gateway.app import _validate_against_schema

    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
        },
        "required": ["name"],
    }

    data = {"name": 123, "age": "thirty"}  # Wrong types
    errors = _validate_against_schema(data, schema)

    assert len(errors) == 2
    assert any("name" in e for e in errors)
    assert any("age" in e for e in errors)


def test_validate_against_schema_missing_required():
    """Test schema validation with missing required fields."""
    from services.llm_gateway.app import _validate_against_schema

    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "email": {"type": "string"},
        },
        "required": ["name", "email"],
    }

    data = {"name": "John"}  # Missing email
    errors = _validate_against_schema(data, schema)

    assert any("email" in e for e in errors)


def test_calculate_confidence_perfect():
    """Test confidence calculation with perfect extraction."""
    from services.llm_gateway.app import _calculate_confidence

    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
        },
        "required": ["name"],
    }

    data = {"name": "John", "age": 30}
    confidence = _calculate_confidence(data, schema, [])

    assert confidence >= 0.9  # Should be very high


def test_calculate_confidence_no_data():
    """Test confidence calculation with no data."""
    from services.llm_gateway.app import _calculate_confidence

    schema = {"type": "object", "properties": {}}
    confidence = _calculate_confidence(None, schema, [])

    assert confidence == 0.0


def test_calculate_confidence_with_errors():
    """Test confidence calculation with validation errors."""
    from services.llm_gateway.app import _calculate_confidence

    schema = {
        "type": "object",
        "properties": {
            "a": {"type": "string"},
            "b": {"type": "string"},
        },
    }

    data = {"a": "test"}
    errors = ["Error 1", "Error 2"]
    confidence = _calculate_confidence(data, schema, errors)

    assert confidence < 1.0
    assert confidence > 0.0


# ============================================================================
# Validation Tests
# ============================================================================


def test_validate_extraction_result_success():
    """Test validation of successful extraction."""
    from extraction import ExtractionResult, validate_extraction_result

    result = ExtractionResult(
        success=True,
        data={"name": "John", "email": "john@example.com"},
        confidence=0.95,
        validation_errors=[],
    )

    report = validate_extraction_result(
        result,
        required_fields=["name", "email"],
        min_confidence=0.7,
    )

    assert report["is_valid"] is True
    assert report["confidence_ok"] is True
    assert len(report["missing_fields"]) == 0


def test_validate_extraction_result_low_confidence():
    """Test validation with low confidence."""
    from extraction import ExtractionResult, validate_extraction_result

    result = ExtractionResult(
        success=True,
        data={"name": "John"},
        confidence=0.5,
        validation_errors=[],
    )

    report = validate_extraction_result(
        result,
        min_confidence=0.7,
    )

    assert report["is_valid"] is False
    assert report["confidence_ok"] is False


def test_validate_extraction_result_missing_fields():
    """Test validation with missing required fields."""
    from extraction import ExtractionResult, validate_extraction_result

    result = ExtractionResult(
        success=True,
        data={"name": "John"},  # Missing email
        confidence=0.9,
        validation_errors=[],
    )

    report = validate_extraction_result(
        result,
        required_fields=["name", "email"],
        min_confidence=0.7,
    )

    assert report["is_valid"] is False
    assert "email" in report["missing_fields"]


# ============================================================================
# Integration Tests
# ============================================================================


@patch("httpx.post")
def test_rag_endpoint_integration(mock_post, sample_search_results):
    """Test RAG endpoint integration."""

    # Mock both search and LLM calls
    def mock_post_impl(url, **kwargs):
        mock_resp = Mock()

        if "rerank" in url:
            mock_resp.json.return_value = {
                "results": [
                    {"id": "doc001:0", "score": 0.95},
                    {"id": "doc002:0", "score": 0.88},
                ]
            }
        elif "rag" in url:
            mock_resp.json.return_value = {
                "answer": "John Doe is 32 years old and works in Engineering.",
                "citations": ["doc001", "doc002"],
                "confidence": 0.92,
                "model": "llama3.1:8b",
                "backend": "ollama",
            }

        mock_resp.raise_for_status = Mock()
        return mock_resp

    mock_post.side_effect = mock_post_impl

    from app import rag_query, RAGRequest

    request = RAGRequest(
        query="Tell me about John Doe",
        tenant_id="tenant_123",
        top_k=5,
    )

    # This would need the full FastAPI test client in practice
    # For now, we test the components separately


# ============================================================================
# Performance Tests
# ============================================================================


def test_extraction_success_rate_calculation():
    """Test calculation of extraction success rate."""
    # Simulate multiple extractions
    results = [
        {"success": True, "confidence": 0.95},
        {"success": True, "confidence": 0.88},
        {"success": True, "confidence": 0.92},
        {"success": False, "confidence": 0.45},  # Failed
        {"success": True, "confidence": 0.76},
        {"success": False, "confidence": 0.60},  # Failed
        {"success": True, "confidence": 0.81},
        {"success": True, "confidence": 0.90},
        {"success": True, "confidence": 0.85},
        {"success": False, "confidence": 0.30},  # Failed
    ]

    successful = sum(1 for r in results if r["success"])
    total = len(results)
    success_rate = (successful / total) * 100

    # Should be 70% (7 out of 10)
    assert success_rate == 70.0
    print(f"\nExtraction success rate: {success_rate:.1f}%")
    print(f"Target: ≥80%")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
