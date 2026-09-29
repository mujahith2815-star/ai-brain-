"""
Error Logger for Orvix Sphere.
Provides persistent SQLite storage at logs/errors.db, deduplication by
error hash (type + message), context capture, and copy-paste-ready bug reports for Antigravity.
"""

from __future__ import annotations
import hashlib
import json
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class ErrorLogger:
    """Lightweight persistent SQLite error logger with deduplication and bug report formatting."""

    _instance: Optional[ErrorLogger] = None
    _lock = threading.Lock()

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = Path(db_path).resolve()
        else:
            base_dir = Path(__file__).resolve().parent.parent
            logs_dir = base_dir / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = logs_dir / "errors.db"

        self._local_lock = threading.Lock()
        self._init_db()

    @classmethod
    def get_instance(cls, db_path: Optional[str] = None) -> ErrorLogger:
        with cls._lock:
            if cls._instance is None:
                cls._instance = ErrorLogger(db_path=db_path)
            return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes the errors table in SQLite."""
        with self._local_lock:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS errors (
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
                conn.execute("CREATE INDEX IF NOT EXISTS idx_errors_last_seen ON errors(last_seen);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_errors_count ON errors(count);")
                conn.commit()

    @staticmethod
    def compute_hash(error_type: str, error_message: str) -> str:
        """Computes deterministic 16-char sha256 hash from error type and message."""
        clean_type = str(error_type or "UnknownError").strip()
        clean_msg = str(error_message or "").strip()
        raw = f"{clean_type}:{clean_msg}".encode("utf-8", errors="replace")
        return hashlib.sha256(raw).hexdigest()[:16]

    def log(self, error_dict: Dict[str, Any]) -> int:
        """
        Logs an error. Deduplicates by (error_type + error_message hash).
        If seen before: increments count and updates last_seen.
        If new: inserts with count=1, first_seen=now, last_seen=now.
        Returns the error record id (int).
        """
        error_type = str(error_dict.get("error_type") or "Exception").strip()
        error_message = str(error_dict.get("error_message") or error_dict.get("error") or "Unknown error").strip()
        category = str(error_dict.get("category") or "GENERAL").strip().upper()
        source_file = error_dict.get("source_file") or ""
        function_name = error_dict.get("function_name") or ""
        tb = error_dict.get("traceback") or ""
        ctx = error_dict.get("context") or error_dict.get("context_json") or {}
        if isinstance(ctx, dict):
            ctx_str = json.dumps(ctx, default=str)
        elif isinstance(ctx, str):
            ctx_str = ctx
        else:
            ctx_str = "{}"

        err_hash = self.compute_hash(error_type, error_message)
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        with self._local_lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, count FROM errors WHERE error_hash = ?;",
                    (err_hash,),
                )
                row = cursor.fetchone()

                if row:
                    error_id = row["id"]
                    new_count = row["count"] + 1
                    cursor.execute(
                        """
                        UPDATE errors
                        SET count = ?,
                            last_seen = ?,
                            traceback = COALESCE(NULLIF(?, ''), traceback),
                            context_json = COALESCE(NULLIF(?, '{}'), context_json),
                            source_file = COALESCE(NULLIF(?, ''), source_file),
                            function_name = COALESCE(NULLIF(?, ''), function_name)
                        WHERE id = ?;
                        """,
                        (new_count, now_str, tb, ctx_str, source_file, function_name, error_id),
                    )
                    conn.commit()
                    return error_id
                else:
                    cursor.execute(
                        """
                        INSERT INTO errors (
                            timestamp, category, source_file, function_name,
                            error_type, error_message, traceback, context_json,
                            count, first_seen, last_seen, error_hash
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?);
                        """,
                        (
                            now_str,
                            category,
                            source_file,
                            function_name,
                            error_type,
                            error_message,
                            tb,
                            ctx_str,
                            now_str,
                            now_str,
                            err_hash,
                        ),
                    )
                    conn.commit()
                    return cursor.lastrowid

    def get_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Returns list of recent error records ordered by last_seen DESC."""
        with self._local_lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, timestamp, category, source_file, function_name,
                           error_type, error_message, traceback, context_json,
                           count, first_seen, last_seen, error_hash
                    FROM errors
                    ORDER BY id DESC
                    LIMIT ?;
                    """,
                    (limit,),
                )
                rows = cursor.fetchall()
                results = []
                for r in rows:
                    d = dict(r)
                    try:
                        d["context"] = json.loads(d["context_json"]) if d.get("context_json") else {}
                    except Exception:
                        d["context"] = {}
                    results.append(d)
                return results

    def get_top_errors(self, days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
        """Returns most frequent errors ordered by count DESC."""
        with self._local_lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if days > 0:
                    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute(
                        """
                        SELECT id, timestamp, category, source_file, function_name,
                               error_type, error_message, traceback, context_json,
                               count, first_seen, last_seen, error_hash
                        FROM errors
                        WHERE last_seen >= ?
                        ORDER BY count DESC, id DESC
                        LIMIT ?;
                        """,
                        (cutoff, limit),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT id, timestamp, category, source_file, function_name,
                               error_type, error_message, traceback, context_json,
                               count, first_seen, last_seen, error_hash
                        FROM errors
                        ORDER BY count DESC, id DESC
                        LIMIT ?;
                        """,
                        (limit,),
                    )
                rows = cursor.fetchall()
                results = []
                for r in rows:
                    d = dict(r)
                    try:
                        d["context"] = json.loads(d["context_json"]) if d.get("context_json") else {}
                    except Exception:
                        d["context"] = {}
                    results.append(d)
                return results

    def get_by_id(self, error_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves a single error record by primary key."""
        with self._local_lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, timestamp, category, source_file, function_name,
                           error_type, error_message, traceback, context_json,
                           count, first_seen, last_seen, error_hash
                    FROM errors
                    WHERE id = ?;
                    """,
                    (error_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                d = dict(row)
                try:
                    d["context"] = json.loads(d["context_json"]) if d.get("context_json") else {}
                except Exception:
                    d["context"] = {}
                return d

    def clear_old(self, days: int = 30) -> int:
        """Deletes error records where last_seen is older than days."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        with self._local_lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM errors WHERE last_seen < ?;", (cutoff,))
                deleted = cursor.rowcount
                conn.commit()
                return deleted

    def export_markdown(self, output_path: Optional[str] = None) -> str:
        """Exports an error digest markdown file formatted for Antigravity."""
        if output_path:
            out_p = Path(output_path).resolve()
        else:
            base_dir = Path(__file__).resolve().parent.parent
            logs_dir = base_dir / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            out_p = logs_dir / "error_digest.md"

        errors = self.get_top_errors(days=30, limit=20)
        recent = self.get_recent(limit=10)

        lines = [
            "# Orvix Sphere — Error Digest for Antigravity",
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n",
            "This document summarizes runtime and tool errors captured by Orvix Sphere.",
            "Paste specific error sections into Antigravity with: *\"Fix this bug and add a test.\"*\n",
            "## Top Recurring Errors (Last 30 Days)\n",
            "| ID | Count | Category | Error Type | Message | Last Seen |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        for e in errors:
            msg = e['error_message'].replace("|", "\\|").replace("\n", " ")[:60]
            lines.append(
                f"| {e['id']} | {e['count']} | {e['category']} | {e['error_type']} | {msg} | {e['last_seen']} |"
            )

        lines.append("\n## Detailed Bug Reports\n")
        for e in recent:
            report_box = self.format_bug_report(e["id"])
            lines.append(f"### Error #{e['id']}: {e['error_type']}\n")
            lines.append("```text")
            lines.append(report_box)
            lines.append("```\n")

        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text("\n".join(lines), encoding="utf-8")
        return str(out_p)

    def format_bug_report(self, error_id_or_dict: Any) -> str:
        """
        Formats a copy-paste-ready bug report in an exact boxed format.
        """
        if isinstance(error_id_or_dict, dict):
            err = error_id_or_dict
        else:
            err = self.get_by_id(int(error_id_or_dict))

        if not err:
            return f"Error ID {error_id_or_dict} not found."

        ctx = err.get("context") or {}
        if isinstance(ctx, str):
            try:
                ctx = json.loads(ctx)
            except Exception:
                ctx = {}

        err_id = err.get("id", "N/A")
        ts = err.get("timestamp") or err.get("last_seen", "N/A")
        cat = err.get("category", "GENERAL")
        src = err.get("source_file") or "unknown"
        if err.get("function_name"):
            src = f"{src}:{err['function_name']}"
        errmsg = err.get("error_message") or err.get("error_type", "Unknown Error")
        tb = err.get("traceback") or "No traceback recorded."

        tool_name = ctx.get("tool") or ctx.get("tool_name", "N/A")
        args_str = json.dumps(ctx.get("args") or ctx.get("parameters") or {}, default=str)
        last_tools = ctx.get("last_3_tools") or ctx.get("recent_tools") or [tool_name] if tool_name != "N/A" else []
        reproduce_cmd = ctx.get("reproduce") or ctx.get("command") or ctx.get("user_query") or "Run Orvix session"

        inner_width = 61
        hr = "─" * inner_width

        box_lines = [
            f"┌{hr}┐",
            f"│ BUG REPORT — ready to paste into Antigravity".ljust(inner_width + 1) + "│",
            f"├{hr}┤",
            f"│ ERROR ID:    {err_id}".ljust(inner_width + 1) + "│",
            f"│ TIMESTAMP:   {ts}".ljust(inner_width + 1) + "│",
            f"│ CATEGORY:    {cat}".ljust(inner_width + 1) + "│",
            f"│ SOURCE:      {src}".ljust(inner_width + 1) + "│",
            f"│ COUNT:       {err.get('count', 1)}".ljust(inner_width + 1) + "│",
            f"│".ljust(inner_width + 1) + "│",
            f"│ ERROR: {errmsg[:inner_width - 10]}".ljust(inner_width + 1) + "│",
            f"│".ljust(inner_width + 1) + "│",
            f"│ CONTEXT:".ljust(inner_width + 1) + "│",
            f"│   tool: {tool_name}".ljust(inner_width + 1) + "│",
            f"│   args: {args_str[:inner_width - 12]}".ljust(inner_width + 1) + "│",
            f"│   recent_tools: {str(last_tools)[:inner_width - 20]}".ljust(inner_width + 1) + "│",
            f"│".ljust(inner_width + 1) + "│",
            f"│ TRACEBACK:".ljust(inner_width + 1) + "│",
        ]

        # Add formatted traceback lines
        tb_clean_lines = [l.strip() for l in tb.strip().splitlines() if l.strip()]
        if not tb_clean_lines:
            box_lines.append(f"│   (none)".ljust(inner_width + 1) + "│")
        else:
            for l in tb_clean_lines[-6:]:
                box_lines.append(f"│   {l[:inner_width - 6]}".ljust(inner_width + 1) + "│")

        box_lines.extend([
            f"│".ljust(inner_width + 1) + "│",
            f"│ REPRODUCE:".ljust(inner_width + 1) + "│",
            f"│   Run: python run_model_chat.py".ljust(inner_width + 1) + "│",
            f"│   Command: {str(reproduce_cmd)[:inner_width - 15]}".ljust(inner_width + 1) + "│",
            f"│".ljust(inner_width + 1) + "│",
            f"│ SUGGESTED ACTION:".ljust(inner_width + 1) + "│",
            f"│   Paste this entire report into Antigravity.".ljust(inner_width + 1) + "│",
            f"│   Ask: \"Fix this bug and add a test.\"".ljust(inner_width + 1) + "│",
            f"└{hr}┘",
        ])

        return "\n".join(box_lines)


# Default module instance
error_logger = ErrorLogger.get_instance()
