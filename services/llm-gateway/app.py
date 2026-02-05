"""
Enhanced LLM Gateway with multi-provider support and streaming.
Supports: Ollama, OpenAI, Anthropic
"""

from datetime import datetime, UTC
from typing import Optional, Dict, Any, List, AsyncGenerator
import json
import re
import logging

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from config import settings, get_model_for_provider

logger = logging.getLogger("llm_gateway")


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    max_tokens: int = 1024
    temperature: float = 0.2
    system_prompt: Optional[str] = None


class GenerateResponse(BaseModel):
    text: str
    model: str
    backend: str


class StreamRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    max_tokens: int = 1024
    temperature: float = 0.2
    system_prompt: Optional[str] = None


class ExtractRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    schema: Dict[str, Any] = Field(..., description="JSON schema for expected output")
    max_tokens: int = 1024
    temperature: float = 0.1


class ExtractResponse(BaseModel):
    data: Optional[Dict[str, Any]]
    raw_text: str
    confidence: float
    validation_errors: List[str]
    model: str
    backend: str


class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    context: str = Field(..., description="Retrieved context with citations")
    max_tokens: int = 1024
    temperature: float = 0.3


class RAGQueryResponse(BaseModel):
    answer: str
    citations: List[str]
    confidence: float
    model: str
    backend: str


class ModelInfo(BaseModel):
    name: str
    provider: str
    capabilities: List[str]


app = FastAPI(title="LLM Gateway")


def _mock_generate(prompt: str) -> str:
    return "[MOCK] " + prompt[:400]


