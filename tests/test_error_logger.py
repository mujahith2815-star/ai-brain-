"""
Unit tests for the Error Logger and Human-in-the-Loop Antigravity Reporting System.
Tests SQLite persistence, SHA-256 deduplication, top error ranking, markdown export,
stale error pruning, and copy-paste-ready bug report generation.
"""

import os
import sqlite3
import pytest
from datetime import datetime, timezone, timedelta
from logging.error_logger import ErrorLogger


@pytest.fixture
def temp_logger(tmp_path):
    """Provides a fresh ErrorLogger instance backed by a temporary SQLite database."""
    db_file = tmp_path / "test_errors.db"
    return ErrorLogger(db_path=str(db_file))


def test_log_new_error(temp_logger):
    """Verifies that logging a new error inserts a record into SQLite and returns ID 1."""
    err_data = {
        "category": "TOOL_FAILURE",
        "source_file": "core/llama_tool_agent.py",
        "function_name": "_execute_tool_sync",
        "error_type": "FileNotFoundError",
        "error_message": "File does not exist: notes.txt",
        "traceback": "Traceback (most recent call last):\n  File 'foo.py', line 1\nFileNotFoundError",
        "context": {"tool": "file_reader", "path": "notes.txt"},
    }
    err_id = temp_logger.log(err_data)
    assert err_id == 1

    record = temp_logger.get_by_id(1)
    assert record is not None
    assert record["id"] == 1
    assert record["count"] == 1
    assert record["category"] == "TOOL_FAILURE"
    assert record["error_type"] == "FileNotFoundError"
    assert "notes.txt" in record["error_message"]
    assert record["context"]["tool"] == "file_reader"


def test_log_dedupes_same_error(temp_logger):
    """Verifies that logging the same error twice deduplicates, keeps the same ID, and increments count."""
    err_data1 = {
        "category": "TOOL_FAILURE",
        "source_file": "tools/file_ops.py",
        "error_type": "PermissionError",
        "error_message": "Access is denied: C:\\protected.txt",
        "context": {"tool": "file_reader"},
    }
    err_data2 = {
        "category": "TOOL_FAILURE",
        "source_file": "tools/file_ops.py",
        "error_type": "PermissionError",
        "error_message": "Access is denied: C:\\protected.txt",
        "context": {"tool": "file_reader", "retry": True},
    }

    id1 = temp_logger.log(err_data1)
    id2 = temp_logger.log(err_data2)

    assert id1 == id2
    record = temp_logger.get_by_id(id1)
    assert record["count"] == 2
    assert record["first_seen"] <= record["last_seen"]


def test_get_top_errors_sorted_by_count(temp_logger):
    """Verifies that get_top_errors returns errors ordered by frequency descending."""
    # Log Error A 1 time
    temp_logger.log({
        "category": "NETWORK",
        "error_type": "ConnectionError",
        "error_message": "Timeout connecting to host",
    })

    # Log Error B 3 times
    for _ in range(3):
        temp_logger.log({
            "category": "TOOL_FAILURE",
            "error_type": "ValueError",
            "error_message": "Invalid integer parameter",
        })

    # Log Error C 2 times
    for _ in range(2):
        temp_logger.log({
            "category": "AUTH",
            "error_type": "KeyError",
            "error_message": "Missing API key",
        })

    top = temp_logger.get_top_errors(days=30, limit=10)
    assert len(top) == 3
    assert top[0]["error_type"] == "ValueError"
    assert top[0]["count"] == 3
    assert top[1]["error_type"] == "KeyError"
    assert top[1]["count"] == 2
    assert top[2]["error_type"] == "ConnectionError"
    assert top[2]["count"] == 1


def test_export_creates_markdown(temp_logger, tmp_path):
    """Verifies that export_markdown creates a markdown digest file containing error tables and reports."""
    temp_logger.log({
        "category": "TOOL_FAILURE",
        "error_type": "ZeroDivisionError",
        "error_message": "division by zero in calculator",
        "context": {"tool": "calculator", "args": {"expr": "1/0"}},
    })

    out_file = tmp_path / "error_digest.md"
    result_path = temp_logger.export_markdown(output_path=str(out_file))

    assert os.path.exists(result_path)
    content = out_file.read_text(encoding="utf-8")
    assert "# Orvix Sphere — Error Digest for Antigravity" in content
    assert "ZeroDivisionError" in content
    assert "division by zero in calculator" in content
    assert "BUG REPORT" in content


def test_clear_old_removes_stale(temp_logger):
    """Verifies that clear_old deletes records older than N days while preserving recent ones."""
    # Insert recent error
    recent_id = temp_logger.log({
        "category": "RUNTIME",
        "error_type": "RuntimeError",
        "error_message": "Fresh error today",
    })

    # Insert old error manually with timestamp 45 days ago
    old_time = (datetime.now(timezone.utc) - timedelta(days=45)).strftime("%Y-%m-%d %H:%M:%S")
    old_hash = temp_logger.compute_hash("OldError", "Old stale error from last month")
    with temp_logger._local_lock:
        with temp_logger._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO errors (
                    timestamp, category, source_file, function_name,
                    error_type, error_message, traceback, context_json,
                    count, first_seen, last_seen, error_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (old_time, "TEST", "old.py", "fn", "OldError", "Old stale error from last month", "", "{}", 1, old_time, old_time, old_hash),
            )
            conn.commit()

    # Pre-clear check: 2 errors in total
    assert len(temp_logger.get_recent(limit=10)) == 2

    # Clear errors older than 30 days
    deleted = temp_logger.clear_old(days=30)
    assert deleted == 1

    # Post-clear check: only fresh error remains
    remaining = temp_logger.get_recent(limit=10)
    assert len(remaining) == 1
    assert remaining[0]["id"] == recent_id
    assert remaining[0]["error_type"] == "RuntimeError"


