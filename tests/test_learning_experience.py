"""
Unit tests for the Learning Engine, Experience DB, and Feedback System.
"""

import pytest
import os
from learning.experience_db import ExperienceDatabase, ExperienceRecord
from learning.feedback import FeedbackClassifier, FeedbackType
from learning.learning_engine import LearningEngine
from memory.retrieval import IntegratedMemorySystem


def test_experience_db_storage(tmp_path):
    db_file = str(tmp_path / "test_exp.db")
    exp_db = ExperienceDatabase(db_path=db_file)

    exp = ExperienceRecord(
        goal_id="GOAL-TEST-101",
        goal_title="Test Task",
        goal_description="Executing unit test",
        success=True,
        lessons_learned=["Unit tests ensure safety boundaries"],
    )
    exp_db.store_experience(exp)

    records = exp_db.get_recent_experiences(5)
    assert len(records) == 1
    assert records[0].goal_title == "Test Task"
    assert "Unit tests ensure safety boundaries" in exp_db.get_all_lessons()


def test_feedback_classifier_distinguishes_correction_vs_info():
    classifier = FeedbackClassifier()

    # Direct correction
    fb1 = classifier.classify_feedback("No, that was wrong, check the dependencies before diagnosing.")
    assert fb1.feedback_type == FeedbackType.CORRECTION
    assert fb1.extracted_lesson is not None

    # Positive reinforcement
    fb2 = classifier.classify_feedback("Great job, the analysis was accurate.")
    assert fb2.feedback_type == FeedbackType.POSITIVE

    # Additional new information
    fb3 = classifier.classify_feedback("The laboratory temperature was set to 23 degrees.")
    assert fb3.feedback_type == FeedbackType.ADDITIONAL_INFO


@pytest.mark.asyncio
async def test_learning_engine_closed_loop(tmp_path):
    mem = IntegratedMemorySystem()
    db_file = str(tmp_path / "test_learning.db")
    learning = LearningEngine(mem, db_path=db_file)

    # Ingest correction
    fb = await learning.ingest_user_feedback("Incorrect, restart service instead of full reboot.")
    assert fb.feedback_type == FeedbackType.CORRECTION
    assert learning.total_lessons_learned >= 1

    # Ingest task completion
    exp = await learning.process_task_completion(
        goal_id="GOAL-01",
        goal_title="Diagnose Service",
        goal_description="Fixing service",
        context={},
        plan_summary="Plan",
        actions=[{"tool": "diagnostics"}],
        result={"status": "SUCCESS"},
        success=True,
    )
    assert exp.success is True
    assert learning.successful_tasks_count == 1

    metrics = learning.get_learning_metrics()
    assert metrics["success_rate_pct"] == 100.0
