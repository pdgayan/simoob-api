"""
Advanced Metrics Router
Provides endpoints for advanced monitoring including sensors, filesystem details,
cgroups, alerts, and metrics export functionality.
"""

from fastapi import APIRouter, Query, Response, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any, List, Optional
from utils import run_command, get_timestamp, safe_parse_int, safe_parse_float
import json
import io
import csv

router = APIRouter(prefix="/api/advanced", tags=["advanced"])


@router.get("/sensors")
def get_all_sensors() -> Dict[str, Any]:
    """
    Get comprehensive sensor data including CPU/GPU temperatures, fan speeds, and voltages.
    Requires lm-sensors package.
    
    Returns:
        All available sensor readings
    """
    sensors_output = run_command("sensors -A -u 2>/dev/null")
    
    if "command not found" in sensors_output.lower():
        return {
            "error": "sensors command not found. Install lm-sensors: sudo apt install lm-sensors",
            "timestamp": get_timestamp()
        }
    
    # Parse detailed output
    sensors = {}
    current_chip = None
    current_feature = None
    
    for line in sensors_output.split("\n"):
        line = line.strip()
        if not line:
            continue
        
        # Chip header
        if not line.startswith(" ") and ":" not in line:
            current_chip = line
            sensors[current_chip] = {}
        # Feature
        elif line and not line.startswith(" ") and ":" in line:
            current_feature = line.split(":")[0]
            sensors[current_chip][current_feature] = {}
        # Reading
        elif line.startswith(" ") and ":" in line and current_feature:
            key, value = line.split(":", 1)
            sensors[current_chip][current_feature][key.strip()] = safe_parse_float(value.strip())
    
    return {
        "sensors": sensors,
        "timestamp": get_timestamp()
    }


@router.get("/filesystem/inodes")
def get_inode_usage() -> Dict[str, Any]:
    """
    Get inode usage statistics for all filesystems.
    
    Returns:
        Inode usage per filesystem
    """
    output = run_command("df -i")
    
    filesystems = []
    lines = output.split("\n")[1:]  # Skip header
    
    for line in lines:
        parts = line.split()
        if len(parts) >= 6:
            filesystems.append({
                "filesystem": parts[0],
                "inodes": safe_parse_int(parts[1]),
                "inodesUsed": safe_parse_int(parts[2]),
                "inodesFree": safe_parse_int(parts[3]),
                "inodesUsagePercent": parts[4],
                "mountPoint": parts[5] if len(parts) > 5 else ""
            })
    
    return {
        "filesystems": filesystems,
        "timestamp": get_timestamp()
    }


@router.get("/filesystem/mounts")
def get_mount_points() -> Dict[str, Any]:
    """
    Get all filesystem mount points with details.
    
    Returns:
        List of mounted filesystems with type and options
    """
    mounts_output = run_command("mount")
    findmnt_output = run_command("findmnt -J")
    
    mounts = []
    for line in mounts_output.split("\n"):
        if line.strip() and " on " in line:
            mounts.append({"mount": line.strip()})
    
    # Try to parse findmnt JSON output for better structure
    findmnt_data = None
    try:
        findmnt_data = json.loads(findmnt_output)
    except json.JSONDecodeError:
        pass
    
    return {
        "mounts": mounts,
        "findmnt": findmnt_data,
        "timestamp": get_timestamp()
    }


@router.get("/cgroups")
def get_cgroups_info() -> Dict[str, Any]:
    """
    Get cgroup (control groups) information for resource limiting.
    
    Returns:
        Cgroup hierarchy and resource limits
    """
    # Check cgroup version
    cgroup_version = run_command("stat -fc %T /sys/fs/cgroup/")
    
    # Get cgroup controllers
    controllers = run_command("cat /sys/fs/cgroup/cgroup.controllers 2>/dev/null")
    if not controllers:
        # v1 fallback
        controllers = run_command("ls /sys/fs/cgroup/")
    
    # Get Docker container cgroups if available
    docker_cgroups = run_command("find /sys/fs/cgroup -name 'docker' -type d 2>/dev/null | head -5")
    
    return {
        "version": cgroup_version.strip(),
        "controllers": controllers.split(),
        "dockerCgroups": docker_cgroups.split("\n") if docker_cgroups else [],
        "timestamp": get_timestamp()
    }


