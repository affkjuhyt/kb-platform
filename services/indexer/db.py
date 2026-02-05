from contextlib import contextmanager

from sqlalchemy import create_engine, insert
from sqlalchemy.orm import sessionmaker

from config import settings
from db_models import Base, ChunkRecord


engine = create_engine(settings.postgres_dsn, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def insert_chunks(chunks: list[dict]) -> int:
    if not chunks:
        return 0
    with get_session() as session:
        session.execute(insert(ChunkRecord), chunks)
        session.commit()
    return len(chunks)
