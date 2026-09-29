"""
Scheduler Tool Module for P.H.A.S.S Sphere & Llama Assistant.
Provides user and agent tools to schedule recurring jobs, delayed actions,
inspect pending tasks, and trigger immediate runs.
"""

from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional
from core.scheduler_engine import scheduler_engine

logger = logging.getLogger("phass.tools.scheduler")


def schedule_task(
    task_name: str,
    cron_or_delay: str,
    tool_or_command: str,
    parameters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Schedules an automated action to run at an interval, delay, or cron time.
    Examples for cron_or_delay: 'in_30s', 'in_10m', 'every_5m', 'every_1h', '@daily'.
    """
    return scheduler_engine.schedule_task(
        name=task_name,
        schedule_expr=cron_or_delay,
        tool_or_command=tool_or_command,
        parameters=parameters or {},
    )


def list_scheduled_tasks() -> Dict[str, Any]:
    """Lists all active and pending scheduled automated tasks."""
    tasks = scheduler_engine.list_tasks()
    return {
        "status": "SUCCESS",
        "task_count": len(tasks),
        "scheduled_tasks": tasks,
    }


def cancel_scheduled_task(task_id: str) -> Dict[str, Any]:
    """Cancels and deletes a scheduled task by ID."""
    return scheduler_engine.cancel_task(task_id=task_id)


def trigger_task_now(task_id: str) -> Dict[str, Any]:
    """Immediately triggers the execution of a scheduled task."""
    return scheduler_engine.trigger_task_now(task_id=task_id)


def get_schedule_history(limit: int = 20) -> Dict[str, Any]:
    """Retrieves the recent execution history and status of automated tasks."""
    history = scheduler_engine.get_history(limit=limit)
    return {
        "status": "SUCCESS",
        "history_count": len(history),
        "history": history,
    }
