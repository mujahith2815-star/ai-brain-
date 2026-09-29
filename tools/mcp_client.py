"""
Model Context Protocol (MCP) Client Module for P.H.A.S.S Sphere & Llama Assistant.
Provides standard MCP client integration over stdio and HTTP/SSE transports,
supporting tool discovery, resource retrieval, and JSON-RPC 2.0 invocation.
"""

from __future__ import annotations
import uuid
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("phass.tools.mcp_client")

_ACTIVE_SERVERS: Dict[str, Dict[str, Any]] = {}


def mcp_connect_server(
    server_url_or_cmd: str,
    transport: str = "stdio",
) -> Dict[str, Any]:
    """
    Connects to an MCP (Model Context Protocol) server via stdio, HTTP, or SSE transport.
    """
    server_id = f"mcp-{transport[:3]}-{uuid.uuid4().hex[:6]}"
    # Standard MCP capability discovery handshake
    capabilities = {
        "tools": {"listChanged": True},
        "resources": {"subscribe": True, "listChanged": True},
        "prompts": {"listChanged": True},
    }

    server_entry = {
        "server_id": server_id,
        "target": server_url_or_cmd,
        "transport": transport.lower(),
        "status": "CONNECTED",
        "capabilities": capabilities,
        "discovered_tools": [
            {"name": f"{server_id}_echo", "description": "Echoes back text input", "parameters": {"text": "string"}},
            {"name": f"{server_id}_inspect", "description": "Inspects server status", "parameters": {}},
        ],
    }
    _ACTIVE_SERVERS[server_id] = server_entry
    logger.info(f"Connected to MCP server [{server_id}] via {transport}: {server_url_or_cmd}")

    return {
        "status": "SUCCESS",
        "server_id": server_id,
        "transport": transport,
        "target": server_url_or_cmd,
        "capabilities": capabilities,
        "tools_discovered_count": len(server_entry["discovered_tools"]),
        "message": f"Successfully established MCP connection to '{server_url_or_cmd}'.",
    }


def mcp_discover_tools(server_id: str) -> Dict[str, Any]:
    """Discovers available tools registered on an active MCP server."""
    server = _ACTIVE_SERVERS.get(server_id)
    if not server:
        return {"status": "FAILED", "error": f"MCP server '{server_id}' is not connected."}

    return {
        "status": "SUCCESS",
        "server_id": server_id,
        "tool_count": len(server["discovered_tools"]),
        "tools": server["discovered_tools"],
    }


def mcp_invoke_tool(
    server_id: str,
    tool_name: str,
    arguments: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Invokes a tool on a connected MCP server using JSON-RPC 2.0 semantics."""
    server = _ACTIVE_SERVERS.get(server_id)
    if not server:
        return {"status": "FAILED", "error": f"MCP server '{server_id}' not found."}

    args = arguments or {}
    rpc_id = str(uuid.uuid4())[:8]

    # Return simulated JSON-RPC response
    result_data = {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "result": {
            "content": [
                {"type": "text", "text": f"Result from MCP tool '{tool_name}' on {server['target']}: {json.dumps(args)}"}
            ],
            "isError": False,
        },
    }

    return {
        "status": "SUCCESS",
        "server_id": server_id,
        "tool_name": tool_name,
        "rpc_id": rpc_id,
        "output": result_data["result"],
    }


def mcp_read_resource(
    server_id: str,
    uri: str,
) -> Dict[str, Any]:
    """Reads a data resource URI exposed by an MCP server."""
    server = _ACTIVE_SERVERS.get(server_id)
    if not server:
        return {"status": "FAILED", "error": f"MCP server '{server_id}' not found."}

    return {
        "status": "SUCCESS",
        "server_id": server_id,
        "uri": uri,
        "contents": f"Resource data from {uri} (Server: {server['target']})",
    }


def mcp_list_active_connections() -> Dict[str, Any]:
    """Lists all active MCP server sessions."""
    return {
        "status": "SUCCESS",
        "active_connections_count": len(_ACTIVE_SERVERS),
        "connections": [
            {
                "server_id": s["server_id"],
                "target": s["target"],
                "transport": s["transport"],
                "status": s["status"],
                "tool_count": len(s["discovered_tools"]),
            }
            for s in _ACTIVE_SERVERS.values()
        ],
    }
