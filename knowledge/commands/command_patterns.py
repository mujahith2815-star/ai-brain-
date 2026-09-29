"""
Command Patterns & Sequence Logging for Layer 3 Learned Patterns.
Maintains execution sequences in command_sequence_log and promotes repeating
successful workflows into high-performance multi-command patterns.
"""

import json
import os
import re
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "agent_memory.db")
)
_LOCK = threading.RLock()


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_patterns_db() -> None:
    """Initializes command_patterns and command_sequence_log tables."""
    with _LOCK:
        with _get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS command_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    command_chain TEXT NOT NULL,
                    shell TEXT DEFAULT 'powershell',
                    success_count INTEGER DEFAULT 0,
                    fail_count INTEGER DEFAULT 0,
                    last_used TIMESTAMP,
                    tags TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS command_sequence_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_description TEXT NOT NULL,
                    commands_run TEXT NOT NULL,
                    final_success BOOLEAN,
                    duration_ms INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pat_name ON command_patterns(pattern_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_seq_task ON command_sequence_log(task_description)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_seq_success ON command_sequence_log(final_success)")
            conn.commit()


# Auto-initialize tables
init_patterns_db()


def log_sequence(
    task_desc: str,
    commands: List[Any],
    success: bool,
    duration_ms: int = 0
) -> int:
    """
    Logs an executed command sequence in command_sequence_log.
    Returns the inserted sequence row ID.
    """
    clean_desc = task_desc.strip()
    chain_json = json.dumps(commands)
    with _LOCK:
        with _get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO command_sequence_log (task_description, commands_run, final_success, duration_ms)
                VALUES (?, ?, ?, ?)
            """, (clean_desc, chain_json, 1 if success else 0, duration_ms))
            conn.commit()
            return cur.lastrowid


def promote_to_pattern(sequence_id: int) -> Optional[Dict[str, Any]]:
    """
    Promotes a logged sequence into a reusable command pattern in command_patterns.
    If a pattern for the same name/task already exists, increments its success count.
    """
    with _LOCK:
        with _get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM command_sequence_log WHERE id = ?", (sequence_id,))
            seq = cur.fetchone()
            if not seq:
                return None

            task_desc = seq["task_description"]
            raw_cmds = json.loads(seq["commands_run"])
            shell = "powershell"

            # Derive clean pattern name
            clean_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", task_desc.lower()).strip("_")
            if len(clean_name) > 60:
                clean_name = clean_name[:60]
            if not clean_name:
                clean_name = f"pattern_{sequence_id}"

            # Format chain
            chain_list = []
            if isinstance(raw_cmds, list):
                for c in raw_cmds:
                    if isinstance(c, dict):
                        chain_list.append(c.get("cmd") or c.get("command") or str(c))
                    else:
                        chain_list.append(str(c))
            else:
                chain_list = [str(raw_cmds)]

            chain_json = json.dumps(chain_list)
            now = datetime.now(timezone.utc).isoformat()
            tags_str = ",".join(re.findall(r"\w+", task_desc.lower()))

            # Count actual successful runs for this task
            cur.execute("""
                SELECT COUNT(*) FROM command_sequence_log
                WHERE LOWER(TRIM(task_description)) = LOWER(TRIM(?)) AND final_success = 1
            """, (task_desc,))
            actual_count = cur.fetchone()[0]
            init_success = max(1, actual_count)

            cur.execute("""
                INSERT INTO command_patterns (pattern_name, description, command_chain, shell, success_count, fail_count, last_used, tags)
                VALUES (?, ?, ?, ?, ?, 0, ?, ?)
                ON CONFLICT(pattern_name) DO UPDATE SET
                    command_chain = excluded.command_chain,
                    success_count = MAX(command_patterns.success_count + 1, excluded.success_count),
                    last_used = excluded.last_used,
                    tags = excluded.tags
            """, (clean_name, task_desc, chain_json, shell, init_success, now, tags_str))
            conn.commit()

            cur.execute("SELECT * FROM command_patterns WHERE pattern_name = ?", (clean_name,))
            row = cur.fetchone()
            if row:
                res = dict(row)
                res["command_chain"] = json.loads(res["command_chain"])
                return res
    return None


def get_all_patterns() -> List[Dict[str, Any]]:
    """Returns all promoted command patterns."""
    with _LOCK:
        with _get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM command_patterns ORDER BY success_count DESC, last_used DESC")
            results = []
            for r in cur.fetchall():
                d = dict(r)
                try:
                    d["command_chain"] = json.loads(d["command_chain"])
                except Exception:
                    pass
                results.append(d)
            return results


def get_pattern_by_name(pattern_name: str) -> Optional[Dict[str, Any]]:
    """Retrieves a pattern by exact or normalized name."""
    clean = pattern_name.strip()
    with _LOCK:
        with _get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM command_patterns WHERE LOWER(pattern_name) = LOWER(?)", (clean,))
            r = cur.fetchone()
            if r:
                d = dict(r)
                try:
                    d["command_chain"] = json.loads(d["command_chain"])
                except Exception:
                    pass
                return d
    return None


def get_similar_patterns(task_desc: str, limit: int = 5, vector_store: Any = None) -> List[Dict[str, Any]]:
    """
    Searches learned patterns for ones matching task_desc.
    Uses token scoring or vector retrieval if vector_store is provided.
    """
    tokens = re.findall(r"\w+", task_desc.lower())
    patterns = get_all_patterns()
    if not patterns:
        return []

    scored = []
    for pat in patterns:
        score = 0.0
        pname = pat.get("pattern_name", "").lower()
        pdesc = pat.get("description", "").lower()
        ptags = pat.get("tags", "").lower()

        for t in tokens:
            if t in pname:
                score += 5.0
            if t in pdesc:
                score += 3.0
            if t in ptags:
                score += 2.0

        if score > 0.0:
            # Factor in success count
            score += min(pat.get("success_count", 1) * 0.5, 5.0)
            scored.append((score, pat))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:limit]]


def suggest_chain(task_desc: str) -> Optional[List[str]]:
    """
    Recommends the best matching command sequence chain for a task description.
    """
    matches = get_similar_patterns(task_desc, limit=1)
    if matches:
        chain = matches[0].get("command_chain")
        if isinstance(chain, list):
            return chain
        elif isinstance(chain, str):
            try:
                return json.loads(chain)
            except Exception:
                return [chain]
    return None


def record_pattern_usage(pattern_name: str, success: bool = True) -> bool:
    """Updates pattern execution statistics."""
    now = datetime.now(timezone.utc).isoformat()
    with _LOCK:
        with _get_connection() as conn:
            cur = conn.cursor()
            if success:
                cur.execute("""
                    UPDATE command_patterns
                    SET success_count = success_count + 1, last_used = ?
                    WHERE LOWER(pattern_name) = LOWER(?)
                """, (now, pattern_name.strip()))
            else:
                cur.execute("""
                    UPDATE command_patterns
                    SET fail_count = fail_count + 1, last_used = ?
                    WHERE LOWER(pattern_name) = LOWER(?)
                """, (now, pattern_name.strip()))
            conn.commit()
            return cur.rowcount > 0
