"""
API Gateway Service for RAG System

Features:
- JWT Authentication
- Multi-tenant support
- Rate limiting
- Audit logging
- Request routing to backend services
- API documentation (Swagger/OpenAPI)
"""

import time
import uuid
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from functools import wraps

from fastapi import FastAPI, HTTPException, Request, Depends, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
import httpx
import redis
from jose import JWTError, jwt
from passlib.context import CryptContext
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_gateway")


# Configuration
class Settings:
    SERVICE_PORT = int(os.getenv("API_GATEWAY_PORT", "8000"))
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

    # Rate limiting
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "3600"))  # 1 hour

    # Backend services
    QUERY_API_URL = os.getenv("QUERY_API_URL", "http://localhost:8001")
    LLM_GATEWAY_URL = os.getenv("LLM_GATEWAY_URL", "http://localhost:8004")
    INGESTION_API_URL = os.getenv("INGESTION_API_URL", "http://localhost:8002")

    # Audit logging
    AUDIT_LOG_ENABLED = os.getenv("AUDIT_LOG_ENABLED", "true").lower() == "true"


settings = Settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer()

# Redis client for rate limiting
try:
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis_client.ping()
    logger.info("Connected to Redis")
except Exception as e:
    logger.warning(f"Redis not available: {e}")
    redis_client = None

app = FastAPI(
    title="RAG System API Gateway",
    description="API Gateway for RAG System with authentication, rate limiting, and audit logging",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])


# ============================================================================
# Models
# ============================================================================


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


class UserLogin(BaseModel):
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")
    tenant_id: str = Field(..., description="Tenant ID")


class UserRegister(BaseModel):
    email: str = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="User password")
    tenant_id: str = Field(..., description="Tenant ID")
    name: str = Field(..., description="User name")


class APIKeyCreate(BaseModel):
    name: str = Field(..., description="API key name")
    permissions: List[str] = Field(default=["read"], description="API key permissions")
    expires_days: Optional[int] = Field(default=30, description="Expiration in days")


class APIKey(BaseModel):
    key_id: str
    api_key: str
    name: str
    tenant_id: str
    permissions: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None


class AuditLogEntry(BaseModel):
    id: str
    timestamp: datetime
    tenant_id: str
    user_id: Optional[str]
    api_key_id: Optional[str]
    method: str
    path: str
    status_code: int
    request_size: int
    response_size: int
    duration_ms: float
    client_ip: str
    user_agent: Optional[str]
    error_message: Optional[str] = None


class RateLimitInfo(BaseModel):
    limit: int
    remaining: int
    reset_at: datetime


# ============================================================================
# Authentication
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
    except JWTError:
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


# ============================================================================
# Rate Limiting
# ============================================================================


def get_rate_limit_key(identifier: str, tenant_id: str) -> str:
    """Generate rate limit key for Redis."""
    return f"ratelimit:{tenant_id}:{identifier}"


async def check_rate_limit(identifier: str, tenant_id: str) -> RateLimitInfo:
    """Check rate limit for identifier (user or API key)."""
    if not redis_client:
        # If Redis not available, allow all requests
        return RateLimitInfo(
            limit=settings.RATE_LIMIT_REQUESTS,
            remaining=settings.RATE_LIMIT_REQUESTS,
            reset_at=datetime.utcnow() + timedelta(seconds=settings.RATE_LIMIT_WINDOW),
        )

    key = get_rate_limit_key(identifier, tenant_id)
    now = int(time.time())
    window_start = now - settings.RATE_LIMIT_WINDOW

    # Remove old entries
    redis_client.zremrangebyscore(key, 0, window_start)

    # Count current requests in window
    current_count = redis_client.zcard(key)

    if current_count >= settings.RATE_LIMIT_REQUESTS:
        # Get oldest request timestamp
        oldest = redis_client.zrange(key, 0, 0, withscores=True)
        reset_at = (
            datetime.fromtimestamp(oldest[0][1] + settings.RATE_LIMIT_WINDOW)
            if oldest
            else datetime.utcnow()
        )

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "limit": settings.RATE_LIMIT_REQUESTS,
                "reset_at": reset_at.isoformat(),
            },
        )

    # Add current request
    redis_client.zadd(key, {str(uuid.uuid4()): now})
    redis_client.expire(key, settings.RATE_LIMIT_WINDOW)

    return RateLimitInfo(
        limit=settings.RATE_LIMIT_REQUESTS,
        remaining=settings.RATE_LIMIT_REQUESTS - current_count - 1,
        reset_at=datetime.utcnow() + timedelta(seconds=settings.RATE_LIMIT_WINDOW),
    )