def _ollama_generate(
    prompt: str,
    max_tokens: int,
    temperature: float,
    system_prompt: Optional[str] = None,
) -> str:
    url = f"{settings.ollama_host}/api/generate"
    payload = {
        "model": settings.ollama_model,
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


async def _ollama_stream(
    prompt: str,
    max_tokens: int,
    temperature: float,
    system_prompt: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    url = f"{settings.ollama_host}/api/generate"
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    if system_prompt:
        payload["system"] = system_prompt

    try:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST", url, json=payload, timeout=120
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
    except Exception as exc:
        logger.error(f"Ollama streaming failed: {exc}")
        yield f"[ERROR: {exc}]"


def _openai_generate(
    prompt: str,
    max_tokens: int,
    temperature: float,
    system_prompt: Optional[str] = None,
) -> str:
    if not settings.openai_api_key:
        raise HTTPException(status_code=400, detail="OpenAI API key not configured")

    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": settings.openai_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        resp = httpx.post(
            f"{settings.openai_base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.error(f"OpenAI generation failed: {exc}")
        raise HTTPException(status_code=502, detail=f"OpenAI error: {exc}")


async def _openai_stream(
    prompt: str,
    max_tokens: int,
    temperature: float,
    system_prompt: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    if not settings.openai_api_key:
        raise HTTPException(status_code=400, detail="OpenAI API key not configured")

    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": settings.openai_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }

    try:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{settings.openai_base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=120,
            ) as response:
                async for line in response.aiter_lines():
                    if line and line.startswith("data: "):
                        data = line[6:]
                        if data != "[DONE]":
                            chunk = json.loads(data)
                            if "choices" in chunk:
                                delta = chunk["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
    except Exception as exc:
        logger.error(f"OpenAI streaming failed: {exc}")
        yield f"[ERROR: {exc}]"


def _anthropic_generate(
    prompt: str,
    max_tokens: int,
    temperature: float,
    system_prompt: Optional[str] = None,
) -> str:
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=400, detail="Anthropic API key not configured")

    headers = {
        "x-api-key": settings.anthropic_api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    messages = [{"role": "user", "content": prompt}]

    payload = {
        "model": settings.anthropic_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if system_prompt:
        payload["system"] = system_prompt

    try:
        resp = httpx.post(
            f"{settings.anthropic_base_url}/v1/messages",
            json=payload,
            headers=headers,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]
    except Exception as exc:
        logger.error(f"Anthropic generation failed: {exc}")
        raise HTTPException(status_code=502, detail=f"Anthropic error: {exc}")


async def _anthropic_stream(
    prompt: str,
    max_tokens: int,
    temperature: float,
    system_prompt: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=400, detail="Anthropic API key not configured")

    headers = {
        "x-api-key": settings.anthropic_api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    messages = [{"role": "user", "content": prompt}]

    payload = {
        "model": settings.anthropic_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    if system_prompt:
        payload["system"] = system_prompt

    try:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{settings.anthropic_base_url}/v1/messages",
                json=payload,
                headers=headers,
                timeout=120,
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        chunk = json.loads(line)
                        if chunk.get("type") == "content_block_delta":
                            delta = chunk.get("delta", {})
                            if delta.get("type") == "text_delta":
                                text = delta.get("text", "")
                                if text:
                                    yield text
    except Exception as exc:
        logger.error(f"Anthropic streaming failed: {exc}")
        yield f"[ERROR: {exc}]"


def _get_generator(provider: str):
    """Get the appropriate generator function for the provider."""
    generators = {
        "ollama": _ollama_generate,
        "openai": _openai_generate,
        "anthropic": _anthropic_generate,
    }
    return generators.get(provider, _ollama_generate)


def _get_streamer(provider: str):
    """Get the appropriate streamer function for the provider."""
    streamers = {
        "ollama": _ollama_stream,
        "openai": _openai_stream,
        "anthropic": _anthropic_stream,
    }
    return streamers.get(provider, _ollama_stream)


def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    code_block_pattern = r"```(?:json)?\s*([\s\S]*?)```"
    matches = re.findall(code_block_pattern, text)

    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue

    json_pattern = r"\{[\s\S]*\}"
    matches = re.findall(json_pattern, text)

    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue

    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    return None


def _validate_against_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    errors = []

    if schema.get("type") != "object":
        return ["Schema must be an object type"]

    properties = schema.get("properties", {})
    required = schema.get("required", [])

    for field in required:
        if field not in data:
            errors.append(f"Missing required field: {field}")
        elif data[field] is None:
            errors.append(f"Required field is null: {field}")

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

            if "enum" in prop_schema and value not in prop_schema["enum"]:
                errors.append(
                    f"Field '{field}' value '{value}' not in enum {prop_schema['enum']}"
                )

    return errors


def _calculate_confidence(
    data: Optional[Dict[str, Any]], schema: Dict[str, Any], validation_errors: List[str]
) -> float:
    if data is None:
        return 0.0

    if validation_errors:
        total_fields = len(schema.get("properties", {}))
        if total_fields == 0:
            return 0.5
        error_weight = len(validation_errors) / total_fields
        return max(0.0, 1.0 - error_weight * 0.5)

    required = schema.get("required", [])
    if required:
        filled_required = sum(1 for field in required if data.get(field) is not None)
        completeness = filled_required / len(required)
    else:
        completeness = 1.0

    confidence = 0.7 + (completeness * 0.3)
    return min(1.0, confidence)


def _extract_citations(text: str) -> List[str]:
    patterns = [
        r"\[([^\]]+:[^\]]+)\]",
        r"\[Document (\d+)\]",
        r"\[([^\]]+)\]",
    ]

    citations = set()
    for pattern in patterns:
        matches = re.findall(pattern, text)
        citations.update(matches)

    return list(citations)


@app.get("/healthz")
def healthz():
    model = get_model_for_provider(settings.llm_provider)
    return {
        "status": "ok",
        "time": datetime.now(UTC).isoformat(),
        "model": model,
        "backend": settings.llm_backend,
        "provider": settings.llm_provider,
    }


@app.get("/models")
def list_models():
    provider = settings.llm_provider
    model = get_model_for_provider(provider)

    if provider == "openai":
        return {
            "provider": "openai",
            "model": model,
            "capabilities": ["generate", "extract", "rag", "stream"],
        }
    elif provider == "anthropic":
        return {
            "provider": "anthropic",
            "model": model,
            "capabilities": ["generate", "extract", "rag", "stream"],
        }
    elif provider == "ollama":
        try:
            resp = httpx.get(f"{settings.ollama_host}/api/tags", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return {
                "provider": "ollama",
                "models": [m["name"] for m in data.get("models", [])],
                "current": settings.ollama_model,
                "capabilities": ["generate", "extract", "rag", "stream"],
            }
        except Exception:
            return {
                "provider": "ollama",
                "model": settings.ollama_model,
                "capabilities": ["generate", "extract", "rag", "stream"],
            }

    return {"error": "Unknown provider"}


@app.post("/generate", response_model=GenerateResponse)
def generate(payload: GenerateRequest):
    provider = settings.llm_provider

    if provider == "mock":
        text = _mock_generate(payload.prompt)
    elif provider == "ollama":
        text = _ollama_generate(
            payload.prompt,
            payload.max_tokens,
            payload.temperature,
            payload.system_prompt,
        )
    elif provider == "openai":
        text = _openai_generate(
            payload.prompt,
            payload.max_tokens,
            payload.temperature,
            payload.system_prompt,
        )
    elif provider == "anthropic":
        text = _anthropic_generate(
            payload.prompt,
            payload.max_tokens,
            payload.temperature,
            payload.system_prompt,
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    model = get_model_for_provider(provider)
    return GenerateResponse(text=text, model=model, backend=provider)


@app.post("/generate/stream")
async def generate_stream(payload: StreamRequest):
    """
    Streaming text generation endpoint.
    Returns Server-Sent Events (SSE) with generated text chunks.
    """
    provider = settings.llm_provider

    async def stream_generator():
        if provider == "mock":
            yield f"data: {json.dumps({'chunk': payload.prompt[:50]})}\n\n"
            yield "data: [DONE]\n\n"
        else:
            streamer = _get_streamer(provider)
            async for chunk in streamer(
                payload.prompt,
                payload.max_tokens,
                payload.temperature,
                payload.system_prompt,
            ):
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


@app.post("/extract", response_model=ExtractResponse)
def extract(payload: ExtractRequest):
    system_prompt = """You are a precise data extraction AI. Your task is to extract structured information and return it as valid JSON.
Rules:
1. Return ONLY valid JSON, no markdown formatting, no explanations
2. Follow the schema exactly
3. Use null for missing optional fields
4. Do not include any text outside the JSON object
5. Ensure proper JSON syntax with double quotes"""

    enhanced_prompt = f"""{payload.prompt}

You must return a JSON object matching this schema:
{json.dumps(payload.schema, indent=2)}

Remember: Return ONLY the JSON object, nothing else."""

    provider = settings.llm_provider

    if provider == "mock":
        raw_text = '{"extracted": "mock data"}'
    elif provider == "ollama":
        raw_text = _ollama_generate(
            enhanced_prompt,
            payload.max_tokens,
            payload.temperature,
            system_prompt=system_prompt,
        )
    elif provider == "openai":
        raw_text = _openai_generate(
            enhanced_prompt,
            payload.max_tokens,
            payload.temperature,
            system_prompt=system_prompt,
        )
    elif provider == "anthropic":
        raw_text = _anthropic_generate(
            enhanced_prompt,
            payload.max_tokens,
            payload.temperature,
            system_prompt=system_prompt,
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    data = _extract_json_from_text(raw_text)

    validation_errors = []
    if data is not None:
        validation_errors = _validate_against_schema(data, payload.schema)
    else:
        validation_errors = ["Failed to parse JSON from response"]

    confidence = _calculate_confidence(data, payload.schema, validation_errors)

    model = get_model_for_provider(provider)
    return ExtractResponse(
        data=data,
        raw_text=raw_text,
        confidence=confidence,
        validation_errors=validation_errors,
        model=model,
        backend=provider,
    )


@app.post("/rag", response_model=RAGQueryResponse)
def rag_query(payload: RAGQueryRequest):
    system_prompt = """You are a helpful RAG assistant. Answer the user's question using ONLY the provided context.
Rules:
1. Use only information from the provided context
2. Cite sources using [doc_id] format
3. Be concise and accurate
4. If the answer isn't in the context, say so clearly"""

    prompt = f"""Context:
{payload.context}

Question: {payload.query}

Provide a clear, accurate answer based on the context above. Cite sources using [doc_id] format."""

    provider = settings.llm_provider

    if provider == "mock":
        answer = f"[MOCK] Based on the provided context, here's the answer to: {payload.query[:50]}..."
        citations = ["doc001", "doc002"]
        confidence = 0.85
    elif provider == "ollama":
        answer = _ollama_generate(
            prompt,
            payload.max_tokens,
            payload.temperature,
            system_prompt=system_prompt,
        )
        citations = _extract_citations(answer)
        confidence = 0.75 if citations else 0.5
    elif provider == "openai":
        answer = _openai_generate(
            prompt,
            payload.max_tokens,
            payload.temperature,
            system_prompt=system_prompt,
        )
        citations = _extract_citations(answer)
        confidence = 0.8 if citations else 0.5
    elif provider == "anthropic":
        answer = _anthropic_generate(
            prompt,
            payload.max_tokens,
            payload.temperature,
            system_prompt=system_prompt,
        )
        citations = _extract_citations(answer)
        confidence = 0.85 if citations else 0.5
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    model = get_model_for_provider(provider)
    return RAGQueryResponse(
        answer=answer,
        citations=citations,
        confidence=confidence,
        model=model,
        backend=provider,
    )


@app.post("/rag/stream")
async def rag_stream(payload: RAGQueryRequest):
    """
    Streaming RAG query endpoint.
    Returns Server-Sent Events (SSE) with generated answer chunks.
    """
    system_prompt = """You are a helpful RAG assistant. Answer the user's question using ONLY the provided context.
Rules:
1. Use only information from the provided context
2. Cite sources using [doc_id] format
3. Be concise and accurate
4. If the answer isn't in the context, say so clearly"""

    prompt = f"""Context:
{payload.context}

Question: {payload.query}

Provide a clear, accurate answer based on the context above. Cite sources using [doc_id] format."""

    provider = settings.llm_provider

    async def rag_stream_generator():
        if provider == "mock":
            yield f"data: {json.dumps({'chunk': 'Based on the context...'})}\n\n"
            yield "data: [DONE]\n\n"
        else:
            streamer = _get_streamer(provider)
            async for chunk in streamer(
                prompt,
                payload.max_tokens,
                payload.temperature,
                system_prompt=system_prompt,
            ):
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(rag_stream_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.service_port)
