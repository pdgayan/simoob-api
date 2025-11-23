"""
Network-Level Metrics Router
Provides endpoints for network monitoring including interfaces, traffic, 
connections, routes, firewall rules, and latency testing.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any, List
from utils import run_command, get_timestamp, safe_parse_int, safe_parse_float
import re

router = APIRouter(prefix="/api/network", tags=["network"])


@router.get("/interfaces")
def get_network_interfaces() -> Dict[str, Any]:
    """
    Get detailed information about all network interfaces.
    
    Returns:
        List of network interfaces with IP addresses, MAC, status, and MTU
    """
    # Get interface list with details
    ip_addr = run_command("ip addr show")
    ip_link = run_command("ip -o link show")
    
    interfaces = []
    current_interface = None
    
    for line in ip_addr.split("\n"):
        # New interface line
        if re.match(r'^\d+:', line):
            if current_interface:
                interfaces.append(current_interface)
            
            parts = line.split(":", 2)
            if len(parts) >= 3:
                iface_name = parts[1].strip()
                flags = parts[2].strip()
                
                current_interface = {
                    "name": iface_name,
                    "flags": flags,
                    "addresses": [],
                    "state": "UP" if "UP" in flags else "DOWN"
                }
        
        # MAC address
        elif "link/" in line and current_interface:
            match = re.search(r'link/\w+ ([0-9a-f:]+)', line)
            if match:
                current_interface["mac"] = match.group(1)
            
            # MTU
            mtu_match = re.search(r'mtu (\d+)', line)
            if mtu_match:
                current_interface["mtu"] = int(mtu_match.group(1))
        
        # IP address
        elif "inet" in line and current_interface:
            match = re.search(r'inet6? ([0-9a-f.:]+/\d+)', line)
            if match:
                current_interface["addresses"].append(match.group(1))
    
    if current_interface:
        interfaces.append(current_interface)
    
    return {
        "interfaces": interfaces,
        "count": len(interfaces),
        "timestamp": get_timestamp()
    }


@router.get("/traffic")
def get_network_traffic() -> Dict[str, Any]:
    """
    Get network traffic statistics for each interface (bytes sent/received).
    
    Returns:
        Traffic statistics per interface
    """
    # Parse /proc/net/dev for traffic stats
    netdev = run_command("cat /proc/net/dev")
    
    interfaces = []
    lines = netdev.split("\n")[2:]  # Skip header lines
    
    for line in lines:
        if ":" in line:
            parts = line.split(":")
            iface = parts[0].strip()
            stats = parts[1].split()
            
            if len(stats) >= 16:
                interfaces.append({
                    "interface": iface,
                    "rxBytes": safe_parse_int(stats[0]),
                    "rxPackets": safe_parse_int(stats[1]),
                    "rxErrors": safe_parse_int(stats[2]),
                    "rxDropped": safe_parse_int(stats[3]),
                    "txBytes": safe_parse_int(stats[8]),
                    "txPackets": safe_parse_int(stats[9]),
                    "txErrors": safe_parse_int(stats[10]),
                    "txDropped": safe_parse_int(stats[11])
                })
    
    return {
        "interfaces": interfaces,
        "timestamp": get_timestamp()
    }


@router.get("/connections")
def get_active_connections() -> Dict[str, Any]:
    """
    Get all active TCP and UDP network connections.
    
    Returns:
        List of active connections with local/remote addresses and state
    """
    # Get TCP connections
    tcp_output = run_command("ss -tun")
    
    connections = []
    lines = tcp_output.split("\n")[1:]  # Skip header
    
    for line in lines:
        parts = line.split()
        if len(parts) >= 5:
            connections.append({
                "protocol": parts[0],
                "recvQ": safe_parse_int(parts[1]),
                "sendQ": safe_parse_int(parts[2]),
                "localAddress": parts[3] if len(parts) > 3 else "",
                "peerAddress": parts[4] if len(parts) > 4 else "",
                "state": parts[5] if len(parts) > 5 else "ESTABLISHED"
            })
    
    return {
        "connections": connections,
        "count": len(connections),
        "timestamp": get_timestamp()
    }


@router.get("/container")
def get_container_network_usage() -> List[Dict[str, Any]]:
    """
    Get network usage statistics per container.
    
    Returns:
        Network I/O for each running container
    """
    cmd = 'docker stats --no-stream --format "{{.Name}}|{{.NetIO}}"'
    output = run_command(cmd).strip()
    
    containers = []
    for line in output.split("\n"):
        if line.strip():
            parts = line.split("|")
            if len(parts) >= 2:
                name = parts[0].strip()
                net_io = parts[1].strip()
                
                # Parse "input / output" format
                io_parts = net_io.split("/")
                containers.append({
                    "container": name,
                    "netIO": net_io,
                    "input": io_parts[0].strip() if len(io_parts) > 0 else "",
                    "output": io_parts[1].strip() if len(io_parts) > 1 else ""
                })
    
    return containers


@router.get("/routes")
def get_routing_table() -> Dict[str, Any]:
    """
    Get system routing table information.
    
    Returns:
        Routing table with destinations, gateways, and interfaces
    """
    route_output = run_command("ip route show")
    route_table = run_command("route -n")
    
    routes = []
    for line in route_output.split("\n"):
        if line.strip():
            routes.append({"rule": line.strip()})
    
    return {
        "routes": routes,
        "routeTable": route_table,
        "timestamp": get_timestamp()
    }


@router.get("/firewall")
def get_firewall_rules() -> Dict[str, Any]:
    """
    Get IPTables firewall rules summary.
    Note: Requires root/sudo privileges.
    
    Returns:
        IPTables rules for INPUT, OUTPUT, and FORWARD chains
    """
    # Try to get iptables rules
    iptables = run_command("sudo iptables -L -n -v 2>/dev/null")
    
    if not iptables or "command not found" in iptables.lower():
        # Try nft (nftables)
        nft = run_command("sudo nft list ruleset 2>/dev/null")
        if nft and "command not found" not in nft.lower():
            return {
                "type": "nftables",
                "rules": nft,
                "timestamp": get_timestamp()
            }
        
        return {
            "error": "Firewall information not accessible. Requires sudo privileges.",
            "timestamp": get_timestamp()
        }
    
    return {
        "type": "iptables",
        "rules": iptables,
        "timestamp": get_timestamp()
    }


@router.get("/latency")
def test_network_latency(
    host: str = Query("8.8.8.8", description="Target host to ping"),
    count: int = Query(4, ge=1, le=10)
) -> Dict[str, Any]:
    """
    Test network latency to a target host using ping.
    
    Args:
        host: Target hostname or IP address
        count: Number of ping packets to send (1-10)
        
    Returns:
        Ping statistics including min/avg/max/mdev latency
    """
    # Validate host to prevent command injection
    if not re.match(r'^[a-zA-Z0-9.-]+$', host):
        raise HTTPException(status_code=400, detail="Invalid host format")
    
    ping_output = run_command(f"ping -c {count} -W 2 {host}")
    
    if "unknown host" in ping_output.lower() or "unreachable" in ping_output.lower():
        return {
            "host": host,
            "status": "unreachable",
            "error": "Host is unreachable or does not exist",
            "timestamp": get_timestamp()
        }
    
    # Parse ping statistics
    stats = {}
    packets_match = re.search(r'(\d+) packets transmitted, (\d+) received', ping_output)
    if packets_match:
        stats["transmitted"] = int(packets_match.group(1))
        stats["received"] = int(packets_match.group(2))
        stats["loss"] = f"{((stats['transmitted'] - stats['received']) / stats['transmitted'] * 100):.1f}%"
    
    # Parse RTT statistics
    rtt_match = re.search(r'min/avg/max/[ms]?dev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)', ping_output)
    if rtt_match:
        stats["rtt"] = {
            "min": float(rtt_match.group(1)),
            "avg": float(rtt_match.group(2)),
            "max": float(rtt_match.group(3)),
            "mdev": float(rtt_match.group(4))
        }
    
    return {
        "host": host,
        "status": "reachable",
        "statistics": stats,
        "rawOutput": ping_output,
        "timestamp": get_timestamp()
    }


@router.get("/errors")
def get_network_errors() -> Dict[str, Any]:
    """
    Get network errors and dropped packets for all interfaces.
    
    Returns:
        Error statistics per interface
    """
    netdev = run_command("cat /proc/net/dev")
    
    interfaces = []
    lines = netdev.split("\n")[2:]  # Skip header lines
    
    for line in lines:
        if ":" in line:
            parts = line.split(":")
            iface = parts[0].strip()
            stats = parts[1].split()
            
            if len(stats) >= 16:
                rx_errors = safe_parse_int(stats[2])
                rx_dropped = safe_parse_int(stats[3])
                tx_errors = safe_parse_int(stats[10])
                tx_dropped = safe_parse_int(stats[11])
                
                # Only include interfaces with errors
                if rx_errors > 0 or rx_dropped > 0 or tx_errors > 0 or tx_dropped > 0:
                    interfaces.append({
                        "interface": iface,
                        "rxErrors": rx_errors,
                        "rxDropped": rx_dropped,
                        "txErrors": tx_errors,
                        "txDropped": tx_dropped
                    })
    
    return {
        "interfaces": interfaces,
        "interfacesWithErrors": len(interfaces),
        "timestamp": get_timestamp()
    }


@router.get("/dns")
def get_dns_configuration() -> Dict[str, Any]:
    """
    Get DNS server configuration.
    
    Returns:
        DNS servers and resolver configuration
    """
    resolv_conf = run_command("cat /etc/resolv.conf")
    
    nameservers = []
    search_domains = []
    
    for line in resolv_conf.split("\n"):
        line = line.strip()
        if line.startswith("nameserver"):
            nameservers.append(line.split()[1] if len(line.split()) > 1 else "")
        elif line.startswith("search"):
            search_domains.extend(line.split()[1:])
    
    return {
        "nameservers": nameservers,
        "searchDomains": search_domains,
        "resolvConf": resolv_conf,
        "timestamp": get_timestamp()
    }


@router.get("/bandwidth")
def get_network_bandwidth() -> Dict[str, Any]:
    """
    Calculate current network bandwidth usage by sampling traffic twice.
    
    Returns:
        Bandwidth usage in bytes/sec for each interface
    """
    import time
    
    # First sample
    netdev1 = run_command("cat /proc/net/dev")
    time.sleep(1)
    # Second sample
    netdev2 = run_command("cat /proc/net/dev")
    
    def parse_netdev(output):
        interfaces = {}
        lines = output.split("\n")[2:]
        for line in lines:
            if ":" in line:
                parts = line.split(":")
                iface = parts[0].strip()
                stats = parts[1].split()
                if len(stats) >= 16:
                    interfaces[iface] = {
                        "rx": safe_parse_int(stats[0]),
                        "tx": safe_parse_int(stats[8])
                    }
        return interfaces
    
    ifaces1 = parse_netdev(netdev1)
    ifaces2 = parse_netdev(netdev2)
    
    bandwidth = []
    for iface in ifaces1:
        if iface in ifaces2:
            rx_rate = ifaces2[iface]["rx"] - ifaces1[iface]["rx"]
            tx_rate = ifaces2[iface]["tx"] - ifaces1[iface]["tx"]
            
            bandwidth.append({
                "interface": iface,
                "rxBytesPerSec": rx_rate,
                "txBytesPerSec": tx_rate,
                "rxMbps": round(rx_rate * 8 / 1_000_000, 2),
                "txMbps": round(tx_rate * 8 / 1_000_000, 2)
            })
    
    return {
        "bandwidth": bandwidth,
        "samplingInterval": "1 second",
        "timestamp": get_timestamp()
    }


@router.get("/docker")
def get_docker_networks() -> List[Dict[str, Any]]:
    """
    Get list of Docker networks with details.
    
    Returns:
        Docker networks with ID, name, driver, and scope
    """
    cmd = 'docker network ls --format "{{.ID}}|{{.Name}}|{{.Driver}}|{{.Scope}}"'
    output = run_command(cmd).strip()

    networks = []
    for line in output.split("\n"):
        if line.strip():
            parts = line.split("|")
            if len(parts) >= 4:
                networks.append({
                    "id": parts[0].strip(),
                    "name": parts[1].strip(),
                    "driver": parts[2].strip(),
                    "scope": parts[3].strip()
                })

    return networks
