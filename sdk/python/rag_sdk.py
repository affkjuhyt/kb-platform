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
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta


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

        raise AuthenticationError("Not authenticated. Call login() first.")

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        auth: bool = True,
    ) -> Dict[str, Any]:
        """Make HTTP request."""
        url = f"{self.base_url}{endpoint}"

        headers = {}
        if auth:
            headers.update(self._get_auth_header())

        try:
            response = self._session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                raise RateLimitError("Rate limit exceeded", retry_after=retry_after)

            # Handle other errors
            if not response.ok:
                error_data = response.json() if response.content else {}
                raise APIError(
                    error_data.get("detail", f"HTTP {response.status_code}"),
                    status_code=response.status_code,
                    response=error_data,
                )

            return response.json() if response.content else {}

        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {str(e)}", status_code=0)

    def login(self, email: str, password: str) -> TokenInfo:
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

            return self._token_info

        except APIError as e:
            if e.status_code == 401:
                raise AuthenticationError("Invalid credentials")
            raise

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

            status = status_response["job"]["status"]

            if status == "completed":
                results = status_response.get("results", [])
                if results:
                    result = results[0]
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
