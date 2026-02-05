from sqlalchemy import Column, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class ChunkRecord(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True)
    doc_id = Column(Text, nullable=False)
    tenant_id = Column(Text, nullable=False)
    source = Column(Text, nullable=False)
    source_id = Column(Text, nullable=False)
    version = Column(Integer, nullable=False)
    raw_object_key = Column(Text, nullable=False)
    content_type = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    heading_path = Column(JSONB, nullable=False)
    section_path = Column(Text, nullable=False)
    start = Column(Integer, nullable=False)
    end = Column(Integer, nullable=False)
    schema_version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
