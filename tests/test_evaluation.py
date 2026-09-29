"""
Unit tests for the AI Evaluation Framework.
"""

from learning.evaluation import EvaluationFramework


def test_evaluation_framework_metrics():
    framework = EvaluationFramework()

    # Record successful goal
    m1 = framework.record_goal_evaluation(
        goal_success=True,
        subtasks_planned=4,
        subtasks_executed=4,
        recovered_from_error=False,
        confidence=0.95,
        had_human_intervention=False,
    )

    assert m1.total_goals_evaluated == 1
    assert m1.goal_success_rate_pct > 80.0
    assert m1.autonomy_index_pct > 90.0

    # Record goal with recovery
    m2 = framework.record_goal_evaluation(
        goal_success=True,
        subtasks_planned=5,
        subtasks_executed=5,
        recovered_from_error=True,
        confidence=0.90,
    )

    assert m2.total_goals_evaluated == 2
    assert m2.error_recovery_rate_pct >= 88.0
