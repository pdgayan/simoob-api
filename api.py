from fastapi import FastAPI
import subprocess
import json
import os
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

app = FastAPI()


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (for testing)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------------------------
# Helper function to run shell commands
# ----------------------------------------------------------------------
def run(cmd):
    return subprocess.getoutput(cmd)


# ----------------------------------------------------------------------
# 1. DOCKER CONTAINER INFORMATION
# ----------------------------------------------------------------------

@app.get("/api/containers/detailed")
def container_details():
    cmd = 'docker ps --all --format "{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}|{{.Size}}|{{.CreatedAt}}"'
    output = run(cmd).strip().split("\n")
    

    containers = []
    for line in output:
        if not line.strip():
            continue
        id, names, image, status, ports, size, createdAt = line.split("|")

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


@app.get("/api/containers/{name}/stats")
def container_stats(name: str):
    cmd = f'docker stats {name} --no-stream --format "{{{{.CPUPerc}}}}|{{{{.MemUsage}}}}|{{{{.NetIO}}}}|{{{{.BlockIO}}}}"'
    cpu, memory, network, disk = run(cmd).split("|")

    return {
        "containerName": name,
        "cpu": cpu.strip(),
        "memory": memory.strip(),
        "network": network.strip(),
        "diskIO": disk.strip(),
        "timestamp": now()
    }


@app.get("/api/containers/{name}/env")
def container_env(name: str):
    cmd = f"docker inspect {name} --format '{{{{range .Config.Env}}}}{{{{.}}}}\\n{{{{end}}}}'"
    output = run(cmd).strip().split("\n")

    env_vars = []
    for line in output:
        if "=" in line:
            key, value = line.split("=", 1)
            env_vars.append({"key": key, "value": value})

    return {"containerName": name, "environment": env_vars}


# ----------------------------------------------------------------------
# 2. SYSTEM STATS
# ----------------------------------------------------------------------

@app.get("/api/system/stats")
def system_stats():
    disk = run("df -h /")
    memory = run("free -h")
    uptime = run("uptime")
    uname = run("uname -a")
    cpu_model = run("cat /proc/cpuinfo | grep 'model name' | head -1")
    core_count = run("nproc")
    os_name = run('cat /etc/os-release | grep PRETTY_NAME').split("=")[1].replace('"', '')

    # Parse disk
    disk_line = [line for line in disk.split("\n") if "/dev/" in line or "overlay" in line]
    if disk_line:
        parts = disk_line[0].split()
        disk_stats = {
            "filesystem": parts[0],
            "total": parts[1],
            "used": parts[2],
            "available": parts[3],
            "percent": parts[4],
        }
    else:
        disk_stats = {}

    # Parse memory
    mem_line = [l for l in memory.split("\n") if "Mem:" in l]
    if mem_line:
        parts = mem_line[0].split()
        memory_stats = {
            "total": parts[1],
            "used": parts[2],
            "free": parts[3],
            "available": parts[6] if len(parts) >= 7 else parts[3]
        }
    else:
        memory_stats = {}

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

    # Uptime
    up = re.findall(r"up (.*?),", uptime)
    uptime_str = up[0] if up else "Unknown"

    return {
        "disk": disk_stats,
        "memory": memory_stats,
        "uptime": uptime_str,
        "loadAverage": load_avg,
        "cpu": {
            "model": cpu_model.split(":")[1].strip() if ":" in cpu_model else cpu_model,
            "cores": core_count
        },
        "os": os_name,
        "hostname": uname.split()[1],
        "timestamp": now()
    }


@app.get("/api/system/cpu")
def cpu_usage():
    cpus = os.cpu_count()
    stat1 = open("/proc/stat").readline().split()[1:]
    idle1 = int(stat1[3])
    total1 = sum(map(int, stat1))

    import time
    time.sleep(0.1)

    stat2 = open("/proc/stat").readline().split()[1:]
    idle2 = int(stat2[3])
    total2 = sum(map(int, stat2))

    cpu_usage = (1 - (idle2 - idle1) / (total2 - total1)) * 100

    return {"cpuUsage": round(cpu_usage, 1), "timestamp": now()}


# ----------------------------------------------------------------------
# 3. DOCKER IMAGES
# ----------------------------------------------------------------------

