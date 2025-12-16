"""
Color Palette Generator for Chat Interfaces

Generates visually distinct color schemes using hue rotation.
Each participant gets a monochromatic palette (background, border, normal, highlight).
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import colorsys


@dataclass
class ColorScheme:
    """A complete color scheme for one participant."""
    hue: int
    background: str
    border: str
    normal: str
    highlight: str
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for easy serialization."""
        return {
            'hue': self.hue,
            'background': self.background,
            'border': self.border,
            'normal': self.normal,
            'highlight': self.highlight
        }
    
    def __repr__(self) -> str:
        return f"ColorScheme(hue={self.hue}°, bg={self.background}, highlight={self.highlight})"


class ColorPaletteGenerator:
    """
    Generates distinct color palettes using hue rotation.
    
    The algorithm uses: (start + increment × n) % 360
    
    Using a prime increment (like 101, 103, 107) ensures maximum
    color separation and full coverage of the hue spectrum.
    """
    
    def __init__(self, increment: int = 101, start: int = 0):
        """
        Initialize the palette generator.
        
        Args:
            increment: Degrees to rotate for each new color (default: 101)
                      Prime numbers coprime to 360 work best (101, 103, 107, 109, 113)
            start: Starting hue in degrees (0-359, default: 0)
                   Use random.randint(0, 359) for random starting point
        """
        self.increment = increment
        self.start = start % 360  # Ensure within valid range
    
    def _hsl_to_hex(self, h: float, s: float, l: float) -> str:
        """
        Convert HSL values to hex color code.
        
        Args:
            h: Hue (0-360)
            s: Saturation (0-100)
            l: Lightness (0-100)
            
        Returns:
            Hex color string (e.g., '#1a2b3c')
        """
        # Normalize to 0-1 range for colorsys
        h_norm = h / 360.0
        s_norm = s / 100.0
        l_norm = l / 100.0
        
        # Convert to RGB
        r, g, b = colorsys.hls_to_rgb(h_norm, l_norm, s_norm)
        
        # Convert to 0-255 range and format as hex
        return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
    
    def _generate_scheme(self, hue: int) -> ColorScheme:
        """
        Generate a complete monochromatic color scheme for a given hue.
        
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
            highlight=self._hsl_to_hex(hue, 60, 85)
        )
    
    def get_palette(self, count: int) -> List[ColorScheme]:
        """
        Generate a list of distinct color schemes.
        
        Args:
            count: Number of color schemes to generate
            
        Returns:
            List of ColorScheme objects
            
        Example:
            >>> gen = ColorPaletteGenerator(increment=101, start=0)
            >>> palettes = gen.get_palette(count=5)
            >>> for i, scheme in enumerate(palettes):
            ...     print(f"User {i}: {scheme.highlight}")
        """
        schemes = []
        for i in range(count):
            hue = (self.start + (self.increment * i)) % 360
            schemes.append(self._generate_scheme(hue))
        return schemes
    
    def get_scheme_for_index(self, index: int) -> ColorScheme:
        """
        Get color scheme for a specific participant index.
        
        Useful when participants join dynamically.
        
        Args:
            index: Participant index (0-based)
            
        Returns:
            ColorScheme object
            
        Example:
            >>> gen = ColorPaletteGenerator()
            >>> user_42_colors = gen.get_scheme_for_index(42)
        """
        hue = (self.start + (self.increment * index)) % 360
        return self._generate_scheme(hue)
    
    def get_scheme_for_user_id(self, user_id: str) -> ColorScheme:
        """
        Get deterministic color scheme for a user ID.
        
        Uses a simple hash to convert user ID to an index,
        ensuring the same user always gets the same colors.
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            ColorScheme object
            
        Example:
            >>> gen = ColorPaletteGenerator()
            >>> alice_colors = gen.get_scheme_for_user_id("alice@example.com")
            >>> # Alice will always get the same colors
        """
        # Simple hash - for production, consider using hashlib
        index = hash(user_id) % 1000  # Limit to reasonable range
        return self.get_scheme_for_index(index)


# Convenience function for simple use cases
def get_color_palettes(count: int, increment: int = 101, start: int = 0) -> List[ColorScheme]:
    """
    Simple function to generate color palettes.
    
    Args:
        count: Number of color schemes to generate
        increment: Degrees to rotate for each color (default: 101)
        start: Starting hue (default: 0)
        
    Returns:
        List of ColorScheme objects
        
    Example:
        >>> palettes = get_color_palettes(count=8)
        >>> for palette in palettes:
        ...     print(palette.background, palette.highlight)
    """
    generator = ColorPaletteGenerator(increment=increment, start=start)
    return generator.get_palette(count)


# Preset increments (all prime and coprime to 360)
class Presets:
    """Recommended rotation increments for different use cases."""
    MAXIMUM_SPREAD = 101  # Best general-purpose choice
    LARGE_SPREAD = 103    # Alternative with similar properties
    WIDE_SPREAD = 107     # Even more dramatic jumps
    GOLDEN_ANGLE = 137.5  # Mathematical optimum (non-repeating)
    COMPLEMENTARY = 180   # Alternates opposite colors
    TRIADIC = 120         # Classic three-color harmony


if __name__ == "__main__":
    # Demo usage
    print("=== Color Palette Generator Demo ===\n")
    
    # Example 1: Generate palettes for 5 users
    print("Example 1: Five user color schemes")
    print("-" * 50)
    gen = ColorPaletteGenerator(increment=101, start=0)
    palettes = gen.get_palette(count=5)
    
    for i, scheme in enumerate(palettes):
        print(f"User {i}: {scheme}")
    
    print("\n" + "=" * 50 + "\n")
    
    # Example 2: Get colors for specific user
    print("Example 2: User-specific color scheme")
    print("-" * 50)
    alice_colors = gen.get_scheme_for_user_id("alice@example.com")
    print(f"Alice's colors: {alice_colors}")
    print(f"Always the same: {gen.get_scheme_for_user_id('alice@example.com')}")
    
    print("\n" + "=" * 50 + "\n")
    
    # Example 3: Random starting point
    print("Example 3: Random starting point")
    print("-" * 50)
    import random
    random_gen = ColorPaletteGenerator(increment=101, start=random.randint(0, 359))
    random_palettes = random_gen.get_palette(count=3)
    
    for i, scheme in enumerate(random_palettes):
        print(f"User {i}: hue={scheme.hue}°, highlight={scheme.highlight}")
    
    print("\n" + "=" * 50 + "\n")
    
    # Example 4: Export to dict for JSON
    print("Example 4: Export as dictionary")
    print("-" * 50)
    scheme = palettes[0]
    print(scheme.to_dict())
    
    print("\n" + "=" * 50 + "\n")
    
    # Example 5: Using convenience function
    print("Example 5: Simple convenience function")
    print("-" * 50)
    simple_palettes = get_color_palettes(count=3, increment=101, start=0)
    for i, palette in enumerate(simple_palettes):
        print(f"Palette {i}: {palette.highlight}")
