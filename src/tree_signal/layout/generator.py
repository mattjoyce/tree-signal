"""Hierarchical layout generator producing treemap-style rectangles."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Tuple

from tree_signal.core import ChannelNodeState, ChannelTreeService, LayoutFrame, LayoutRect, PanelState


class LinearLayoutGenerator:
    """Generate nested rectangles by alternating split orientation per depth."""

    def __init__(self, min_extent: float = 0.02) -> None:
        self._min_extent = min_extent

    def generate(self, tree: ChannelTreeService, *, timestamp: datetime | None = None) -> List[LayoutFrame]:
        """Produce layout frames for all nodes except the synthetic root."""

        timestamp = timestamp or datetime.now(tz=timezone.utc)
        frames: List[LayoutFrame] = []

        root = tree.root
        if not root.children:
            return frames

        root_rect = LayoutRect(x=0.0, y=0.0, width=1.0, height=1.0)
        self._populate_frames(root, root_rect, depth=0, frames=frames, timestamp=timestamp)
        return frames

    def _populate_frames(
        self,
        node: ChannelNodeState,
        rect: LayoutRect,
        *,
        depth: int,
        frames: List[LayoutFrame],
        timestamp: datetime,
    ) -> None:
        if node.path:
            frames.append(
                LayoutFrame(
                    path=node.path,
                    rect=rect,
                    state=self._resolve_state(node, timestamp),
                    weight=node.weight,
                    generated_at=timestamp,
                )
            )

        children = list(node.children.values())
        if not children:
            return

        orientation_horizontal = depth % 2 == 0
        if depth == 0:
            weights = [1.0 for _ in children]
        else:
            weights = [max(child.weight, 0.0) for child in children]

        total_weight = sum(weights)
        if total_weight <= 0:
            total_weight = float(len(children))

        remaining = 1.0
        cursor = rect.x if orientation_horizontal else rect.y

        for index, (child, weight) in enumerate(zip(children, weights)):
            raw_fraction = weight / total_weight if total_weight else 0.0
            fraction = max(raw_fraction, self._min_extent)

            if index == len(children) - 1:
                fraction = remaining
            else:
                fraction = min(fraction, remaining)

            if orientation_horizontal:
                width = fraction * rect.width
                child_rect = LayoutRect(
                    x=cursor,
                    y=rect.y,
                    width=width,
                    height=rect.height,
                )
                cursor += width
            else:
                height = fraction * rect.height
                child_rect = LayoutRect(
                    x=rect.x,
                    y=cursor,
                    width=rect.width,
                    height=height,
                )
                cursor += height

            remaining = max(0.0, remaining - fraction)
            self._populate_frames(child, child_rect, depth=depth + 1, frames=frames, timestamp=timestamp)

    def _resolve_state(self, node: ChannelNodeState, timestamp: datetime) -> PanelState:
        deadline = node.fade_deadline
        if deadline is None:
            return PanelState.ACTIVE

        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)

        if timestamp >= deadline:
            return PanelState.FADING
        return PanelState.ACTIVE


__all__ = ["LinearLayoutGenerator"]
