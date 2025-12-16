"""Color palette generator for channel visualization.

Generates visually distinct color schemes using hue rotation.
Each channel gets a monochromatic palette (background, border, normal, highlight).
"""
from __future__ import annotations

import colorsys
import hashlib
from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True, slots=True)
class ColorScheme:
    """A complete color scheme for one channel."""

    hue: int
    background: str
    border: str
    normal: str
    highlight: str

    def to_dict(self) -> Dict[str, str | int]:
        """Convert to dictionary for serialization."""
        return {
            "hue": self.hue,
            "background": self.background,
            "border": self.border,
            "normal": self.normal,
            "highlight": self.highlight,
        }


class ColorPaletteGenerator:
    """Generates distinct color palettes using hue rotation.

    The algorithm uses: (start + increment × n) % 360

    Using a prime increment (like 101) ensures maximum color separation
    and full coverage of the hue spectrum.
    """

    def __init__(self, increment: int = 101, start: int = 0) -> None:
        """Initialize the palette generator.

        Args:
            increment: Degrees to rotate for each new color (default: 101)
                      Prime numbers coprime to 360 work best (101, 103, 107, 109, 113)
            start: Starting hue in degrees (0-359, default: 0)
        """
        self.increment = increment
        self.start = start % 360

    def _hsl_to_hex(self, h: float, s: float, l: float) -> str:
        """Convert HSL values to hex color code.

        Args:
            h: Hue (0-360)
            s: Saturation (0-100)
            l: Lightness (0-100)

        Returns:
            Hex color string (e.g., '#1a2b3c')
        """
        h_norm = h / 360.0
        s_norm = s / 100.0
        l_norm = l / 100.0

        r, g, b = colorsys.hls_to_rgb(h_norm, l_norm, s_norm)

        return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"

    def _generate_scheme(self, hue: int) -> ColorScheme:
        """Generate a complete monochromatic color scheme for a given hue.

        Creates a dark-mode friendly palette with:
        - Dark background (15% lightness)
        - Medium border (30% lightness)
        - Readable normal text (65% lightness)
        - Bright highlight (85% lightness)

        Args:
            hue: Base hue (0-359)

        Returns:
            ColorScheme object with all colors
        """
        return ColorScheme(
            hue=hue,
            background=self._hsl_to_hex(hue, 35, 15),
            border=self._hsl_to_hex(hue, 40, 30),
            normal=self._hsl_to_hex(hue, 50, 65),
            highlight=self._hsl_to_hex(hue, 60, 85),
        )

    def get_scheme_for_index(self, index: int) -> ColorScheme:
        """Get color scheme for a specific index.

        Args:
            index: Channel index (0-based)

        Returns:
            ColorScheme object
        """
        hue = (self.start + (self.increment * index)) % 360
        return self._generate_scheme(hue)

    def get_scheme_for_hash(self, channel: str) -> ColorScheme:
        """Get deterministic color scheme for a channel using hash.

        Uses SHA256 hash to ensure the same channel always gets the same colors.

        Args:
            channel: Channel identifier string

        Returns:
            ColorScheme object
        """
        hash_bytes = hashlib.sha256(channel.encode()).digest()
        index = int.from_bytes(hash_bytes[:4], "big") % 1000
        return self.get_scheme_for_index(index)


