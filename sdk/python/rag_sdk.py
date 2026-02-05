"""
RAG System Python SDK

A Python SDK for interacting with the RAG System API Gateway.

Features:
- Authentication (JWT and API Key)
- Search operations
- RAG queries
- Data extraction
- Automatic token refresh
- Rate limit handling

Installation:
    pip install rag-sdk

Usage:
    from rag_sdk import RAGClient

    client = RAGClient(
        base_url="https://api.ragsystem.com",
        tenant_id="your-tenant-id"
    )

    # Login
    client.login("user@example.com", "password")

    # Search
    results = client.search("machine learning", top_k=5)

    # RAG Query
    answer = client.rag_query("What is deep learning?")

    # Extract data
    data = client.extract("Extract company info", schema={...})
"""

import requests
import time
import json
import logging
import os

try:
    import yaml  # type: ignore
except Exception:
    yaml = None
import logging.config
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

# Optional JSON Schema validation
try:
    import jsonschema  # type: ignore
except Exception:  # pragma: no cover
    jsonschema = None


def _setup_logging():
    # Try to load YAML config if available, otherwise fall back to basicConfig
    if yaml is not None:
        cfg_path = os.path.join(os.path.dirname(__file__), "logging.yaml")
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r") as f:
                    cfg = yaml.safe_load(f)
                    logging.config.dictConfig(cfg)
                    return
            except Exception:
                pass
    logging.basicConfig(level=logging.INFO)


_setup_logging()
logger = logging.getLogger(__name__)


@dataclass
class TokenInfo:
    """Token information."""

    access_token: str
    token_type: str
    expires_in: int
    tenant_id: str
    obtained_at: datetime

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        expiry = self.obtained_at + timedelta(seconds=self.expires_in - 60)
        return datetime.utcnow() >= expiry


@dataclass
class SearchResult:
    """Search result item."""

    doc_id: str
    source: str
    source_id: str
    version: int
    chunk_index: int
    score: float
    text: str
    section_path: str
    heading_path: List[str]


@dataclass
class RAGResponse:
    """RAG query response."""

    query: str
    answer: str
    citations: List[Dict[str, Any]]
    confidence: float
    model: Optional[str] = None


@dataclass
class ExtractionResponse:
    """Extraction response."""

    success: bool
    data: Optional[Dict[str, Any]]
    confidence: float
    validation_errors: List[str]
    job_id: Optional[str] = None


class RAGError(Exception):
    """Base RAG SDK error."""

    pass


class AuthenticationError(RAGError):
    """Authentication error."""

    pass


