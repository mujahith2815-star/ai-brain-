"""
State Recovery System for P.H.A.S.S v10.0.
Saves session state (action list, board detected, recent messages) to
checkpoints/session_state.json every 10 seconds to protect against crashes.
On restart, detects interrupted tasks and prompts:
"I see we were programming an [board]. Would you like me to resume?"
"""

from __future__ import annotations
import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("phass.core.state_recovery")


class StateRecoveryManager:
    """
    Manages session state persistence and crash recovery.
    """
    _instance: Optional[StateRecoveryManager] = None

    def __init__(self, state_file: str = "checkpoints/session_state.json"):
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.current_state: Dict[str, Any] = {
            "task": "Idle",
            "actions": [],
            "board_detected": None,
            "recent_messages": [],
            "status": "idle",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._bg_thread: Optional[threading.Thread] = None

    @classmethod
    def get_instance(cls) -> StateRecoveryManager:
        if cls._instance is None:
            cls._instance = StateRecoveryManager()
        return cls._instance

    def update_task_state(
        self,
        task: str,
        actions: Optional[List[Dict[str, Any]]] = None,
        board_detected: Optional[Dict[str, Any]] = None,
        recent_messages: Optional[List[Dict[str, Any]]] = None,
        status: str = "in_progress",
    ):
        """Updates in-memory session state and immediately flushes to disk."""
        with self._lock:
            self.current_state["task"] = task
            if actions is not None:
                self.current_state["actions"] = actions
            if board_detected is not None:
                self.current_state["board_detected"] = board_detected
            if recent_messages is not None:
                self.current_state["recent_messages"] = recent_messages[-3:]
            self.current_state["status"] = status
            self.current_state["timestamp"] = datetime.now(timezone.utc).isoformat()

        self.save_to_disk()

    def record_message(self, role: str, content: str):
        """Records a recent user/assistant message (keeping last 3)."""
        with self._lock:
            msgs = self.current_state.get("recent_messages", [])
            msgs.append({"role": role, "content": content, "time": datetime.now().strftime("%H:%M:%S")})
            self.current_state["recent_messages"] = msgs[-3:]

    def save_to_disk(self):
        """Persists current state to checkpoints/session_state.json."""
        with self._lock:
            try:
                with open(self.state_file, "w", encoding="utf-8") as f:
                    json.dump(self.current_state, f, indent=2)
            except Exception as e:
                logger.warning(f"Failed to save session state: {e}")

    def load_from_disk(self) -> Optional[Dict[str, Any]]:
        """Loads state from checkpoints/session_state.json."""
        if not self.state_file.exists():
            return None
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            logger.warning(f"Failed to read session state: {e}")
        return None

    def check_pending_recovery(self) -> Optional[Dict[str, Any]]:
        """
        Checks if a previous crashed or interrupted task exists.
        Returns recovery metadata with human-friendly resume prompt if applicable.
        """
        saved = self.load_from_disk()
        if not saved:
            return None

        status = saved.get("status")
        task = saved.get("task", "")
        board_info = saved.get("board_detected") or {}
        board_name = board_info.get("board", "ESP32")

        if status == "in_progress" and task and task.lower() != "idle":
            if "program" in task.lower() or "flash" in task.lower():
                prompt = f"I see we were programming an {board_name}. Would you like me to resume?"
            else:
                prompt = f"I see we were working on: '{task}'. Would you like me to resume?"

            return {
                "recoverable": True,
                "task": task,
                "board": board_name,
                "actions": saved.get("actions", []),
                "recent_messages": saved.get("recent_messages", []),
                "prompt": prompt,
            }
        return None

    def mark_completed(self):
        """Marks current task as completed / idle."""
        self.update_task_state(task="Idle", status="completed")

    def start_autosave(self, interval_seconds: float = 10.0):
        """Starts 10-second periodic background autosave loop."""
        if self._bg_thread and self._bg_thread.is_alive():
            return

        def _loop():
            while not self._stop_event.is_set():
                time.sleep(interval_seconds)
                if not self._stop_event.is_set():
                    self.save_to_disk()

        self._stop_event.clear()
        self._bg_thread = threading.Thread(target=_loop, daemon=True)
        self._bg_thread.start()

    def stop_autosave(self):
        """Stops background autosave thread."""
        self._stop_event.set()


state_recovery_manager = StateRecoveryManager.get_instance()
