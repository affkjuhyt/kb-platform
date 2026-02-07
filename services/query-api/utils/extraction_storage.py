"""
Storage service for extraction results and RAG conversations.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import desc

from extraction_models import (
    ExtractionJob,
    ExtractionResult,
    ExtractedEntity,
    RAGConversation,
)

logger = logging.getLogger("extraction_storage")


class ExtractionStorageService:
    """Service for storing and retrieving extraction data."""

    def __init__(self, db_session: Session):
        self.db = db_session

    def create_job(
        self,
        tenant_id: str,
        query: str,
        schema_definition: Dict[str, Any],
        schema_name: Optional[str] = None,
        top_k: int = 5,
        min_confidence: float = 0.7,
    ) -> ExtractionJob:
        """Create a new extraction job."""
        job = ExtractionJob(
            tenant_id=tenant_id,
            query=query,
            schema_name=schema_name or "custom",
            schema_definition=schema_definition,
            top_k=top_k,
            min_confidence=min_confidence,
            status="pending",
        )

        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        logger.info(f"Created extraction job {job.id} for tenant {tenant_id}")
        return job

    def update_job_status(
        self,
        job_id: UUID,
        status: str,
        error_message: Optional[str] = None,
    ) -> ExtractionJob:
        """Update job status."""
        job = self.db.query(ExtractionJob).filter(ExtractionJob.id == job_id).first()

        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.status = status

        if status == "processing":
            job.started_at = datetime.utcnow()
        elif status in ["completed", "failed"]:
            job.completed_at = datetime.utcnow()

        if error_message:
            # Store error in schema_definition temporarily
            job.schema_definition["_error"] = error_message

        self.db.commit()
        self.db.refresh(job)

        return job

    def save_result(
        self,
        job_id: UUID,
        data: Optional[Dict[str, Any]],
        confidence: float,
        is_valid: bool,
        validation_errors: List[str],
        raw_response: Optional[str] = None,
        source_doc_id: Optional[str] = None,
        source_chunk_index: Optional[int] = None,
    ) -> ExtractionResult:
        """Save an extraction result."""
        result = ExtractionResult(
            job_id=job_id,
            data=data,
            raw_response=raw_response,
            confidence=confidence,
            is_valid=is_valid,
            validation_errors=validation_errors,
            source_doc_id=source_doc_id,
            source_chunk_index=source_chunk_index,
        )

        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)

        # If valid data, also create extracted entities for querying
        if is_valid and data:
            self._create_entities_from_result(result)

        logger.info(f"Saved extraction result {result.id} for job {job_id}")
        return result

    def _create_entities_from_result(
        self,
        result: ExtractionResult,
    ) -> List[ExtractedEntity]:
        """Create normalized entity records from extraction result."""
        entities = []

        if not result.data:
            return entities

        # Get job info for entity type
        job = (
            self.db.query(ExtractionJob)
            .filter(ExtractionJob.id == result.job_id)
            .first()
        )

        entity_type = job.schema_name if job else "unknown"

        # Create entity record
        entity = ExtractedEntity(
            result_id=result.id,
            entity_type=entity_type,
            entity_id=result.data.get("id") or result.data.get("entity_id"),
            name=result.data.get("name"),
            email=result.data.get("email"),
            phone=result.data.get("phone"),
            attributes=result.data,  # Store full data
            source_doc_id=result.source_doc_id,
            source_version=None,  # Could be populated from context
            confidence=result.confidence,
        )

        self.db.add(entity)
        entities.append(entity)

        # Handle nested entities or arrays
        for key, value in result.data.items():
            if (
                isinstance(value, list)
                and len(value) > 0
                and isinstance(value[0], dict)
            ):
                # Array of entities
                for item in value:
                    if isinstance(item, dict):
                        nested_entity = ExtractedEntity(
                            result_id=result.id,
                            entity_type=f"{entity_type}.{key}",
                            attributes=item,
                            confidence=result.confidence,
                        )
                        self.db.add(nested_entity)
                        entities.append(nested_entity)

        self.db.commit()
        return entities

    def get_job(self, job_id: UUID) -> Optional[ExtractionJob]:
        """Get extraction job by ID."""
        return self.db.query(ExtractionJob).filter(ExtractionJob.id == job_id).first()

    def get_job_results(self, job_id: UUID) -> List[ExtractionResult]:
        """Get all results for a job."""
        return (
            self.db.query(ExtractionResult)
            .filter(ExtractionResult.job_id == job_id)
            .order_by(desc(ExtractionResult.confidence))
            .all()
        )

    def list_jobs(
        self,
        tenant_id: str,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ExtractionJob]:
        """List extraction jobs for a tenant."""
        query = self.db.query(ExtractionJob).filter(
            ExtractionJob.tenant_id == tenant_id
        )

        if status:
            query = query.filter(ExtractionJob.status == status)

        return (
            query.order_by(desc(ExtractionJob.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def search_entities(
        self,
        tenant_id: str,
        entity_type: Optional[str] = None,
        name: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 100,
    ) -> List[ExtractedEntity]:
        """Search extracted entities."""
        # Note: This requires joining with ExtractionJob to filter by tenant
        from sqlalchemy import join

        query = (
            self.db.query(ExtractedEntity)
            .join(ExtractionResult, ExtractedEntity.result_id == ExtractionResult.id)
            .join(ExtractionJob, ExtractionResult.job_id == ExtractionJob.id)
            .filter(ExtractionJob.tenant_id == tenant_id)
        )

        if entity_type:
            query = query.filter(ExtractedEntity.entity_type == entity_type)

        if name:
            query = query.filter(ExtractedEntity.name.ilike(f"%{name}%"))

        if min_confidence > 0:
            query = query.filter(ExtractedEntity.confidence >= min_confidence)

        return query.order_by(desc(ExtractedEntity.confidence)).limit(limit).all()

    def save_rag_conversation(
        self,
        tenant_id: str,
        query: str,
        answer: str,
        citations: List[str],
        confidence: float,
        context_chunks: List[Dict[str, Any]],
        session_id: Optional[str] = None,
        model: Optional[str] = None,
        backend: Optional[str] = None,
    ) -> RAGConversation:
        """Save a RAG conversation."""
        conversation = RAGConversation(
            tenant_id=tenant_id,
            session_id=session_id,
            query=query,
            answer=answer,
            citations=citations,
            confidence=confidence,
            context_chunks=context_chunks,
            model=model,
            backend=backend,
        )

        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)

        logger.info(f"Saved RAG conversation {conversation.id} for tenant {tenant_id}")
        return conversation

    def get_conversation_history(
        self,
        session_id: str,
        limit: int = 50,
    ) -> List[RAGConversation]:
        """Get conversation history for a session."""
        return (
            self.db.query(RAGConversation)
            .filter(RAGConversation.session_id == session_id)
            .order_by(RAGConversation.created_at)
            .limit(limit)
            .all()
        )

    def get_extraction_stats(
        self,
        tenant_id: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get extraction statistics for a tenant."""
        from datetime import timedelta
        from sqlalchemy import func

        since = datetime.utcnow() - timedelta(days=days)

        # Job stats
        job_stats = (
            self.db.query(
                ExtractionJob.status, func.count(ExtractionJob.id).label("count")
            )
            .filter(
                ExtractionJob.tenant_id == tenant_id, ExtractionJob.created_at >= since
            )
            .group_by(ExtractionJob.status)
            .all()
        )

        # Result stats
        result_stats = (
            self.db.query(
                func.avg(ExtractionResult.confidence).label("avg_confidence"),
                func.sum(ExtractionResult.is_valid.cast(Integer)).label("valid_count"),
                func.count(ExtractionResult.id).label("total_count"),
            )
            .join(ExtractionJob)
            .filter(
                ExtractionJob.tenant_id == tenant_id,
                ExtractionResult.created_at >= since,
            )
            .first()
        )

        return {
            "period_days": days,
            "jobs_by_status": {status: count for status, count in job_stats},
            "average_confidence": float(result_stats.avg_confidence)
            if result_stats.avg_confidence
            else 0.0,
            "valid_results": result_stats.valid_count or 0,
            "total_results": result_stats.total_count or 0,
            "success_rate": (
                (result_stats.valid_count / result_stats.total_count * 100)
                if result_stats.total_count
                else 0.0
            ),
        }


if __name__ == "__main__":
    # Example usage
    print("Extraction Storage Service")
    print("=" * 60)
    print("\nThis service provides:")
    print("- Create and manage extraction jobs")
    print("- Store extraction results with validation")
    print("- Create normalized entity records")
    print("- Store RAG conversations")
    print("- Query and statistics")
    print("\nUse with a SQLAlchemy session:")
    print("  service = ExtractionStorageService(db_session)")
    print("  job = service.create_job(tenant_id, query, schema)")
    print("  result = service.save_result(job.id, data, confidence, ...)")
