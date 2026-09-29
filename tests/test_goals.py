"""
Unit tests for the Goal Management System.
"""

import pytest
from core.goal_manager import GoalManager, Goal, GoalState, GoalPriority, SubTask


@pytest.mark.asyncio
async def test_goal_creation_and_prioritization():
    mgr = GoalManager()

    g_low = mgr.create_goal("Low priority task", "Do when idle", priority=GoalPriority.LOW)
    g_high = mgr.create_goal("Urgent system repair", "Fix anomaly now", priority=GoalPriority.CRITICAL)
    g_norm = mgr.create_goal("Routine inspection", "Scan area", priority=GoalPriority.NORMAL)

    highest = mgr.get_highest_priority_goal()
    assert highest is not None
    assert highest.id == g_high.id
    assert highest.priority == GoalPriority.CRITICAL


@pytest.mark.asyncio
async def test_goal_state_transitions():
    mgr = GoalManager()
    goal = mgr.create_goal("Diagnostics test", "Run self-check")

    assert goal.state == GoalState.CREATED
    assert goal.id in mgr.active_goals

    await mgr.update_goal_state(goal.id, GoalState.UNDERSTANDING, "Analyzing directive")
    assert goal.state == GoalState.UNDERSTANDING

    await mgr.update_goal_state(goal.id, GoalState.PLANNING, "Decomposing into subtasks")
    assert goal.state == GoalState.PLANNING

    await mgr.update_goal_state(goal.id, GoalState.COMPLETED, "All subtasks finished")
    assert goal.state == GoalState.COMPLETED
    assert goal.id not in mgr.active_goals
    assert goal in mgr.completed_goals


def test_subtask_progress_tracking():
    goal = Goal(title="Multi-step goal", description="Testing progress calculation")
    goal.subtasks = [
        SubTask(title="Step 1", state=GoalState.COMPLETED),
        SubTask(title="Step 2", state=GoalState.COMPLETED),
        SubTask(title="Step 3", state=GoalState.EXECUTING),
        SubTask(title="Step 4", state=GoalState.CREATED),
    ]

    goal.update_progress()
    assert goal.completion_percentage == 50.0

    current = goal.get_current_subtask()
    assert current is not None
    assert current.title == "Step 3"
