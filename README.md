# Tree Signal

A lightweight treemap-based hierarchical message dashboard perfect for monitoring applications, logs, and system events.

![Tree Signal Dashboard](https://via.placeholder.com/800x400/1a1b26/7aa2f7?text=Tree+Signal+Dashboard)

## Features

- **Hierarchical Visualization**: Messages organized by dot-separated channels (`project.api.auth`)
- **Real-time Treemap**: Panel sizes reflect message activity and severity
- **Lightweight**: ~50MB RAM, minimal CPU usage
- **Docker Ready**: Perfect for Unraid, Portainer, and Docker Compose
- **No Dependencies**: Self-contained with built-in web interface
- **Auto-decay**: Panels fade and disappear when inactive

## Quick Start

### Docker (Recommended)

```bash
# Build and run with appdata mount
git clone https://github.com/mattjoyce/tree-signal.git
cd tree-signal
docker build -t tree-signal .
docker run -d --name tree-signal -p 8013:8013 -p 8014:8014 -v /mnt/user/appdata/tree-signal:/app/data --restart unless-stopped tree-signal
```

Visit **http://localhost:8014** for the dashboard.

### Send Test Messages

```bash
curl -X POST "http://localhost:8013/v1/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "myapp.api.auth",
    "payload": "User authentication successful",
    "severity": "info"
  }'
```

## Use Cases

- **Application Monitoring**: Visualize microservice health and activity
- **Log Aggregation**: Display log events by component hierarchy  
- **System Alerts**: Monitor server metrics and alerts in real-time
- **DevOps Dashboards**: Track deployment pipelines and build status
- **IoT Data**: Visualize sensor data by location/device hierarchy

## Unraid Installation

1. **Community Applications**: Search for "tree-signal"
2. **Manual**: Use `mattjoyce/tree-signal:latest` image
3. **Ports**: 8013 (API), 8014 (Web UI)
4. **Volume**: `/mnt/user/appdata/tree-signal` → `/app/data`

## API Endpoints

- `POST /v1/messages` - Send messages
- `GET /v1/layout` - Current treemap layout
- `GET /v1/messages/{channel}` - Message history
- `POST /v1/control/decay` - Configure decay settings

## Development

```bash
# Local development
git clone https://github.com/mattjoyce/tree-signal.git
cd tree-signal
python3.11 -m venv venv
source venv/bin/activate
pip install -e .

# Run servers
uvicorn tree_signal.api.main:app --reload --port 8000 &
python -m http.server --directory client 8001
```

## Documentation

- [Docker Deployment Guide](DOCKER.md)
- [API Documentation](tree_signal_spec.md)
- [Development Setup](src/README.md)

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request
