"""
Container-Level Metrics Router
Provides endpoints for Docker container management, monitoring, and control.
Includes container listing, stats, logs, control operations, and health checks.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from utils import run_command, get_timestamp, extract_uptime, parse_docker_format

router = APIRouter(prefix="/api/containers", tags=["containers"])


@router.get("/detailed")
def get_container_details() -> List[Dict[str, Any]]:
    """
    Get detailed information about all containers (running and stopped).
    
    Returns:
        List of containers with ID, name, image, status, ports, size, and uptime
    """
    cmd = 'docker ps --all --format "{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}|{{.Size}}|{{.CreatedAt}}"'
    output = run_command(cmd).strip()
    
    if not output:
        return []
    
    containers = []
    for line in output.split("\n"):
        if not line.strip():
            continue
        
        parts = line.split("|")
        if len(parts) >= 7:
            id, names, image, status, ports, size, createdAt = parts
            
            containers.append({
                "id": id.strip(),
                "name": names.strip(),
                "image": image.strip(),
                "status": status.strip(),
                "ports": ports.strip() or "No ports exposed",
                "size": size.strip(),
                "createdAt": createdAt.strip(),
                "state": "running" if "Up" in status else "stopped",
                "uptime": extract_uptime(status)
            })

    return containers


@router.get("/{name}/stats")
def get_container_stats(name: str) -> Dict[str, Any]:
    """
    Get real-time resource usage statistics for a specific container.
    
    Args:
        name: Container name or ID
        
    Returns:
        CPU, memory, network, and disk I/O statistics
    """
    cmd = f'docker stats {name} --no-stream --format "{{{{.CPUPerc}}}}|{{{{.MemUsage}}}}|{{{{.MemPerc}}}}|{{{{.NetIO}}}}|{{{{.BlockIO}}}}"'
    output = run_command(cmd).strip()
    
    if not output or "No such container" in output:
        raise HTTPException(status_code=404, detail=f"Container '{name}' not found")
    
    parts = output.split("|")
    if len(parts) >= 5:
        return {
            "containerName": name,
            "cpu": parts[0].strip(),
            "memoryUsage": parts[1].strip(),
            "memoryPercent": parts[2].strip(),
            "network": parts[3].strip(),
            "diskIO": parts[4].strip(),
            "timestamp": get_timestamp()
        }
    
    return {"error": "Could not parse stats", "timestamp": get_timestamp()}


@router.get("/{name}/env")
def get_container_env(name: str) -> Dict[str, Any]:
    """
    Get environment variables for a specific container.
    
    Args:
        name: Container name or ID
        
    Returns:
        List of environment variables with keys and values
    """
    cmd = f"docker inspect {name} --format '{{{{range .Config.Env}}}}{{{{.}}}}\\n{{{{end}}}}'"
    output = run_command(cmd).strip()
    
    if "No such object" in output or "Error" in output:
        raise HTTPException(status_code=404, detail=f"Container '{name}' not found")

    env_vars = []
    for line in output.split("\n"):
        if "=" in line:
            key, value = line.split("=", 1)
            env_vars.append({"key": key, "value": value})

    return {
        "containerName": name,
        "environment": env_vars,
        "count": len(env_vars),
        "timestamp": get_timestamp()
    }


@router.get("/{name}/logs")
def get_container_logs(
    name: str,
    lines: int = Query(100, ge=1, le=10000),
    follow: bool = False
) -> Dict[str, Any]:
    """
    Get logs from a specific container.
    
    Args:
        name: Container name or ID
        lines: Number of log lines to retrieve
        follow: Whether to follow logs (not recommended for API)
        
    Returns:
        Container logs
    """
    follow_flag = "-f" if follow else ""
    cmd = f"docker logs {name} --tail {lines} {follow_flag} 2>&1"
    output = run_command(cmd)
    
    if "No such container" in output:
        raise HTTPException(status_code=404, detail=f"Container '{name}' not found")
    
    log_lines = output.split("\n")
    
    return {
        "containerName": name,
        "logs": log_lines,
        "lineCount": len(log_lines),
        "linesRequested": lines,
        "timestamp": get_timestamp()
    }


@router.get("/{name}/processes")
def get_container_processes(name: str) -> Dict[str, Any]:
    """
    Get list of processes running inside a container.
    
    Args:
        name: Container name or ID
        
    Returns:
        List of processes with PID, user, and command
    """
    cmd = f"docker top {name}"
    output = run_command(cmd)
    
    if "No such container" in output or "is not running" in output:
        raise HTTPException(status_code=404, detail=f"Container '{name}' not found or not running")
    
    lines = output.split("\n")
    if len(lines) < 2:
        return {"containerName": name, "processes": [], "timestamp": get_timestamp()}
    
    # Parse header and processes
    header = lines[0].split()
    processes = []
    
    for line in lines[1:]:
        if line.strip():
            parts = line.split(None, len(header) - 1)
            if len(parts) >= len(header):
                proc = {}
                for i, col in enumerate(header):
                    proc[col.lower()] = parts[i] if i < len(parts) else ""
                processes.append(proc)
    
    return {
        "containerName": name,
        "processes": processes,
        "count": len(processes),
        "timestamp": get_timestamp()
    }


@router.get("/images")
def get_docker_images() -> List[Dict[str, Any]]:
    """
    Get list of all Docker images on the system.
    
    Returns:
        List of images with repository, tag, ID, creation time, and size
    """
    cmd = 'docker images --format "{{.Repository}}|{{.Tag}}|{{.ID}}|{{.CreatedSince}}|{{.Size}}"'
    output = run_command(cmd).strip()

    images = []
    for line in output.split("\n"):
        if line.strip():
            parts = line.split("|")
            if len(parts) >= 5:
                repo, tag, id, created, size = parts
                images.append({
                    "repository": repo.strip(),
                    "tag": tag.strip(),
                    "id": id.strip(),
                    "createdSince": created.strip(),
                    "size": size.strip(),
                    "fullName": f"{repo.strip()}:{tag.strip()}"
                })

    return images


@router.post("/restart/{name}")
def restart_container(name: str) -> Dict[str, Any]:
    """
    Restart a specific container.
    
    Args:
        name: Container name or ID
        
    Returns:
        Success message and container name
    """
    output = run_command(f"docker restart {name}")
    
    if "Error" in output or "No such container" in output:
        raise HTTPException(status_code=404, detail=f"Failed to restart container '{name}': {output}")
    
    return {
        "message": f"Container '{name}' restarted successfully",
        "containerName": name,
        "timestamp": get_timestamp()
    }


@router.post("/stop/{name}")
def stop_container(name: str, timeout: int = Query(10, ge=1, le=300)) -> Dict[str, Any]:
    """
    Stop a running container.
    
    Args:
        name: Container name or ID
        timeout: Seconds to wait before killing container
        
    Returns:
        Success message
    """
    output = run_command(f"docker stop -t {timeout} {name}")
    
    if "Error" in output or "No such container" in output:
        raise HTTPException(status_code=404, detail=f"Failed to stop container '{name}': {output}")
    
    return {
        "message": f"Container '{name}' stopped successfully",
        "containerName": name,
        "timestamp": get_timestamp()
    }


@router.post("/start/{name}")
def start_container(name: str) -> Dict[str, Any]:
    """
    Start a stopped container.
    
    Args:
        name: Container name or ID
        
    Returns:
        Success message
    """
    output = run_command(f"docker start {name}")
    
    if "Error" in output or "No such container" in output:
        raise HTTPException(status_code=404, detail=f"Failed to start container '{name}': {output}")
    
    return {
        "message": f"Container '{name}' started successfully",
        "containerName": name,
        "timestamp": get_timestamp()
    }


@router.get("/net")
def get_container_network_details() -> List[Dict[str, Any]]:
    """
    Get network details for all containers.
    
    Returns:
        Network configuration for each container
    """
    cmd = 'docker ps --format "{{.Names}}"'
    containers = run_command(cmd).strip().split("\n")
    
    network_info = []
    for container in containers:
        if not container.strip():
            continue
        
        # Get network settings
        inspect_cmd = f"docker inspect {container} --format '{{{{json .NetworkSettings}}}}'"
        network_data = run_command(inspect_cmd)
        
        network_info.append({
            "container": container.strip(),
            "networkData": network_data.strip()
        })
    
    return network_info


@router.get("/health")
def get_container_health_status() -> List[Dict[str, Any]]:
    """
    Check health status of all containers with health checks configured.
    
    Returns:
        Health status for containers with HEALTHCHECK
    """
    cmd = 'docker ps --format "{{.Names}}|{{.Status}}"'
    output = run_command(cmd).strip()
    
    health_statuses = []
    for line in output.split("\n"):
        if not line.strip():
            continue
        
        parts = line.split("|")
        if len(parts) >= 2:
            name = parts[0].strip()
            status = parts[1].strip()
            
            # Extract health status if present
            health = "no healthcheck"
            if "healthy" in status.lower():
                health = "healthy"
            elif "unhealthy" in status.lower():
                health = "unhealthy"
            elif "health: starting" in status.lower():
                health = "starting"
            
            health_statuses.append({
                "container": name,
                "status": status,
                "health": health
            })
    
    return health_statuses


@router.get("/{name}/inspect")
def inspect_container(name: str) -> Dict[str, Any]:
    """
    Get complete inspection data for a container (full Docker inspect output).
    
    Args:
        name: Container name or ID
        
    Returns:
        Full container configuration and state information
    """
    import json
    
    cmd = f"docker inspect {name}"
    output = run_command(cmd)
    
    if "No such object" in output or "Error" in output:
        raise HTTPException(status_code=404, detail=f"Container '{name}' not found")
    
    try:
        inspect_data = json.loads(output)
        return {
            "containerName": name,
            "inspect": inspect_data,
            "timestamp": get_timestamp()
        }
    except json.JSONDecodeError:
        return {
            "error": "Failed to parse inspect output",
            "rawOutput": output,
            "timestamp": get_timestamp()
        }


@router.get("/metrics/summary")
def get_all_containers_metrics() -> Dict[str, Any]:
    """
    Get aggregated metrics for all running containers.
    
    Returns:
        Summary statistics across all containers
    """
    cmd = 'docker stats --no-stream --format "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}|{{.NetIO}}|{{.BlockIO}}"'
    output = run_command(cmd).strip()
    
    if not output:
        return {"containers": [], "totalCount": 0, "timestamp": get_timestamp()}
    
    containers = []
    for line in output.split("\n"):
        if line.strip():
            parts = line.split("|")
            if len(parts) >= 5:
                containers.append({
                    "name": parts[0].strip(),
                    "cpu": parts[1].strip(),
                    "memory": parts[2].strip(),
                    "network": parts[3].strip(),
                    "diskIO": parts[4].strip()
                })
    
    return {
        "containers": containers,
        "totalCount": len(containers),
        "timestamp": get_timestamp()
    }


@router.delete("/{name}")
def remove_container(name: str, force: bool = Query(False)) -> Dict[str, Any]:
    """
    Remove a container.
    
    Args:
        name: Container name or ID
        force: Force removal even if running
        
    Returns:
        Success message
    """
    force_flag = "-f" if force else ""
    output = run_command(f"docker rm {force_flag} {name}")
    
    if "Error" in output or "No such container" in output:
        raise HTTPException(status_code=404, detail=f"Failed to remove container '{name}': {output}")
    
    return {
        "message": f"Container '{name}' removed successfully",
        "containerName": name,
        "forced": force,
        "timestamp": get_timestamp()
    }
