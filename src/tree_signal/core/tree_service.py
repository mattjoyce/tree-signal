"""In-memory channel tree service used by the layout engine."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, Optional

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
        """Add a message to the tree and update node weights."""

        timestamp = message.received_at
        node = self._root
        node.touch(timestamp=timestamp, weight_delta=weight_delta)

        for segment in message.channel_path:
            node = self._ensure_child(node=node, segment=segment)
            node.touch(timestamp=timestamp, weight_delta=weight_delta)

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

    def _ensure_child(self, node: ChannelNodeState, segment: str) -> ChannelNodeState:
        """Fetch or create a child node for the given segment."""

        try:
            return node.children[segment]
        except KeyError:
            child_path = (*node.path, segment)
            child = ChannelNodeState(path=child_path, weight=0.0)
            node.children[segment] = child
            return child


__all__ = ["ChannelTreeService"]
