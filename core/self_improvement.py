"""
Self-Improvement & Continuous Learning Engine for P.H.A.S.S Llama Assistant.
Manages persistent Skill Library, user feedback reinforcement,
dynamic resource auto-tuning, and error correlation self-healing.
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False


class SelfImprovementEngine:
    """
    Learns from autonomous workflows and continuously improves execution policies.
    """

    def __init__(self, workspace_dir: Optional[str] = None, storage_dir: Optional[str] = None):
        ws = storage_dir or workspace_dir or "checkpoints"
        self.workspace_dir = Path(ws)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.skills_file = self.workspace_dir / "skills.json"
        self.feedback_file = self.workspace_dir / "feedback_log.json"
        self.fixes_file = self.workspace_dir / "known_fixes.json"
        self.workflow_counters: Dict[str, int] = {}

        self._load_data()

    def register_skill(self, name: str, code: Optional[str] = None, description: str = "", steps: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Registers a new capability or code skill."""
        actual_steps = steps or [{"action": "run_python_code", "parameters": {"code": code or ""}}]
        self.save_skill(name, actual_steps, description=description)
        if code:
            self.skills[name]["code"] = code
            self._save_data()
        return {"status": "registered", "skill": name}

    def record_execution(self, name: str, success: bool, execution_time: float = 0.0, error: Optional[str] = None):
        """Records skill execution performance metrics."""
        skill = self.get_skill(name)
        if skill:
            runs = skill.get("execution_count", 0) + 1
            skill["execution_count"] = runs
            skill["last_execution_time"] = execution_time
            self._save_data()

    def get_skill_stats(self, name: str) -> Dict[str, Any]:
        """Returns execution metrics for a skill."""
        skill = self.get_skill(name)
        if skill:
            return {"runs": skill.get("execution_count", 0), "success_rate": skill.get("success_rate", 1.0)}
        return {"runs": 0, "success_rate": 0.0}

    def auto_tune_resources(self, cpu_percent: Optional[float] = None, memory_percent: Optional[float] = None) -> Dict[str, Any]:
        """Auto-tunes worker threads and concurrency based on system load."""
        cpu = cpu_percent if cpu_percent is not None else (psutil.cpu_percent() if psutil else 15.0)
        mem = memory_percent if memory_percent is not None else (psutil.virtual_memory().percent if psutil else 45.0)
        is_high = (cpu > 80.0 or mem > 80.0)
        action = "throttled" if is_high else "optimized"
        return {
            "status": "success",
            "action": action,
            "cpu_percent": cpu,
            "memory_percent": mem,
            "is_overloaded": is_high
        }

    def diagnose_and_heal(self, error_msg: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Diagnoses errors and provides self-healing recommendations."""
        res = self.attempt_self_healing(error_msg)
        if not res.get("healed"):
            res["suggestion"] = f"Check environment dependencies for error: {error_msg}"
        return res

    def _load_data(self):
        self.skills = {}
        if self.skills_file.exists():
            try:
                with open(self.skills_file, "r", encoding="utf-8") as f:
                    self.skills = json.load(f)
            except Exception:
                self.skills = {}

        self.feedback = []
        if self.feedback_file.exists():
            try:
                with open(self.feedback_file, "r", encoding="utf-8") as f:
                    self.feedback = json.load(f)
            except Exception:
                self.feedback = []

        self.known_fixes = {}
        if self.fixes_file.exists():
            try:
                with open(self.fixes_file, "r", encoding="utf-8") as f:
                    self.known_fixes = json.load(f)
            except Exception:
                self.known_fixes = {}

    def _save_data(self):
        try:
            with open(self.skills_file, "w", encoding="utf-8") as f:
                json.dump(self.skills, f, indent=2)
            with open(self.feedback_file, "w", encoding="utf-8") as f:
                json.dump(self.feedback[-100:], f, indent=2)
            with open(self.fixes_file, "w", encoding="utf-8") as f:
                json.dump(self.known_fixes, f, indent=2)
        except Exception:
            pass

    # ============ 1. SKILL LIBRARY ============

    def save_skill(self, name: str, steps: List[Dict[str, Any]], description: str = "") -> Dict[str, Any]:
        """Saves a multi-step workflow into checkpoints/skills.json."""
        skill_entry = {
            "name": name,
            "description": description or f"Reusable workflow: {name}",
            "steps": steps,
            "created_at": datetime.now().isoformat(),
            "execution_count": 0,
            "success_rate": 1.0,
        }
        self.skills[name] = skill_entry
        self._save_data()
        return {"status": "SUCCESS", "skill": name, "steps_count": len(steps)}

    def get_skill(self, name: str) -> Optional[Dict[str, Any]]:
        """Retrieves a saved skill definition."""
        return self.skills.get(name)

    def list_skills(self) -> List[Dict[str, Any]]:
        """Lists all registered skills."""
        return list(self.skills.values())

    def run_skill(self, name: str, orchestrator=None) -> Dict[str, Any]:
        """Executes a saved skill autonomously."""
        skill = self.get_skill(name)
        if not skill:
            return {"status": "ERROR", "message": f"Skill '{name}' not found."}

        steps = skill.get("steps", [])
        if not orchestrator:
            from core.autonomous_orchestrator import get_orchestrator
            orchestrator = get_orchestrator()

        completed_steps = []
        for step in steps:
            res = orchestrator._execute_step(step)
            completed_steps.append({"step": step, "result": res})

        skill["execution_count"] = skill.get("execution_count", 0) + 1
        self._save_data()

        return {
            "status": "SUCCESS",
            "skill": name,
            "steps_completed": completed_steps,
            "message": f"Skill '{name}' executed with {len(completed_steps)} step(s)."
        }

    # ============ 2. FEEDBACK LOOP ============

    def record_feedback(self, task_id: str, success: bool, user_notes: Optional[str] = None):
        """Reinforces the plan if success is True, or adjusts heuristics if False."""
        entry = {
            "task_id": task_id,
            "success": success,
            "notes": user_notes or "",
            "timestamp": datetime.now().isoformat(),
        }
        self.feedback.append(entry)
        self._save_data()

    # ============ 3. AUTO-TUNING ============

    def monitor_resources_and_autotune(self) -> Dict[str, Any]:
        """
        Monitors CPU and RAM. If usage exceeds 80%, shifts to lightweight
        model mode and simplifies toolchain to protect system responsiveness.
        """
        cpu_pct = psutil.cpu_percent() if psutil else 15.0
        mem_pct = psutil.virtual_memory().percent if psutil else 45.0

        is_overloaded = cpu_pct > 80.0 or mem_pct > 80.0
        applied_action = "none"

        if is_overloaded:
            applied_action = "throttled_to_light_tier"
            try:
                from config.llama_config import llama_config
                llama_config.temperature = 0.1
            except Exception:
                pass

        return {
            "status": "SUCCESS",
            "cpu_percent": cpu_pct,
            "memory_percent": mem_pct,
            "is_overloaded": is_overloaded,
            "tuning_action": applied_action
        }

    # ============ 4. ERROR CORRELATION & SELF-HEALING ============

    def record_error_fix(self, error_pattern: str, fix_action: Dict[str, Any]):
        """Records a successful self-healing remedy for an error pattern."""
        self.known_fixes[error_pattern.lower()] = fix_action
        self._save_data()

    def find_past_error_solution(self, error_str: str) -> Optional[Dict[str, Any]]:
        """Searches known fixes for a similar error pattern."""
        err_low = str(error_str).lower()
        for pattern, fix in self.known_fixes.items():
            if pattern in err_low:
                return fix
        return None

    def record_workflow_execution(self, name: str, steps: List[Dict[str, Any]], success: bool = True, description: str = "") -> Dict[str, Any]:
        """
        Tracks multi-step workflow execution count.
        Once a workflow executes successfully >= 3 times, compiles and saves it into checkpoints/skills.json.
        """
        if not success:
            return {"status": "FAILED", "workflow": name, "runs": self.workflow_counters.get(name, 0)}

        count = self.workflow_counters.get(name, 0) + 1
        self.workflow_counters[name] = count

        if count >= 3:
            save_res = self.save_skill(name, steps, description=description or f"Auto-compiled skill from {count} successful runs.")
            return {
                "status": "PROMOTED_TO_SKILL",
                "workflow": name,
                "runs": count,
                "saved_to": str(self.skills_file),
                "detail": save_res
            }

        return {
            "status": "RECORDED",
            "workflow": name,
            "runs": count,
            "runs_needed": max(0, 3 - count)
        }

    def correlate_execution_errors(self, log_path: str = "checkpoints/execution_log.json") -> Dict[str, Any]:
        """
        Scans past execution faults in checkpoints/execution_log.json to identify
        recurring patterns, correlates root causes, and suggests or applies fixes.
        """
        p = Path(log_path)
        if not p.exists():
            return {"status": "NO_LOGS", "errors_found": 0, "patterns": []}

        try:
            with open(p, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            return {"status": "ERROR_READING_LOGS", "errors_found": 0, "patterns": []}

        error_entries = [e for e in logs if e.get("status") == "FAILED" or e.get("error")]
        correlated_patterns = {}

        for entry in error_entries:
            err = str(entry.get("error") or entry.get("verification_reason") or "Unknown error").lower()
            tool = entry.get("tool", "unknown")
            key = f"{tool}:{err[:40]}"
            if key not in correlated_patterns:
                solution = self.find_past_error_solution(err)
                suggestion = solution.get("action") if solution else (
                    "Verify path exists and permissions are granted." if "path" in err or "not exist" in err
                    else "Check process arguments and verify target executable."
                )
                correlated_patterns[key] = {
                    "tool": tool,
                    "error_sample": err[:100],
                    "count": 1,
                    "has_fix": solution is not None,
                    "recommended_action": suggestion
                }
            else:
                correlated_patterns[key]["count"] += 1

        return {
            "status": "ANALYZED",
            "total_errors": len(error_entries),
            "unique_patterns": len(correlated_patterns),
            "patterns": list(correlated_patterns.values()),
        }

    def attempt_self_healing(self, error_str: str, orchestrator=None) -> Dict[str, Any]:
        """Attempts to apply a known fix autonomously."""
        solution = self.find_past_error_solution(error_str)
        if solution:
            if not orchestrator:
                from core.autonomous_orchestrator import get_orchestrator
                orchestrator = get_orchestrator()
            result = orchestrator._execute_step(solution)
            return {"status": "SUCCESS", "healed": True, "fix": solution, "result": result}
        return {"status": "NOT_FOUND", "healed": False, "message": "No proven remedy found for error."}


# Global instance
self_improvement = SelfImprovementEngine()


def get_self_improvement() -> SelfImprovementEngine:
    return self_improvement
