"""
Learning Engine for P.H.A.S.S Sphere.
Implements the continuous closed-loop learning cycle:
Experience -> Evaluation -> Error/Success Analysis -> Knowledge & Policy Update -> Future Improvement.
"""

from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import logging
from .experience_db import ExperienceDatabase, ExperienceRecord
from .feedback import FeedbackClassifier, FeedbackItem, FeedbackType
from memory.retrieval import IntegratedMemorySystem
from core.event_bus import event_bus, Event, EventType

logger = logging.getLogger("phass.learning.engine")


@dataclass
class LearnedStrategy:
    pattern: str
    recommended_action: str
    confidence_weight: float = 1.0
    times_applied: int = 0
    source_experience_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern": self.pattern,
            "recommended_action": self.recommended_action,
            "confidence_weight": round(self.confidence_weight, 2),
            "times_applied": self.times_applied,
            "source_experience_id": self.source_experience_id,
        }


class LearningEngine:
    def __init__(self, memory_system: IntegratedMemorySystem, db_path: str = "data/phass_experiences.db"):
        self.memory = memory_system
        self.exp_db = ExperienceDatabase(db_path=db_path)
        self.feedback_classifier = FeedbackClassifier()
        self.strategies: Dict[str, LearnedStrategy] = {}
        self.total_lessons_learned = 0
        self.successful_tasks_count = 0
        self.failed_tasks_count = 0

        self._seed_baseline_strategies()

    def _seed_baseline_strategies(self) -> None:
        self.register_strategy(
            pattern="diagnose failure",
            recommended_action="Inspect dependency states and logs prior to deep probing",
            weight=1.2,
        )
        self.register_strategy(
            pattern="low battery",
            recommended_action="Abort non-essential tasks and navigate to charging dock",
            weight=1.5,
        )

    def register_strategy(self, pattern: str, recommended_action: str, weight: float = 1.0, exp_id: str = "") -> None:
        key = pattern.lower().strip()
        self.strategies[key] = LearnedStrategy(
            pattern=pattern,
            recommended_action=recommended_action,
            confidence_weight=weight,
            source_experience_id=exp_id,
        )

    async def process_task_completion(
        self,
        goal_id: str,
        goal_title: str,
        goal_description: str,
        context: Dict[str, Any],
        plan_summary: str,
        actions: List[Dict[str, Any]],
        result: Dict[str, Any],
        success: bool,
        error: Optional[str] = None,
    ) -> ExperienceRecord:
        """
        Processes finished task, extracts lessons, updates long-term memory, and persists to Experience DB.
        """
        lessons = []
        if success:
            self.successful_tasks_count += 1
            lessons.append(f"Successful strategy for '{goal_title}': Executed {len(actions)} actions cleanly.")
        else:
            self.failed_tasks_count += 1
            lessons.append(f"Failure diagnosis for '{goal_title}': Encountered error '{error}'. In future, check pre-conditions.")

        self.total_lessons_learned += len(lessons)

        # Create Experience Record
        exp = ExperienceRecord(
            goal_id=goal_id,
            goal_title=goal_title,
            goal_description=goal_description,
            context=context,
            plan_summary=plan_summary,
            actions=actions,
            result=result,
            success=success,
            confidence=0.95 if success else 0.40,
            error=error,
            lessons_learned=lessons,
        )
        self.exp_db.store_experience(exp)

        # Store in Long-Term / Knowledge Memory
        for lesson in lessons:
            self.memory.long_term.store(
                content=lesson,
                tags=["learned_strategy", "lesson", "experience"],
                importance=0.90 if not success else 0.75,
                metadata={"experience_id": exp.id, "goal_id": goal_id},
            )

        # Publish learning event
        await event_bus.publish(
            Event(
                type=EventType.LEARNING_EVENT,
                source="LearningEngine",
                data={
                    "experience_id": exp.id,
                    "goal_title": goal_title,
                    "success": success,
                    "lessons": lessons,
                },
            )
        )

        return exp

    async def ingest_user_feedback(self, text: str, target_goal_id: Optional[str] = None) -> FeedbackItem:
        """
        Receives user feedback, classifies type, and immediately adapts learning heuristics.
        """
        item = self.feedback_classifier.classify_feedback(text, target_goal_id)

        if item.extracted_lesson:
            self.total_lessons_learned += 1
            # If it's a correction, give it high priority in knowledge memory
            importance = 1.0 if item.feedback_type == FeedbackType.CORRECTION else 0.8
            self.memory.long_term.store(
                content=item.extracted_lesson,
                tags=["user_feedback", item.feedback_type.value.lower()],
                importance=importance,
                metadata={"raw_feedback": text, "source": "user"},
            )

            # Adapt dynamic strategy
            self.register_strategy(
                pattern=text[:30],
                recommended_action=item.extracted_lesson,
                weight=1.4 if item.feedback_type == FeedbackType.CORRECTION else 1.0,
            )

        await event_bus.publish(
            Event(
                type=EventType.FEEDBACK_RECEIVED,
                source="LearningEngine",
                data=item.to_dict(),
            )
        )

        return item

    def get_learning_metrics(self) -> Dict[str, Any]:
        total_tasks = self.successful_tasks_count + self.failed_tasks_count
        success_rate = (self.successful_tasks_count / total_tasks * 100.0) if total_tasks > 0 else 100.0
        return {
            "total_experiences": len(self.exp_db.in_memory_records),
            "successful_tasks": self.successful_tasks_count,
            "failed_tasks": self.failed_tasks_count,
            "success_rate_pct": round(success_rate, 1),
            "total_lessons_learned": self.total_lessons_learned,
            "active_strategies_count": len(self.strategies),
            "strategies": [s.to_dict() for s in self.strategies.values()],
        }
