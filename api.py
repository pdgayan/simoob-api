"""
System Monitoring API
A comprehensive FastAPI application for monitoring Docker containers, system resources,
network metrics, logs, and advanced system statistics with historical data storage.

Author: Simoob Team
Version: 2.1
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
import atexit

# Import routers from modular structure
from routers import system, containers, network, logs, advanced, history, analytics

# Import database and collector modules
from database import init_database, cleanup_old_data
from collector import collect_all_metrics

# ----------------------------------------------------------------------
# Logging Configuration
# ----------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# FastAPI Application Setup
# ----------------------------------------------------------------------

app = FastAPI(
    title="System Monitoring API",
    description="Comprehensive monitoring API with historical data storage and analytics",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ----------------------------------------------------------------------
# CORS Middleware Configuration
# ----------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (configure appropriately for production)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# ----------------------------------------------------------------------
# Database Initialization
# ----------------------------------------------------------------------

@app.on_event("startup")
def startup_event():
    """Initialize database and start background tasks on application startup"""
    logger.info("Initializing database...")
    init_database()
    logger.info("Database initialized successfully")
    
    # Start background scheduler for metrics collection
    logger.info("Starting background metrics collector...")
    scheduler = BackgroundScheduler()
    
    # Collect metrics every 5 minutes
    scheduler.add_job(
        func=collect_all_metrics,
        trigger=IntervalTrigger(minutes=5),
        id='collect_metrics',
        name='Collect system metrics',
        replace_existing=True
    )
    
    # Clean up old data daily (remove data older than 30 days)
    scheduler.add_job(
        func=cleanup_old_data,
        trigger=IntervalTrigger(hours=24),
        id='cleanup_data',
        name='Cleanup old metrics data',
        replace_existing=True,
        kwargs={'days_to_keep': 30}
    )
    
    scheduler.start()
    logger.info("Background scheduler started successfully")
    
    # Ensure scheduler shuts down on exit
    atexit.register(lambda: scheduler.shutdown())
    
    # Collect initial metrics immediately
    try:
        logger.info("Collecting initial metrics...")
        collect_all_metrics()
        logger.info("Initial metrics collection completed")
    except Exception as e:
        logger.error(f"Error collecting initial metrics: {e}")

# ----------------------------------------------------------------------
# Register Routers
# ----------------------------------------------------------------------

# System-level metrics router
app.include_router(system.router)

# Container-level metrics router
app.include_router(containers.router)

# Network-level metrics router
app.include_router(network.router)

# Logs and events router
app.include_router(logs.router)

# Advanced metrics router
app.include_router(advanced.router)

# Historical data query router
app.include_router(history.router)

# Analytics and trends router
app.include_router(analytics.router)

# ----------------------------------------------------------------------
# Root Endpoint
# ----------------------------------------------------------------------

@app.get("/")
def read_root():
    """
    API root endpoint with welcome message and available routes.
    """
    return {
        "message": "System Monitoring API v2.1 with Historical Data Storage",
        "documentation": "/docs",
        "redoc": "/redoc",
        "categories": {
            "system": "/api/system/* - Real-time system metrics",
            "containers": "/api/containers/* - Docker container management",
            "network": "/api/network/* - Network monitoring",
            "logs": "/api/logs/* - Log aggregation and search",
            "advanced": "/api/advanced/* - Advanced metrics and alerts",
            "history": "/api/history/* - Historical data queries",
            "analytics": "/api/analytics/* - Trend analysis and forecasting"
        },
        "features": [
            "Real-time system monitoring",
            "Docker container management",
            "Network traffic analysis",
            "Log aggregation and search",
            "Advanced metrics and alerts",
            "Prometheus metrics export",
            "Historical data storage (SQLite)",
            "Automated metrics collection",
            "Trend analysis and forecasting",
            "Capacity planning"
        ],
        "database": {
            "location": "data/monitoring.db",
            "collection_interval": "5 minutes",
            "retention_period": "30 days"
        }
    }


@app.get("/health")
def health_check():
    """
    Health check endpoint for monitoring API availability.
    """
    return {"status": "healthy", "service": "System Monitoring API", "version": "2.1.0"}


# ----------------------------------------------------------------------
# Application Startup
# ----------------------------------------------------------------------
# To run this application:
#   uvicorn api:app --reload --port 3001 --host 0.0.0.0
# 
# For production:
#   uvicorn api:app --port 3001 --host 0.0.0.0 --workers 4
#
# Database will be automatically initialized on first startup.
# Metrics are collected every 5 minutes in the background.
# ----------------------------------------------------------------------
