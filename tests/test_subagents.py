import pytest
from core.subagent_orchestrator import (
    subagent_orchestrator,
    spawn_subagent,
    parallel_execute,
    aggregate_results,
    PREBUILT_ROLES,
)


def test_available_roles():
    roles = subagent_orchestrator.get_available_roles()
    expected = ["researcher", "coder", "data_analyst", "file_manager", "system_monitor", "writer", "translator", "security_auditor"]
    for r in expected:
        assert r in roles


def test_spawn_single_subagent():
    res = spawn_subagent(role="system_monitor", task="Check memory and system telemetry")
    assert res is not None
    assert res.role == "system_monitor"
    assert res.subagent_id.startswith("subagent-")
    assert res.status in ["SUCCESS", "PARTIAL", "FAILED"]


def test_subagent_role_alias():
    res = spawn_subagent(role="code", task="Refactor Fibonacci logic")
    assert res.role == "coder"


def test_parallel_subagent_execution():
    tasks = [
        {"role": "researcher", "task": "Lookup AI news"},
        {"role": "data_analyst", "task": "Summarize test metric array"},
    ]
    results = parallel_execute(tasks, max_workers=2)
    assert len(results) == 2
    roles = [r.role for r in results]
    assert "researcher" in roles
    assert "data_analyst" in roles


def test_aggregate_results():
    tasks = [
        {"role": "writer", "task": "Draft intro email"},
        {"role": "translator", "task": "Translate greeting"},
    ]
    results = parallel_execute(tasks, max_workers=2)
    report = aggregate_results(results)
    assert "CONSOLIDATED SUBAGENT REPORT" in report
    assert "WRITER" in report
    assert "TRANSLATOR" in report