"""In-memory channel tree service used by the layout engine."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Iterable, Optional

from . import ChannelNodeState, ChannelPath, Message


class ChannelTreeService:
    """Maintains the hierarchical channel state and derived weights."""

    def __init__(self) -> None:
        self._root = ChannelNodeState(path=(), weight=0.0)
        self._hold = timedelta(seconds=10)
        self._decay = timedelta(seconds=5)

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
            node.schedule_fade(self._hold, self._decay)

    def configure_decay(self, hold: timedelta, decay: timedelta) -> None:
        """Update decay configuration used when scheduling fades."""

        self._hold = hold
        self._decay = decay

    def schedule_decay(self, now: datetime) -> None:
        """Apply decay semantics across the tree.

        Phase 1 placeholder: propagate fade deadlines, but do not modify weights yet.
        """

        for node in self.iter_nodes():
            if node.last_message_at is None or node.locked:
                continue
            node.schedule_fade(self._hold, self._decay)

    def prune(self, path: ChannelPath) -> None:
        """Remove a subtree rooted at the given path."""

        if not path:
            raise ValueError("Cannot prune the root node")

        parent = self.get_node(path[:-1])
        if parent is None:
            return

        segment = path[-1]
        try:
            removed = parent.children.pop(segment)
        except KeyError:
            return

        delta = removed.weight
        node = parent
        while node:
            node.weight = max(node.weight - delta, 0.0)
            if node.path:
                node = self.get_node(node.path[:-1])
            else:
                break

    def iter_nodes(self) -> Iterable[ChannelNodeState]:
        """Yield nodes in depth-first order for layout calculations."""

        stack: list[ChannelNodeState] = [self._root]
        while stack:
            node = stack.pop()
            yield node
            stack.extend(reversed(list(node.children.values())))

    def get_node(self, path: ChannelPath) -> Optional[ChannelNodeState]:
        """Return the node at the requested path if it exists."""

        node = self._root
        for segment in path:
            try:
                node = node.children[segment]
            except KeyError:
                return None
        return node

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
