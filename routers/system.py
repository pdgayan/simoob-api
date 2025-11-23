"""
System-Level Metrics Router
Provides endpoints for monitoring system resources including CPU, memory, disk, 
processes, network interfaces, services, and more.
"""

from fastapi import APIRouter, Query
from typing import Dict, Any, List
import os
import time
from utils import run_command, get_timestamp, parse_percentage, safe_parse_float, safe_parse_int

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/stats")
def get_system_stats() -> Dict[str, Any]:
    """
    Get comprehensive system statistics including disk, memory, CPU, uptime, and load averages.
    
    Returns:
        Complete system overview with all major metrics
    """
    disk = run_command("df -h /")
    memory = run_command("free -h")
    uptime = run_command("uptime")
    uname = run_command("uname -a")
    cpu_model = run_command("cat /proc/cpuinfo | grep 'model name' | head -1")
    core_count = run_command("nproc")
    os_name_raw = run_command('cat /etc/os-release | grep PRETTY_NAME')
    
    # Parse OS name safely
    os_name = "Unknown"
    if "=" in os_name_raw:
        os_name = os_name_raw.split("=")[1].replace('"', '').strip()

    # Parse disk usage
    disk_line = [line for line in disk.split("\n") if "/dev/" in line or "overlay" in line]
    disk_stats = {}
    if disk_line:
        parts = disk_line[0].split()
        if len(parts) >= 5:
            disk_stats = {
                "filesystem": parts[0],
                "total": parts[1],
                "used": parts[2],
                "available": parts[3],
                "percent": parts[4],
            }

    # Parse memory usage
    mem_line = [l for l in memory.split("\n") if "Mem:" in l]
    memory_stats = {}
    if mem_line:
        parts = mem_line[0].split()
        if len(parts) >= 7:
            memory_stats = {
                "total": parts[1],
                "used": parts[2],
                "free": parts[3],
                "available": parts[6]
            }

    # Parse load average
    import re
    load = re.findall(r"load average: ([\d.]+), ([\d.]+), ([\d.]+)", uptime)
    load_avg = None
    if load:
        load_avg = {
            "1min": float(load[0][0]),
            "5min": float(load[0][1]),
            "15min": float(load[0][2]),
        }

    # Extract uptime
    up = re.findall(r"up (.*?),", uptime)
    uptime_str = up[0] if up else "Unknown"

    return {
        "disk": disk_stats,
        "memory": memory_stats,
        "uptime": uptime_str,
        "loadAverage": load_avg,
        "cpu": {
            "model": cpu_model.split(":")[1].strip() if ":" in cpu_model else cpu_model,
            "cores": core_count.strip()
        },
        "os": os_name,
        "hostname": uname.split()[1] if uname.split() else "unknown",
        "timestamp": get_timestamp()
    }


@router.get("/cpu")
def get_cpu_usage() -> Dict[str, Any]:
    """
    Get current CPU usage percentage.
    Calculates usage by sampling /proc/stat twice with a short interval.
    
    Returns:
        Current CPU usage percentage and timestamp
    """
    try:
        # Read first sample
        with open("/proc/stat") as f:
            stat1 = f.readline().split()[1:]
        idle1 = int(stat1[3])
        total1 = sum(map(int, stat1))

        # Wait briefly
        time.sleep(0.1)

        # Read second sample
        with open("/proc/stat") as f:
            stat2 = f.readline().split()[1:]
        idle2 = int(stat2[3])
        total2 = sum(map(int, stat2))

        # Calculate CPU usage
        cpu_usage = (1 - (idle2 - idle1) / (total2 - total1)) * 100

        return {
            "cpuUsage": round(cpu_usage, 1),
            "cores": os.cpu_count(),
            "timestamp": get_timestamp()
        }
    except Exception as e:
        return {"error": str(e), "cpuUsage": 0, "timestamp": get_timestamp()}


@router.get("/memory")
def get_memory_usage() -> Dict[str, Any]:
    """
    Get detailed memory usage statistics including RAM and swap.
    
    Returns:
        Memory usage with total, used, free, available, cached, and swap info
    """
    memory = run_command("free -b")  # Get in bytes for precise calculation
    lines = memory.split("\n")
    
    mem_stats = {}
    swap_stats = {}
    
    for line in lines:
        if "Mem:" in line:
            parts = line.split()
            if len(parts) >= 7:
                total = safe_parse_int(parts[1])
                used = safe_parse_int(parts[2])
                free = safe_parse_int(parts[3])
                available = safe_parse_int(parts[6])
                cached = safe_parse_int(parts[5]) if len(parts) > 5 else 0
                
                mem_stats = {
                    "total": total,
                    "used": used,
                    "free": free,
                    "available": available,
                    "cached": cached,
                    "usagePercent": round((used / total * 100), 2) if total > 0 else 0
                }
        elif "Swap:" in line:
            parts = line.split()
            if len(parts) >= 4:
                swap_total = safe_parse_int(parts[1])
                swap_used = safe_parse_int(parts[2])
                swap_free = safe_parse_int(parts[3])
                
                swap_stats = {
                    "total": swap_total,
                    "used": swap_used,
                    "free": swap_free,
                    "usagePercent": round((swap_used / swap_total * 100), 2) if swap_total > 0 else 0
                }
    
    return {
        "memory": mem_stats,
        "swap": swap_stats,
        "timestamp": get_timestamp()
    }


