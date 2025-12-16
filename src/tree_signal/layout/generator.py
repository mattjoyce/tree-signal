"""Hierarchical layout generator producing treemap-style rectangles."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Tuple

from tree_signal.core import (
    ChannelNodeState,
    ChannelTreeService,
    ColorService,
    LayoutFrame,
    LayoutRect,
    PanelState,
)


class LinearLayoutGenerator:
    """Generate nested rectangles by alternating split orientation per depth."""

    def __init__(self, min_extent: float = 0.02, color_service: ColorService | None = None) -> None:
        self._min_extent = min_extent
        self._color_service = color_service or ColorService()

    def generate(self, tree: ChannelTreeService, *, timestamp: datetime | None = None) -> List[LayoutFrame]:
        """Produce layout frames for all nodes except the synthetic root."""

        timestamp = timestamp or datetime.now(tz=timezone.utc)

        # Clean up expired messages before generating layout
        tree.cleanup_expired(timestamp)

        frames: List[LayoutFrame] = []

        root = tree.root
        if not root.children:
            return frames

        root_rect = LayoutRect(x=0.0, y=0.0, width=1.0, height=1.0)
        self._populate_frames(root, root_rect, depth=0, frames=frames, timestamp=timestamp, tree=tree)
        return frames

    def _populate_frames(
        self,
        node: ChannelNodeState,
        rect: LayoutRect,
        *,
        depth: int,
        frames: List[LayoutFrame],
        timestamp: datetime,
        tree: ChannelTreeService,
    ) -> None:
        children = list(node.children.values())
        if not children:
            if node.path:
                colors = self._color_service.get_scheme_for_channel(node.path)
                frames.append(
                    LayoutFrame(
                        path=node.path,
                        rect=rect,
                        state=self._resolve_state(node, timestamp),
                        weight=node.weight,
                        generated_at=timestamp,
                        colors=colors,
                    )
                )
            return

        include_self = bool(node.path)

        # Determine parent size based on whether it has messages
        history = tree.get_history(node.path) if include_self else []
        has_messages = len(history) > 0

        # Parent gets 50% height if it has messages, 20% if empty (greedy children)
        parent_fraction = 0.5 if has_messages else 0.2
        children_fraction = 1.0 - parent_fraction

        self_rect: LayoutRect | None = None

        if include_self:
            # Parent always takes full width, adaptive height at top
            self_rect = LayoutRect(
                x=rect.x,
                y=rect.y,
                width=rect.width,
                height=parent_fraction * rect.height,
            )
            # Children get remaining height below parent
            children_rect = LayoutRect(
                x=rect.x,
                y=rect.y + parent_fraction * rect.height,
                width=rect.width,
                height=children_fraction * rect.height,
            )

            colors = self._color_service.get_scheme_for_channel(node.path)
            frames.append(
                LayoutFrame(
                    path=node.path,
                    rect=self_rect,
                    state=self._resolve_state(node, timestamp),
                    weight=node.weight,
                    generated_at=timestamp,
                    colors=colors,
                )
            )
        else:
            # No parent panel, children get full rect
            children_rect = rect

        # Now layout children within children_rect - always split horizontally
        child_list = list(children)
        if not child_list:
            return

        # Split children horizontally (side by side)
        total_weight = sum(max(child.weight, 0.0) or 1.0 for child in child_list)
        if total_weight <= 0:
            total_weight = float(len(child_list))

        remaining = 1.0
        cursor = children_rect.x

        for index, child in enumerate(child_list):
            if depth == 0:
                weight = 1.0
            else:
                weight = max(child.weight, 0.0) or 1.0

            raw_fraction = weight / total_weight if total_weight else 0.0
            fraction = max(raw_fraction, self._min_extent)

            if index == len(child_list) - 1:
                fraction = remaining
            else:
                fraction = min(fraction, remaining)

            width = fraction * children_rect.width
            child_rect = LayoutRect(
                x=cursor,
                y=children_rect.y,
                width=width,
                height=children_rect.height,
            )
            cursor += width

            remaining = max(0.0, remaining - fraction)
            self._populate_frames(child, child_rect, depth=depth + 1, frames=frames, timestamp=timestamp, tree=tree)

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
