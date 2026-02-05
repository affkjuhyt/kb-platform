"""
Prometheus Metrics Module for RAG System

This module provides Prometheus metrics collection for all services.
Usage:
    from metrics import metrics, track_request_duration, increment_request_count

    @track_request_duration
    def my_endpoint():
        increment_request_count(method="GET", endpoint="/search")
        return result
"""

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    CollectorRegistry,
    multiprocess,
    generate_latest,
)
from prometheus_client.openmetrics.exposition import CONTENT_TYPE_LATEST
from functools import wraps
import time
from typing import Optional, Callable

# Create a registry
REGISTRY = CollectorRegistry()

# Service info
SERVICE_INFO = Info("rag_service", "RAG service information", registry=REGISTRY)

# Request metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code", "tenant_id"],
    registry=REGISTRY,
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint", "tenant_id"],
    buckets=[
        0.005,
        0.01,
        0.025,
        0.05,
        0.075,
        0.1,
        0.25,
        0.5,
        0.75,
        1.0,
        2.0,
        2.5,
        5.0,
        7.5,
        10.0,
    ],
    registry=REGISTRY,
)

REQUEST_SIZE = Histogram(
    "http_request_size_bytes",
    "HTTP request size in bytes",
    ["method", "endpoint"],
    buckets=[100, 1000, 10000, 100000, 1000000],
    registry=REGISTRY,
)

RESPONSE_SIZE = Histogram(
    "http_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "endpoint"],
    buckets=[100, 1000, 10000, 100000, 1000000],
    registry=REGISTRY,
)

# Business metrics
SEARCH_LATENCY = Histogram(
    "search_latency_seconds",
    "Search operation latency",
    ["tenant_id", "search_type"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0],
    registry=REGISTRY,
)

RAG_LATENCY = Histogram(
    "rag_query_latency_seconds",
    "RAG query latency",
    ["tenant_id"],
    buckets=[0.1, 0.5, 1.0, 2.0, 2.1, 2.5, 3.0, 5.0, 10.0],
    registry=REGISTRY,
)

