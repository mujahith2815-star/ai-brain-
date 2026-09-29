"""
Pattern Learner Background Worker for Layer 3 Learned Patterns.
Analyzes recorded command execution sequences in command_sequence_log.
When a successful sequence for a task is executed 3+ times, automatically
promotes it to a permanent command pattern in command_patterns and indexes it.
"""

import json
import logging
import os
import sqlite3
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from knowledge.commands.command_patterns import promote_to_pattern, get_all_patterns

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
PATTERN_LOG_FILE = os.path.join(LOGS_DIR, "pattern_learner.log")

logger = logging.getLogger("orvix.knowledge.commands.pattern_learner")
logger.setLevel(logging.INFO)
if not any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", "") == str(os.path.abspath(PATTERN_LOG_FILE)) for h in logger.handlers):
    fh = logging.FileHandler(PATTERN_LOG_FILE, encoding="utf-8")
    fh.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
    logger.addHandler(fh)

DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "agent_memory.db")
)


class PatternLearner:
    """
    Background worker that discovers repeating multi-command workflows and promotes them.
    """

    def __init__(self, interval_seconds: int = 300, vector_store: Any = None):
        self.interval = interval_seconds
        self.vector_store = vector_store
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def scan_and_promote(self) -> int:
        """
        Scans command_sequence_log for successful sequences repeated 3+ times.
        Promotes eligible sequences to command_patterns.
        Returns count of newly promoted or updated patterns.
        """
        promoted_count = 0
        if not os.path.exists(DB_PATH):
            return 0

        try:
            with sqlite3.connect(DB_PATH, timeout=10.0) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()

                # Find task descriptions with 3+ successful executions
                cur.execute("""
                    SELECT task_description, COUNT(*) as success_cnt, MAX(id) as latest_id
                    FROM command_sequence_log
                    WHERE final_success = 1
                    GROUP BY LOWER(TRIM(task_description))
                    HAVING success_cnt >= 3
                """)
                candidates = cur.fetchall()

                for cand in candidates:
                    task_desc = cand["task_description"]
                    latest_id = cand["latest_id"]
                    pattern = promote_to_pattern(latest_id)
                    if pattern:
                        promoted_count += 1
                        logger.info(
                            f"Promoted pattern '{pattern['pattern_name']}' for task '{task_desc}' "
                            f"({cand['success_cnt']} successful runs)"
                        )

                        # Optionally index into vector store
                        if self.vector_store is not None:
                            try:
                                text_snippet = (
                                    f"Command Pattern: {pattern['pattern_name']}\n"
                                    f"Description: {pattern['description']}\n"
                                    f"Chain: {' && '.join(pattern.get('command_chain', []))}"
                                )
                                self.vector_store.add_document(
                                    text=text_snippet,
                                    metadata={
                                        "source": "pattern",
                                        "pattern_name": pattern["pattern_name"],
                                        "category": "learned_pattern",
                                        "tags": pattern.get("tags", ""),
                                    }
                                )
                            except Exception as ve:
                                logger.warning(f"Vector indexing pattern error: {ve}")

        except Exception as e:
            logger.error(f"Error in scan_and_promote: {e}")

        return promoted_count

    def _run_loop(self) -> None:
        logger.info(f"PatternLearner background loop started (interval={self.interval}s)")
        while not self._stop_event.is_set():
            try:
                count = self.scan_and_promote()
                if count > 0:
                    logger.info(f"PatternLearner cycle completed: {count} patterns updated/promoted")
            except Exception as e:
                logger.error(f"Unexpected error in PatternLearner loop: {e}")
            
            # Sleep until next cycle or stop requested
            self._stop_event.wait(timeout=self.interval)

        logger.info("PatternLearner background loop stopped")

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="PatternLearnerWorker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None


_GLOBAL_LEARNER: Optional[PatternLearner] = None


def start_pattern_learner(interval_seconds: int = 300, vector_store: Any = None) -> PatternLearner:
    """Starts or returns the global singleton PatternLearner."""
    global _GLOBAL_LEARNER
    if _GLOBAL_LEARNER is None:
        _GLOBAL_LEARNER = PatternLearner(interval_seconds=interval_seconds, vector_store=vector_store)
        _GLOBAL_LEARNER.start()
    return _GLOBAL_LEARNER


def stop_pattern_learner() -> None:
    """Stops the global pattern learner."""
    global _GLOBAL_LEARNER
    if _GLOBAL_LEARNER is not None:
        _GLOBAL_LEARNER.stop()
        _GLOBAL_LEARNER = None
