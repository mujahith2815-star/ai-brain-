"""
Task Scheduler for Proactive Autonomous Layer.
Uses APScheduler with persistence in proactive/schedules.json and a global emergency kill switch.
"""

import json
import logging
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False

logger = logging.getLogger("orvix.proactive.scheduler")

# Global emergency kill switch
GLOBAL_PAUSED: bool = False


class TaskScheduler:
    """
    Background cron-style task scheduler with persistence, logging, and kill switch.
    """
    _instance: Optional["TaskScheduler"] = None
    _lock = threading.RLock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, schedules_path: str = "proactive/schedules.json"):
        with self._lock:
            if getattr(self, "_initialized", False):
                return
            self.schedules_path = Path(schedules_path)
            self._tasks: Dict[str, Dict[str, Any]] = {}
            self._callbacks: Dict[str, Callable] = {}
            self._scheduler = None

            if APSCHEDULER_AVAILABLE:
                try:
                    self._scheduler = BackgroundScheduler(daemon=True)
                    self._scheduler.start()
                except Exception as e:
                    logger.warning(f"APScheduler startup notice: {e}")
                    self._scheduler = None

            self._load_schedules()
            self._initialized = True

    def _load_schedules(self) -> None:
        """Loads persistent schedules from JSON."""
        if self.schedules_path.exists():
            try:
                with open(self.schedules_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self._tasks = data
            except Exception as e:
                logger.error(f"Failed to load schedules: {e}")

    def _save_schedules(self) -> None:
        """Persists schedules to JSON."""
        try:
            self.schedules_path.parent.mkdir(parents=True, exist_ok=True)
            serializable = {}
            for name, t in self._tasks.items():
                serializable[name] = {
                    "name": name,
                    "type": t.get("type", "CRON"),
                    "trigger_type": t.get("trigger_type", "CRON"),
                    "cron_expr": t.get("cron_expr"),
                    "config": t.get("config", {}),
                    "action": t.get("action"),
                    "requires_approval": t.get("requires_approval", False),
                    "args": t.get("args", []),
                    "enabled": t.get("enabled", True),
                    "next_run": t.get("next_run", "Scheduled"),
                    "next_run_time": t.get("next_run_time", "Scheduled"),
                }
            with open(self.schedules_path, "w", encoding="utf-8") as f:
                json.dump(serializable, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save schedules: {e}")

    def add_task(
        self,
        name: str,
        cron_expr: Optional[str] = None,
        action_fn: Optional[Callable] = None,
        args: Optional[List[Any]] = None,
        enabled: bool = True,
        trigger_type: str = "CRON",
        config: Optional[Dict[str, Any]] = None,
        action: Optional[Any] = None,
        requires_approval: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Adds or updates a scheduled task.
        """
        with self._lock:
            args = args or []
            config = config or {}
            t_type = (trigger_type or "CRON").upper()

            # Resolve cron expression from config if not explicitly passed
            if not cron_expr and t_type == "CRON":
                cron_expr = config.get("cron") or config.get("cron_expr")

            if action_fn is not None:
                self._callbacks[name] = action_fn

            def _job_wrapper():
                if self.is_paused():
                    logger.info(f"Task '{name}' skipped: Scheduler is PAUSED.")
                    self._log_execution(name, "SKIPPED", "Scheduler is PAUSED", approved=False)
                    return None
                try:
                    fn = self._callbacks.get(name)
                    if fn:
                        res = fn(*args)
                    else:
                        res = f"Executed trigger '{name}' ({action})"
                    self._log_execution(name, "SUCCESS", res, approved=True)
                    return res
                except Exception as ex:
                    logger.error(f"Task '{name}' error: {ex}")
                    self._log_execution(name, "FAILED", str(ex), approved=False)
                    return None

            next_run_desc = "Scheduled"
            if t_type == "CRON" and cron_expr:
                if self._scheduler is not None and APSCHEDULER_AVAILABLE:
                    try:
                        trigger = CronTrigger.from_crontab(cron_expr)
                        job = self._scheduler.add_job(
                            _job_wrapper,
                            trigger=trigger,
                            id=name,
                            replace_existing=True,
                        )
                        if job.next_run_time:
                            next_run_desc = job.next_run_time.isoformat()
                    except Exception as e:
                        logger.warning(f"Could not register APScheduler job for '{name}': {e}")
            elif t_type == "FILE_CHANGE":
                watch_path = config.get("path") or config.get("folder") or "inbox"
                next_run_desc = f"On file change ({watch_path})"
            elif t_type == "CONDITION":
                metric = config.get("metric", "system")
                next_run_desc = f"On condition ({metric})"
            else:
                next_run_desc = "Scheduled"

            task_info = {
                "name": name,
                "type": t_type,
                "trigger_type": t_type,
                "cron_expr": cron_expr,
                "config": config,
                "action": action,
                "requires_approval": requires_approval,
                "args": args,
                "enabled": enabled,
                "next_run": next_run_desc,
                "next_run_time": next_run_desc,
            }
            self._tasks[name] = task_info
            self._save_schedules()
            return task_info

    def bootstrap_from_triggers(self, triggers_path: str = "proactive/triggers.json") -> int:
        """Load triggers from JSON and register them with the scheduler."""
        from proactive.triggers import load_triggers, validate_trigger
        triggers = load_triggers(triggers_path)
        loaded = 0
        for t in triggers:
            if not t.enabled:
                continue
            valid, reason = validate_trigger(t)
            if not valid:
                logger.warning(f"Skipping trigger {t.name}: {reason}")
                continue
            self.add_task(
                name=t.name,
                trigger_type=t.type,
                config=t.config,
                action=t.action,
                requires_approval=t.requires_approval,
                enabled=t.enabled,
            )
            loaded += 1
        logger.info(f"Bootstrap complete: {loaded} triggers loaded")
        return loaded

    def remove_task(self, name: str) -> bool:
        """Removes a scheduled task."""
        with self._lock:
            found = name in self._tasks
            if found:
                del self._tasks[name]
                if name in self._callbacks:
                    del self._callbacks[name]
                if self._scheduler is not None and APSCHEDULER_AVAILABLE:
                    try:
                        self._scheduler.remove_job(name)
                    except Exception:
                        pass
                self._save_schedules()
            return found

    def pause_all(self) -> None:
        """Emergency pause all scheduled background tasks."""
        global GLOBAL_PAUSED
        with self._lock:
            GLOBAL_PAUSED = True
            if self._scheduler is not None and APSCHEDULER_AVAILABLE:
                try:
                    self._scheduler.pause()
                except Exception:
                    pass

    def resume_all(self) -> None:
        """Resume scheduled background tasks."""
        global GLOBAL_PAUSED
        with self._lock:
            GLOBAL_PAUSED = False
            if self._scheduler is not None and APSCHEDULER_AVAILABLE:
                try:
                    self._scheduler.resume()
                except Exception:
                    pass

    def is_paused(self) -> bool:
        """Checks if global kill switch is active."""
        global GLOBAL_PAUSED
        return GLOBAL_PAUSED

    def list_tasks(self) -> List[Dict[str, Any]]:
        """Returns all scheduled tasks with next_run_time and trigger metadata."""
        with self._lock:
            tasks_list = []
            for name, info in self._tasks.items():
                next_time = info.get("next_run_time") or info.get("next_run", "Scheduled")
                if self._scheduler is not None and APSCHEDULER_AVAILABLE:
                    try:
                        job = self._scheduler.get_job(name)
                        if job and job.next_run_time:
                            next_time = job.next_run_time.isoformat()
                    except Exception:
                        pass
                tasks_list.append({
                    "name": name,
                    "type": info.get("type", "CRON"),
                    "trigger_type": info.get("trigger_type", info.get("type", "CRON")),
                    "cron_expr": info.get("cron_expr"),
                    "config": info.get("config", {}),
                    "action": info.get("action"),
                    "requires_approval": info.get("requires_approval", False),
                    "args": info.get("args", []),
                    "enabled": info.get("enabled", True),
                    "next_run": next_time,
                    "next_run_time": next_time,
                })
            return tasks_list

    def _log_execution(self, task_name: str, action: str, result: Any, approved: bool = True) -> None:
        """Logs task execution to KnowledgeStore.task_log."""
        try:
            from knowledge.sqlite_store import KnowledgeStore
            ks = KnowledgeStore()
            ks.log_task_execution(
                task_name=task_name,
                action=action,
                result=result,
                approved=approved,
            )
        except Exception as e:
            logger.debug(f"Task log notice: {e}")

    def shutdown(self) -> None:
        """Shuts down APScheduler gracefully."""
        if self._scheduler is not None and APSCHEDULER_AVAILABLE:
            try:
                self._scheduler.shutdown(wait=False)
            except Exception:
                pass
