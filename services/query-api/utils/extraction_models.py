"""
Database models for storing structured extraction data.
"""

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    Text,
    Boolean,
    Index,
    ForeignKey,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base, relationship
import uuid

Base = declarative_base()


class ExtractionJob(Base):
    """Represents an extraction job/request."""

    __tablename__ = "extraction_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Text, nullable=False, index=True)
    query = Column(Text, nullable=False)
    schema_name = Column(Text, nullable=True)  # e.g., "person", "company", "contract"
    schema_definition = Column(JSONB, nullable=False)  # Full JSON schema
    status = Column(
        Text,
        nullable=False,
        default="pending",  # pending, processing, completed, failed
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Configuration
    top_k = Column(Integer, default=5)
    min_confidence = Column(Float, default=0.7)

    # Relationships
    results = relationship(
        "ExtractionResult", back_populates="job", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_extraction_jobs_tenant_status", "tenant_id", "status"),
        Index("idx_extraction_jobs_created", "created_at"),
    )


class ExtractionResult(Base):
    """Stores the result of an extraction operation."""

    __tablename__ = "extraction_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True), ForeignKey("extraction_jobs.id"), nullable=False, index=True
    )

    # Source information
    source_doc_id = Column(Text, nullable=True)
    source_chunk_index = Column(Integer, nullable=True)
    source_tenant_id = Column(Text, nullable=True)

    # Extracted data
    data = Column(JSONB, nullable=True)  # The extracted structured data
    raw_response = Column(Text, nullable=True)  # Raw LLM response

    # Quality metrics
    confidence = Column(Float, nullable=False, default=0.0)
    is_valid = Column(Boolean, nullable=False, default=False)
    validation_errors = Column(JSONB, default=list)  # List of error messages

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    job = relationship("ExtractionJob", back_populates="results")

    __table_args__ = (
        Index("idx_extraction_results_job", "job_id"),
        Index("idx_extraction_results_confidence", "confidence"),
        Index("idx_extraction_results_valid", "is_valid"),
    )


class ExtractedEntity(Base):
    """
    Normalized view of extracted entities for querying.
    This table stores flattened extraction data for easy querying.
    """

    __tablename__ = "extracted_entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    result_id = Column(
        UUID(as_uuid=True), ForeignKey("extraction_results.id"), nullable=False
    )

    # Entity identification
    entity_type = Column(Text, nullable=False, index=True)  # e.g., "person", "company"
    entity_id = Column(Text, nullable=True)  # Optional entity identifier

    # Key fields for searching
    name = Column(Text, nullable=True, index=True)
    email = Column(Text, nullable=True)
    phone = Column(Text, nullable=True)

    # Full data
    attributes = Column(JSONB, nullable=False, default=dict)

    # Source tracking
    source_doc_id = Column(Text, nullable=True)
    source_version = Column(Integer, nullable=True)
    confidence = Column(Float, nullable=False, default=0.0)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("idx_extracted_entities_type", "entity_type"),
        Index("idx_extracted_entities_name", "name"),
        Index("idx_extracted_entities_confidence", "confidence"),
    )


class RAGConversation(Base):
    """Stores RAG query-response conversations."""

    __tablename__ = "rag_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Text, nullable=False, index=True)
    session_id = Column(Text, nullable=True, index=True)  # For grouping conversations

    # Query info
    query = Column(Text, nullable=False)
    context_chunks = Column(JSONB, default=list)  # List of chunk IDs used

    # Response
    answer = Column(Text, nullable=True)
    citations = Column(JSONB, default=list)  # List of citations
    confidence = Column(Float, default=0.0)

    # Model info
    model = Column(Text, nullable=True)
    backend = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_rag_conversations_tenant", "tenant_id"),
        Index("idx_rag_conversations_session", "session_id"),
        Index("idx_rag_conversations_created", "created_at"),
    )


# Migration script helpers
def create_extraction_tables(engine):
    """Create all extraction-related tables."""
    Base.metadata.create_all(
        engine,
        tables=[
            ExtractionJob.__table__,
            ExtractionResult.__table__,
            ExtractedEntity.__table__,
            RAGConversation.__table__,
        ],
    )


def drop_extraction_tables(engine):
    """Drop all extraction-related tables."""
    Base.metadata.drop_all(
        engine,
        tables=[
            RAGConversation.__table__,
            ExtractedEntity.__table__,
            ExtractionResult.__table__,
            ExtractionJob.__table__,
        ],
    )
