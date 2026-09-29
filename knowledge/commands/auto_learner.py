"""
Autonomous Feedback Learner for Orvix Universal Control.
Analyzes command execution history to detect failures, discover successful alternatives,
learn custom user command patterns, and index them into persistent knowledge.
"""

import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from .command_history import get_history, get_failed_commands, get_most_used_commands
from .load_commands import get_command_by_name

LEARNED_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "learned_commands.json")
)

logger = logging.getLogger("orvix.knowledge.commands.auto_learner")
_LEARNER_THREAD: Optional[threading.Thread] = None
_STOP_EVENT = threading.Event()
_LOCK = threading.RLock()


def load_learned_commands() -> List[Dict[str, Any]]:
    """Loads previously discovered/learned command patterns."""
    if not os.path.exists(LEARNED_FILE):
        return []
    try:
        with open(LEARNED_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning(f"Failed to read {LEARNED_FILE}: {e}")
        return []


def save_learned_commands(commands: List[Dict[str, Any]]) -> None:
    """Saves learned commands to disk atomically."""
    with _LOCK:
        temp_path = LEARNED_FILE + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(commands, f, indent=2, ensure_ascii=False)
        try:
            os.replace(temp_path, LEARNED_FILE)
        except Exception:
            if os.path.exists(LEARNED_FILE):
                os.remove(LEARNED_FILE)
            os.rename(temp_path, LEARNED_FILE)


def learn_from_history(vector_store: Optional[Any] = None) -> Dict[str, Any]:
    """
    Analyzes command execution history to extract new command patterns and failure-recovery pairs.
    Returns summary of new commands learned.
    """
    history = get_history(limit=200)
    if not history:
        return {"status": "no_history", "learned_count": 0}

    existing_learned = load_learned_commands()
    learned_names = {c.get("name", "").lower() for c in existing_learned}
    new_learned: List[Dict[str, Any]] = []

    # 1. Identify successful custom commands executed multiple times that aren't in KB
    most_used = get_most_used_commands(limit=30)
    for row in most_used:
        cmd_str = row.get("command", "").strip()
        cmd_head = cmd_str.split()[0].lower() if cmd_str.split() else ""
        if not cmd_head or len(cmd_head) < 2:
            continue

        # Check if known in standard datasets
        if get_command_by_name(cmd_head) is None and cmd_head not in learned_names:
            success_count = row.get("successes", 0)
            if success_count >= 2:  # Proven reliable pattern
                learned_entry = {
                    "name": cmd_head,
                    "shell": "auto-detected",
                    "category": "custom_learned",
                    "description": f"Learned command pattern '{cmd_head}' discovered from reliable execution history.",
                    "syntax": cmd_str,
                    "examples": [{"cmd": cmd_str, "desc": "Auto-recorded execution"}],
                    "safety": "caution",
                    "is_destructive": False,
                    "requires_elevation": False,
                    "tags": ["learned", "auto-discovered", cmd_head],
                    "first_learned": datetime.now().isoformat(),
                    "times_executed": row.get("count", 0),
                    "success_count": success_count,
                }
                existing_learned.append(learned_entry)
                learned_names.add(cmd_head)
                new_learned.append(learned_entry)

    # 2. Save newly learned commands if any
    if new_learned:
        save_learned_commands(existing_learned)
        logger.info(f"Learned {len(new_learned)} new command patterns from history.")

        # Index into VectorStore if available
        if vector_store:
            docs = []
            for c in new_learned:
                docs.append({
                    "text": f"Learned Command: {c['name']}\nSyntax: {c['syntax']}\nDescription: {c['description']}",
                    "source": f"learned/{c['name']}",
                })
            if hasattr(vector_store, "add_documents"):
                vector_store.add_documents(docs)

    return {
        "status": "success",
        "total_learned": len(existing_learned),
        "newly_learned": len(new_learned),
        "new_commands": [c["name"] for c in new_learned],
    }


def _learner_loop(interval: int) -> None:
    while not _STOP_EVENT.is_set():
        try:
            learn_from_history()
        except Exception as e:
            logger.error(f"Auto-learner loop error: {e}")
        _STOP_EVENT.wait(timeout=interval)


def start_background_learner(interval_seconds: int = 300) -> None:
    """Starts background learning thread."""
    global _LEARNER_THREAD
    if _LEARNER_THREAD and _LEARNER_THREAD.is_alive():
        return
    _STOP_EVENT.clear()
    _LEARNER_THREAD = threading.Thread(
        target=_learner_loop,
        args=(interval_seconds,),
        daemon=True,
        name="OrvixAutoLearner",
    )
    _LEARNER_THREAD.start()
    logger.info("Orvix autonomous command learner thread started.")


def stop_background_learner() -> None:
    """Stops background learning thread."""
    global _LEARNER_THREAD
    _STOP_EVENT.set()
    if _LEARNER_THREAD and _LEARNER_THREAD.is_alive():
        _LEARNER_THREAD.join(timeout=2.0)
    _LEARNER_THREAD = None
