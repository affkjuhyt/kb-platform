from schema import ExtractRequest, ExtractResult, ExtractionJobResponse
from typing import Optional
from fastapi import HTTPException
from utils.extraction_storage import ExtractionStorageService
from db import get_db_session
from sqlalchemy.orm import Session
from fastapi import Depends, APIRouter
from utils.extraction import ExtractionService

extract_router = APIRouter()


@extract_router.post("/extract", response_model=ExtractResult)
def extract_data(payload: ExtractRequest):
    """
    Extract structured data from documents based on query and schema.

    1. Searches for relevant context
    2. Performs structured extraction
    3. Validates against schema
    4. Returns extracted data with confidence score
    """
    extraction_service = ExtractionService()

    result = extraction_service.extract_from_search(
        query=payload.query,
        tenant_id=payload.tenant_id,
        extraction_schema=payload.schema,
        top_k=payload.top_k,
        min_confidence=payload.min_confidence,
    )

    return ExtractResult(
        success=result.success,
        data=result.data,
        confidence=result.confidence,
        validation_errors=result.validation_errors,
    )


@extract_router.post("/extract/jobs", response_model=ExtractionJobResponse)
def create_extraction_job(
    payload: ExtractRequest,
    db: Session = Depends(get_db_session),
):
    """
    Create an extraction job and save results to database.
    """
    storage_service = ExtractionStorageService(db)

    # Create job
    job = storage_service.create_job(
        tenant_id=payload.tenant_id,
        query=payload.query,
        schema_definition=payload.schema,
        schema_name=payload.schema_name,
        top_k=payload.top_k,
        min_confidence=payload.min_confidence,
    )

    # Update status to processing
    storage_service.update_job_status(job.id, "processing")

    try:
        # Perform extraction
        extraction_service = ExtractionService()
        result = extraction_service.extract_from_search(
            query=payload.query,
            tenant_id=payload.tenant_id,
            extraction_schema=payload.schema,
            top_k=payload.top_k,
            min_confidence=payload.min_confidence,
        )

        # Save result
        storage_service.save_result(
            job_id=job.id,
            data=result.data,
            confidence=result.confidence,
            is_valid=result.success and len(result.validation_errors) == 0,
            validation_errors=result.validation_errors,
            raw_response=result.raw_response,
        )

        # Update job status
        if result.success:
            storage_service.update_job_status(job.id, "completed")
        else:
            storage_service.update_job_status(
                job.id, "failed", error_message="; ".join(result.validation_errors)
            )

        return ExtractionJobResponse(
            job_id=str(job.id),
            status="completed" if result.success else "failed",
            query=job.query,
            schema_name=job.schema_name,
            created_at=job.created_at,
            result_count=1 if result.data else 0,
        )

    except Exception as e:
        storage_service.update_job_status(job.id, "failed", error_message=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@extract_router.get("/extract/jobs/{job_id}")
def get_extraction_job(
    job_id: str,
    db: Session = Depends(get_db_session),
):
    """Get extraction job details and results."""
    from uuid import UUID

    storage_service = ExtractionStorageService(db)
    job = storage_service.get_job(UUID(job_id))

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    results = storage_service.get_job_results(UUID(job_id))

    return {
        "job": {
            "id": str(job.id),
            "tenant_id": job.tenant_id,
            "query": job.query,
            "schema_name": job.schema_name,
            "status": job.status,
            "created_at": job.created_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        },
        "results": [
            {
                "id": str(r.id),
                "data": r.data,
                "confidence": r.confidence,
                "is_valid": r.is_valid,
                "validation_errors": r.validation_errors,
                "created_at": r.created_at.isoformat(),
            }
            for r in results
        ],
    }


@extract_router.get("/extract/jobs")
def list_extraction_jobs(
    tenant_id: str,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db_session),
):
    """List extraction jobs for a tenant."""
    storage_service = ExtractionStorageService(db)
    jobs = storage_service.list_jobs(tenant_id, status, limit, offset)

    return {
        "jobs": [
            {
                "id": str(job.id),
                "query": job.query,
                "schema_name": job.schema_name,
                "status": job.status,
                "created_at": job.created_at.isoformat(),
            }
            for job in jobs
        ],
        "total": len(jobs),
    }


@extract_router.get("/extract/stats")
def get_extraction_stats(
    tenant_id: str,
    days: int = 30,
    db: Session = Depends(get_db_session),
):
    """Get extraction statistics for a tenant."""
    storage_service = ExtractionStorageService(db)
    stats = storage_service.get_extraction_stats(tenant_id, days)

    return stats
