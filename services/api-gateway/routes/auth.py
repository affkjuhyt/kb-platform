from datetime import timedelta
from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
import secrets

from database import get_db
from models import User, Tenant, TenantUser, TenantSettings, Invitation
from auth import (
    Token,
    UserLogin,
    UserRegister,
    APIKeyCreate,
    APIKey,
    TokenData,
    create_access_token,
    get_current_user,
    verify_password,
    get_password_hash,
)
from config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT token.
    """
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    # Check if user is member of the requested tenant
    # If tenant_id is "default", finding the first tenant the user belongs to
    target_tenant_id = credentials.tenant_id

    user_tenants = db.query(TenantUser).filter(TenantUser.user_id == user.id).all()
    if not user_tenants:
        # Should not happen as register creates a tenant
        raise HTTPException(status_code=400, detail="User has no tenants")

    if target_tenant_id == "default" or not target_tenant_id:
        target_tenant_id = user_tenants[0].tenant_id
    else:
        # Verify membership
        is_member = any(t.tenant_id == target_tenant_id for t in user_tenants)
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this tenant",
            )

    # Get permissions (for now simplified)
    permissions = ["read", "write"]

    access_token_expires = timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    access_token = create_access_token(
        data={
            "sub": user.id,
            "email": user.email,
            "tenant_id": target_tenant_id,
            "permissions": permissions,
        },
        expires_delta=access_token_expires,
    )

    return Token(
        access_token=access_token,
        expires_in=int(access_token_expires.total_seconds()),
        tenant_id=target_tenant_id,
    )


@router.post("/register", response_model=Token)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user and return JWT token.
    Creates a new Tenant for the user automatically.
    """
    # Check if user exists
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create User
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        id=user_id,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.name,
        is_active=True,
    )
    db.add(new_user)
    db.flush()  # Ensure user exists before referencing in TenantUser or Invitations

    # Create Tenant (if tenant_id provided is "new" or similar, usually we create one based on name)
    # But UserRegister model has tenant_id. If frontend sends "default", we generate one.
    # We will ignore user_data.tenant_id for creation logic and generate a new one

    tenant_id = str(uuid.uuid4())
    # Use user name's Workspace or similar
    tenant_name = f"{user_data.name}'s Workspace"

    new_tenant = Tenant(
        id=tenant_id,
        name=tenant_name,
        description="Default workspace",
        owner_id=user_id,
        plan="free",
    )
    db.add(new_tenant)

    # Create Settings
    new_settings = TenantSettings(tenant_id=tenant_id)
    db.add(new_settings)

    # Link User to Tenant
    tenant_user = TenantUser(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        user_id=user_id,
        email=user_data.email,
        name=user_data.name,
        role="owner",
    )
    db.add(tenant_user)

    # Process pending invitations
    pending_invites = (
        db.query(Invitation)
        .filter(Invitation.email == user_data.email, Invitation.status == "pending")
        .all()
    )

    for invite in pending_invites:
        # Create TenantUser link for this workspace
        new_member = TenantUser(
            id=str(uuid.uuid4()),
            tenant_id=invite.tenant_id,
            user_id=user_id,
            email=user_data.email,
            name=user_data.name,
            role=invite.role,
        )
        db.add(new_member)
        # Mark invitation as accepted
        invite.status = "accepted"

    try:
        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

    # Generate Token
    access_token_expires = timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    access_token = create_access_token(
        data={
            "sub": user_id,
            "email": user_data.email,
            "tenant_id": tenant_id,
            "permissions": ["read", "write"],
        },
        expires_delta=access_token_expires,
    )

    return Token(
        access_token=access_token,
        expires_in=int(access_token_expires.total_seconds()),
        tenant_id=tenant_id,
    )


@router.get("/me")
async def get_current_user_info(current_user: TokenData = Depends(get_current_user)):
    """Get current user information."""
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "tenant_id": current_user.tenant_id,
        "permissions": current_user.permissions,
    }


@router.post("/api-keys", response_model=APIKey)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new API key for programmatic access.
    """
    # TODO: Implement DB storage for API Keys if needed
    # For now returning mock as per original app.py logic but ideally should save to DB
    # The original app.py didn't save API keys to DB in the snippet I saw.
    # Wait, models.APIKey exists? No, APIKey is Pydantic model in app.py
    # I should check models.py for APIKey table.

    # There is NO APIKey table in models.py (only TenantSettings has api_keys_enabled).
    # so I will keep the mock implementation for now or simple return

    key_id = str(uuid.uuid4())
    api_key = f"rag_{key_id}_{secrets.token_urlsafe(32)}"

    expires_at = None
    if key_data.expires_days:
        # from datetime import datetime
        pass
        # Import missing

    from datetime import datetime

    expires_at = None
    if key_data.expires_days:
        expires_at = datetime.utcnow() + timedelta(days=key_data.expires_days)

    return APIKey(
        key_id=key_id,
        api_key=api_key,
        name=key_data.name,
        tenant_id=current_user.tenant_id,
        permissions=key_data.permissions,
        created_at=datetime.utcnow(),
        expires_at=expires_at,
    )
