"""
Goal Management System for P.H.A.S.S Sphere.
Manages hierarchical goals, state transitions, subtask execution graphs,
priorities, and lifecycle events.
"""

from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
import logging
from .event_bus import event_bus, Event, EventType

logger = logging.getLogger("phass.goal_manager")


class GoalState(str, Enum):
    CREATED = "CREATED"
    UNDERSTANDING = "UNDERSTANDING"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    WAITING = "WAITING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    LEARNING = "LEARNING"


class GoalPriority(int, Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class SubTask:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    description: str = ""
    tool_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    state: GoalState = GoalState.CREATED
    priority: int = 1
    dependencies: List[str] = field(default_factory=list)
    result: Optional[Any] = None
    error: Optional[str] = None
    confidence: float = 1.0
    start_time: Optional[str] = None
    end_time: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "state": self.state.value if isinstance(self.state, Enum) else str(self.state),
            "priority": self.priority,
            "dependencies": self.dependencies,
            "result": self.result,
            "error": self.error,
            "confidence": self.confidence,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }


@dataclass
class Goal:
    title: str
    description: str
    id: str = field(default_factory=lambda: f"GOAL-{str(uuid.uuid4())[:8].upper()}")
    priority: GoalPriority = GoalPriority.NORMAL
    state: GoalState = GoalState.CREATED
    context: Dict[str, Any] = field(default_factory=dict)
    required_resources: List[str] = field(default_factory=list)
    subtasks: List[SubTask] = field(default_factory=list)
    current_subtask_index: int = 0
    result: Optional[Any] = None
    confidence: float = 0.90
    completion_percentage: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: Optional[str] = None
    lessons_learned: List[str] = field(default_factory=list)

    def transition_to(self, new_state: GoalState, reason: str = "") -> None:
        old_state = self.state
        self.state = new_state
        self.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Goal {self.id} ('{self.title}') transitioned: {old_state.value} -> {new_state.value}. {reason}")

    def update_progress(self) -> None:
        if not self.subtasks:
            self.completion_percentage = 100.0 if self.state == GoalState.COMPLETED else 0.0
            return
        completed_count = sum(1 for s in self.subtasks if s.state == GoalState.COMPLETED)
        self.completion_percentage = round((completed_count / len(self.subtasks)) * 100.0, 1)

    def get_current_subtask(self) -> Optional[SubTask]:
        for subtask in self.subtasks:
            if subtask.state in (GoalState.CREATED, GoalState.EXECUTING, GoalState.WAITING, GoalState.PLANNING):
                return subtask
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.name if isinstance(self.priority, Enum) else str(self.priority),
            "state": self.state.value if isinstance(self.state, Enum) else str(self.state),
            "context": self.context,
            "required_resources": self.required_resources,
            "subtasks": [st.to_dict() for st in self.subtasks],
            "current_subtask_index": self.current_subtask_index,
            "result": self.result,
            "confidence": self.confidence,
            "completion_percentage": self.completion_percentage,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
            "lessons_learned": self.lessons_learned,
        }


class GoalManager:
    """
    Manages active goals, priority ordering, state transitions, and history.
    """

    def __init__(self):
        self.active_goals: Dict[str, Goal] = {}
        self.completed_goals: List[Goal] = []
        self.failed_goals: List[Goal] = []

    @property
    def goals(self) -> Dict[str, Goal]:
        """Returns unified dictionary of active, completed, and failed goals."""
        all_dict = dict(self.active_goals)
        for g in self.completed_goals + self.failed_goals:
            all_dict[g.id] = g
        return all_dict

    def get_all_goals(self) -> Dict[str, Goal]:
        return self.goals

    def create_goal(
        self,
        title: str,
        description: str,
        priority: GoalPriority = GoalPriority.NORMAL,
        context: Optional[Dict[str, Any]] = None,
        required_resources: Optional[List[str]] = None,
    ) -> Goal:
        goal = Goal(
            title=title,
            description=description,
            priority=priority,
            context=context or {},
            required_resources=required_resources or ["ai_core", "perception"],
        )
        self.active_goals[goal.id] = goal
        logger.info(f"Created goal {goal.id}: {goal.title} (Priority: {goal.priority.name})")

        # Publish event if event loop is running
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                event_bus.publish(
                    Event(
                        type=EventType.GOAL_CREATED,
                        source="GoalManager",
                        data={"goal": goal.to_dict()},
                    )
                )
            )
        except RuntimeError:
            pass
        return goal

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        if goal_id in self.active_goals:
            return self.active_goals[goal_id]
        for g in self.completed_goals + self.failed_goals:
            if g.id == goal_id:
                return g
        return None

    def get_highest_priority_goal(self) -> Optional[Goal]:
        if not self.active_goals:
            return None
        # Sort by Priority descending, then created_at ascending
        sorted_goals = sorted(
            self.active_goals.values(),
            key=lambda g: (-int(g.priority), g.created_at),
        )
        return sorted_goals[0]

    async def update_goal_state(self, goal_id: str, new_state: GoalState, reason: str = "") -> Optional[Goal]:
        goal = self.get_goal(goal_id)
        if not goal:
            return None

        goal.transition_to(new_state, reason)
        goal.update_progress()

        if new_state == GoalState.COMPLETED:
            if goal_id in self.active_goals:
                del self.active_goals[goal_id]
            self.completed_goals.append(goal)
        elif new_state == GoalState.FAILED:
            if goal_id in self.active_goals:
                del self.active_goals[goal_id]
            self.failed_goals.append(goal)

        await event_bus.publish(
            Event(
                type=EventType.GOAL_UPDATED,
                source="GoalManager",
                data={"goal": goal.to_dict(), "reason": reason},
            )
        )
        return goal

    def list_active_goals(self) -> List[Dict[str, Any]]:
        return [g.to_dict() for g in self.active_goals.values()]

    def list_all_goals(self, limit: int = 50) -> List[Dict[str, Any]]:
        all_g = list(self.active_goals.values()) + self.completed_goals + self.failed_goals
        return [g.to_dict() for g in all_g[-limit:]]

    def cancel_goal(self, goal_id: str, reason: str = "User cancellation") -> bool:
        if goal_id in self.active_goals:
            goal = self.active_goals.pop(goal_id)
            goal.transition_to(GoalState.FAILED, reason)
            goal.error = reason
            self.failed_goals.append(goal)
            return True
        return False
