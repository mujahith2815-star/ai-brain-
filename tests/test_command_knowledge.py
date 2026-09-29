"""
Unit tests for Orvix Command Knowledge Base, Auto-Ingestion, and History Analytics.
"""

import os
import pytest
from knowledge.commands import (
    load_all_commands,
    get_command_by_name,
    search_commands,
    get_by_category,
    get_by_shell,
    get_by_tag,
    get_all_categories,
    get_command_summary,
    ensure_commands_indexed,
    is_indexed,
    log_command,
    get_history,
    get_success_rate,
    learn_from_history,
)


def test_load_all_commands():
    """Verify pre-loaded command dataset has at least 240 commands."""
    cmds = load_all_commands()
    assert isinstance(cmds, list)
    assert len(cmds) >= 240, f"Expected at least 240 commands, found {len(cmds)}"


def test_command_schema_validity():
    """Verify all command entries conform to standard schema."""
    cmds = load_all_commands()
    required_keys = {"name", "shell", "category", "description", "syntax"}
    for c in cmds:
        for k in required_keys:
            assert k in c, f"Command {c.get('name')} missing required key '{k}'"
        assert isinstance(c.get("tags", []), list)
        assert c.get("safety") in ("safe", "caution", "moderate", "dangerous", "destructive", None)


def test_get_command_by_name():
    """Verify exact command lookup for key Windows and Linux commands."""
    ls_cmd = get_command_by_name("ls")
    assert ls_cmd is not None
    assert "directory" in ls_cmd["description"].lower()

    gci_cmd = get_command_by_name("Get-ChildItem")
    assert gci_cmd is not None
    assert gci_cmd["shell"] == "powershell"

    curl_cmd = get_command_by_name("curl")
    assert curl_cmd is not None


def test_get_command_by_name_case_insensitive():
    """Verify lookup is case-insensitive."""
    cmd1 = get_command_by_name("LS")
    assert cmd1 is not None
    assert cmd1["name"] == "ls"

    cmd2 = get_command_by_name("get-childitem")
    assert cmd2 is not None


def test_search_commands_keyword():
    """Verify keyword searching across commands."""
    results = search_commands("disk space", limit=5)
    assert len(results) > 0
    names = [r["name"].lower() for r in results]
    assert any("df" in n or "psdrive" in n or "disk" in n or "volume" in n for n in names)


def test_get_by_category():
    """Verify grouping and retrieval by category."""
    cats = get_all_categories()
    assert "filesystem" in cats
    assert "network" in cats

    fs_cmds = get_by_category("filesystem")
    assert len(fs_cmds) >= 20
    assert any(c["name"] == "ls" for c in fs_cmds)


def test_get_by_shell():
    """Verify shell-specific filtering."""
    ps_cmds = get_by_shell("powershell")
    assert len(ps_cmds) >= 50
    assert all(c["shell"] in ("powershell", "universal") for c in ps_cmds)

    bash_cmds = get_by_shell("bash")
    assert len(bash_cmds) >= 50


def test_get_by_tag():
    """Verify tag-based filtering."""
    file_cmds = get_by_tag("files")
    assert len(file_cmds) > 0


def test_get_command_summary():
    """Verify summary statistics calculation."""
    summary = get_command_summary()
    assert summary["total_commands"] >= 240
    assert "shells" in summary
    assert "categories" in summary
    assert "powershell" in summary["shells"]
    assert "bash" in summary["shells"]


def test_ensure_commands_indexed():
    """Verify idempotent command auto-indexing into VectorStore."""
    res = ensure_commands_indexed()
    assert res["status"] in ("indexed", "already_indexed")
    assert is_indexed()


def test_command_history_logging_and_stats():
    """Verify SQLite command history logging, retrieval, and statistics."""
    row_id = log_command(
        command="Get-Process",
        shell="powershell",
        working_dir=os.getcwd(),
        exit_code=0,
        stdout="Test stdout",
        stderr="",
        execution_time_ms=25.5,
    )
    assert row_id > 0

    history = get_history(limit=5)
    assert len(history) > 0
    assert history[0]["command"] == "Get-Process"

    stats = get_success_rate()
    assert stats["total_executed"] > 0
    assert stats["successful"] > 0


def test_auto_learner_analysis():
    """Verify autonomous learner analysis over command history."""
    learner_res = learn_from_history()
    assert "status" in learner_res
    assert learner_res["status"] in ("success", "no_history")
    assert "total_learned" in learner_res or "learned_count" in learner_res