# ============================================================================
# Audit Logging
# ============================================================================

audit_logs: List[AuditLogEntry] = []  # In production, use database


async def log_audit_event(
    tenant_id: str,
    user_id: Optional[str],
    api_key_id: Optional[str],
    method: str,
    path: str,
    status_code: int,
    request_size: int,
    response_size: int,
    duration_ms: float,
    client_ip: str,
    user_agent: Optional[str],
    error_message: Optional[str] = None,
):
    """Log audit event."""
    if not settings.AUDIT_LOG_ENABLED:
        return

    entry = AuditLogEntry(
        id=str(uuid.uuid4()),
        timestamp=datetime.utcnow(),
        tenant_id=tenant_id,
        user_id=user_id,
        api_key_id=api_key_id,
        method=method,
        path=path,
        status_code=status_code,
        request_size=request_size,
        response_size=response_size,
        duration_ms=duration_ms,
        client_ip=client_ip,
        user_agent=user_agent,
        error_message=error_message,
    )

    audit_logs.append(entry)

    # In production, write to database or logging service
    logger.info(f"AUDIT: {entry.json()}")


# ============================================================================
# Middleware
# ============================================================================


@app.middleware("http")
async def audit_logging_middleware(request: Request, call_next):
    """Middleware for audit logging and rate limiting."""
    start_time = time.time()

    # Extract tenant and user info
    tenant_id = request.headers.get("X-Tenant-ID", "default")
    user_id = None
    api_key_id = None

    # Try to extract from Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header.split(" ")[1]
            token_data = verify_token(token)
            user_id = token_data.user_id
            tenant_id = token_data.tenant_id
        except:
            pass

    # Process request
    try:
        response = await call_next(request)
        status_code = response.status_code
        error_message = None
    except Exception as e:
        status_code = 500
        error_message = str(e)
        response = JSONResponse(
            status_code=500, content={"detail": "Internal server error"}
        )

    # Calculate duration
    duration_ms = (time.time() - start_time) * 1000

    # Log audit event
    await log_audit_event(
        tenant_id=tenant_id,
        user_id=user_id,
        api_key_id=api_key_id,
        method=request.method,
        path=request.url.path,
        status_code=status_code,
        request_size=0,  # Calculate from request body
        response_size=0,  # Calculate from response
        duration_ms=duration_ms,
        client_ip=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("User-Agent"),
        error_message=error_message,
    )

    return response


# ============================================================================
# Auth Endpoints
# ============================================================================


@app.post("/auth/login", response_model=Token, tags=["Authentication"])
async def login(credentials: UserLogin):
    """
    Authenticate user and return JWT token.

    - **email**: User email address
    - **password**: User password
    - **tenant_id**: Tenant identifier
    """
    # In production, verify against database
    # For demo, accept any credentials

    user_id = str(uuid.uuid4())
    access_token_expires = timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    access_token = create_access_token(
        data={
            "sub": user_id,
            "email": credentials.email,
            "tenant_id": credentials.tenant_id,
            "permissions": ["read", "write"],
        },
        expires_delta=access_token_expires,
    )

    return Token(
        access_token=access_token,
        expires_in=int(access_token_expires.total_seconds()),
        tenant_id=credentials.tenant_id,
    )


@app.post("/auth/register", response_model=Token, tags=["Authentication"])
async def register(user_data: UserRegister):
    """
    Register a new user and return JWT token.

    - **email**: User email address
    - **password**: Password (min 8 characters)
    - **tenant_id**: Tenant identifier
    - **name**: User full name
    """
    # In production, save to database
    user_id = str(uuid.uuid4())
    access_token_expires = timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    access_token = create_access_token(
        data={
            "sub": user_id,
            "email": user_data.email,
            "tenant_id": user_data.tenant_id,
            "permissions": ["read", "write"],
        },
        expires_delta=access_token_expires,
    )

    return Token(
        access_token=access_token,
        expires_in=int(access_token_expires.total_seconds()),
        tenant_id=user_data.tenant_id,
    )


@app.post("/auth/api-keys", response_model=APIKey, tags=["Authentication"])
async def create_api_key(
    key_data: APIKeyCreate, current_user: TokenData = Depends(get_current_user)
):
    """
    Create a new API key for programmatic access.

    - **name**: Descriptive name for the API key
    - **permissions**: List of permissions (e.g., ["read", "write"])
    - **expires_days**: Number of days until expiration (optional)
    """
    key_id = str(uuid.uuid4())
    api_key = f"rag_{key_id}_{secrets.token_urlsafe(32)}"

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


