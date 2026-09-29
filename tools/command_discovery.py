"""
Live Command Discovery Engine for Layer 2 Command Intelligence.
Dynamically inspects and queries the host operating system to discover
unlimited installed commands, tools, binaries, and package CLI utilities
(PowerShell, CMD/System32, Bash, Python pip, NPM, and Winget).
"""

import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from tools.command_cache import cache_commands_batch, count_cached, search_cached
from tools.help_reader import HelpReader

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DISCOVERED_DIR = os.path.join(PROJECT_ROOT, "knowledge", "commands", "discovered")
os.makedirs(DISCOVERED_DIR, exist_ok=True)


class CommandDiscovery:
    """
    Scans the operating system to dynamically discover all available CLI tools and commands.
    """

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.is_windows = platform.system().lower() == "windows"
        self.help_reader = HelpReader(timeout=timeout)

    def discover_powershell_commands(self) -> List[Dict[str, Any]]:
        """
        Queries Windows PowerShell for installed cmdlets and functions.
        Runs: Get-Command | Select-Object -First 2000 Name, Source, CommandType, Version | ConvertTo-Json
        """
        if not self.is_windows:
            return []

        script = (
            "$ProgressPreference = 'SilentlyContinue'; "
            "Get-Command | Select-Object -First 2500 Name, Source, CommandType, "
            "@{N='Version';E={$_.Version.ToString()}} | "
            "ConvertTo-Json -Compress"
        )
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding="utf-8",
                errors="replace"
            )
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                if isinstance(data, dict):
                    data = [data]
                results = []
                for item in data:
                    name = item.get("Name")
                    if name:
                        results.append({
                            "name": name,
                            "shell": "powershell",
                            "source": "powershell",
                            "type": str(item.get("CommandType", "Cmdlet")),
                            "module": str(item.get("Source", "")),
                            "version": str(item.get("Version", "")),
                        })
                return results
        except Exception as e:
            print(f"[CommandDiscovery] PowerShell discovery notice: {e}")
        return []

    def discover_cmd_commands(self) -> List[Dict[str, Any]]:
        """
        Discovers standard system executable binaries in System32 / Windows path.
        """
        results = []
        seen = set()
        system32 = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32")
        if os.path.exists(system32):
            try:
                for entry in os.scandir(system32):
                    if entry.is_file() and entry.name.lower().endswith(".exe"):
                        base = entry.name[:-4]
                        if base.lower() not in seen:
                            seen.add(base.lower())
                            results.append({
                                "name": base,
                                "shell": "cmd",
                                "source": "cmd",
                                "path": entry.path,
                            })
                            if len(results) >= 1000:
                                break
            except Exception as e:
                print(f"[CommandDiscovery] System32 scan notice: {e}")
        return results

    def discover_bash_commands(self) -> List[Dict[str, Any]]:
        """
        Discovers Bash builtins and executables using compgen -c on Linux/WSL.
        """
        results = []
        if not self.is_windows:
            try:
                res = subprocess.run(
                    ["bash", "-c", "compgen -c | sort -u | head -n 2000"],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    encoding="utf-8",
                    errors="replace"
                )
                if res.returncode == 0:
                    for line in res.stdout.splitlines():
                        name = line.strip()
                        if name:
                            results.append({
                                "name": name,
                                "shell": "bash",
                                "source": "bash"
                            })
            except Exception:
                pass
        else:
            # Try WSL if installed
            try:
                res = subprocess.run(
                    ["wsl", "bash", "-c", "compgen -c | sort -u | head -n 1000"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    encoding="utf-8",
                    errors="replace"
                )
                if res.returncode == 0 and res.stdout.strip():
                    for line in res.stdout.splitlines():
                        name = line.strip()
                        if name:
                            results.append({
                                "name": name,
                                "shell": "bash",
                                "source": "bash"
                            })
            except Exception:
                pass
        return results

    def discover_python_packages(self) -> List[Dict[str, Any]]:
        """
        Discovers installed Python packages via pip list --format=json.
        """
        python_exe = sys.executable
        try:
            res = subprocess.run(
                [python_exe, "-m", "pip", "list", "--format=json"],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding="utf-8",
                errors="replace"
            )
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                results = []
                for pkg in data:
                    name = pkg.get("name")
                    if name:
                        results.append({
                            "name": name,
                            "shell": "python",
                            "source": "pip",
                            "version": pkg.get("version", ""),
                        })
                return results
        except Exception as e:
            print(f"[CommandDiscovery] Python pip list notice: {e}")
        return []

    def discover_npm_globals(self) -> List[Dict[str, Any]]:
        """
        Discovers globally installed NPM packages via npm list -g --depth=0 --json.
        """
        try:
            cmd = "npm.cmd" if self.is_windows else "npm"
            res = subprocess.run(
                [cmd, "list", "-g", "--depth=0", "--json"],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding="utf-8",
                errors="replace"
            )
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                deps = data.get("dependencies", {})
                results = []
                for name, info in deps.items():
                    results.append({
                        "name": name,
                        "shell": "node",
                        "source": "npm",
                        "version": info.get("version", "") if isinstance(info, dict) else "",
                    })
                return results
        except Exception:
            pass
        return []

    def discover_winget_packages(self) -> List[Dict[str, Any]]:
        """
        Discovers installed Windows packages via winget list.
        """
        if not self.is_windows:
            return []
        try:
            res = subprocess.run(
                ["winget", "list", "-n", "100"],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding="utf-8",
                errors="replace"
            )
            if res.returncode == 0 and res.stdout.strip():
                lines = res.stdout.splitlines()
                results = []
                start_parsing = False
                for line in lines:
                    if "---" in line:
                        start_parsing = True
                        continue
                    if start_parsing and line.strip():
                        parts = line.split()
                        if parts:
                            results.append({
                                "name": parts[0],
                                "shell": "windows",
                                "source": "winget",
                                "id": parts[1] if len(parts) > 1 else "",
                                "version": parts[2] if len(parts) > 2 else "",
                            })
                return results
        except Exception:
            pass
        return []

    def discover_all(self, save_snapshot: bool = True) -> Dict[str, Any]:
        """
        Aggregates all discovered commands from all sources, saves a dated snapshot,
        and caches them into SQLite discovered_commands.
        """
        by_source: Dict[str, int] = {}
        all_commands: List[Dict[str, Any]] = []

        # 1. PowerShell
        ps_cmds = self.discover_powershell_commands()
        by_source["powershell"] = len(ps_cmds)
        all_commands.extend(ps_cmds)

        # 2. CMD / System32
        cmd_cmds = self.discover_cmd_commands()
        by_source["cmd"] = len(cmd_cmds)
        all_commands.extend(cmd_cmds)

        # 3. Bash / WSL
        bash_cmds = self.discover_bash_commands()
        by_source["bash"] = len(bash_cmds)
        all_commands.extend(bash_cmds)

        # 4. Python pip
        pip_cmds = self.discover_python_packages()
        by_source["pip"] = len(pip_cmds)
        all_commands.extend(pip_cmds)

        # 5. NPM
        npm_cmds = self.discover_npm_globals()
        by_source["npm"] = len(npm_cmds)
        all_commands.extend(npm_cmds)

        # 6. Winget
        winget_cmds = self.discover_winget_packages()
        by_source["winget"] = len(winget_cmds)
        all_commands.extend(winget_cmds)

        total = len(all_commands)

        # Save dated JSON snapshot
        if save_snapshot:
            date_str = datetime.now().strftime("%Y%m%d")
            snapshot_file = os.path.join(DISCOVERED_DIR, f"{date_str}.json")
            try:
                with open(snapshot_file, "w", encoding="utf-8") as f:
                    json.dump(all_commands, f, indent=2)
            except Exception as e:
                print(f"[CommandDiscovery] Snapshot write notice: {e}")

        # Batch insert into SQLite cache
        cached_count = cache_commands_batch(all_commands)

        return {
            "total": total,
            "cached_count": cached_count,
            "by_source": by_source,
        }

    def search_discovered(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Searches SQLite cache of discovered commands."""
        return search_cached(keyword, limit=limit)

    def get_help(self, command: str, shell: str = "auto") -> Dict[str, Any]:
        """Fetches live OS help and returns structured parsed documentation."""
        raw_help = self.help_reader.get_help_text(command, shell=shell)
        parsed = self.help_reader.parse_help(raw_help)
        parsed["command"] = command
        parsed["raw_help"] = raw_help
        return parsed
