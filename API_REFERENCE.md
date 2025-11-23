# API Endpoint Reference

Complete reference for all API endpoints in the System Monitoring API v2.0

## Table of Contents

- [System Endpoints](#system-endpoints)
- [Container Endpoints](#container-endpoints)
- [Network Endpoints](#network-endpoints)
- [Log Endpoints](#log-endpoints)
- [Advanced Endpoints](#advanced-endpoints)

---

## System Endpoints

### GET /api/system/stats

**Description**: Get comprehensive system statistics  
**Parameters**: None  
**Returns**: Complete system overview with CPU, memory, disk, uptime, load

### GET /api/system/cpu

**Description**: Get current CPU usage percentage  
**Parameters**: None  
**Returns**: CPU usage with timestamp

### GET /api/system/memory

**Description**: Get detailed memory usage statistics  
**Parameters**: None  
**Returns**: RAM and swap memory details

### GET /api/system/disk-usage

**Description**: Get disk usage for important directories  
**Parameters**: None  
**Returns**: Disk usage by directory

### GET /api/system/load

**Description**: Get system load averages  
**Parameters**: None  
**Returns**: 1, 5, and 15-minute load averages

### GET /api/system/processes

**Description**: Get top processes by CPU usage  
**Parameters**: None  
**Returns**: List of top 20 processes

### GET /api/system/ports

**Description**: Get list of open TCP/UDP ports  
**Parameters**: None  
**Returns**: Listening ports with addresses

### GET /api/system/logs

**Description**: Get recent system logs  
**Parameters**:

- `lines` (optional, default: 50): Number of log lines

**Returns**: System logs from journalctl

### GET /api/system/network

**Description**: Get network interface information  
**Parameters**: None  
**Returns**: Network interfaces and IP addresses

### GET /api/system/users

**Description**: Get logged-in users  
**Parameters**: None  
**Returns**: Active user sessions

### GET /api/system/services

**Description**: Check status of system services  
**Parameters**: None  
**Returns**: Status of docker, nginx, mysql, ssh, etc.

### GET /api/system/io

**Description**: Get disk I/O statistics  
**Parameters**: None  
**Returns**: Read/write stats for block devices

### GET /api/system/temp

**Description**: Get temperature sensor readings  
**Parameters**: None  
**Returns**: CPU, GPU, motherboard temperatures  
**Note**: Requires lm-sensors package

### GET /api/system/power

**Description**: Get battery and UPS status  
**Parameters**: None  
**Returns**: Battery/UPS information if available

---

## Container Endpoints

### GET /api/containers/detailed

**Description**: List all containers with details  
**Parameters**: None  
**Returns**: List of containers (running and stopped)

### GET /api/containers/{name}/stats

**Description**: Get container resource usage  
**Parameters**:

- `name` (path): Container name or ID

**Returns**: CPU, memory, network, disk I/O stats

### GET /api/containers/{name}/env

**Description**: Get container environment variables  
**Parameters**:

- `name` (path): Container name or ID

**Returns**: Environment variables

### GET /api/containers/{name}/logs

**Description**: Get container logs  
**Parameters**:

- `name` (path): Container name or ID
- `lines` (optional, default: 100): Number of log lines
- `since` (optional): Show logs since time
- `timestamps` (optional, default: false): Include timestamps

**Returns**: Container logs

### GET /api/containers/{name}/processes

**Description**: Get processes inside container  
**Parameters**:

- `name` (path): Container name or ID

**Returns**: List of running processes

### GET /api/containers/images

**Description**: List all Docker images  
**Parameters**: None  
**Returns**: List of images with repository, tag, size

### POST /api/containers/restart/{name}

**Description**: Restart a container  
**Parameters**:

- `name` (path): Container name or ID

**Returns**: Success message

### POST /api/containers/stop/{name}

**Description**: Stop a running container  
**Parameters**:

- `name` (path): Container name or ID
- `timeout` (optional, default: 10): Seconds to wait

**Returns**: Success message

### POST /api/containers/start/{name}

**Description**: Start a stopped container  
**Parameters**:

- `name` (path): Container name or ID

**Returns**: Success message

### GET /api/containers/net

**Description**: Get container network details  
**Parameters**: None  
**Returns**: Network configuration for all containers

### GET /api/containers/health

**Description**: Check container health status  
**Parameters**: None  
**Returns**: Health status for containers with healthchecks

### GET /api/containers/{name}/inspect

**Description**: Get full container inspection data  
**Parameters**:

- `name` (path): Container name or ID

**Returns**: Complete Docker inspect output

### GET /api/containers/metrics/summary

**Description**: Get aggregated metrics for all containers  
**Parameters**: None  
**Returns**: Summary stats across all containers

### DELETE /api/containers/{name}

**Description**: Remove a container  
**Parameters**:

- `name` (path): Container name or ID
- `force` (optional, default: false): Force removal

**Returns**: Success message

---

## Network Endpoints

### GET /api/network/interfaces

**Description**: Get network interface details  
**Parameters**: None  
**Returns**: Interfaces with IP, MAC, status, MTU

### GET /api/network/traffic

**Description**: Get network traffic statistics  
**Parameters**: None  
**Returns**: Bytes sent/received per interface

### GET /api/network/connections

**Description**: Get active network connections  
**Parameters**: None  
**Returns**: TCP/UDP connections with addresses

### GET /api/network/container

**Description**: Get per-container network usage  
**Parameters**: None  
**Returns**: Network I/O for each container

### GET /api/network/routes

**Description**: Get routing table  
**Parameters**: None  
**Returns**: System routing information

### GET /api/network/firewall

**Description**: Get firewall rules  
**Parameters**: None  
**Returns**: IPTables/nftables rules  
**Note**: Requires sudo privileges

### GET /api/network/latency

**Description**: Test network latency to a host  
**Parameters**:

- `host` (optional, default: "8.8.8.8"): Target host
- `count` (optional, default: 4): Number of pings

**Returns**: Ping statistics with min/avg/max latency

### GET /api/network/errors

**Description**: Get network errors and dropped packets  
**Parameters**: None  
**Returns**: Error statistics per interface

### GET /api/network/dns

**Description**: Get DNS configuration  
**Parameters**: None  
**Returns**: DNS servers and search domains

### GET /api/network/bandwidth

**Description**: Calculate current bandwidth usage  
**Parameters**: None  
**Returns**: Bytes/sec for each interface

### GET /api/network/docker

**Description**: Get Docker networks  
**Parameters**: None  
**Returns**: List of Docker networks

---

## Log Endpoints

### GET /api/logs/system

**Description**: Get system logs with filtering  
**Parameters**:

- `lines` (optional, default: 100): Number of lines
- `priority` (optional): Log priority level
- `since` (optional): Show logs since time

**Returns**: Filtered system logs

### GET /api/logs/docker

**Description**: Get Docker service logs  
**Parameters**:

- `lines` (optional, default: 50): Number of lines

**Returns**: Docker daemon logs

### GET /api/logs/container/{name}

**Description**: Get container logs with options  
**Parameters**:

- `name` (path): Container name or ID
- `lines` (optional, default: 100): Number of lines
- `since` (optional): Show logs since time
- `timestamps` (optional, default: false): Include timestamps

**Returns**: Container logs

### GET /api/logs/app/{service}

**Description**: Get application service logs  
**Parameters**:

- `service` (path): Service name
- `lines` (optional, default: 100): Number of lines

**Returns**: Service logs from journalctl

### GET /api/logs/errors

**Description**: Get filtered error logs  
**Parameters**:

- `lines` (optional, default: 100): Number of lines
- `severity` (optional, default: "err"): Minimum severity

**Returns**: Error and critical logs

### GET /api/logs/kernel

**Description**: Get kernel logs  
**Parameters**:

- `lines` (optional, default: 100): Number of lines

**Returns**: Kernel ring buffer logs (dmesg)

### GET /api/logs/auth

**Description**: Get authentication logs  
**Parameters**:

- `lines` (optional, default: 50): Number of lines

**Returns**: Login attempts, sudo usage, etc.

### GET /api/logs/search

**Description**: Search logs for text pattern  
**Parameters**:

- `query` (required): Search text
- `lines` (optional, default: 100): Number of lines to search
- `case_sensitive` (optional, default: false): Case sensitivity

**Returns**: Matching log entries

### GET /api/logs/stats

**Description**: Get log statistics  
**Parameters**: None  
**Returns**: Log counts by priority and service

### GET /api/logs/tail/{service}

**Description**: Get recent logs for a service  
**Parameters**:

- `service` (path): Service name
- `lines` (optional, default: 20): Number of lines

**Returns**: Most recent log entries

---

## Advanced Endpoints

### GET /api/advanced/sensors

**Description**: Get all sensor readings  
**Parameters**: None  
**Returns**: Temperature, fan speed, voltage sensors  
**Note**: Requires lm-sensors

### GET /api/advanced/filesystem/inodes

**Description**: Get inode usage statistics  
**Parameters**: None  
**Returns**: Inode usage per filesystem

### GET /api/advanced/filesystem/mounts

**Description**: Get filesystem mount points  
**Parameters**: None  
**Returns**: Mounted filesystems with details

### GET /api/advanced/cgroups

**Description**: Get cgroup information  
**Parameters**: None  
**Returns**: Cgroup hierarchy and controllers

### GET /api/advanced/cgroups/container/{name}

**Description**: Get container cgroup statistics  
**Parameters**:

- `name` (path): Container name or ID

**Returns**: CPU, memory, I/O cgroup limits

### GET /api/advanced/alerts

**Description**: Check metrics against thresholds  
**Parameters**:

- `cpu_threshold` (optional, default: 80): CPU alert threshold %
- `memory_threshold` (optional, default: 80): Memory alert threshold %
- `disk_threshold` (optional, default: 80): Disk alert threshold %

**Returns**: Active alerts based on thresholds

### GET /api/advanced/metrics/export/json

**Description**: Export metrics as JSON  
**Parameters**: None  
**Returns**: Complete system snapshot in JSON

### GET /api/advanced/metrics/export/csv

**Description**: Export metrics as CSV  
**Parameters**: None  
**Returns**: CSV file with metrics (downloadable)

### GET /api/advanced/metrics/prometheus

**Description**: Export metrics in Prometheus format  
**Parameters**: None  
**Returns**: Prometheus text exposition format

### GET /api/advanced/hardware/info

**Description**: Get hardware information  
**Parameters**: None  
**Returns**: CPU, memory, disk hardware details

---

## Response Format

All endpoints return JSON (except CSV export) with the following structure:

```json
{
  "data": "...",
  "timestamp": "2025-11-23T10:30:00.000000"
}
```

## Error Responses

```json
{
  "detail": "Error message"
}
```

HTTP Status Codes:

- `200`: Success
- `404`: Resource not found
- `400`: Bad request
- `500`: Internal server error
