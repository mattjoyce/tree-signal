"""API schemas for message, layout, and control endpoints."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, model_validator

from tree_signal.core import ColorScheme, LayoutFrame, LayoutRect, Message, PanelState


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


class ColorSchemeModel(BaseModel):
    hue: int
    background: str
    border: str
    normal: str
    highlight: str

    @classmethod
    def from_domain(cls, scheme: ColorScheme) -> "ColorSchemeModel":
        return cls(
            hue=scheme.hue,
            background=scheme.background,
            border=scheme.border,
            normal=scheme.normal,
            highlight=scheme.highlight,
        )


class LayoutFrameResponse(BaseModel):
    path: Tuple[str, ...]
    rect: LayoutRectModel
    state: PanelState
    weight: float
    generated_at: datetime
    colors: ColorSchemeModel

    @classmethod
    def from_domain(cls, frame: LayoutFrame) -> "LayoutFrameResponse":
        return cls(
            path=frame.path,
            rect=LayoutRectModel.from_domain(frame.rect),
            state=frame.state,
            weight=frame.weight,
            generated_at=frame.generated_at,
            colors=ColorSchemeModel.from_domain(frame.colors),
        )


class DecayConfig(BaseModel):
    """Request payload for adjusting decay timing."""

    hold_seconds: float = Field(..., gt=0, description="Duration to hold full weight before decay begins")
    decay_seconds: float = Field(..., gt=0, description="Duration to fade from full weight to removal")

    @model_validator(mode="after")
    def validate_durations(self) -> "DecayConfig":
        if self.decay_seconds < 0.1:
            raise ValueError("decay_seconds must be at least 0.1 seconds")
        return self

    def to_timedelta(self) -> Tuple[timedelta, timedelta]:
        return timedelta(seconds=self.hold_seconds), timedelta(seconds=self.decay_seconds)


class DecayConfigResponse(BaseModel):
    hold_seconds: float
    decay_seconds: float


class PruneRequest(BaseModel):
    channel: str


__all__ = [
    "ColorSchemeModel",
    "DecayConfig",
    "DecayConfigResponse",
    "LayoutFrameResponse",
    "LayoutRectModel",
    "MessageIngress",
    "MessageIngressResponse",
    "MessageRecord",
    "PruneRequest",
]
