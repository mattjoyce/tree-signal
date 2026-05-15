"""Hierarchical layout generator producing treemap-style rectangles."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from tree_signal.core import (
    ChannelNodeState,
    ChannelTreeService,
    ColorService,
    LayoutFrame,
    LayoutRect,
    PanelState,
)

from tree_signal.layouts.config import LinearLayoutConfig


class LinearLayoutGenerator:
    """Generate nested rectangles using alternating split orientation (slice-and-dice)."""

    def __init__(
        self,
        config: Optional[LinearLayoutConfig] = None,
        color_service: Optional[ColorService] = None,
    ) -> None:
        self._config = config or LinearLayoutConfig()
        self._color_service = color_service or ColorService()
        self._min_extent = self._config.min_extent
        self._parent_fraction = self._config.parent_fraction
        self._show_empty_parents = self._config.show_empty_parents
        self._depth_decay_factor = self._config.depth_decay_factor
        self._panel_gap = self._config.panel_gap

    def generate(self, tree: ChannelTreeService, *, timestamp: datetime | None = None) -> List[LayoutFrame]:
        """Produce layout frames for all nodes except the synthetic root."""

        timestamp = timestamp or datetime.now(tz=timezone.utc)

        # Apply weight decay first so layout reflects current fade state,
        # then prune anything that has fully aged out.
        tree.schedule_decay(timestamp)
        tree.cleanup_expired(timestamp)

        frames: List[LayoutFrame] = []

        root = tree.root
        if not root.children:
            return frames

        root_rect = LayoutRect(x=0.0, y=0.0, width=1.0, height=1.0)
        self._populate_frames(root, root_rect, depth=0, frames=frames, timestamp=timestamp, tree=tree)
        return frames

    def _get_parent_fraction(self, depth: int, has_messages: bool) -> float:
        """Calculate parent fraction based on config and depth."""
        if not has_messages and not self._show_empty_parents:
            return 0.0
        if not has_messages:
            return 0.0  # Empty parents always invisible

        fraction = self._parent_fraction

        # Apply depth decay if configured
        if self._depth_decay_factor > 0:
            fraction = max(0.0, fraction - (depth * self._depth_decay_factor))

        return fraction

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
                # Skip tiny panels
                if rect.width < self._min_extent or rect.height < self._min_extent:
                    return
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

        parent_fraction = self._get_parent_fraction(depth, has_messages)
        children_fraction = 1.0 - parent_fraction

        # Skip invisible parent panels
        should_render_parent = include_self and (has_messages or self._show_empty_parents)

        if should_render_parent and parent_fraction > 0:
            # Apply panel gap
            gap = self._panel_gap / 2
            parent_rect = LayoutRect(
                x=rect.x + gap,
                y=rect.y + gap,
                width=rect.width - gap * 2,
                height=parent_fraction * rect.height - gap,
            )
            children_rect = LayoutRect(
                x=rect.x + gap,
                y=rect.y + parent_fraction * rect.height,
                width=rect.width - gap * 2,
                height=children_fraction * rect.height - gap,
            )

            # Skip tiny panels
            if parent_rect.width >= self._min_extent and parent_rect.height >= self._min_extent:
                colors = self._color_service.get_scheme_for_channel(node.path)
                frames.append(
                    LayoutFrame(
                        path=node.path,
                        rect=parent_rect,
                        state=self._resolve_state(node, timestamp),
                        weight=node.weight,
                        generated_at=timestamp,
                        colors=colors,
                    )
                )
        else:
            children_rect = rect

        child_list = list(children)
        if not child_list:
            return

        # Alternate between horizontal and vertical splits based on depth
        horizontal = (depth % 2) == 0

        self._layout_children(
            child_list, children_rect, horizontal, depth, frames, timestamp, tree
        )

    def _layout_children(
        self,
        children: List[ChannelNodeState],
        rect: LayoutRect,
        horizontal: bool,
        depth: int,
        frames: List[LayoutFrame],
        timestamp: datetime,
        tree: ChannelTreeService,
    ) -> None:
        """Layout children within the given rectangle, splitting either horizontally or vertically."""

        # Calculate total weight for proportional sizing
        total_weight = sum(max(child.weight, 0.0) or 1.0 for child in children)
        if total_weight <= 0:
            total_weight = float(len(children))

        remaining = 1.0

        if horizontal:
            # Split along x-axis (side by side)
            cursor = rect.x
            for index, child in enumerate(children):
                weight = max(child.weight, 0.0) or 1.0
                fraction = weight / total_weight if total_weight else 0.0
                fraction = max(fraction, self._min_extent)

                if index == len(children) - 1:
                    fraction = remaining
                else:
                    fraction = min(fraction, remaining)

                width = fraction * rect.width
                child_rect = LayoutRect(
                    x=cursor,
                    y=rect.y,
                    width=width,
                    height=rect.height,
                )
                cursor += width
                remaining = max(0.0, remaining - fraction)

                self._populate_frames(
                    child, child_rect, depth=depth + 1, frames=frames, timestamp=timestamp, tree=tree
                )
        else:
            # Split along y-axis (stacked)
            cursor = rect.y
            for index, child in enumerate(children):
                weight = max(child.weight, 0.0) or 1.0
                fraction = weight / total_weight if total_weight else 0.0
                fraction = max(fraction, self._min_extent)

                if index == len(children) - 1:
                    fraction = remaining
                else:
                    fraction = min(fraction, remaining)

                height = fraction * rect.height
                child_rect = LayoutRect(
                    x=rect.x,
                    y=cursor,
                    width=rect.width,
                    height=height,
                )
                cursor += height
                remaining = max(0.0, remaining - fraction)

                self._populate_frames(
                    child, child_rect, depth=depth + 1, frames=frames, timestamp=timestamp, tree=tree
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
