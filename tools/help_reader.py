"""
HelpReader for On-Demand OS Help Querying and Parsing.
Fetches real, authoritative documentation from the underlying operating system
(PowerShell Get-Help, CMD /?, Linux man/--help) and extracts structured syntax,
parameters, examples, and descriptions.
"""

import os
import platform
import re
import subprocess
from typing import Any, Dict, List, Optional

from tools.command_cache import get_cached, update_help_text
from tools.shell_detector import get_default_shell


class HelpReader:
    """
    On-demand reader and parser for live system command help documentation.
    """

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.is_windows = platform.system().lower() == "windows"

    def get_help_text(self, command: str, shell: str = "auto") -> str:
        """
        Executes live OS help utility to fetch full text documentation.
        Checks cache first; if not present, queries OS and updates cache.
        """
        cmd_clean = command.strip().split()[0] if command.strip() else ""
        if not cmd_clean:
            return ""

        # Check cache first
        cached = get_cached(cmd_clean)
        if cached and cached.get("help_text"):
            return cached["help_text"]

        resolved_shell = shell
        if resolved_shell == "auto":
            resolved_shell = "powershell" if self.is_windows else "bash"

        raw_help = ""
        if self.is_windows:
            if resolved_shell in ("powershell", "pwsh"):
                raw_help = self._fetch_powershell_help(cmd_clean)
            else:
                raw_help = self._fetch_cmd_help(cmd_clean)
                if not raw_help:
                    raw_help = self._fetch_powershell_help(cmd_clean)
        else:
            raw_help = self._fetch_linux_help(cmd_clean)

        if raw_help.strip():
            # Update cache asynchronously/inline
            try:
                update_help_text(cmd_clean, raw_help.strip())
            except Exception:
                pass

        return raw_help.strip()

    def _fetch_powershell_help(self, command: str) -> str:
        """Invokes Get-Help in PowerShell."""
        ps_cmd = f"Get-Help {command} -Full -ErrorAction SilentlyContinue | Out-String -Width 120"
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding="utf-8",
                errors="replace"
            )
            out = res.stdout.strip()
            if out and "Get-Help" not in out and "Cannot find" not in out:
                return out
            # Fallback to basic help
            fallback_res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", f"Get-Help {command} | Out-String -Width 120"],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding="utf-8",
                errors="replace"
            )
            return fallback_res.stdout.strip()
        except Exception as e:
            return f"PowerShell help error: {e}"

    def _fetch_cmd_help(self, command: str) -> str:
        """Invokes <cmd> /? in Windows CMD."""
        try:
            res = subprocess.run(
                f"{command} /?",
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding="utf-8",
                errors="replace"
            )
            out = (res.stdout or res.stderr).strip()
            return out
        except Exception as e:
            return f"CMD help error: {e}"

    def _fetch_linux_help(self, command: str) -> str:
        """Invokes man or --help on Linux."""
        try:
            res = subprocess.run(
                ["man", command],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding="utf-8",
                errors="replace"
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass

        try:
            res2 = subprocess.run(
                [command, "--help"],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding="utf-8",
                errors="replace"
            )
            return (res2.stdout or res2.stderr).strip()
        except Exception as e:
            return f"Linux help error: {e}"

    def parse_help(self, help_text: str) -> Dict[str, Any]:
        """
        Parses raw help output into structured dictionary:
        {
            "description": str,
            "syntax": str,
            "parameters": List[str],
            "examples": List[str]
        }
        """
        if not help_text:
            return {
                "description": "",
                "syntax": "",
                "parameters": [],
                "examples": [],
            }

        lines = help_text.splitlines()
        description_lines = []
        syntax_lines = []
        parameters = []
        examples = []

        current_section: Optional[str] = None

        for line in lines:
            line_str = line.strip()
            upper = line_str.upper()

            # Section headers
            if upper in ("NAME", "SYNOPSIS", "SYNTAX", "USAGE"):
                current_section = "syntax"
                continue
            elif upper in ("DESCRIPTION", "DETAILED DESCRIPTION"):
                current_section = "description"
                continue
            elif upper in ("PARAMETERS", "OPTIONS", "FLAGS"):
                current_section = "parameters"
                continue
            elif upper in ("EXAMPLES", "EXAMPLE"):
                current_section = "examples"
                continue
            elif upper in ("REMARKS", "RELATED LINKS"):
                current_section = "other"
                continue

            if current_section == "syntax":
                if line_str:
                    syntax_lines.append(line_str)
            elif current_section == "description":
                if line_str:
                    description_lines.append(line_str)
            elif current_section == "parameters":
                if line_str.startswith("-") or line_str.startswith("/"):
                    parameters.append(line_str)
            elif current_section == "examples":
                if line_str:
                    examples.append(line_str)

        # Fallbacks if sections were not explicitly tagged
        desc = " ".join(description_lines[:5]).strip()
        syn = " ".join(syntax_lines[:3]).strip()

        if not syn:
            for l in lines[:10]:
                if any(k in l.lower() for k in ["syntax:", "usage:", "options:"]):
                    syn = l.strip()
                    break

        if not desc and lines:
            # First non-empty lines often contain brief description
            first_chunk = [l.strip() for l in lines[:5] if l.strip() and not l.strip().startswith("-")]
            desc = " ".join(first_chunk)

        if not parameters:
            for l in lines:
                s = l.strip()
                if (s.startswith("-") or s.startswith("/")) and len(s) > 2 and len(s) < 120:
                    parameters.append(s)

        return {
            "description": desc[:500],
            "syntax": syn[:300],
            "parameters": parameters[:15],
            "examples": examples[:10],
            "raw_length": len(help_text),
        }
