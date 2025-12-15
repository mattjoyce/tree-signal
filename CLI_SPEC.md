# Tree Signal CLI Tool Specification

## Purpose
Provide a lightweight command-line tool that reads log streams from stdin and routes them to a Tree Signal API server, enabling real-time log visualization through hierarchical channel routing.

## Primary Use Case
```bash
tail -f /var/log/app.log | tree-signal --channel myapp.logs
journalctl -fu myservice | tree-signal --config production
docker logs -f container | tree-signal --channel docker.container
```

## Command-Line Interface

### Basic Syntax
```bash
tree-signal [OPTIONS]
```

### Required Behavior
- Read from stdin line-by-line
- Route each line to Tree Signal API based on routing rules
- Continue until stdin closes or interrupted (Ctrl+C)
- Exit gracefully on SIGINT/SIGTERM

### Command-Line Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--channel CHANNEL` | `-c` | (required if no config) | Target channel path (e.g., `myapp.api.auth`) |
| `--config PATH` | | `~/.config/tree-signal/config.yaml` | Path to configuration file |
| `--api URL` | `-a` | `http://localhost:8013` | Tree Signal API base URL |
| `--api-key KEY` | `-k` | (none) | API authentication key (or use env: `TREE_SIGNAL_API_KEY`) |
| `--severity LEVEL` | `-s` | `info` | Default severity: `debug`, `info`, `warning`, `error`, `critical` |
| `--batch-size N` | `-b` | `1` | Batch N messages before sending (reduces API calls) |
| `--batch-interval MS` | | `1000` | Max milliseconds to wait before flushing batch |
| `--rate-limit N` | `-r` | `0` (unlimited) | Max messages per second (0 = unlimited) |
| `--retry COUNT` | | `3` | Number of retries on API failure |
| `--retry-delay MS` | | `1000` | Base delay between retries (exponential backoff) |
| `--quiet` | `-q` | `false` | Suppress informational output to stderr |
| `--debug` | | `false` | Enable debug logging to stderr |
| `--dry-run` | | `false` | Parse and route but don't send to API (print to stdout) |
| `--no-config` | | `false` | Ignore config file, use CLI args only |

### Environment Variables
- `TREE_SIGNAL_API_KEY` - API key if not provided via `--api-key`
- `TREE_SIGNAL_API_URL` - API URL if not provided via `--api`
- `TREE_SIGNAL_CONFIG` - Config file path if not provided via `--config`

### Exit Codes
- `0` - Normal exit (stdin closed cleanly)
- `1` - Configuration error (invalid config, missing required args)
- `2` - API connection error (cannot reach server after retries)
- `3` - Authentication error (invalid API key)
- `130` - Interrupted by user (SIGINT)

## Configuration Precedence

Settings are resolved in this order (lowest to highest priority):

```
1. Built-in defaults (hardcoded in the tool)
   ↓
2. Config file (~/.config/tree-signal/config.yaml)
   ↓
3. Environment variables (TREE_SIGNAL_*)
   ↓
4. CLI arguments (--flag values)
```

**Higher priority values override lower priority values.**

### Precedence Examples

**Example 1: API URL Resolution**
```bash
# Built-in default:           http://localhost:8013
# Config sets:                http://prod-server:8013
# Env variable overrides:     export TREE_SIGNAL_API_URL="http://staging:8013"
# CLI arg wins:               tree-signal --api http://dev:8013
# Final result:               http://dev:8013
```

**Example 2: Partial Overrides**
```toml
# config.toml
[api]
url = "http://prod:8013"
key = "config-key"

[defaults]
severity = "warning"
channel = "prod.logs"

[decay]
hold_seconds = 30.0
decay_seconds = 10.0
```

```bash
export TREE_SIGNAL_API_KEY="env-key"
tree-signal --channel myapp.logs --severity info

# Effective configuration:
#   api.url:      http://prod:8013    (from config)
#   api.key:      env-key              (from env, overrides config)
#   severity:     info                 (from CLI, overrides config)
#   channel:      myapp.logs           (from CLI, overrides config)
```

## Configuration File Format

### Supported Formats

The tool supports multiple config formats through a modular loader:

1. **TOML** (preferred) - Uses stdlib `tomllib` (Python 3.11+)
2. **JSON** (fallback) - Uses stdlib `json`
3. **YAML** (future) - Requires `PyYAML` if installed

