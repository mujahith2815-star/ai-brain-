"""
MCP Manager (Singleton) for Orvix Sphere.
Orchestrates multi-server lifecycle, tool aggregation, automatic retry,
and Node.js/npx environment detection.
"""

import shutil
import logging
import threading
from typing import Dict, Any, List, Optional
from pathlib import Path

from mcp.mcp_config import MCPServerConfig, load_mcp_config
from mcp.mcp_client import MCPClient

logger = logging.getLogger("orvix.mcp.manager")


class MCPManager:
    """
    Central manager for all external MCP servers.
    Singleton pattern ensures unified access across the cognitive agent.
    """

    _instance: Optional["MCPManager"] = None
    _lock = threading.RLock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MCPManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, config_path: Optional[Path] = None):
        if getattr(self, "_initialized", False):
            return

        self.config_path = config_path
        self.configs: Dict[str, MCPServerConfig] = load_mcp_config(config_path)
        self.clients: Dict[str, MCPClient] = {}
        self.retry_counts: Dict[str, int] = {}
        self.max_retries = 3
        self.node_available = self._detect_node_environment()
        self._init_clients()
        self._initialized = True

    def _detect_node_environment(self) -> bool:
        """Detects whether Node.js and npx are installed on the host."""
        import os
        node_dir = Path(r"C:\Program Files\nodejs")
        if node_dir.exists() and str(node_dir) not in os.environ.get("PATH", ""):
            os.environ["PATH"] = str(node_dir) + os.pathsep + os.environ.get("PATH", "")

        has_node = bool(shutil.which("node") or shutil.which("node.exe") or (node_dir / "node.exe").exists())
        has_npx = bool(shutil.which("npx") or shutil.which("npx.cmd") or shutil.which("npx.exe") or (node_dir / "npx.cmd").exists())
        available = has_node or has_npx
        if not available:
            logger.warning(
                "[MCPManager] Node.js/npx not detected on host system. "
                "External STDIO MCP servers will operate in offline/fallback mode. "
                "Install Node.js (v18+) to enable npx MCP servers."
            )
        self.mcp_available = available
        return available

    def _init_clients(self):
        for name, cfg in self.configs.items():
            self.clients[name] = MCPClient(cfg)
            self.retry_counts[name] = 0

    def start_all(self) -> Dict[str, bool]:
        """Starts all enabled MCP servers."""
        results = {}
        for name, client in self.clients.items():
            if client.config.enabled:
                ok = client.start()
                results[name] = ok
            else:
                results[name] = False
        return results

    def start_server(self, name: str) -> bool:
        """Starts a specific server by name."""
        if name not in self.clients:
            logger.error(f"[MCPManager] Server '{name}' not found in configuration.")
            return False
        return self.clients[name].start()

    def stop_server(self, name: str):
        """Stops a specific server by name."""
        if name in self.clients:
            self.clients[name].stop()

    def shutdown(self):
        """Stops all active MCP servers."""
        for client in self.clients.values():
            client.stop()

    def restart_all(self) -> Dict[str, bool]:
        """Restarts all servers and re-discovers tools."""
        self.shutdown()
        self.configs = load_mcp_config(self.config_path)
        self._init_clients()
        return self.start_all()

    def get_all_tools(self) -> Dict[str, List[Dict[str, Any]]]:
        """Aggregates tool schemas from all connected MCP servers."""
        aggregated: Dict[str, List[Dict[str, Any]]] = {}
        for name, client in self.clients.items():
            if client.is_connected:
                aggregated[name] = client.tools
            else:
                aggregated[name] = []
        return aggregated

    def call_tool(self, server_name: str, tool_name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Routes a tool call to the specified server with automatic retry logic (max 3 retries).
        """
        if server_name not in self.clients:
            return {
                "status": "FAILED",
                "error": f"MCP server '{server_name}' is not registered."
            }

        client = self.clients[server_name]
        retries = 0

        while retries <= self.max_retries:
            res = client.call_tool(tool_name, args)
            if res.get("status") == "SUCCESS":
                self.retry_counts[server_name] = 0
                return res

            # Auto-restart on crash if error suggests process death
            retries += 1
            if retries <= self.max_retries:
                logger.info(f"[MCPManager] Tool call '{tool_name}' on '{server_name}' failed. Retrying ({retries}/{self.max_retries})...")
                client.stop()
                client.start()

        return {
            "status": "FAILED",
            "server": server_name,
            "tool": tool_name,
            "error": f"Tool call failed after {self.max_retries} retries."
        }

    def get_status(self) -> Dict[str, Any]:
        """Returns comprehensive health telemetry for all servers."""
        status_report = {
            "node_available": self.node_available,
            "total_servers": len(self.clients),
            "connected_servers": sum(1 for c in self.clients.values() if c.is_connected),
            "servers": {}
        }
        for name, client in self.clients.items():
            status_report["servers"][name] = {
                "connected": client.is_connected,
                "type": client.config.server_type.value,
                "enabled": client.config.enabled,
                "tools_count": len(client.tools),
                "tools": [t.get("name") for t in client.tools if isinstance(t, dict)]
            }
        return status_report
