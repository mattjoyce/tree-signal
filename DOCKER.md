# Tree Signal - Docker Deployment

A lightweight treemap-based hierarchical message dashboard that can run as a Docker container.

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/mattjoyce/tree-signal.git
cd tree-signal

# Start the service
docker-compose up -d

# View logs
docker-compose logs -f
```

### Using Docker Build

```bash
# Build the image
docker build -t tree-signal .

# Run the container
docker run -d \
  --name tree-signal \
  -p 8000:8000 \
  -p 8001:8001 \
  --restart unless-stopped \
  tree-signal
```

### Using Pre-built Image (once available)

```bash
docker run -d \
  --name tree-signal \
  -p 8000:8000 \
  -p 8001:8001 \
  --restart unless-stopped \
  ghcr.io/mattjoyce/tree-signal:latest
```

## Access the Application

- **Web Dashboard**: http://localhost:8001
- **API Server**: http://localhost:8000
- **Health Check**: http://localhost:8000/healthz

## Sending Test Messages

```bash
# Send a test message
curl -X POST "http://localhost:8000/v1/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "myapp.api.auth",
    "payload": "User logged in successfully",
    "severity": "info",
    "metadata": {"user": "alice"}
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
- **Repository**: `ghcr.io/mattjoyce/tree-signal:latest`
- **Network Type**: `Bridge`
- **Port Mappings**:
  - Container Port: `8000` → Host Port: `8000` (API)
  - Container Port: `8001` → Host Port: `8001` (Web UI)
- **Restart Policy**: `unless-stopped`

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
curl http://localhost:8000/healthz
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