Format is detected by file extension (`.toml`, `.json`, `.yaml`/`.yml`) or by attempting to parse in order.

### Config File Location Precedence
When looking for a config file (unless `--no-config` is used):

1. `--config PATH` (explicitly specified, must exist or error)
2. `$TREE_SIGNAL_CONFIG` (environment variable, must exist or error)
3. `~/.config/tree-signal/config.toml` (user config, preferred)
4. `~/.config/tree-signal/config.json` (user config, fallback)
5. `/etc/tree-signal/config.toml` (system-wide, optional)
6. `/etc/tree-signal/config.json` (system-wide fallback, optional)

**Only the first file found is loaded. Config files do not merge.**

### Modular Config Loader Design

```python
# Internal architecture (for implementation)
class ConfigLoader:
    """Abstract base for config loaders"""
    def can_load(self, path: str) -> bool: ...
    def load(self, path: str) -> dict: ...

class TOMLLoader(ConfigLoader):
    """Uses stdlib tomllib (Python 3.11+)"""

class JSONLoader(ConfigLoader):
    """Uses stdlib json"""

class YAMLLoader(ConfigLoader):
    """Optional, requires PyYAML"""

# Config reader tries loaders in order
def load_config(path: str) -> dict:
    for loader in [TOMLLoader(), JSONLoader(), YAMLLoader()]:
        if loader.can_load(path):
            return loader.load(path)
```

This design allows:
- Easy addition of new formats (XML, INI, etc.)
- Graceful degradation (skip YAML if PyYAML not installed)
- Format-agnostic core logic

### CLI Argument to Config Mapping

Every CLI argument (except `--config`) can be specified in the config file:

| CLI Argument | Config File Path | Example |
|--------------|------------------|---------|
| `--api URL` | `api.url` | `api:\n  url: "http://localhost:8013"` |
| `--api-key KEY` | `api.key` | `api:\n  key: "secret"` |
| `--channel NAME` | `defaults.channel` | `defaults:\n  channel: "logs"` |
| `--severity LEVEL` | `defaults.severity` | `defaults:\n  severity: "info"` |
| `--batch-size N` | `performance.batch_size` | `performance:\n  batch_size: 10` |
| `--batch-interval MS` | `performance.batch_interval` | `performance:\n  batch_interval: 1000` |
| `--rate-limit N` | `performance.rate_limit` | `performance:\n  rate_limit: 100` |
| `--retry COUNT` | `retry.max_attempts` | `retry:\n  max_attempts: 3` |
| `--retry-delay MS` | `retry.base_delay` | `retry:\n  base_delay: 1000` |
| `--quiet` | `logging.quiet` | `logging:\n  quiet: true` |
| `--debug` | `logging.debug` | `logging:\n  debug: true` |
| `--dry-run` | `logging.dry_run` | `logging:\n  dry_run: true` |

### Complete Configuration Schema (TOML)

```toml
# ~/.config/tree-signal/config.toml

# API connection settings
[api]
url = "http://localhost:8013"    # --api
key = "your-api-key-here"        # --api-key (or use environment variable)
timeout = 5000                   # milliseconds (not exposed as CLI arg)

# Default message settings
[defaults]
severity = "info"                # --severity
channel = "default"              # --channel (fallback if no routing matches)

# Decay configuration (controls panel fade-out behavior)
[decay]
hold_seconds = 30.0              # Duration to hold full weight before decay begins
decay_seconds = 10.0             # Duration to fade from full weight to removal

# Performance tuning
[performance]
batch_size = 10                  # --batch-size
batch_interval = 1000            # --batch-interval (max ms to wait)
rate_limit = 100                 # --rate-limit (0 = unlimited)

# Retry behavior
[retry]
max_attempts = 3                 # --retry
base_delay = 1000                # --retry-delay (ms, exponential backoff)
max_delay = 30000                # ms, cap for backoff (not exposed as CLI arg)

# Logging (for the CLI tool itself)
[logging]
level = "info"                   # debug, info, warning, error
format = "text"                  # text or json
quiet = false                    # --quiet (suppress informational output)
debug = false                    # --debug (enable debug logging)
dry_run = false                  # --dry-run (don't send to API, print to stdout)

# Routing rules (evaluated in order, first match wins)
[[routing]]
name = "systemd-errors"
pattern = '.*\b(error|fatal|critical)\b.*'
severity = "error"
channel = "system.errors"

[[routing]]
name = "nginx-access"
pattern = '^(?P<ip>[\d.]+).*?"(?P<method>\w+) (?P<path>/\S+).*?" (?P<status>\d+)'
channel = "nginx.access.{method}.{status}"

[routing.severity_map]
"^5\\d\\d$" = "error"
"^4\\d\\d$" = "warning"
"^2\\d\\d$" = "info"

[[routing]]
name = "json-logs"
pattern = '^(?P<json>\{.*\})$'

[routing.json_extract]
channel = "service"              # JSON path: log.service → channel
severity = "level"               # JSON path: log.level → severity
message = "message"              # JSON path: log.message → payload

[[routing]]
name = "syslog-format"
pattern = '^(?P<timestamp>\w+\s+\d+\s+[\d:]+)\s+(?P<host>\S+)\s+(?P<process>\S+?)(\[(?P<pid>\d+)\])?:\s+(?P<message>.*)$'
channel = "syslog.{host}.{process}"

[[routing]]
name = "default-passthrough"
pattern = ".*"                   # catch-all
channel = "{channel}"            # use --channel arg or defaults.channel

# Optional: channel-specific overrides
[channels."myapp.api.*"]
severity = "debug"
rate_limit = 50

[channels."system.errors"]
batch_size = 1                   # send immediately, don't batch
```

