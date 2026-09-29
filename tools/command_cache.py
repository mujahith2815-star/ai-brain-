"""
Discovered Command Cache for Layer 2 Live Discovery.
Maintains an SQLite table in agent_memory.db to store thousands of OS-discovered
commands, executables, packages, and on-demand help documentation without bloating
the vector store.
"""

import os
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "knowledge", "agent_memory.db")
)
_LOCK = threading.RLock()


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_cache_db() -> None:
    """Initializes the discovered_commands SQLite table and indexes."""
    with _LOCK:
        with _get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS discovered_commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    shell TEXT,
                    source TEXT,
                    path TEXT,
                    help_text TEXT,
                    last_seen TIMESTAMP,
                    usage_count INTEGER DEFAULT 0,
                    is_favorite BOOLEAN DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_disc_name ON discovered_commands(name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_disc_source ON discovered_commands(source)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_disc_last_seen ON discovered_commands(last_seen)")
            conn.commit()


# Auto-initialize on import
init_cache_db()


def cache_command(
    name: str,
    shell: str = "powershell",
    source: str = "powershell",
    path: Optional[str] = None,
    help_text: Optional[str] = None,
) -> bool:
    """Inserts or updates a single discovered command in SQLite cache."""
    clean_name = name.strip()
    if not clean_name:
        return False
    now = datetime.now(timezone.utc).isoformat()
    with _LOCK:
        with _get_connection() as conn:
            conn.execute("""
                INSERT INTO discovered_commands (name, shell, source, path, help_text, last_seen, usage_count, is_favorite)
                VALUES (?, ?, ?, ?, ?, ?, 0, 0)
                ON CONFLICT(name) DO UPDATE SET
                    shell = excluded.shell,
                    source = excluded.source,
                    path = COALESCE(excluded.path, discovered_commands.path),
                    help_text = COALESCE(excluded.help_text, discovered_commands.help_text),
                    last_seen = excluded.last_seen
            """, (clean_name, shell, source, path, help_text, now))
            conn.commit()
    return True


def cache_commands_batch(commands: List[Dict[str, Any]]) -> int:
    """
    Inserts or updates a batch of discovered commands efficiently in a single transaction.
    Each item must have at least 'name', and optional 'shell', 'source', 'path', 'help_text'.
    """
    if not commands:
        return 0
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for c in commands:
        name = str(c.get("name", "")).strip()
        if not name:
            continue
        shell = c.get("shell", "powershell")
        source = c.get("source", "powershell")
        path = c.get("path")
        help_text = c.get("help_text")
        rows.append((name, shell, source, path, help_text, now))

    with _LOCK:
        with _get_connection() as conn:
            conn.executemany("""
                INSERT INTO discovered_commands (name, shell, source, path, help_text, last_seen, usage_count, is_favorite)
                VALUES (?, ?, ?, ?, ?, ?, 0, 0)
                ON CONFLICT(name) DO UPDATE SET
                    shell = excluded.shell,
                    source = excluded.source,
                    path = COALESCE(excluded.path, discovered_commands.path),
                    help_text = COALESCE(excluded.help_text, discovered_commands.help_text),
                    last_seen = excluded.last_seen
            """, rows)
            conn.commit()
    return len(rows)


def get_cached(name: str) -> Optional[Dict[str, Any]]:
    """Retrieves a cached command definition by name."""
    clean_name = name.strip()
    with _LOCK:
        with _get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM discovered_commands WHERE LOWER(name) = LOWER(?)", (clean_name,))
            row = cur.fetchone()
            if row:
                return dict(row)
    return None


def update_help_text(name: str, help_text: str) -> bool:
    """Updates the cached on-demand help text for a command."""
    with _LOCK:
        with _get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE discovered_commands
                SET help_text = ?, last_seen = ?
                WHERE LOWER(name) = LOWER(?)
            """, (help_text, datetime.now(timezone.utc).isoformat(), name.strip()))
            conn.commit()
            return cur.rowcount > 0


def increment_usage(name: str) -> None:
    """Increments the usage count for a discovered command."""
    with _LOCK:
        with _get_connection() as conn:
            conn.execute("""
                UPDATE discovered_commands
                SET usage_count = usage_count + 1, last_seen = ?
                WHERE LOWER(name) = LOWER(?)
            """, (datetime.now(timezone.utc).isoformat(), name.strip()))
            conn.commit()


def mark_favorite(name: str, is_favorite: bool = True) -> bool:
    """Marks or unmarks a command as favorite."""
    with _LOCK:
        with _get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE discovered_commands
                SET is_favorite = ?
                WHERE LOWER(name) = LOWER(?)
            """, (1 if is_favorite else 0, name.strip()))
            conn.commit()
            return cur.rowcount > 0


def list_by_source(source: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Lists cached commands filtered by origin source (e.g. powershell, cmd, pip, npm)."""
    with _LOCK:
        with _get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM discovered_commands
                WHERE LOWER(source) = LOWER(?)
                ORDER BY usage_count DESC, name ASC
                LIMIT ?
            """, (source.strip(), limit))
            return [dict(r) for r in cur.fetchall()]


def list_favorites() -> List[Dict[str, Any]]:
    """Returns list of favorite discovered commands."""
    with _LOCK:
        with _get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM discovered_commands WHERE is_favorite = 1 ORDER BY usage_count DESC, name ASC")
            return [dict(r) for r in cur.fetchall()]


def stale_commands(days: int = 30) -> List[Dict[str, Any]]:
    """Returns commands not seen in the system for more than specified days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with _LOCK:
        with _get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM discovered_commands WHERE last_seen < ? ORDER BY last_seen ASC", (cutoff,))
            return [dict(r) for r in cur.fetchall()]


def count_cached() -> Dict[str, Any]:
    """Returns total count and breakdown by source."""
    with _LOCK:
        with _get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM discovered_commands")
            total = cur.fetchone()[0]

            cur.execute("SELECT source, COUNT(*) as cnt FROM discovered_commands GROUP BY source")
            by_source = {row["source"]: row["cnt"] for row in cur.fetchall()}

    return {"total": total, "by_source": by_source}


def search_cached(keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Searches discovered commands by name or help text snippet."""
    q = f"%{keyword.strip().lower()}%"
    with _LOCK:
        with _get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM discovered_commands
                WHERE LOWER(name) LIKE ? OR LOWER(help_text) LIKE ?
                ORDER BY (LOWER(name) LIKE ?) DESC, usage_count DESC
                LIMIT ?
            """, (q, q, f"{keyword.strip().lower()}%", limit))
            return [dict(r) for r in cur.fetchall()]
