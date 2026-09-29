"""
Hooks and Interceptors Management Tool Module for P.H.A.S.S Sphere & Llama Assistant.
Provides operational tools to register, list, toggle, and inspect lifecycle
interceptors and execution audit logs.
"""

from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional
from core.hook_engine import hook_engine

logger = logging.getLogger("phass.tools.hooks_interceptors")


def register_interceptor(
    hook_point: str,
    hook_name: str,
    rule: str,
    action: str = "allow",  # "allow", "block", "log"
    priority: int = 100,
) -> Dict[str, Any]:
    """
    Registers a dynamic policy rule interceptor at a lifecycle hook point.
    Rule can specify string patterns or conditions to evaluate.
    """
    hp = hook_point.strip().lower()
    if hp not in hook_engine.VALID_HOOK_POINTS:
        return {
            "status": "FAILED",
            "error": f"Invalid hook point '{hook_point}'. Valid: {list(hook_engine.VALID_HOOK_POINTS)}",
        }

    def _dynamic_interceptor_callback(*args, **kwargs):
        # Evaluation logic based on rule
        target_str = str(args) + str(kwargs)
        if rule.lower() in target_str.lower():
            if action == "block":
                return False, f"Blocked by rule interceptor '{hook_name}': matched '{rule}'"
        return True, "Passed"

    success = hook_engine.register_hook(
        name=hook_name,
        hook_point=hp,
        callback=_dynamic_interceptor_callback,
        priority=priority,
        description=f"User-registered {action} rule for '{rule}'",
    )

    return {
        "status": "SUCCESS" if success else "FAILED",
        "hook_name": hook_name,
        "hook_point": hp,
        "rule": rule,
        "action": action,
        "message": f"Interceptor '{hook_name}' registered at '{hp}'.",
    }


def list_interceptors() -> Dict[str, Any]:
    """Lists all active and registered lifecycle interceptor hooks."""
    hooks = hook_engine.list_hooks()
    return {
        "status": "SUCCESS",
        "total_hooks": len(hooks),
        "hooks": hooks,
    }


def toggle_interceptor(hook_name: str, enabled: bool) -> Dict[str, Any]:
    """Enables or disables an existing interceptor hook."""
    success = hook_engine.enable_hook(hook_name, enabled=enabled)
    if not success:
        return {"status": "FAILED", "error": f"Hook '{hook_name}' not found."}
    return {
        "status": "SUCCESS",
        "hook_name": hook_name,
        "enabled": enabled,
        "message": f"Hook '{hook_name}' set to enabled={enabled}.",
    }


def audit_interceptor_logs(limit: int = 50) -> Dict[str, Any]:
    """Retrieves recent interceptor audit trail logs."""
    logs = hook_engine.get_audit_logs(limit=limit)
    return {
        "status": "SUCCESS",
        "log_count": len(logs),
        "audit_logs": logs,
    }
