from datetime import datetime, timedelta
from typing import Optional, List
from functools import wraps
from fastapi import HTTPException, Depends, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext
from config import settings

# Security schemes
security = HTTPBearer()
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


# ============================================================================
# Models
# ============================================================================


# ============================================================================
# Models
# ============================================================================


class UserLogin(BaseModel):
    email: str
    password: str
    tenant_id: Optional[str] = "default"


class UserRegister(BaseModel):
    email: str
    password: str
    tenant_id: str
    name: str


class APIKeyCreate(BaseModel):
    name: str
    permissions: List[str] = ["read"]
    expires_days: Optional[int] = 30


class APIKey(BaseModel):
    key_id: str
    api_key: str
    name: str
    tenant_id: str
    permissions: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    tenant_id: str


class TokenData(BaseModel):
    user_id: str
    tenant_id: str
    email: str
    permissions: List[str]
    exp: Optional[datetime] = None


# ============================================================================
# Auth Functions
# ============================================================================


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)

    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "access"})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )

        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )

        return TokenData(
            user_id=payload.get("sub"),
            tenant_id=payload.get("tenant_id"),
            email=payload.get("email"),
            permissions=payload.get("permissions", []),
            exp=datetime.fromtimestamp(payload.get("exp")),
        )
    except JWTError as e:
        import logging

        logger = logging.getLogger("api_gateway")
        logger.error(f"Token verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> TokenData:
    """Dependency to get current authenticated user."""
    token = credentials.credentials
    return verify_token(token)


def require_permissions(required_permissions: List[str]):
    """Decorator to require specific permissions."""

    def decorator(func):
        @wraps(func)
        async def wrapper(
            *args, current_user: TokenData = Depends(get_current_user), **kwargs
        ):
            user_permissions = set(current_user.permissions)
            required = set(required_permissions)

            if not required.issubset(user_permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required: {required_permissions}",
                )

            return await func(*args, current_user=current_user, **kwargs)

        return wrapper

    return decorator
