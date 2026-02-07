from contextlib import contextmanager

from sqlalchemy import create_engine, select, tuple_
from sqlalchemy.orm import sessionmaker, Session

from config import settings
from models import ChunkRecord


engine = create_engine(settings.postgres_dsn, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_db_session() -> Session:
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_chunks_by_ids(ids: list[tuple[str, int]]):
    if not ids:
        return []
    with get_session() as session:
        stmt = select(ChunkRecord).where(
            tuple_(ChunkRecord.doc_id, ChunkRecord.chunk_index).in_(ids)
        )
        rows = session.execute(stmt).scalars().all()
        return rows


def get_chunks_by_doc(tenant_id: str, doc_id: str, section_path: str | None = None):
    with get_session() as session:
        stmt = select(ChunkRecord).where(
            ChunkRecord.tenant_id == tenant_id, ChunkRecord.doc_id == doc_id
        )
        if section_path:
            stmt = stmt.where(ChunkRecord.section_path == section_path)
        rows = session.execute(stmt).scalars().all()
        return rows


def get_chunks_by_source_id(
    tenant_id: str, source: str, source_id: str, version: int | None = None
):
    """Get all chunks for a specific source_id.

    Args:
        tenant_id: Tenant ID
        source: Source identifier
        source_id: Document source ID
        version: Optional specific version (if None, gets latest)

    Returns:
        List of ChunkRecord objects
    """
    with get_session() as session:
        stmt = select(ChunkRecord).where(
            ChunkRecord.tenant_id == tenant_id,
            ChunkRecord.source == source,
            ChunkRecord.source_id == source_id,
        )
        if version is not None:
            stmt = stmt.where(ChunkRecord.version == version)
        stmt = stmt.order_by(ChunkRecord.chunk_index)
        rows = session.execute(stmt).scalars().all()
        return rows
