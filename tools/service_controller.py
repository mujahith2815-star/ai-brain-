"""
System Service Controller for Orvix Universal Control.
Inspects, queries, starts, stops, and restarts Windows Services (or Linux systemd units).
"""

import json
import platform
import subprocess
from typing import Any, Dict, List, Optional


def list_services(status_filter: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    """
    Lists system services with optional filtering by status (e.g. 'Running', 'Stopped').
    """
    is_win = platform.system().lower() == "windows"
    services: List[Dict[str, Any]] = []

    try:
        if is_win:
            filter_clause = f"| Where-Object {{ $_.Status -eq '{status_filter}' }}" if status_filter else ""
            ps_cmd = (
                f"Get-Service {filter_clause} "
                "| Select-Object -First " + str(limit) + " Name, DisplayName, Status, StartType "
                "| ConvertTo-Json"
            )
            res = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if res.returncode == 0 and res.stdout.strip():
                try:
                    data = json.loads(res.stdout)
                    if isinstance(data, dict):
                        data = [data]
                    for s in data:
                        status_str = "Running" if s.get("Status") == 4 else ("Stopped" if s.get("Status") == 1 else str(s.get("Status")))
                        services.append({
                            "name": s.get("Name"),
                            "display_name": s.get("DisplayName"),
                            "status": status_str,
                            "start_type": str(s.get("StartType", "")),
                        })
                except Exception:
                    pass
        else:
            state_flag = f"--state={status_filter.lower()}" if status_filter else ""
            cmd = f"systemctl list-units --type=service {state_flag} --no-pager --no-legend | head -n {limit}"
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            for line in res.stdout.strip().split("\n"):
                parts = line.split(maxsplit=4)
                if len(parts) >= 4:
                    services.append({
                        "name": parts[0],
                        "status": parts[3],
                        "display_name": parts[4] if len(parts) > 4 else parts[0],
                    })

        return {
            "status": "SUCCESS",
            "total_services": len(services),
            "services": services,
        }
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}


def get_service_status(service_name: str) -> Dict[str, Any]:
    """Retrieves current operational status of a named service."""
    clean_name = service_name.strip()
    is_win = platform.system().lower() == "windows"

    try:
        if is_win:
            ps_cmd = f"Get-Service -Name '{clean_name}' -ErrorAction SilentlyContinue | Select-Object Name, DisplayName, Status, StartType | ConvertTo-Json"
            res = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0 and res.stdout.strip():
                try:
                    data = json.loads(res.stdout)
                    status_str = "Running" if data.get("Status") == 4 else ("Stopped" if data.get("Status") == 1 else str(data.get("Status")))
                    return {
                        "status": "SUCCESS",
                        "service_name": clean_name,
                        "display_name": data.get("DisplayName"),
                        "service_status": status_str,
                        "start_type": str(data.get("StartType", "")),
                    }
                except Exception:
                    pass
            return {"status": "NOT_FOUND", "service_name": clean_name, "message": "Service not found"}
        else:
            res = subprocess.run(["systemctl", "is-active", clean_name], capture_output=True, text=True)
            active_state = res.stdout.strip()
            return {
                "status": "SUCCESS",
                "service_name": clean_name,
                "service_status": active_state,
            }
    except Exception as e:
        return {"status": "FAILED", "service_name": clean_name, "error": str(e)}


def start_service(service_name: str) -> Dict[str, Any]:
    """Starts a stopped service."""
    clean_name = service_name.strip()
    is_win = platform.system().lower() == "windows"

    try:
        if is_win:
            ps_cmd = f"Start-Service -Name '{clean_name}' -ErrorAction Stop"
            res = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_cmd], capture_output=True, text=True)
        else:
            res = subprocess.run(["sudo", "systemctl", "start", clean_name], capture_output=True, text=True)

        if res.returncode == 0:
            return {"status": "SUCCESS", "message": f"Service '{clean_name}' started successfully"}
        else:
            return {"status": "FAILED", "error": res.stderr.strip() or "Failed to start service"}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}


def stop_service(service_name: str) -> Dict[str, Any]:
    """Stops an active service."""
    clean_name = service_name.strip()
    is_win = platform.system().lower() == "windows"

    try:
        if is_win:
            ps_cmd = f"Stop-Service -Name '{clean_name}' -Force -ErrorAction Stop"
            res = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_cmd], capture_output=True, text=True)
        else:
            res = subprocess.run(["sudo", "systemctl", "stop", clean_name], capture_output=True, text=True)

        if res.returncode == 0:
            return {"status": "SUCCESS", "message": f"Service '{clean_name}' stopped successfully"}
        else:
            return {"status": "FAILED", "error": res.stderr.strip() or "Failed to stop service"}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}


def restart_service(service_name: str) -> Dict[str, Any]:
    """Restarts a running or stopped service."""
    clean_name = service_name.strip()
    is_win = platform.system().lower() == "windows"

    try:
        if is_win:
            ps_cmd = f"Restart-Service -Name '{clean_name}' -Force -ErrorAction Stop"
            res = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_cmd], capture_output=True, text=True)
        else:
            res = subprocess.run(["sudo", "systemctl", "restart", clean_name], capture_output=True, text=True)

        if res.returncode == 0:
            return {"status": "SUCCESS", "message": f"Service '{clean_name}' restarted successfully"}
        else:
            return {"status": "FAILED", "error": res.stderr.strip() or "Failed to restart service"}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}
