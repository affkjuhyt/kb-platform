"""
Tenant Management Routes
Handles CRUD operations for tenants, settings, and user management using PostgreSQL.
"""

from datetime import datetime
from typing import List, Optional, Union
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
import uuid

from database import get_db
import models
from auth import get_current_user, TokenData

# Pydantic Models for Request/Response
from pydantic import BaseModel, Field

# ============================================================================
# Pydantic Models
# ============================================================================


class TenantBase(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    plan: str = "free"


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    plan: Optional[str] = None


class TenantResponse(TenantBase):
    id: str
    owner_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TenantSettingsBase(BaseModel):
    rate_limit: dict
    quotas: dict
    api_keys_enabled: bool


class TenantSettingsUpdate(BaseModel):
    rate_limit: Optional[dict] = None
    quotas: Optional[dict] = None
    api_keys_enabled: Optional[bool] = None


class TenantSettingsResponse(TenantSettingsBase):
    tenant_id: str
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TenantUserBase(BaseModel):
    email: str
    role: str = "member"


class UserInvite(TenantUserBase):
    pass


class TenantUserResponse(TenantUserBase):
    id: str
    tenant_id: str
    user_id: str
    name: str
    joined_at: datetime

    class Config:
        from_attributes = True


class InvitationResponse(BaseModel):
    id: str
    tenant_id: str
    email: str
    role: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Routes
# ============================================================================

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("", response_model=List[TenantResponse])
async def list_tenants(
    current_user: TokenData = Depends(get_current_user), db: Session = Depends(get_db)
):
    """List tenants the user has access to."""
    # For simplicity, if user is admin, list all. Otherwise, list where they are members.
    # Logic: Join TenantUser table.
    # But current_user is a dict from auth.py which is mock.
    # If using DB auth, we would check User table.
    # For now, let's return all tenants created by this user (owner) OR where they are member.

    user_id = current_user.user_id

    # Query: Select T.* from Tenant T join TenantUser TU on T.id = TU.tenant_id where TU.user_id = :user_id
    # Or strict owner check for now?
    # Let's support ownership query first.

    # tenants = db.query(models.Tenant).filter(models.Tenant.owner_id == user_id).all()

    # BETTER: Get all tenants where user is a member (including owner if we add owner as member)
    # When creating tenant, we add owner as 'owner' in TenantUser.

    member_tenants = (
        db.query(models.Tenant)
        .join(models.TenantUser)
        .filter(models.TenantUser.user_id == user_id)
        .all()
    )
    return member_tenants


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_in: TenantCreate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new tenant."""
    user_id = current_user.user_id
    user_email = current_user.email

    # 1. Create Tenant
    new_tenant = models.Tenant(
        name=tenant_in.name,
        description=tenant_in.description,
        plan=tenant_in.plan,
        owner_id=user_id,
    )
    db.add(new_tenant)
    db.flush()  # get ID

    # 2. Create Default Settings
    settings = models.TenantSettings(tenant_id=new_tenant.id)
    db.add(settings)

    # 3. Add Owner as Tenant User
    owner_member = models.TenantUser(
        tenant_id=new_tenant.id,
        user_id=user_id,
        email=user_email,
        name=user_email.split("@")[0],  # Simple name derivation
        role="owner",
    )
    db.add(owner_member)

    try:
        db.commit()
        db.refresh(new_tenant)
        return new_tenant
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get tenant details."""
    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Verify access
    user_id = current_user.user_id
    user_access = (
        db.query(models.TenantUser)
        .filter(
            models.TenantUser.tenant_id == tenant_id,
            models.TenantUser.user_id == user_id,
        )
        .first()
    )

    if not user_access and tenant.owner_id != user_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this tenant"
        )

    return tenant


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    tenant_in: TenantUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update tenant details."""
    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Check permission (owner or admin)
    user_id = current_user.user_id
    user_access = (
        db.query(models.TenantUser)
        .filter(
            models.TenantUser.tenant_id == tenant_id,
            models.TenantUser.user_id == user_id,
        )
        .first()
    )

    if not user_access or user_access.role not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Requires owner or admin role")

    if tenant_in.name:
        tenant.name = tenant_in.name
    if tenant_in.description:
        tenant.description = tenant_in.description
    if tenant_in.plan:
        tenant.plan = tenant_in.plan

    db.commit()
    db.refresh(tenant)
    return tenant


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a tenant."""
    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Only owner can delete
    if tenant.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Only owner can delete tenant")

    db.delete(tenant)
    db.commit()
    return None


