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


def get_chunks_by_doc(doc_id: str, section_path: str | None = None):
    with get_session() as session:
        stmt = select(ChunkRecord).where(ChunkRecord.doc_id == doc_id)
        if section_path:
            stmt = stmt.where(ChunkRecord.section_path == section_path)
        rows = session.execute(stmt).scalars().all()
        return rows
