import pytest
import time
from core.proactive_engine import (
    proactive_engine,
    context_prediction,
    suggestion_engine,
    alert_system,
    add_reminder,
    get_reminders,
    automated_workflows,
)


def test_context_prediction():
    pred = context_prediction()
    assert "time_of_day" in pred
    assert "day" in pred
    assert "predicted_needs" in pred
    assert isinstance(pred["predicted_needs"], list)


def test_suggestion_engine():
    suggestions = suggestion_engine()
    assert isinstance(suggestions, list)
    assert len(suggestions) >= 1
    types = [s["type"] for s in suggestions]
    assert "SECURITY_CHECK" in types or "ROUTINE_BACKUP" in types


def test_alert_system():
    alert = alert_system()
    assert "status" in alert
    assert alert["status"] in ["HEALTHY", "WARNING", "CRITICAL"]
    assert "alerts" in alert


def test_smart_reminders():
    due = time.time() + 3600
    res = add_reminder("Backup database dump", due, priority="high")
    assert res["status"] == "SUCCESS"
    rid = res["reminder_id"]

    active_rems = get_reminders(active_only=True)
    matching = [r for r in active_rems if r["reminder_id"] == rid]
    assert len(matching) == 1
    assert matching[0]["text"] == "Backup database dump"

    # Acknowledge
    assert proactive_engine.acknowledge_reminder(rid) is True
    active_after = get_reminders(active_only=True)
    assert rid not in [r["reminder_id"] for r in active_after]


def test_automated_workflows():
    res = automated_workflows("clean_temp")
    assert res["status"] == "SUCCESS"
    assert res["workflows_executed_count"] >= 1