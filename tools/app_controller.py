"""
Application Controller for Orvix Universal Control.
Launches, closes, inspects, and monitors installed/running desktop applications.
"""

import os
import platform
import shutil
import subprocess
from typing import Any, Dict, List, Optional


def launch_app(app_name_or_path: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Launches an application by binary name, registered shortcut, or absolute path.
    """
    clean_target = app_name_or_path.strip()
    is_win = platform.system().lower() == "windows"
    cmd_args = [clean_target] + (args or [])

    try:
        if is_win:
            # On Windows, use start or Popen with shell=True for friendly app names like 'notepad' or 'calc'
            full_cmd = f"Start-Process -FilePath '{clean_target}'"
            if args:
                args_str = " ".join(f"'{a}'" for a in args)
                full_cmd += f" -ArgumentList {args_str}"
            proc = subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", full_cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        else:
            proc = subprocess.Popen(
                cmd_args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

        return {
            "status": "SUCCESS",
            "message": f"Launched application: {clean_target}",
            "target": clean_target,
        }
    except Exception as e:
        return {
            "status": "FAILED",
            "error": f"Failed to launch '{clean_target}': {str(e)}",
            "target": clean_target,
        }


def close_app(app_name: str, force: bool = False) -> Dict[str, Any]:
    """
    Terminates running instances of an application by process name.
    """
    is_win = platform.system().lower() == "windows"
    name = app_name.strip()
    if is_win and not name.lower().endswith(".exe"):
        exe_name = f"{name}.exe"
    else:
        exe_name = name

    try:
        if is_win:
            force_flag = "-Force" if force else ""
            ps_cmd = f"Stop-Process -Name '{name.replace('.exe', '')}' {force_flag} -ErrorAction Stop"
            res = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                capture_output=True,
                text=True,
            )
            if res.returncode == 0:
                return {"status": "SUCCESS", "message": f"Closed application '{name}'"}
            else:
                return {"status": "FAILED", "error": res.stderr.strip() or "Process not found or access denied"}
        else:
            signal = "-9" if force else "-15"
            res = subprocess.run(["killall", signal, name], capture_output=True, text=True)
            if res.returncode == 0:
                return {"status": "SUCCESS", "message": f"Closed application '{name}'"}
            else:
                return {"status": "FAILED", "error": res.stderr.strip() or "Process not found"}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}


def list_running_apps(limit: int = 50) -> Dict[str, Any]:
    """
    Lists running graphical or high-level application processes.
    """
    is_win = platform.system().lower() == "windows"
    apps: List[Dict[str, Any]] = []

    try:
        if is_win:
            ps_cmd = (
                "Get-Process | Where-Object { $_.MainWindowHandle -ne 0 -or $_.MainWindowTitle -ne '' } "
                "| Select-Object Id, ProcessName, MainWindowTitle, WorkingSet64 "
                "| ConvertTo-Json"
            )
            res = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if res.returncode == 0 and res.stdout.strip():
                import json
                try:
                    data = json.loads(res.stdout)
                    if isinstance(data, dict):
                        data = [data]
                    for item in data[:limit]:
                        mem_mb = round(item.get("WorkingSet64", 0) / (1024 * 1024), 2)
                        apps.append({
                            "pid": item.get("Id"),
                            "name": item.get("ProcessName"),
                            "title": item.get("MainWindowTitle"),
                            "memory_mb": mem_mb,
                        })
                except Exception:
                    pass
        else:
            # Linux fallback via wmctrl or ps
            res = subprocess.run(
                ["ps", "-eo", "pid,comm,%mem,%cpu", "--sort=-%mem"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            lines = res.stdout.strip().split("\n")[1:limit+1]
            for l in lines:
                parts = l.split()
                if len(parts) >= 4:
                    apps.append({
                        "pid": int(parts[0]),
                        "name": parts[1],
                        "memory_percent": parts[2],
                        "cpu_percent": parts[3],
                    })

        return {
            "status": "SUCCESS",
            "total_apps": len(apps),
            "apps": apps,
        }
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}


def is_app_running(app_name: str) -> Dict[str, Any]:
    """
    Checks if an application is currently running.
    """
    clean = app_name.lower().replace(".exe", "").strip()
    app_list = list_running_apps(limit=200)
    if app_list.get("status") != "SUCCESS":
        return {"status": "FAILED", "error": app_list.get("error")}

    running = any(clean in a.get("name", "").lower() or clean in a.get("title", "").lower() for a in app_list.get("apps", []))
    return {
        "status": "SUCCESS",
        "app_name": app_name,
        "is_running": running,
    }
