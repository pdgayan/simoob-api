"""
Database Models for System Monitoring
Defines SQLAlchemy ORM models for storing historical metrics, alerts, and logs.
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class SystemMetric(Base):
    """
    Store system-level metrics over time.
    Collected periodically for historical analysis.
    """
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # CPU metrics
    cpu_usage_percent = Column(Float)
    cpu_cores = Column(Integer)
    load_1min = Column(Float)
    load_5min = Column(Float)
    load_15min = Column(Float)
    
    # Memory metrics (in bytes)
    memory_total = Column(Integer)
    memory_used = Column(Integer)
    memory_free = Column(Integer)
    memory_available = Column(Integer)
    memory_percent = Column(Float)
    
    # Swap metrics
    swap_total = Column(Integer)
    swap_used = Column(Integer)
    swap_free = Column(Integer)
    swap_percent = Column(Float)
    
    # Disk metrics
    disk_total = Column(String)
    disk_used = Column(String)
    disk_free = Column(String)
    disk_percent = Column(String)
    
    # Additional info
    uptime = Column(String)
    hostname = Column(String)


class ContainerMetric(Base):
    """
    Store per-container resource usage metrics.
    """
    __tablename__ = "container_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Container identification
    container_id = Column(String, index=True)
    container_name = Column(String, index=True)
    image = Column(String)
    
    # Resource metrics
    cpu_percent = Column(String)  # Stored as string due to format like "25.4%"
    memory_usage = Column(String)  # e.g., "256MB / 2GB"
    memory_percent = Column(String)
    network_input = Column(String)
    network_output = Column(String)
    block_read = Column(String)
    block_write = Column(String)
    
    # Status
    status = Column(String)  # running, stopped, etc.
    state = Column(String)
    uptime = Column(String)


class NetworkMetric(Base):
    """
    Store network interface statistics over time.
    """
    __tablename__ = "network_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Interface info
    interface = Column(String, index=True)
    
    # Traffic metrics (in bytes)
    rx_bytes = Column(Integer)
    rx_packets = Column(Integer)
    rx_errors = Column(Integer)
    rx_dropped = Column(Integer)
    
    tx_bytes = Column(Integer)
    tx_packets = Column(Integer)
    tx_errors = Column(Integer)
    tx_dropped = Column(Integer)


class AlertHistory(Base):
    """
    Store triggered alerts for historical analysis.
    """
    __tablename__ = "alert_history"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Alert details
    alert_type = Column(String, index=True)  # CPU, Memory, Disk, etc.
    severity = Column(String, index=True)  # warning, critical
    message = Column(Text)
    
    # Metric values
    current_value = Column(Float)
    threshold_value = Column(Float)
    
    # Status
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    
    # Additional context
    resource_name = Column(String, nullable=True)  # e.g., container name
    extra_data = Column(JSON, nullable=True)  # Additional metadata (renamed from 'metadata' to avoid SQLAlchemy reserved word)


class ContainerEvent(Base):
    """
    Store container lifecycle events (start, stop, restart, remove).
    """
    __tablename__ = "container_events"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Container info
    container_id = Column(String, index=True)
    container_name = Column(String, index=True)
    image = Column(String)
    
    # Event details
    event_type = Column(String, index=True)  # start, stop, restart, create, remove
    status = Column(String)  # success, failed
    error_message = Column(Text, nullable=True)
    
    # Additional info
    triggered_by = Column(String, nullable=True)  # API, user, system
    extra_data = Column(JSON, nullable=True)  # Additional metadata (renamed from 'metadata' to avoid SQLAlchemy reserved word)


class ApiAccessLog(Base):
    """
    Store API access logs for auditing and analysis.
    """
    __tablename__ = "api_access_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Request details
    method = Column(String)
    endpoint = Column(String, index=True)
    path = Column(String)
    query_params = Column(String, nullable=True)
    
    # Response details
    status_code = Column(Integer)
    response_time_ms = Column(Float)
    
    # Client info
    client_ip = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    # Errors
    error_message = Column(Text, nullable=True)


class DiskIOMetric(Base):
    """
    Store disk I/O statistics over time.
    """
    __tablename__ = "disk_io_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Device info
    device = Column(String, index=True)
    
    # I/O metrics
    reads = Column(Integer)
    writes = Column(Integer)
    sectors_read = Column(Integer)
    sectors_written = Column(Integer)
    
    # Additional stats (if available from iostat)
    read_kb_per_sec = Column(Float, nullable=True)
    write_kb_per_sec = Column(Float, nullable=True)
    util_percent = Column(Float, nullable=True)


class ProcessSnapshot(Base):
    """
    Store periodic snapshots of top processes.
    """
    __tablename__ = "process_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Process info
    pid = Column(Integer)
    user = Column(String)
    cpu_percent = Column(Float)
    memory_percent = Column(Float)
    command = Column(String)
    
    # Additional details
    vsz = Column(Integer, nullable=True)  # Virtual memory size
    rss = Column(Integer, nullable=True)  # Resident set size
    state = Column(String, nullable=True)


class ServiceStatus(Base):
    """
    Track service status changes over time.
    """
    __tablename__ = "service_status"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Service info
    service_name = Column(String, index=True)
    status = Column(String)  # active, inactive, failed
    enabled = Column(Boolean)
    
    # Change detection
    status_changed = Column(Boolean, default=False)
    previous_status = Column(String, nullable=True)