@router.get("/cgroups/container/{name}")
def get_container_cgroup_stats(name: str) -> Dict[str, Any]:
    """
    Get detailed cgroup statistics for a specific container.
    
    Args:
        name: Container name or ID
        
    Returns:
        CPU, memory, and I/O cgroup limits and usage
    """
    # Get container ID
    container_id = run_command(f"docker inspect -f '{{{{.Id}}}}' {name}").strip()
    
    if not container_id or "No such" in container_id:
        raise HTTPException(status_code=404, detail=f"Container '{name}' not found")
    
    # Find cgroup path
    cgroup_path = run_command(f"find /sys/fs/cgroup -name '*{container_id[:12]}*' -type d | head -1").strip()
    
    if not cgroup_path:
        return {
            "container": name,
            "error": "Cgroup path not found",
            "timestamp": get_timestamp()
        }
    
    # Read various cgroup stats
    stats = {}
    
    # Memory stats
    memory_limit = run_command(f"cat {cgroup_path}/memory.limit_in_bytes 2>/dev/null || cat {cgroup_path}/memory.max 2>/dev/null")
    memory_usage = run_command(f"cat {cgroup_path}/memory.usage_in_bytes 2>/dev/null || cat {cgroup_path}/memory.current 2>/dev/null")
    
    if memory_limit:
        stats["memoryLimit"] = safe_parse_int(memory_limit.strip())
    if memory_usage:
        stats["memoryUsage"] = safe_parse_int(memory_usage.strip())
    
    # CPU stats
    cpu_shares = run_command(f"cat {cgroup_path}/cpu.shares 2>/dev/null || cat {cgroup_path}/cpu.weight 2>/dev/null")
    if cpu_shares:
        stats["cpuShares"] = safe_parse_int(cpu_shares.strip())
    
    return {
        "container": name,
        "containerId": container_id,
        "cgroupPath": cgroup_path,
        "stats": stats,
        "timestamp": get_timestamp()
    }


@router.get("/alerts")
def get_system_alerts(
    cpu_threshold: float = Query(80.0, description="CPU usage threshold %"),
    memory_threshold: float = Query(80.0, description="Memory usage threshold %"),
    disk_threshold: float = Query(80.0, description="Disk usage threshold %")
) -> Dict[str, Any]:
    """
    Check system metrics against thresholds and generate alerts.
    
    Args:
        cpu_threshold: Alert if CPU usage exceeds this percentage
        memory_threshold: Alert if memory usage exceeds this percentage
        disk_threshold: Alert if disk usage exceeds this percentage
        
    Returns:
        List of active alerts based on thresholds
    """
    alerts = []
    
    # Check CPU
    import time
    with open("/proc/stat") as f:
        stat1 = f.readline().split()[1:]
    idle1 = int(stat1[3])
    total1 = sum(map(int, stat1))
    time.sleep(0.1)
    with open("/proc/stat") as f:
        stat2 = f.readline().split()[1:]
    idle2 = int(stat2[3])
    total2 = sum(map(int, stat2))
    cpu_usage = (1 - (idle2 - idle1) / (total2 - total1)) * 100
    
    if cpu_usage > cpu_threshold:
        alerts.append({
            "type": "CPU",
            "severity": "warning" if cpu_usage < 90 else "critical",
            "message": f"CPU usage is {cpu_usage:.1f}% (threshold: {cpu_threshold}%)",
            "value": cpu_usage,
            "threshold": cpu_threshold
        })
    
    # Check Memory
    memory = run_command("free -b")
    mem_line = [l for l in memory.split("\n") if "Mem:" in l]
    if mem_line:
        parts = mem_line[0].split()
        if len(parts) >= 3:
            total = safe_parse_int(parts[1])
            used = safe_parse_int(parts[2])
            mem_percent = (used / total * 100) if total > 0 else 0
            
            if mem_percent > memory_threshold:
                alerts.append({
                    "type": "Memory",
                    "severity": "warning" if mem_percent < 90 else "critical",
                    "message": f"Memory usage is {mem_percent:.1f}% (threshold: {memory_threshold}%)",
                    "value": mem_percent,
                    "threshold": memory_threshold
                })
    
    # Check Disk
    disk = run_command("df -h /")
    disk_line = [line for line in disk.split("\n") if "/dev/" in line or "overlay" in line]
    if disk_line:
        parts = disk_line[0].split()
        if len(parts) >= 5:
            disk_percent_str = parts[4].replace("%", "")
            disk_percent = safe_parse_float(disk_percent_str)
            
            if disk_percent > disk_threshold:
                alerts.append({
                    "type": "Disk",
                    "severity": "warning" if disk_percent < 90 else "critical",
                    "message": f"Disk usage is {disk_percent}% (threshold: {disk_threshold}%)",
                    "value": disk_percent,
                    "threshold": disk_threshold
                })
    
    return {
        "alerts": alerts,
        "alertCount": len(alerts),
        "thresholds": {
            "cpu": cpu_threshold,
            "memory": memory_threshold,
            "disk": disk_threshold
        },
        "timestamp": get_timestamp()
    }


@router.get("/metrics/export/json")
def export_metrics_json() -> Dict[str, Any]:
    """
    Export comprehensive system metrics in JSON format.
    
    Returns:
        Complete system snapshot with all metrics
    """
    # Gather all metrics
    metrics = {
        "timestamp": get_timestamp(),
        "system": {},
        "containers": [],
        "network": {},
        "metadata": {
            "exportFormat": "json",
            "version": "1.0"
        }
    }
    
    # System metrics
    uptime = run_command("uptime")
    metrics["system"]["uptime"] = uptime.strip()
    
    # CPU
    cpus = run_command("nproc").strip()
    metrics["system"]["cpuCores"] = cpus
    
    # Memory
    memory = run_command("free -h")
    metrics["system"]["memory"] = memory
    
    # Disk
    disk = run_command("df -h")
    metrics["system"]["disk"] = disk
    
    # Containers
    containers_cmd = run_command('docker ps --format "{{.Names}}|{{.Status}}|{{.Image}}"')
    for line in containers_cmd.split("\n"):
        if line.strip():
            parts = line.split("|")
            if len(parts) >= 3:
                metrics["containers"].append({
                    "name": parts[0],
                    "status": parts[1],
                    "image": parts[2]
                })
    
    # Network
    interfaces = run_command("ip -brief addr")
    metrics["network"]["interfaces"] = interfaces
    
    return metrics


