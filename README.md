# System Monitoring API v2.0

A comprehensive FastAPI application for monitoring Docker containers, system resources, network metrics, logs, and advanced system statistics.

## 🚀 Features

- **System Monitoring**: CPU, memory, disk, load averages, temperature sensors, power status
- **Container Management**: List, start, stop, restart containers, view stats and logs
- **Network Analytics**: Interface monitoring, traffic analysis, connection tracking, latency testing
- **Log Management**: System logs, container logs, authentication logs, error filtering
- **Advanced Metrics**: Cgroups, filesystem inodes, alerts, Prometheus export

## 📁 Project Structure

```
simoob-product/
├── api.py              # Main FastAPI application
├── utils.py            # Shared utility functions
├── requirements.txt    # Python dependencies
├── dockerfile          # Docker container configuration
├── README.md          # This file
└── routers/           # Modular route handlers
    ├── __init__.py
    ├── system.py      # System-level metrics
    ├── containers.py  # Container management
    ├── network.py     # Network monitoring
    ├── logs.py        # Log management
    └── advanced.py    # Advanced metrics
```

## 🛠️ Installation

### Prerequisites

- Python 3.8+
- Docker (for container monitoring)
- Linux system (Ubuntu/Debian/CentOS/RHEL)

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Optional System Packages

For full functionality, install these system packages:

```bash
# For temperature monitoring
sudo apt install lm-sensors
sudo sensors-detect

# For I/O statistics
sudo apt install sysstat

# For network analysis
sudo apt install net-tools iproute2
```

## 🚀 Running the API

### Development Mode

```bash
uvicorn api:app --reload --port 3001 --host 0.0.0.0
```

### Production Mode

```bash
uvicorn api:app --port 3001 --host 0.0.0.0 --workers 4
```

### Using Docker

```bash
docker build -t system-monitor-api .
docker run -d -p 3001:3001 --name monitor-api system-monitor-api
```

## 📚 API Documentation

Once running, access interactive API documentation at:

- **Swagger UI**: http://localhost:3001/docs
- **ReDoc**: http://localhost:3001/redoc
- **OpenAPI JSON**: http://localhost:3001/openapi.json

## 🔗 API Endpoints Overview

### System-Level Metrics (15 endpoints)

- `/api/system/stats` - Full system overview
- `/api/system/cpu` - CPU usage monitoring
- `/api/system/memory` - Memory statistics
- `/api/system/load` - Load averages
- `/api/system/processes` - Process monitoring
- And 10+ more system endpoints...

### Container-Level Metrics (15 endpoints)

- `/api/containers/detailed` - List all containers
- `/api/containers/{name}/stats` - Container metrics
- `/api/containers/start/{name}` - Start container
- `/api/containers/stop/{name}` - Stop container
- And 11+ more container endpoints...

### Network-Level Metrics (11 endpoints)

- `/api/network/interfaces` - Network interfaces
- `/api/network/traffic` - Traffic statistics
- `/api/network/connections` - Active connections
- `/api/network/latency` - Latency testing
- And 7+ more network endpoints...

### Logs & Events (10 endpoints)

- `/api/logs/system` - System logs
- `/api/logs/container/{name}` - Container logs
- `/api/logs/errors` - Error logs
- `/api/logs/search` - Search logs
- And 6+ more log endpoints...

### Advanced Metrics (10 endpoints)

- `/api/advanced/sensors` - Temperature sensors
- `/api/advanced/alerts` - Threshold alerts
- `/api/advanced/metrics/prometheus` - Prometheus export
- `/api/advanced/cgroups` - Cgroup statistics
- And 6+ more advanced endpoints...

**Total: 60+ Endpoints**

## 📊 Usage Examples

### Get System Stats

```bash
curl http://localhost:3001/api/system/stats
```

### Monitor Container

```bash
curl http://localhost:3001/api/containers/my-container/stats
```

### Check Alerts

```bash
curl "http://localhost:3001/api/advanced/alerts?cpu_threshold=80&memory_threshold=85"
```

### Export Metrics

```bash
# JSON export
curl http://localhost:3001/api/advanced/metrics/export/json > metrics.json

# Prometheus format
curl http://localhost:3001/api/advanced/metrics/prometheus
```

## ⚙️ Configuration

Create a `.env` file for configuration:

```bash
API_HOST=0.0.0.0
API_PORT=3001
API_WORKERS=4
CORS_ORIGINS=*
```

## 🔒 Security Notes

1. Add authentication for production
2. Restrict CORS origins
3. Implement rate limiting
4. Some endpoints require sudo privileges

## 📄 License

MIT License

## 👥 Authors

Simoob Team - System Monitoring Solutions
