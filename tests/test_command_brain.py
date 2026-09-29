"""
Unit and Integration Tests for 3-Layer Command Intelligence Brain (v1.2.0).
Tests Core Catalog (Layer 1), Live Discovery Caching (Layer 2),
Learned Pattern Promotion (Layer 3), Cascade Search, and Storage Budget.
"""

import json
import os
import pytest
from pathlib import Path

from knowledge.commands.core.load_core import (
    load_core_commands,
    get_core_command,
    search_core_commands,
)
from tools.command_discovery import CommandDiscovery
from tools.command_cache import (
    cache_command,
    get_cached,
    search_cached,
    count_cached,
)
from knowledge.commands.command_patterns import (
    log_sequence,
    promote_to_pattern,
    get_all_patterns,
    suggest_chain,
    get_similar_patterns,
)
from knowledge.commands.pattern_learner import PatternLearner
from tools.command_brain import CommandBrain


def test_layer1_core_loads_500_commands():
    """Verifies that Layer 1 loads ~500 high-value commands across all shells."""
    commands = load_core_commands(force_reload=True)
    assert len(commands) >= 480, f"Expected ~500 commands, got {len(commands)}"

    shells = {c.get("shell") for c in commands}
    assert "powershell" in shells
    assert "cmd" in shells
    assert "bash" in shells
    assert "cross-platform" in shells

    for cmd in commands:
        assert "name" in cmd
        assert "syntax" in cmd
        assert "description" in cmd
        assert cmd.get("source") == "core"


def test_layer2_discovery_runs():
    """Verifies that CommandDiscovery returns structured results and counts."""
    d = CommandDiscovery()
    py_pkgs = d.discover_python_packages()
    assert isinstance(py_pkgs, list)
    assert len(py_pkgs) > 0

    cmd_tools = d.discover_cmd_commands()
    assert isinstance(cmd_tools, list)


def test_layer3_pattern_promotion_after_3_uses():
    """Verifies that a workflow sequence repeated 3+ times is automatically promoted to a pattern."""
    task_desc = "Automated Test Clean & Rebuild Cache"
    commands = ["Get-Process python*", "Clear-Host", "Write-Output 'Clean'"]

    # Log 3 successful executions
    id1 = log_sequence(task_desc, commands, success=True, duration_ms=120)
    id2 = log_sequence(task_desc, commands, success=True, duration_ms=110)
    id3 = log_sequence(task_desc, commands, success=True, duration_ms=105)

    learner = PatternLearner(interval_seconds=999)
    promoted_count = learner.scan_and_promote()
    assert promoted_count >= 1

    patterns = get_all_patterns()
    matching = [p for p in patterns if p.get("description") == task_desc]
    assert len(matching) >= 1
    assert matching[0]["success_count"] >= 3
    assert matching[0]["command_chain"] == commands


def test_cascade_search_finds_learned_first():
    """Cascade search should hit Layer 3 (Learned Patterns) before core or discovery."""
    task_desc = "Deploy Special Web Service Stack"
    chain = ["docker build -t app .", "docker compose up -d"]
    seq_id = log_sequence(task_desc, chain, success=True, duration_ms=500)
    promote_to_pattern(seq_id)

    brain = CommandBrain()
    res = brain.find("Deploy Special Web Service Stack")
    assert res["status"] == "FOUND"
    assert res["layer"] == "layer3_learned"
    assert len(res["results"]) > 0


def test_cascade_search_falls_back_to_core():
    """Cascade search should find known core commands in Layer 1."""
    brain = CommandBrain()
    res = brain.find("Compress-Archive")
    assert res["status"] == "FOUND"
    assert res["layer"] == "layer1_core"
    assert res["results"][0]["name"] == "Compress-Archive"


def test_cascade_search_falls_back_to_discovery():
    """Cascade search should find cached system tools in Layer 2 SQLite cache."""
    # Cache a unique discovery entry
    unique_tool_name = "test_custom_os_tool_xyz"
    cache_command(
        name=unique_tool_name,
        shell="powershell",
        source="powershell",
        path="C:/Tools/xyz.exe",
        help_text="Custom internal utility"
    )

    brain = CommandBrain()
    res = brain.find("test_custom_os_tool_xyz")
    assert res["status"] == "FOUND"
    assert res["layer"] == "layer2_discovered"
    assert any(r["name"] == unique_tool_name for r in res["results"])


def test_command_explain_uses_live_help(monkeypatch):
    """Verifies that explain retrieves documentation for core and live OS commands."""
    brain = CommandBrain()
    # Core command
    core_exp = brain.explain("Get-ChildItem")
    assert core_exp.get("source") == "layer1_core"
    assert "Get-ChildItem" in core_exp.get("command", "")
    assert core_exp.get("syntax")

    # Mocked live help
    def mock_fetch(cmd):
        return "NAME\n    fake-tool\nSYNOPSIS\n    fake-tool [flags]\nDESCRIPTION\n    A fake utility."

    monkeypatch.setattr(brain.discovery.help_reader, "_fetch_powershell_help", mock_fetch)
    monkeypatch.setattr(brain.discovery.help_reader, "_fetch_cmd_help", mock_fetch)

    live_exp = brain.explain("nonexistent_rare_cmd_tool")
    assert live_exp.get("source") == "layer2_live_help"
    assert "fake-tool" in live_exp.get("raw_help", "")


def test_pattern_storage_and_retrieval():
    """Tests sequence logging, promotion, and chain recommendation."""
    task = "Benchmark Local Model Run"
    chain = ["python -m pytest", "python run_model_chat.py -c /stats"]
    seq_id = log_sequence(task, chain, success=True, duration_ms=250)
    pat = promote_to_pattern(seq_id)
    assert pat is not None

    suggested = suggest_chain(task)
    assert suggested == chain


def test_storage_size_under_budget():
    """Verifies that all Layer 1 JSON files combined are under 500 KB."""
    core_dir = Path("knowledge/commands/core")
    total_bytes = 0
    for f in core_dir.glob("*.json"):
        total_bytes += f.stat().st_size

    total_kb = total_bytes / 1024.0
    print(f"Layer 1 total storage: {total_kb:.2f} KB")
    assert total_kb < 500.0, f"Layer 1 size {total_kb} KB exceeds 500 KB limit"
