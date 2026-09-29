"""
Hardware and System Metrics Controller for Orvix Universal Control.
Inspects CPU, RAM, disks, battery, displays, and motherboard specifications
using psutil, platform utilities, and PowerShell/WMI fallback.
"""

import os
import platform
import shutil
import subprocess
from typing import Any, Dict, List, Optional


def get_cpu_info() -> Dict[str, Any]:
    """Retrieves processor model, core counts, and current utilization."""
    try:
        import psutil
        cpu_pct = psutil.cpu_percent(interval=0.2)
        cores_phys = psutil.cpu_count(logical=False) or 1
        cores_total = psutil.cpu_count(logical=True) or 1
        freq = psutil.cpu_freq()
        current_mhz = round(freq.current, 1) if freq else None
    except ImportError:
        cpu_pct = None
        cores_phys = os.cpu_count() or 1
        cores_total = os.cpu_count() or 1
        current_mhz = None

    model = platform.processor() or platform.machine()
    return {
        "status": "SUCCESS",
        "processor_model": model,
        "physical_cores": cores_phys,
        "logical_cores": cores_total,
        "current_usage_percent": cpu_pct,
        "current_frequency_mhz": current_mhz,
        "architecture": platform.architecture()[0],
    }


def get_ram_info() -> Dict[str, Any]:
    """Retrieves physical RAM and swap/pagefile metrics."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            "status": "SUCCESS",
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "usage_percent": mem.percent,
            "swap_total_gb": round(swap.total / (1024**3), 2),
            "swap_used_gb": round(swap.used / (1024**3), 2),
            "swap_percent": swap.percent,
        }
    except ImportError:
        return {"status": "FAILED", "error": "psutil library not available"}


def get_disk_info() -> Dict[str, Any]:
    """Inspects storage partitions and mounted drives."""
    disks = []
    try:
        import psutil
        partitions = psutil.disk_partitions(all=False)
        for p in partitions:
            try:
                usage = psutil.disk_usage(p.mountpoint)
                disks.append({
                    "device": p.device,
                    "mountpoint": p.mountpoint,
                    "fstype": p.fstype,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "usage_percent": usage.percent,
                })
            except (PermissionError, OSError):
                continue
    except ImportError:
        # Fallback to shutil.disk_usage
        usage = shutil.disk_usage(os.getcwd())
        disks.append({
            "device": "current",
            "mountpoint": os.getcwd(),
            "fstype": "unknown",
            "total_gb": round(usage.total / (1024**3), 2),
            "used_gb": round(usage.used / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
            "usage_percent": round((usage.used / usage.total) * 100, 1),
        })

    return {
        "status": "SUCCESS",
        "disk_count": len(disks),
        "disks": disks,
    }


def get_battery_status() -> Dict[str, Any]:
    """Retrieves laptop battery percentage, power plug status, and discharge time."""
    try:
        import psutil
        battery = psutil.sensors_battery()
        if battery is None:
            return {
                "status": "SUCCESS",
                "has_battery": False,
                "message": "No battery detected (Desktop or VM system)",
            }
        return {
            "status": "SUCCESS",
            "has_battery": True,
            "percent": round(battery.percent, 1),
            "power_plugged": battery.power_plugged,
            "secsleft": battery.secsleft,
        }
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}


def get_display_info() -> Dict[str, Any]:
    """Retrieves display and monitor count information."""
    is_win = platform.system().lower() == "windows"
    monitors = []

    try:
        if is_win:
            ps_cmd = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "[System.Windows.Forms.Screen]::AllScreens | ForEach-Object { "
                "  @{ DeviceName=$_.DeviceName; Primary=$_.Primary; Width=$_.Bounds.Width; Height=$_.Bounds.Height } "
                "} | ConvertTo-Json"
            )
            res = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0 and res.stdout.strip():
                import json
                try:
                    data = json.loads(res.stdout)
                    if isinstance(data, dict):
                        data = [data]
                    for d in data:
                        monitors.append({
                            "device": d.get("DeviceName"),
                            "primary": d.get("Primary"),
                            "resolution": f"{d.get('Width')}x{d.get('Height')}",
                        })
                except Exception:
                    pass
        if not monitors:
            monitors.append({"device": "Primary", "resolution": "Standard Display"})

        return {
            "status": "SUCCESS",
            "monitor_count": len(monitors),
            "monitors": monitors,
        }
    except Exception as e:
        return {"status": "SUCCESS", "monitor_count": 1, "monitors": [{"device": "Default", "resolution": "Unknown"}]}


def get_hardware_summary() -> Dict[str, Any]:
    """Consolidated hardware inspection."""
    return {
        "status": "SUCCESS",
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "cpu": get_cpu_info(),
        "ram": get_ram_info(),
        "disks": get_disk_info(),
        "battery": get_battery_status(),
        "displays": get_display_info(),
    }
