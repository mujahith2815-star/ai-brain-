import pytest
from core.mcp_client import (
    mcp_client,
    connect,
    discover_tools,
    execute_tool,
    list_connections,
    PREBUILT_MCP_CONFIGS,
)


def test_prebuilt_mcp_configs_exist():
    configs = mcp_client.get_prebuilt_connections()
    expected = ["filesystem", "git", "docker", "postgres", "slack", "google_drive"]
    for service in expected:
        assert service in configs
        assert len(configs[service]["tools"]) > 0


def test_connect_prebuilt_filesystem():
    res = connect("filesystem")
    assert res["status"] == "SUCCESS"
    assert res["server_id"] == "mcp-filesystem"
    assert "read_file" in res["tools"]
    assert "list_directory" in res["tools"]


def test_discover_tools():
    tools_res = discover_tools("mcp-filesystem")
    assert tools_res["status"] == "SUCCESS"
    assert tools_res["tool_count"] >= 4
    tool_names = [t["name"] for t in tools_res["tools"]]
    assert "list_directory" in tool_names


def test_execute_mcp_tool():
    exec_res = execute_tool("mcp-filesystem", "list_directory", {"path": "."})
    assert exec_res["status"] == "SUCCESS"
    assert exec_res["jsonrpc"] == "2.0"
    content = exec_res["result"]["content"][0]["text"]
    assert "entries" in content or "directory" in content


def test_list_active_connections():
    conns = list_connections()
    assert len(conns) >= 1
    server_ids = [c["server_id"] for c in conns]
    assert "mcp-filesystem" in server_ids