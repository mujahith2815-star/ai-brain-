"""
Network Management and Diagnostics Controller for Orvix Universal Control.
Inspects adapters, IP addresses, active sockets, WiFi networks,
and performs port testing, ping diagnostics, and DNS flushes.
"""

import platform
import re
import socket
import subprocess
from typing import Any, Dict, List, Optional


def get_ip_addresses() -> Dict[str, Any]:
    """Retrieves local IPv4 and IPv6 addresses for all active interfaces."""
    ips = []
    try:
        import psutil
        addrs = psutil.net_if_addrs()
        for iface, if_addrs in addrs.items():
            for addr in if_addrs:
                if addr.family == socket.AF_INET:
                    ips.append({
                        "interface": iface,
                        "family": "IPv4",
                        "address": addr.address,
                        "netmask": addr.netmask,
                    })
                elif addr.family == socket.AF_INET6 and not addr.address.startswith("fe80"):
                    ips.append({
                        "interface": iface,
                        "family": "IPv6",
                        "address": addr.address,
                    })
    except ImportError:
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            ips.append({"interface": "primary", "family": "IPv4", "address": local_ip})
        except Exception:
            pass

    return {
        "status": "SUCCESS",
        "ip_addresses": ips,
    }


def ping_host(host: str, count: int = 4) -> Dict[str, Any]:
    """Tests ICMP connectivity and measures round-trip latency to a host."""
    is_win = platform.system().lower() == "windows"
    param = "-n" if is_win else "-c"
    cmd = ["ping", param, str(count), host]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        success = res.returncode == 0
        return {
            "status": "SUCCESS" if success else "FAILED",
            "host": host,
            "connected": success,
            "output": res.stdout.strip(),
        }
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "host": host, "connected": False, "error": "Ping timed out"}
    except Exception as e:
        return {"status": "FAILED", "host": host, "connected": False, "error": str(e)}


def test_port(host: str, port: int, timeout: float = 3.0) -> Dict[str, Any]:
    """Checks if a remote or local TCP port is open and accepting connections."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        res = s.connect_ex((host, int(port)))
        is_open = res == 0
        return {
            "status": "SUCCESS",
            "host": host,
            "port": port,
            "is_open": is_open,
            "message": "Port is open" if is_open else f"Port closed (code {res})",
        }
    except Exception as e:
        return {
            "status": "FAILED",
            "host": host,
            "port": port,
            "is_open": False,
            "error": str(e),
        }
    finally:
        s.close()


def get_active_connections(limit: int = 30) -> Dict[str, Any]:
    """Lists currently open TCP/UDP sockets and established network connections."""
    connections = []
    try:
        import psutil
        for conn in psutil.net_connections(kind="inet"):
            if conn.status == "LISTEN" or conn.status == "ESTABLISHED":
                connections.append({
                    "fd": conn.fd,
                    "family": "IPv4" if conn.family == socket.AF_INET else "IPv6",
                    "type": "TCP" if conn.type == socket.SOCK_STREAM else "UDP",
                    "local_address": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                    "remote_address": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                    "status": conn.status,
                    "pid": conn.pid,
                })
                if len(connections) >= limit:
                    break
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}

    return {
        "status": "SUCCESS",
        "total_connections": len(connections),
        "connections": connections,
    }


def get_wifi_networks() -> Dict[str, Any]:
    """Scans for visible Wi-Fi SSIDs."""
    is_win = platform.system().lower() == "windows"
    networks = []

    try:
        if is_win:
            res = subprocess.run(
                ["netsh", "wlan", "show", "networks"],
                capture_output=True,
                text=True,
                timeout=8,
            )
            if res.returncode == 0:
                for line in res.stdout.split("\n"):
                    if "SSID" in line and ":" in line:
                        ssid = line.split(":", 1)[1].strip()
                        if ssid and ssid not in networks:
                            networks.append(ssid)
        else:
            res = subprocess.run(
                ["nmcli", "-t", "-f", "SSID", "dev", "wifi"],
                capture_output=True,
                text=True,
                timeout=8,
            )
            if res.returncode == 0:
                for line in res.stdout.split("\n"):
                    clean = line.strip()
                    if clean and clean not in networks:
                        networks.append(clean)

        return {
            "status": "SUCCESS",
            "networks_found": len(networks),
            "ssids": networks,
        }
    except Exception as e:
        return {"status": "FAILED", "error": str(e), "networks_found": 0, "ssids": []}


def flush_dns() -> Dict[str, Any]:
    """Flushes the local OS DNS resolver cache."""
    is_win = platform.system().lower() == "windows"
    try:
        if is_win:
            res = subprocess.run(["ipconfig", "/flushdns"], capture_output=True, text=True)
        else:
            res = subprocess.run(["resolvectl", "flush-caches"], capture_output=True, text=True)

        return {
            "status": "SUCCESS" if res.returncode == 0 else "FAILED",
            "message": res.stdout.strip() or "DNS cache flushed",
        }
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}