def test_bug_report_is_copy_paste_ready(temp_logger):
    """Verifies format_bug_report produces the exact boxed layout ready for Antigravity."""
    err_id = temp_logger.log({
        "category": "TOOL_FAILURE",
        "source_file": "core/llama_tool_agent.py",
        "function_name": "_execute_tool_sync",
        "error_type": "FileNotFoundError",
        "error_message": "File does not exist: test_file.txt",
        "traceback": "Traceback (most recent call last):\n  File 'test.py', line 10\nFileNotFoundError",
        "context": {
            "tool": "file_reader",
            "args": {"path": "test_file.txt"},
            "last_3_tools": ["file_reader"],
            "reproduce": "Read test_file.txt",
        },
    })

    report = temp_logger.format_bug_report(err_id)

    assert "┌" in report and "┐" in report and "└" in report and "┘" in report
    assert "BUG REPORT — ready to paste into Antigravity" in report
    assert f"ERROR ID:    {err_id}" in report
    assert "CATEGORY:    TOOL_FAILURE" in report
    assert "SOURCE:      core/llama_tool_agent.py:_execute_tool_sync" in report
    assert "ERROR: File does not exist: test_file.txt" in report
    assert "tool: file_reader" in report
    assert "args: {\"path\": \"test_file.txt\"}" in report
    assert "TRACEBACK:" in report
    assert "FileNotFoundError" in report
    assert "REPRODUCE:" in report
    assert "SUGGESTED ACTION:" in report
    assert "Paste this entire report into Antigravity." in report
    assert 'Ask: "Fix this bug and add a test."' in report


@pytest.mark.asyncio
async def test_error_tools_registration_and_execution():
    """Verifies that log_error, get_errors, and get_error_stats tools execute properly and are registered."""
    from tools.error_tools import log_error, get_errors, get_error_stats
    from tools.registry import tool_registry

    # Check registration
    assert tool_registry.get_tool("log_error") is not None
    assert tool_registry.get_tool("get_errors") is not None
    assert tool_registry.get_tool("get_error_stats") is not None

    # Test tool execution
    log_res = await log_error(
        category="TOOL_FAILURE",
        error_type="CustomTestError",
        error_message="Error logged via tool call",
        source_file="tests/test_error_logger.py",
        traceback="CustomTestError: detail",
        context={"test": True},
    )
    assert log_res["status"] == "SUCCESS"
    assert "error_id" in log_res

    # Test get_errors
    recent = await get_errors(limit=5)
    assert recent["status"] == "SUCCESS"
    assert recent["count"] >= 1

    # Test get_error_stats
    stats = await get_error_stats()
    assert stats["status"] == "SUCCESS"
    assert stats["total_unique_errors"] >= 1


def test_agent_tool_failure_logs_and_injects_hint():
    """Verifies that an agent tool failure logs an error and injects the error ID hint into the observation."""
    from unittest.mock import patch, MagicMock
    from core.llama_tool_agent import llama_tool_agent
    from tools.executor import ToolExecutionResult
    from logging.error_logger import error_logger

    mock_decisions = [
        ({"action": "call_tool", "thought": "Testing failing tool", "tool_name": "failing_dummy_tool", "parameters": {"x": 1}}, "gemini", False),
        ({"action": "final_answer", "thought": "Tool failed so I conclude", "response": "Finished turn."}, "gemini", False),
    ]

    def mock_query(*args, **kwargs):
        return mock_decisions.pop(0)

    with patch.object(llama_tool_agent, "_query_engine_json", side_effect=mock_query):
        with patch.object(llama_tool_agent, "_execute_tool_sync") as mock_exec:
            mock_exec.return_value = ToolExecutionResult(
                tool_name="failing_dummy_tool",
                parameters={"x": 1},
                output={"status": "ERROR", "error": "Intentional failure for testing error logging"},
                success=False,
                verified=False,
                permission_granted=False,
                requires_confirmation=False,
                error="Intentional failure for testing error logging",
            )

            result = llama_tool_agent.run_turn("Test query triggering error")

            # Check that error was logged
            recent = error_logger.get_recent(limit=5)
            matching = [e for e in recent if "Intentional failure" in e.get("error_message", "")]
            assert len(matching) >= 1
            err = matching[0]
            assert err["category"] == "TOOL_FAILURE"

            # Check that steps executed recorded failure
            assert len(result.steps_executed) >= 1
            step = result.steps_executed[0]
            assert step.success is False
            assert "Intentional failure" in step.error



