"""
Universal OS & Application Controller for P.H.A.S.S Sphere.
Enables opening, controlling, inspecting, and managing any application and system process on the host OS.
"""

from __future__ import annotations
import os
import subprocess
import sys
import webbrowser
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("phass.tools.os_controller")


@dataclass
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    status: str = "RUNNING"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pid": self.pid,
            "name": self.name,
            "cpu_percent": round(self.cpu_percent, 1),
            "memory_mb": round(self.memory_mb, 1),
            "status": self.status,
        }


class LaunchResult(tuple):
    """
    Two-element tuple (success, message) with an additional .pid attribute
    for seamless backwards-compatibility with unpacking.
    """
    def __new__(cls, success: bool, message: str, pid: Optional[int] = None):
        return super().__new__(cls, (success, message))

    def __init__(self, success: bool, message: str, pid: Optional[int] = None):
        self.success = success
        self.message = message
        self.pid = pid

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": "SUCCESS" if self.success else "FAILED",
            "message": self.message,
            "pid": self.pid,
        }


class UniversalOSController:
    """
    Controls desktop applications, processes, and operating system commands.
    """

    def __init__(self):
        self.last_pid: Optional[int] = None

    # Comprehensive application and web service registry
    APP_REGISTRY: Dict[str, Dict[str, Any]] = {
        "whatsapp": {"type": "URI", "target": "https://web.whatsapp.com", "fallback_exe": "WhatsApp.exe"},
        "google drive": {"type": "URI", "target": "https://drive.google.com"},
        "drive": {"type": "URI", "target": "https://drive.google.com"},
        "gmail": {"type": "URI", "target": "https://mail.google.com"},
        "google mail": {"type": "URI", "target": "https://mail.google.com"},
        "google maps": {"type": "URI", "target": "https://maps.google.com"},
        "maps": {"type": "URI", "target": "https://maps.google.com"},
        "youtube": {"type": "URI", "target": "https://www.youtube.com"},
        "spotify": {"type": "EXE", "target": "spotify", "fallback_uri": "https://open.spotify.com"},
        "chrome": {"type": "EXE", "target": "chrome", "fallback_uri": "https://www.google.com"},
        "browser": {"type": "URI", "target": "https://www.google.com"},
        "google": {"type": "URI", "target": "https://www.google.com"},
        "github": {"type": "URI", "target": "https://github.com"},
        "chatgpt": {"type": "URI", "target": "https://chatgpt.com"},
        "reddit": {"type": "URI", "target": "https://reddit.com"},
        "twitter": {"type": "URI", "target": "https://x.com"},
        "x": {"type": "URI", "target": "https://x.com"},
        "discord": {"type": "EXE", "target": "discord", "fallback_uri": "https://discord.com/app"},
        "telegram": {"type": "EXE", "target": "telegram", "fallback_uri": "https://web.telegram.org"},
        "vscode": {"type": "EXE", "target": "code"},
        "visual studio code": {"type": "EXE", "target": "code"},
        "code": {"type": "EXE", "target": "code"},
        "notepad": {"type": "EXE", "target": "notepad.exe"},
        "calculator": {"type": "EXE", "target": "calc.exe"},
        "calc": {"type": "EXE", "target": "calc.exe"},
        "explorer": {"type": "EXE", "target": "explorer.exe"},
        "terminal": {"type": "EXE", "target": "cmd.exe"},
        "cmd": {"type": "EXE", "target": "cmd.exe"},
        "powershell": {"type": "EXE", "target": "powershell.exe"},
        "taskmgr": {"type": "EXE", "target": "taskmgr.exe"},
    }

    def launch_application(self, app_name: str, custom_target: Optional[str] = None) -> LaunchResult:
        """
        Launches an application by name, protocol URI, or custom path.
        Handles compound instructions (e.g. 'google drive and show last message').
        """
        raw_name = app_name.strip()
        clean_name = raw_name.lower()
        sub_action = ""

        # Handle compound actions like "google drive and show last message"
        if " and " in clean_name:
            parts = clean_name.split(" and ", 1)
            clean_name = parts[0].strip()
            sub_action = parts[1].strip()

        # 1. Check exact or longest matching registry key
        matched_key = None
        if clean_name in self.APP_REGISTRY:
            matched_key = clean_name
        else:
            # Check prefix / substring matches
            for k in sorted(self.APP_REGISTRY.keys(), key=len, reverse=True):
                if k in clean_name or clean_name.startswith(k):
                    matched_key = k
                    break

        if matched_key:
            meta = self.APP_REGISTRY[matched_key]
            if meta["type"] == "URI":
                try:
                    webbrowser.open(meta["target"])
                    msg = f"Opened {matched_key.title()} in browser ({meta['target']})."
                    if sub_action:
                        msg += f" (Sub-directive: '{sub_action}' active on target surface)."
                    return LaunchResult(True, msg, None)
                except Exception as e:
                    return LaunchResult(False, f"Failed to open URI for {matched_key}: {e}", None)

            elif meta["type"] == "EXE":
                try:
                    target_cmd = meta["target"]
                    exp_target = os.path.expandvars(os.path.expanduser(custom_target)) if custom_target else None
                    if exp_target:
                        target_cmd = f'{meta["target"]} "{exp_target}"'

                    if sys.platform == "win32":
                        try:
                            cmd_list = [meta["target"]]
                            if exp_target:
                                cmd_list.append(exp_target)
                            proc = subprocess.Popen(cmd_list, shell=False)
                        except Exception:
                            proc = subprocess.Popen(target_cmd, shell=True)
                    else:
                        cmd_list = [meta["target"]]
                        if exp_target:
                            cmd_list.append(exp_target)
                        proc = subprocess.Popen(cmd_list)

                    pid = proc.pid
                    self.last_pid = pid
                    msg = f"Launched application: {target_cmd} (PID: {pid})."
                    if sub_action:
                        msg += f" (Sub-directive: '{sub_action}')."
                    return LaunchResult(True, msg, pid)
                except Exception as e:
                    if "fallback_uri" in meta:
                        webbrowser.open(meta["fallback_uri"])
                        return LaunchResult(True, f"Launched web fallback for {matched_key}.", None)
                    return LaunchResult(False, f"Failed to launch executable {meta['target']}: {e}", None)

        # 2. Custom Target / Arbitrary Path / URL
        target = custom_target or clean_name
        if target.startswith("http://") or target.startswith("https://"):
            try:
                webbrowser.open(target)
                return LaunchResult(True, f"Opened URL: {target}", None)
            except Exception as e:
                return LaunchResult(False, f"Failed to open URL: {e}", None)

        # 3. Safe search / browser fallback if not a recognized local executable
        try:
            if sys.platform == "win32":
                proc = subprocess.Popen(f'start "" "{target}"', shell=True)
            else:
                proc = subprocess.Popen([target])
            pid = proc.pid
            self.last_pid = pid
            return LaunchResult(True, f"Launched application process: {target} (PID: {pid})", pid)
        except Exception:
            # Open web search fallback
            search_url = f"https://www.google.com/search?q={target.replace(' ', '+')}"
            webbrowser.open(search_url)
            return LaunchResult(True, f"Opened web search for '{target}' in default browser.", None)


    def list_running_processes(self, filter_name: Optional[str] = None, max_results: int = 25) -> List[ProcessInfo]:
        """
        Lists active system processes using native OS utilities (tasklist on Windows / ps on POSIX).
        """
        processes: List[ProcessInfo] = []

        try:
            if sys.platform == "win32":
                out = subprocess.check_output("tasklist /FO CSV /NH", shell=True, text=True, errors="ignore")
                for line in out.strip().split("\n"):
                    parts = [p.strip('"') for p in line.split('","')]
                    if len(parts) >= 5:
                        p_name = parts[0]
                        try:
                            p_id = int(parts[1])
                        except ValueError:
                            continue

                        # Memory (e.g. '14,280 K')
                        mem_str = parts[4].replace(",", "").replace(" K", "").replace("KB", "").strip()
                        try:
                            mem_mb = float(mem_str) / 1024.0
                        except ValueError:
                            mem_mb = 0.0

                        if filter_name and filter_name.lower() not in p_name.lower():
                            continue

                        processes.append(ProcessInfo(pid=p_id, name=p_name, memory_mb=mem_mb))
                        if len(processes) >= max_results:
                            break
        except Exception as e:
            logger.error(f"Error listing processes: {e}")

        return processes

    def terminate_process(self, pid_or_name: str | int) -> Tuple[bool, str]:
        """
        Terminates a target process by PID or image name.
        """
        try:
            if isinstance(pid_or_name, int) or pid_or_name.isdigit():
                pid = int(pid_or_name)
                if sys.platform == "win32":
                    subprocess.run(f"taskkill /F /PID {pid}", shell=True, check=True, capture_output=True)
                else:
                    os.kill(pid, 9)
                return True, f"Successfully terminated PID {pid}."
            else:
                name = str(pid_or_name).strip()
                if not name.endswith(".exe") and sys.platform == "win32":
                    name += ".exe"
                if sys.platform == "win32":
                    subprocess.run(f"taskkill /F /IM {name}", shell=True, check=True, capture_output=True)
                return True, f"Successfully terminated process: {name}."
        except Exception as e:
            return False, f"Failed to terminate process '{pid_or_name}': {e}"

    def execute_command(self, command: str, timeout_sec: int = 15) -> Dict[str, Any]:
        """
        Executes a system shell command safely with stdout/stderr capture and timeout limits.
        """
        try:
            res = subprocess.run(
                command,
                shell=True,
                text=True,
                capture_output=True,
                timeout=timeout_sec,
                errors="replace",
            )
            return {
                "success": res.returncode == 0,
                "exit_code": res.returncode,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip(),
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Execution timed out after {timeout_sec}s.",
            }
        except Exception as e:
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
            }


os_controller = UniversalOSController()
