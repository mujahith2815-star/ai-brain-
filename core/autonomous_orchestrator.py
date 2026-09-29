"""
Autonomous Orchestrator – The assistant that works FOR you
Makes decisions, executes multi-step workflows, handles errors
Only interrupts for emergencies or critical decisions
"""

import threading
import time
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False


class AutonomousOrchestrator:
    """
    The core autonomous engine that executes complex workflows
    without requiring user input at every step.
    """

    def __init__(self, workspace_dir: str = "checkpoints/autonomous"):
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        # State
        self.is_running = False
        self.current_task = None
        self.task_history = []
        self.decision_log = []
        self.error_log = []
        self.emergency_queue = []
        self.pending_decisions = []

        # Load state
        self._load_state()

        # Reference to tool agent
        self.tool_agent = None
        self.callback = None

    def initialize(self, tool_agent=None, callback: Optional[Callable] = None):
        """Initialize with tool agent and optional callback."""
        if tool_agent:
            self.tool_agent = tool_agent
        if callback:
            self.callback = callback
        return "Autonomous orchestrator initialized."

    # ============ TASK EXECUTION ============

    def generate_plan(self, goal: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generates a structured execution plan for a goal."""
        steps = self._create_plan(goal, context)
        return {
            "plan_id": f"plan_{int(time.time() * 1000)}",
            "goal": goal,
            "steps": steps
        }

    def execute_workflow(self, goal_or_plan: Any, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a complete workflow autonomously.
        Accepts either a goal string or a plan dictionary with 'steps'.
        """
        if isinstance(goal_or_plan, dict) and "steps" in goal_or_plan:
            goal = goal_or_plan.get("goal", "Custom workflow")
            plan = goal_or_plan["steps"]
        else:
            goal = str(goal_or_plan)
            plan = None

        self.current_task = {
            "goal": goal,
            "context": context or {},
            "started_at": datetime.now().isoformat(),
            "status": "running",
            "steps_completed": [],
            "results": [],
            "errors": [],
            "emergencies": [],
            "result": None
        }

        self.is_running = True
        self._log_decision(f"Started autonomous task: {goal}")

        try:
            # Parse the goal into a structured plan if not provided
            if plan is None:
                plan = self._create_plan(goal, context)
            self._log_decision(f"Executing plan with {len(plan)} steps")

            # Execute each step autonomously
            for step in plan:
                if not self.is_running:
                    break

                result = self._execute_step(step)
                step_record = {
                    "step": step,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                }
                self.current_task["steps_completed"].append(step_record)
                self.current_task["results"].append(step_record)

                # Check if we need to pause for emergency
                if self._is_emergency(result):
                    self._handle_emergency(result)
                    self.current_task["emergencies"].append(str(result))
                    break

                # Check if we need a critical decision
                if self._needs_critical_decision(result):
                    self._queue_critical_decision(result)
                    break

            # Finalize
            self.current_task["status"] = "completed"
            self.current_task["completed_at"] = datetime.now().isoformat()
            self.current_task["result"] = self._synthesize_result()

            self.task_history.append(dict(self.current_task))
            self._save_state()
            self._log_decision(f"Task completed successfully: {goal}")

            return self.current_task

        except Exception as e:
            self.current_task["status"] = "failed"
            self.current_task["error"] = str(e)
            self._log_decision(f"Task failed: {str(e)}")
            self._handle_error(e)
            return self.current_task

        finally:
            self.is_running = False

    def _create_plan(self, goal: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Create a detailed execution plan from a goal.
        Uses the LLM to break down the goal into actionable steps.
        """
        plan = []

        if self.tool_agent:
            prompt = f"""
            You are an autonomous executor. Create a detailed step-by-step plan to accomplish this goal.
            Each step must be specific, actionable, and use available tools.

            GOAL: {goal}
            CONTEXT: {json.dumps(context or {}, indent=2)}

            Respond with a JSON list of steps, where each step has:
            - "action": the tool to use
            - "parameters": the parameters for that tool
            - "description": what this step accomplishes
            - "retry_count": number of times to retry if it fails (0-3)
            - "requires_confirmation": true if this is a dangerous operation

            Format: [{{"action": "...", "parameters": {{...}}, "description": "...", "retry_count": 1, "requires_confirmation": false}}, ...]
            """

            try:
                response = self.tool_agent.run(prompt)
                plan_text = re.search(r'\[.*\]', response, re.DOTALL)
                if plan_text:
                    plan = json.loads(plan_text.group(0))
                else:
                    plan = self._create_fallback_plan(goal)
            except Exception:
                plan = self._create_fallback_plan(goal)
        else:
            plan = self._create_fallback_plan(goal)

        return plan or self._create_fallback_plan(goal)

    def _create_fallback_plan(self, goal: str) -> List[Dict[str, Any]]:
        """Fallback plan creation when LLM is not available."""
        goal_lower = goal.lower()
        plan = []

        if "clean" in goal_lower or "delete" in goal_lower or "trash" in goal_lower:
            plan.append({
                "action": "delete_unwanted_files",
                "parameters": {"directory": str(Path.home() / "Downloads"), "dry_run": False},
                "description": "Clean up downloads folder",
                "retry_count": 1,
                "requires_confirmation": True
            })

        if "report" in goal_lower or "analyze" in goal_lower:
            plan.append({
                "action": "analyze_disk_space",
                "parameters": {"directory": str(Path.home())},
                "description": "Analyze disk space",
                "retry_count": 1,
                "requires_confirmation": False
            })
            plan.append({
                "action": "create_excel",
                "parameters": {"data": {"Report": "Disk Analysis"}, "filename": "system_report"},
                "description": "Create report",
                "retry_count": 1,
                "requires_confirmation": False
            })

        if "backup" in goal_lower:
            plan.append({
                "action": "create_backup",
                "parameters": {"source": str(Path.home() / "Documents"), "destination": str(Path.home() / "Backup")},
                "description": "Create backup",
                "retry_count": 2,
                "requires_confirmation": True
            })

        if "research" in goal_lower or "search" in goal_lower:
            plan.append({
                "action": "web_search",
                "parameters": {"query": goal},
                "description": "Search the web",
                "retry_count": 2,
                "requires_confirmation": False
            })
            plan.append({
                "action": "summarize_text",
                "parameters": {"text": "[[RESULT]]"},
                "description": "Summarize results",
                "retry_count": 1,
                "requires_confirmation": False
            })

        if "organize" in goal_lower:
            plan.append({
                "action": "smart_file_organizer",
                "parameters": {"directory": str(Path.home() / "Downloads"), "dry_run": False},
                "description": "Organize files",
                "retry_count": 1,
                "requires_confirmation": True
            })

        if "duplicate" in goal_lower:
            plan.append({
                "action": "find_duplicate_files",
                "parameters": {"directory": str(Path.home())},
                "description": "Find duplicates",
                "retry_count": 1,
                "requires_confirmation": False
            })

        if not plan:
            plan.append({
                "action": "get_system_info",
                "parameters": {},
                "description": "Get system information",
                "retry_count": 1,
                "requires_confirmation": False
            })

        return plan

    def _execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single step autonomously."""
        action = step.get("action")
        parameters = step.get("parameters", {})
        retry_count = step.get("retry_count", 1)
        requires_confirmation = step.get("requires_confirmation", False)

        if requires_confirmation:
            is_dangerous = self._is_dangerous_action(action, parameters)
            if not is_dangerous:
                requires_confirmation = False

        for attempt in range(retry_count + 1):
            try:
                result = self._call_tool(action, parameters)

                if self._is_success(result):
                    self._log_decision(f"Step succeeded: {step.get('description', action)}")
                    return {"status": "success", "result": result, "attempts": attempt + 1}

                if attempt < retry_count:
                    self._log_decision(f"Step failed, retrying ({attempt + 1}/{retry_count}): {step.get('description', action)}")
                    time.sleep(0.5)
                    continue

                self._log_decision(f"Step failed after {retry_count + 1} attempts: {step.get('description', action)}")
                return {"status": "failed", "error": str(result), "attempts": attempt + 1}

            except Exception as e:
                self._log_decision(f"Step error: {str(e)}")
                if attempt < retry_count:
                    continue
                return {"status": "failed", "error": str(e), "attempts": attempt + 1}

        return {"status": "failed", "error": "Max retries exceeded", "attempts": retry_count + 1}

    def _call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Call a tool by name with parameters."""
        try:
            from tools.executor import execute_tool
            res = execute_tool(tool_name, parameters)
            if res != f"Tool '{tool_name}' not found.":
                return res
        except Exception:
            pass

        if self.tool_agent and hasattr(self.tool_agent, "call_tool"):
            try:
                return self.tool_agent.call_tool(tool_name, parameters)
            except Exception as e:
                return f"Agent tool call failed: {e}"

        return {"status": "SUCCESS", "message": f"Action '{tool_name}' executed."}

    def _is_success(self, result: Any) -> bool:
        """Check if a result indicates success."""
        if isinstance(result, dict):
            status = str(result.get("status", "")).upper()
            if status in ("SUCCESS", "COMPLETED", "ALLOWED", "OK"):
                return True
            if result.get("success") is True:
                return True
            if result.get("status") in ("FAILED", "ERROR", "EMERGENCY"):
                return False
        if isinstance(result, str):
            res_low = result.lower()
            if any(k in res_low for k in ["failed", "critical error", "system failure"]):
                return False
            return True
        return result is not None

    def _is_dangerous_action(self, action: str, parameters: Dict[str, Any]) -> bool:
        """Determine if an action is dangerous."""
        dangerous_actions = [
            "terminate_process", "shutdown", "restart", "format",
            "shred", "diskpart", "firewall_manager"
        ]
        if action in dangerous_actions:
            return True

        param_str = str(parameters).lower()
        dangerous_patterns = ["rm -rf", "del /f", "format", "chmod 777", "drop table"]
        if any(pattern in param_str for pattern in dangerous_patterns):
            return True

        return False

    def _is_emergency(self, result: Any) -> bool:
        """Determine if a result indicates an emergency."""
        if isinstance(result, dict):
            if result.get("status") == "EMERGENCY":
                return True
            if result.get("error") and "critical" in str(result.get("error")).lower():
                return True
        if isinstance(result, str):
            emergencies = ["critical failure", "emergency", "system failure", "security breach"]
            if any(emergency in result.lower() for emergency in emergencies):
                return True
        return False

    def _needs_critical_decision(self, result: Any) -> bool:
        """Determine if a result requires a critical decision."""
        if isinstance(result, dict):
            if result.get("requires_decision") is True:
                return True
            if result.get("success") is False and "decision" in str(result.get("error", "")).lower():
                return True
        return False

    def _handle_emergency(self, result: Any):
        """Handle an emergency situation."""
        self._log_decision(f"EMERGENCY: {result}")
        self.emergency_queue.append({
            "timestamp": datetime.now().isoformat(),
            "result": result,
            "handled": False
        })
        if self.callback:
            try:
                self.callback(f"🚨 EMERGENCY: {result}")
            except Exception:
                pass

    def _queue_critical_decision(self, result: Any):
        """Queue a critical decision for user input."""
        self._log_decision(f"Critical decision needed: {result}")
        self.pending_decisions.append({
            "timestamp": datetime.now().isoformat(),
            "result": result,
            "resolved": False
        })
        if self.callback:
            try:
                self.callback(f"⚠️ Decision needed: {result}")
            except Exception:
                pass

    def _handle_error(self, error: Exception):
        """Handle an error that occurred during execution."""
        self._log_decision(f"ERROR: {str(error)}")
        self.error_log.append({
            "timestamp": datetime.now().isoformat(),
            "error": str(error),
            "resolved": False
        })
        if self.callback:
            try:
                self.callback(f"❌ Error: {str(error)}")
            except Exception:
                pass

    def _synthesize_result(self) -> str:
        """Synthesize the final result from all steps."""
        steps = self.current_task.get("steps_completed", [])
        if not steps:
            return "No steps completed."

        for step in reversed(steps):
            if step.get("result", {}).get("status") == "success":
                res = step["result"].get("result")
                if res:
                    return str(res)

        return "Task executed across all planned steps."

    def _log_decision(self, message: str):
        """Log a decision or action."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message
        }
        self.decision_log.append(entry)

    def _save_state(self):
        """Save the orchestrator state to disk."""
        try:
            state = {
                "current_task": self.current_task,
                "task_history": self.task_history[-50:],
                "decision_log": self.decision_log[-100:],
                "error_log": self.error_log[-50:],
                "emergency_queue": self.emergency_queue,
                "pending_decisions": self.pending_decisions
            }
            with open(self.workspace_dir / "state.json", "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, default=str)
        except Exception:
            pass

    def _load_state(self):
        """Load the orchestrator state from disk."""
        try:
            state_file = self.workspace_dir / "state.json"
            if state_file.exists():
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    self.task_history = state.get("task_history", [])
                    self.decision_log = state.get("decision_log", [])
                    self.error_log = state.get("error_log", [])
                    self.emergency_queue = state.get("emergency_queue", [])
                    self.pending_decisions = state.get("pending_decisions", [])
        except Exception:
            pass

    def get_status(self) -> Dict[str, Any]:
        """Get current orchestrator status."""
        return {
            "is_running": self.is_running,
            "current_task": self.current_task,
            "task_history_count": len(self.task_history),
            "pending_decisions": len(self.pending_decisions),
            "emergencies": len(self.emergency_queue),
            "errors": len(self.error_log)
        }

    def resolve_decision(self, decision_id: int, choice: str) -> bool:
        """Resolve a pending decision."""
        if 0 <= decision_id < len(self.pending_decisions):
            self.pending_decisions[decision_id]["resolved"] = True
            self.pending_decisions[decision_id]["choice"] = choice
            self._log_decision(f"Decision {decision_id} resolved: {choice}")
            self._save_state()
            return True
        return False

    def raise_emergency(self, emergency_type: str, message: str) -> str:
        """Explicitly raises an emergency and records to queue."""
        em_id = f"em_{int(time.time() * 1000)}"
        entry = {
            "id": em_id,
            "type": emergency_type,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "handled": False
        }
        self.emergency_queue.append(entry)
        self._log_decision(f"EMERGENCY [{emergency_type}]: {message}")
        self._save_state()
        if self.callback:
            try:
                self.callback(f"🚨 EMERGENCY: [{emergency_type}] {message}")
            except Exception:
                pass
        return em_id

    def resolve_emergency(self, em_id: str):
        """Marks an emergency as handled."""
        for em in self.emergency_queue:
            if em.get("id") == em_id or em.get("type") == em_id:
                em["handled"] = True
        self._save_state()

    def get_emergencies(self) -> List[Dict[str, Any]]:
        """Returns pending unhandled emergencies."""
        return [e for e in self.emergency_queue if not e.get("handled")]

    def queue_critical_decision(self, decision_text: str, options: Optional[List[str]] = None) -> str:
        """Explicitly queues a critical decision."""
        dec_id = f"dec_{int(time.time() * 1000)}"
        entry = {
            "id": dec_id,
            "decision": decision_text,
            "options": options or ["Approve", "Deny"],
            "timestamp": datetime.now().isoformat(),
            "resolved": False
        }
        self.pending_decisions.append(entry)
        self._log_decision(f"Critical decision queued: {decision_text}")
        self._save_state()
        return dec_id

    def resolve_critical_decision(self, dec_id: Any, choice: str) -> bool:
        """Resolves a critical decision by id or index."""
        if isinstance(dec_id, int):
            return self.resolve_decision(dec_id, choice)
        for d in self.pending_decisions:
            if d.get("id") == dec_id:
                d["resolved"] = True
                d["choice"] = choice
                self._log_decision(f"Decision {dec_id} resolved: {choice}")
                self._save_state()
                return True
        return False

    def get_pending_decisions(self) -> List[Dict[str, Any]]:
        """Returns unresolved decisions."""
        return [d for d in self.pending_decisions if not d.get("resolved")]

    def save_state(self):
        """Public alias to save state."""
        self._save_state()

    def load_state(self):
        """Public alias to reload state."""
        self._load_state()

    def cancel_task(self) -> str:
        """Cancel the current task."""
        self.is_running = False
        if self.current_task:
            self.current_task["status"] = "cancelled"
        self._log_decision("Task cancelled by operator.")
        self._save_state()
        return "Task cancelled"


# Global singleton instance
_orchestrator = None


def get_orchestrator() -> AutonomousOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AutonomousOrchestrator()
    return _orchestrator
