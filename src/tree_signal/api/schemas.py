"""API schemas for message ingestion endpoints."""
from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, Field


class MessageIngress(BaseModel):
    """Payload accepted by the message ingestion endpoint."""

    channel: str = Field(..., description="Hierarchical channel path using '.' separators")
    payload: str = Field(..., description="Opaque message payload to display")
    severity: str = Field(default="info", description="Severity level: debug|info|warn|error")
    metadata: Optional[Dict[str, str]] = Field(default=None, description="Optional additional metadata")


class MessageIngressResponse(BaseModel):
    """Simple acknowledgement returned after ingesting a message."""

    id: str
    status: str = "accepted"


__all__ = ["MessageIngress", "MessageIngressResponse"]
