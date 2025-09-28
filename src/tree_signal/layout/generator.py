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
        children = list(node.children.values())
        if not children:
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
            return

        orientation_horizontal = depth % 2 == 0

        segments = []
        include_self = bool(node.path)

        child_segments = []
        for child in children:
            if depth == 0:
                weight = 1.0
            else:
                weight = max(child.weight, 0.0) or 1.0
            child_segments.append((child, weight))

        if include_self:
            if child_segments:
                self_weight = min(weight for _, weight in child_segments)
            else:
                self_weight = max(node.weight, 0.0) or 1.0
            segments.append(("self", self_weight))

        segments.extend(child_segments)

        total_weight = sum(weight for _, weight in segments)
        if total_weight <= 0:
            total_weight = float(len(segments))

        remaining = 1.0
        cursor = rect.x if orientation_horizontal else rect.y
        self_rect: LayoutRect | None = None

        for index, (segment, weight) in enumerate(segments):
            raw_fraction = weight / total_weight if total_weight else 0.0
            fraction = max(raw_fraction, self._min_extent)

            if index == len(segments) - 1:
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

            if segment == "self":
                self_rect = child_rect
            else:
                self._populate_frames(segment, child_rect, depth=depth + 1, frames=frames, timestamp=timestamp)

        if node.path and self_rect is not None:
            frames.append(
                LayoutFrame(
                    path=node.path,
                    rect=self_rect,
                    state=self._resolve_state(node, timestamp),
                    weight=node.weight,
                    generated_at=timestamp,
                )
            )

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
