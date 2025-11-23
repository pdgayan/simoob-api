"""
Analytics Router
Provides advanced analytics endpoints for trend analysis, capacity planning,
and predictive insights based on historical metrics data.
"""

from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any, List
from datetime import datetime, timedelta
from database import get_db
from models import SystemMetric, ContainerMetric, NetworkMetric, AlertHistory

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/trends/system")
def analyze_system_trends(
    hours: int = Query(168, ge=24, le=720, description="Analysis period in hours (1-30 days)"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Analyze system resource trends over the specified period.
    Calculates moving averages, growth rates, and identifies patterns.
    
    Args:
        hours: Number of hours to analyze
        
    Returns:
        Comprehensive trend analysis for CPU, memory, disk, and load
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    metrics = db.query(SystemMetric).filter(
        SystemMetric.timestamp >= cutoff_time
    ).order_by(SystemMetric.timestamp.asc()).all()
    
    if len(metrics) < 10:
        return {
            "message": "Insufficient data for trend analysis (minimum 10 data points required)",
            "records": len(metrics)
        }
    
    # Calculate statistics for each metric
    cpu_values = [m.cpu_usage_percent for m in metrics if m.cpu_usage_percent]
    memory_values = [m.memory_percent for m in metrics if m.memory_percent]
    disk_values = [m.disk_percent for m in metrics if m.disk_percent]
    load_1min_values = [m.load_1min for m in metrics if m.load_1min]
    
    def calculate_trend_stats(values: List[float]) -> Dict[str, Any]:
        """Helper function to calculate comprehensive statistics"""
        if not values:
            return {}
        
        sorted_vals = sorted(values)
        n = len(values)
        
        # Basic statistics
        stats = {
            "min": round(min(values), 2),
            "max": round(max(values), 2),
            "avg": round(sum(values) / n, 2),
            "median": round(sorted_vals[n // 2], 2),
            "percentile_95": round(sorted_vals[int(n * 0.95)], 2),
            "percentile_99": round(sorted_vals[int(n * 0.99)], 2),
        }
        
        # Calculate standard deviation
        variance = sum((x - stats["avg"]) ** 2 for x in values) / n
        stats["std_dev"] = round(variance ** 0.5, 2)
        
        # Calculate trend direction (linear regression slope)
        x_values = list(range(len(values)))
        x_mean = sum(x_values) / len(x_values)
        y_mean = sum(values) / len(values)
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        slope = numerator / denominator if denominator != 0 else 0
        
        if slope > 0.1:
            trend = "increasing"
        elif slope < -0.1:
            trend = "decreasing"
        else:
            trend = "stable"
        
        stats["trend_direction"] = trend
        stats["trend_slope"] = round(slope, 4)
        
        return stats
    
    analysis = {
        "analysis_period_hours": hours,
        "data_points": len(metrics),
        "start_time": metrics[0].timestamp.isoformat(),
        "end_time": metrics[-1].timestamp.isoformat(),
        "cpu_usage": calculate_trend_stats(cpu_values),
        "memory_usage": calculate_trend_stats(memory_values),
        "disk_usage": calculate_trend_stats(disk_values),
        "load_average": calculate_trend_stats(load_1min_values)
    }
    
    # Identify peak usage periods
    peak_hours = _identify_peak_hours(metrics)
    analysis["peak_usage_hours"] = peak_hours
    
    return analysis


@router.get("/trends/container/{name}")
def analyze_container_trends(
    name: str,
    hours: int = Query(168, ge=24, le=720),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Analyze resource usage trends for a specific container.
    
    Args:
        name: Container name
        hours: Number of hours to analyze
        
    Returns:
        Container-specific trend analysis
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    metrics = db.query(ContainerMetric).filter(
        ContainerMetric.container_name == name,
        ContainerMetric.timestamp >= cutoff_time
    ).order_by(ContainerMetric.timestamp.asc()).all()
    
    if len(metrics) < 10:
        raise HTTPException(
            status_code=404,
            detail=f"Insufficient data for container '{name}' (minimum 10 data points required)"
        )
    
    cpu_values = [m.cpu_percent for m in metrics if m.cpu_percent]
    memory_values = [m.memory_usage for m in metrics if m.memory_usage]
    
    # Calculate growth rate
    if len(cpu_values) > 1:
        cpu_growth = ((cpu_values[-1] - cpu_values[0]) / cpu_values[0] * 100) if cpu_values[0] > 0 else 0
    else:
        cpu_growth = 0
    
    if len(memory_values) > 1:
        memory_growth = ((memory_values[-1] - memory_values[0]) / memory_values[0] * 100) if memory_values[0] > 0 else 0
    else:
        memory_growth = 0
    
    return {
        "container_name": name,
        "analysis_period_hours": hours,
        "data_points": len(metrics),
        "cpu_usage": {
            "min": round(min(cpu_values), 2) if cpu_values else 0,
            "max": round(max(cpu_values), 2) if cpu_values else 0,
            "avg": round(sum(cpu_values) / len(cpu_values), 2) if cpu_values else 0,
            "growth_rate_percent": round(cpu_growth, 2)
        },
        "memory_usage_bytes": {
            "min": min(memory_values) if memory_values else 0,
            "max": max(memory_values) if memory_values else 0,
            "avg": round(sum(memory_values) / len(memory_values), 2) if memory_values else 0,
            "growth_rate_percent": round(memory_growth, 2)
        },
        "uptime_changes": _count_container_restarts(metrics)
    }


@router.get("/capacity-planning")
def capacity_planning_analysis(
    forecast_days: int = Query(30, ge=7, le=90, description="Days to forecast"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Perform capacity planning analysis based on historical trends.
    Projects future resource needs using linear extrapolation.
    
    Args:
        forecast_days: Number of days to forecast into the future
        
    Returns:
        Capacity forecasts and recommendations
    """
    # Analyze last 30 days
    cutoff_time = datetime.utcnow() - timedelta(days=30)
    
    metrics = db.query(SystemMetric).filter(
        SystemMetric.timestamp >= cutoff_time
    ).order_by(SystemMetric.timestamp.asc()).all()
    
    if len(metrics) < 50:
        return {
            "message": "Insufficient data for capacity planning (minimum 50 data points required)",
            "recommendation": "Continue collecting data for accurate forecasting"
        }
    
    cpu_values = [m.cpu_usage_percent for m in metrics if m.cpu_usage_percent]
    memory_values = [m.memory_percent for m in metrics if m.memory_percent]
    disk_values = [m.disk_percent for m in metrics if m.disk_percent]
    
    def forecast_linear(values: List[float], days_ahead: int) -> Dict[str, Any]:
        """Simple linear forecasting"""
        n = len(values)
        x_values = list(range(n))
        x_mean = sum(x_values) / n
        y_mean = sum(values) / n
        
        # Calculate slope
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        slope = numerator / denominator if denominator != 0 else 0
        
        # Calculate intercept
        intercept = y_mean - slope * x_mean
        
        # Forecast
        samples_per_day = n / 30  # Assuming 30 days of data
        future_x = n + (days_ahead * samples_per_day)
        forecast_value = slope * future_x + intercept
        
        # Calculate confidence
        current_avg = sum(values[-10:]) / 10  # Last 10 samples
        
        return {
            "current_avg": round(current_avg, 2),
            "forecasted_value": round(max(0, min(100, forecast_value)), 2),  # Clamp 0-100
            "daily_growth_rate": round(slope * samples_per_day, 4),
            "days_until_80_percent": _calculate_days_to_threshold(current_avg, slope * samples_per_day, 80),
            "days_until_90_percent": _calculate_days_to_threshold(current_avg, slope * samples_per_day, 90)
        }
    
    cpu_forecast = forecast_linear(cpu_values, forecast_days)
    memory_forecast = forecast_linear(memory_values, forecast_days)
    disk_forecast = forecast_linear(disk_values, forecast_days)
    
    # Generate recommendations
    recommendations = []
    
    if cpu_forecast["forecasted_value"] > 80:
        recommendations.append({
            "resource": "CPU",
            "severity": "high",
            "message": f"CPU usage projected to reach {cpu_forecast['forecasted_value']}% in {forecast_days} days",
            "action": "Consider upgrading CPU resources or optimizing workloads"
        })
    
    if memory_forecast["forecasted_value"] > 80:
        recommendations.append({
            "resource": "Memory",
            "severity": "high",
            "message": f"Memory usage projected to reach {memory_forecast['forecasted_value']}% in {forecast_days} days",
            "action": "Consider adding more RAM or investigating memory leaks"
        })
    
    if disk_forecast["forecasted_value"] > 80:
        recommendations.append({
            "resource": "Disk",
            "severity": "high",
            "message": f"Disk usage projected to reach {disk_forecast['forecasted_value']}% in {forecast_days} days",
            "action": "Plan for storage expansion or implement data cleanup policies"
        })
    
    return {
        "forecast_period_days": forecast_days,
        "analysis_based_on_days": 30,
        "data_points": len(metrics),
        "cpu": cpu_forecast,
        "memory": memory_forecast,
        "disk": disk_forecast,
        "recommendations": recommendations
    }


@router.get("/peak-usage")
def identify_peak_usage_patterns(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Identify peak usage patterns by hour of day and day of week.
    Helps understand usage patterns for better resource scheduling.
    
    Args:
        days: Number of days to analyze
        
    Returns:
        Peak usage patterns and recommendations
    """
    cutoff_time = datetime.utcnow() - timedelta(days=days)
    
    metrics = db.query(SystemMetric).filter(
        SystemMetric.timestamp >= cutoff_time
    ).all()
    
    if not metrics:
        return {"message": "No data available for analysis"}
    
    # Group by hour of day
    hourly_usage = {hour: {"cpu": [], "memory": []} for hour in range(24)}
    
    for m in metrics:
        hour = m.timestamp.hour
        if m.cpu_usage_percent:
            hourly_usage[hour]["cpu"].append(m.cpu_usage_percent)
        if m.memory_percent:
            hourly_usage[hour]["memory"].append(m.memory_percent)
    
    # Calculate averages per hour
    hourly_averages = []
    for hour in range(24):
        cpu_avg = sum(hourly_usage[hour]["cpu"]) / len(hourly_usage[hour]["cpu"]) if hourly_usage[hour]["cpu"] else 0
        memory_avg = sum(hourly_usage[hour]["memory"]) / len(hourly_usage[hour]["memory"]) if hourly_usage[hour]["memory"] else 0
        
        hourly_averages.append({
            "hour": hour,
            "hour_label": f"{hour:02d}:00",
            "avg_cpu": round(cpu_avg, 2),
            "avg_memory": round(memory_avg, 2),
            "sample_count": len(hourly_usage[hour]["cpu"])
        })
    
    # Find peak hours
    peak_cpu_hour = max(hourly_averages, key=lambda x: x["avg_cpu"])
    peak_memory_hour = max(hourly_averages, key=lambda x: x["avg_memory"])
    
    # Find off-peak hours (lowest usage)
    offpeak_hour = min(hourly_averages, key=lambda x: x["avg_cpu"] + x["avg_memory"])
    
    return {
        "analysis_period_days": days,
        "total_samples": len(metrics),
        "hourly_patterns": hourly_averages,
        "peak_cpu_hour": {
            "hour": peak_cpu_hour["hour_label"],
            "avg_cpu_percent": peak_cpu_hour["avg_cpu"]
        },
        "peak_memory_hour": {
            "hour": peak_memory_hour["hour_label"],
            "avg_memory_percent": peak_memory_hour["avg_memory"]
        },
        "recommended_maintenance_window": {
            "hour": offpeak_hour["hour_label"],
            "avg_cpu_percent": offpeak_hour["avg_cpu"],
            "avg_memory_percent": offpeak_hour["avg_memory"]
        }
    }


@router.get("/alerts/summary")
def alert_summary_analytics(
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Generate comprehensive alert analytics and patterns.
    
    Args:
        days: Number of days to analyze
        
    Returns:
        Alert statistics, patterns, and trends
    """
    cutoff_time = datetime.utcnow() - timedelta(days=days)
    
    alerts = db.query(AlertHistory).filter(
        AlertHistory.timestamp >= cutoff_time
    ).all()
    
    if not alerts:
        return {
            "message": "No alerts in the specified period",
            "days": days
        }
    
    # Count by severity
    severity_counts = {}
    for alert in alerts:
        severity_counts[alert.severity] = severity_counts.get(alert.severity, 0) + 1
    
    # Count by type
    type_counts = {}
    for alert in alerts:
        type_counts[alert.alert_type] = type_counts.get(alert.alert_type, 0) + 1
    
    # Most frequent alerts
    most_frequent = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Calculate alert rate (alerts per day)
    alert_rate = len(alerts) / days
    
    # Identify trends
    recent_alerts = [a for a in alerts if a.timestamp >= datetime.utcnow() - timedelta(days=7)]
    older_alerts = [a for a in alerts if a.timestamp < datetime.utcnow() - timedelta(days=7)]
    
    recent_rate = len(recent_alerts) / 7 if days >= 7 else len(recent_alerts) / days
    older_rate = len(older_alerts) / (days - 7) if days > 7 else 0
    
    if older_rate > 0:
        trend = "increasing" if recent_rate > older_rate * 1.2 else "decreasing" if recent_rate < older_rate * 0.8 else "stable"
    else:
        trend = "stable"
    
    return {
        "analysis_period_days": days,
        "total_alerts": len(alerts),
        "alerts_per_day": round(alert_rate, 2),
        "severity_breakdown": severity_counts,
        "alert_type_breakdown": type_counts,
        "most_frequent_alerts": [{"type": t, "count": c} for t, c in most_frequent[:5]],
        "trend": {
            "direction": trend,
            "recent_7days_rate": round(recent_rate, 2),
            "older_period_rate": round(older_rate, 2)
        },
        "acknowledged_count": sum(1 for a in alerts if a.acknowledged),
        "resolved_count": sum(1 for a in alerts if a.resolved)
    }


@router.get("/network/bandwidth-trends")
def analyze_network_bandwidth_trends(
    interface: str = Query(..., description="Network interface name"),
    hours: int = Query(24, ge=6, le=168),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Analyze network bandwidth usage trends for capacity planning.
    
    Args:
        interface: Network interface name
        hours: Number of hours to analyze
        
    Returns:
        Bandwidth trend analysis
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    metrics = db.query(NetworkMetric).filter(
        NetworkMetric.interface == interface,
        NetworkMetric.timestamp >= cutoff_time
    ).order_by(NetworkMetric.timestamp.asc()).all()
    
    if len(metrics) < 10:
        raise HTTPException(
            status_code=404,
            detail=f"Insufficient data for interface '{interface}'"
        )
    
    # Calculate bandwidth between samples
    bandwidth_samples = []
    for i in range(1, len(metrics)):
        time_diff = (metrics[i].timestamp - metrics[i-1].timestamp).total_seconds()
        if time_diff > 0:
            rx_bps = (metrics[i].rx_bytes - metrics[i-1].rx_bytes) / time_diff
            tx_bps = (metrics[i].tx_bytes - metrics[i-1].tx_bytes) / time_diff
            bandwidth_samples.append({
                "rx_mbps": rx_bps * 8 / 1_000_000,
                "tx_mbps": tx_bps * 8 / 1_000_000,
                "total_mbps": (rx_bps + tx_bps) * 8 / 1_000_000
            })
    
    if not bandwidth_samples:
        return {"message": "Unable to calculate bandwidth"}
    
    total_bandwidth = [s["total_mbps"] for s in bandwidth_samples]
    
    return {
        "interface": interface,
        "analysis_period_hours": hours,
        "bandwidth_mbps": {
            "min": round(min(total_bandwidth), 2),
            "max": round(max(total_bandwidth), 2),
            "avg": round(sum(total_bandwidth) / len(total_bandwidth), 2),
            "peak_utilization": round(max(total_bandwidth), 2)
        },
        "total_data_transferred": {
            "rx_gb": round(metrics[-1].rx_bytes / 1_000_000_000, 2),
            "tx_gb": round(metrics[-1].tx_bytes / 1_000_000_000, 2)
        },
        "error_rate": {
            "rx_errors": metrics[-1].rx_errors,
            "tx_errors": metrics[-1].tx_errors,
            "total_packets": metrics[-1].rx_packets + metrics[-1].tx_packets,
            "error_rate_percent": round(
                (metrics[-1].rx_errors + metrics[-1].tx_errors) / 
                max(1, metrics[-1].rx_packets + metrics[-1].tx_packets) * 100, 4
            )
        }
    }


# Helper functions

def _identify_peak_hours(metrics: List[SystemMetric]) -> Dict[str, Any]:
    """Identify hours with highest resource usage"""
    hourly_data = {}
    
    for m in metrics:
        hour = m.timestamp.hour
        if hour not in hourly_data:
            hourly_data[hour] = []
        
        if m.cpu_usage_percent:
            hourly_data[hour].append(m.cpu_usage_percent)
    
    hourly_averages = {hour: sum(values) / len(values) for hour, values in hourly_data.items() if values}
    
    if not hourly_averages:
        return {}
    
    peak_hour = max(hourly_averages.items(), key=lambda x: x[1])
    
    return {
        "peak_hour": f"{peak_hour[0]:02d}:00",
        "avg_usage": round(peak_hour[1], 2)
    }


def _count_container_restarts(metrics: List[ContainerMetric]) -> int:
    """Count how many times container status changed"""
    status_changes = 0
    for i in range(1, len(metrics)):
        if metrics[i].status != metrics[i-1].status:
            status_changes += 1
    
    return status_changes


def _calculate_days_to_threshold(current: float, daily_growth: float, threshold: float) -> int:
    """Calculate days until a threshold is reached"""
    if daily_growth <= 0 or current >= threshold:
        return -1  # Already above threshold or declining
    
    days = (threshold - current) / daily_growth
    return int(days) if days > 0 else -1
