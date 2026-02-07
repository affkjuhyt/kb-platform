from typing import Any, Optional
from pydantic import BaseModel, Field


class IngestWebhookRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    source_id: str = Field(..., min_length=1)
    content_type: str = "text/plain"
    content: Optional[str] = None
    content_base64: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestPullRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    source_id: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    content_type: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestResponse(BaseModel):
    doc_id: str
    version: int
    duplicate: bool
    raw_object_key: str
