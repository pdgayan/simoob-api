"""
Database Connection and Session Management
Handles SQLite database initialization, connection, and session management.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
import os
from pathlib import Path
from models import Base
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_DIR = Path("data")
DATABASE_FILE = DATABASE_DIR / "monitoring.db"
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

# Create engine with appropriate settings for SQLite
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Needed for SQLite with FastAPI
    poolclass=StaticPool,  # Use static pool for SQLite
    echo=False  # Set to True for SQL query logging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_database():
    """
    Initialize the database by creating all tables.
    Creates the data directory if it doesn't exist.
    """
    try:
        # Create data directory if it doesn't exist
        DATABASE_DIR.mkdir(exist_ok=True)
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        logger.info(f"Database initialized at: {DATABASE_FILE}")
        logger.info(f"Database size: {get_database_size()}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


def get_database_size() -> str:
    """
    Get the current size of the database file.
    
    Returns:
        Formatted string with database size
    """
    try:
        if DATABASE_FILE.exists():
            size_bytes = DATABASE_FILE.stat().st_size
            
            # Format size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.2f} {unit}"
                size_bytes /= 1024.0
            return f"{size_bytes:.2f} TB"
        return "0 B"
    except Exception as e:
        logger.error(f"Failed to get database size: {e}")
        return "Unknown"


@contextmanager
def get_db_session():
    """
    Context manager for database sessions.
    Ensures proper session cleanup.
    
    Usage:
        with get_db_session() as db:
            db.query(Model).all()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()


def get_db():
    """
    Dependency function for FastAPI endpoints.
    Provides database session to route handlers.
    
    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            return db.query(Model).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def cleanup_old_data(days_to_keep: int = 30) -> dict:
    """
    Clean up old data from the database.
    Removes records older than specified days.
    
    Args:
        days_to_keep: Number of days of data to retain
        
    Returns:
        Dictionary with cleanup statistics
    """
    from datetime import datetime, timedelta
    from models import (
        SystemMetric, ContainerMetric, NetworkMetric, 
        DiskIOMetric, ProcessSnapshot, ApiAccessLog
    )
    
    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
    
    stats = {}
    
    with get_db_session() as db:
        try:
            # Delete old records from each table
            tables = [
                ("system_metrics", SystemMetric),
                ("container_metrics", ContainerMetric),
                ("network_metrics", NetworkMetric),
                ("disk_io_metrics", DiskIOMetric),
                ("process_snapshots", ProcessSnapshot),
                ("api_access_logs", ApiAccessLog)
            ]
            
            for table_name, model in tables:
                deleted = db.query(model).filter(model.timestamp < cutoff_date).delete()
                stats[table_name] = deleted
                logger.info(f"Deleted {deleted} old records from {table_name}")
            
            db.commit()
            stats["status"] = "success"
            stats["cutoff_date"] = cutoff_date.isoformat()
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            stats["status"] = "failed"
            stats["error"] = str(e)
    
    return stats


def get_database_stats() -> dict:
    """
    Get statistics about database usage.
    
    Returns:
        Dictionary with record counts per table
    """
    from models import (
        SystemMetric, ContainerMetric, NetworkMetric, AlertHistory,
        ContainerEvent, ApiAccessLog, DiskIOMetric, ProcessSnapshot, ServiceStatus
    )
    
    stats = {}
    
    with get_db_session() as db:
        try:
            stats["system_metrics"] = db.query(SystemMetric).count()
            stats["container_metrics"] = db.query(ContainerMetric).count()
            stats["network_metrics"] = db.query(NetworkMetric).count()
            stats["alert_history"] = db.query(AlertHistory).count()
            stats["container_events"] = db.query(ContainerEvent).count()
            stats["api_access_logs"] = db.query(ApiAccessLog).count()
            stats["disk_io_metrics"] = db.query(DiskIOMetric).count()
            stats["process_snapshots"] = db.query(ProcessSnapshot).count()
            stats["service_status"] = db.query(ServiceStatus).count()
            
            # Calculate total records
            stats["total_records"] = sum(stats.values())
            
            # Get database file size
            stats["database_size"] = get_database_size()
            stats["database_path"] = str(DATABASE_FILE)
            
            # Get oldest and newest records
            oldest_system = db.query(SystemMetric).order_by(SystemMetric.timestamp.asc()).first()
            newest_system = db.query(SystemMetric).order_by(SystemMetric.timestamp.desc()).first()
            
            if oldest_system:
                stats["oldest_record"] = oldest_system.timestamp.isoformat()
            if newest_system:
                stats["newest_record"] = newest_system.timestamp.isoformat()
                
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            stats["error"] = str(e)
    
    return stats


def vacuum_database():
    """
    Vacuum the SQLite database to reclaim space.
    Should be run after cleanup operations.
    """
    try:
        with engine.connect() as conn:
            conn.execute("VACUUM")
        logger.info("Database vacuumed successfully")
        return {"status": "success", "message": "Database vacuumed"}
    except Exception as e:
        logger.error(f"Vacuum failed: {e}")
        return {"status": "failed", "error": str(e)}


def export_database_backup(backup_path: str = None) -> dict:
    """
    Create a backup of the database file.
    
    Args:
        backup_path: Optional custom backup path
        
    Returns:
        Dictionary with backup status
    """
    import shutil
    from datetime import datetime
    
    try:
        if backup_path is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_path = DATABASE_DIR / f"monitoring_backup_{timestamp}.db"
        
        shutil.copy2(DATABASE_FILE, backup_path)
        
        return {
            "status": "success",
            "backup_path": str(backup_path),
            "backup_size": get_database_size(),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return {"status": "failed", "error": str(e)}


# Enable foreign key constraints for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable foreign key constraints and other optimizations."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for better concurrency
    cursor.close()
