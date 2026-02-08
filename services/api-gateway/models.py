from sqlalchemy import Column, String, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.sql import func
from database import Base
import uuid


def generate_uuid():
    return str(uuid.uuid4())


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    plan = Column(String, default="free")
    owner_id = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TenantSettings(Base):
    __tablename__ = "tenant_settings"

    tenant_id = Column(
        String, ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True
    )
    rate_limit = Column(
        JSON, default=lambda: {"requests_per_minute": 60, "requests_per_day": 10000}
    )
    quotas = Column(
        JSON,
        default=lambda: {
            "max_documents": 1000,
            "max_storage_gb": 10,
            "max_users": 5,
        },
    )
    api_keys_enabled = Column(Boolean, default=True)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TenantUser(Base):
    __tablename__ = "tenant_users"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    email = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, default="member")  # owner, admin, member, viewer
    joined_at = Column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Invitation(Base):
    __tablename__ = "invitations"
    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(
        String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    email = Column(String, nullable=False, index=True)
    role = Column(String, default="member")
    status = Column(String, default="pending")  # pending, accepted, expired
    invited_by = Column(String, nullable=True)  # user_id of the inviter
    created_at = Column(DateTime(timezone=True), server_default=func.now())
