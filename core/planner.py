"""
Task Planner for P.H.A.S.S Sphere.
Dynamically decomposes goals into executable subtasks with tool bindings,
dependency graph ordering, and adaptation based on past lessons learned.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import logging
from .goal_manager import Goal, SubTask, GoalState
from .ai_model import BaseAIModel, OfflineCognitiveEngine

logger = logging.getLogger("phass.planner")


@dataclass
class Plan:
    goal_id: str
    subtasks: List[SubTask]
    estimated_steps: int
    estimated_duration_sec: float
    confidence: float
    strategy_note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "estimated_steps": self.estimated_steps,
            "estimated_duration_sec": self.estimated_duration_sec,
            "confidence": self.confidence,
            "strategy_note": self.strategy_note,
            "subtasks": [st.to_dict() for st in self.subtasks],
        }


class TaskPlanner:
    def __init__(self, ai_model: Optional[BaseAIModel] = None):
        self.ai_model = ai_model or OfflineCognitiveEngine()

    async def create_plan(
        self,
        goal: Goal,
        world_context: Dict[str, Any],
        lessons_learned: Optional[List[str]] = None,
    ) -> Plan:
        """
        Synthesizes an optimal execution plan for a goal.
        Applies lessons learned to inject prerequisite checks or defensive validation steps.
        """
        logger.info(f"Generating dynamic plan for goal: {goal.id} - '{goal.title}'")

        # 1. Query AI model / cognitive engine for decomposition
        decomp = await self.ai_model.reason_and_plan(goal.description or goal.title, world_context)
        raw_subtasks = decomp.get("subtasks", [])

        # 2. Apply Learned Strategies / Policy adaptations
        # E.g. If past lesson was "Check dependency configuration before deeper diagnosis", insert dependency check early
        adapted_subtasks = list(raw_subtasks)
        if lessons_learned:
            for lesson in lessons_learned:
                if "dependency" in lesson.lower() and not any("dependency" in st["title"].lower() for st in adapted_subtasks):
                    logger.info(f"Applying learned policy from experience: Injected dependency check prerequisite.")
                    adapted_subtasks.insert(0, {
                        "title": "Validate dependency configurations (Applied Lesson)",
                        "description": "Pre-flight verification learned from previous experience",
                        "tool": "system_diagnostics",
                        "parameters": {"scope": "dependencies"},
                        "expected_output": "Dependency verification report",
                        "priority": 1,
                    })

        # 3. Instantiate SubTasks with dependency chaining
        subtask_objs: List[SubTask] = []
        prev_id: Optional[str] = None

        for idx, item in enumerate(adapted_subtasks):
            st = SubTask(
                title=item.get("title", f"Subtask {idx + 1}"),
                description=item.get("description", ""),
                tool_name=item.get("tool", "system_diagnostics"),
                parameters=item.get("parameters", {}),
                state=GoalState.CREATED,
                priority=item.get("priority", 1),
                dependencies=[prev_id] if prev_id else [],
                confidence=decomp.get("estimated_confidence", 0.92),
            )
            subtask_objs.append(st)
            prev_id = st.id

        # 4. Attach to Goal object
        goal.subtasks = subtask_objs
        goal.current_subtask_index = 0

        plan = Plan(
            goal_id=goal.id,
            subtasks=subtask_objs,
            estimated_steps=len(subtask_objs),
            estimated_duration_sec=len(subtask_objs) * 1.5,
            confidence=decomp.get("estimated_confidence", 0.92),
            strategy_note=decomp.get("reasoning_summary", "Plan generated successfully"),
        )
        return plan