## Routing Rules Specification

### Rule Evaluation
1. Rules evaluated in order from top to bottom
2. First matching pattern wins
3. If no rules match and `--channel` provided, use that
4. If no rules match and no `--channel`, use `defaults.channel`
5. If `defaults.channel` not set, error and skip message

### Pattern Matching
- Uses Python `re` module (PCRE-style regex)
- Named capture groups `(?P<name>...)` available for interpolation
- Case-sensitive by default (add `(?i)` for case-insensitive)

### Channel Templating
- Format: `"base.{variable}.{other}"`
- Variables from:
  - Named regex groups: `{method}`, `{status}`, etc.
  - JSON extraction: `{service}`, `{level}`, etc.
  - CLI args: `{channel}` (from `--channel`)
- Sanitization: replace invalid chars with `_`, lowercase

### JSON Extraction
```toml
[routing.json_extract]
channel = "service"              # extracts log.service
severity = "level"               # extracts log.level
message = "message"              # extracts log.message (or use full line)
```

Example JSON:
```json
{"service": "api", "level": "error", "message": "Auth failed", "user": 123}
```
Results in: `channel="api"`, `severity="error"`, `payload="Auth failed"`

### Severity Mapping
```toml
[routing.severity_map]
"^5\\d\\d$" = "error"            # regex pattern → severity level
"^4\\d\\d$" = "warning"
"^2\\d\\d$" = "info"
```
Applied to captured groups or JSON fields.

## Rate Limiting & Batching

### Batching Behavior
- Accumulate up to `batch_size` messages
- OR wait up to `batch_interval` milliseconds
- Whichever comes first, flush batch to API
- Single API call with array of messages (if API supports batch endpoint)
- Fallback: individual POSTs if batch endpoint unavailable

### Rate Limiting
- Token bucket algorithm
- `rate_limit` messages per second
- If exceeded, buffer messages (up to reasonable limit)
- If buffer full, drop oldest messages (log warning)
- `0` = unlimited (no rate limiting)

### Per-Channel Overrides
Channels can override global performance settings:
```toml
[channels."high-priority.*"]
batch_size = 1             # immediate
rate_limit = 0             # unlimited

[channels."low-priority.*"]
batch_size = 100
rate_limit = 10
```

## Error Handling

### API Connection Failures
1. Retry with exponential backoff: `base_delay * 2^attempt`
2. Max retries: `retry.max_attempts`
3. Cap delay at `retry.max_delay`
4. If all retries fail:
   - Log error to stderr
   - Exit with code `2` (connection error)

