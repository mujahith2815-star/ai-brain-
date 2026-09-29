"""
Command Execution History and SQLite Persistence for Orvix Universal Control.
Records every executed terminal command, exit status, duration, stdout/stderr snippets,
and error classification to power the self-learning feedback loop.
"""

import os
import sqlite3
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "agent_memory.db")
)
_LOCK = threading.RLock()


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_command_history_db() -> None:
    """Creates the command_history table if it doesn't already exist."""
    with _LOCK:
        with _get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS command_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command TEXT NOT NULL,
                    shell TEXT NOT NULL,
                    working_dir TEXT,
                    exit_code INTEGER,
                    stdout TEXT,
                    stderr TEXT,
                    execution_time_ms REAL,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN,
                    user_feedback TEXT,
                    error_category TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cmd_executed_at ON command_history(executed_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cmd_success ON command_history(success)")
            conn.commit()


def classify_error(stderr: str, exit_code: int) -> Optional[str]:
    """Infers high-level error category from stderr message and exit code."""
    if exit_code == 0:
        return None
    err_low = (stderr or "").lower()
    if "not recognized" in err_low or "command not found" in err_low or "not found" in err_low:
        return "not_found"
    if "permission denied" in err_low or "access is denied" in err_low or "unauthorized" in err_low:
        return "permission_denied"
    if "syntax error" in err_low or "unexpected token" in err_low or "invalid argument" in err_low:
        return "syntax_error"
    if "timed out" in err_low or "timeout" in err_low:
        return "timeout"
    if "no such file or directory" in err_low or "cannot find path" in err_low:
        return "path_not_found"
    return "runtime_error"


def log_command(
    command: str,
    shell: str,
    working_dir: str,
    exit_code: int,
    stdout: str,
    stderr: str,
    execution_time_ms: float,
    user_feedback: Optional[str] = None,
) -> int:
    """Logs a command execution event to SQLite. Returns inserted row ID."""
    init_command_history_db()
    success = exit_code == 0
    error_cat = classify_error(stderr, exit_code)

    # Trim stored stdout/stderr to 4KB max to keep db lightweight
    stdout_trimmed = (stdout or "")[:4096]
    stderr_trimmed = (stderr or "")[:4096]

    with _LOCK:
        with _get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO command_history (
                    command, shell, working_dir, exit_code,
                    stdout, stderr, execution_time_ms,
                    executed_at, success, user_feedback, error_category
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                command, shell, working_dir, exit_code,
                stdout_trimmed, stderr_trimmed, execution_time_ms,
                datetime.now().isoformat(), success, user_feedback, error_cat
            ))
            conn.commit()
            return cursor.lastrowid


def get_history(
    limit: int = 50,
    shell: Optional[str] = None,
    success_only: bool = False,
) -> List[Dict[str, Any]]:
    """Retrieves recent command history records."""
    init_command_history_db()
    query = "SELECT * FROM command_history WHERE 1=1"
    params: List[Any] = []

    if shell:
        query += " AND shell = ?"
        params.append(shell)
    if success_only:
        query += " AND success = 1"

    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with _LOCK:
        with _get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]


def get_most_used_commands(limit: int = 10) -> List[Dict[str, Any]]:
    """Returns the most frequently executed command patterns."""
    init_command_history_db()
    with _LOCK:
        with _get_connection() as conn:
            rows = conn.execute("""
                SELECT command, COUNT(*) as count,
                       SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
                       AVG(execution_time_ms) as avg_ms
                FROM command_history
                GROUP BY command
                ORDER BY count DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]


def get_failed_commands(limit: int = 10) -> List[Dict[str, Any]]:
    """Returns recent failed commands with error categories."""
    init_command_history_db()
    with _LOCK:
        with _get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM command_history
                WHERE success = 0
                ORDER BY id DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]


def get_success_rate() -> Dict[str, Any]:
    """Computes overall execution statistics."""
    init_command_history_db()
    with _LOCK:
        with _get_connection() as conn:
            row = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed,
                    AVG(execution_time_ms) as avg_duration_ms
                FROM command_history
            """).fetchone()
            total = row["total"] or 0
            successful = row["successful"] or 0
            rate = round((successful / total * 100), 2) if total > 0 else 0.0
            return {
                "total_executed": total,
                "successful": successful,
                "failed": row["failed"] or 0,
                "success_rate_percent": rate,
                "avg_duration_ms": round(row["avg_duration_ms"] or 0.0, 2),
            }


def record_feedback(command_id: int, feedback: str) -> bool:
    """Records user feedback ('thumbs_up', 'thumbs_down', 'verified') for a command."""
    init_command_history_db()
    with _LOCK:
        with _get_connection() as conn:
            cursor = conn.execute("""
                UPDATE command_history
                SET user_feedback = ?
                WHERE id = ?
            """, (feedback, command_id))
            conn.commit()
            return cursor.rowcount > 0
