"""API schemas for message and layout endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from tree_signal.core import LayoutFrame, LayoutRect, Message, PanelState


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


class MessageRecord(BaseModel):
    """Outbound representation of a stored message."""

    id: str
    channel: Tuple[str, ...]
    payload: str
    severity: str
    received_at: datetime
    metadata: Optional[Dict[str, str]]

    @classmethod
    def from_domain(cls, message: Message) -> "MessageRecord":
        return cls(
            id=message.id,
            channel=message.channel_path,
            payload=message.payload,
            severity=message.severity.value,
            received_at=message.received_at,
            metadata=message.metadata,
        )


class LayoutRectModel(BaseModel):
    x: float
    y: float
    width: float
    height: float

    @classmethod
    def from_domain(cls, rect: LayoutRect) -> "LayoutRectModel":
        return cls(x=rect.x, y=rect.y, width=rect.width, height=rect.height)


class LayoutFrameResponse(BaseModel):
    path: Tuple[str, ...]
    rect: LayoutRectModel
    state: PanelState
    weight: float
    generated_at: datetime

    @classmethod
    def from_domain(cls, frame: LayoutFrame) -> "LayoutFrameResponse":
        return cls(
            path=frame.path,
            rect=LayoutRectModel.from_domain(frame.rect),
            state=frame.state,
            weight=frame.weight,
            generated_at=frame.generated_at,
        )


__all__ = [
    "LayoutFrameResponse",
    "LayoutRectModel",
    "MessageIngress",
    "MessageIngressResponse",
    "MessageRecord",
]
