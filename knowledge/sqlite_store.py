"""
SQLite Knowledge Store for P.H.A.S.S Sphere Knowledge Layer.
Provides persistent storage for structured facts, user-defined lists,
and long-term conversation logs.
"""

from __future__ import annotations
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class FactResult(dict):
    """
    Dual-interface dict representing a retrieved fact.
    Permits dictionary access (res['value'], res['status']),
    direct value equality (res == 'expected_value'), and boolean evaluation.
    """
    def __init__(self, key: str, value: Any, category: str = "general", status: str = "SUCCESS"):
        super().__init__(status=status, key=key, value=value, category=category)
        self.value = value

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, dict):
            return super().__eq__(other)
        return self.value == other

    def __str__(self) -> str:
        return str(self.value)


class ListResult(dict):
    """
    Dual-interface dict representing a retrieved list.
    Supports both dict access (res['items'], res['status'], res['count'])
    and list iteration/indexing (for item in res: ..., len(res), res[0]).
    """
    def __init__(self, list_name: str, items: List[Dict[str, Any]], status: str = "SUCCESS"):
        super().__init__(status=status, list=list_name, items=items, count=len(items))
        self.items = items

    def __iter__(self):
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, key: Union[int, str]) -> Any:
        if isinstance(key, int):
            return self.items[key]
        return super().__getitem__(key)


class SearchFactsResult(dict):
    """
    Dual-interface dict representing facts search results.
    Supports dictionary access (res['results'], res['status'])
    and list iteration (for r in res: ...).
    """
    def __init__(self, keyword: str, results: List[Dict[str, Any]], status: str = "SUCCESS"):
        super().__init__(status=status, keyword=keyword, results=results, count=len(results))
        self.results = results

    def __iter__(self):
        return iter(self.results)

    def __len__(self) -> int:
        return len(self.results)

    def __getitem__(self, key: Union[int, str]) -> Any:
        if isinstance(key, int):
            return self.results[key]
        return super().__getitem__(key)