@router.get("/disk-usage")
def get_disk_usage() -> Dict[str, Any]:
    """
    Get disk usage for important directories.
    
    Returns:
        Disk usage by directory with sizes
    """
    output = run_command("du -sh /var/lib/docker /home /tmp /var/log 2>/dev/null | sort -hr")
    
    dirs = []
    for line in output.split("\n"):
        if line.strip() and "\t" in line:
            size, path = line.split("\t", 1)
            dirs.append({"size": size.strip(), "path": path.strip()})

    return {
        "directories": dirs,
        "timestamp": get_timestamp()
    }


@router.get("/load")
def get_system_load() -> Dict[str, Any]:
    """
    Get system load averages for 1, 5, and 15 minutes.
    
    Returns:
        Load averages and CPU core count for context
    """
    uptime = run_command("uptime")
    
    import re
    load = re.findall(r"load average: ([\d.]+), ([\d.]+), ([\d.]+)", uptime)
    
    if load:
        return {
            "loadAverage": {
                "1min": float(load[0][0]),
                "5min": float(load[0][1]),
                "15min": float(load[0][2])
            },
            "cpuCores": os.cpu_count(),
            "timestamp": get_timestamp()
        }
    
    return {"error": "Could not parse load average", "timestamp": get_timestamp()}


@router.get("/processes")
def get_top_processes() -> Dict[str, Any]:
    """
    Get top processes sorted by CPU usage.
    
    Returns:
        List of top 20 processes with CPU, memory, and command info
    """
    output = run_command("ps aux --sort=-%cpu | head -21")  # +1 for header
    lines = output.split("\n")
    
    proc_list = []
    for line in lines[1:]:  # Skip header
        parts = line.split()
        if len(parts) >= 11:
            proc_list.append({
                "user": parts[0],
                "pid": parts[1],
                "cpu": parts[2],
                "memory": parts[3],
                "vsz": parts[4],
                "rss": parts[5],
                "tty": parts[6],
                "stat": parts[7],
                "start": parts[8],
                "time": parts[9],
                "command": " ".join(parts[10:])
            })

    return {
        "processes": proc_list,
        "count": len(proc_list),
        "timestamp": get_timestamp()
    }


@router.get("/ports")
def get_open_ports() -> Dict[str, Any]:
    """
    Get list of open TCP/UDP ports in LISTEN state.
    
    Returns:
        List of listening ports with protocol and address info
    """
    output = run_command('ss -tuln | grep LISTEN')
    
    ports = []
    for line in output.split("\n"):
        parts = line.split()
        if len(parts) >= 5:
            ports.append({
                "protocol": parts[0],
                "recvQ": parts[1],
                "sendQ": parts[2],
                "localAddress": parts[4],
                "state": parts[1] if len(parts) > 1 else "LISTEN"
            })

    return {
        "openPorts": ports,
        "count": len(ports),
        "timestamp": get_timestamp()
    }


@router.get("/logs")
def get_system_logs(lines: int = Query(50, ge=1, le=1000)) -> Dict[str, Any]:
    """
    Get recent system logs from journalctl.
    
    Args:
        lines: Number of log lines to retrieve (1-1000)
        
    Returns:
        System logs with line count
    """
    output = run_command(f"journalctl -n {lines} --no-pager")
    log_lines = output.split("\n")
    
    return {
        "logs": log_lines,
        "count": len(log_lines),
        "linesRequested": lines,
        "timestamp": get_timestamp()
    }


@router.get("/network")
def get_network_info() -> Dict[str, Any]:
    """
    Get network interface information including IP addresses and status.
    
    Returns:
        Network interface details
    """
    output = run_command('ip addr show')
    interfaces_raw = run_command('ip -o link show')
    
    return {
        "fullOutput": output,
        "interfaces": interfaces_raw.split("\n"),
        "timestamp": get_timestamp()
    }


@router.get("/users")
def get_logged_users() -> Dict[str, Any]:
    """
    Get list of currently logged-in users and their sessions.
    
    Returns:
        Active user sessions with login time and terminal
    """
    # Get users with 'who' command
    who_output = run_command("who")
    # Get more detailed info with 'w' command
    w_output = run_command("w")
    
    users = []
    for line in who_output.split("\n"):
        if line.strip():
            parts = line.split()
            if len(parts) >= 3:
                users.append({
                    "user": parts[0],
                    "terminal": parts[1],
                    "loginTime": " ".join(parts[2:4]) if len(parts) >= 4 else parts[2],
                    "from": parts[4] if len(parts) > 4 else "local"
                })
    
    return {
        "users": users,
        "userCount": len(users),
        "detailedInfo": w_output.split("\n"),
        "timestamp": get_timestamp()
    }