class RateLimitError(RAGError):
    """Rate limit exceeded error."""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class APIError(RAGError):
    """API error."""

    def __init__(self, message: str, status_code: int, response: Optional[dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class RAGClient:
    """
    RAG System API Client.

    Args:
        base_url: API Gateway base URL
        tenant_id: Tenant identifier
        api_key: Optional API key for authentication

    Example:
        >>> client = RAGClient(
        ...     base_url="https://api.ragsystem.com",
        ...     tenant_id="tenant-123"
        ... )
        >>> client.login("user@example.com", "password")
        >>> results = client.search("machine learning")
    """

    def __init__(
        self,
        base_url: str,
        tenant_id: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
    ):
        self.base_url = base_url.rstrip("/")
        self.tenant_id = tenant_id
        self.api_key = api_key
        self.timeout = timeout
        self._token_info: Optional[TokenInfo] = None
        self._session = requests.Session()
        # Token refresh support: store credentials for auto-refresh
        self._credentials: Optional[tuple[str, str]] = None
        self._remember_credentials: bool = False
        # Retry/backoff configuration
        self._max_retries: int = 3
        self._backoff_factor: float = 0.5
        # Simple in-process metrics (per-call granularity)
        self._last_retry_count: int = 0
        # Basic metrics for logging/observability
        self._metrics = {
            "request_count": 0,
            "error_count": 0,
            "latency_ms_total": 0.0,
        }

        # Set default headers
        self._session.headers.update(
            {"Content-Type": "application/json", "Accept": "application/json"}
        )

        if api_key:
            self._session.headers["X-API-Key"] = api_key

    def _get_auth_header(self) -> Dict[str, str]:
        """Get authentication header."""
        if self.api_key:
            return {"X-API-Key": self.api_key}

        if self._token_info and not self._token_info.is_expired:
            return {"Authorization": f"Bearer {self._token_info.access_token}"}
        # Token expired or absent: attempt to refresh if credentials stored
        if self._credentials:
            self._refresh_token()
            if self._token_info and not self._token_info.is_expired:
                return {"Authorization": f"Bearer {self._token_info.access_token}"}

        raise AuthenticationError("Not authenticated. Call login() first.")

    def _refresh_token(self) -> None:
        """Refresh token using stored credentials if available."""
        if not self._credentials:
            raise AuthenticationError("Not authenticated. Call login() first.")
        email, password = self._credentials
        # Re-authenticate to obtain a new token
        token = self.login(email, password, remember_credentials=True)
        self._token_info = token

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        auth: bool = True,
    ) -> Dict[str, Any]:
        """Make HTTP request with retries and backoff."""
        url = f"{self.base_url}{endpoint}"

        start_ts = time.time()
        self._metrics["request_count"] += 1

        headers = {}
        if auth:
            headers.update(self._get_auth_header())

        attempt = 0
        self._last_retry_count = 0
        # Retry metrics
        self._retry_stats = getattr(
            self, "_retry_stats", {"transient_retries": 0, "total_backoff": 0.0}
        )
        while True:
            try:
                response = self._session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                )
            except requests.exceptions.RequestException as e:
                duration_ms = int((time.time() - start_ts) * 1000)
                self._metrics["error_count"] += 1
                logger.error(
                    "Request failed",
                    extra={
                        "endpoint": endpoint,
                        "method": method,
                        "tenant_id": self.tenant_id,
                        "status": 0,
                        "duration_ms": duration_ms,
                        "error": str(e),
                    },
                )
                raise APIError(f"Request failed: {str(e)}", status_code=0)

            # Retry on transient errors
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                self._last_retry_count = attempt
                # update metrics
                self._retry_stats["transient_retries"] = (
                    self._retry_stats.get("transient_retries", 0) + 1
                )
                self._retry_stats["total_backoff"] = self._retry_stats.get(
                    "total_backoff", 0.0
                ) + float(retry_after)
                if attempt < self._max_retries:
                    logger.warning(
                        "Retrying due to 429 on %s %s (attempt %d, after %ss)",
                        method,
                        endpoint,
                        attempt,
                        retry_after,
                    )
                    time.sleep(max(1, retry_after))
                    self._retry_stats["total_backoff"] = self._retry_stats.get(
                        "total_backoff", 0.0
                    ) + float(retry_after)
                    attempt += 1
                    continue
                raise RateLimitError("Rate limit exceeded", retry_after=retry_after)
            if 500 <= response.status_code < 600:
                self._last_retry_count = attempt
                if attempt < self._max_retries:
                    backoff = max(0.5, self._backoff_factor * (2**attempt))  # seconds
                    self._retry_stats["transient_retries"] = (
                        self._retry_stats.get("transient_retries", 0) + 1
                    )
                    self._retry_stats["total_backoff"] = (
                        self._retry_stats.get("total_backoff", 0.0) + backoff
                    )
                    logger.warning(
                        "Retrying due to server error on %s %s (status %d, attempt %d, backoff %ss)",
                        method,
                        endpoint,
                        response.status_code,
                        attempt,
                        backoff,
                    )
                    time.sleep(backoff)
                    attempt += 1
                    continue
                # fallthrough to error return if max retries exceeded

            # Handle other errors
            if not response.ok:
                error_data = response.json() if response.content else {}
                raise APIError(
                    error_data.get("detail", f"HTTP {response.status_code}"),
                    status_code=response.status_code,
                    response=error_data,
                )

            if response.content:
                duration_ms = int((time.time() - start_ts) * 1000)
                self._metrics["latency_ms_total"] += duration_ms
                logger.info(
                    "HTTP request completed",
                    extra={
                        "endpoint": endpoint,
                        "method": method,
                        "tenant_id": self.tenant_id,
                        "status": response.status_code,
                        "duration_ms": duration_ms,
                        "error": None,
                    },
                )
                return response.json()
            duration_ms = int((time.time() - start_ts) * 1000)
            self._metrics["latency_ms_total"] += duration_ms
            logger.info(
                "HTTP request completed (no content)",
                extra={
                    "endpoint": endpoint,
                    "method": method,
                    "tenant_id": self.tenant_id,
                    "status": 0,
                    "duration_ms": duration_ms,
                    "error": None,
                },
            )
            return {}

    def login(
        self, email: str, password: str, remember_credentials: bool = False
    ) -> TokenInfo:
        """
        Authenticate with email and password.

        Args:
            email: User email
            password: User password

        Returns:
            TokenInfo object with access token

        Raises:
            AuthenticationError: If credentials are invalid
        """
        try:
            response = self._request(
                "POST",
                "/auth/login",
                data={
                    "email": email,
                    "password": password,
                    "tenant_id": self.tenant_id,
                },
                auth=False,
            )

            self._token_info = TokenInfo(
                access_token=response["access_token"],
                token_type=response["token_type"],
                expires_in=response["expires_in"],
                tenant_id=response["tenant_id"],
                obtained_at=datetime.utcnow(),
            )

            if remember_credentials:
                self._credentials = (email, password)  # store for refresh
            return self._token_info

        except APIError as e:
            if e.status_code == 401:
                raise AuthenticationError("Invalid credentials")
            raise

    def _validate_against_schema(self, instance: Any, schema: Dict[str, Any]) -> None:
        """Validate a Python object against a JSON Schema (best effort).
        Uses jsonschema if available; otherwise performs a lightweight check.
        """
        if not schema or instance is None:
            return
        if jsonschema:
            jsonschema.validate(instance=instance, schema=schema)
            return
        # Lightweight fallback: minimal object/type checks
        try:
            t = schema.get("type")
            if t == "object" and isinstance(instance, dict):
                required = schema.get("required", [])
                for key in required:
                    if key not in instance:
                        raise ValueError(f"Missing required key: {key}")
        except Exception as e:
            raise APIError(
                f"Schema validation failed: {str(e)}",
                status_code=0,
                response={"validation_error": str(e)},
            )

    def register(self, email: str, password: str, name: str) -> TokenInfo:
        """
        Register a new user.

        Args:
            email: User email
            password: User password (min 8 characters)
            name: User full name

        Returns:
            TokenInfo object with access token
        """
        response = self._request(
            "POST",
            "/auth/register",
            data={
                "email": email,
                "password": password,
                "tenant_id": self.tenant_id,
                "name": name,
            },
            auth=False,
        )

        self._token_info = TokenInfo(
            access_token=response["access_token"],
            token_type=response["token_type"],
            expires_in=response["expires_in"],
            tenant_id=response["tenant_id"],
            obtained_at=datetime.utcnow(),
        )

        return self._token_info

    def search(
        self, query: str, top_k: int = 10, filters: Optional[Dict] = None
    ) -> List[SearchResult]:
        """
        Search documents.

        Args:
            query: Search query
            top_k: Number of results to return
            filters: Optional filters (e.g., {"source": "manual"})

        Returns:
            List of SearchResult objects
        """
        data = {"query": query, "tenant_id": self.tenant_id, "top_k": top_k}

        if filters:
            data["filters"] = filters

        response = self._request("POST", "/query/search", data=data)

        return [
            SearchResult(
                doc_id=r["doc_id"],
                source=r["source"],
                source_id=r["source_id"],
                version=r["version"],
                chunk_index=r["chunk_index"],
                score=r["score"],
                text=r["text"],
                section_path=r["section_path"],
                heading_path=r["heading_path"],
            )
            for r in response.get("results", [])
        ]

    def rag_query(
        self, query: str, top_k: int = 5, session_id: Optional[str] = None
    ) -> RAGResponse:
        """
        Perform RAG query.

        Args:
            query: User question
            top_k: Number of context documents
            session_id: Optional session ID for conversation tracking

        Returns:
            RAGResponse with answer and citations
        """
        data = {"query": query, "tenant_id": self.tenant_id, "top_k": top_k}

        if session_id:
            data["session_id"] = session_id

        response = self._request("POST", "/query/rag", data=data)

        return RAGResponse(
            query=response["query"],
            answer=response["answer"],
            citations=response.get("citations", []),
            confidence=response["confidence"],
            model=response.get("model"),
        )

    def extract(
        self,
        query: str,
        schema: Dict[str, Any],
        top_k: int = 5,
        min_confidence: float = 0.7,
    ) -> ExtractionResponse:
        """
        Extract structured data.

        Args:
            query: Extraction query/description
            schema: JSON schema defining expected output
            top_k: Number of documents to search
            min_confidence: Minimum confidence threshold

        Returns:
            ExtractionResponse with extracted data
        """
        response = self._request(
            "POST",
            "/query/extract",
            data={
                "query": query,
                "tenant_id": self.tenant_id,
                "schema": schema,
                "top_k": top_k,
                "min_confidence": min_confidence,
            },
        )
        # Validate server payload against provided schema, if available
        try:
            self._validate_against_schema(response.get("data"), schema)
        except Exception:
            # Silently propagate as APIError already handled in validator
            pass

        return ExtractionResponse(
            success=response["success"],
            data=response.get("data"),
            confidence=response["confidence"],
            validation_errors=response.get("validation_errors", []),
        )

    def extract_with_job(
        self,
        query: str,
        schema: Dict[str, Any],
        schema_name: str = "custom",
        top_k: int = 5,
        min_confidence: float = 0.7,
        poll_interval: int = 2,
        max_wait: int = 60,
    ) -> ExtractionResponse:
        """
        Extract structured data with job tracking (async).

        Args:
            query: Extraction query/description
            schema: JSON schema defining expected output
            schema_name: Name for the schema
            top_k: Number of documents to search
            min_confidence: Minimum confidence threshold
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait

        Returns:
            ExtractionResponse with extracted data
        """
        # Create job
        create_response = self._request(
            "POST",
            "/query/extract/jobs",
            data={
                "query": query,
                "tenant_id": self.tenant_id,
                "schema": schema,
                "schema_name": schema_name,
                "top_k": top_k,
                "min_confidence": min_confidence,
            },
        )

        job_id = create_response["job_id"]

        # Poll for completion
        start_time = time.time()
        while time.time() - start_time < max_wait:
            status_response = self._request("GET", f"/query/extract/jobs/{job_id}")

            status = status_response.get("job", {}).get("status")

            if status == "completed":
                results = status_response.get("results", [])
                if results:
                    result = results[0]
                    # Validate extracted data against provided schema when available
                    try:
                        self._validate_against_schema(result.get("data"), schema)
                    except Exception:
                        pass
                    return ExtractionResponse(
                        success=True,
                        data=result.get("data"),
                        confidence=result["confidence"],
                        validation_errors=result.get("validation_errors", []),
                        job_id=job_id,
                    )
                else:
                    return ExtractionResponse(
                        success=False,
                        data=None,
                        confidence=0.0,
                        validation_errors=["No results"],
                        job_id=job_id,
                    )
            elif status == "failed":
                return ExtractionResponse(
                    success=False,
                    data=None,
                    confidence=0.0,
                    validation_errors=["Job failed"],
                    job_id=job_id,
                )

            time.sleep(poll_interval)

        # Timeout
        return ExtractionResponse(
            success=False,
            data=None,
            confidence=0.0,
            validation_errors=["Timeout waiting for job completion"],
            job_id=job_id,
        )

    def health_check(self) -> Dict[str, Any]:
        """
        Check API health.

        Returns:
            Health status information
        """
        return self._request("GET", "/health", auth=False)

    def close(self):
        """Close client session."""
        self._session.close()

    def get_retry_stats(self) -> Dict[str, Any]:
        """Return retry-related metrics collected during requests."""
        return getattr(
            self, "_retry_stats", {"transient_retries": 0, "total_backoff": 0.0}
        )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# ============================================================================
