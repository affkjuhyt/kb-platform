"""
OpenTelemetry Tracing Module for RAG System

This module provides distributed tracing using OpenTelemetry.
Usage:
    from tracing import tracer, trace_span

    @trace_span("search_operation")
    def search(query):
        with tracer.start_as_current_span("vector_search") as span:
            span.set_attribute("query", query)
            span.set_attribute("tenant_id", tenant_id)
            return vector_search(query)
"""

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import (
    Resource,
    SERVICE_NAME,
    SERVICE_VERSION,
    DEPLOYMENT_ENVIRONMENT,
)
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.trace import Status, StatusCode
from functools import wraps
import os
from typing import Optional, Callable, Any

# Configuration
JAEGER_HOST = os.getenv("JAEGER_HOST", "localhost")
JAEGER_PORT = int(os.getenv("JAEGER_PORT", "6831"))
OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv(
    "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
)
OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "rag-system")
OTEL_ENVIRONMENT = os.getenv("OTEL_ENVIRONMENT", "development")


class TracingConfig:
    """OpenTelemetry tracing configuration."""

    def __init__(
        self, service_name: str = OTEL_SERVICE_NAME, environment: str = OTEL_ENVIRONMENT
    ):
        self.service_name = service_name
        self.environment = environment
        self.provider: Optional[TracerProvider] = None
        self.tracer: Optional[trace.Tracer] = None

    def initialize(self):
        """Initialize OpenTelemetry tracing."""
        # Create resource
        resource = Resource.create(
            {
                SERVICE_NAME: self.service_name,
                SERVICE_VERSION: "1.0.0",
                DEPLOYMENT_ENVIRONMENT: self.environment,
            }
        )

        # Create provider
        self.provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(self.provider)

        # Configure exporters
        self._configure_exporters()

        # Get tracer
        self.tracer = trace.get_tracer(self.service_name)

        # Instrument libraries
        self._instrument_libraries()

        return self

    def _configure_exporters(self):
        """Configure span exporters."""
        # Jaeger exporter
        try:
            jaeger_exporter = JaegerExporter(
                agent_host_name=JAEGER_HOST,
                agent_port=JAEGER_PORT,
            )
            self.provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
            print(f"✓ Jaeger exporter configured ({JAEGER_HOST}:{JAEGER_PORT})")
        except Exception as e:
            print(f"⚠ Jaeger exporter failed: {e}")

        # OTLP exporter (for collectors like Grafana Agent)
        try:
            otlp_exporter = OTLPSpanExporter(
                endpoint=OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True
            )
            self.provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            print(f"✓ OTLP exporter configured ({OTEL_EXPORTER_OTLP_ENDPOINT})")
        except Exception as e:
            print(f"⚠ OTLP exporter failed: {e}")

        # Console exporter for debugging
        if os.getenv("OTEL_DEBUG", "false").lower() == "true":
            console_exporter = ConsoleSpanExporter()
            self.provider.add_span_processor(BatchSpanProcessor(console_exporter))
            print("✓ Console exporter configured")

    def _instrument_libraries(self):
        """Auto-instrument libraries."""
        # Redis
        try:
            RedisInstrumentor().instrument()
            print("✓ Redis instrumented")
        except Exception as e:
            print(f"⚠ Redis instrumentation failed: {e}")

        # HTTPX
        try:
            HTTPXClientInstrumentor().instrument()
            print("✓ HTTPX instrumented")
        except Exception as e:
            print(f"⚠ HTTPX instrumentation failed: {e}")


def instrument_fastapi(app):
    """Instrument FastAPI application."""
    FastAPIInstrumentor.instrument_app(app)
    print("✓ FastAPI instrumented")


def instrument_sqlalchemy(engine):
    """Instrument SQLAlchemy engine."""
    try:
        SQLAlchemyInstrumentor().instrument(
            engine=engine, enable_commenter=True, commenter_options={}
        )
        print("✓ SQLAlchemy instrumented")
    except Exception as e:
        print(f"⚠ SQLAlchemy instrumentation failed: {e}")