@router.get("/{tenant_id}/settings", response_model=TenantSettingsResponse)
async def get_tenant_settings(
    tenant_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get tenant settings."""
    settings = (
        db.query(models.TenantSettings)
        .filter(models.TenantSettings.tenant_id == tenant_id)
        .first()
    )
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")

    # Check access
    user_id = current_user.user_id
    user_access = (
        db.query(models.TenantUser)
        .filter(
            models.TenantUser.tenant_id == tenant_id,
            models.TenantUser.user_id == user_id,
        )
        .first()
    )
    if not user_access:
        raise HTTPException(status_code=403, detail="Not authorized")

    return settings


@router.put("/{tenant_id}/settings", response_model=TenantSettingsResponse)
async def update_tenant_settings(
    tenant_id: str,
    settings_in: TenantSettingsUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update tenant settings."""
    settings = (
        db.query(models.TenantSettings)
        .filter(models.TenantSettings.tenant_id == tenant_id)
        .first()
    )
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")

    # Check permissions
    user_id = current_user.user_id
    user_access = (
        db.query(models.TenantUser)
        .filter(
            models.TenantUser.tenant_id == tenant_id,
            models.TenantUser.user_id == user_id,
        )
        .first()
    )

    if not user_access or user_access.role not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Requires owner or admin role")

    if settings_in.rate_limit:
        # Deep merge or replace? Replace for simplicity of JSON field
        # Ideally pydantic handles this, but JSON column updates need care.
        # We assume dictionary is passed.
        # Check current value, it might be None if default lambda not triggered? No, default is set.
        current_rate = settings.rate_limit.copy() if settings.rate_limit else {}
        current_rate.update(settings_in.rate_limit)
        settings.rate_limit = current_rate

    if settings_in.quotas:
        current_quotas = settings.quotas.copy() if settings.quotas else {}
        current_quotas.update(settings_in.quotas)
        settings.quotas = current_quotas

    if settings_in.api_keys_enabled is not None:
        settings.api_keys_enabled = settings_in.api_keys_enabled

    db.commit()
    db.refresh(settings)
    return settings


@router.get("/{tenant_id}/users", response_model=List[TenantUserResponse])
async def list_tenant_users(
    tenant_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List users in a tenant."""
    # Check access
    user_id = current_user.user_id
    user_access = (
        db.query(models.TenantUser)
        .filter(
            models.TenantUser.tenant_id == tenant_id,
            models.TenantUser.user_id == user_id,
        )
        .first()
    )
    if not user_access:
        raise HTTPException(status_code=403, detail="Not authorized")

    users = (
        db.query(models.TenantUser)
        .filter(models.TenantUser.tenant_id == tenant_id)
        .all()
    )
    return users


@router.post(
    "/{tenant_id}/users/invite",
    response_model=Union[TenantUserResponse, InvitationResponse],
)
async def invite_user(
    tenant_id: str,
    invite: UserInvite,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Invite a user to the tenant."""
    # Check permissions (admin/owner)
    user_id = current_user.user_id
    user_access = (
        db.query(models.TenantUser)
        .filter(
            models.TenantUser.tenant_id == tenant_id,
            models.TenantUser.user_id == user_id,
        )
        .first()
    )

    if not user_access or user_access.role not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Requires owner or admin role")

    # Check if user already exists in tenant
    existing = (
        db.query(models.TenantUser)
        .filter(
            models.TenantUser.tenant_id == tenant_id,
            models.TenantUser.email == invite.email,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="User already in tenant")

    # Check for existing pending invitation
    existing_invite = (
        db.query(models.Invitation)
        .filter(
            models.Invitation.tenant_id == tenant_id,
            models.Invitation.email == invite.email,
            models.Invitation.status == "pending",
        )
        .first()
    )
    if existing_invite:
        raise HTTPException(status_code=400, detail="Invitation already pending")

    # Check if user already exists in the global users table
    user = db.query(models.User).filter(models.User.email == invite.email).first()

    if user:
        # User exists, link to tenant immediately
        new_member = models.TenantUser(
            tenant_id=tenant_id,
            user_id=user.id,
            email=invite.email,
            name=user.full_name or invite.email.split("@")[0],
            role=invite.role,
        )
        db.add(new_member)
        db.commit()
        db.refresh(new_member)
        return new_member
    else:
        # User doesn't exist, create an invitation
        new_invite = models.Invitation(
            tenant_id=tenant_id,
            email=invite.email,
            role=invite.role,
            invited_by=user_id,  # user_id of the person inviting
        )
        db.add(new_invite)
        db.commit()
        db.refresh(new_invite)

        # In a real app, we would return the invitation or a success message
        # For compatibility with existing return type hints, we can return a mock user
        # or update the endpoint to reflect invitations.
        # For now, let's return the new invitation as a dict or similar if possible
        return new_invite


@router.delete("/{tenant_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user(
    tenant_id: str,
    user_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a user from the tenant."""
    # Check permissions
    current_uid = current_user.user_id
    user_access = (
        db.query(models.TenantUser)
        .filter(
            models.TenantUser.tenant_id == tenant_id,
            models.TenantUser.user_id == current_uid,
        )
        .first()
    )

    if not user_access or user_access.role not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Requires owner or admin role")

    # Cannot remove self? Optional check.
    if user_id == current_uid:
        raise HTTPException(
            status_code=400, detail="Cannot remove self. Leave tenant instead."
        )

    member_to_remove = (
        db.query(models.TenantUser)
        .filter(
            models.TenantUser.tenant_id == tenant_id,
            models.TenantUser.user_id == user_id,
        )
        .first()
    )

    if not member_to_remove:
        raise HTTPException(status_code=404, detail="User not found")

    # Owner cannot be removed
    if member_to_remove.role == "owner":
        raise HTTPException(status_code=403, detail="Cannot remove owner")

    db.delete(member_to_remove)
    db.commit()
    return None
