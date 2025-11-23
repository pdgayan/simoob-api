# Quick Start Guide

Get your System Monitoring API up and running in 5 minutes!

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Start the API

```bash
uvicorn api:app --reload --port 3001 --host 0.0.0.0
```

You should see:

```
INFO:     Uvicorn running on http://0.0.0.0:3001 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## Step 3: Access the Interactive Documentation

Open your browser and go to:

**http://localhost:3001/docs**

You'll see the Swagger UI with all 60+ endpoints organized by category!

## Step 4: Try Your First API Call

### Option A: Using the Browser

1. Go to http://localhost:3001/docs
2. Find "system" section
3. Click on `GET /api/system/stats`
4. Click "Try it out"
5. Click "Execute"
6. See the response!

### Option B: Using curl

```bash
curl http://localhost:3001/api/system/stats
```

### Option C: Using Python

```python
import requests

response = requests.get('http://localhost:3001/api/system/stats')
print(response.json())
```

## Common API Calls to Try

### 1. Check System Health

```bash
curl http://localhost:3001/health
```

### 2. Get Container List

```bash
curl http://localhost:3001/api/containers/detailed
```

### 3. Monitor CPU Usage

```bash
curl http://localhost:3001/api/system/cpu
```

### 4. Check Memory

```bash
curl http://localhost:3001/api/system/memory
```

### 5. View Docker Images

```bash
curl http://localhost:3001/api/containers/images
```

### 6. Get Network Interfaces

```bash
curl http://localhost:3001/api/network/interfaces
```

### 7. Search Logs

```bash
curl "http://localhost:3001/api/logs/search?query=error&lines=100"
```

### 8. Check System Alerts

```bash
curl "http://localhost:3001/api/advanced/alerts?cpu_threshold=80"
```

### 9. Export Metrics (Prometheus)

```bash
curl http://localhost:3001/api/advanced/metrics/prometheus
```

### 10. Test Network Latency

```bash
curl "http://localhost:3001/api/network/latency?host=google.com&count=4"
```

## Troubleshooting

### Issue: Port Already in Use

```bash
# Change the port
uvicorn api:app --reload --port 8000 --host 0.0.0.0
```

### Issue: Module Not Found

```bash
# Make sure you're in the project directory
cd "f:\client projects\my startup\simoob-agent\simoob-product"

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: Docker Commands Not Working

```bash
# Make sure Docker is installed and running
docker ps

# Add your user to docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker
```

### Issue: Permission Denied for Some Commands

Some endpoints require elevated privileges. Either:

1. Run with sudo: `sudo uvicorn api:app --port 3001`
2. Or accept that some endpoints may return limited data

## Next Steps

1. ✅ Explore the API documentation at `/docs`
2. ✅ Try different endpoints
3. ✅ Check out the full documentation in `README.md`
4. ✅ Review the endpoint reference in `API_REFERENCE.md`
5. ✅ Read the implementation summary in `SUMMARY.md`

## API Overview

- **Base URL**: http://localhost:3001
- **Documentation**: http://localhost:3001/docs
- **Alternative Docs**: http://localhost:3001/redoc
- **Health Check**: http://localhost:3001/health

## Categories

- 🖥️ **System** (`/api/system/*`) - 14 endpoints
- 🐳 **Containers** (`/api/containers/*`) - 14 endpoints
- 🌐 **Network** (`/api/network/*`) - 11 endpoints
- 📝 **Logs** (`/api/logs/*`) - 10 endpoints
- ⚡ **Advanced** (`/api/advanced/*`) - 10 endpoints

**Total: 60+ endpoints!**

## Production Deployment

For production use:

```bash
# Install production server
pip install gunicorn

# Run with multiple workers
gunicorn api:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:3001
```

## Need Help?

- 📖 Check `README.md` for detailed documentation
- 📚 Check `API_REFERENCE.md` for endpoint details
- 💡 Check `SUMMARY.md` for feature overview
- 🔍 Use the interactive docs at `/docs`

---

**Happy Monitoring! 🚀**
