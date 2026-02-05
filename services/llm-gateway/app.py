"""
Enhanced LLM Gateway with extraction and structured output support.
"""

from datetime import datetime, UTC
from typing import Optional, Dict, Any, List
import json
import re
import logging

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from config import settings

logger = logging.getLogger("llm_gateway")


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    max_tokens: int = 512
    temperature: float = 0.2


class GenerateResponse(BaseModel):
    text: str
    model: str
    backend: str


class ExtractRequest(BaseModel):
    """Request for structured data extraction."""

    prompt: str = Field(..., min_length=1)
    schema: Dict[str, Any] = Field(..., description="JSON schema for expected output")
    max_tokens: int = 1024
    temperature: float = 0.1  # Lower temp for more deterministic extraction


class ExtractResponse(BaseModel):
    """Response from structured extraction."""

    data: Optional[Dict[str, Any]]
    raw_text: str
    confidence: float
    validation_errors: List[str]
    model: str
    backend: str


class RAGQueryRequest(BaseModel):
    """Request for RAG-based question answering."""

    query: str = Field(..., min_length=1)
    context: str = Field(
        ..., min_length=1, description="Retrieved context with citations"
    )
    max_tokens: int = 1024
    temperature: float = 0.3


class RAGQueryResponse(BaseModel):
    """Response from RAG query."""

    answer: str
    citations: List[str]
    confidence: float
    model: str
    backend: str


app = FastAPI(title="LLM Gateway")


def _mock_generate(prompt: str) -> str:
    """Mock generation for testing."""
    return "[MOCK] " + prompt[:400]


def _ollama_generate(
    prompt: str,
    max_tokens: int,
    temperature: float,
    system_prompt: Optional[str] = None,
) -> str:
    """Generate text using Ollama backend."""
    url = f"{settings.ollama_host}/api/generate"

    payload = {
        "model": settings.model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }

    if system_prompt:
        payload["system"] = system_prompt

    try:
        resp = httpx.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "")
    except Exception as exc:
        logger.error(f"Ollama generation failed: {exc}")
        raise HTTPException(status_code=502, detail=f"LLM backend error: {exc}")


def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Extract JSON object from text, handling various formats."""
    # Try to find JSON between code blocks
    code_block_pattern = r"```(?:json)?\s*([\s\S]*?)```"
    matches = re.findall(code_block_pattern, text)

    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue

    # Try to find JSON between curly braces
    json_pattern = r"\{[\s\S]*\}"
    matches = re.findall(json_pattern, text)

    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue

    # Try the whole text
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    return None


def _validate_against_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """Validate extracted data against JSON schema."""
    errors = []

    if schema.get("type") != "object":
        return ["Schema must be an object type"]

    properties = schema.get("properties", {})
    required = schema.get("required", [])

    # Check required fields
    for field in required:
        if field not in data:
            errors.append(f"Missing required field: {field}")
        elif data[field] is None:
            errors.append(f"Required field is null: {field}")

    # Check types
    for field, value in data.items():
        if field in properties:
            prop_schema = properties[field]
            expected_type = prop_schema.get("type")

            if expected_type == "string" and not isinstance(value, str):
                errors.append(f"Field '{field}' should be a string")
            elif expected_type == "integer" and not isinstance(value, int):
                errors.append(f"Field '{field}' should be an integer")
            elif expected_type == "number" and not isinstance(value, (int, float)):
                errors.append(f"Field '{field}' should be a number")
            elif expected_type == "boolean" and not isinstance(value, bool):
                errors.append(f"Field '{field}' should be a boolean")
            elif expected_type == "array" and not isinstance(value, list):
                errors.append(f"Field '{field}' should be an array")
            elif expected_type == "object" and not isinstance(value, dict):
                errors.append(f"Field '{field}' should be an object")

            # Check enum
            if "enum" in prop_schema and value not in prop_schema["enum"]:
                errors.append(
                    f"Field '{field}' value '{value}' not in enum {prop_schema['enum']}"
                )

    return errors


def _calculate_confidence(
    data: Optional[Dict[str, Any]], schema: Dict[str, Any], validation_errors: List[str]
) -> float:
    """Calculate confidence score for extraction."""
    if data is None:
        return 0.0

    if validation_errors:
        # Calculate based on errors vs total fields
        total_fields = len(schema.get("properties", {}))
        if total_fields == 0:
            return 0.5
        error_weight = len(validation_errors) / total_fields
        return max(0.0, 1.0 - error_weight * 0.5)

    # Check completeness
    required = schema.get("required", [])
    if required:
        filled_required = sum(1 for field in required if data.get(field) is not None)
        completeness = filled_required / len(required)
    else:
        completeness = 1.0

    # Base confidence on completeness
    confidence = 0.7 + (completeness * 0.3)

    return min(1.0, confidence)


def _extract_citations(text: str) -> List[str]:
    """Extract citation references from generated text."""
    # Pattern to match [doc_id] or [Document X] citations
    patterns = [
        r"\[([^\]]+:[^\]]+)\]",  # [doc_id:chunk_index]
        r"\[Document (\d+)\]",  # [Document 1]
        r"\[([^\]]+)\]",  # [any citation]
    ]

    citations = set()
    for pattern in patterns:
        matches = re.findall(pattern, text)
        citations.update(matches)

    return list(citations)


@app.get("/healthz")
def healthz():
    """Health check endpoint."""
    return {
        "status": "ok",
        "time": datetime.now(UTC).isoformat(),
        "model": settings.model,
        "backend": settings.llm_backend,
    }


@app.post("/generate", response_model=GenerateResponse)
def generate(payload: GenerateRequest):
    """Generate text from prompt."""
    if settings.llm_backend == "mock":
        text = _mock_generate(payload.prompt)
    else:
        text = _ollama_generate(payload.prompt, payload.max_tokens, payload.temperature)

    return GenerateResponse(
        text=text, model=settings.model, backend=settings.llm_backend
    )


@app.post("/extract", response_model=ExtractResponse)
def extract(payload: ExtractRequest):
    """
    Extract structured data from prompt using JSON schema.

    Uses structured prompting to ensure JSON output.
    """
    # Build extraction-specific system prompt
    system_prompt = """You are a precise data extraction AI. Your task is to extract structured information and return it as valid JSON.
