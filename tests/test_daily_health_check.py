"""
Unit and Integration Tests for the Daily Health Check & Alerting System (v1.4.4).
Verifies:
1. SystemDoctor diagnostic aggregation
2. 24-hour error frequency detection and flagging
3. Disk space capacity boundaries and low-disk failure
4. MCP server status evaluation
5. Proactive task scheduler checking
6. Toast notification alert dispatching
7. SMTP email alerting branch handling
8. Historical health snapshot persistence and retrieval
9. CLI report formatting and table outputs
"""

import json
import os
import shutil
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from scripts.daily_health_check import (
    check_system_doctor,
    check_recent_errors,
    check_disk_space,
    check_mcp_servers,
    check_proactive_tasks,
    send_health_alert,
    save_health_history,
    get_health_history,
    run_health_check,
    format_health_report,
    format_history_table,
)


@pytest.fixture
def test_workspace(tmp_path):
    """Sets up an isolated mock workspace for health checks."""
    ws = tmp_path / "orvix_test_ws"
    ws.mkdir(parents=True, exist_ok=True)
    logs_dir = ws / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    knowledge_dir = ws / "knowledge"
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    proactive_dir = ws / "proactive"
    proactive_dir.mkdir(parents=True, exist_ok=True)

    # Initialize empty errors.db
    db_path = logs_dir / "errors.db"
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                category TEXT NOT NULL,
                source_file TEXT,
                function_name TEXT,
                error_type TEXT NOT NULL,
                error_message TEXT NOT NULL,
                traceback TEXT,
                context_json TEXT,
                count INTEGER DEFAULT 1,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                error_hash TEXT UNIQUE
            );
            """
        )
        conn.commit()

    # Initialize triggers.json
    (proactive_dir / "triggers.json").write_text(
        json.dumps([{"name": "daily_health_check", "type": "CRON", "enabled": True}]),
        encoding="utf-8",
    )

    return ws


def test_check_recent_errors_clean(test_workspace):
    """Verifies check passes when errors.db has zero errors."""
    res = check_recent_errors(test_workspace, hours=24)
    assert res["passed"] is True
    assert res["error_count"] == 0
    assert "0 errors recorded" in res["message"]


def test_check_recent_errors_flags_failures(test_workspace):
    """Verifies check fails when errors are logged in the 24h window."""
    db_path = test_workspace / "logs" / "errors.db"
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            INSERT INTO errors (
                timestamp, category, error_type, error_message, count, first_seen, last_seen, error_hash
            ) VALUES (?, 'CORE', 'SystemError', 'Critical memory fault', 3, ?, ?, 'abc123hash');
            """,
            (now_str, now_str, now_str),
        )
        conn.commit()

    res = check_recent_errors(test_workspace, hours=24, max_allowed=0)
    assert res["passed"] is False
    assert res["error_count"] == 3
    assert res["unique_errors"] == 1
    assert "3 error occurrences" in res["message"]


