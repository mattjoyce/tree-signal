# Color Palette Feature Design

## Overview
Each channel/container gets its own distinct 4-color palette (background, border, normal, highlight) for visual differentiation.

**Status:** Design document
**Date:** 2025-12-16

---

## Color Assignment Strategy

### Configuration
**Environment Variable:** `COLOR_ASSIGNMENT_MODE`
**Default:** `increment`
**Options:** `increment` | `hash`

```env
# .env
COLOR_ASSIGNMENT_MODE=increment  # Default: sequential colors
# COLOR_ASSIGNMENT_MODE=hash      # Alternative: deterministic hash-based
```

### Increment Mode (Default)

Channels get colors in order they first appear:

```
First channel:  index=0 → hue=0°   → blue tones
Second channel: index=1 → hue=101° → green tones
Third channel:  index=2 → hue=202° → red/pink tones
Fourth channel: index=3 → hue=303° → purple tones
...
```

**Behavior:**
- Maintains in-memory map: `{"this.that.other": 0, "app.auth": 1, ...}`
- Next index counter increments on new channel
- Guarantees visually distinct adjacent channels
- **Lost on server restart** (ephemeral like messages)

**Example:**
```bash
./tree-signal --channel app.auth "login"        # Gets hue 0°
./tree-signal --channel app.db "connected"      # Gets hue 101°
./tree-signal --channel monitor.cpu "high"      # Gets hue 202°
```

### Hash Mode (Alternative)

Channels get deterministic colors based on path hash:

```python
import hashlib

def channel_to_index(channel: str) -> int:
    hash_bytes = hashlib.sha256(channel.encode()).digest()
    return int.from_bytes(hash_bytes[:4], 'big') % 1000
```

**Behavior:**
- Same channel always gets same color (across restarts)
- No state to track
- Colors feel "random" but are stable

**Example:**
```bash
./tree-signal --channel app.auth "login"        # Always gets hue X°
# Server restart
./tree-signal --channel app.auth "login"        # Still gets hue X°
```

---

## Color Palette Specification

Each channel gets 4 colors using monochromatic scheme (same hue, varying lightness):

| Color      | HSL Formula          | Lightness | Usage              |
|------------|----------------------|-----------|-------------------- |
| Background | HSL(hue, 35%, 15%)   | 15%       | Panel background   |
| Border     | HSL(hue, 40%, 30%)   | 30%       | Panel border       |
| Normal     | HSL(hue, 50%, 65%)   | 65%       | Text/content       |
| Highlight  | HSL(hue, 60%, 85%)   | 85%       | Headers/accents    |

**Hue Calculation:**
```python
hue = (start + increment * index) % 360

# Defaults:
start = 0        # Starting hue
increment = 101  # Prime number for maximum color separation
```

---

## Implementation Plan

### Backend Changes

#### 1. Port Color Generator
**File:** `src/tree_signal/core/color_palette.py` (new)

Port from `colour-pallete.py`:
- `ColorScheme` dataclass
- `ColorPaletteGenerator` class
- HSL to hex conversion
- Both increment and hash modes

#### 2. Add Color Service
**File:** `src/tree_signal/core/color_service.py` (new)

```python
class ColorService:
    """Manages color assignment for channels."""

    def __init__(self, mode: str = "increment"):
        self.mode = mode  # "increment" or "hash"
        self.generator = ColorPaletteGenerator(increment=101, start=0)
        self.channel_index_map: Dict[str, int] = {}
        self.next_index: int = 0

    def get_scheme_for_channel(self, channel_path: Tuple[str, ...]) -> ColorScheme:
        """Get color scheme for a channel path."""
        channel = ".".join(channel_path)

        if self.mode == "increment":
            return self._get_incremental_scheme(channel)
        else:
            return self._get_hash_scheme(channel)

    def _get_incremental_scheme(self, channel: str) -> ColorScheme:
        if channel not in self.channel_index_map:
            self.channel_index_map[channel] = self.next_index
            self.next_index += 1

        index = self.channel_index_map[channel]
        return self.generator.get_scheme_for_index(index)

    def _get_hash_scheme(self, channel: str) -> ColorScheme:
        import hashlib
        hash_bytes = hashlib.sha256(channel.encode()).digest()
        index = int.from_bytes(hash_bytes[:4], 'big') % 1000
        return self.generator.get_scheme_for_index(index)
```

#### 3. Update Models
**File:** `src/tree_signal/core/models.py`

Add ColorScheme to exports:
```python
@dataclass(frozen=True, slots=True)
class ColorScheme:
    """Color palette for a channel."""
    hue: int
    background: str
    border: str
    normal: str
    highlight: str
```

#### 4. Update Layout Generator
**File:** `src/tree_signal/layout/generator.py`

```python
class LinearLayoutGenerator:
    def __init__(self, min_extent: float = 0.02, color_service: ColorService = None):
        self._min_extent = min_extent
        self._color_service = color_service or ColorService()

    def generate(self, tree: ChannelTreeService, ...) -> List[LayoutFrame]:
        # ... existing code ...
        # When creating frames, add colors
```

