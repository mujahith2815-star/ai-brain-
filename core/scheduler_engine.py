"""
Scheduled Tasks & Automation Engine for P.H.A.S.S Sphere & Llama Assistant.
Provides persistent task scheduling with cron expressions, fixed intervals,
delayed one-shot execution, and background worker automation.
"""

from __future__ import annotations
import os
import time
import json
import uuid
import threading
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Tuple

logger = logging.getLogger("phass.core.scheduler")


@dataclass
class ScheduledTask:
    task_id: str
    name: str
    schedule_expr: str  # e.g., "every_5m", "every_1h", "in_30s", "0 3 * * 0"
    tool_or_command: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    last_run: Optional[float] = None
    next_run: float = field(default_factory=time.time)
    run_count: int = 0
    is_one_shot: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "schedule_expr": self.schedule_expr,
            "tool_or_command": self.tool_or_command,
            "parameters": self.parameters,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "last_run": self.last_run,
            "next_run": self.next_run,
            "run_count": self.run_count,
            "is_one_shot": self.is_one_shot,
        }


class SchedulerEngine:
    """
    Background scheduler orchestrating automated periodic and delayed directives.
    Persists jobs to memory_vault/scheduled_tasks.json.
    Supports cron expressions, natural interval directives, pause/resume, and pre-built routines.
    """

    PREBUILT_ROUTINES = [
        {
            "name": "clean_downloads_weekly",
            "description": "clean downloads every Sunday at 3 AM",
            "cron": "0 3 * * 0",
            "command": "clean_downloads",
            "parameters": {"target_dir": "Downloads", "older_than_days": 14},
        },
        {
            "name": "backup_documents_weekly",
            "description": "backup Documents every Friday at 5 PM",
            "cron": "0 17 * * 5",
            "command": "backup_documents",
            "parameters": {"source": "Documents", "destination": "Backups/Documents"},
        },
        {
            "name": "check_disk_space_hourly",
            "description": "check disk space every hour, alert if under 10%",
            "cron": "0 * * * *",
            "command": "analyze_disk_space",
            "parameters": {"threshold_percent": 10.0, "alert_on_low": True},
        },
        {
            "name": "daily_summary_report",
            "description": "generate daily summary report at end of day",
            "cron": "0 23 * * *",
            "command": "generate_daily_summary",
            "parameters": {"report_type": "executive"},
        },
    ]

    def __init__(self, storage_dir: Optional[str] = None):
        if storage_dir:
            self.storage_path = Path(storage_dir) / "scheduled_tasks.json"
        else:
            try:
                from core.data_hub import data_hub
                self.storage_path = data_hub.resolve("tasks", "scheduled_tasks.json")
            except Exception:
                self.storage_path = Path("memory_vault") / "scheduled_tasks.json"
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        self.tasks: Dict[str, ScheduledTask] = {}
        self.history: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None

        self._load_tasks()
        self.start()

    def start(self):
        """Starts the background schedule monitor thread."""
        with self._lock:
            if not self._running:
                self._running = True
                self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
                self._worker_thread.start()
                logger.info("Scheduler worker thread started.")

    def stop(self):
        """Stops the background scheduler thread."""
        with self._lock:
            self._running = False

    def _load_tasks(self):
        """Loads tasks from local JSON persistence."""
        target_path = self.storage_path
        if not target_path.exists():
            legacy_path = Path("memory_vault") / "scheduled_tasks.json"
            if legacy_path.exists():
                target_path = legacy_path
            else:
                return
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("tasks", []):
                    task = ScheduledTask(**item)
                    self.tasks[task.task_id] = task
            logger.info(f"Loaded {len(self.tasks)} scheduled tasks.")
        except Exception as e:
            logger.warning(f"Could not load scheduled tasks from {target_path}: {e}")

    def _save_tasks(self):
        """Saves active tasks to JSON persistence."""
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump({"tasks": [t.to_dict() for t in self.tasks.values()]}, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save scheduled tasks: {e}")

    def _match_cron_field(self, field_str: str, val: int, min_val: int, max_val: int) -> bool:
        """Evaluates whether a value matches a cron field expression."""
        field_str = field_str.strip()
        if field_str == "*":
            return True
        if "/" in field_str:
            base, step = field_str.split("/", 1)
            step_int = int(step)
            start = min_val if base == "*" else int(base)
            return (val >= start) and ((val - start) % step_int == 0)
        if "," in field_str:
            parts = [int(p) for p in field_str.split(",")]
            return val in parts
        if "-" in field_str:
            start, end = field_str.split("-", 1)
            return int(start) <= val <= int(end)
        try:
            return int(field_str) == val
        except ValueError:
            return False

    def _compute_next_cron_run(self, cron_expr: str, from_time: float) -> float:
        """Calculates next timestamp matching standard 5-part cron: min hour dom mon dow."""
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            # Fallback to hourly if malformed
            return from_time + 3600.0

        min_expr, hour_expr, dom_expr, mon_expr, dow_expr = parts

        # Search up to 366 days into the future minute by minute or hour by hour
        dt = datetime.fromtimestamp(from_time, tz=timezone.utc).replace(second=0, microsecond=0) + timedelta(minutes=1)
        max_limit = dt + timedelta(days=366)

        while dt < max_limit:
            # Python weekday: Monday is 0, Sunday is 6. Cron: Sunday is 0 or 7.
            cron_dow = (dt.weekday() + 1) % 7

            if not self._match_cron_field(mon_expr, dt.month, 1, 12):
                dt = (dt.replace(day=1, hour=0, minute=0) + timedelta(days=32)).replace(day=1)
                continue
            if not (self._match_cron_field(dom_expr, dt.day, 1, 31) and self._match_cron_field(dow_expr, cron_dow, 0, 7)):
                dt = (dt + timedelta(days=1)).replace(hour=0, minute=0)
                continue
            if not self._match_cron_field(hour_expr, dt.hour, 0, 23):
                dt = (dt + timedelta(hours=1)).replace(minute=0)
                continue
            if not self._match_cron_field(min_expr, dt.minute, 0, 59):
                dt += timedelta(minutes=1)
                continue

            return dt.timestamp()

        return from_time + 3600.0

    def _compute_next_run(self, expr: str, from_time: float) -> Tuple[float, bool]:
        """
        Parses expression and returns (next_timestamp, is_one_shot).
        Supports:
          - in_Xs / in_Xm / in_Xh (one-shot delay)
          - every_Xs / every_Xm / every_Xh / every_Xd (periodic interval)
          - @hourly (3600s), @daily (86400s), @weekly (604800s)
          - 5-part Cron format: '* * * * *', '0 3 * * 0', etc.
        """
        e = expr.strip()
        e_lower = e.lower()
        now = from_time

        if e_lower.startswith("in_"):
            val_str = e_lower.replace("in_", "")
            if val_str.endswith("s"):
                sec = int(val_str[:-1])
            elif val_str.endswith("m"):
                sec = int(val_str[:-1]) * 60
            elif val_str.endswith("h"):
                sec = int(val_str[:-1]) * 3600
            else:
                sec = int(val_str)
            return now + sec, True

        if e_lower.startswith("every_"):
            val_str = e_lower.replace("every_", "")
            if val_str.endswith("s"):
                sec = int(val_str[:-1])
            elif val_str.endswith("m"):
                sec = int(val_str[:-1]) * 60
            elif val_str.endswith("h"):
                sec = int(val_str[:-1]) * 3600
            elif val_str.endswith("d"):
                sec = int(val_str[:-1]) * 86400
            else:
                sec = int(val_str)
            return now + sec, False

        if e_lower == "@hourly":
            return now + 3600, False
        if e_lower == "@daily":
            return now + 86400, False
        if e_lower == "@weekly":
            return now + 604800, False

        # Check if 5-field cron expression
        if len(e.split()) == 5:
            return self._compute_next_cron_run(e, now), False

        # Default fallback: every 1 hour
        return now + 3600, False

    def schedule_task(
        self,
        name_or_expr: Optional[str] = None,
        schedule_expr_or_command: Optional[str] = None,
        tool_or_command: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        *args,
        name: Optional[str] = None,
        task_name: Optional[str] = None,
        schedule_expr: Optional[str] = None,
        cron_or_delay: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Creates and registers a new automated task.
        Supports keyword and positional signatures:
          1) schedule_task(name="...", schedule_expr="...", tool_or_command="...", parameters=...)
          2) schedule_task(cron_expression, command)
          3) schedule_task(name, schedule_expr, tool_or_command, parameters)
        """
        actual_name = name or task_name or kwargs.get("name") or kwargs.get("task_name")
        actual_expr = schedule_expr or cron_or_delay or kwargs.get("schedule_expr") or kwargs.get("cron_or_delay")
        actual_cmd = tool_or_command or kwargs.get("tool_or_command") or kwargs.get("command") or kwargs.get("cmd")
        params = parameters or kwargs.get("parameters") or {}

        if actual_cmd is not None and actual_expr is not None:
            task_name = actual_name or f"task_{int(time.time())}"
            schedule_expr = actual_expr
            cmd = actual_cmd
        elif tool_or_command is None and name_or_expr and schedule_expr_or_command:
            schedule_expr = name_or_expr
            cmd = schedule_expr_or_command
            task_name = actual_name or f"routine_{cmd}_{int(time.time())}"
        else:
            task_name = name_or_expr or actual_name or f"task_{int(time.time())}"
            schedule_expr = schedule_expr_or_command or actual_expr or "every_1h"
            cmd = tool_or_command or actual_cmd or "system_diagnostics"


        now = time.time()
        next_run, is_one_shot = self._compute_next_run(schedule_expr, now)
        task_id = f"task-{uuid.uuid4().hex[:8]}"

        task = ScheduledTask(
            task_id=task_id,
            name=task_name,
            schedule_expr=schedule_expr,
            tool_or_command=cmd,
            parameters=params,
            enabled=True,
            created_at=now,
            next_run=next_run,
            is_one_shot=is_one_shot,
        )

        with self._lock:
            self.tasks[task_id] = task
            self._save_tasks()

        logger.info(f"Task '{task_name}' scheduled [ID: {task_id}] next run at {next_run}")
        return {
            "status": "SUCCESS",
            "task_id": task_id,
            "name": task_name,
            "schedule_expr": schedule_expr,
            "next_run_timestamp": next_run,
            "is_one_shot": is_one_shot,
            "message": f"Task '{task_name}' registered. Next execution in {max(0, int(next_run - now))} seconds.",
        }

    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """Cancels and removes a scheduled task."""
        with self._lock:
            if task_id in self.tasks:
                task = self.tasks.pop(task_id)
                self._save_tasks()
                return {"status": "SUCCESS", "task_id": task_id, "message": f"Task '{task.name}' cancelled."}
            for h in self.history:
                if h.get("task_id") == task_id:
                    return {"status": "SUCCESS", "task_id": task_id, "message": f"Task '{task_id}' was already executed and cleared."}
        return {"status": "FAILED", "error": f"Task ID '{task_id}' not found."}

    def remove_scheduled_task(self, task_id: str) -> Dict[str, Any]:
        """Alias for cancel_task for user-requested API symmetry."""
        return self.cancel_task(task_id)

    def pause_schedule(self, task_id: str) -> Dict[str, Any]:
        """Pauses a scheduled task without deleting it."""
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return {"status": "FAILED", "error": f"Task ID '{task_id}' not found."}
            task.enabled = False
            self._save_tasks()
            return {"status": "SUCCESS", "task_id": task_id, "message": f"Task '{task.name}' paused."}

    def resume_schedule(self, task_id: str) -> Dict[str, Any]:
        """Resumes a paused scheduled task."""
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return {"status": "FAILED", "error": f"Task ID '{task_id}' not found."}
            task.enabled = True
            # Recalculate next run from now
            next_t, _ = self._compute_next_run(task.schedule_expr, time.time())
            task.next_run = next_t
            self._save_tasks()
            return {"status": "SUCCESS", "task_id": task_id, "message": f"Task '{task.name}' resumed."}

    def get_prebuilt_schedules(self) -> List[Dict[str, Any]]:
        """Returns catalogue of standard pre-configured automated schedules."""
        return list(self.PREBUILT_ROUTINES)

    def register_all_prebuilt_routines(self) -> List[Dict[str, Any]]:
        """Registers all 4 user-specified pre-built automated schedules."""
        registered = []
        for r in self.PREBUILT_ROUTINES:
            res = self.schedule_task(
                name=r["name"],
                schedule_expr=r["cron"],
                tool_or_command=r["command"],
                parameters=r["parameters"],
            )
            registered.append(res)
        return registered

    def list_tasks(self) -> List[Dict[str, Any]]:
        """Lists all registered tasks and their schedules."""
        with self._lock:
            return [t.to_dict() for t in self.tasks.values()]

    def trigger_task_now(self, task_id: str) -> Dict[str, Any]:
        """Executes a task immediately without affecting its regular interval."""
        with self._lock:
            task = self.tasks.get(task_id)
        if not task:
            return {"status": "FAILED", "error": f"Task ID '{task_id}' not found."}

        return self._execute_task(task)

    def _execute_task(self, task: ScheduledTask) -> Dict[str, Any]:
        """Executes the task action via ToolRegistry or primary brain."""
        start_t = time.time()
        logger.info(f"Executing scheduled task '{task.name}' [{task.task_id}] -> {task.tool_or_command}")
        output = {}
        status = "SUCCESS"

        try:
            from tools.registry import tool_registry
            tool_def = tool_registry.get_tool(task.tool_or_command)
            if tool_def:
                import asyncio
                import inspect
                if inspect.iscoroutinefunction(tool_def.handler):
                    res = asyncio.run(tool_def.handler(**task.parameters))
                else:
                    res = tool_def.handler(**task.parameters)
                output = res if isinstance(res, dict) else {"result": res}
            else:
                from core.platform_abstraction import get_platform
                plat = get_platform()
                res = plat.execute_command(task.tool_or_command)
                output = res
                if res.get("status") == "FAILED":
                    status = "FAILED"
        except Exception as e:
            logger.error(f"Error executing scheduled task '{task.name}': {e}")
            output = {"error": str(e)}
            status = "FAILED"

        duration = round(time.time() - start_t, 3)
        history_record = {
            "task_id": task.task_id,
            "name": task.name,
            "timestamp": time.time(),
            "status": status,
            "duration_seconds": duration,
            "output_summary": str(output)[:200],
        }

        with self._lock:
            task.last_run = time.time()
            task.run_count += 1
            self.history.append(history_record)
            if len(self.history) > 200:
                self.history.pop(0)

            if task.is_one_shot:
                self.tasks.pop(task.task_id, None)
            else:
                next_t, _ = self._compute_next_run(task.schedule_expr, time.time())
                task.next_run = next_t
            self._save_tasks()

        return {
            "status": status,
            "task_id": task.task_id,
            "output": output,
            "duration_seconds": duration,
        }

    def _worker_loop(self):
        """Background worker evaluating due tasks."""
        while self._running:
            now = time.time()
            due_tasks = []
            with self._lock:
                for task in self.tasks.values():
                    if task.enabled and task.next_run <= now:
                        due_tasks.append(task)

            for dt in due_tasks:
                try:
                    self._execute_task(dt)
                except Exception as e:
                    logger.error(f"Worker task error: {e}")

            time.sleep(1.0)

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Returns recent execution history."""
        with self._lock:
            return list(reversed(self.history[-limit:]))


# Global Singleton
scheduler_engine = SchedulerEngine()


# Top-level standalone functions matching user requests
def schedule_task(
    name_or_expr: Optional[str] = None,
    schedule_expr_or_command: Optional[str] = None,
    tool_or_command: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    *args,
    name: Optional[str] = None,
    task_name: Optional[str] = None,
    schedule_expr: Optional[str] = None,
    cron_or_delay: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    return scheduler_engine.schedule_task(
        name_or_expr,
        schedule_expr_or_command,
        tool_or_command,
        parameters,
        *args,
        name=name,
        task_name=task_name,
        schedule_expr=schedule_expr,
        cron_or_delay=cron_or_delay,
        **kwargs,
    )


def remove_scheduled_task(task_id: str) -> Dict[str, Any]:
    return scheduler_engine.remove_scheduled_task(task_id)


def pause_schedule(task_id: str) -> Dict[str, Any]:
    return scheduler_engine.pause_schedule(task_id)


def resume_schedule(task_id: str) -> Dict[str, Any]:
    return scheduler_engine.resume_schedule(task_id)


def get_prebuilt_schedules() -> List[Dict[str, Any]]:
    return scheduler_engine.get_prebuilt_schedules()