class KnowledgeStore:
    """
    Thread-safe SQLite persistent store for agent facts, user lists,
    and conversation history.
    """

    def __init__(self, db_path: str = "knowledge/agent_memory.db"):
        self.db_path = db_path
        db_dir = Path(self.db_path).parent
        if db_dir and not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_tables()

    def _init_tables(self):
        """Initializes tables for facts, lists, and conversation log."""
        with self._lock:
            cursor = self.conn.cursor()
            # Generic key-value facts store
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE,
                    value TEXT,
                    category TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # User custom lists (shopping, tasks, hardware inventory, etc.)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_lists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    list_name TEXT,
                    item TEXT,
                    quantity INTEGER DEFAULT 1,
                    notes TEXT,
                    completed BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Long-term conversation logging
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Proactive task execution log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_name TEXT,
                    triggered_at TIMESTAMP,
                    action_taken TEXT,
                    result TEXT,
                    approved_by_user BOOLEAN,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Proactive approval queue for dangerous/uncertain actions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS approval_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_name TEXT,
                    reason TEXT,
                    tool TEXT,
                    args TEXT,
                    status TEXT DEFAULT 'PENDING',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP
                )
            """)
            self.conn.commit()

    def store_fact(self, key: str, value: Any, category: str = "general") -> Dict[str, Any]:
        """Stores or updates a fact by its key."""
        try:
            serialized_value = json.dumps(value) if not isinstance(value, str) else value
            with self._lock:
                cursor = self.conn.cursor()
                cursor.execute("""
                    INSERT INTO facts (key, value, category, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        category = excluded.category,
                        updated_at = CURRENT_TIMESTAMP
                """, (key, serialized_value, category))
                self.conn.commit()
            return {"status": "SUCCESS", "key": key, "category": category}
        except Exception as e:
            return {"status": "FAILED", "key": key, "error": str(e)}

    def get_fact(self, key: str) -> Optional[FactResult]:
        """Retrieves a stored fact by its key."""
        try:
            with self._lock:
                cursor = self.conn.cursor()
                cursor.execute("SELECT value, category FROM facts WHERE key = ?", (key,))
                row = cursor.fetchone()

            if row:
                raw_val, category = row[0], row[1]
                try:
                    parsed_val = json.loads(raw_val)
                except (json.JSONDecodeError, TypeError):
                    parsed_val = raw_val
                return FactResult(key=key, value=parsed_val, category=category, status="SUCCESS")

            return None
        except Exception as e:
            return FactResult(key=key, value=None, status="FAILED")

    def add_to_list(self, list_name: str, item: str, quantity: int = 1, notes: str = "") -> Dict[str, Any]:
        """Adds an item to a named user list."""
        try:
            with self._lock:
                cursor = self.conn.cursor()
                cursor.execute("""
                    INSERT INTO user_lists (list_name, item, quantity, notes)
                    VALUES (?, ?, ?, ?)
                """, (list_name, item, quantity, notes))
                self.conn.commit()
            return {
                "status": "SUCCESS",
                "list": list_name,
                "item": item,
                "quantity": quantity,
                "notes": notes,
            }
        except Exception as e:
            return {"status": "FAILED", "list": list_name, "error": str(e)}

    def get_list(self, list_name: str) -> ListResult:
        """Retrieves all items from a named user list."""
        try:
            with self._lock:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT item, quantity, notes, completed
                    FROM user_lists WHERE list_name = ?
                """, (list_name,))
                rows = cursor.fetchall()

            items = [
                {
                    "item": r[0],
                    "quantity": r[1],
                    "notes": r[2] or "",
                    "completed": bool(r[3]),
                }
                for r in rows
            ]
            return ListResult(list_name=list_name, items=items, status="SUCCESS")
        except Exception as e:
            return ListResult(list_name=list_name, items=[], status="FAILED")

    def search_facts(self, keyword: str) -> SearchFactsResult:
        """Searches facts where key or value matches the keyword."""
        try:
            with self._lock:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT key, value, category FROM facts
                    WHERE key LIKE ? OR value LIKE ?
                """, (f"%{keyword}%", f"%{keyword}%"))
                rows = cursor.fetchall()

            results = []
            for r in rows:
                key, raw_val, cat = r[0], r[1], r[2]
                try:
                    val = json.loads(raw_val)
                except (json.JSONDecodeError, TypeError):
                    val = raw_val
                results.append({"key": key, "value": val, "category": cat})

            return SearchFactsResult(keyword=keyword, results=results, status="SUCCESS")
        except Exception as e:
            return SearchFactsResult(keyword=keyword, results=[], status="FAILED")

    def log_conversation(self, session_id: str, role: str, content: str) -> Dict[str, Any]:
        """Appends a conversational turn to long-term memory."""
        try:
            with self._lock:
                cursor = self.conn.cursor()
                cursor.execute("""
                    INSERT INTO conversation_log (session_id, role, content)
                    VALUES (?, ?, ?)
                """, (session_id, role, content))
                self.conn.commit()
            return {"status": "SUCCESS", "session_id": session_id, "role": role}
        except Exception as e:
            return {"status": "FAILED", "session_id": session_id, "error": str(e)}

    def get_conversation_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves past conversation turns for a given session."""
        try:
            with self._lock:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT role, content, timestamp FROM conversation_log
                    WHERE session_id = ?
                    ORDER BY id ASC LIMIT ?
                """, (session_id, limit))
                rows = cursor.fetchall()
            return [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in rows]
        except Exception as e:
            return []

    def log_task_execution(self, task_name: str, action: str, result: Any, approved: bool = True) -> int:
        """Logs an autonomous/scheduled task execution to task_log."""
        try:
            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            res_str = json.dumps(result) if not isinstance(result, str) else result
            act_str = json.dumps(action) if not isinstance(action, str) else action
            with self._lock:
                cursor = self.conn.cursor()
                cursor.execute("""
                    INSERT INTO task_log (task_name, triggered_at, action_taken, result, approved_by_user, timestamp)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (task_name, now_iso, act_str, res_str, 1 if approved else 0))
                self.conn.commit()
                return cursor.lastrowid or 0
        except Exception:
            return -1

    def queue_approval(self, action_name: str, reason: str, tool: str, args: Any) -> int:
        """Queues an action requiring explicit operator review and returns queue ID."""
        try:
            args_str = json.dumps(args) if not isinstance(args, str) else args
            with self._lock:
                cursor = self.conn.cursor()
                cursor.execute("""
                    INSERT INTO approval_queue (action_name, reason, tool, args, status, created_at)
                    VALUES (?, ?, ?, ?, 'PENDING', CURRENT_TIMESTAMP)
                """, (action_name, reason, tool, args_str))
                self.conn.commit()
                return cursor.lastrowid or 0
        except Exception:
            return -1

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Retrieves all pending actions awaiting operator approval."""
        try:
            with self._lock:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT id, action_name, reason, tool, args, status, created_at
                    FROM approval_queue
                    WHERE status = 'PENDING'
                    ORDER BY id ASC
                """)
                rows = cursor.fetchall()
            res = []
            for r in rows:
                try:
                    parsed_args = json.loads(r[4])
                except Exception:
                    parsed_args = r[4]
                res.append({
                    "id": r[0],
                    "action_name": r[1],
                    "reason": r[2],
                    "tool": r[3],
                    "args": parsed_args,
                    "status": r[5],
                    "created_at": r[6],
                })
            return res
        except Exception:
            return []

    def resolve_approval(self, action_id: int, approve: bool) -> bool:
        """Marks a pending action as APPROVED or REJECTED."""
        try:
            new_status = "APPROVED" if approve else "REJECTED"
            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            with self._lock:
                cursor = self.conn.cursor()
                cursor.execute("""
                    UPDATE approval_queue
                    SET status = ?, resolved_at = ?
                    WHERE id = ? AND status = 'PENDING'
                """, (new_status, now_iso, action_id))
                self.conn.commit()
                return cursor.rowcount > 0
        except Exception:
            return False

    def get_recent_task_logs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieves the most recent autonomous task execution entries."""
        try:
            with self._lock:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT id, task_name, triggered_at, action_taken, result, approved_by_user, timestamp
                    FROM task_log
                    ORDER BY id DESC LIMIT ?
                """, (limit,))
                rows = cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "task_name": r[1],
                    "triggered_at": r[2],
                    "action_taken": r[3],
                    "result": r[4],
                    "approved_by_user": bool(r[5]),
                    "timestamp": r[6],
                }
                for r in rows
            ]
        except Exception:
            return []

    def close(self):
        """Closes the underlying SQLite connection."""
        with self._lock:
            try:
                self.conn.close()
            except Exception:
                pass
