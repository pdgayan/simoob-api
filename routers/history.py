"""
History Router
Provides endpoints for querying historical metrics data from the database.
Allows users to view trends and historical performance over time.
"""

from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from database import get_db
from models import (
    SystemMetric, ContainerMetric, NetworkMetric, AlertHistory,
    ContainerEvent, DiskIOMetric, ProcessSnapshot, ServiceStatus
)

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/system")
def get_system_history(
    hours: int = Query(24, ge=1, le=168, description="Hours of history to retrieve (max 7 days)"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get historical system metrics for the specified time period.
    
    Args:
        hours: Number of hours of history to retrieve (1-168)
        
    Returns:
        Time-series data for CPU, memory, disk, and load
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    metrics = db.query(SystemMetric).filter(
        SystemMetric.timestamp >= cutoff_time
    ).order_by(SystemMetric.timestamp.asc()).all()
    
    if not metrics:
        return {
            "message": "No historical data available",
            "hours_requested": hours,
            "data": []
        }
    
    # Format data for charting
    data = []
    for m in metrics:
        data.append({
            "timestamp": m.timestamp.isoformat(),
            "cpu_percent": m.cpu_usage_percent,
            "memory_percent": m.memory_percent,
            "load_1min": m.load_1min,
            "load_5min": m.load_5min,
            "load_15min": m.load_15min,
            "disk_percent": m.disk_percent,
            "uptime": m.uptime
        })
    
    return {
        "hours_requested": hours,
        "records_count": len(data),
        "oldest_record": metrics[0].timestamp.isoformat(),
        "newest_record": metrics[-1].timestamp.isoformat(),
        "data": data
    }


@router.get("/system/cpu")
def get_cpu_history(
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get CPU usage history.
    
    Args:
        hours: Number of hours of history
        
    Returns:
        CPU usage time-series data
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    metrics = db.query(SystemMetric.timestamp, SystemMetric.cpu_usage_percent).filter(
        SystemMetric.timestamp >= cutoff_time
    ).order_by(SystemMetric.timestamp.asc()).all()
    
    data = [{"timestamp": m.timestamp.isoformat(), "cpu_percent": m.cpu_usage_percent} for m in metrics]
    
    # Calculate statistics
    cpu_values = [m.cpu_usage_percent for m in metrics if m.cpu_usage_percent]
    stats = {}
    if cpu_values:
        stats = {
            "min": round(min(cpu_values), 2),
            "max": round(max(cpu_values), 2),
            "avg": round(sum(cpu_values) / len(cpu_values), 2)
        }
    
    return {
        "hours": hours,
        "records": len(data),
        "statistics": stats,
        "data": data
    }


@router.get("/system/memory")
def get_memory_history(
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get memory usage history.
    
    Args:
        hours: Number of hours of history
        
    Returns:
        Memory usage time-series data
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    metrics = db.query(
        SystemMetric.timestamp,
        SystemMetric.memory_percent,
        SystemMetric.memory_used,
        SystemMetric.memory_total
    ).filter(
        SystemMetric.timestamp >= cutoff_time
    ).order_by(SystemMetric.timestamp.asc()).all()
    
    data = [{
        "timestamp": m.timestamp.isoformat(),
        "memory_percent": m.memory_percent,
        "memory_used_bytes": m.memory_used,
        "memory_total_bytes": m.memory_total
    } for m in metrics]
    
    # Calculate statistics
    mem_values = [m.memory_percent for m in metrics if m.memory_percent]
    stats = {}
    if mem_values:
        stats = {
            "min": round(min(mem_values), 2),
            "max": round(max(mem_values), 2),
            "avg": round(sum(mem_values) / len(mem_values), 2)
        }
    
    return {
        "hours": hours,
        "records": len(data),
        "statistics": stats,
        "data": data
    }


@router.get("/container/{name}")
def get_container_history(
    name: str,
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get historical metrics for a specific container.
    
    Args:
        name: Container name
        hours: Number of hours of history
        
    Returns:
        Container metrics time-series data
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    metrics = db.query(ContainerMetric).filter(
        ContainerMetric.container_name == name,
        ContainerMetric.timestamp >= cutoff_time
    ).order_by(ContainerMetric.timestamp.asc()).all()
    
    if not metrics:
        raise HTTPException(
            status_code=404,
            detail=f"No historical data found for container '{name}'"
        )
    
    data = [{
        "timestamp": m.timestamp.isoformat(),
        "cpu_percent": m.cpu_percent,
        "memory_usage": m.memory_usage,
        "memory_percent": m.memory_percent,
        "network_input": m.network_input,
        "network_output": m.network_output,
        "block_read": m.block_read,
        "block_write": m.block_write,
        "status": m.status
    } for m in metrics]
    
    return {
        "container_name": name,
        "container_id": metrics[0].container_id if metrics else None,
        "image": metrics[0].image if metrics else None,
        "hours": hours,
        "records": len(data),
        "data": data
    }


@router.get("/containers")
def get_all_containers_history(
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get historical metrics for all containers.
    
    Args:
        hours: Number of hours of history
        
    Returns:
        List of containers with their metrics
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    # Get unique container names
    container_names = db.query(ContainerMetric.container_name).filter(
        ContainerMetric.timestamp >= cutoff_time
    ).distinct().all()
    
    result = []
    for (name,) in container_names:
        metrics = db.query(ContainerMetric).filter(
            ContainerMetric.container_name == name,
            ContainerMetric.timestamp >= cutoff_time
        ).order_by(ContainerMetric.timestamp.desc()).limit(1).first()
        
        if metrics:
            result.append({
                "container_name": name,
                "container_id": metrics.container_id,
                "image": metrics.image,
                "latest_status": metrics.status,
                "latest_timestamp": metrics.timestamp.isoformat()
            })
    
    return result


@router.get("/network/{interface}")
def get_network_interface_history(
    interface: str,
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get historical network metrics for a specific interface.
    
    Args:
        interface: Network interface name (e.g., eth0, wlan0)
        hours: Number of hours of history
        
    Returns:
        Network traffic time-series data
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    metrics = db.query(NetworkMetric).filter(
        NetworkMetric.interface == interface,
        NetworkMetric.timestamp >= cutoff_time
    ).order_by(NetworkMetric.timestamp.asc()).all()
    
    if not metrics:
        raise HTTPException(
            status_code=404,
            detail=f"No historical data found for interface '{interface}'"
        )
    
    data = [{
        "timestamp": m.timestamp.isoformat(),
        "rx_bytes": m.rx_bytes,
        "tx_bytes": m.tx_bytes,
        "rx_packets": m.rx_packets,
        "tx_packets": m.tx_packets,
        "rx_errors": m.rx_errors,
        "tx_errors": m.tx_errors
    } for m in metrics]
    
    # Calculate bandwidth (bytes per second between samples)
    bandwidth_data = []
    for i in range(1, len(metrics)):
        time_diff = (metrics[i].timestamp - metrics[i-1].timestamp).total_seconds()
        if time_diff > 0:
            rx_bps = (metrics[i].rx_bytes - metrics[i-1].rx_bytes) / time_diff
            tx_bps = (metrics[i].tx_bytes - metrics[i-1].tx_bytes) / time_diff
            bandwidth_data.append({
                "timestamp": metrics[i].timestamp.isoformat(),
                "rx_bytes_per_sec": round(rx_bps, 2),
                "tx_bytes_per_sec": round(tx_bps, 2),
                "rx_mbps": round(rx_bps * 8 / 1_000_000, 2),
                "tx_mbps": round(tx_bps * 8 / 1_000_000, 2)
            })
    
    return {
        "interface": interface,
        "hours": hours,
        "records": len(data),
        "raw_data": data,
        "bandwidth": bandwidth_data
    }


@router.get("/alerts")
def get_alert_history(
    hours: int = Query(24, ge=1, le=720),
    severity: Optional[str] = Query(None, description="Filter by severity: warning, critical"),
    alert_type: Optional[str] = Query(None, description="Filter by type: CPU, Memory, Disk"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get historical alerts with optional filtering.
    
    Args:
        hours: Number of hours of history (up to 30 days)
        severity: Filter by severity level
        alert_type: Filter by alert type
        
    Returns:
        List of triggered alerts
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    query = db.query(AlertHistory).filter(AlertHistory.timestamp >= cutoff_time)
    
    if severity:
        query = query.filter(AlertHistory.severity == severity)
    
    if alert_type:
        query = query.filter(AlertHistory.alert_type == alert_type)
    
    alerts = query.order_by(AlertHistory.timestamp.desc()).all()
    
    data = [{
        "id": a.id,
        "timestamp": a.timestamp.isoformat(),
        "type": a.alert_type,
        "severity": a.severity,
        "message": a.message,
        "current_value": a.current_value,
        "threshold_value": a.threshold_value,
        "acknowledged": a.acknowledged,
        "resolved": a.resolved
    } for a in alerts]
    
    # Count by severity
    severity_counts = {}
    for alert in alerts:
        severity_counts[alert.severity] = severity_counts.get(alert.severity, 0) + 1
    
    return {
        "hours": hours,
        "total_alerts": len(data),
        "severity_counts": severity_counts,
        "filters": {
            "severity": severity,
            "alert_type": alert_type
        },
        "alerts": data
    }


@router.get("/disk-io")
def get_disk_io_history(
    device: Optional[str] = Query(None, description="Filter by device name"),
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get disk I/O history for all devices or a specific device.
    
    Args:
        device: Optional device name filter
        hours: Number of hours of history
        
    Returns:
        Disk I/O time-series data
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    query = db.query(DiskIOMetric).filter(DiskIOMetric.timestamp >= cutoff_time)
    
    if device:
        query = query.filter(DiskIOMetric.device == device)
    
    metrics = query.order_by(DiskIOMetric.timestamp.asc()).all()
    
    # Group by device
    devices_data = {}
    for m in metrics:
        if m.device not in devices_data:
            devices_data[m.device] = []
        
        devices_data[m.device].append({
            "timestamp": m.timestamp.isoformat(),
            "reads": m.reads,
            "writes": m.writes,
            "sectors_read": m.sectors_read,
            "sectors_written": m.sectors_written
        })
    
    return {
        "hours": hours,
        "devices": list(devices_data.keys()),
        "data": devices_data
    }


@router.get("/processes/top")
def get_top_processes_history(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get history of top processes by CPU usage.
    
    Args:
        hours: Number of hours of history
        limit: Number of top processes per snapshot
        
    Returns:
        Process snapshots over time
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    # Get unique timestamps
    timestamps = db.query(ProcessSnapshot.timestamp).filter(
        ProcessSnapshot.timestamp >= cutoff_time
    ).distinct().order_by(ProcessSnapshot.timestamp.desc()).all()
    
    snapshots = []
    for (ts,) in timestamps[:50]:  # Limit to 50 snapshots
        processes = db.query(ProcessSnapshot).filter(
            ProcessSnapshot.timestamp == ts
        ).order_by(ProcessSnapshot.cpu_percent.desc()).limit(limit).all()
        
        snapshots.append({
            "timestamp": ts.isoformat(),
            "processes": [{
                "pid": p.pid,
                "user": p.user,
                "cpu_percent": p.cpu_percent,
                "memory_percent": p.memory_percent,
                "command": p.command
            } for p in processes]
        })
    
    return {
        "hours": hours,
        "snapshot_count": len(snapshots),
        "snapshots": snapshots
    }


@router.get("/container-events")
def get_container_events(
    container_name: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=720),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get container lifecycle events (start, stop, restart, etc.).
    
    Args:
        container_name: Optional container name filter
        hours: Number of hours of history
        
    Returns:
        Container events log
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    query = db.query(ContainerEvent).filter(ContainerEvent.timestamp >= cutoff_time)
    
    if container_name:
        query = query.filter(ContainerEvent.container_name == container_name)
    
    events = query.order_by(ContainerEvent.timestamp.desc()).all()
    
    data = [{
        "id": e.id,
        "timestamp": e.timestamp.isoformat(),
        "container_name": e.container_name,
        "container_id": e.container_id,
        "image": e.image,
        "event_type": e.event_type,
        "status": e.status,
        "error_message": e.error_message
    } for e in events]
    
    return {
        "hours": hours,
        "total_events": len(data),
        "events": data
    }