### Authentication Failures (401/403)
- Do NOT retry (auth won't magically work)
- Log error to stderr
- Exit with code `3`

### Transient Errors (429, 5xx)
- Retry with backoff (treat as connection failure)
- Respect `Retry-After` header if present

### Invalid Configuration
- Validate config on startup
- Exit with code `1` and helpful error message
- Show which config file was loaded

### Stdin Errors
- If stdin closes unexpectedly, flush any buffered messages
- Exit cleanly (code `0`)

## Implementation Notes

### Language & Dependencies
- **Python 3.11+** using stdlib only:
  - `argparse` - CLI parsing
  - `urllib` - HTTP client
  - `json` - JSON handling
  - `re` - Regex routing
  - `yaml` - config parsing (stdlib `yaml` or vendored PyYAML)
  - `sys`, `signal` - I/O and signal handling
  - `time`, `collections` - rate limiting and batching

### Installation
- Shipped in `scripts/tree-signal` (executable Python script)
- Shebang: `#!/usr/bin/env python3`
- Can be symlinked to `~/.local/bin/tree-signal` or `/usr/local/bin/tree-signal`
- Optional: package as `tree-signal` PyPI package for `pip install tree-signal`

### Performance Targets
- Handle 1000+ messages/sec with batching enabled
- Minimal memory footprint (<10MB typical)
- Graceful degradation under load (drop messages rather than OOM)

## API Endpoint Requirements

### Expected API Behavior
```bash
# Single message
POST /v1/messages
Content-Type: application/json
X-API-Key: <key>

{
  "channel": "myapp.api.auth",
  "payload": "User login successful",
  "severity": "info"
}

# Batch messages (if supported, future enhancement)
POST /v1/messages/batch
Content-Type: application/json
X-API-Key: <key>

{
  "messages": [
    {"channel": "myapp.api.auth", "payload": "...", "severity": "info"},
    {"channel": "myapp.api.auth", "payload": "...", "severity": "error"}
  ]
}
```

## Example Configurations

### Simple: Forward Everything
```toml
# config.toml
[api]
url = "http://localhost:8013"

[defaults]
channel = "logs"
severity = "info"

[decay]
hold_seconds = 30.0
decay_seconds = 10.0
```

Usage: `tail -f app.log | tree-signal`

### Advanced: Multi-Service Routing
```toml
# config.toml
[api]
url = "http://monitoring.internal:8013"
key = "prod-key-123"

[defaults]
severity = "info"
channel = "unknown"

[decay]
hold_seconds = 30.0
decay_seconds = 10.0

[performance]
batch_size = 20
rate_limit = 200

[[routing]]
name = "docker-logs"
pattern = '^(?P<timestamp>\S+) (?P<container>\S+) \[(?P<level>\w+)\] (?P<msg>.*)$'
channel = "docker.{container}"
severity = "{level}"

[[routing]]
name = "systemd-unit"
pattern = '^(?P<unit>\S+)\[\d+\]: (?P<msg>.*)$'
channel = "systemd.{unit}"

[[routing]]
name = "catch-all"
pattern = ".*"
channel = "unmatched"
```

### JSON Logs from Application
```toml
# config.toml
[[routing]]
name = "structured-json"
pattern = '^(?P<json>\{.*\})$'

[routing.json_extract]
channel = "app"
severity = "level"
message = "msg"
```

Input: `{"app": "api", "level": "error", "msg": "DB timeout"}`
Output: `channel="api"`, `severity="error"`, `payload="DB timeout"`

## Testing Strategy

### Unit Tests
- Config parsing and validation
- Routing rule matching and interpolation
- JSON extraction logic
- Rate limiting behavior
- Batching flush logic

### Integration Tests
- End-to-end with mock API server
- Retry behavior on failures
- Signal handling (SIGINT, SIGTERM)
- Config file precedence

### Manual Testing
```bash
# Generate test logs
seq 1 100 | awk '{print "2024-01-15 app[" $1 "] Log line " $1}' | tree-signal --dry-run

# Test with real API
tail -f /var/log/syslog | tree-signal --channel system.syslog --debug

# Test batching
yes "test message" | head -1000 | tree-signal --batch-size 50 --debug
```

## Future Enhancements (Out of Scope for MVP)

- WebSocket mode for bidirectional communication
- Local buffering to disk when API unavailable
- Metrics export (messages sent, errors, latency)
- Built-in log file watching (instead of requiring `tail -f`)
- Plugin system for custom parsers
- Go binary distribution for easier deployment

## Open Questions

1. Should we support multiple simultaneous streams (multiple files → different channels)?
2. Do we need a daemon mode that watches files persistently?
3. Should there be a built-in config validator command (`tree-signal validate-config`)?
4. Should we support output formats other than Tree Signal API (e.g., webhook, syslog)?

## Next Steps

1. Review and refine this spec
2. Create sample config files for common use cases
3. Implement MVP with core features (routing, batching, retry)
4. Write tests
5. Document in main README with examples
