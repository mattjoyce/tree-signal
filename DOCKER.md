# Tree Signal - Docker Deployment

A lightweight treemap-based hierarchical message dashboard that can run as a Docker container.

## Quick Start

### Clone and Build

```bash
# Clone the repository
git clone https://github.com/mattjoyce/tree-signal.git
cd tree-signal

# Build the image
docker build -t tree-signal .

# Run the container with appdata mount
docker run -d \
  --name tree-signal \
  -p 8013:8013 \
  -p 8014:8014 \
  -v /mnt/user/appdata/tree-signal:/app/data \
  --restart unless-stopped \
  tree-signal
```

### Or Build from GitHub directly

```bash
# Build directly from GitHub (no clone needed)
docker build -t tree-signal https://github.com/mattjoyce/tree-signal.git

# Run the container with appdata mount
docker run -d \
  --name tree-signal \
  -p 8013:8013 \
  -p 8014:8014 \
  -v /mnt/user/appdata/tree-signal:/app/data \
  --restart unless-stopped \
  tree-signal
```

## Access the Application

- **Web Dashboard**: http://localhost:8014
- **API Server**: http://localhost:8013
- **Health Check**: http://localhost:8013/healthz

## Sending Test Messages

### From the same machine (Unraid host):
```bash
curl -X POST "http://localhost:8013/v1/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "myapp.api.auth",
    "payload": "User logged in successfully",
    "severity": "info",
    "metadata": {"user": "alice"}
  }'
```

### From external machines on your network:
```bash
curl -X POST "http://YOUR_UNRAID_IP:8013/v1/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "monitoring.alerts.cpu",
    "payload": "CPU usage at 85%",
    "severity": "warn",
    "metadata": {"server": "web01", "source": "external"}
  }'
```

### Example with more complex hierarchy:
```bash
curl -X POST "http://YOUR_UNRAID_IP:8013/v1/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "datacenter.rack1.server03.docker.container_restart",
    "payload": "Container nginx restarted successfully",
    "severity": "info",
    "metadata": {"container": "nginx", "uptime": "5m"}
  }'
```

## Unraid Configuration

### Community Applications

1. Go to **Apps** tab in Unraid
2. Search for "tree-signal" (once submitted to CA)
3. Click **Install**

### Manual Template

Create a new container with these settings:

- **Name**: `tree-signal`
- **Repository**: `mattjoyce/tree-signal:latest` (or build from GitHub)
- **Network Type**: `Bridge`
- **Port Mappings**:
  - Container Port: `8013` → Host Port: `8013` (API)
  - Container Port: `8014` → Host Port: `8014` (Web UI)
- **Volume Mappings**:
  - Container Path: `/app/data` → Host Path: `/mnt/user/appdata/tree-signal`
- **Restart Policy**: `unless-stopped`

## Integration Examples

Tree Signal can receive messages from any system that can make HTTP requests:

### Shell Scripts & Cron Jobs
```bash
#!/bin/bash
# Send system status
curl -X POST "http://192.168.20.4:8013/v1/messages" \
  -H "Content-Type: application/json" \
  -d "{\"channel\":\"system.health.$(hostname)\",\"payload\":\"System check: $(uptime)\",\"severity\":\"info\"}"
```

### Python Applications
```python
import requests

def send_tree_signal(channel, message, severity="info", metadata=None):
    data = {
        "channel": channel,
        "payload": message, 
        "severity": severity,
        "metadata": metadata or {}
    }
    response = requests.post("http://192.168.20.4:8013/v1/messages", json=data)
    return response.json()

# Usage
send_tree_signal("app.database.connection", "Connection pool exhausted", "error", {"pool_size": 10})
```

### Docker Container Health Checks
```bash
# Add to your container health check scripts
curl -X POST "http://192.168.20.4:8013/v1/messages" \
  -H "Content-Type: application/json" \
  -d '{"channel":"docker.'$(hostname)'.health","payload":"Container health check passed","severity":"info"}'
```

### Log Processing (rsyslog, fluentd, etc.)
Forward parsed log entries to Tree Signal to visualize application hierarchy and error patterns in real-time.

## Environment Variables

Currently no environment variables are required, but these may be added in future versions:

- `API_KEY`: Authentication key for message submission
- `DECAY_HOLD_SECONDS`: How long panels stay at full weight (default: 10)
- `DECAY_FADE_SECONDS`: How long panels take to fade (default: 5)

## Data Persistence

Tree Signal currently runs entirely in-memory with no persistence. All data is ephemeral and will be lost on container restart. This is by design for the initial prototype.

Future versions may add optional persistence for:
- Panel layouts and preferences
- Message history
- Configuration settings

## Resource Usage

- **CPU**: Very light (< 5% on typical systems)
- **Memory**: ~50-100MB depending on message volume
- **Storage**: ~20MB container image
- **Network**: Minimal (only API calls)

## Security Considerations

- No authentication required by default
- CORS enabled for all origins (suitable for internal networks)
- Consider running behind a reverse proxy for external access
- Future versions will add API key authentication

## Troubleshooting

### Check container logs
```bash
docker logs tree-signal
```

### Verify health
```bash
curl http://localhost:8013/healthz
```

### Reset data
```bash
docker restart tree-signal
```

## Building from Source

```bash
git clone https://github.com/mattjoyce/tree-signal.git
cd tree-signal
docker build -t tree-signal .
```

## License

See LICENSE file in the repository.
