"""
Unit Tests for Layer 2 CommandDiscovery, HelpReader, and CommandCache.
"""

import os
import pytest
from tools.command_discovery import CommandDiscovery
from tools.help_reader import HelpReader
from tools.command_cache import (
    cache_command,
    cache_commands_batch,
    get_cached,
    search_cached,
    list_by_source,
    mark_favorite,
    list_favorites,
    increment_usage,
)


def test_discover_powershell_commands():
    """Tests discovery of PowerShell commands or graceful fallback."""
    d = CommandDiscovery()
    cmds = d.discover_powershell_commands()
    assert isinstance(cmds, list)
    if cmds:
        assert "name" in cmds[0]
        assert cmds[0]["source"] == "powershell"


def test_discover_cmd_commands():
    """Tests discovery of System32 Windows binaries."""
    d = CommandDiscovery()
    cmds = d.discover_cmd_commands()
    assert isinstance(cmds, list)
    if cmds:
        assert "name" in cmds[0]
        assert cmds[0]["source"] == "cmd"


def test_discover_python_packages():
    """Tests discovery of installed pip packages."""
    d = CommandDiscovery()
    pkgs = d.discover_python_packages()
    assert isinstance(pkgs, list)
    assert len(pkgs) > 0
    pkg_names = [p["name"].lower() for p in pkgs]
    assert "pytest" in pkg_names or "transformers" in pkg_names or len(pkg_names) > 5


def test_get_help_for_known_command():
    """Tests HelpReader fetching documentation."""
    hr = HelpReader()
    help_text = hr.get_help_text("dir", shell="cmd")
    assert isinstance(help_text, str)
    assert len(help_text) > 0


def test_cache_persists_discovered():
    """Tests SQLite caching of discovered commands."""
    name = "pytest_custom_tool_test"
    cache_command(name, shell="powershell", source="pip", path="/bin/pytest", help_text="Run tests")

    cached = get_cached(name)
    assert cached is not None
    assert cached["name"] == name
    assert cached["source"] == "pip"

    increment_usage(name)
    cached_after = get_cached(name)
    assert cached_after["usage_count"] >= 1

    mark_favorite(name, True)
    favs = list_favorites()
    assert any(f["name"] == name for f in favs)


def test_help_parser_extracts_syntax():
    """Tests parsing raw help text into structured syntax, parameters, examples, and description."""
    sample_help = r"""
NAME
    Get-Process
SYNOPSIS
    Gets the processes that are running on the local computer.
SYNTAX
    Get-Process [[-Name] <String[]>] [-ComputerName <String[]>] [<CommonParameters>]
DESCRIPTION
    The Get-Process cmdlet gets the processes on a local or remote computer.
PARAMETERS
    -Name <String[]>
        Specifies one or more process names.
    -Id <Int32[]>
        Specifies one or more process IDs (PIDs).
EXAMPLES
    Example 1: Get all running processes
    PS C:\> Get-Process
"""
    hr = HelpReader()
    parsed = hr.parse_help(sample_help)

    assert "Get-Process" in parsed["syntax"]
    assert "processes on a local" in parsed["description"]
    assert any("-Name" in p for p in parsed["parameters"])
    assert any("Get-Process" in e for e in parsed["examples"])
