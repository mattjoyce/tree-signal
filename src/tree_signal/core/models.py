"""Core domain models for the Tree Signal service."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional, Tuple

ChannelPath = Tuple[str, ...]


class MessageSeverity(str, Enum):
    """Severity levels recognised by the message pipeline."""

    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class Message:
    """Incoming payload published to a hierarchical channel."""

    id: str
    channel_path: ChannelPath
    payload: str
    received_at: datetime
    severity: MessageSeverity = MessageSeverity.INFO
    metadata: Optional[Dict[str, str]] = None


class PanelState(str, Enum):
    """Lifecycle state for a panel within the layout."""

    ACTIVE = "active"
    FADING = "fading"
    REMOVED = "removed"


@dataclass(slots=True)
class LayoutRect:
    """Normalised rectangle describing panel placement."""

    x: float
    y: float
    width: float
    height: float


@dataclass(slots=True)
class LayoutFrame:
    """Computed layout data for a specific channel node."""

    path: ChannelPath
    rect: LayoutRect
    state: PanelState
    weight: float
    generated_at: datetime


@dataclass(slots=True)
class ChannelNodeState:
    """Runtime representation of a node in the channel tree."""

    path: ChannelPath
    weight: float
    last_message_at: Optional[datetime] = None
    fade_deadline: Optional[datetime] = None
    locked: bool = False
    children: Dict[str, "ChannelNodeState"] = field(default_factory=dict)

    def touch(self, timestamp: datetime, weight_delta: float) -> None:
        """Update node activity in-place when a new message arrives."""

        self.last_message_at = timestamp
        self.weight = max(self.weight + weight_delta, 0.0)

    def schedule_fade(self, hold: timedelta, decay: timedelta) -> None:
        """Set fade deadline based on hold and decay intervals."""

        if self.last_message_at is None:
            return
        self.fade_deadline = self.last_message_at + hold + decay


__all__ = [
    "ChannelNodeState",
    "ChannelPath",
    "LayoutFrame",
    "LayoutRect",
    "Message",
    "MessageSeverity",
    "PanelState",
]