class ColorService:
    """Manages color assignment for channels."""

    def __init__(self, mode: str = "increment", inheritance_mode: str = "unique") -> None:
        """Initialize the color service.

        Args:
            mode: Assignment mode - "increment" (sequential) or "hash" (deterministic)
            inheritance_mode: Color inheritance - "unique", "root", or "family"
        """
        self.mode = mode
        self.inheritance_mode = inheritance_mode
        self.generator = ColorPaletteGenerator(increment=101, start=0)
        self.channel_index_map: Dict[str, int] = {}
        self.root_index_map: Dict[str, int] = {}
        self.next_index: int = 0
        self.next_root_index: int = 0

    def get_scheme_for_channel(self, channel_path: Tuple[str, ...]) -> ColorScheme:
        """Get color scheme for a channel path.

        Args:
            channel_path: Tuple of channel segments (e.g., ("this", "that", "other"))

        Returns:
            ColorScheme object with background, border, normal, highlight colors
        """
        if self.inheritance_mode == "root":
            return self._get_root_inherited_scheme(channel_path)
        elif self.inheritance_mode == "family":
            return self._get_family_scheme(channel_path)
        else:  # unique
            channel = ".".join(channel_path)
            if self.mode == "increment":
                return self._get_incremental_scheme(channel)
            else:
                return self._get_hash_scheme(channel)

    def _get_incremental_scheme(self, channel: str) -> ColorScheme:
        """Get color scheme using sequential index assignment."""
        if channel not in self.channel_index_map:
            self.channel_index_map[channel] = self.next_index
            self.next_index += 1

        index = self.channel_index_map[channel]
        return self.generator.get_scheme_for_index(index)

    def _get_hash_scheme(self, channel: str) -> ColorScheme:
        """Get color scheme using deterministic hash."""
        return self.generator.get_scheme_for_hash(channel)

    def _get_root_inherited_scheme(self, channel_path: Tuple[str, ...]) -> ColorScheme:
        """Get color scheme with root-based inheritance.

        Root channels get distinct colors, children get slight hue variations.
        Example: prod=0°, prod.api=5°, prod.db=10°
        """
        if not channel_path:
            return self.generator.get_scheme_for_index(0)

        root = channel_path[0]
        depth = len(channel_path)

        # Assign color to root channel
        if root not in self.root_index_map:
            if self.mode == "increment":
                self.root_index_map[root] = self.next_root_index
                self.next_root_index += 1
            else:  # hash mode
                hash_bytes = hashlib.sha256(root.encode()).digest()
                self.root_index_map[root] = int.from_bytes(hash_bytes[:4], "big") % 1000

        root_index = self.root_index_map[root]

        # Root gets base hue, children get +5° per level
        hue_offset = (depth - 1) * 5
        modified_index = root_index + (hue_offset // self.generator.increment)

        base_hue = (self.generator.start + (self.generator.increment * root_index)) % 360
        final_hue = (base_hue + hue_offset) % 360

        return self.generator._generate_scheme(final_hue)

    def _get_family_scheme(self, channel_path: Tuple[str, ...]) -> ColorScheme:
        """Get color scheme with family-based inheritance.

        Channels inherit parent's hue but vary lightness by depth.
        Example: prod=50% light, prod.api=60% light, prod.api.users=70% light
        """
        if not channel_path:
            return self.generator.get_scheme_for_index(0)

        root = channel_path[0]
        depth = len(channel_path)

        # Assign base hue to root channel
        if root not in self.root_index_map:
            if self.mode == "increment":
                self.root_index_map[root] = self.next_root_index
                self.next_root_index += 1
            else:  # hash mode
                hash_bytes = hashlib.sha256(root.encode()).digest()
                self.root_index_map[root] = int.from_bytes(hash_bytes[:4], "big") % 1000

        root_index = self.root_index_map[root]
        base_hue = (self.generator.start + (self.generator.increment * root_index)) % 360

        # Vary lightness by depth: 15%→25%→35% for bg, 65%→70%→75% for normal
        lightness_offset = (depth - 1) * 5

        # Create custom scheme with adjusted lightness
        bg_light = min(15 + lightness_offset, 25)
        border_light = min(30 + lightness_offset, 40)
        normal_light = min(65 + lightness_offset, 80)
        highlight_light = min(85 + lightness_offset, 95)

        return ColorScheme(
            hue=base_hue,
            background=self.generator._hsl_to_hex(base_hue, 35, bg_light),
            border=self.generator._hsl_to_hex(base_hue, 40, border_light),
            normal=self.generator._hsl_to_hex(base_hue, 50, normal_light),
            highlight=self.generator._hsl_to_hex(base_hue, 60, highlight_light),
        )


__all__ = ["ColorScheme", "ColorPaletteGenerator", "ColorService"]
