"""
End-to-end integration tests for the Autonomous Agent Loop.
"""

import pytest
import asyncio
from core.cognitive_core import CognitiveCore, CognitiveState
from core.goal_manager import GoalState


@pytest.mark.asyncio
async def test_cognitive_core_boot_and_execution():
    core = CognitiveCore(engine_type="offline")

    # 1. Boot
    boot_ok = await core.boot_sequence()
    assert boot_ok is True
    assert core.state == CognitiveState.READY

    # 2. Start loop
    await core.start_autonomous_loop()
    assert core.is_running is True

    # 3. Submit directive
    res = await core.submit_user_directive("Inspect the environment and map room")
    assert res is not None
    assert res["status"] == "GOAL_CREATED"
    assert "nlg_response" in res
    assert "nlu" in res

    goal_id = res["goal"]["id"]
    goal = core.goal_manager.get_goal(goal_id)
    assert goal is not None
    assert goal.state in (GoalState.CREATED, GoalState.UNDERSTANDING, GoalState.PLANNING, GoalState.EXECUTING)

    # 4. Wait for autonomous execution loop to complete the subtasks
    for _ in range(40):
        await asyncio.sleep(0.1)
        if goal.state in (GoalState.COMPLETED, GoalState.FAILED):
            break

    assert goal.state == GoalState.COMPLETED
    assert goal.completion_percentage == 100.0
    assert len(goal.subtasks) >= 3

    # Stop loop
    await core.stop_autonomous_loop()
    assert core.is_running is False
