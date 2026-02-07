from sqlalchemy import Boolean, Column, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Document(Base):
    __tablename__ = "documents"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4()
    )
    tenant_id = Column(Text, nullable=False)
    source = Column(Text, nullable=False)
    source_id = Column(Text, nullable=False)
    content_hash = Column(Text, nullable=False)
    version = Column(Integer, nullable=False)
    latest = Column(Boolean, nullable=False, default=True)
    raw_object_key = Column(Text, nullable=False)
    content_type = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSONB, nullable=False, server_default="{}")
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
