"""
Unit Tests for Proactive Autonomous Agent Layer.
Covers TaskScheduler, SafetyGuard, AutonomousAgent, Watchers, Triggers,
Approval Queue, Task Log, and Rate Limiting.
All tests use mocks with zero background execution or network dependencies.
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from proactive.safety import SafetyGuard
from proactive.scheduler import TaskScheduler
from proactive.watchers import FileSystemWatcher, ConditionWatcher
from proactive.triggers import Trigger, TriggerType, load_triggers, validate_trigger
from proactive.autonomous_agent import AutonomousAgent
from knowledge.sqlite_store import KnowledgeStore
from config.proactive_config import ProactiveConfig


def test_scheduler_add_and_list_tasks(tmp_path):
    """Test scheduling, listing, and removing background tasks."""
    sched_file = tmp_path / "schedules.json"
    scheduler = TaskScheduler(schedules_path=str(sched_file))

    # Add task
    t = scheduler.add_task(
        name="test_daily_check",
        cron_expr="0 9 * * *",
        action_fn=lambda: "completed",
        args=["arg1"],
    )
    assert t["name"] == "test_daily_check"
    assert t["cron_expr"] == "0 9 * * *"

    # List tasks
    tasks = scheduler.list_tasks()
    matching = [task for task in tasks if task["name"] == "test_daily_check"]
    assert len(matching) == 1
    assert matching[0]["cron_expr"] == "0 9 * * *"

    # Remove task
    ok = scheduler.remove_task("test_daily_check")
    assert ok is True
    tasks_after = scheduler.list_tasks()
    assert not any(task["name"] == "test_daily_check" for task in tasks_after)


def test_scheduler_pause_resume(tmp_path):
    """Test emergency pause and resume of scheduler operations."""
    sched_file = tmp_path / "schedules.json"
    scheduler = TaskScheduler(schedules_path=str(sched_file))

    scheduler.pause_all()
    assert scheduler.is_paused() is True

    scheduler.resume_all()
    assert scheduler.is_paused() is False


def test_safety_guard_blocks_destructive_tools():
    """Verify SafetyGuard heuristic blocking of destructive commands."""
    sg = SafetyGuard()

    # Exact check required by validation specification
    allowed, reason = sg.validate_action("execute_command", {"cmd": "rm -rf /"})
    assert allowed is False
    assert reason == "blocked: destructive command"

    # Shell command with del /f /q
    allowed, _ = sg.validate_action("execute_command", {"command": "del /f /q C:\\important.txt"})
    assert allowed is False

    # Direct destructive tools
    allowed, _ = sg.validate_action("terminate_process", {"pid": 1234})
    assert allowed is False

    allowed, _ = sg.validate_action("delete_file", {"path": "system32.dll"})
    assert allowed is False


def test_safety_guard_allows_whitelisted_tools():
    """Verify SafetyGuard grants execution for all whitelisted tools."""
    sg = SafetyGuard()
    whitelisted = [
        "file_reader",
        "search_documents",
        "recall_fact",
        "add_to_list",
        "live_search",
        "list_processes",
    ]
    for tool in whitelisted:
        allowed, reason = sg.validate_action(tool, {"query": "test"})
        assert allowed is True
        assert reason == "whitelisted tool"


def test_autonomous_agent_respects_kill_switch(tmp_path):
    """Verify AutonomousAgent halts actions immediately when kill switch is active."""
    store = KnowledgeStore(db_path=str(tmp_path / "agent_memory.db"))
    agent = AutonomousAgent(knowledge_store=store)

    agent.pause()
    assert agent.is_paused() is True

    res = agent.execute_action(
        name="test_action",
        tool="file_reader",
        args={"file_path": "readme.txt"},
    )
    assert res["status"] == "SKIPPED"
    assert res["reason"] == "kill switch paused"

    agent.resume()
    assert agent.is_paused() is False


def test_autonomous_agent_queues_approval_required_actions(tmp_path):
    """Verify actions requiring approval or non-whitelisted tools are routed to approval queue."""
    store = KnowledgeStore(db_path=str(tmp_path / "agent_memory.db"))
    agent = AutonomousAgent(knowledge_store=store)

    res = agent.execute_action(
        name="dangerous_format",
        tool="execute_command",
        args={"cmd": "format D:"},
        requires_approval=True,
    )
    assert res["status"] == "QUEUED"
    assert "action_id" in res

    # Verify action appears in pending approval queue
    pending = agent.get_approval_queue()
    assert len(pending) == 1
    assert pending[0]["action_name"] == "dangerous_format"
    assert pending[0]["tool"] == "execute_command"


def test_approval_queue_approve_reject(tmp_path):
    """Test manual approval and rejection lifecycle of queued actions."""
    store = KnowledgeStore(db_path=str(tmp_path / "agent_memory.db"))
    agent = AutonomousAgent(knowledge_store=store)
    agent._execute_tool_direct = MagicMock(return_value="Executed approved tool")

    # 1. Propose two actions
    qid1 = agent.propose_action("action_1", "Reason 1", "file_writer", {"path": "out.txt", "content": "hi"})
    qid2 = agent.propose_action("action_2", "Reason 2", "execute_command", {"cmd": "dir"})

    pending = agent.get_approval_queue()
    assert len(pending) == 2

    # 2. Approve action 1
    appr_res = agent.approve_action(qid1)
    assert appr_res["status"] == "EXECUTED"
    assert appr_res["result"] == "Executed approved tool"

    # 3. Reject action 2
    rej_res = agent.reject_action(qid2)
    assert rej_res["status"] == "REJECTED"

    # 4. Queue should now be empty of pending actions
    assert len(agent.get_approval_queue()) == 0


def test_trigger_loading_and_validation(tmp_path):
    """Test loading and safety validation of triggers.json."""
    trig_file = tmp_path / "test_triggers.json"
    raw_triggers = [
        {
            "name": "valid_cron",
            "type": "CRON",
            "config": {"cron": "0 10 * * *"},
            "action": {"tool": "recall_fact", "args": {"key": "status"}},
            "requires_approval": False,
            "enabled": True,
        },
        {
            "name": "invalid_destructive_without_approval",
            "type": "CRON",
            "config": {"cron": "0 0 * * *"},
            "action": {"tool": "execute_command", "args": {"cmd": "rm -rf /tmp"}},
            "requires_approval": False,  # Should fail validation
            "enabled": True,
        },
    ]
    trig_file.write_text(json.dumps(raw_triggers), encoding="utf-8")

    loaded = load_triggers(str(trig_file))
    # Only the valid non-destructive trigger should pass loader validation
    assert len(loaded) == 1
    assert loaded[0].name == "valid_cron"

    # Test direct validator rejection
    bad_trigger = Trigger.from_dict(raw_triggers[1])
    valid, reason = validate_trigger(bad_trigger)
    assert valid is False
    assert "Destructive trigger actions must require user approval" in reason


def test_condition_watcher_edge_triggered():
    """Verify ConditionWatcher triggers strictly on False -> True transition (edge-triggered)."""
    watcher = ConditionWatcher()
    mock_metric = [False]
    trigger_count = [0]

    def _callback(name):
        trigger_count[0] += 1

    watcher.add_condition("high_load", lambda: mock_metric[0], _callback)

    # Poll 1: False -> False (No event)
    mock_metric[0] = False
    watcher.poll()
    assert trigger_count[0] == 0

    # Poll 2: False -> True (EDGE TRIGGERED -> Fire event)
    mock_metric[0] = True
    watcher.poll()
    assert trigger_count[0] == 1

    # Poll 3: True -> True (Level is still True -> NO extra event)
    mock_metric[0] = True
    watcher.poll()
    assert trigger_count[0] == 1

    # Poll 4: True -> False (Reset back to False -> No event)
    mock_metric[0] = False
    watcher.poll()
    assert trigger_count[0] == 1

    # Poll 5: False -> True (EDGE TRIGGERED again -> Fire event)
    mock_metric[0] = True
    watcher.poll()
    assert trigger_count[0] == 2


def test_file_watcher_triggers_callback():
    """Verify FileSystemWatcher triggers the registered callback on file events."""
    fsw = FileSystemWatcher(watch_paths=["knowledge/inbox"])
    captured_events = []

    fsw.callback = lambda event_type, path: captured_events.append((event_type, path))

    # Simulate filesystem events deterministically
    fsw.simulate_event("created", "knowledge/inbox/notes.pdf")
    fsw.simulate_event("modified", "knowledge/inbox/notes.pdf")
    fsw.simulate_event("deleted", "knowledge/inbox/notes.pdf")

    assert len(captured_events) == 3
    assert captured_events[0] == ("created", "knowledge/inbox/notes.pdf")
    assert captured_events[1] == ("modified", "knowledge/inbox/notes.pdf")
    assert captured_events[2] == ("deleted", "knowledge/inbox/notes.pdf")


def test_task_log_persistence(tmp_path):
    """Verify task log writes to database and retrieves recent history."""
    store = KnowledgeStore(db_path=str(tmp_path / "agent_memory.db"))

    # Log executions
    store.log_task_execution(
        task_name="daily_summary",
        action="search_documents({'query': 'inbox'})",
        result="Generated 3 summaries",
        approved=True,
    )
    store.log_task_execution(
        task_name="cleanup_job",
        action="execute_command({'cmd': 'clean'})",
        result="Cleaned 50MB",
        approved=False,
    )

    logs = store.get_recent_task_logs(limit=10)
    assert len(logs) == 2
    # Ordered DESC by ID
    assert logs[0]["task_name"] == "cleanup_job"
    assert logs[0]["approved_by_user"] is False
    assert logs[1]["task_name"] == "daily_summary"
    assert logs[1]["approved_by_user"] is True


def test_max_actions_per_hour_rate_limit(tmp_path):
    """Verify rate limiter blocks autonomous actions exceeding hourly quota."""
    store = KnowledgeStore(db_path=str(tmp_path / "agent_memory.db"))
    custom_cfg = ProactiveConfig(max_actions_per_hour=3)
    agent = AutonomousAgent(knowledge_store=store, config=custom_cfg)
    agent._execute_tool_direct = MagicMock(return_value="executed")

    # Run 3 actions within rate limit
    for i in range(3):
        res = agent.execute_action(f"action_{i}", "recall_fact", {"key": "foo"})
        assert res["status"] == "EXECUTED"

    # 4th action exceeds rate limit of 3
    res4 = agent.execute_action("action_4", "recall_fact", {"key": "foo"})
    assert res4["status"] == "SKIPPED"
    assert res4["reason"] == "rate limit exceeded"


def test_bootstrap_loads_default_triggers():
    """Verify bootstrap_from_triggers registers all default triggers from triggers.json."""
    scheduler = TaskScheduler()
    count = scheduler.bootstrap_from_triggers("proactive/triggers.json")
    assert count >= 4
    assert len(scheduler.list_tasks()) >= 4


def test_disabled_triggers_skipped(tmp_path):
    """Verify triggers with enabled=False are skipped during bootstrap."""
    sched_file = tmp_path / "schedules.json"
    trig_file = tmp_path / "triggers.json"
    data = [
        {
            "name": "disabled_cron",
            "type": "CRON",
            "config": {"cron": "0 12 * * *"},
            "action": "Some safe task",
            "requires_approval": False,
            "enabled": False,
        },
        {
            "name": "enabled_cron",
            "type": "CRON",
            "config": {"cron": "0 13 * * *"},
            "action": "Another safe task",
            "requires_approval": False,
            "enabled": True,
        }
    ]
    trig_file.write_text(json.dumps(data), encoding="utf-8")

    scheduler = TaskScheduler(schedules_path=str(sched_file))
    count = scheduler.bootstrap_from_triggers(str(trig_file))
    assert count == 1
    task_names = [t["name"] for t in scheduler.list_tasks()]
    assert "disabled_cron" not in task_names
    assert "enabled_cron" in task_names


def test_destructive_trigger_without_approval_rejected(tmp_path):
    """Verify destructive triggers without requires_approval=True are rejected."""
    sched_file = tmp_path / "schedules.json"
    trig_file = tmp_path / "triggers.json"
    data = [
        {
            "name": "dangerous_delete",
            "type": "CRON",
            "config": {"cron": "0 0 * * *"},
            "action": "Delete all log files with rm -rf /logs",
            "requires_approval": False,
            "enabled": True,
        }
    ]
    trig_file.write_text(json.dumps(data), encoding="utf-8")

    scheduler = TaskScheduler(schedules_path=str(sched_file))
    count = scheduler.bootstrap_from_triggers(str(trig_file))
    assert count == 0
    assert not any(t["name"] == "dangerous_delete" for t in scheduler.list_tasks())


def test_bootstrap_idempotent():
    """Verify repeated bootstrap calls do not duplicate registered tasks."""
    scheduler = TaskScheduler()
    count1 = scheduler.bootstrap_from_triggers("proactive/triggers.json")
    tasks_len1 = len(scheduler.list_tasks())

    count2 = scheduler.bootstrap_from_triggers("proactive/triggers.json")
    tasks_len2 = len(scheduler.list_tasks())

    assert tasks_len1 == tasks_len2
    names = [t["name"] for t in scheduler.list_tasks()]
    assert len(names) == len(set(names))


def test_scheduler_pause_stops_bootstrap(tmp_path):
    """Verify pausing scheduler ensures bootstrapped tasks do not fire."""
    sched_file = tmp_path / "schedules.json"
    scheduler = TaskScheduler(schedules_path=str(sched_file))
    scheduler.pause_all()
    assert scheduler.is_paused() is True

    count = scheduler.bootstrap_from_triggers("proactive/triggers.json")
    assert count >= 4
    # Tasks are registered
    assert len(scheduler.list_tasks()) >= 4
    # But scheduler remains paused so jobs will be skipped if triggered
    assert scheduler.is_paused() is True
    scheduler.resume_all()
    assert scheduler.is_paused() is False
