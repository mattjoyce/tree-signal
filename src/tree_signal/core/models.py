"""Core domain models for the Tree Signal service."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Dict, Optional, Tuple

if TYPE_CHECKING:
    from .color_palette import ColorScheme

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
    lifespan_seconds: float = 30.0  # Default 30 second lifespan

    @property
    def expires_at(self) -> datetime:
        """Calculate when this message expires."""
        return self.received_at + timedelta(seconds=self.lifespan_seconds)


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
    colors: "ColorScheme"


@dataclass(slots=True)
class ChannelNodeState:
    """Runtime representation of a node in the channel tree."""

    path: ChannelPath
    weight: float
    last_message_at: Optional[datetime] = None
    fade_start: Optional[datetime] = None
    fade_deadline: Optional[datetime] = None
    decay_start_weight: Optional[float] = None
    locked: bool = False
    created_at: Optional[datetime] = None
    children: Dict[str, "ChannelNodeState"] = field(default_factory=dict)

    def touch(self, timestamp: datetime, weight_delta: float) -> None:
        """Update node activity in-place when a new message arrives."""

        self.last_message_at = timestamp
        self.weight = max(self.weight + weight_delta, 0.0)
        # New activity restarts the decay snapshot so the next fade window
        # measures from the freshly-touched weight, not the stale one.
        self.decay_start_weight = None

    def schedule_fade(self, hold: timedelta, decay: timedelta) -> None:
        """Set fade window based on hold and decay intervals."""

        if self.last_message_at is None:
            return
        self.fade_start = self.last_message_at + hold
        self.fade_deadline = self.fade_start + decay

    def state_at(self, now: datetime) -> "PanelState":
        """Return the panel's lifecycle state at ``now``.

        Lives on the node so the generator doesn't have to know the rules
        for what "fading" means — the node owns its own state semantics.
        """

        if self.fade_start is None or self.fade_deadline is None:
            return PanelState.ACTIVE
        if now < self.fade_start:
            return PanelState.ACTIVE
        if now < self.fade_deadline:
            return PanelState.FADING
        return PanelState.REMOVED

    def apply_decay(self, now: datetime) -> None:
        """Reduce weight linearly across the [fade_start, fade_deadline] window."""

        if self.fade_start is None or self.fade_deadline is None:
            return
        if now < self.fade_start:
            return
        if now >= self.fade_deadline:
            self.weight = 0.0
            self.decay_start_weight = None
            return
        if self.decay_start_weight is None:
            self.decay_start_weight = self.weight
        span = (self.fade_deadline - self.fade_start).total_seconds()
        # fade_deadline = fade_start + (positive) decay, so span > 0 by construction.
        # If that ever stops being true, fail loud rather than silently zero out.
        assert span > 0, "fade window invariant broken: fade_start must precede fade_deadline"
        remaining = (self.fade_deadline - now).total_seconds()
        fraction = max(0.0, min(1.0, remaining / span))
        self.weight = self.decay_start_weight * fraction


__all__ = [
    "ChannelNodeState",
    "ChannelPath",
    "LayoutFrame",
    "LayoutRect",
    "Message",
    "MessageSeverity",
    "PanelState",
]
