"""
Model Context Protocol (MCP) Integration Package for Orvix Sphere.
Enables dynamic tool discovery and execution via external MCP servers.
"""

from mcp.mcp_config import MCPServerConfig, MCPServerType, load_mcp_config
from mcp.mcp_client import MCPClient
from mcp.mcp_manager import MCPManager
from mcp.mcp_tool_adapter import MCPToolAdapter

__all__ = [
    "MCPServerConfig",
    "MCPServerType",
    "load_mcp_config",
    "MCPClient",
    "MCPManager",
    "MCPToolAdapter",
]