#### 5. Update API Schema
**File:** `src/tree_signal/api/schemas.py`

```python
class ColorSchemeModel(BaseModel):
    hue: int
    background: str
    border: str
    normal: str
    highlight: str

class LayoutFrameResponse(BaseModel):
    path: Tuple[str, ...]
    rect: LayoutRectModel
    state: PanelState
    weight: float
    generated_at: datetime
    colors: ColorSchemeModel  # NEW
```

#### 6. Configuration
**File:** `src/tree_signal/api/main.py` or config module

```python
import os

COLOR_ASSIGNMENT_MODE = os.getenv("COLOR_ASSIGNMENT_MODE", "increment")

# Initialize services
color_service = ColorService(mode=COLOR_ASSIGNMENT_MODE)
layout_generator = LinearLayoutGenerator(color_service=color_service)
```

### Frontend Changes

#### 1. Receive Colors
**File:** `client/app.js`

Layout frames now include `colors`:
```javascript
{
  "path": ["this", "that", "other"],
  "rect": {...},
  "state": "active",
  "weight": 1.0,
  "colors": {
    "hue": 101,
    "background": "#1a2b1c",
    "border": "#2d4a2f",
    "normal": "#7ab87d",
    "highlight": "#c8ecc9"
  }
}
```

#### 2. Apply Colors to Panels
**File:** `client/app.js` (renderLayout function)

```javascript
// In renderLayout, when creating cell:
const cell = document.createElement("div");
cell.className = `layout-cell state-${frame.state.toLowerCase()}`;

// Apply color scheme using CSS custom properties
if (frame.colors) {
  cell.style.setProperty('--channel-bg', frame.colors.background);
  cell.style.setProperty('--channel-border', frame.colors.border);
  cell.style.setProperty('--channel-normal', frame.colors.normal);
  cell.style.setProperty('--channel-highlight', frame.colors.highlight);
}
```

#### 3. Update CSS
**File:** `client/index.html` or `client/style.css`

```css
.layout-cell {
  /* Use CSS custom properties */
  background-color: var(--channel-bg, #1a1b26);
  border: 2px solid var(--channel-border, #414868);
  color: var(--channel-normal, #a9b1d6);
}

.layout-cell header {
  background-color: var(--channel-border, #414868);
  color: var(--channel-highlight, #7aa2f7);
}

.layout-cell .snippet {
  background-color: var(--channel-bg, #1a1b26);
  color: var(--channel-normal, #a9b1d6);
}

.layout-cell.state-fading {
  opacity: 0.5;
}
```

---

## Environment Configuration

### .env.example
```env
# Color Assignment Mode
# - increment: Sequential colors (first channel=hue 0°, second=101°, etc.)
# - hash: Deterministic hash-based (same channel always same color)
COLOR_ASSIGNMENT_MODE=increment
```

### .env (user's actual config)
```env
COLOR_ASSIGNMENT_MODE=increment
```

---

## Examples

### Example 1: Three Channels (Increment Mode)

```bash
# Terminal
./tree-signal --channel app.auth "login successful"
./tree-signal --channel app.db "connected"
./tree-signal --channel monitor.cpu "usage: 45%"
```

**Result:**
- `app.auth`: Hue 0° (blue) → bg=#0d1a1a, border=#1a3333, normal=#4d9999, highlight=#b3e6e6
- `app.db`: Hue 101° (green) → bg=#1a1d0d, border=#334a1a, normal=#99b84d, highlight=#e6eeb3
- `monitor.cpu`: Hue 202° (red) → bg=#1a0d11, border=#331a22, normal=#b84d6b, highlight=#eeb3c4

### Example 2: Same Channel Multiple Messages

```bash
./tree-signal --channel app.auth "login successful"
./tree-signal --channel app.auth "logout"
./tree-signal --channel app.auth "session expired"
```

**Result:**
- All messages in `app.auth` panel
- All use same color scheme (hue 0°)
- Panel accumulates messages with consistent colors

---

## Future Enhancements

1. **Persistence:** Save channel→index map to disk for consistent colors across restarts
2. **Custom Palettes:** Allow user-defined color schemes per channel
3. **Color Profiles:** Light mode vs dark mode palettes
4. **Accessibility:** WCAG contrast ratio validation
5. **Color Reset API:** Endpoint to reset color assignments

---

## Open Questions

1. Should locked panels have different color treatment?
2. Should severity (debug/info/warn/error) affect colors?
3. Should parent containers inherit colors from children or have their own?
4. Should we persist the channel→index map, or accept ephemeral colors?

---

## Testing Checklist

- [ ] Increment mode assigns sequential colors
- [ ] Hash mode gives deterministic colors
- [ ] Same channel always gets same color within session
- [ ] Colors are visually distinct (adjacent hues separated by 101°)
- [ ] CSS custom properties apply correctly
- [ ] Works with panel decay/fade states
- [ ] Environment variable switching works
- [ ] Default to increment mode when not configured