@router.get("/metrics/export/csv")
def export_metrics_csv() -> Response:
    """
    Export system metrics in CSV format for analysis.
    
    Returns:
        CSV file with system metrics
    """
    # Gather container metrics
    cmd = 'docker stats --no-stream --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.NetIO}},{{.BlockIO}}"'
    output = run_command(cmd)
    
    # Create CSV
    csv_output = io.StringIO()
    csv_writer = csv.writer(csv_output)
    
    # Write header
    csv_writer.writerow(["Timestamp", "Container", "CPU %", "Memory Usage", "Network I/O", "Block I/O"])
    
    # Write data
    timestamp = get_timestamp()
    for line in output.split("\n"):
        if line.strip():
            parts = line.split(",")
            if len(parts) >= 5:
                csv_writer.writerow([timestamp] + parts)
    
    # Return as downloadable CSV
    csv_output.seek(0)
    return Response(
        content=csv_output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=metrics_{timestamp}.csv"}
    )


@router.get("/metrics/prometheus")
def export_prometheus_metrics() -> Response:
    """
    Export metrics in Prometheus format for monitoring integration.
    
    Returns:
        Metrics in Prometheus text exposition format
    """
    metrics_lines = []
    
    # System metrics
    metrics_lines.append("# HELP system_cpu_usage_percent Current CPU usage percentage")
    metrics_lines.append("# TYPE system_cpu_usage_percent gauge")
    
    # Get CPU
    import time
    with open("/proc/stat") as f:
        stat1 = f.readline().split()[1:]
    idle1 = int(stat1[3])
    total1 = sum(map(int, stat1))
    time.sleep(0.1)
    with open("/proc/stat") as f:
        stat2 = f.readline().split()[1:]
    idle2 = int(stat2[3])
    total2 = sum(map(int, stat2))
    cpu_usage = (1 - (idle2 - idle1) / (total2 - total1)) * 100
    metrics_lines.append(f"system_cpu_usage_percent {cpu_usage:.2f}")
    
    # Memory metrics
    memory = run_command("free -b")
    mem_line = [l for l in memory.split("\n") if "Mem:" in l]
    if mem_line:
        parts = mem_line[0].split()
        if len(parts) >= 7:
            metrics_lines.append("# HELP system_memory_total_bytes Total system memory")
            metrics_lines.append("# TYPE system_memory_total_bytes gauge")
            metrics_lines.append(f"system_memory_total_bytes {parts[1]}")
            
            metrics_lines.append("# HELP system_memory_used_bytes Used system memory")
            metrics_lines.append("# TYPE system_memory_used_bytes gauge")
            metrics_lines.append(f"system_memory_used_bytes {parts[2]}")
    
    # Container count
    container_count = run_command("docker ps -q | wc -l").strip()
    metrics_lines.append("# HELP docker_containers_running Number of running containers")
    metrics_lines.append("# TYPE docker_containers_running gauge")
    metrics_lines.append(f"docker_containers_running {container_count}")
    
    return Response(
        content="\n".join(metrics_lines) + "\n",
        media_type="text/plain"
    )


@router.get("/hardware/info")
def get_hardware_info() -> Dict[str, Any]:
    """
    Get detailed hardware information about the system.
    
    Returns:
        CPU, memory, disk, and other hardware details
    """
    hardware = {}
    
    # CPU info
    cpu_model = run_command("cat /proc/cpuinfo | grep 'model name' | head -1")
    if ":" in cpu_model:
        hardware["cpu"] = {
            "model": cpu_model.split(":")[1].strip(),
            "cores": run_command("nproc").strip(),
            "architecture": run_command("uname -m").strip()
        }
    
    # Memory info
    meminfo = run_command("cat /proc/meminfo")
    mem_total = None
    for line in meminfo.split("\n"):
        if "MemTotal" in line:
            parts = line.split()
            if len(parts) >= 2:
                mem_total = f"{safe_parse_int(parts[1]) / 1024 / 1024:.2f} GB"
                break
    hardware["memory"] = {"total": mem_total}
    
    # Disk info
    disks = run_command("lsblk -d -o NAME,SIZE,TYPE,MODEL")
    hardware["disks"] = disks
    
    # System info
    hardware["system"] = {
        "hostname": run_command("hostname").strip(),
        "kernel": run_command("uname -r").strip(),
        "os": run_command("cat /etc/os-release | grep PRETTY_NAME").split("=")[1].replace('"', '').strip() if "=" in run_command("cat /etc/os-release | grep PRETTY_NAME") else "Unknown"
    }
    
    return {
        "hardware": hardware,
        "timestamp": get_timestamp()
    }
