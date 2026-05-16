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

        # Pure read. Callers must invoke ``tree.tick(now)`` to advance simulated
        # time before generating — keeping render free of state evolution lets
        # the layout be reasoned about as a function of tree-at-time-T.

        frames: List[LayoutFrame] = []

        root = tree.root
        if not root.children:
            return frames

        root_rect = LayoutRect(x=0.0, y=0.0, width=1.0, height=1.0)
        self._populate_frames(root, root_rect, depth=0, frames=frames, timestamp=timestamp, tree=tree)
        return frames

    def _get_parent_fraction(self, depth: int, has_messages: bool) -> float:
        """Vertical share for a parent's own message strip.

        Only parents with their *own* messages take a strip. Empty parents
        are handled separately: a multi-child empty parent is emitted as a
        zero-strip grouping container (the client draws its border/label at
        the children's bounding box); a single-child empty parent collapses.
        """
        if not has_messages:
            return 0.0

        fraction = self._parent_fraction
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
                        state=node.state_at(timestamp),
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

        # An interior node falls into one of three cases:
        #  A. has its own messages → strip model: parent shows content above,
        #     children take the remainder.
        #  B. empty but groups >= 2 children → grouping container: emit the
        #     parent frame; children take the full rect. The client draws the
        #     parent border/label at the children's bounding box and nests
        #     them via the DOM, so no strip is carved (a thin strip races
        #     min_extent and disappears for realistic low-weight data).
        #  C. empty single-child / leaf → collapse: no parent frame, children
        #     take the full rect. No value boxing one thing.
        is_grouping = (
            include_self
            and not has_messages
            and self._show_empty_parents
            and len(children) >= 2
        )

        if include_self and has_messages and parent_fraction > 0:
            children_fraction = 1.0 - parent_fraction
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
                        state=node.state_at(timestamp),
                        weight=node.weight,
                        generated_at=timestamp,
                        colors=colors,
                    )
                )
        else:
            if is_grouping:
                colors = self._color_service.get_scheme_for_channel(node.path)
                frames.append(
                    LayoutFrame(
                        path=node.path,
                        rect=rect,
                        state=node.state_at(timestamp),
                        weight=node.weight,
                        generated_at=timestamp,
                        colors=colors,
                    )
                )
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


__all__ = ["LinearLayoutGenerator"]
