"""
Metrics Collector - Background Task
Automatically collects system and container metrics at regular intervals
and stores them in the database for historical analysis.
"""

import logging
from datetime import datetime
from database import get_db_session
from models import (
    SystemMetric, ContainerMetric, NetworkMetric, 
    DiskIOMetric, ProcessSnapshot, ServiceStatus, AlertHistory
)
from utils import run_command, safe_parse_int, safe_parse_float
import os
import time
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def collect_system_metrics():
    """
    Collect current system metrics and store in database.
    Includes CPU, memory, disk, and load averages.
    """
    try:
        with get_db_session() as db:
            # Get CPU usage
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
            
            # Get load averages
            uptime = run_command("uptime")
            load_match = re.findall(r"load average: ([\d.]+), ([\d.]+), ([\d.]+)", uptime)
            load_1, load_5, load_15 = (float(load_match[0][0]), float(load_match[0][1]), float(load_match[0][2])) if load_match else (0, 0, 0)
            
            # Get memory info
            memory = run_command("free -b")
            mem_line = [l for l in memory.split("\n") if "Mem:" in l]
            
            mem_total = mem_used = mem_free = mem_available = 0
            swap_total = swap_used = swap_free = 0
            
            if mem_line:
                parts = mem_line[0].split()
                if len(parts) >= 7:
                    mem_total = safe_parse_int(parts[1])
                    mem_used = safe_parse_int(parts[2])
                    mem_free = safe_parse_int(parts[3])
                    mem_available = safe_parse_int(parts[6])
            
            # Get swap info
            swap_line = [l for l in memory.split("\n") if "Swap:" in l]
            if swap_line:
                parts = swap_line[0].split()
                if len(parts) >= 4:
                    swap_total = safe_parse_int(parts[1])
                    swap_used = safe_parse_int(parts[2])
                    swap_free = safe_parse_int(parts[3])
            
            # Get disk info
            disk = run_command("df -h /")
            disk_line = [line for line in disk.split("\n") if "/dev/" in line or "overlay" in line]
            disk_total = disk_used = disk_free = disk_percent = ""
            
            if disk_line:
                parts = disk_line[0].split()
                if len(parts) >= 5:
                    disk_total = parts[1]
                    disk_used = parts[2]
                    disk_free = parts[3]
                    disk_percent = parts[4]
            
            # Get uptime
            uptime_match = re.findall(r"up (.*?),", uptime)
            uptime_str = uptime_match[0] if uptime_match else "Unknown"
            
            # Get hostname
            hostname = run_command("hostname").strip()
            
            # Create metric record
            metric = SystemMetric(
                timestamp=datetime.utcnow(),
                cpu_usage_percent=round(cpu_usage, 2),
                cpu_cores=os.cpu_count(),
                load_1min=load_1,
                load_5min=load_5,
                load_15min=load_15,
                memory_total=mem_total,
                memory_used=mem_used,
                memory_free=mem_free,
                memory_available=mem_available,
                memory_percent=round((mem_used / mem_total * 100), 2) if mem_total > 0 else 0,
                swap_total=swap_total,
                swap_used=swap_used,
                swap_free=swap_free,
                swap_percent=round((swap_used / swap_total * 100), 2) if swap_total > 0 else 0,
                disk_total=disk_total,
                disk_used=disk_used,
                disk_free=disk_free,
                disk_percent=disk_percent,
                uptime=uptime_str,
                hostname=hostname
            )
            
            db.add(metric)
            db.commit()
            
            logger.info(f"Collected system metrics: CPU={cpu_usage:.1f}%, Memory={metric.memory_percent:.1f}%")
            
    except Exception as e:
        logger.error(f"Failed to collect system metrics: {e}")


def collect_container_metrics():
    """
    Collect metrics for all running containers.
    """
    try:
        with get_db_session() as db:
            # Get list of containers
            cmd = 'docker ps --format "{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}"'
            output = run_command(cmd).strip()
            
            if not output:
                logger.info("No running containers found")
                return
            
            for line in output.split("\n"):
                if not line.strip():
                    continue
                
                parts = line.split("|")
                if len(parts) < 4:
                    continue
                
                container_id, name, image, status = parts
                
                # Get container stats
                stats_cmd = f'docker stats {name} --no-stream --format "{{{{.CPUPerc}}}}|{{{{.MemUsage}}}}|{{{{.MemPerc}}}}|{{{{.NetIO}}}}|{{{{.BlockIO}}}}"'
                stats_output = run_command(stats_cmd).strip()
                
                if not stats_output or "No such container" in stats_output:
                    continue
                
                stats_parts = stats_output.split("|")
                if len(stats_parts) < 5:
                    continue
                
                cpu_percent = stats_parts[0].strip()
                mem_usage = stats_parts[1].strip()
                mem_percent = stats_parts[2].strip()
                net_io = stats_parts[3].strip()
                block_io = stats_parts[4].strip()
                
                # Parse network I/O
                net_parts = net_io.split("/")
                net_input = net_parts[0].strip() if len(net_parts) > 0 else ""
                net_output = net_parts[1].strip() if len(net_parts) > 1 else ""
                
                # Parse block I/O
                block_parts = block_io.split("/")
                block_read = block_parts[0].strip() if len(block_parts) > 0 else ""
                block_write = block_parts[1].strip() if len(block_parts) > 1 else ""
                
                # Extract uptime from status
                uptime = ""
                if "Up" in status:
                    match = re.search(r"Up (.+?)(?:\(|$)", status)
                    uptime = match.group(1).strip() if match else "Running"
                
                # Create metric record
                metric = ContainerMetric(
                    timestamp=datetime.utcnow(),
                    container_id=container_id.strip(),
                    container_name=name.strip(),
                    image=image.strip(),
                    cpu_percent=cpu_percent,
                    memory_usage=mem_usage,
                    memory_percent=mem_percent,
                    network_input=net_input,
                    network_output=net_output,
                    block_read=block_read,
                    block_write=block_write,
                    status=status.strip(),
                    state="running",
                    uptime=uptime
                )
                
                db.add(metric)
            
            db.commit()
            logger.info(f"Collected metrics for {len(output.split(chr(10)))} containers")
            
    except Exception as e:
        logger.error(f"Failed to collect container metrics: {e}")