@app.get("/auth/me", tags=["Authentication"])
async def get_current_user_info(current_user: TokenData = Depends(get_current_user)):
    """Get current user information."""
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "tenant_id": current_user.tenant_id,
        "permissions": current_user.permissions,
    }


# ============================================================================
# Proxy Endpoints
# ============================================================================


async def proxy_request(
    method: str,
    path: str,
    base_url: str,
    request: Request,
    current_user: TokenData,
    body: Optional[dict] = None,
):
    """Proxy request to backend service."""
    url = f"{base_url}{path}"

    headers = {
        "X-Tenant-ID": current_user.tenant_id,
        "X-User-ID": current_user.user_id,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        try:
            if method == "GET":
                response = await client.get(url, headers=headers, timeout=30)
            elif method == "POST":
                response = await client.post(
                    url, headers=headers, json=body, timeout=30
                )
            elif method == "PUT":
                response = await client.put(url, headers=headers, json=body, timeout=30)
            elif method == "DELETE":
                response = await client.delete(url, headers=headers, timeout=30)
            else:
                raise HTTPException(status_code=405, detail="Method not allowed")

            return JSONResponse(
                status_code=response.status_code, content=response.json()
            )
        except httpx.RequestError as e:
            logger.error(f"Error proxying request: {e}")
            raise HTTPException(status_code=503, detail="Service unavailable")


@app.api_route(
    "/query/{path:path}", methods=["GET", "POST", "PUT", "DELETE"], tags=["Query API"]
)
async def query_api_proxy(
    path: str, request: Request, current_user: TokenData = Depends(get_current_user)
):
    """
    Proxy requests to Query API service.

    Requires authentication. Supports search, RAG, and extraction operations.
    """
    await check_rate_limit(current_user.user_id, current_user.tenant_id)

    body = None
    if request.method in ["POST", "PUT"]:
        body = await request.json()

    return await proxy_request(
        request.method, f"/{path}", settings.QUERY_API_URL, request, current_user, body
    )


@app.api_route("/llm/{path:path}", methods=["GET", "POST"], tags=["LLM Gateway"])
async def llm_gateway_proxy(
    path: str, request: Request, current_user: TokenData = Depends(get_current_user)
):
    """
    Proxy requests to LLM Gateway service.

    Requires authentication. Supports text generation and extraction.
    """
    await check_rate_limit(current_user.user_id, current_user.tenant_id)

    body = None
    if request.method == "POST":
        body = await request.json()

    return await proxy_request(
        request.method,
        f"/{path}",
        settings.LLM_GATEWAY_URL,
        request,
        current_user,
        body,
    )


# ============================================================================
# Audit Log Endpoints
# ============================================================================


@app.get("/admin/audit-logs", tags=["Admin"])
async def get_audit_logs(
    current_user: TokenData = Depends(get_current_user),
    limit: int = 100,
    offset: int = 0,
):
    """
    Get audit logs (admin only).

    Returns recent API access logs with timing and status information.
    """
    if "admin" not in current_user.permissions:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Filter by tenant
    logs = [log for log in audit_logs if log.tenant_id == current_user.tenant_id]
    logs = logs[offset : offset + limit]

    return {
        "total": len(logs),
        "offset": offset,
        "limit": limit,
        "logs": [log.dict() for log in logs],
    }


@app.get("/admin/stats", tags=["Admin"])
async def get_gateway_stats(current_user: TokenData = Depends(get_current_user)):
    """
    Get gateway statistics (admin only).

    Returns aggregate statistics about API usage.
    """
    if "admin" not in current_user.permissions:
        raise HTTPException(status_code=403, detail="Admin access required")

    tenant_logs = [log for log in audit_logs if log.tenant_id == current_user.tenant_id]

    total_requests = len(tenant_logs)
    successful_requests = len([log for log in tenant_logs if log.status_code < 400])
    error_requests = len([log for log in tenant_logs if log.status_code >= 400])
    avg_duration = (
        sum(log.duration_ms for log in tenant_logs) / total_requests
        if total_requests > 0
        else 0
    )

    return {
        "tenant_id": current_user.tenant_id,
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "error_requests": error_requests,
        "success_rate": (successful_requests / total_requests * 100)
        if total_requests > 0
        else 0,
        "avg_response_time_ms": round(avg_duration, 2),
        "period": "all_time",
    }


# ============================================================================
# Health Check
# ============================================================================


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "services": {
            "redis": "connected" if redis_client else "disconnected",
            "query_api": "unknown",  # Check in production
            "llm_gateway": "unknown",
        },
    }


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import os
    import secrets
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.SERVICE_PORT)
