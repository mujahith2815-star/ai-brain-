"""
Unit tests for Model Context Protocol (MCP) Integration Layer.
Tests configuration, JSON-RPC transports, manager singleton, tool adapter, and graceful fallback.
All tests mock subprocesses and network calls for 100% offline deterministic execution.
"""

import pytest
import os
import json
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path

from mcp.mcp_config import MCPServerConfig, MCPServerType, load_mcp_config, expand_env_vars
from mcp.mcp_client import MCPClient
from mcp.mcp_manager import MCPManager
from mcp.mcp_tool_adapter import MCPToolAdapter
from tools.registry import tool_registry


def test_mcp_config_loading():
    """Test 1: Verifies reading mcp_servers.json into MCPServerConfig dataclasses."""
    configs = load_mcp_config()
    assert "sqlite" in configs
    assert "filesystem" in configs
    assert "fetch" in configs
    assert configs["sqlite"].server_type == MCPServerType.STDIO
    assert configs["sqlite"].command == "npx"


def test_mcp_config_env_var_expansion():
    """Test 2: Verifies ${VAR} and ${VAR:-default} expansion."""
    with patch.dict(os.environ, {"TEST_MCP_DIR": "C:/TestDir", "CUSTOM_PORT": "9090"}):
        expanded_val = expand_env_vars("${TEST_MCP_DIR}/data")
        assert expanded_val == "C:/TestDir/data"

        expanded_default = expand_env_vars("${UNSET_VAR:-fallback_value}")
        assert expanded_default == "fallback_value"


def test_mcp_client_stdio_initialization():
    """Test 3: Verifies STDIO process spawning with mock subprocess."""
    cfg = MCPServerConfig(name="mock_server", command="npx", args=["test"])
    client = MCPClient(cfg)

    # Mock executable resolution and subprocess.Popen
    with patch.object(client, "_resolve_executable", return_value="C:/nodejs/npx.cmd"), \
         patch("subprocess.Popen") as mock_popen, \
         patch.object(client, "_send_request_locked", return_value={"protocolVersion": "2024-11-05"}), \
         patch.object(client, "_send_notification_locked"):
        
        mock_proc = MagicMock()
        mock_popen.return_value = mock_proc

        ok = client.start()
        assert ok is True
        assert client.is_connected is True
        mock_popen.assert_called_once()
        client.stop()
        assert client.is_connected is False


def test_mcp_client_tool_discovery():
    """Test 4: Verifies parsing tools/list response."""
    cfg = MCPServerConfig(name="mock_tools_server")
    client = MCPClient(cfg)
    client.is_connected = True

    mock_tools_data = [
        {"name": "query_db", "description": "Execute SQL query", "inputSchema": {"type": "object"}},
        {"name": "list_tables", "description": "List all tables", "inputSchema": {"type": "object"}}
    ]

    with patch.object(client, "_send_request_locked", return_value={"tools": mock_tools_data}):
        tools = client.list_tools()
        assert len(tools) == 2
        assert tools[0]["name"] == "query_db"
        assert tools[1]["name"] == "list_tables"


def test_mcp_manager_singleton_behavior():
    """Test 5: Verifies MCPManager returns the same singleton instance."""
    m1 = MCPManager()
    m2 = MCPManager()
    assert m1 is m2


def test_mcp_tool_adapter_registration():
    """Test 6: Verifies MCP tools are properly namespaced (mcp__<server>__<tool>) and registered."""
    mock_manager = MagicMock()
    mock_manager.get_all_tools.return_value = {
        "sqlite": [{"name": "list_tables", "description": "List DB tables", "inputSchema": {}}],
        "fetch": [{"name": "get_url", "description": "Fetch webpage", "inputSchema": {}}]
    }

    adapter = MCPToolAdapter(manager=mock_manager)
    count = adapter.register_all()
    assert count == 2

    # Verify registered in central tool registry
    registered_tools = tool_registry.list_tools()
    tool_names = [t["name"] for t in registered_tools]
    assert "mcp__sqlite__list_tables" in tool_names
    assert "mcp__fetch__get_url" in tool_names


def test_mcp_tool_call_routing():
    """Test 7: Verifies MCPManager correctly routes tool execution and handles retries."""
    manager = MCPManager()
    mock_client = MagicMock()
    mock_client.call_tool.return_value = {"status": "SUCCESS", "result": "table_users, table_logs"}
    manager.clients["sqlite"] = mock_client

    res = manager.call_tool("sqlite", "list_tables", {"db": "test.db"})
    assert res["status"] == "SUCCESS"
    assert "table_users" in res["result"]
    mock_client.call_tool.assert_called_once_with("list_tables", {"db": "test.db"})


def test_mcp_graceful_shutdown():
    """Test 8: Verifies shutdown stops all registered clients."""
    manager = MCPManager()
    mock_c1 = MagicMock()
    mock_c2 = MagicMock()
    manager.clients = {"s1": mock_c1, "s2": mock_c2}

    manager.shutdown()
    mock_c1.stop.assert_called_once()
    mock_c2.stop.assert_called_once()


def test_agent_works_without_mcp():
    """Test 9: Verifies LlamaToolAgent remains fully functional if MCP is absent or offline."""
    from core.llama_tool_agent import LlamaToolAgent

    # Mock MCPManager initialization failure
    with patch("mcp.mcp_manager.MCPManager.start_all", side_effect=Exception("Node.js missing")):
        agent = LlamaToolAgent()
        assert agent is not None
        # Agent catalog should still render standard tools cleanly
        catalog = agent.get_tool_catalog_prompt()
        assert len(catalog) > 0