# Decorator for tracing functions
class trace_span:
    """Decorator to add tracing to functions."""

    def __init__(self, span_name: str = None, attributes: dict = None):
        self.span_name = span_name
        self.attributes = attributes or {}

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(OTEL_SERVICE_NAME)
            span_name = self.span_name or func.__name__

            with tracer.start_as_current_span(span_name) as span:
                # Set attributes
                for key, value in self.attributes.items():
                    span.set_attribute(key, value)

                # Set function name
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)

                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        return wrapper


# Helper functions for manual tracing
def start_span(name: str, attributes: dict = None):
    """Start a new span."""
    tracer = trace.get_tracer(OTEL_SERVICE_NAME)
    span = tracer.start_span(name)

    if attributes:
        for key, value in attributes.items():
            span.set_attribute(key, value)

    return span


def set_span_attributes(span, **kwargs):
    """Set multiple span attributes."""
    for key, value in kwargs.items():
        span.set_attribute(key, value)


def set_span_error(span, error: Exception):
    """Mark span as error and record exception."""
    span.set_status(Status(StatusCode.ERROR, str(error)))
    span.record_exception(error)


# Tracer context manager
class TracedContext:
    """Context manager for tracing."""

    def __init__(self, span_name: str, attributes: dict = None):
        self.span_name = span_name
        self.attributes = attributes or {}
        self.span = None
        self.tracer = trace.get_tracer(OTEL_SERVICE_NAME)

    def __enter__(self):
        self.span = self.tracer.start_span(self.span_name)

        for key, value in self.attributes.items():
            self.span.set_attribute(key, value)

        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            set_span_error(self.span, exc_val)
        else:
            self.span.set_status(Status(StatusCode.OK))

        self.span.end()


# Convenience functions for common operations
def trace_search(query: str, tenant_id: str, search_type: str = "hybrid"):
    """Trace search operation."""
    return TracedContext(
        "search",
        {
            "search.query": query,
            "search.tenant_id": tenant_id,
            "search.type": search_type,
        },
    )


def trace_rag(query: str, tenant_id: str):
    """Trace RAG query operation."""
    return TracedContext("rag_query", {"rag.query": query, "rag.tenant_id": tenant_id})


def trace_extraction(query: str, tenant_id: str, extraction_type: str = "sync"):
    """Trace extraction operation."""
    return TracedContext(
        "extraction",
        {
            "extraction.query": query,
            "extraction.tenant_id": tenant_id,
            "extraction.type": extraction_type,
        },
    )


def trace_llm_request(model: str, backend: str, prompt_tokens: int = 0):
    """Trace LLM request."""
    return TracedContext(
        "llm_request",
        {
            "llm.model": model,
            "llm.backend": backend,
            "llm.prompt_tokens": prompt_tokens,
        },
    )


def trace_vector_db(operation: str, collection: str):
    """Trace vector DB operation."""
    return TracedContext(
        "vector_db_operation",
        {"vector_db.operation": operation, "vector_db.collection": collection},
    )


def trace_cache_operation(operation: str, cache_type: str = "redis"):
    """Trace cache operation."""
    return TracedContext(
        "cache_operation", {"cache.operation": operation, "cache.type": cache_type}
    )


def trace_db_query(operation: str, table: str):
    """Trace database query."""
    return TracedContext("db_query", {"db.operation": operation, "db.table": table})


# Initialize global tracing
tracing_config: Optional[TracingConfig] = None


def initialize_tracing(
    service_name: str = OTEL_SERVICE_NAME, environment: str = OTEL_ENVIRONMENT
):
    """Initialize global tracing."""
    global tracing_config
    tracing_config = TracingConfig(service_name, environment).initialize()
    return tracing_config


def get_tracer() -> trace.Tracer:
    """Get the global tracer."""
    return trace.get_tracer(OTEL_SERVICE_NAME)


# Example usage
if __name__ == "__main__":
    # Initialize tracing
    initialize_tracing("rag-query-api", "development")

    # Example function with tracing
    @trace_span("example_operation", {"custom.attribute": "value"})
    def example_function():
        with trace_search("machine learning", "tenant-123"):
            print("Performing search...")

        with trace_rag("What is AI?", "tenant-123"):
            print("Performing RAG query...")

        return "success"

    # Run example
    result = example_function()
    print(f"Result: {result}")

    # Shutdown
    if tracing_config and tracing_config.provider:
        tracing_config.provider.shutdown()
