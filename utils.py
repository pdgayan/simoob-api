"""
Utility functions for system monitoring and Docker operations.
Provides helper functions for running shell commands, parsing outputs, and formatting data.
"""

import subprocess
import re
from datetime import datetime
from typing import List, Dict, Any, Optional


def run_command(cmd: str) -> str:
    """
    Execute a shell command and return its output.
    
    Args:
        cmd: The shell command to execute
        
    Returns:
        Command output as string
    """
    try:
        return subprocess.getoutput(cmd)
    except Exception as e:
        return f"Error executing command: {str(e)}"


def parse_docker_format(output: str, separator: str = "|") -> List[List[str]]:
    """
    Parse Docker command output with custom format.
    
    Args:
        output: Raw command output
        separator: Field separator character
        
    Returns:
        List of parsed rows
    """
    lines = output.strip().split("\n")
    result = []
    for line in lines:
        if line.strip():
            result.append([field.strip() for field in line.split(separator)])
    return result


def extract_uptime(status: str) -> str:
    """
    Extract uptime information from Docker container status.
    
    Args:
        status: Docker container status string
        
    Returns:
        Formatted uptime or "Stopped"
    """
    if "Up" in status:
        match = re.search(r"Up (.+?)(?:\(|$)", status)
        return match.group(1).strip() if match else "Running"
    return "Stopped"


def get_timestamp() -> str:
    """
    Get current UTC timestamp in ISO format.
    
    Returns:
        ISO formatted timestamp
    """
    return datetime.utcnow().isoformat()


def parse_size_to_bytes(size_str: str) -> Optional[int]:
    """
    Convert human-readable size to bytes.
    
    Args:
        size_str: Size string like "1.5GB", "256MB", etc.
        
    Returns:
        Size in bytes or None if parsing fails
    """
    units = {
        'B': 1,
        'KB': 1024,
        'MB': 1024**2,
        'GB': 1024**3,
        'TB': 1024**4,
        'K': 1024,
        'M': 1024**2,
        'G': 1024**3,
        'T': 1024**4
    }
    
    match = re.match(r'([\d.]+)\s*([KMGT]?B?)', size_str.upper())
    if match:
        value, unit = match.groups()
        return int(float(value) * units.get(unit, 1))
    return None


def parse_percentage(percent_str: str) -> float:
    """
    Extract percentage value from string.
    
    Args:
        percent_str: String containing percentage (e.g., "45.2%")
        
    Returns:
        Percentage as float
    """
    match = re.search(r'([\d.]+)%?', percent_str)
    return float(match.group(1)) if match else 0.0


def format_bytes(bytes_val: int) -> str:
    """
    Format bytes to human-readable string.
    
    Args:
        bytes_val: Number of bytes
        
    Returns:
        Formatted string (e.g., "1.5 GB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} PB"


def safe_parse_int(value: str, default: int = 0) -> int:
    """
    Safely parse string to integer with fallback.
    
    Args:
        value: String to parse
        default: Default value if parsing fails
        
    Returns:
        Parsed integer or default
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_parse_float(value: str, default: float = 0.0) -> float:
    """
    Safely parse string to float with fallback.
    
    Args:
        value: String to parse
        default: Default value if parsing fails
        
    Returns:
        Parsed float or default
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def check_command_exists(command: str) -> bool:
    """
    Check if a command exists on the system.
    
    Args:
        command: Command name to check
        
    Returns:
        True if command exists, False otherwise
    """
    result = run_command(f"which {command} 2>/dev/null")
    return bool(result.strip())