Rules:
1. Return ONLY valid JSON, no markdown formatting, no explanations
2. Follow the schema exactly
3. Use null for missing optional fields
4. Do not include any text outside the JSON object
5. Ensure proper JSON syntax with double quotes"""

    # Enhance prompt with schema info
    enhanced_prompt = f"""{payload.prompt}

You must return a JSON object matching this schema:
{json.dumps(payload.schema, indent=2)}

Remember: Return ONLY the JSON object, nothing else."""

    # Generate
    if settings.llm_backend == "mock":
        raw_text = _mock_generate(enhanced_prompt)
        # Mock extraction for testing
        if "person" in payload.prompt.lower():
            raw_text = '{"name": "John Doe", "age": 30, "email": "john@example.com"}'
        else:
            raw_text = '{"extracted": "mock data"}'
    else:
        raw_text = _ollama_generate(
            enhanced_prompt,
            payload.max_tokens,
            payload.temperature,
            system_prompt=system_prompt,
        )

    # Extract JSON
    data = _extract_json_from_text(raw_text)

    # Validate
    validation_errors = []
    if data is not None:
        validation_errors = _validate_against_schema(data, payload.schema)
    else:
        validation_errors = ["Failed to parse JSON from response"]

    # Calculate confidence
    confidence = _calculate_confidence(data, payload.schema, validation_errors)

    logger.info(
        f"Extraction completed: confidence={confidence:.2f}, "
        f"errors={len(validation_errors)}, has_data={data is not None}"
    )

    return ExtractResponse(
        data=data,
        raw_text=raw_text,
        confidence=confidence,
        validation_errors=validation_errors,
        model=settings.model,
        backend=settings.llm_backend,
    )


@app.post("/rag", response_model=RAGQueryResponse)
def rag_query(payload: RAGQueryRequest):
    """
    Answer a query using RAG context.

    The context should include retrieved documents with citations.
    """
    # Build RAG system prompt
    system_prompt = """You are a helpful RAG assistant. Answer the user's question using ONLY the provided context.
Rules:
1. Use only information from the provided context
2. Cite sources using [doc_id] format
3. Be concise and accurate
4. If the answer isn't in the context, say so clearly"""

    # Build the prompt
    prompt = f"""Context:
{payload.context}

Question: {payload.query}

Provide a clear, accurate answer based on the context above. Cite sources using [doc_id] format."""

    # Generate answer
    if settings.llm_backend == "mock":
        answer = f"[MOCK] Based on the provided context, here's the answer to: {payload.query[:50]}..."
        citations = ["doc001", "doc002"]
        confidence = 0.85
    else:
        answer = _ollama_generate(
            prompt,
            payload.max_tokens,
            payload.temperature,
            system_prompt=system_prompt,
        )
        citations = _extract_citations(answer)
        confidence = 0.75 if citations else 0.5

    return RAGQueryResponse(
        answer=answer,
        citations=citations,
        confidence=confidence,
        model=settings.model,
        backend=settings.llm_backend,
    )


@app.get("/models")
def list_models():
    """List available models (Ollama specific)."""
    if settings.llm_backend == "mock":
        return {
            "models": ["mock-model"],
            "current": settings.model,
        }

    try:
        url = f"{settings.ollama_host}/api/tags"
        resp = httpx.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return {
            "models": [m["name"] for m in data.get("models", [])],
            "current": settings.model,
        }
    except Exception as exc:
        logger.error(f"Failed to list models: {exc}")
        return {
            "models": [],
            "current": settings.model,
            "error": str(exc),
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.service_port)
