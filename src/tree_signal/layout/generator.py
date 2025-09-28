"""Simple layout generator producing placeholder rectangles for panels."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List

from tree_signal.core import ChannelNodeState, ChannelTreeService, LayoutFrame, LayoutRect, PanelState


class LinearLayoutGenerator:
    """Generate a vertical stack of panels sized proportionally by weight."""

    def __init__(self, min_height: float = 0.05) -> None:
        self._min_height = min_height

    def generate(self, tree: ChannelTreeService, *, timestamp: datetime | None = None) -> List[LayoutFrame]:
        """Produce layout frames for all non-root nodes."""

        timestamp = timestamp or datetime.now(tz=timezone.utc)
        nodes = [node for node in tree.iter_nodes() if node.path]
        if not nodes:
            return []

        total_weight = sum(max(node.weight, 0.0) for node in nodes)
        if total_weight <= 0:
            total_weight = float(len(nodes))

        frames: List[LayoutFrame] = []
        cursor_y = 0.0

        for node in nodes:
            weight_fraction = max(node.weight, 0.0) / total_weight
            height = max(weight_fraction, self._min_height)
            if cursor_y + height > 1.0:
                height = max(0.0, 1.0 - cursor_y)

            rect = LayoutRect(x=0.0, y=cursor_y, width=1.0, height=height)
            state = self._resolve_state(node=node, timestamp=timestamp)

            frames.append(
                LayoutFrame(
                    path=node.path,
                    rect=rect,
                    state=state,
                    weight=node.weight,
                    generated_at=timestamp,
                )
            )

            cursor_y = min(1.0, cursor_y + height)

        return frames

    def _resolve_state(self, node: ChannelNodeState, timestamp: datetime) -> PanelState:
        """Determine the panel state based on fade deadlines."""

        if node.fade_deadline is None:
            return PanelState.ACTIVE

        deadline = node.fade_deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)

        if timestamp >= deadline:
            return PanelState.FADING
        return PanelState.ACTIVE


__all__ = ["LinearLayoutGenerator"]
