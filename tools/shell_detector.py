"""
Shell and OS detector for Orvix Universal Control.
Detects available shells on the host machine, default shell, and infers
appropriate shell interpreter from command syntax.
"""

import os
import platform
import shutil
import subprocess
from typing import Any, Dict, List, Optional


class ShellDetector:
    """Detects operating system environment, available shells, and formats execution commands."""

    _cached_shells: Optional[List[Dict[str, Any]]] = None

    @staticmethod
    def get_os() -> str:
        """Returns normalized OS name: 'windows', 'linux', or 'darwin'."""
        system = platform.system().lower()
        if "windows" in system:
            return "windows"
        elif "linux" in system:
            return "linux"
        elif "darwin" in system:
            return "darwin"
        return system

    @classmethod
    def get_available_shells(cls, refresh: bool = False) -> List[Dict[str, Any]]:
        """Scans the system for installed shells."""
        if cls._cached_shells is not None and not refresh:
            return cls._cached_shells

        shells: List[Dict[str, Any]] = []
        is_win = cls.get_os() == "windows"

        if is_win:
            # Check PowerShell Core (pwsh)
            pwsh_path = shutil.which("pwsh")
            if pwsh_path:
                shells.append({"name": "pwsh", "path": pwsh_path, "type": "powershell", "version": "core"})
            
            # Check Windows PowerShell (powershell)
            ps_path = shutil.which("powershell") or shutil.which("powershell.exe")
            if ps_path:
                shells.append({"name": "powershell", "path": ps_path, "type": "powershell", "version": "desktop"})

            # Check CMD
            cmd_path = shutil.which("cmd") or shutil.which("cmd.exe")
            if cmd_path:
                shells.append({"name": "cmd", "path": cmd_path, "type": "cmd", "version": "legacy"})

            # Check Git Bash
            git_bash_candidates = [
                r"C:\Program Files\Git\bin\bash.exe",
                r"C:\Program Files (x86)\Git\bin\bash.exe",
                shutil.which("bash.exe"),
            ]
            for c in git_bash_candidates:
                if c and os.path.exists(c):
                    shells.append({"name": "git-bash", "path": c, "type": "bash", "version": "git"})
                    break

            # Check WSL
            wsl_path = shutil.which("wsl") or shutil.which("wsl.exe")
            if wsl_path:
                shells.append({"name": "wsl", "path": wsl_path, "type": "wsl", "version": "wsl"})

        else:
            for sh_name in ["bash", "zsh", "sh", "dash", "fish"]:
                path = shutil.which(sh_name)
                if path:
                    shells.append({"name": sh_name, "path": path, "type": sh_name, "version": "unix"})

        cls._cached_shells = shells
        return shells

    @classmethod
    def get_default_shell(cls) -> str:
        """Determines best default shell for the current host environment."""
        shells = cls.get_available_shells()
        is_win = cls.get_os() == "windows"

        if is_win:
            for s in shells:
                if s["name"] in ("pwsh", "powershell"):
                    return s["path"]
            cmd = shutil.which("cmd.exe")
            return cmd if cmd else "powershell.exe"
        else:
            bash = shutil.which("bash")
            if bash:
                return bash
            sh = shutil.which("sh")
            return sh if sh else "/bin/sh"

    @classmethod
    def detect_shell_for_command(cls, command: str) -> str:
        """
        Analyzes command keywords to guess whether it is intended for PowerShell, CMD, or Bash.
        """
        cmd_lower = command.lower().strip()
        
        # PowerShell signatures
        ps_patterns = [
            "get-", "set-", "new-", "remove-", "start-", "stop-", "restart-",
            "invoke-", "test-", "where-object", "select-object", "format-table",
            "format-list", "measure-object", "$env:", "out-null", "| %", "| ?",
        ]
        if any(p in cmd_lower for p in ps_patterns):
            return "powershell"

        # Linux/Bash signatures
        bash_patterns = [
            "sudo ", "apt ", "apt-get ", "systemctl ", "journalctl ", "grep ",
            "awk ", "sed ", "chmod ", "chown ", "uname ", "df -h", "free -h",
            "ps aux", "cat /etc/", "export ", "source ",
        ]
        if any(p in cmd_lower for p in bash_patterns):
            return "bash"

        # CMD signatures
        cmd_patterns = [
            "dir /", "del /", "copy /", "xcopy ", "robocopy ", "attrib ", "echo %",
        ]
        if any(p in cmd_lower for p in cmd_patterns):
            return "cmd"

        return "default"

    @classmethod
    def build_execution_args(cls, command: str, shell_override: Optional[str] = None) -> List[str]:
        """
        Builds the argument list for subprocess.Popen based on shell selection.
        """
        is_win = cls.get_os() == "windows"
        chosen_shell = shell_override or cls.detect_shell_for_command(command)

        if is_win:
            if chosen_shell in ("cmd", "batch"):
                return ["cmd.exe", "/c", command]
            elif chosen_shell in ("bash", "git-bash"):
                # Try finding git-bash or wsl
                for s in cls.get_available_shells():
                    if s["type"] == "bash":
                        return [s["path"], "-c", command]
                # Fallback to wsl or powershell
                wsl = shutil.which("wsl.exe")
                if wsl:
                    return [wsl, "bash", "-c", command]
            # Default to PowerShell on Windows
            return ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", command]
        else:
            return ["/bin/bash", "-c", command]


get_default_shell = ShellDetector.get_default_shell
