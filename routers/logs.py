"""
Logs and Events Router
Provides endpoints for accessing system logs, Docker logs, container logs,
application logs, and filtered error logs.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any, List, Optional
from utils import run_command, get_timestamp
import re

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/system")
def get_system_logs(
    lines: int = Query(100, ge=1, le=10000),
    priority: Optional[str] = Query(None, description="Log priority: emerg, alert, crit, err, warning, notice, info, debug"),
    since: Optional[str] = Query(None, description="Show logs since (e.g., '1 hour ago', '2023-01-01', 'yesterday')")
) -> Dict[str, Any]:
    """
    Get system logs from journalctl with optional filtering.
    
    Args:
        lines: Number of log lines to retrieve
        priority: Filter by log priority level
        since: Show logs since specified time
        
    Returns:
        System logs with filtering applied
    """
    cmd = f"journalctl -n {lines} --no-pager"
    
    # Add priority filter
    if priority:
        valid_priorities = ["emerg", "alert", "crit", "err", "warning", "notice", "info", "debug"]
        if priority.lower() in valid_priorities:
            cmd += f" -p {priority}"
    
    # Add time filter
    if since:
        cmd += f" --since '{since}'"
    
    output = run_command(cmd)
    log_lines = output.split("\n")
    
    return {
        "logs": log_lines,
        "count": len(log_lines),
        "linesRequested": lines,
        "filters": {
            "priority": priority,
            "since": since
        },
        "timestamp": get_timestamp()
    }


@router.get("/docker")
def get_docker_logs(lines: int = Query(50, ge=1, le=1000)) -> Dict[str, Any]:
    """
    Get Docker service logs from journalctl.
    
    Args:
        lines: Number of log lines to retrieve
        
    Returns:
        Docker daemon logs
    """
    output = run_command(f"journalctl -u docker --no-pager -n {lines}")
    log_lines = output.split("\n")
    
    return {
        "service": "docker",
        "logs": log_lines,
        "count": len(log_lines),
        "timestamp": get_timestamp()
    }


@router.get("/container/{name}")
def get_container_logs(
    name: str,
    lines: int = Query(100, ge=1, le=10000),
    since: Optional[str] = Query(None, description="Show logs since (e.g., '1h', '30m', '2023-01-01T00:00:00')"),
    timestamps: bool = Query(False, description="Show timestamps")
) -> Dict[str, Any]:
    """
    Get logs from a specific container with filtering options.
    
    Args:
        name: Container name or ID
        lines: Number of log lines to retrieve
        since: Show logs since specified time
        timestamps: Include timestamps in log output
        
    Returns:
        Container logs
    """
    cmd = f"docker logs {name} --tail {lines}"
    
    if since:
        cmd += f" --since {since}"
    
    if timestamps:
        cmd += " --timestamps"
    
    cmd += " 2>&1"  # Capture both stdout and stderr
    
    output = run_command(cmd)
    
    if "No such container" in output:
        raise HTTPException(status_code=404, detail=f"Container '{name}' not found")
    
    log_lines = output.split("\n")
    
    return {
        "container": name,
        "logs": log_lines,
        "count": len(log_lines),
        "filters": {
            "lines": lines,
            "since": since,
            "timestamps": timestamps
        },
        "timestamp": get_timestamp()
    }


@router.get("/app/{service}")
def get_application_logs(
    service: str,
    lines: int = Query(100, ge=1, le=10000)
) -> Dict[str, Any]:
    """
    Get logs for a specific system service.
    
    Args:
        service: Service name (e.g., nginx, mysql, ssh)
        lines: Number of log lines to retrieve
        
    Returns:
        Service logs from journalctl
    """
    # Validate service name to prevent command injection
    if not re.match(r'^[a-zA-Z0-9_-]+$', service):
        raise HTTPException(status_code=400, detail="Invalid service name format")
    
    output = run_command(f"journalctl -u {service} --no-pager -n {lines}")
    
    if "No entries" in output or "Failed to" in output:
        return {
            "service": service,
            "logs": [],
            "message": f"No logs found for service '{service}' or service does not exist",
            "timestamp": get_timestamp()
        }
    
    log_lines = output.split("\n")
    
    return {
        "service": service,
        "logs": log_lines,
        "count": len(log_lines),
        "timestamp": get_timestamp()
    }


@router.get("/errors")
def get_error_logs(
    lines: int = Query(100, ge=1, le=10000),
    severity: str = Query("err", description="Minimum severity: emerg, alert, crit, err")
) -> Dict[str, Any]:
    """
    Get filtered error logs from system journal.
    
    Args:
        lines: Number of log lines to retrieve
        severity: Minimum severity level to include
        
    Returns:
        Filtered error logs
    """
    valid_severities = ["emerg", "alert", "crit", "err"]
    if severity.lower() not in valid_severities:
        severity = "err"
    
    output = run_command(f"journalctl -p {severity} -n {lines} --no-pager")
    log_lines = output.split("\n")
    
    # Parse and categorize errors
    errors = []
    for line in log_lines:
        if line.strip():
            # Try to extract timestamp, hostname, service, and message
            match = re.match(r'(\w+\s+\d+\s+[\d:]+)\s+(\S+)\s+(\S+?):\s+(.+)', line)
            if match:
                errors.append({
                    "timestamp": match.group(1),
                    "hostname": match.group(2),
                    "service": match.group(3),
                    "message": match.group(4),
                    "rawLog": line
                })
            else:
                errors.append({
                    "rawLog": line
                })
    
    return {
        "errors": errors,
        "count": len(errors),
        "severity": severity,
        "timestamp": get_timestamp()
    }


@router.get("/kernel")
def get_kernel_logs(lines: int = Query(100, ge=1, le=1000)) -> Dict[str, Any]:
    """
    Get kernel logs using dmesg.
    
    Args:
        lines: Number of log lines to retrieve
        
    Returns:
        Kernel ring buffer logs
    """
    output = run_command(f"dmesg | tail -n {lines}")
    log_lines = output.split("\n")
    
    return {
        "logs": log_lines,
        "count": len(log_lines),
        "source": "dmesg",
        "timestamp": get_timestamp()
    }


@router.get("/auth")
def get_authentication_logs(lines: int = Query(50, ge=1, le=1000)) -> Dict[str, Any]:
    """
    Get authentication and authorization logs (login attempts, sudo usage, etc.).
    
    Args:
        lines: Number of log lines to retrieve
        
    Returns:
        Authentication logs
    """
    # Try to read auth.log or secure log depending on distribution
    auth_log = run_command(f"tail -n {lines} /var/log/auth.log 2>/dev/null")
    
    if not auth_log:
        # Try alternative location
        auth_log = run_command(f"tail -n {lines} /var/log/secure 2>/dev/null")
    
    if not auth_log:
        # Fallback to journalctl
        auth_log = run_command(f"journalctl _COMM=sshd _COMM=sudo --no-pager -n {lines}")
    
    log_lines = auth_log.split("\n") if auth_log else []
    
    # Parse for failed login attempts
    failed_logins = []
    successful_logins = []
    
    for line in log_lines:
        if "Failed password" in line or "authentication failure" in line.lower():
            failed_logins.append(line)
        elif "Accepted password" in line or "session opened" in line:
            successful_logins.append(line)
    
    return {
        "logs": log_lines,
        "count": len(log_lines),
        "failedLogins": failed_logins,
        "successfulLogins": successful_logins,
        "timestamp": get_timestamp()
    }


@router.get("/search")
def search_logs(
    query: str = Query(..., min_length=1),
    lines: int = Query(100, ge=1, le=10000),
    case_sensitive: bool = Query(False)
) -> Dict[str, Any]:
    """
    Search system logs for specific text pattern.
    
    Args:
        query: Text to search for in logs
        lines: Number of recent log lines to search
        case_sensitive: Whether search should be case-sensitive
        
    Returns:
        Matching log entries
    """
    grep_flag = "" if case_sensitive else "-i"
    
    # Escape special characters for grep
    escaped_query = query.replace("'", "'\\''")
    
    cmd = f"journalctl -n {lines} --no-pager | grep {grep_flag} '{escaped_query}'"
    output = run_command(cmd)
    
    matches = output.split("\n") if output else []
    matches = [m for m in matches if m.strip()]
    
    return {
        "query": query,
        "matches": matches,
        "matchCount": len(matches),
        "caseSensitive": case_sensitive,
        "timestamp": get_timestamp()
    }


@router.get("/stats")
def get_log_statistics() -> Dict[str, Any]:
    """
    Get statistics about system logs (counts by priority, service, etc.).
    
    Returns:
        Log statistics and summary
    """
    # Get log counts by priority
    priority_stats = {}
    priorities = ["emerg", "alert", "crit", "err", "warning", "notice", "info"]
    
    for priority in priorities:
        count_output = run_command(f"journalctl -p {priority} --no-pager | wc -l")
        priority_stats[priority] = int(count_output.strip()) if count_output.strip().isdigit() else 0
    
    # Get most active services
    services_output = run_command("journalctl --no-pager -n 1000 | grep -oP '\\w+\\[\\d+\\]:' | sort | uniq -c | sort -rn | head -10")
    
    top_services = []
    for line in services_output.split("\n"):
        if line.strip():
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                count = parts[0]
                service = parts[1].replace("[", " [").split("[")[0].strip()
                top_services.append({
                    "service": service,
                    "logCount": int(count) if count.isdigit() else 0
                })
    
    # Get journal disk usage
    disk_usage = run_command("journalctl --disk-usage")
    
    return {
        "priorityStats": priority_stats,
        "topServices": top_services,
        "diskUsage": disk_usage.strip(),
        "timestamp": get_timestamp()
    }


@router.get("/tail/{service}")
def tail_service_logs(
    service: str,
    lines: int = Query(20, ge=1, le=100)
) -> Dict[str, Any]:
    """
    Get the most recent logs for a service (similar to tail -f but single snapshot).
    
    Args:
        service: Service name
        lines: Number of recent lines
        
    Returns:
        Most recent log entries
    """
    if not re.match(r'^[a-zA-Z0-9_-]+$', service):
        raise HTTPException(status_code=400, detail="Invalid service name format")
    
    output = run_command(f"journalctl -u {service} --no-pager -n {lines} --output=short-precise")
    log_lines = output.split("\n")
    
    return {
        "service": service,
        "logs": log_lines,
        "count": len(log_lines),
        "timestamp": get_timestamp()
    }
