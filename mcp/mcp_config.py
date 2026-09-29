"""
Configuration loader and schema models for Model Context Protocol (MCP) servers.
Supports STDIO, HTTP, and SSE transports with environment variable expansion (${VAR}).
"""

import os
import re
import json
import logging
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional

logger = logging.getLogger("orvix.mcp.config")


class MCPServerType(str, Enum):
    STDIO = "stdio"
    HTTP = "http"
    SSE = "sse"


@dataclass
class MCPServerConfig:
    name: str
    server_type: MCPServerType = MCPServerType.STDIO
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    url: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    timeout_sec: float = 30.0
    enabled: bool = True
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["server_type"] = self.server_type.value
        return d


def expand_env_vars(val: Any) -> Any:
    """
    Recursively expands ${VAR} and ${VAR:-default} syntax against os.environ.
    """
    if isinstance(val, str):
        def _repl(match):
            var_name = match.group(1)
            default_val = match.group(2) if match.group(2) is not None else (match.group(3) or "")
            return os.environ.get(var_name, default_val)

        # Matches ${VAR}, ${VAR:-default}, ${VAR:default}
        pattern = re.compile(r"\$\{([A-Za-z0-9_]+)(?::-(.*?)|:(.*?))?\}")
        return pattern.sub(_repl, val)
    elif isinstance(val, list):
        return [expand_env_vars(item) for item in val]
    elif isinstance(val, dict):
        return {k: expand_env_vars(v) for k, v in val.items()}
    return val


def load_mcp_config(config_path: Optional[Path] = None) -> Dict[str, MCPServerConfig]:
    """
    Loads MCP server configurations from config/mcp_servers.json.
    Returns a dictionary mapping server name to MCPServerConfig.
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "mcp_servers.json"

    if not config_path.exists():
        logger.warning(f"MCP configuration file not found at {config_path}. Using built-in defaults.")
        return get_default_configs()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        expanded_data = expand_env_vars(raw_data)
        servers_dict = expanded_data.get("mcpServers", expanded_data)

        configs: Dict[str, MCPServerConfig] = {}
        for s_name, s_data in servers_dict.items():
            if not isinstance(s_data, dict):
                continue

            # Determine transport type
            if "url" in s_data or s_data.get("server_type") in ("http", "sse"):
                s_type = MCPServerType.HTTP if s_data.get("server_type") != "sse" else MCPServerType.SSE
            else:
                s_type = MCPServerType.STDIO

            cfg = MCPServerConfig(
                name=s_name,
                server_type=s_type,
                command=s_data.get("command"),
                args=s_data.get("args", []),
                env=s_data.get("env", {}),
                url=s_data.get("url"),
                headers=s_data.get("headers", {}),
                timeout_sec=float(s_data.get("timeout_sec", 30.0)),
                enabled=bool(s_data.get("enabled", True)),
                description=s_data.get("description", f"MCP Server: {s_name}")
            )
            configs[s_name] = cfg

        return configs
    except Exception as e:
        logger.error(f"Error loading MCP configuration from {config_path}: {e}")
        return get_default_configs()


def get_default_configs() -> Dict[str, MCPServerConfig]:
    """Provides standard fallback configurations for sqlite, filesystem, and fetch."""
    return {
        "sqlite": MCPServerConfig(
            name="sqlite",
            server_type=MCPServerType.STDIO,
            command="npx",
            args=["-y", "@modelcontextprotocol/server-sqlite", "knowledge/agent_memory.db"],
            description="SQLite database query and inspection server"
        ),
        "filesystem": MCPServerConfig(
            name="filesystem",
            server_type=MCPServerType.STDIO,
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", os.path.expanduser("~/Documents")],
            description="Secure local filesystem browser and reader"
        ),
        "fetch": MCPServerConfig(
            name="fetch",
            server_type=MCPServerType.STDIO,
            command="npx",
            args=["-y", "@modelcontextprotocol/server-fetch"],
            description="Real-time web URL content retrieval and conversion"
        )
    }