EXTRACTION_LATENCY = Histogram(
    "extraction_latency_seconds",
    "Data extraction latency",
    ["tenant_id", "extraction_type"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    registry=REGISTRY,
)

# Cache metrics
CACHE_HITS = Counter(
    "cache_hits_total",
    "Total cache hits",
    ["cache_type", "tenant_id"],
    registry=REGISTRY,
)

CACHE_MISSES = Counter(
    "cache_misses_total",
    "Total cache misses",
    ["cache_type", "tenant_id"],
    registry=REGISTRY,
)

CACHE_SIZE = Gauge(
    "cache_size_bytes", "Current cache size in bytes", ["cache_type"], registry=REGISTRY
)

# LLM metrics
LLM_REQUESTS = Counter(
    "llm_requests_total",
    "Total LLM requests",
    ["model", "backend", "tenant_id"],
    registry=REGISTRY,
)

LLM_LATENCY = Histogram(
    "llm_latency_seconds",
    "LLM request latency",
    ["model", "backend"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    registry=REGISTRY,
)

LLM_TOKENS = Counter(
    "llm_tokens_total",
    "Total LLM tokens processed",
    ["model", "token_type"],
    registry=REGISTRY,
)

# Vector DB metrics
VECTOR_DB_LATENCY = Histogram(
    "vector_db_latency_seconds",
    "Vector database operation latency",
    ["operation", "collection"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=REGISTRY,
)

# Database metrics
DB_CONNECTIONS = Gauge(
    "db_connections_active",
    "Active database connections",
    ["database"],
    registry=REGISTRY,
)

DB_QUERY_LATENCY = Histogram(
    "db_query_latency_seconds",
    "Database query latency",
    ["operation", "table"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=REGISTRY,
)

# Queue metrics
QUEUE_SIZE = Gauge(
    "queue_size", "Current queue size", ["queue_name"], registry=REGISTRY
)

QUEUE_LATENCY = Histogram(
    "queue_latency_seconds",
    "Queue processing latency",
    ["queue_name"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
    registry=REGISTRY,
)

# Rate limiting metrics
RATE_LIMIT_HITS = Counter(
    "rate_limit_hits_total",
    "Total rate limit hits",
    ["tenant_id", "user_id"],
    registry=REGISTRY,
)

# Error metrics
ERRORS_TOTAL = Counter(
    "errors_total", "Total errors", ["error_type", "endpoint"], registry=REGISTRY
)


class MetricsCollector:
    """Helper class for collecting metrics."""

    @staticmethod
    def track_request_duration(method: str, endpoint: str, tenant_id: str = "default"):
        """Decorator to track request duration."""

        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    status_code = 200
                    return result
                except Exception as e:
                    status_code = 500
                    ERRORS_TOTAL.labels(
                        error_type=type(e).__name__, endpoint=endpoint
                    ).inc()
                    raise
                finally:
                    duration = time.time() - start_time
                    REQUEST_DURATION.labels(
                        method=method, endpoint=endpoint, tenant_id=tenant_id
                    ).observe(duration)
                    REQUEST_COUNT.labels(
                        method=method,
                        endpoint=endpoint,
                        status_code=str(status_code),
                        tenant_id=tenant_id,
                    ).inc()

            return wrapper

        return decorator

    @staticmethod
    def time_search(tenant_id: str = "default", search_type: str = "hybrid"):
        """Context manager for timing search operations."""
        return SEARCH_LATENCY.labels(
            tenant_id=tenant_id, search_type=search_type
        ).time()

    @staticmethod
    def time_rag(tenant_id: str = "default"):
        """Context manager for timing RAG queries."""
        return RAG_LATENCY.labels(tenant_id=tenant_id).time()

    @staticmethod
    def time_extraction(tenant_id: str = "default", extraction_type: str = "sync"):
        """Context manager for timing extraction."""
        return EXTRACTION_LATENCY.labels(
            tenant_id=tenant_id, extraction_type=extraction_type
        ).time()

    @staticmethod
    def time_llm(model: str = "default", backend: str = "default"):
        """Context manager for timing LLM requests."""
        return LLM_LATENCY.labels(model=model, backend=backend).time()

    @staticmethod
    def record_cache_hit(cache_type: str = "redis", tenant_id: str = "default"):
        """Record cache hit."""
        CACHE_HITS.labels(cache_type=cache_type, tenant_id=tenant_id).inc()

    @staticmethod
    def record_cache_miss(cache_type: str = "redis", tenant_id: str = "default"):
        """Record cache miss."""
        CACHE_MISSES.labels(cache_type=cache_type, tenant_id=tenant_id).inc()

    @staticmethod
    def record_rate_limit_hit(tenant_id: str, user_id: str):
        """Record rate limit hit."""
        RATE_LIMIT_HITS.labels(tenant_id=tenant_id, user_id=user_id).inc()

    @staticmethod
    def increment_llm_tokens(model: str, prompt_tokens: int, completion_tokens: int):
        """Record LLM token usage."""
        LLM_TOKENS.labels(model=model, token_type="prompt").inc(prompt_tokens)
        LLM_TOKENS.labels(model=model, token_type="completion").inc(completion_tokens)

    @staticmethod
    def set_service_info(service_name: str, version: str):
        """Set service information."""
        SERVICE_INFO.info({"service": service_name, "version": version})


# Global instance
metrics = MetricsCollector()


def track_request_duration(method: str, endpoint: str, tenant_id: str = "default"):
    """Decorator factory to track request duration."""
    return metrics.track_request_duration(method, endpoint, tenant_id)


def increment_request_count(
    method: str, endpoint: str, status_code: int, tenant_id: str = "default"
):
    """Increment request counter."""
    REQUEST_COUNT.labels(
        method=method,
        endpoint=endpoint,
        status_code=str(status_code),
        tenant_id=tenant_id,
    ).inc()


def get_metrics():
    """Get Prometheus metrics in text format."""
    return generate_latest(REGISTRY)


# FastAPI middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class PrometheusMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for automatic Prometheus metrics collection."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Get tenant ID from header or use default
        tenant_id = request.headers.get("X-Tenant-ID", "default")
        method = request.method
        path = request.url.path

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            ERRORS_TOTAL.labels(error_type=type(e).__name__, endpoint=path).inc()
            raise
        finally:
            duration = time.time() - start_time
            REQUEST_DURATION.labels(
                method=method, endpoint=path, tenant_id=tenant_id
            ).observe(duration)
            REQUEST_COUNT.labels(
                method=method,
                endpoint=path,
                status_code=str(status_code),
                tenant_id=tenant_id,
            ).inc()

        return response
