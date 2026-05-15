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
        self._max_weight: Optional[float] = 10.0
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
        self._apply_weight_cap(node)

        for segment in message.channel_path:
            node = self._ensure_child(node=node, segment=segment, timestamp=timestamp)
            node.touch(timestamp=timestamp, weight_delta=weight_delta)
            self._apply_weight_cap(node)
            node.schedule_fade(self._hold, self._decay)

        self._append_history(message)

    def configure_decay(self, hold: timedelta, decay: timedelta) -> None:
        """Update decay configuration used when scheduling fades."""

        self._hold = hold
        self._decay = decay

    def configure_max_weight(self, max_weight: Optional[float]) -> None:
        """Update the per-node weight cap. Pass None to disable."""

        if max_weight is not None and max_weight <= 0:
            raise ValueError("max_weight must be positive or None")
        self._max_weight = max_weight

    def _apply_weight_cap(self, node: ChannelNodeState) -> None:
        """Clamp a node's weight to ``_max_weight`` so busy channels do not swamp siblings."""

        if self._max_weight is not None and node.weight > self._max_weight:
            node.weight = self._max_weight

    def schedule_decay(self, now: datetime) -> None:
        """Refresh fade windows and linearly reduce weight inside the decay window."""

        for node in self.iter_nodes():
            if node.last_message_at is None or node.locked:
                continue
            node.schedule_fade(self._hold, self._decay)
            node.apply_decay(now)

    def tick(self, now: datetime) -> None:
        """Advance simulated time: apply decay, then prune what has fully aged out.

        Pulling this out of ``LinearLayoutGenerator.generate`` lets the layout
        be read as a function of the tree at a known moment, instead of
        secretly advancing the simulation as a side effect of rendering.
        """

        self.schedule_decay(now)
        self.cleanup_expired(now)

    EMPTY_NODE_LIFESPAN = timedelta(seconds=10)

    def cleanup_expired(self, now: datetime) -> None:
        """Drop aged-out messages, then prune leaves that have nothing left to show."""

        self._expire_messages(now)
        self._prune_empty_leaves(now)

    def _expire_messages(self, now: datetime) -> None:
        """Remove messages whose ``expires_at`` is in the past from history queues."""

        for history in self._history.values():
            while history and history[0].expires_at <= now:
                history.popleft()

    def _prune_empty_leaves(self, now: datetime) -> None:
        """Prune leaf nodes that have no messages and have aged past EMPTY_NODE_LIFESPAN."""

        paths_to_prune: List[ChannelPath] = []
        for node in list(self.iter_nodes()):
            if not node.path:
                continue  # never prune the synthetic root
            if node.children:
                continue  # never prune a node that still has descendants
            if node.created_at is None:
                continue
            if self.get_history(node.path):
                continue
            if now - node.created_at < self.EMPTY_NODE_LIFESPAN:
                continue
            paths_to_prune.append(node.path)

        # Bottom-up so a parent never disappears before its children.
        # ``prune`` cannot raise here because the loop above already excludes
        # the root path — if that invariant ever breaks, let it surface.
        for path in sorted(paths_to_prune, key=lambda p: len(p), reverse=True):
            self.prune(path)

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
