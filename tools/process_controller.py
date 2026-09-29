"""
Process Controller for Orvix Universal Control.
Inspects running processes, sorts by CPU/memory consumption, finds processes by name/PID,
gathers detailed metrics, and terminates processes safely.
"""

import os
import platform
import subprocess
from typing import Any, Dict, List, Optional, Union


def list_processes(sort_by: str = "cpu", limit: int = 20) -> Dict[str, Any]:
    """
    Lists active system processes sorted by 'cpu' or 'memory'.
    """
    procs: List[Dict[str, Any]] = []

    try:
        import psutil
        # Prime CPU percent measurement
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'status']):
            try:
                info = p.info
                mem_mb = round(info['memory_info'].rss / (1024 * 1024), 2) if info['memory_info'] else 0
                procs.append({
                    "pid": info["pid"],
                    "name": info["name"],
                    "cpu_percent": info["cpu_percent"] or 0.0,
                    "memory_mb": mem_mb,
                    "status": info["status"],
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if sort_by.lower() == "memory" or sort_by.lower() == "mem":
            procs.sort(key=lambda x: x["memory_mb"], reverse=True)
        else:
            procs.sort(key=lambda x: x["cpu_percent"], reverse=True)

        return {
            "status": "SUCCESS",
            "sort_by": sort_by,
            "total_processes": len(procs),
            "processes": procs[:limit],
        }
    except ImportError:
        return {"status": "FAILED", "error": "psutil library required for process inspection"}


def find_process(query: Union[str, int]) -> Dict[str, Any]:
    """
    Finds running processes matching a process name or specific PID.
    """
    matches = []
    try:
        import psutil
        is_numeric = str(query).strip().isdigit()
        target_pid = int(query) if is_numeric else None
        target_name = str(query).strip().lower()

        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'username']):
            try:
                info = p.info
                pid = info['pid']
                name = (info['name'] or "").lower()

                if (target_pid is not None and pid == target_pid) or (target_name in name):
                    mem_mb = round(info['memory_info'].rss / (1024 * 1024), 2) if info['memory_info'] else 0
                    matches.append({
                        "pid": pid,
                        "name": info["name"],
                        "cpu_percent": info["cpu_percent"],
                        "memory_mb": mem_mb,
                        "username": info.get("username"),
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return {
            "status": "SUCCESS",
            "query": str(query),
            "total_found": len(matches),
            "matches": matches,
        }
    except ImportError:
        return {"status": "FAILED", "error": "psutil library required"}


def kill_process(target: Union[str, int], force: bool = False) -> Dict[str, Any]:
    """
    Terminates a process by PID or process name.
    """
    try:
        import psutil
        is_numeric = str(target).strip().isdigit()

        if is_numeric:
            pid = int(target)
            proc = psutil.Process(pid)
            if force:
                proc.kill()
            else:
                proc.terminate()
            return {"status": "SUCCESS", "message": f"Terminated process PID {pid}"}
        else:
            name = str(target).strip().lower()
            terminated = []
            for p in psutil.process_iter(['pid', 'name']):
                try:
                    if name in (p.info['name'] or '').lower():
                        if force:
                            p.kill()
                        else:
                            p.terminate()
                        terminated.append(p.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return {
                "status": "SUCCESS",
                "message": f"Terminated {len(terminated)} processes matching '{name}'",
                "terminated_pids": terminated,
            }
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}


def get_process_metrics(pid: int) -> Dict[str, Any]:
    """
    Gathers detailed resource consumption metrics for a specific PID.
    """
    try:
        import psutil
        proc = psutil.Process(pid)
        with proc.oneshot():
            mem = proc.memory_info()
            cpu = proc.cpu_percent(interval=0.1)
            num_threads = proc.num_threads()
            status = proc.status()
            create_time = proc.create_time()
            name = proc.name()
            cmdline = proc.cmdline()

        return {
            "status": "SUCCESS",
            "pid": pid,
            "name": name,
            "cmdline": " ".join(cmdline),
            "status": status,
            "cpu_percent": cpu,
            "memory_rss_mb": round(mem.rss / (1024 * 1024), 2),
            "memory_vms_mb": round(mem.vms / (1024 * 1024), 2),
            "threads": num_threads,
            "created_at": create_time,
        }
    except Exception as e:
        return {"status": "FAILED", "pid": pid, "error": str(e)}
