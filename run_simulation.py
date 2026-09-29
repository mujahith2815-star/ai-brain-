"""
Headless Simulation & Benchmark Runner for P.H.A.S.S Sphere.
Demonstrates the full autonomous cognitive loop without requiring a browser.
"""

import asyncio
import sys
from pathlib import Path

# Ensure UTF-8 stdout on Windows
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.cognitive_core import cognitive_core, CognitiveState
from core.goal_manager import GoalState
from learning.evaluation import evaluation_framework


async def run_benchmark_mission():
    print("\n=======================================================")
    print("      P.H.A.S.S SPHERE — AUTONOMOUS MISSION BENCHMARK      ")
    print("=======================================================\n")

    # 1. Boot System
    await cognitive_core.boot_sequence()
    await cognitive_core.start_autonomous_loop()

    # 2. Submit Goal 1: Environment Scan
    print("\n[MISSION 1] Submitting Directive: 'Inspect the environment and map room'")
    res1 = await cognitive_core.submit_user_directive("Inspect the environment and map room")
    goal1 = cognitive_core.goal_manager.get_goal(res1["goal"]["id"])
    print(f"  [NLU] Recognized Intent: {res1['nlu']['intent']} (Confidence: {res1['nlu']['intent_confidence']})")
    print(f"  [NLG] Robot Verbal Response: \"{res1['nlg_response']}\"")

    # Await completion
    while goal1.state not in (GoalState.COMPLETED, GoalState.FAILED):
        await asyncio.sleep(0.2)
        print(f"  > State: {goal1.state.value} | Progress: {goal1.completion_percentage}% | Subtask: {goal1.get_current_subtask().title if goal1.get_current_subtask() else 'Verifying'}")

    print(f"[OK] Mission 1 Concluded: {goal1.state.value} (Result: {goal1.result})")

    # 3. Submit User Feedback / Lesson
    print("\n[FEEDBACK] Submitting User Correction: 'Check dependency configuration before deeper diagnosis'")
    fb = await cognitive_core.learning_engine.ingest_user_feedback(
        "Check dependency configuration before deeper diagnosis", target_goal_id=goal1.id
    )
    print(f"[OK] Feedback Registered: Type={fb.feedback_type.value}, Extracted Lesson='{fb.extracted_lesson}'")

    # 4. Submit Goal 2: Failure Diagnostics (Should apply learned lesson)
    print("\n[MISSION 2] Submitting Directive: 'Analyze the system and find the reason for the failure'")
    res2 = await cognitive_core.submit_user_directive("Analyze the system and find the reason for the failure")
    goal2 = cognitive_core.goal_manager.get_goal(res2["goal"]["id"])
    print(f"  [NLU] Recognized Intent: {res2['nlu']['intent']} (Confidence: {res2['nlu']['intent_confidence']})")
    print(f"  [NLG] Robot Verbal Response: \"{res2['nlg_response']}\"")

    while goal2.state not in (GoalState.COMPLETED, GoalState.FAILED):
        await asyncio.sleep(0.2)
        print(f"  > State: {goal2.state.value} | Progress: {goal2.completion_percentage}% | Subtask: {goal2.get_current_subtask().title if goal2.get_current_subtask() else 'Verifying'}")

    print(f"[OK] Mission 2 Concluded: {goal2.state.value}")

    # 5. Display Evaluation Metrics
    metrics = evaluation_framework.get_latest_metrics()
    print("\n=======================================================")
    print("              AI EVALUATION BENCHMARK REPORT           ")
    print("=======================================================")
    print(f"  • Goal Success Rate:        {metrics['goal_success_rate_pct']}%")
    print(f"  • Planning Quality Score:   {metrics['planning_quality_score']}")
    print(f"  • Error Recovery Rate:      {metrics['error_recovery_rate_pct']}%")
    print(f"  • Autonomy Index:           {metrics['autonomy_index_pct']}%")
    print(f"  • Average Confidence:       {metrics['average_decision_confidence']}")
    print(f"  • Total Goals Evaluated:    {metrics['total_goals_evaluated']}")
    print("=======================================================\n")

    await cognitive_core.stop_autonomous_loop()


if __name__ == "__main__":
    asyncio.run(run_benchmark_mission())