def test_check_recent_errors_ignores_stale_errors(test_workspace):
    """Verifies check ignores errors older than the specified window."""
    db_path = test_workspace / "logs" / "errors.db"
    stale_str = (datetime.now(timezone.utc) - timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            INSERT INTO errors (
                timestamp, category, error_type, error_message, count, first_seen, last_seen, error_hash
            ) VALUES (?, 'CORE', 'StaleError', 'Old crash', 1, ?, ?, 'stalehash');
            """,
            (stale_str, stale_str, stale_str),
        )
        conn.commit()

    res = check_recent_errors(test_workspace, hours=24, max_allowed=0)
    assert res["passed"] is True
    assert res["error_count"] == 0


def test_check_disk_space_healthy(test_workspace):
    """Verifies check passes when disk space is sufficient."""
    fake_usage = MagicMock(total=100 * 1024**3, used=50 * 1024**3, free=50 * 1024**3)
    with patch("shutil.disk_usage", return_value=fake_usage):
        res = check_disk_space(test_workspace, min_gb=1.0)
        assert res["passed"] is True
        assert res["free_c_gb"] >= 50.0


def test_check_disk_space_low_disk(test_workspace):
    """Verifies check fails when disk space falls below minimum threshold."""
    low_usage = MagicMock(total=100 * 1024**3, used=99.5 * 1024**3, free=0.5 * 1024**3)
    with patch("shutil.disk_usage", return_value=low_usage):
        res = check_disk_space(test_workspace, min_gb=1.0)
        assert res["passed"] is False
        assert "Low disk space" in res["message"]


def test_check_mcp_servers_pass_and_fail(test_workspace):
    """Verifies MCP server connectivity check reflects doctor status."""
    with patch("diagnostics.doctor.SystemDoctor.check_mcp_servers", return_value=(True, "MCP: 3/3 online")):
        res = check_mcp_servers(test_workspace)
        assert res["passed"] is True
        assert "3/3 online" in res["message"]

    with patch("diagnostics.doctor.SystemDoctor.check_mcp_servers", return_value=(False, "MCP: 0/3 online (failed)")):
        res = check_mcp_servers(test_workspace)
        assert res["passed"] is False
        assert "0/3 online" in res["message"]


def test_check_proactive_tasks(test_workspace):
    """Verifies proactive scheduler status reflection."""
    with patch("diagnostics.doctor.SystemDoctor.check_proactive_scheduler", return_value=(True, "5 tasks registered")):
        res = check_proactive_tasks(test_workspace)
        assert res["passed"] is True
        assert "5 tasks" in res["message"]


def test_send_health_alert_dispatches_toast():
    """Verifies alert dispatcher triggers native desktop notification toast."""
    mock_result = {
        "timestamp": "2026-09-18 08:00:00 UTC",
        "healthy": False,
        "failed_count": 2,
        "total_checks": 5,
        "failing_checks": ["24h Error Rate", "Disk Capacity"],
        "checks": [
            {"name": "24h Error Rate", "passed": False, "message": "5 errors"},
            {"name": "Disk Capacity", "passed": False, "message": "Low disk space"},
        ],
    }

    with patch("tools.notification_tool.show_notification", return_value={"status": "SUCCESS"}) as mock_notify:
        alert_info = send_health_alert(mock_result)
        assert alert_info["alert_sent"] is True
        assert "desktop_toast" in alert_info["channels"]
        mock_notify.assert_called_once()
        call_args = mock_notify.call_args[0]
        assert "Orvix Health Alert" in call_args[0]
        assert "2/5 Checks Failed" in call_args[0]


def test_send_health_alert_smtp_channel(monkeypatch):
    """Verifies SMTP email dispatch channel when environment credentials exist."""
    monkeypatch.setenv("ALERT_EMAIL_TO", "operator@example.com")
    monkeypatch.setenv("SMTP_SERVER", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "alert@example.com")
    monkeypatch.setenv("SMTP_PASS", "secret")

    mock_result = {
        "timestamp": "2026-09-18 08:00:00 UTC",
        "healthy": False,
        "failed_count": 1,
        "total_checks": 5,
        "failing_checks": ["SystemDoctor Diagnostics"],
        "checks": [{"name": "SystemDoctor Diagnostics", "passed": False, "message": "Database access failure"}],
    }

    with patch("tools.notification_tool.show_notification", return_value={"status": "SUCCESS"}):
        with patch("tools.web_automation.email_client", return_value={"status": "SUCCESS"}) as mock_email:
            alert_info = send_health_alert(mock_result)
            assert "smtp_email" in alert_info["channels"]
            mock_email.assert_called_once()
            call_kwargs = mock_email.call_args[1]
            assert call_kwargs["to_email"] == "operator@example.com"
            assert "System Health Degraded" in call_kwargs["subject"]


def test_save_and_get_health_history(tmp_path):
    """Verifies health history JSON persistence and rolling retention."""
    hist_file = tmp_path / "test_history.json"

    for i in range(10):
        entry = {
            "timestamp": f"2026-09-18 08:0{i}:00 UTC",
            "healthy": i % 2 == 0,
            "passed_checks": 5 if i % 2 == 0 else 4,
            "total_checks": 5,
            "failing_checks": [] if i % 2 == 0 else ["Disk Capacity"],
            "error_count_24h": 0,
            "free_c_gb": 10.0,
            "alert_dispatched": i % 2 != 0,
        }
        save_health_history(entry, history_file=hist_file, max_history=5)

    loaded = get_health_history(limit=7, history_file=hist_file)
    assert len(loaded) == 5  # capped by max_history=5
    # Latest should be index 9
    assert loaded[0]["timestamp"] == "2026-09-18 08:09:00 UTC"


def test_format_health_report_output():
    """Verifies format_health_report generates clean structured output."""
    mock_result = {
        "timestamp": "2026-09-18 08:00:00 UTC",
        "healthy": True,
        "total_checks": 5,
        "passed_checks": 5,
        "failed_count": 0,
        "failing_checks": [],
        "checks": [
            {"name": "SystemDoctor Diagnostics", "passed": True, "message": "9/9 passed"},
            {"name": "24h Error Rate", "passed": True, "message": "0 errors"},
            {"name": "Disk Capacity", "passed": True, "message": "13.2 GB free"},
            {"name": "MCP Server Connectivity", "passed": True, "message": "3/3 online"},
            {"name": "Proactive Task Scheduler", "passed": True, "message": "6 tasks"},
        ],
        "alert_dispatched": False,
    }

    report = format_health_report(mock_result)
    assert "ORVIX SPHERE DAILY HEALTH CHECK REPORT" in report
    assert "[✓] ALL SYSTEMS HEALTHY" in report
    assert "PASSED (5/5 checks verified)" in report
    assert "[✓] SystemDoctor Diagnostics" in report


def test_format_history_table():
    """Verifies format_history_table generates aligned tabular digest."""
    history = [
        {
            "timestamp": "2026-09-18 08:00:00 UTC",
            "healthy": True,
            "passed_checks": 5,
            "total_checks": 5,
            "error_count_24h": 0,
            "free_c_gb": 13.2,
            "alert_sent": False,
        },
        {
            "timestamp": "2026-09-17 08:00:00 UTC",
            "healthy": False,
            "passed_checks": 4,
            "total_checks": 5,
            "error_count_24h": 2,
            "free_c_gb": 13.0,
            "alert_sent": True,
        },
    ]

    table = format_history_table(history)
    assert "ORVIX SPHERE HEALTH CHECK HISTORY" in table
    assert "HEALTHY" in table
    assert "UNHEALTHY" in table
    assert "13.2 GB" in table
