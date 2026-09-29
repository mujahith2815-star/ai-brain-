"""
Autonomous Agent Orchestration Loop.
Manages rate limiting, safety checks, execution whitelisting, approval queue,
and audit logging.
"""

import time
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from .safety import SafetyGuard
from .scheduler import TaskScheduler
from config.proactive_config import proactive_config, ProactiveConfig

logger = logging.getLogger("orvix.proactive.agent")


class AutonomousAgent:
    """
    Proactive Autonomous Agent taking whitelisted actions without user prompting,
    routing risky actions to an approval queue, and adhering to strict rate limits.
    """

    def __init__(
        self,
        agent=None,
        safety_guard: Optional[SafetyGuard] = None,
        knowledge_store=None,
        config: Optional[ProactiveConfig] = None,
    ):
        self.agent = agent
        self.safety = safety_guard or SafetyGuard()
        self.config = config or proactive_config
        self.scheduler = TaskScheduler()
        self._action_timestamps: List[float] = []
        self._paused: bool = False

        if knowledge_store is not None:
            self.store = knowledge_store
        else:
            try:
                from knowledge.sqlite_store import KnowledgeStore
                self.store = KnowledgeStore()
            except Exception:
                self.store = None

        # Bootstrap triggers and wire handlers
        try:
            self.scheduler.bootstrap_from_triggers()
            for t in self.scheduler.list_tasks():
                t_name = t["name"]
                t_action = t.get("action")
                t_appr = t.get("requires_approval", False)
                self.scheduler._callbacks[t_name] = (
                    lambda name=t_name, act=t_action, appr=t_appr: self.handle_task_fire(name, act, appr)
                )
        except Exception as e:
            logger.debug(f"Bootstrap triggers notice: {e}")

    def pause(self) -> None:
        """Emergency pause: immediately halts all autonomous actions."""
        self._paused = True
        self.scheduler.pause_all()

    def resume(self) -> None:
        """Resumes autonomous operations."""
        self._paused = False
        self.scheduler.resume_all()

    def is_paused(self) -> bool:
        """Checks if autonomous agent or scheduler is paused."""
        return self._paused or self.scheduler.is_paused()

    def check_rate_limit(self) -> bool:
        """
        Enforces maximum actions per hour rate limit.
        Returns True if within limits, False if rate limited.
        """
        now = time.time()
        one_hour_ago = now - 3600.0
        self._action_timestamps = [t for t in self._action_timestamps if t > one_hour_ago]
        return len(self._action_timestamps) < self.config.max_actions_per_hour

    def propose_action(self, name: str, reason: str, tool: str, args: Any) -> int:
        """Adds an action to the user approval queue and returns the queue ID."""
        if self.store is not None:
            q_id = self.store.queue_approval(name, reason, tool, args)
            return q_id
        return -1

    def get_approval_queue(self) -> List[Dict[str, Any]]:
        """Returns all pending actions requiring user review."""
        if self.store is not None:
            return self.store.get_pending_approvals()
        return []

    def approve_action(self, action_id: int) -> Dict[str, Any]:
        """Approves and immediately executes a queued action."""
        if self.store is None:
            return {"status": "FAILED", "error": "KnowledgeStore unavailable"}

        # Find queued action details
        pending = self.store.get_pending_approvals()
        target = next((p for p in pending if p["id"] == action_id), None)
        if not target:
            return {"status": "NOT_FOUND", "action_id": action_id}

        ok = self.store.resolve_approval(action_id, approve=True)
        if not ok:
            return {"status": "FAILED", "action_id": action_id}

        # Execute the approved action
        tool = target["tool"]
        args = target["args"]
        exec_res = self._execute_tool_direct(tool, args)

        # Log approval resolution to task_log
        self.store.log_task_execution(
            task_name=f"approved:{target['action_name']}",
            action=f"{tool}({args})",
            result=exec_res,
            approved=True,
        )
        return {"status": "EXECUTED", "action_id": action_id, "result": exec_res}

    def reject_action(self, action_id: int) -> Dict[str, Any]:
        """Rejects a queued action."""
        if self.store is None:
            return {"status": "FAILED", "error": "KnowledgeStore unavailable"}

        ok = self.store.resolve_approval(action_id, approve=False)
        return {"status": "REJECTED" if ok else "FAILED", "action_id": action_id}

    def execute_action(
        self,
        name: str,
        tool: str,
        args: Dict[str, Any],
        requires_approval: bool = False,
    ) -> Dict[str, Any]:
        """
        Main autonomous execution pipeline:
        1. Check kill switch
        2. Check rate limit
        3. Validate safety
        4. Queue or Execute
        5. Log decision and results
        """
        # 1. Kill Switch
        if self.is_paused():
            logger.info(f"Action '{name}' skipped: Agent is paused.")
            if self.store:
                self.store.log_task_execution(name, f"{tool}({args})", "SKIPPED: kill switch paused", approved=False)
            return {"status": "SKIPPED", "reason": "kill switch paused"}

        # 2. Rate Limit
        if not self.check_rate_limit():
            logger.warning(f"Action '{name}' skipped: Rate limit of {self.config.max_actions_per_hour}/hr exceeded.")
            if self.store:
                self.store.log_task_execution(name, f"{tool}({args})", "SKIPPED: rate limit exceeded", approved=False)
            return {"status": "SKIPPED", "reason": "rate limit exceeded"}

        # 3. Safety Check
        allowed, reason = self.safety.validate_action(tool, args)

        # 4. Approval Routing
        if requires_approval or not allowed or self.safety.is_destructive(tool, args):
            q_id = self.propose_action(name, reason, tool, args)
            if self.store:
                self.store.log_task_execution(name, f"{tool}({args})", f"QUEUED: {reason}", approved=False)
            return {"status": "QUEUED", "action_id": q_id, "reason": reason}

        # 5. Whitelisted Execution
        if self.store:
            self.store.log_task_execution(name, f"{tool}({args})", "EXECUTING", approved=True)

        res = self._execute_tool_direct(tool, args)
        self._action_timestamps.append(time.time())

        if self.store:
            self.store.log_task_execution(name, f"{tool}({args})", res, approved=True)

        return {"status": "EXECUTED", "result": res}

    def _execute_tool_direct(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """Executes a tool via LlamaToolAgent or ToolExecutor."""
        try:
            if self.agent is not None:
                if hasattr(self.agent, "run_restricted"):
                    return self.agent.run_restricted(f"Execute {tool_name} with {args}", self.safety.ALLOWED_TOOLS_WHITELIST)
                elif hasattr(self.agent, "call_tool"):
                    return self.agent.call_tool(tool_name, args)

            from tools.executor import execute_tool
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop.run_until_complete(execute_tool(tool_name, args))
        except Exception as e:
            return f"Execution error: {e}"

    def handle_task_fire(
        self,
        task_name: str,
        action: Any = None,
        requires_approval: bool = False,
        trigger_type: str = "CRON",
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Invoked when a scheduled task or trigger fires:
        a) Check PAUSED kill switch
        b) Check rate limit
        c) If requires_approval -> queue_approval()
        d) Else -> run_restricted() with whitelist
        """
        # a) Check kill switch
        if self.is_paused():
            logger.info(f"Task '{task_name}' skipped: Agent is paused.")
            if self.store:
                self.store.log_task_execution(task_name, str(action), "SKIPPED: kill switch paused", approved=False)
            return {"status": "SKIPPED", "reason": "kill switch paused"}

        # b) Check rate limit
        if not self.check_rate_limit():
            logger.warning(f"Task '{task_name}' skipped: Rate limit exceeded.")
            if self.store:
                self.store.log_task_execution(task_name, str(action), "SKIPPED: rate limit exceeded", approved=False)
            return {"status": "SKIPPED", "reason": "rate limit exceeded"}

        # Determine tool and arguments
        tool = "autonomous_task"
        args = {"task": action}
        if isinstance(action, dict):
            tool = action.get("tool", "autonomous_task")
            args = action.get("args", {})
            if self.safety.is_destructive(tool, args):
                requires_approval = True
        elif isinstance(action, str):
            tool = "run_task"
            args = {"instruction": action}
            if self.safety.DESTRUCTIVE_PATTERN.search(action):
                requires_approval = True

        # c) If requires_approval -> queue_approval()
        if requires_approval:
            q_id = self.propose_action(task_name, f"Trigger '{task_name}' mandates approval", tool, args)
            if self.store:
                self.store.log_task_execution(task_name, str(action), f"QUEUED: requires approval (ID: {q_id})", approved=False)
            return {"status": "QUEUED", "action_id": q_id, "reason": "requires approval"}

        # d) Else -> run_restricted() with whitelist
        if self.store:
            self.store.log_task_execution(task_name, str(action), "EXECUTING", approved=True)

        res = None
        if task_name == "daily_backup" or "backup_orvix.py" in str(action):
            try:
                from scripts.backup_orvix import create_backup
                b_res = create_backup()
                res = f"Backup status: {b_res.get('status')} ({b_res.get('path', '')})"
            except Exception as be:
                res = f"Backup error: {be}"
        elif task_name == "daily_health_check" or "daily health check" in str(action).lower():
            try:
                from scripts.daily_health_check import run_health_check
                h_res = run_health_check()
                st_label = "HEALTHY" if h_res.get("healthy") else "UNHEALTHY"
                res = f"Health check status: {st_label} ({h_res.get('passed_checks', 0)}/{h_res.get('total_checks', 0)} passed)"
            except Exception as he:
                res = f"Health check error: {he}"
        elif self.agent is not None and hasattr(self.agent, "run_restricted"):
            res = self.agent.run_restricted(str(action), self.safety.ALLOWED_TOOLS_WHITELIST)
        elif isinstance(action, dict):
            res = self._execute_tool_direct(tool, args)
        else:
            res = f"Executed autonomous task '{task_name}': {action}"

        self._action_timestamps.append(time.time())
        if self.store:
            self.store.log_task_execution(task_name, str(action), res, approved=True)

        return {"status": "EXECUTED", "result": res}
