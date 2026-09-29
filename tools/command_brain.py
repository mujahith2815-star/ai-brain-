"""
Unified Command Brain for 3-Layer Command Intelligence.
Provides the agent with a single, intelligent query interface capable of
resolving any command through a cascade across:
  Layer 3: Learned Patterns (fastest, user-specific workflows)
  Layer 1: Core Catalog (~520 high-value offline commands)
  Layer 2: Discovered Cache (2,000+ OS binaries, packages, and cmdlets)
  Layer 2 Live: Real-time OS lookup (Get-Command / where)
"""

import os
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional

from knowledge.commands.core.load_core import (
    load_core_commands,
    get_core_command,
    search_core_commands,
)
from tools.command_discovery import CommandDiscovery
from tools.command_cache import get_cached, count_cached, search_cached
from knowledge.commands.command_patterns import (
    get_all_patterns,
    get_similar_patterns,
    suggest_chain,
)


class CommandBrain:
    """
    Unified 3-layer command intelligence brain for Orvix Sphere.
    """

    def __init__(self, vector_store: Any = None):
        self.vector_store = vector_store
        self.discovery = CommandDiscovery()
        # Ensure core catalog is primed
        self.core = load_core_commands()

    def find(self, task_description: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Cascade search across all 3 layers:
        1. Check command_patterns (learned, fastest)
        2. Check core commands (baked-in, high-value)
        3. Check discovered commands cache (SQLite)
        4. Query live OS if still not found
        5. Fallback with recommendations
        """
        task_clean = task_description.strip()
        if not task_clean:
            return {"status": "EMPTY", "results": [], "layer": None}

        # -------------------------------------------------------------
        # Step 1: Check Layer 3 (Learned Patterns)
        # -------------------------------------------------------------
        patterns = get_similar_patterns(task_clean, limit=max_results, vector_store=self.vector_store)
        if patterns:
            formatted = []
            for p in patterns:
                formatted.append({
                    "name": p["pattern_name"],
                    "syntax": " && ".join(p.get("command_chain", [])),
                    "description": p.get("description", ""),
                    "source": "layer3_learned",
                    "shell": p.get("shell", "powershell"),
                    "confidence": 0.95,
                })
            return {
                "status": "FOUND",
                "layer": "layer3_learned",
                "results": formatted[:max_results]
            }

        # -------------------------------------------------------------
        # Step 2: Check Layer 1 (Core Catalog)
        # -------------------------------------------------------------
        # Check exact name match first
        exact_core = get_core_command(task_clean)
        if exact_core:
            return {
                "status": "FOUND",
                "layer": "layer1_core",
                "results": [{
                    "name": exact_core.get("name"),
                    "syntax": exact_core.get("syntax"),
                    "description": exact_core.get("description"),
                    "source": "layer1_core",
                    "shell": exact_core.get("shell"),
                    "category": exact_core.get("category"),
                    "examples": exact_core.get("examples", []),
                    "confidence": 0.90,
                }]
            }

        core_matches = search_core_commands(task_clean, limit=max_results)
        if core_matches:
            formatted = []
            for c in core_matches:
                formatted.append({
                    "name": c.get("name"),
                    "syntax": c.get("syntax"),
                    "description": c.get("description"),
                    "source": "layer1_core",
                    "shell": c.get("shell"),
                    "category": c.get("category"),
                    "examples": c.get("examples", []),
                    "confidence": 0.85,
                })
            return {
                "status": "FOUND",
                "layer": "layer1_core",
                "results": formatted[:max_results]
            }

        # -------------------------------------------------------------
        # Step 3: Check Layer 2 (Discovered SQLite Cache)
        # -------------------------------------------------------------
        cached_matches = search_cached(task_clean, limit=max_results)
        if cached_matches:
            formatted = []
            for d in cached_matches:
                formatted.append({
                    "name": d.get("name"),
                    "syntax": d.get("path") or d.get("name"),
                    "description": (d.get("help_text") or f"Discovered system utility from {d.get('source')}")[:150],
                    "source": "layer2_discovered",
                    "shell": d.get("shell"),
                    "origin_source": d.get("source"),
                    "confidence": 0.70,
                })
            return {
                "status": "FOUND",
                "layer": "layer2_discovered",
                "results": formatted[:max_results]
            }

        # -------------------------------------------------------------
        # Step 4: Query Live OS (Live Discovery)
        # -------------------------------------------------------------
        live_res = self._query_live_os(task_clean)
        if live_res:
            return {
                "status": "FOUND",
                "layer": "layer2_live",
                "results": live_res[:max_results]
            }

        # -------------------------------------------------------------
        # Step 5: Fallback
        # -------------------------------------------------------------
        return {
            "status": "NOT_FOUND",
            "layer": None,
            "results": [],
            "message": f"No pre-indexed, discovered, or live command found matching '{task_clean}'."
        }

    def _query_live_os(self, query: str) -> List[Dict[str, Any]]:
        """Queries the OS directly via Get-Command or where."""
        results = []
        q_clean = query.strip().split()[0]

        # Try PowerShell Get-Command
        if self.discovery.is_windows:
            try:
                cmd = f"Get-Command *{q_clean}* -ErrorAction SilentlyContinue | Select-Object -First 3 Name, Source, CommandType | ConvertTo-Json"
                res = subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    encoding="utf-8",
                    errors="replace"
                )
                if res.returncode == 0 and res.stdout.strip():
                    import json
                    data = json.loads(res.stdout)
                    if isinstance(data, dict):
                        data = [data]
                    for item in data:
                        results.append({
                            "name": item.get("Name"),
                            "syntax": item.get("Name"),
                            "description": f"Live OS command found in {item.get('Source')}",
                            "source": "layer2_live",
                            "shell": "powershell",
                            "confidence": 0.60,
                        })
            except Exception:
                pass

        # Try which / where
        if not results:
            which_path = shutil.which(q_clean)
            if which_path:
                results.append({
                    "name": q_clean,
                    "syntax": which_path,
                    "description": f"Live binary found on PATH: {which_path}",
                    "source": "layer2_live",
                    "shell": "cmd" if self.discovery.is_windows else "bash",
                    "confidence": 0.60,
                })

        return results

    def explain(self, command: str) -> Dict[str, Any]:
        """
        Gets comprehensive documentation for a command.
        Checks Core Catalog first (for structured examples); falls back to Live HelpReader.
        """
        cmd_name = command.strip().split()[0] if command.strip() else ""
        if not cmd_name:
            return {"error": "Empty command provided"}

        # 1. Check Core catalog
        core_cmd = get_core_command(cmd_name)
        if core_cmd:
            return {
                "command": core_cmd.get("name"),
                "source": "layer1_core",
                "shell": core_cmd.get("shell"),
                "category": core_cmd.get("category"),
                "description": core_cmd.get("description"),
                "syntax": core_cmd.get("syntax"),
                "examples": core_cmd.get("examples", []),
                "safety": core_cmd.get("safety"),
                "tags": core_cmd.get("tags", []),
            }

        # 2. Query Live OS Help
        live_help = self.discovery.get_help(cmd_name)
        live_help["source"] = "layer2_live_help"
        return live_help

    def suggest(self, task_description: str) -> List[Dict[str, Any]]:
        """
        Returns top 3 suggested commands for a task description.
        """
        res = self.find(task_description, max_results=3)
        return res.get("results", [])

    def stats(self) -> Dict[str, Any]:
        """
        Returns metric breakdown across all 3 layers:
        Layer 1 (Core): ~520 commands
        Layer 2 (Discovered): 2,000+ cached
        Layer 3 (Learned): count of patterns
        """
        core_count = len(self.core)
        cached_stats = count_cached()
        patterns = get_all_patterns()

        return {
            "layer1_core_commands": core_count,
            "layer2_discovered_total": cached_stats.get("total", 0),
            "layer2_by_source": cached_stats.get("by_source", {}),
            "layer3_learned_patterns": len(patterns),
            "status": "READY"
        }
