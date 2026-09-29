"""
Unit tests for Tool Execution, Tool Registry, and RBAC Permissions.
"""

import pytest
from tools.permissions import PermissionManager, PermissionLevel
from tools.registry import ToolRegistry
from tools.executor import ToolExecutor


@pytest.mark.asyncio
async def test_tool_permission_gate_requires_confirmation():
    perm = PermissionManager(require_confirmation_for=[PermissionLevel.EXECUTE, PermissionLevel.SYSTEM])

    # 1. READ level (Safe, no confirmation required)
    granted, req_conf, reason = perm.verify_permission(
        "file_reader", PermissionLevel.READ, {}, user_confirmed=False
    )
    assert granted is True
    assert req_conf is False

    # 2. SYSTEM level without user confirmation (Must be denied)
    granted, req_conf, reason = perm.verify_permission(
        "system_execute_script", PermissionLevel.SYSTEM, {"script": "reboot.sh"}, user_confirmed=False
    )
    assert granted is False
    assert req_conf is True

    # 3. SYSTEM level WITH user confirmation (Granted)
    granted, req_conf, reason = perm.verify_permission(
        "system_execute_script", PermissionLevel.SYSTEM, {"script": "reboot.sh"}, user_confirmed=True
    )
    assert granted is True
    assert req_conf is False


@pytest.mark.asyncio
async def test_tool_executor_pipeline():
    executor = ToolExecutor()

    # Execute safe builtin tool
    res = await executor.execute_tool("system_diagnostics", {"scope": "full_telemetry"})
    assert res.success is True
    assert res.verified is True
    assert res.permission_granted is True
    assert "telemetry" in res.output

    # Execute non-existent tool
    bad_res = await executor.execute_tool("non_existent_tool_xyz", {})
    assert bad_res.success is False
    assert "not found" in bad_res.error
