# Tree Signal CLI

Command-line tools for streaming logs to a Tree Signal dashboard. Two versions available:

- **`tree-signal`** (Python) - Advanced routing, batching, JSON extraction
- **`tree-signal.sh`** (Bash) - Minimal dependencies, simple message sending

## Choose Your CLI

### Bash Version (`tree-signal.sh`) - Recommended for Simple Use Cases

**Use when:**
- ✅ You want minimal dependencies (just bash + curl)
- ✅ Simple log forwarding without complex routing
- ✅ Quick ad-hoc message sending
- ✅ Systems without Python 3.11+

**Features:**
- 📨 Stdin-only processing (tail -f | tree-signal.sh)
- 🎯 Simple channel targeting
- ⚡ Immediate message sending
- 🔧 Config via environment variables or simple config file
- 📦 ~150 lines of bash, no dependencies

### Python Version (`tree-signal`) - Advanced Log Processing

**Use when:**
- ✅ You need regex routing rules
- ✅ JSON log extraction
- ✅ Batching and rate limiting
- ✅ Complex log transformation

**Features:**
- 📊 **Hierarchical Routing** - Route logs to channels like `app.api.auth` or `system.errors`
- 🎯 **Pattern Matching** - Use regex to extract channel/severity from log lines
- 🔄 **JSON Extraction** - Parse structured JSON logs automatically
- ⚡ **Batching & Rate Limiting** - Optimize API calls with configurable batching
- 🔁 **Retry Logic** - Exponential backoff on failures
- ⚙️ **Config Precedence** - defaults < config file < env vars < CLI args
- 📝 **Multiple Formats** - TOML (preferred), JSON, YAML (optional)

## Quick Start

### Bash CLI - Simple Message Sending

```bash
# Simple - use default host from config/env
echo "Deploy started" | ./tree-signal.sh app.deploy
tail -f /var/log/app.log | ./tree-signal.sh app.logs

# Specify host:port explicitly
echo "Error occurred" | ./tree-signal.sh localhost:8013 app.errors
tail -f /var/log/nginx/access.log | ./tree-signal.sh 192.168.1.10:8013 nginx.access

# With grep filtering and severity
tail -f app.log | grep ERROR | ./tree-signal.sh -s error app.errors

# Dry run (print curl commands without sending)
echo "Test" | ./tree-signal.sh --dry-run test.channel
```

**Configuration (Bash):**
```bash
# Environment variables
export TREE_SIGNAL_URL=http://localhost:8013
export TREE_SIGNAL_API_KEY=your-key

# Or config file: ~/.config/tree-signal/config
TREE_SIGNAL_URL=http://localhost:8013
TREE_SIGNAL_API_KEY=your-key
```

### Python CLI - Advanced Routing

```bash
# Forward all logs to a single channel
tail -f /var/log/app.log | ./tree-signal --channel myapp.logs

# With API URL
tail -f /var/log/nginx/access.log | ./tree-signal \
  --api http://192.168.20.4:8013 \
  --channel nginx.access

# Dry run (print without sending)
echo "Test message" | ./tree-signal --channel test --dry-run
```

**Configuration (Python):**
```bash
# Create TOML config
mkdir -p ~/.config/tree-signal
cp examples/simple.toml ~/.config/tree-signal/config.toml

# Edit config with your API URL and routing rules
vim ~/.config/tree-signal/config.toml

# Run with config
tail -f /var/log/syslog | ./tree-signal
```

## Installation

### Bash CLI (`tree-signal.sh`)

```bash
# Make executable
chmod +x tree-signal.sh

# Symlink to your PATH
ln -s $(pwd)/tree-signal.sh ~/.local/bin/tree-signal-sh

# Or copy to system location
sudo cp tree-signal.sh /usr/local/bin/

# Test it
echo "Hello" | ./tree-signal.sh --dry-run test.channel
```

**Requirements:**
- Bash 4.0+ (standard on most systems)
- `curl` (pre-installed on most systems)
- No other dependencies

### Python CLI (`tree-signal`)

