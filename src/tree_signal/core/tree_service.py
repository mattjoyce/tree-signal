"""In-memory channel tree service used by the layout engine."""
from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional

from . import ChannelNodeState, ChannelPath, Message


class ChannelTreeService:
    """Maintains the hierarchical channel state and derived weights."""

    def __init__(self) -> None:
        self._root = ChannelNodeState(path=(), weight=0.0)

    @property
    def root(self) -> ChannelNodeState:
        """Return the synthetic root node."""

        return self._root

    def ingest(self, message: Message, weight_delta: float = 1.0) -> None:
        """Add a message to the tree and update node weights.

        Phase 1 placeholder: real implementation will construct nodes on demand,
        adjust weights along the path, and record timestamps.
        """

        raise NotImplementedError("Channel ingestion not implemented yet")

    def schedule_decay(self, now: datetime) -> None:
        """Apply decay semantics across the tree.

        Placeholder for the lifecycle scheduler that will shrink inactive panels.
        """

        raise NotImplementedError("Decay scheduling not implemented yet")

    def prune(self, path: ChannelPath) -> None:
        """Remove a subtree rooted at the given path."""

        raise NotImplementedError("Pruning not implemented yet")

    def iter_nodes(self) -> Iterable[ChannelNodeState]:
        """Yield nodes in depth-first order for layout calculations."""

        raise NotImplementedError("Node iteration not implemented yet")

    def get_node(self, path: ChannelPath) -> Optional[ChannelNodeState]:
        """Return the node at the requested path if it exists."""

        raise NotImplementedError("Node lookup not implemented yet")


__all__ = ["ChannelTreeService"]
