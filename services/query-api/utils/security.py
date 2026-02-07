import logging
from fastapi import Header, HTTPException, status

logger = logging.getLogger("query-api.security")


class TenantContext:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    def validate_tenant(self, requested_tenant_id: str):
        """
        Verify that the requested tenant ID matches the authenticated tenant ID.
        Raises 403 Forbidden if there is a mismatch.
        """
        if requested_tenant_id != self.tenant_id:
            logger.warning(
                f"Security: Tenant mismatch! Authenticated: {self.tenant_id}, Requested: {requested_tenant_id}"
            )
            # We return 403 Forbidden for tenant mismatches
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to access this tenant's data.",
            )


async def get_tenant_context(
    x_tenant_id: str = Header(
        ..., alias="X-Tenant-ID", description="Tenant ID injected by API Gateway"
    ),
) -> TenantContext:
    """
    FastAPI dependency to get the current tenant context from headers.
    In the RAG system architecture, the API Gateway is responsible for
    authentication and injecting the X-Tenant-ID header.
    """
    return TenantContext(tenant_id=x_tenant_id)