```bash
# Make executable
chmod +x tree-signal

# Symlink to your PATH
ln -s $(pwd)/tree-signal ~/.local/bin/tree-signal

# Or copy to system location
sudo cp tree-signal /usr/local/bin/
```

**Requirements:**
- Python 3.11+ (for stdlib `tomllib`)
- No external dependencies for TOML/JSON support
- Optional: `pyyaml` for YAML config support

## Configuration

### Precedence Order

Configuration is resolved in this order (lowest to highest priority):

```
Built-in defaults → Config file → Environment variables → CLI arguments
```

### Config File Locations

Tree Signal CLI looks for config files in this order:

1. `--config PATH` (explicitly specified)
2. `$TREE_SIGNAL_CONFIG` (environment variable)
3. `~/.config/tree-signal/config.toml`
4. `~/.config/tree-signal/config.json`
5. `/etc/tree-signal/config.toml`
6. `/etc/tree-signal/config.json`

### Example Configs

See the `examples/` directory:

- **`simple.toml`** - Basic forwarding to a single channel
- **`advanced.toml`** - Multi-service routing with patterns
- **`json-logs.toml`** - JSON log extraction

### Simple Config

```toml
[api]
url = "http://localhost:8013"

[defaults]
channel = "logs"
severity = "info"

[decay]
hold_seconds = 30.0
decay_seconds = 10.0

[performance]
batch_size = 10
rate_limit = 100
```

### Advanced Routing

```toml
[api]
url = "http://192.168.20.4:8013"

[defaults]
channel = "unmatched"

[decay]
hold_seconds = 30.0
decay_seconds = 10.0

# Route nginx access logs
[[routing]]
name = "nginx-access"
pattern = '^(?P<ip>[\d.]+).*?"(?P<method>\w+) (?P<path>/\S+).*?" (?P<status>\d+)'
channel = "nginx.access"

# Route error logs
[[routing]]
name = "errors"
pattern = '.*\b(error|fatal|critical)\b.*'
severity = "error"
channel = "system.errors"

# Catch-all
[[routing]]
name = "catch-all"
pattern = ".*"
channel = "{channel}"
```

## CLI Options

### Bash CLI Options (`tree-signal.sh`)

**Usage:** `tree-signal.sh [OPTIONS] [HOST:PORT] CHANNEL`

| Option | Short | Description |
|--------|-------|-------------|
| `--severity LEVEL` | `-s` | Severity: debug\|info\|warn\|error (default: info) |
| `--quiet` | `-q` | Suppress informational output |
| `--debug` | `-d` | Enable debug output |
| `--dry-run` | | Print curl commands without sending |
| `--help` | `-h` | Show help |

**Arguments:**
- `CHANNEL` - Required hierarchical channel (e.g., `app.api.auth`)
- `HOST:PORT` - Optional API endpoint (default: from config/env)

