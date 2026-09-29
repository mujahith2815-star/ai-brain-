"""
Experience Database for P.H.A.S.S Sphere.
Stores structured records of tasks, executions, outcomes, feedback, and extracted lessons.
Supports SQLite persistence and in-memory querying.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import sqlite3
from typing import Any, Dict, List, Optional
import uuid
import logging
from pathlib import Path

logger = logging.getLogger("phass.learning.experience_db")


@dataclass
class ExperienceRecord:
    id: str = field(default_factory=lambda: f"EXP-{str(uuid.uuid4())[:8].upper()}")
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    goal_id: str = ""
    goal_title: str = ""
    goal_description: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    plan_summary: str = ""
    actions: List[Dict[str, Any]] = field(default_factory=list)
    result: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    confidence: float = 0.90
    error: Optional[str] = None
    user_feedback: Optional[Dict[str, Any]] = None
    lessons_learned: List[str] = field(default_factory=list)
    related_memories: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "goal_id": self.goal_id,
            "goal_title": self.goal_title,
            "goal_description": self.goal_description,
            "context": self.context,
            "plan_summary": self.plan_summary,
            "actions": self.actions,
            "result": self.result,
            "success": self.success,
            "confidence": round(self.confidence, 2),
            "error": self.error,
            "user_feedback": self.user_feedback,
            "lessons_learned": self.lessons_learned,
            "related_memories": self.related_memories,
        }


class ExperienceDatabase:
    def __init__(self, db_path: str = "data/phass_experiences.db"):
        self.db_path = db_path
        self.in_memory_records: List[ExperienceRecord] = []
        self._init_db()

    def _init_db(self) -> None:
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS experiences (
                        id TEXT PRIMARY KEY,
                        timestamp TEXT,
                        goal_id TEXT,
                        goal_title TEXT,
                        goal_description TEXT,
                        context_json TEXT,
                        plan_summary TEXT,
                        actions_json TEXT,
                        result_json TEXT,
                        success INTEGER,
                        confidence REAL,
                        error TEXT,
                        user_feedback_json TEXT,
                        lessons_json TEXT,
                        related_memories_json TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.warning(f"Could not initialize SQLite DB ({e}). Using in-memory store.")

    def store_experience(self, exp: ExperienceRecord) -> None:
        self.in_memory_records.append(exp)
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO experiences VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        exp.id,
                        exp.timestamp,
                        exp.goal_id,
                        exp.goal_title,
                        exp.goal_description,
                        json.dumps(exp.context),
                        exp.plan_summary,
                        json.dumps(exp.actions),
                        json.dumps(exp.result),
                        1 if exp.success else 0,
                        exp.confidence,
                        exp.error,
                        json.dumps(exp.user_feedback) if exp.user_feedback else None,
                        json.dumps(exp.lessons_learned),
                        json.dumps(exp.related_memories),
                    ),
                )
                conn.commit()
            logger.info(f"Persisted experience record {exp.id} ('{exp.goal_title}') - Success: {exp.success}")
        except Exception as e:
            logger.warning(f"Error persisting experience to SQLite: {e}")

    def get_recent_experiences(self, limit: int = 20) -> List[ExperienceRecord]:
        if self.in_memory_records:
            return self.in_memory_records[-limit:]
        return []

    def get_all_lessons(self) -> List[str]:
        lessons = []
        for exp in self.in_memory_records:
            lessons.extend(exp.lessons_learned)
        return list(dict.fromkeys(lessons))  # Deduplicate preserving order
