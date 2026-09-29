"""
Tests for Proactive Sentinel & Anticipation Engine.
"""

import time
import pytest
from core.proactive_engine import (
    proactive_engine,
    morning_briefing,
    monitor_disk_space,
    auto_cleanup_temp,
    add_reminder,
    scheduled_reminders,
    context_prediction,
    suggestion_engine,
    automated_workflows,
)


def test_morning_briefing():
    briefing = morning_briefing()
    assert "date" in briefing
    assert "greeting" in briefing
    assert "system_health" in briefing
    assert "daily_inspiration" in briefing
    assert briefing["disk_free_gb"] > 0


def test_monitor_disk_space():
    disk = monitor_disk_space(threshold_percent=95.0)
    assert "total_gb" in disk
    assert "used_gb" in disk
    assert "free_gb" in disk
    assert "used_percent" in disk
    assert disk["threshold_percent"] == 95.0
    assert isinstance(disk["warning"], bool)


def test_auto_cleanup_temp():
    res = auto_cleanup_temp(dry_run=True)
    assert res["status"] == "SUCCESS"
    assert res["dry_run"] is True
    assert "files_cleaned" in res
    assert "freed_kb" in res


def test_reminders_lifecycle():
    now = time.time()
    # Add a reminder due in the past (overdue)
    r1 = add_reminder("Run weekly security audit", due_time=now - 10, priority="high")
    assert r1["status"] == "SUCCESS"

    due = scheduled_reminders()
    assert len(due) >= 1
    texts = [r["text"] for r in due]
    assert "Run weekly security audit" in texts

    # Acknowledge
    proactive_engine.acknowledge_reminder(r1["reminder_id"])
    due_after = scheduled_reminders()
    texts_after = [r["text"] for r in due_after]
    assert "Run weekly security audit" not in texts_after


def test_context_prediction():
    pred = context_prediction()
    assert "time_of_day" in pred
    assert "day" in pred
    assert len(pred["predicted_needs"]) > 0


def test_suggestion_engine():
    suggs = suggestion_engine()
    assert isinstance(suggs, list)
    assert len(suggs) >= 1
    types = [s["type"] for s in suggs]
    assert "SECURITY_CHECK" in types or "ROUTINE_BACKUP" in types


def test_automated_workflows():
    wf = automated_workflows("clean_temp")
    assert wf["status"] == "SUCCESS"
    assert wf["workflows_executed_count"] == 1