# Convenience Functions
# ============================================================================


def search(
    base_url: str, tenant_id: str, api_key: str, query: str, top_k: int = 10
) -> List[SearchResult]:
    """
    Quick search function using API key.

    Example:
        >>> results = search(
        ...     "https://api.ragsystem.com",
        ...     "tenant-123",
        ...     "your-api-key",
        ...     "machine learning"
        ... )
    """
    with RAGClient(base_url, tenant_id, api_key) as client:
        return client.search(query, top_k)


def rag_query(base_url: str, tenant_id: str, api_key: str, query: str) -> RAGResponse:
    """
    Quick RAG query function using API key.

    Example:
        >>> answer = rag_query(
        ...     "https://api.ragsystem.com",
        ...     "tenant-123",
        ...     "your-api-key",
        ...     "What is AI?"
        ... )
    """
    with RAGClient(base_url, tenant_id, api_key) as client:
        return client.rag_query(query)


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # Example usage
    print("RAG SDK Example")
    print("=" * 60)

    # Initialize client
    client = RAGClient(base_url="http://localhost:8000", tenant_id="demo-tenant")

    # Login
    try:
        token = client.login("user@example.com", "password")
        print(f"✓ Logged in successfully")
        print(f"  Token expires in: {token.expires_in} seconds")
    except AuthenticationError as e:
        print(f"✗ Login failed: {e}")
        exit(1)

    # Health check
    health = client.health_check()
    print(f"\n✓ API Health: {health['status']}")

    # Search example
    print("\nExample: Search")
    try:
        results = client.search("machine learning", top_k=3)
        print(f"✓ Found {len(results)} results")
        for i, result in enumerate(results[:2], 1):
            print(f"  {i}. {result.doc_id} (score: {result.score:.2f})")
    except Exception as e:
        print(f"  Search example skipped: {e}")

    # RAG query example
    print("\nExample: RAG Query")
    try:
        response = client.rag_query("What is deep learning?")
        print(f"✓ Answer: {response.answer[:100]}...")
        print(f"  Confidence: {response.confidence:.2f}")
        print(f"  Citations: {len(response.citations)}")
    except Exception as e:
        print(f"  RAG example skipped: {e}")

    # Close client
    client.close()
    print("\n✓ Client closed")
