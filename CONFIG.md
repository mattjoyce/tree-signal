# Tree Signal Configuration Guide

Tree Signal supports comprehensive configuration through TOML files, allowing you to customize server behavior, client dashboard appearance, and operational parameters.

## Configuration File Locations

Tree Signal searches for configuration files in the following order:

1. **Environment variable**: `TREE_SIGNAL_CONFIG=/path/to/config.toml`
2. **Docker mount**: `/app/data/config.toml` (recommended for containers)
3. **Current directory**: `./config.toml`
4. **User config**: `~/.config/tree-signal/config.toml`

If no configuration file is found, Tree Signal uses built-in defaults.

## Quick Start

Copy the example configuration and customize it:

```bash
cp config.toml.example config.toml
# Edit config.toml with your preferences
```

Restart the server to apply changes:

```bash
# Docker
docker restart tree-signal

# Local development
# Ctrl+C to stop, then:
uvicorn tree_signal.api.main:app --host 0.0.0.0 --port 8000
```

## Configuration Sections

### Server Configuration

Controls the HTTP server settings.

```toml
[server]
host = "0.0.0.0"  # Listen address (0.0.0.0 = all interfaces)
port = 8013        # HTTP port
```

**Common scenarios:**
- Production: `host = "0.0.0.0"` (accept external connections)
- Development: `host = "127.0.0.1"` (localhost only)

### Decay Configuration

Controls how panels fade and disappear over time.

```toml
[decay]
hold_seconds = 30.0   # Time at full brightness before fading
decay_seconds = 10.0  # Time to fade from full to removed
```

**Examples:**
- Fast decay (testing): `hold_seconds = 5.0`, `decay_seconds = 2.0`
- Slow decay (monitoring): `hold_seconds = 300.0`, `decay_seconds = 60.0`
- No decay: Set very high values like `hold_seconds = 86400.0` (1 day)

### History Configuration

Controls message retention per channel.

```toml
[history]
max_messages = 100  # Messages to keep per channel
```

Higher values use more memory but provide better history. Lower values reduce memory footprint.

### Cleanup Configuration

Controls the background cleanup task that removes expired panels.

```toml
[cleanup]
interval_seconds = 60.0  # How often to run cleanup
```

## Client Dashboard Configuration

The `[client]` section controls the web dashboard behavior and appearance.

### Basic Client Settings

```toml
[client]
# API base URL (empty = same origin as dashboard)
api_base_url = ""

# Auto-refresh interval in milliseconds
refresh_interval_ms = 5000

# Show debug metrics (weight, dimensions) on panels
show_debug = false

# Application version displayed in dashboard
version = "0.2.0"
```

**API Base URL scenarios:**
- Same-origin (default): `api_base_url = ""`
- External API: `api_base_url = "https://api.tree-signal.company.com"`
- Different port: `api_base_url = "http://localhost:8013"`

### Color Configuration

Controls panel color assignment and inheritance.

```toml
[client.colors]
assignment_mode = "increment"   # How colors are assigned
inheritance_mode = "unique"     # How child panels get colors
palette = null                  # Optional custom colors
```

**Assignment Modes:**

- `increment` (default): Sequential color assignment with maximum separation
  - First channel: 0° (red)
  - Second channel: 101° (green-ish)
  - Third channel: 202° (blue-ish)
  - Cycles through hue spectrum

- `hash`: Deterministic SHA256-based assignment
  - Same channel always gets same color
  - Consistent across server restarts
  - Good for persistent deployments

**Inheritance Modes:**

- `unique` (default): Every channel gets a distinct color
  - `app` = red
  - `app.frontend` = green
  - `app.backend` = blue

- `root`: Children inherit root channel's hue with slight variations
  - `app` = 0° (red)
  - `app.frontend` = 5° (red-orange)
  - `app.backend` = 10° (orange)
  - Creates color families

- `family`: All descendants share exact hue, vary by lightness
  - `app` = 0° hue, 15% lightness
  - `app.frontend` = 0° hue, 20% lightness
  - `app.backend` = 0° hue, 25% lightness
  - Strong visual hierarchy

**Custom Palettes:**

```toml
[client.colors]
assignment_mode = "increment"
palette = ["#003366", "#006699", "#3399CC", "#66CCFF"]
```

Overrides HSL generation with specific hex colors. Colors cycle when exhausted.

### UI Configuration

Controls dashboard layout and appearance.

```toml
[client.ui]
min_panel_size = 5.0                    # Minimum panel size (%)
panel_gap = 0.6                         # Gap between panels (%)
font_family = "Fira Code, monospace"    # Dashboard font
show_timestamps = true                  # Show message times
timestamp_format = "locale"             # Time display format
```

**Timestamp Formats:**

- `locale` (default): Browser locale format
  - Example: "3:45:12 PM" (US), "15:45:12" (Europe)