**Environment Variables:**
- `TREE_SIGNAL_URL` - API base URL (default: http://localhost:8013)
- `TREE_SIGNAL_API_KEY` - API authentication key
- `TREE_SIGNAL_CONFIG` - Config file path

### Python CLI Options (`tree-signal`)

| Option | Short | Description |
|--------|-------|-------------|
| `--config PATH` | | Path to config file |
| `--no-config` | | Ignore config file |
| `--api URL` | `-a` | Tree Signal API URL |
| `--api-key KEY` | `-k` | API authentication key |
| `--channel NAME` | `-c` | Target channel path |
| `--severity LEVEL` | `-s` | Default severity (debug/info/warning/error/critical) |
| `--batch-size N` | `-b` | Batch N messages before sending |
| `--batch-interval MS` | | Max milliseconds before flushing batch |
| `--rate-limit N` | `-r` | Max messages per second (0=unlimited) |
| `--retry COUNT` | | Number of retries on API failure |
| `--retry-delay MS` | | Base delay between retries (ms) |
| `--quiet` | `-q` | Suppress informational output |
| `--debug` | | Enable debug logging |
| `--dry-run` | | Print messages instead of sending |

## Environment Variables

- `TREE_SIGNAL_API_URL` - API base URL
- `TREE_SIGNAL_API_KEY` - API authentication key
- `TREE_SIGNAL_CONFIG` - Config file path

## Common Use Cases

### System Logs (journald)

```bash
# All systemd logs
journalctl -f | ./tree-signal --channel systemd.all

# Specific service
journalctl -fu nginx | ./tree-signal --channel systemd.nginx
```

### Docker Logs

```bash
# Single container
docker logs -f my-container | ./tree-signal --channel docker.my-container

# All containers with routing
docker events --format '{{.Actor.Attributes.name}}: {{.Status}}' | \
  ./tree-signal --config docker.toml
```

### Application Logs

```bash
# Simple forwarding
tail -f /var/log/app/production.log | ./tree-signal --channel app.production

# With severity extraction
tail -f /var/log/app/app.log | ./tree-signal --config app-routing.toml
```

### JSON Logs

```toml
# config.toml
[[routing]]
name = "json-logs"
pattern = '^(?P<json>\{.*\})$'

[routing.json_extract]
channel = "service"
severity = "level"
message = "msg"
```

```bash
# Route structured logs
tail -f /var/log/app/json.log | ./tree-signal
```

## Routing Rules

Routing rules are evaluated in order; **first match wins**.

### Pattern Matching

Uses Python regex with named capture groups:

```toml
[[routing]]
pattern = '^(?P<timestamp>\S+) (?P<level>\w+) (?P<msg>.*)$'
channel = "app.{level}"
```

### Channel Templating

Use `{variable}` to reference captured groups:

```toml
pattern = '^(?P<service>\w+): (?P<message>.*)$'
channel = "myapp.{service}"
```

Variables are sanitized: lowercase, non-alphanumeric chars become `_`

### JSON Extraction

Extract fields from JSON logs:

```toml
[[routing]]
pattern = '^(?P<json>\{.*\})$'

[routing.json_extract]
channel = "service"    # Extract from log["service"]
severity = "level"     # Extract from log["level"]
message = "msg"        # Extract from log["msg"]
```

### Severity Mapping

Map captured values to severity levels:

```toml
[[routing]]
pattern = '.*status=(?P<status>\d+).*'

[routing.severity_map]
"^5\\d\\d$" = "error"     # 5xx -> error
"^4\\d\\d$" = "warning"   # 4xx -> warning
"^2\\d\\d$" = "info"      # 2xx -> info
```

## Testing

```bash
# Run basic tests
python3 tests/test_config.py
python3 tests/test_router.py

# Test with dry-run
echo "Test message" | ./tree-signal --channel test --dry-run

# Generate test logs
seq 1 100 | awk '{print "Log line " $1}' | \
  ./tree-signal --channel test.logs --debug
```

## Troubleshooting

### Module Not Found

If you get `ModuleNotFoundError: No module named 'tree_signal_cli'`:

```bash
# Run from the cli/ directory
cd /path/to/tree-signal/cli
./tree-signal --help
```

### Connection Refused

```bash
# Check API is running
curl http://192.168.20.4:8013/healthz

# Use --debug to see details
echo "test" | ./tree-signal --api http://192.168.20.4:8013 \
  --channel test --debug
```

### No Matching Route

```bash
# Use --debug to see routing decisions
tail -f app.log | ./tree-signal --config myconfig.toml --debug

# Or provide a default channel
tail -f app.log | ./tree-signal --channel fallback.logs
```

## Architecture

- **`config.py`** - Modular config loader (TOML/JSON/YAML)
- **`router.py`** - Pattern matching and channel routing
- **`sender.py`** - API client with batching/retry
- **`main.py`** - CLI entry point and orchestration

## License

MIT License - Part of the Tree Signal project

## Contributing

This is hobby-grade code designed for easy adaptation:

- Good docstrings for clarity
- Simple error handling (fail with useful messages)
- Minimal dependencies (Python 3.11+ stdlib)
- Basic tests for key features

Feel free to fork and adapt for your use case!