def collect_network_metrics():
    """
    Collect network interface statistics.
    """
    try:
        with get_db_session() as db:
            # Parse /proc/net/dev for traffic stats
            netdev = run_command("cat /proc/net/dev")
            lines = netdev.split("\n")[2:]  # Skip header lines
            
            for line in lines:
                if ":" in line:
                    parts = line.split(":")
                    iface = parts[0].strip()
                    stats = parts[1].split()
                    
                    if len(stats) >= 16:
                        metric = NetworkMetric(
                            timestamp=datetime.utcnow(),
                            interface=iface,
                            rx_bytes=safe_parse_int(stats[0]),
                            rx_packets=safe_parse_int(stats[1]),
                            rx_errors=safe_parse_int(stats[2]),
                            rx_dropped=safe_parse_int(stats[3]),
                            tx_bytes=safe_parse_int(stats[8]),
                            tx_packets=safe_parse_int(stats[9]),
                            tx_errors=safe_parse_int(stats[10]),
                            tx_dropped=safe_parse_int(stats[11])
                        )
                        
                        db.add(metric)
            
            db.commit()
            logger.info("Collected network metrics")
            
    except Exception as e:
        logger.error(f"Failed to collect network metrics: {e}")


def collect_disk_io_metrics():
    """
    Collect disk I/O statistics.
    """
    try:
        with get_db_session() as db:
            # Parse /proc/diskstats
            diskstats = run_command("cat /proc/diskstats")
            
            for line in diskstats.split("\n"):
                parts = line.split()
                if len(parts) >= 14:
                    # Skip loop and ram devices
                    device = parts[2]
                    if device.startswith("loop") or device.startswith("ram"):
                        continue
                    
                    metric = DiskIOMetric(
                        timestamp=datetime.utcnow(),
                        device=device,
                        reads=safe_parse_int(parts[3]),
                        writes=safe_parse_int(parts[7]),
                        sectors_read=safe_parse_int(parts[5]),
                        sectors_written=safe_parse_int(parts[9])
                    )
                    
                    db.add(metric)
            
            db.commit()
            logger.info("Collected disk I/O metrics")
            
    except Exception as e:
        logger.error(f"Failed to collect disk I/O metrics: {e}")


def collect_process_snapshots():
    """
    Collect snapshot of top processes.
    """
    try:
        with get_db_session() as db:
            output = run_command("ps aux --sort=-%cpu | head -11")  # Top 10 + header
            lines = output.split("\n")[1:]  # Skip header
            
            for line in lines:
                parts = line.split()
                if len(parts) >= 11:
                    metric = ProcessSnapshot(
                        timestamp=datetime.utcnow(),
                        pid=safe_parse_int(parts[1]),
                        user=parts[0],
                        cpu_percent=safe_parse_float(parts[2]),
                        memory_percent=safe_parse_float(parts[3]),
                        vsz=safe_parse_int(parts[4]),
                        rss=safe_parse_int(parts[5]),
                        state=parts[7],
                        command=" ".join(parts[10:])
                    )
                    
                    db.add(metric)
            
            db.commit()
            logger.info("Collected process snapshots")
            
    except Exception as e:
        logger.error(f"Failed to collect process snapshots: {e}")


def check_and_log_alerts():
    """
    Check system metrics against thresholds and log alerts.
    """
    try:
        with get_db_session() as db:
            # Check CPU
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
            
            if cpu_usage > 80:
                alert = AlertHistory(
                    timestamp=datetime.utcnow(),
                    alert_type="CPU",
                    severity="warning" if cpu_usage < 90 else "critical",
                    message=f"CPU usage is {cpu_usage:.1f}%",
                    current_value=cpu_usage,
                    threshold_value=80.0
                )
                db.add(alert)
                logger.warning(f"CPU Alert: {cpu_usage:.1f}%")
            
            # Check Memory
            memory = run_command("free -b")
            mem_line = [l for l in memory.split("\n") if "Mem:" in l]
            
            if mem_line:
                parts = mem_line[0].split()
                if len(parts) >= 3:
                    total = safe_parse_int(parts[1])
                    used = safe_parse_int(parts[2])
                    mem_percent = (used / total * 100) if total > 0 else 0
                    
                    if mem_percent > 80:
                        alert = AlertHistory(
                            timestamp=datetime.utcnow(),
                            alert_type="Memory",
                            severity="warning" if mem_percent < 90 else "critical",
                            message=f"Memory usage is {mem_percent:.1f}%",
                            current_value=mem_percent,
                            threshold_value=80.0
                        )
                        db.add(alert)
                        logger.warning(f"Memory Alert: {mem_percent:.1f}%")
            
            db.commit()
            
    except Exception as e:
        logger.error(f"Failed to check alerts: {e}")


def collect_all_metrics():
    """
    Collect all metrics in one function call.
    This is the main function called by the scheduler.
    """
    logger.info("Starting metrics collection cycle")
    
    collect_system_metrics()
    collect_container_metrics()
    collect_network_metrics()
    collect_disk_io_metrics()
    collect_process_snapshots()
    check_and_log_alerts()
    
    logger.info("Metrics collection cycle completed")
