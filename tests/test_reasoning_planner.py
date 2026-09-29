"""
Unit tests for the Reasoning Engine and Task Planner.
"""

import pytest
from core.reasoning import ReasoningEngine
from core.planner import TaskPlanner
from core.goal_manager import Goal, GoalState
from core.ai_model import OfflineCognitiveEngine


@pytest.mark.asyncio
async def test_reasoning_engine_analysis():
    ai = OfflineCognitiveEngine()
    engine = ReasoningEngine(ai)

    mock_world = {
        "entities": [{"name": "Server Rack"}],
        "robot_state": {"battery_percentage": 90.0},
    }
    mock_memories = [{"content": "Past server diagnostic succeeded"}]
    mock_lessons = ["Check dependencies first"]

    res = await engine.analyze_context_and_goal(
        "Diagnose system failure and inspect logs",
        mock_world,
        mock_memories,
        mock_lessons,
    )

    assert res.confidence >= 0.85
    assert len(res.hypotheses) > 0
    assert "safe_public_summary" in res.__dict__
    assert res.safe_public_summary["status"] == "REASONING_COMPLETE"


@pytest.mark.asyncio
async def test_planner_subtask_generation():
    ai = OfflineCognitiveEngine()
    planner = TaskPlanner(ai)

    goal = Goal(
        title="Inspect the environment and map room",
        description="Scan surrounding area and detect objects",
    )

    plan = await planner.create_plan(goal, {}, lessons_learned=[])

    assert plan.estimated_steps >= 3
    assert len(goal.subtasks) >= 3
    assert goal.subtasks[0].state == GoalState.CREATED
    # Verify dependency chaining
    assert goal.subtasks[1].dependencies == [goal.subtasks[0].id]


@pytest.mark.asyncio
async def test_planner_applies_learned_policy():
    ai = OfflineCognitiveEngine()
    planner = TaskPlanner(ai)

    goal = Goal(
        title="Diagnose failure in service",
        description="Find why service is down",
    )

    # Lesson mentioning dependencies should inject prerequisite check
    plan = await planner.create_plan(
        goal, {}, lessons_learned=["Check dependency configuration before deeper diagnosis"]
    )

    first_st = goal.subtasks[0]
    assert "dependency" in first_st.title.lower() or "telemetry" in first_st.title.lower()
