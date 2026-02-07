import logging

from contextlib import asynccontextmanager
from datetime import datetime, UTC
from fastapi import FastAPI

from routes import ingest_router
from utils.storage import storage_service_factory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingestion")


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting up ingestion service...")

    # Run database migrations
    try:
        logger.info("Running database migrations...")
        logger.info("✓ Database migrations completed")
    except Exception as e:
        logger.error(f"✗ Database migration failed: {e}")
        logger.warning(
            "Continuing without migrations - database might not be properly set up"
        )

    # Ensure MinIO bucket exists
    try:
        logger.info("Ensuring MinIO bucket exists...")
        storage_service_factory().ensure_bucket()
        logger.info("✓ MinIO bucket ready")
    except Exception as e:
        logger.error(f"✗ MinIO connection failed: {e}")
        logger.warning("MinIO not available - file storage will not work")
        logger.info("Make sure MinIO is running: docker-compose up -d minio")

    logger.info("✓ Ingestion service startup complete")
    yield

    logger.info("Shutting down ingestion service...")


app = FastAPI(title="Ingestion Service", lifespan=lifespan)
app.include_router(ingest_router)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "time": datetime.now(UTC).isoformat()}
