"""
Unit tests for Orvix Terminal Tools, Shell Safety Guard, and Shell Detector.
"""

import os
import pytest
from tools.shell_safety import ShellSafety
from tools.shell_detector import ShellDetector
from tools.terminal_tools import (
    run_terminal,
    chain_commands,
    pipe_command,
    find_file,
    translate_command,
    explain_command,
    suggest_command,
    lookup_command,
    search_commands_tool,
)


def test_shell_safety_safe_commands():
    """Verify safe commands are allowed."""
    assert ShellSafety.check_command("echo Hello")["allowed"]
    assert ShellSafety.check_command("ls -la")["allowed"]
    assert ShellSafety.check_command("Get-Process")["allowed"]
    assert ShellSafety.check_command("ping 127.0.0.1")["allowed"]


def test_shell_safety_blocked_commands():
    """Verify destructive commands are blocked outright."""
    res1 = ShellSafety.check_command("rm -rf /")
    assert not res1["allowed"]
    assert res1["risk_level"] == "BLOCKED"

    res2 = ShellSafety.check_command("format C:")
    assert not res2["allowed"]
    assert res2["risk_level"] == "BLOCKED"

    res3 = ShellSafety.check_command("Clear-Disk")
    assert not res3["allowed"]


def test_shell_safety_approval_commands():
    """Verify commands with high impact require human approval."""
    res = ShellSafety.check_command("shutdown -h now")
    assert res["allowed"]  # allowed only with explicit approval
    assert res["requires_approval"]
    assert res["risk_level"] == "DANGEROUS"


def test_shell_detector_available_shells():
    """Verify shell detection discovers system shells."""
    shells = ShellDetector.get_available_shells()
    assert isinstance(shells, list)
    assert len(shells) > 0
    assert all("name" in s and "path" in s for s in shells)


def test_shell_detector_default_shell():
    """Verify default shell resolution."""
    sh = ShellDetector.get_default_shell()
    assert isinstance(sh, str)
    assert len(sh) > 0


def test_run_terminal_echo():
    """Verify execution of simple echo command."""
    res = run_terminal("echo Hello_Orvix_Test")
    assert res["status"] == "SUCCESS"
    assert res["exit_code"] == 0
    assert "Hello_Orvix_Test" in res["stdout"]


def test_run_terminal_blocked():
    """Verify run_terminal rejects blocked commands without spawning subprocess."""
    res = run_terminal("rm -rf /")
    assert res["status"] == "BLOCKED"
    assert "BLOCKED" in res["error"]


def test_run_terminal_error_exit_code():
    """Verify non-existent command returns FAILED and logs error."""
    res = run_terminal("nonexistent_command_xyz_12345")
    assert res["status"] in ("FAILED", "BLOCKED")
    assert res["exit_code"] != 0 or res.get("stderr")


def test_chain_commands_sequential():
    """Verify sequential execution of chained commands."""
    res = chain_commands(["echo cmd1", "echo cmd2"])
    assert res["status"] == "SUCCESS"
    assert res["total_executed"] == 2
    assert len(res["results"]) == 2


def test_chain_commands_stop_on_error():
    """Verify chain halts when a command fails with stop_on_error=True."""
    res = chain_commands(["nonexistent_xyz_error_cmd", "echo should_not_run"], stop_on_error=True)
    assert res["status"] == "FAILED"
    assert res["total_executed"] == 1


def test_find_file_existing():
    """Verify file finding in current directory."""
    res = find_file("run_model_chat.py", max_depth=2)
    assert res["status"] == "SUCCESS"
    assert res["total_found"] >= 1
    assert any("run_model_chat.py" in m["name"] for m in res["matches"])


def test_find_file_fallback():
    """Verify graceful handling when search_path does not exist."""
    res = find_file("*.py", search_path="non_existent_folder_xyz_123")
    assert res["status"] == "SUCCESS"
    assert "matches" in res


def test_explain_command():
    """Verify command dissection and flag documentation."""
    exp = explain_command("ls -la")
    assert exp["status"] == "SUCCESS"
    assert exp["base_command"] == "ls"
    assert "-la" in exp["recognized_flags"] or "-l" in exp["recognized_flags"] or "-a" in exp["recognized_flags"] or len(exp["recognized_flags"]) > 0


def test_suggest_command():
    """Verify natural language intent suggestion."""
    res = suggest_command("how to check memory usage")
    assert res["status"] == "SUCCESS"
    assert res["suggested_count"] > 0


def test_lookup_and_search_tools():
    """Verify lookup_command and search_commands_tool."""
    lookup_res = lookup_command("ls")
    assert lookup_res["status"] == "SUCCESS"
    assert lookup_res["command"]["name"] == "ls"

    search_res = search_commands_tool("process")
    assert search_res["status"] == "SUCCESS"
    assert search_res["count"] > 0