- `iso`: ISO 8601 format
  - Example: "2025-12-17T15:45:12.123Z"
  - Good for debugging, international consistency

- `relative`: Human-friendly relative time
  - Example: "5m ago", "2h ago", "3d ago"
  - Good for real-time monitoring

**Layout Tuning:**

- Tighter layout: `min_panel_size = 2.0`, `panel_gap = 0.3`
- Spacious layout: `min_panel_size = 8.0`, `panel_gap = 1.0`

## Configuration Precedence

Settings are applied in this order (later overrides earlier):

1. **Built-in defaults** (hardcoded fallbacks)
2. **Config file** (`config.toml`)
3. **Environment variables** (legacy: `COLOR_ASSIGNMENT_MODE`, `COLOR_INHERITANCE_MODE`)
4. **Client localStorage** (per-browser overrides)
5. **URL parameters** (per-session overrides)

### Client-Side Overrides

Users can override server config using:

**URL Parameters** (temporary):
```
http://localhost:8000/?refresh=1000&debug=true&api=http://custom:8013
```

**localStorage** (persistent per-browser):
```javascript
localStorage.setItem('tree-signal.refreshMs', '10000');
localStorage.setItem('tree-signal.showDebug', 'true');
```

## Example Configurations

### Corporate Deployment

```toml
[client]
api_base_url = "https://tree-signal.company.com"
refresh_interval_ms = 10000
show_debug = false

[client.colors]
assignment_mode = "increment"
inheritance_mode = "root"
palette = ["#003366", "#006699", "#3399CC", "#66CCFF"]

[client.ui]
font_family = "Roboto, sans-serif"
timestamp_format = "locale"

[decay]
hold_seconds = 120.0
decay_seconds = 30.0
```

### Development Environment

```toml
[client]
api_base_url = ""
refresh_interval_ms = 1000
show_debug = true

[client.ui]
show_timestamps = true
timestamp_format = "iso"

[decay]
hold_seconds = 5.0
decay_seconds = 2.0
```

### High-Traffic Monitoring

```toml
[client]
refresh_interval_ms = 2000

[client.colors]
assignment_mode = "hash"
inheritance_mode = "family"

[client.ui]
min_panel_size = 2.0
panel_gap = 0.3
timestamp_format = "relative"

[history]
max_messages = 50

[cleanup]
interval_seconds = 30.0
```

## Docker Configuration

Mount a custom config into the container:

```bash
docker run -d \
  --name tree-signal \
  -p 8013:8013 -p 8014:8014 \
  -v /path/to/config.toml:/app/data/config.toml \
  -v /mnt/user/appdata/tree-signal:/app/data \
  --restart unless-stopped \
  tree-signal
```

Or use environment variable:

```bash
docker run -d \
  --name tree-signal \
  -p 8013:8013 -p 8014:8014 \
  -e TREE_SIGNAL_CONFIG=/app/data/config.toml \
  -v /mnt/user/appdata/tree-signal:/app/data \
  --restart unless-stopped \
  tree-signal
```

## Troubleshooting

### Config not loading

**Check file location:**
```bash
# Docker
docker exec tree-signal ls -la /app/data/config.toml

# Local
ls -la ./config.toml
```

**Check logs:**
```bash
# Docker
docker logs tree-signal | grep -i config

# Local
# Look for "Warning: Failed to load config" messages
```

**Verify config syntax:**
```bash
# TOML syntax checker
python3 -c "import tomllib; tomllib.load(open('config.toml', 'rb'))"
```

### Changes not applying

Configuration is loaded at server startup. After editing `config.toml`, **restart the server**:

```bash
# Docker
docker restart tree-signal

# Local development
# Ctrl+C to stop server, then restart
uvicorn tree_signal.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Client not using server config

1. Check browser console (F12) for config fetch errors
2. Verify `/v1/client/config` endpoint:
   ```bash
   curl http://localhost:8000/v1/client/config | python3 -m json.tool
   ```
3. Clear browser localStorage:
   ```javascript
   localStorage.clear()
   ```
4. Hard refresh the dashboard (Ctrl+Shift+R)

## API Reference

### Get Client Configuration

```http
GET /v1/client/config
```

Returns the current client configuration as JSON.

**Response:**
```json
{
  "api_base_url": "",
  "refresh_interval_ms": 5000,
  "show_debug": false,
  "version": "0.2.0",
  "colors": {
    "assignment_mode": "increment",
    "inheritance_mode": "unique",
    "palette": null
  },
  "ui": {
    "min_panel_size": 5.0,
    "panel_gap": 0.6,
    "font_family": "Fira Code, monospace",
    "show_timestamps": true,
    "timestamp_format": "locale"
  }
}
```

## See Also

- [README.md](README.md) - Project overview and quick start
- [tree_signal_spec.md](tree_signal_spec.md) - API specification
- [config.toml.example](config.toml.example) - Full configuration example
