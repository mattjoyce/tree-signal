"""In-memory channel tree service used by the layout engine."""
from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Deque, Dict, Iterable, List, Optional

from .models import ChannelNodeState, ChannelPath, Message

MAX_HISTORY = 100


class ChannelTreeService:
    """Maintains the hierarchical channel state and derived weights."""

    def __init__(self) -> None:
        self._root = ChannelNodeState(path=(), weight=0.0)
        self._hold = timedelta(seconds=10)
        self._decay = timedelta(seconds=5)
        self._history: Dict[ChannelPath, Deque[Message]] = {}

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
            node = self._ensure_child(node=node, segment=segment, timestamp=timestamp)
            node.touch(timestamp=timestamp, weight_delta=weight_delta)
            node.schedule_fade(self._hold, self._decay)

        self._append_history(message)

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

    def cleanup_expired(self, now: datetime) -> None:
        """Remove expired messages and prune leaf nodes with no active messages."""
        # Clean up expired messages from history (but keep the history entry)
        for path, history in list(self._history.items()):
            # Remove only expired messages
            while history and history[0].expires_at <= now:
                history.popleft()

        # Only prune LEAF nodes (no children) with no messages AND created >10s ago
        from datetime import timedelta
        empty_node_lifespan = timedelta(seconds=10)
        paths_to_prune = []

        for node in list(self.iter_nodes()):
            if not node.path:  # Skip root
                continue

            # CRITICAL: Never prune if node has children
            if node.children:
                continue

            # Only prune leaf nodes with no messages that are old enough
            history = self.get_history(node.path)
            if not history and node.created_at:
                age = now - node.created_at
                if age >= empty_node_lifespan:
                    paths_to_prune.append(node.path)

        # Prune paths (bottom-up)
        for path in sorted(paths_to_prune, key=lambda p: len(p), reverse=True):
            try:
                self.prune(path)
            except ValueError:
                pass  # Ignore errors

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

        self._history.pop(path, None)

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

    def get_history(self, path: ChannelPath) -> List[Message]:
        """Return recent messages for the requested channel path."""

        return list(self._history.get(path, ()))

    def _append_history(self, message: Message) -> None:
        """Store a message in the bounded in-memory history."""

        history = self._history.setdefault(message.channel_path, deque(maxlen=MAX_HISTORY))
        history.append(message)

    def _ensure_child(self, node: ChannelNodeState, segment: str, timestamp: datetime) -> ChannelNodeState:
        """Fetch or create a child node for the given segment."""

        try:
            return node.children[segment]
        except KeyError:
            child_path = (*node.path, segment)
            child = ChannelNodeState(path=child_path, weight=0.0, created_at=timestamp)
            node.children[segment] = child
            return child


__all__ = ["ChannelTreeService", "MAX_HISTORY"]