@router.get("/services")
def get_services_status() -> Dict[str, Any]:
    """
    Check status of critical system services.
    
    Returns:
        Status of docker, nginx, mysql, ssh, and other important services
    """
    services = ["docker", "nginx", "mysql", "ssh", "postgresql", "redis", "mongodb"]
    result = []

    for svc in services:
        status = run_command(f"systemctl is-active {svc} 2>/dev/null")
        enabled = run_command(f"systemctl is-enabled {svc} 2>/dev/null")
        
        result.append({
            "name": svc,
            "status": status.strip(),
            "active": status.strip() == "active",
            "enabled": enabled.strip() == "enabled"
        })

    return {
        "services": result,
        "timestamp": get_timestamp()
    }


@router.get("/io")
def get_disk_io_stats() -> Dict[str, Any]:
    """
    Get disk I/O statistics for all block devices.
    
    Returns:
        Read/write stats for each disk device
    """
    # Use iostat if available, otherwise parse /proc/diskstats
    iostat_output = run_command("iostat -x 1 2 | tail -n +4")
    diskstats = run_command("cat /proc/diskstats")
    
    devices = []
    
    # Try parsing iostat output first
    if iostat_output and "command not found" not in iostat_output.lower():
        lines = iostat_output.split("\n")
        for line in lines:
            parts = line.split()
            if len(parts) >= 14 and parts[0] not in ["Device", "Device:"]:
                devices.append({
                    "device": parts[0],
                    "rrqm_s": safe_parse_float(parts[1]),
                    "wrqm_s": safe_parse_float(parts[2]),
                    "r_s": safe_parse_float(parts[3]),
                    "w_s": safe_parse_float(parts[4]),
                    "rkB_s": safe_parse_float(parts[5]),
                    "wkB_s": safe_parse_float(parts[6]),
                    "util": safe_parse_float(parts[-1])
                })
    else:
        # Fallback to /proc/diskstats
        for line in diskstats.split("\n"):
            parts = line.split()
            if len(parts) >= 14:
                devices.append({
                    "device": parts[2],
                    "reads": safe_parse_int(parts[3]),
                    "writes": safe_parse_int(parts[7]),
                    "sectors_read": safe_parse_int(parts[5]),
                    "sectors_written": safe_parse_int(parts[9])
                })
    
    return {
        "devices": devices,
        "timestamp": get_timestamp()
    }


@router.get("/temp")
def get_temperature_sensors() -> Dict[str, Any]:
    """
    Get CPU, GPU, and motherboard temperatures.
    Requires lm-sensors package (sensors command).
    
    Returns:
        Temperature readings from all available sensors
    """
    sensors_output = run_command("sensors 2>/dev/null")
    
    if "command not found" in sensors_output.lower():
        return {
            "error": "sensors command not found. Install lm-sensors package.",
            "timestamp": get_timestamp()
        }
    
    # Parse sensors output
    temps = {}
    current_chip = None
    
    for line in sensors_output.split("\n"):
        line = line.strip()
        if not line:
            continue
            
        # New chip section
        if line.endswith(":") and "-" in line:
            current_chip = line[:-1]
            temps[current_chip] = {}
        # Temperature reading
        elif "°C" in line and current_chip:
            parts = line.split(":")
            if len(parts) >= 2:
                sensor_name = parts[0].strip()
                # Extract temperature value
                import re
                temp_match = re.search(r'[+-]?([\d.]+)°C', parts[1])
                if temp_match:
                    temps[current_chip][sensor_name] = float(temp_match.group(1))
    
    return {
        "sensors": temps,
        "rawOutput": sensors_output,
        "timestamp": get_timestamp()
    }


@router.get("/power")
def get_power_status() -> Dict[str, Any]:
    """
    Get battery and UPS power status (if applicable).
    
    Returns:
        Battery/UPS status, charge level, and power source
    """
    # Check for battery using upower
    battery_info = run_command("upower -i /org/freedesktop/UPower/devices/battery_BAT0 2>/dev/null")
    
    # Check for UPS using apcaccess
    ups_info = run_command("apcaccess status 2>/dev/null")
    
    battery_data = {}
    if battery_info and "command not found" not in battery_info.lower():
        for line in battery_info.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                battery_data[key.strip()] = value.strip()
    
    ups_data = {}
    if ups_info and "command not found" not in ups_info.lower():
        for line in ups_info.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                ups_data[key.strip()] = value.strip()
    
    # Check AC power
    ac_online = run_command("cat /sys/class/power_supply/AC*/online 2>/dev/null")
    
    return {
        "battery": battery_data if battery_data else None,
        "ups": ups_data if ups_data else None,
        "acPower": ac_online.strip() == "1" if ac_online else None,
        "timestamp": get_timestamp()
    }
