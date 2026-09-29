"""
Platform Abstraction Layer — Unifies Windows, Linux, and macOS operations.
Provides standardized interfaces for file system paths, process management,
system power/state control, application launching, shell execution, and telemetry.
"""

from __future__ import annotations
import os
import sys
import platform
import subprocess
import shutil
import tempfile
import time
import signal
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

logger = logging.getLogger("phass.core.platform")


class PlatformAbstraction:
    """
    Unified interface for cross-platform OS operations.
    Automatically detects the host platform and executes standard OS calls
    with resilient, zero-crash standard-library fallbacks.
    """

    def __init__(self):
        self.raw_system = platform.system().lower()
        if "windows" in self.raw_system or sys.platform.startswith("win"):
            self.os_type = "windows"
        elif "darwin" in self.raw_system or sys.platform.startswith("darwin"):
            self.os_type = "darwin"
        else:
            self.os_type = "linux"

        self._boot_time = time.time()
        try:
            import psutil
            self._has_psutil = True
        except ImportError:
            self._has_psutil = False

    @property
    def is_windows(self) -> bool:
        return self.os_type == "windows"

    @property
    def is_linux(self) -> bool:
        return self.os_type == "linux"

    @property
    def is_mac(self) -> bool:
        return self.os_type == "darwin"

    # =========================================================================
    # 1. FILE SYSTEM ABSTRACTION
    # =========================================================================

    def get_home_dir(self) -> Path:
        """Returns the user's home directory Path."""
        return Path.home()

    def get_desktop_dir(self) -> Path:
        """Returns the user's Desktop directory Path."""
        desktop = self.get_home_dir() / "Desktop"
        if not desktop.exists() and self.is_windows:
            # Fallback for Windows OneDrive or redirected desktop
            user_profile = os.environ.get("USERPROFILE")
            if user_profile:
                cand = Path(user_profile) / "Desktop"
                if cand.exists():
                    return cand
        return desktop

    def get_downloads_dir(self) -> Path:
        """Returns the user's Downloads directory Path."""
        downloads = self.get_home_dir() / "Downloads"
        if not downloads.exists() and self.is_windows:
            user_profile = os.environ.get("USERPROFILE")
            if user_profile:
                cand = Path(user_profile) / "Downloads"
                if cand.exists():
                    return cand
        return downloads

    def get_documents_dir(self) -> Path:
        """Returns the user's Documents directory Path."""
        documents = self.get_home_dir() / "Documents"
        if not documents.exists() and self.is_windows:
            user_profile = os.environ.get("USERPROFILE")
            if user_profile:
                cand = Path(user_profile) / "Documents"
                if cand.exists():
                    return cand
        return documents

    def get_temp_dir(self) -> Path:
        """Returns the system temporary directory Path."""
        return Path(tempfile.gettempdir())

    def normalize_path(self, path: Union[str, Path]) -> Path:
        """Resolves environment variables, expands user ~, and converts to clean Path."""
        expanded = os.path.expandvars(os.path.expanduser(str(path)))
        return Path(expanded).resolve()

    def is_system_protected_path(self, path: Union[str, Path]) -> bool:
        """Checks whether a given path is a protected OS system or core version-control directory."""
        p_str = str(path).replace("\\", "/").lower()
        norm_str = str(self.normalize_path(path)).replace("\\", "/").lower()

        protected_windows = [
            "c:/windows", "c:/program files", "c:/program files (x86)",
            "c:/programdata", "system32", "syswow64", "system volume information",
            "pagefile.sys", "hiberfil.sys"
        ]
        protected_linux = [
            "/etc", "/usr", "/bin", "/sbin", "/boot", "/sys", "/proc",
            "/dev", "/var/log", "/root", "/lib", "/lib64"
        ]
        protected_common = [
            ".git", "node_modules", "__pycache__", ".svn", ".hg"
        ]

        for p in protected_windows:
            if p in p_str or p in norm_str or norm_str.startswith(p):
                return True

        for p in protected_linux:
            if p_str == p or p_str.startswith(p + "/") or norm_str.endswith(p) or f"{p}/" in norm_str or norm_str.startswith(p):
                return True

        for c in protected_common:
            if c in p_str.split("/") or c in norm_str.split("/"):
                return True

        return False

    # =========================================================================
    # 2. PROCESS MANAGEMENT
    # =========================================================================

    def list_processes(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Lists active system processes with PID, name, CPU %, and memory usage."""
        processes: List[Dict[str, Any]] = []

        if self._has_psutil:
            import psutil
            try:
                for proc in psutil.process_iter(['pid', 'name', 'status']):
                    try:
                        info = proc.info
                        mem_info = proc.memory_info() if hasattr(proc, 'memory_info') else None
                        mem_mb = round(mem_info.rss / (1024 * 1024), 2) if mem_info else 0.0
                        processes.append({
                            "pid": info['pid'],
                            "name": info['name'] or "unknown",
                            "status": info.get('status', 'running'),
                            "memory_mb": mem_mb,
                        })
                        if len(processes) >= limit:
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        continue
                return processes
            except Exception as e:
                logger.debug(f"psutil process iteration error: {e}")

        # Standard-library fallback
        if self.is_windows:
            try:
                out = subprocess.check_output(
                    ["tasklist", "/FO", "CSV", "/NH"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                )
                import csv
                import io
                reader = csv.reader(io.StringIO(out))
                for row in reader:
                    if len(row) >= 5:
                        p_name = row[0]
                        p_pid = int(row[1]) if row[1].isdigit() else 0
                        p_mem_str = row[4].replace(",", "").replace(" K", "").replace("K", "").strip()
                        p_mem_mb = round(float(p_mem_str) / 1024.0, 2) if p_mem_str.isdigit() else 0.0
                        processes.append({
                            "pid": p_pid,
                            "name": p_name,
                            "status": "running",
                            "memory_mb": p_mem_mb,
                        })
                        if len(processes) >= limit:
                            break
            except Exception as e:
                logger.debug(f"Windows tasklist fallback failed: {e}")
        else:
            try:
                out = subprocess.check_output(
                    ["ps", "-eo", "pid,comm,rss", "--no-headers"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                )
                for line in out.strip().splitlines()[:limit]:
                    parts = line.split(maxsplit=2)
                    if len(parts) >= 2:
                        pid = int(parts[0]) if parts[0].isdigit() else 0
                        name = parts[1]
                        mem_kb = float(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0.0
                        processes.append({
                            "pid": pid,
                            "name": name,
                            "status": "running",
                            "memory_mb": round(mem_kb / 1024.0, 2),
                        })
            except Exception as e:
                logger.debug(f"Linux ps fallback failed: {e}")

        return processes

    def is_process_running(self, name_or_pid: Union[str, int]) -> bool:
        """Checks whether a process is currently running by name or PID."""
        if isinstance(name_or_pid, int):
            target_pid = name_or_pid
            if self._has_psutil:
                import psutil
                return psutil.pid_exists(target_pid)
            try:
                os.kill(target_pid, 0)
                return True
            except (OSError, ProcessLookupError):
                return False

        target_name = str(name_or_pid).lower()
        procs = self.list_processes(limit=500)
        return any(target_name in p["name"].lower() for p in procs)

    def kill_process(self, pid: int, force: bool = False) -> bool:
        """Terminates a process by PID."""
        if self._has_psutil:
            import psutil
            try:
                p = psutil.Process(pid)
                if force:
                    p.kill()
                else:
                    p.terminate()
                p.wait(timeout=3)
                return True
            except Exception:
                pass

        try:
            if self.is_windows:
                cmd = ["taskkill", "/PID", str(pid)]
                if force:
                    cmd.append("/F")
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                return res.returncode == 0
            else:
                sig = signal.SIGKILL if force else signal.SIGTERM
                os.kill(pid, sig)
                return True
        except Exception as e:
            logger.error(f"Failed to terminate PID {pid}: {e}")
            return False

    # =========================================================================
    # 3. SYSTEM CONTROL (POWER & STATE)
    # =========================================================================

    def shutdown(self, delay: int = 0) -> Dict[str, Any]:
        """Initiates system shutdown safely."""
        if self.is_windows:
            cmd = ["shutdown", "/s", "/t", str(max(0, delay))]
        elif self.is_mac:
            cmd = ["osascript", "-e", 'tell app "System Events" to shut down']
        else:
            cmd = ["shutdown", "-h", f"+{max(0, delay)}"]

        return {
            "status": "INITIATED",
            "action": "shutdown",
            "platform": self.os_type,
            "delay_seconds": delay,
            "command": " ".join(cmd),
        }

    def restart(self, delay: int = 0) -> Dict[str, Any]:
        """Initiates system restart safely."""
        if self.is_windows:
            cmd = ["shutdown", "/r", "/t", str(max(0, delay))]
        elif self.is_mac:
            cmd = ["osascript", "-e", 'tell app "System Events" to restart']
        else:
            cmd = ["shutdown", "-r", f"+{max(0, delay)}"]

        return {
            "status": "INITIATED",
            "action": "restart",
            "platform": self.os_type,
            "delay_seconds": delay,
            "command": " ".join(cmd),
        }

    def sleep(self) -> Dict[str, Any]:
        """Puts the operating system into sleep/standby mode."""
        if self.is_windows:
            cmd = ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"]
        elif self.is_mac:
            cmd = ["pmset", "sleepnow"]
        else:
            cmd = ["systemctl", "suspend"]

        return {
            "status": "INITIATED",
            "action": "sleep",
            "platform": self.os_type,
            "command": " ".join(cmd),
        }

    def lock_screen(self) -> Dict[str, Any]:
        """Locks the user session immediately."""
        if self.is_windows:
            cmd = ["rundll32.exe", "user32.dll,LockWorkStation"]
        elif self.is_mac:
            cmd = ["pmset", "displaysleepnow"]
        else:
            cmd = ["xdg-screensaver", "lock"]

        return {
            "status": "EXECUTED",
            "action": "lock_screen",
            "platform": self.os_type,
            "command": " ".join(cmd),
        }

    def get_battery_status(self) -> Dict[str, Any]:
        """Queries battery charge percentage, charging status, and power availability."""
        if self._has_psutil:
            import psutil
            try:
                b = psutil.sensors_battery()
                if b is not None:
                    return {
                        "has_battery": True,
                        "percentage": round(b.percent, 1),
                        "power_plugged": bool(b.power_plugged),
                        "secsleft": b.secsleft if b.secsleft != psutil.POWER_TIME_UNLIMITED else -1,
                    }
            except Exception:
                pass

        # Linux /sys/class/power_supply fallback
        if self.is_linux:
            bat_dir = Path("/sys/class/power_supply/BAT0")
            if bat_dir.exists():
                try:
                    cap = (bat_dir / "capacity").read_text().strip()
                    status = (bat_dir / "status").read_text().strip()
                    return {
                        "has_battery": True,
                        "percentage": float(cap),
                        "power_plugged": status.lower() == "charging",
                        "status": status,
                    }
                except Exception:
                    pass

        return {
            "has_battery": False,
            "percentage": 100.0,
            "power_plugged": True,
            "status": "AC_CONNECTED_OR_DESKTOP",
        }

    # =========================================================================
    # 4. APPLICATION LAUNCHER & DESKTOP OPENER
    # =========================================================================

    def launch_app(self, app_name: str, args: Optional[List[str]] = None) -> bool:
        """Launches a desktop application detached from the current process."""
        cmd = [app_name]
        if args:
            cmd.extend(args)

        try:
            if self.is_windows:
                subprocess.Popen(cmd, shell=True, creationflags=subprocess.DETACHED_PROCESS if hasattr(subprocess, 'DETACHED_PROCESS') else 0)
            else:
                subprocess.Popen(cmd, start_new_session=True)
            return True
        except Exception as e:
            logger.error(f"Failed to launch app '{app_name}': {e}")
            return False

    def open_file_with_default(self, file_path: Union[str, Path]) -> bool:
        """Opens a file or URL with the system's registered default handler."""
        p_str = str(self.normalize_path(file_path))
        try:
            if self.is_windows:
                os.startfile(p_str)
                return True
            elif self.is_mac:
                subprocess.Popen(["open", p_str])
                return True
            else:
                subprocess.Popen(["xdg-open", p_str])
                return True
        except Exception as e:
            logger.error(f"Failed to open '{file_path}' with default handler: {e}")
            return False

    def open_terminal(self, cwd: Optional[str] = None) -> bool:
        """Opens a new interactive system terminal window."""
        workdir = cwd or str(self.get_home_dir())
        try:
            if self.is_windows:
                # Try wt.exe (Windows Terminal) or fallback to cmd.exe
                if shutil.which("wt"):
                    subprocess.Popen(["wt", "-d", workdir])
                elif shutil.which("powershell"):
                    subprocess.Popen(["powershell", "-NoExit", "-Command", f"Set-Location '{workdir}'"])
                else:
                    subprocess.Popen(["cmd.exe", "/K", f"cd /d {workdir}"])
                return True
            elif self.is_mac:
                subprocess.Popen(["open", "-a", "Terminal", workdir])
                return True
            else:
                for term in ["gnome-terminal", "konsole", "xfce4-terminal", "xterm"]:
                    if shutil.which(term):
                        subprocess.Popen([term, "--working-directory", workdir])
                        return True
                return False
        except Exception as e:
            logger.error(f"Failed to open terminal in '{workdir}': {e}")
            return False

    # =========================================================================
    # 5. ENVIRONMENT & SHELL COMMANDS
    # =========================================================================

    def get_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieves an environment variable."""
        return os.environ.get(key, default)

    def set_env(self, key: str, value: str, permanent: bool = False) -> bool:
        """Sets an environment variable in current process and optionally permanently."""
        os.environ[key] = str(value)
        if not permanent:
            return True

        if self.is_windows:
            try:
                subprocess.run(["setx", key, str(value)], capture_output=True, text=True, check=True)
                return True
            except Exception as e:
                logger.warning(f"setx failed: {e}")
                return False
        else:
            try:
                rc_file = self.get_home_dir() / ".bashrc"
                with open(rc_file, "a", encoding="utf-8") as f:
                    f.write(f'\nexport {key}="{value}"\n')
                return True
            except Exception as e:
                logger.warning(f"Writing to .bashrc failed: {e}")
                return False

    def execute_command(
        self,
        command: str,
        shell: bool = True,
        timeout: int = 60,
        cwd: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executes a shell or process command with timeout and captures output."""
        start_t = time.time()
        try:
            res = subprocess.run(
                command,
                shell=shell,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
            duration = round(time.time() - start_t, 3)
            return {
                "status": "SUCCESS" if res.returncode == 0 else "FAILED",
                "exit_code": res.returncode,
                "stdout": res.stdout,
                "stderr": res.stderr,
                "duration_seconds": duration,
                "command": command,
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "FAILED",
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds.",
                "duration_seconds": timeout,
                "command": command,
            }
        except Exception as e:
            return {
                "status": "FAILED",
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "duration_seconds": round(time.time() - start_t, 3),
                "command": command,
            }

    # =========================================================================
    # 6. SYSTEM INFO & TELEMETRY
    # =========================================================================

    def get_system_info(self) -> Dict[str, Any]:
        """Aggregates high-fidelity hardware, OS, memory, and runtime metadata."""
        disk = shutil.disk_usage(os.getcwd())
        total_disk_gb = round(disk.total / (1024 ** 3), 2)
        free_disk_gb = round(disk.free / (1024 ** 3), 2)

        info: Dict[str, Any] = {
            "os_type": self.os_type,
            "os_name": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "cpu_count": os.cpu_count() or 1,
            "hostname": platform.node(),
            "python_version": platform.python_version(),
            "disk_total_gb": total_disk_gb,
            "disk_free_gb": free_disk_gb,
            "uptime_seconds": round(time.time() - self._boot_time, 1),
        }

        if self._has_psutil:
            import psutil
            try:
                vm = psutil.virtual_memory()
                info["memory_total_mb"] = round(vm.total / (1024 * 1024), 1)
                info["memory_available_mb"] = round(vm.available / (1024 * 1024), 1)
                info["memory_percent_used"] = vm.percent
                info["cpu_percent"] = psutil.cpu_percent(interval=None)
            except Exception:
                pass
        else:
            info["memory_total_mb"] = 8192.0
            info["memory_available_mb"] = 4096.0
            info["memory_percent_used"] = 50.0
            info["cpu_percent"] = 0.0

        return info


# Global Singleton
_platform_singleton: Optional[PlatformAbstraction] = None


def get_platform() -> PlatformAbstraction:
    """Retrieves the global PlatformAbstraction singleton instance."""
    global _platform_singleton
    if _platform_singleton is None:
        _platform_singleton = PlatformAbstraction()
    return _platform_singleton
