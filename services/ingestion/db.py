from contextlib import contextmanager

from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import sessionmaker

from config import settings
from models import Document


engine = create_engine(settings.postgres_dsn, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_latest_doc(tenant_id: str, source: str, source_id: str):
    stmt = (
        select(Document.id, Document.content_hash, Document.version)
        .where(
            Document.tenant_id == tenant_id,
            Document.source == source,
            Document.source_id == source_id,
            Document.latest.is_(True),
        )
        .limit(1)
    )
    with get_session() as session:
        result = session.execute(stmt).first()
        return result


def mark_latest_false(tenant_id: str, source: str, source_id: str) -> None:
    stmt = (
        update(Document)
        .where(
            Document.tenant_id == tenant_id,
            Document.source == source,
            Document.source_id == source_id,
            Document.latest.is_(True),
        )
        .values(latest=False)
    )
    with get_session() as session:
        session.execute(stmt)
        session.commit()


def insert_document(
    *,
    tenant_id: str,
    source: str,
    source_id: str,
    content_hash: str,
    version: int,
    raw_object_key: str,
    content_type: str,
    metadata: dict,
):
    with get_session() as session:
        doc = Document(
            tenant_id=tenant_id,
            source=source,
            source_id=source_id,
            content_hash=content_hash,
            version=version,
            latest=True,
            raw_object_key=raw_object_key,
            content_type=content_type,
            metadata_=metadata,
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)
        return doc.id