@app.get("/api/images")
def images():
    cmd = 'docker images --format "{{.Repository}}|{{.Tag}}|{{.ID}}|{{.CreatedSince}}|{{.Size}}"'
    output = run(cmd).strip().split("\n")

    images = []
    for line in output:
        repo, tag, id, created, size = line.split("|")
        images.append({
            "repository": repo,
            "tag": tag,
            "id": id,
            "createdSince": created,
            "size": size,
            "fullName": f"{repo}:{tag}"
        })

    return images


# ----------------------------------------------------------------------
# 4. NETWORK
# ----------------------------------------------------------------------

@app.get("/api/networks")
def networks():
    cmd = 'docker network ls --format "{{.ID}}|{{.Name}}|{{.Driver}}|{{.Scope}}"'
    output = run(cmd).strip().split("\n")

    networks = []
    for line in output:
        id, name, driver, scope = line.split("|")
        networks.append({
            "id": id,
            "name": name,
            "driver": driver,
            "scope": scope
        })

    return networks


@app.get("/api/system/network")
def system_network():
    output = run('ip addr show | grep -E "inet |UP|DOWN"')
    return {"interfaces": output, "timestamp": now()}


# ----------------------------------------------------------------------
# 5. LOGS
# ----------------------------------------------------------------------

@app.get("/api/system/logs")
def system_logs(lines: int = 50):
    output = run(f"journalctl -n {lines} --no-pager").split("\n")
    return {"logs": output, "count": len(output), "timestamp": now()}


@app.get("/api/docker/logs")
def docker_logs():
    output = run("journalctl -u docker --no-pager -n 50").split("\n")
    return {"service": "docker", "logs": output, "count": len(output), "timestamp": now()}


# ----------------------------------------------------------------------
# 6. PROCESSES
# ----------------------------------------------------------------------

@app.get("/api/system/processes")
def processes():
    output = run("ps aux --sort=-%cpu | head -20").split("\n")
    header = output[0].split()

    proc_list = []
    for line in output[1:]:
        parts = line.split()
        if len(parts) < 11:
            continue
        proc_list.append({
            "user": parts[0],
            "pid": parts[1],
            "cpu": parts[2],
            "memory": parts[3],
            "command": " ".join(parts[10:])
        })

    return {"processes": proc_list, "timestamp": now()}


# ----------------------------------------------------------------------
# 7. SERVICE STATUS
# ----------------------------------------------------------------------

@app.get("/api/services/status")
def services_status():
    services = ["docker", "nginx", "mysql", "ssh"]
    result = []

    for svc in services:
        status = run(f"systemctl is-active {svc}")
        result.append({
            "name": svc,
            "status": status,
            "active": status == "active"
        })

    return {"services": result, "timestamp": now()}


# ----------------------------------------------------------------------
# 8. DISK USAGE
# ----------------------------------------------------------------------

@app.get("/api/system/disk-usage")
def disk_usage():
    output = run("du -sh /var/lib/docker /home /tmp /var/log 2>/dev/null | sort -hr").split("\n")

    dirs = []
    for line in output:
        if not line.strip():
            continue
        size, path = line.split("\t")
        dirs.append({"size": size, "path": path})

    return {"directories": dirs, "timestamp": now()}


# ----------------------------------------------------------------------
# 9. PORTS
# ----------------------------------------------------------------------

@app.get("/api/system/ports")
def ports():
    output = run('ss -tuln | grep LISTEN').split("\n")

    ports = []
    for line in output:
        parts = line.split()
        if len(parts) >= 5:
            ports.append({
                "protocol": parts[0],
                "localAddress": parts[4],
                "state": parts[1]
            })

    return {"openPorts": ports, "timestamp": now()}


# ----------------------------------------------------------------------
# Helper Functions
# ----------------------------------------------------------------------

def extract_uptime(status):
    import re
    if "Up" in status:
        match = re.search(r"Up (.+?)(?:\(|$)", status)
        return match.group(1).strip() if match else "Running"
    return "Stopped"


def now():
    return datetime.utcnow().isoformat()


# ----------------------------------------------------------------------
# RUN COMMAND (same as Node's app.listen)
# ----------------------------------------------------------------------
# Start with:
#   uvicorn main:app --reload --port 3001
# ----------------------------------------------------------------------
