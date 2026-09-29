import pytest
from core.scheduler_engine import (
    scheduler_engine,
    schedule_task,
    remove_scheduled_task,
    pause_schedule,
    resume_schedule,
    get_prebuilt_schedules,
)


def test_prebuilt_schedules_catalogue():
    schedules = get_prebuilt_schedules()
    assert len(schedules) >= 4
    names = [s["name"] for s in schedules]
    assert "clean_downloads_weekly" in names
    assert "backup_documents_weekly" in names
    assert "check_disk_space_hourly" in names
    assert "daily_summary_report" in names


def test_schedule_cron_task():
    res = schedule_task("0 3 * * 0", "clean_downloads")
    assert res["status"] == "SUCCESS"
    task_id = res["task_id"]
    assert task_id in scheduler_engine.tasks

    # Verify task attributes
    task = scheduler_engine.tasks[task_id]
    assert task.schedule_expr == "0 3 * * 0"
    assert task.tool_or_command == "clean_downloads"
    assert task.enabled is True

    # Clean up
    remove_scheduled_task(task_id)


def test_pause_and_resume_schedule():
    res = schedule_task("every_1h", "check_disk_space")
    task_id = res["task_id"]

    pause_res = pause_schedule(task_id)
    assert pause_res["status"] == "SUCCESS"
    assert scheduler_engine.tasks[task_id].enabled is False

    resume_res = resume_schedule(task_id)
    assert resume_res["status"] == "SUCCESS"
    assert scheduler_engine.tasks[task_id].enabled is True

    remove_scheduled_task(task_id)


def test_remove_scheduled_task():
    res = schedule_task("in_10s", "generate_daily_summary")
    task_id = res["task_id"]
    assert task_id in scheduler_engine.tasks

    del_res = remove_scheduled_task(task_id)
    assert del_res["status"] == "SUCCESS"
    assert task_id not in scheduler_engine.tasks


def test_cron_evaluator_validity():
    now = 1700000000.0  # reference epoch
    next_run = scheduler_engine._compute_next_cron_run("0 3 * * 0", now)
    assert next_run > now