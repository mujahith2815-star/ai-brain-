"""
Hook and Interceptor Engine for P.H.A.S.S Sphere & Llama Assistant.
Provides lifecycle hooks for before_tool_call, after_tool_call,
before_model_call, after_model_call, on_error, and safety_check.
Includes pre-built confirmation guards, cryptographic audit loggers, and rate limiters.
"""

from __future__ import annotations
import time
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable, Tuple

logger = logging.getLogger("phass.core.hooks")


@dataclass
class HookRecord:
    name: str
    hook_point: str
    callback: Callable
    priority: int = 100  # Lower numbers run first
    enabled: bool = True
    description: str = ""


@dataclass
class HookAuditLog:
    timestamp: float
    hook_point: str
    hook_name: str
    status: str  # "ALLOWED", "BLOCKED", "MODIFIED", "ERROR"
    details: str
    chain_hash: str = ""


class RateLimiter:
    """Rolling window rate limiter to guard against runaway operations."""

    def __init__(self, max_calls: int = 40, window_seconds: float = 5.0):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.timestamps: List[float] = []

    def check_and_record(self) -> bool:
        now = time.time()
        self.timestamps = [t for t in self.timestamps if now - t <= self.window_seconds]
        if len(self.timestamps) >= self.max_calls:
            return False
        self.timestamps.append(now)
        return True

    def reset(self):
        self.timestamps.clear()


class HookEngine:
    """
    Central event and policy interception engine.
    Allows inspection, mutation, or cancellation of cognitive and tool actions.
    Supports before_tool_call, after_tool_call, before_model_call, after_model_call,
    on_error, safety_check / safety_hook.
    """

    VALID_HOOK_POINTS = {
        "before_tool_call",
        "after_tool_call",
        "before_model_call",
        "after_model_call",
        "on_error",
        "safety_hook",
        "safety_check",
    }

    def __init__(self):
        self._hooks: Dict[str, List[HookRecord]] = {hp: [] for hp in self.VALID_HOOK_POINTS}
        self._audit_logs: List[HookAuditLog] = []
        self._rate_limiter = RateLimiter(max_calls=40, window_seconds=5.0)
        self._last_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        self._init_built_in_safety_hooks()

    def _init_built_in_safety_hooks(self):
        """Registers essential out-of-the-box guardrail hooks."""

        def default_system_safety_guard(action: str, payload: Dict[str, Any]) -> Tuple[bool, str]:
            target_path = str(payload.get("path") or payload.get("directory") or payload.get("file_path") or "")
            from core.platform_abstraction import get_platform
            if target_path and get_platform().is_system_protected_path(target_path):
                if action in ["delete", "file_deleter", "file_shredder", "disk_cleaner"]:
                    return False, f"Safety Guard Blocked: Access to protected OS path '{target_path}' is strictly prohibited."
            return True, "Passed"

        self.register_hook(
            name="core_os_safety_guard",
            hook_point="safety_hook",
            callback=default_system_safety_guard,
            priority=10,
            description="Prevents destructive actions targeting critical operating system directories.",
        )

        self.register_hook(
            name="confirm_dangerous_actions",
            hook_point="safety_check",
            callback=self.confirm_dangerous_actions,
            priority=5,
            description="Pre-checks and flags potentially destructive actions like rm -rf, sudo, format.",
        )

    def confirm_dangerous_actions(self, action: str, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Safety check hook: flags high-risk commands (sudo, rm -rf, taskkill /F, format, dd).
        Returns (is_safe, reason).
        """
        cmd = str(payload.get("command") or payload.get("cmd") or payload.get("tool_or_command") or "")
        path = str(payload.get("path") or payload.get("target") or payload.get("file_path") or "")
        text = f"{action} {cmd} {path}".lower()

        dangerous_patterns = [
            "rm -rf /",
            "rm -rf /*",
            "del /f /s /q c:\\",
            "format c:",
            ":(){ :|:& };:",
            "dd if=/dev/zero of=/dev/sd",
            "sudo rm -rf",
            "taskkill /f /im explorer.exe",
            "taskkill /f /im system",
        ]

        for pattern in dangerous_patterns:
            if pattern in text:
                return False, f"Dangerous operation blocked: '{pattern}' requires explicit emergency override."

        return True, "Passed"

    def rate_limiter(self, tool_name: str, parameters: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        """Rate limiter hook preventing accidental runaway loops."""
        if not self._rate_limiter.check_and_record():
            return False, parameters, "Rate limit exceeded: tool call frequency too high. Pausing execution."
        return True, parameters, None

    def audit_log(self, hook_point: str, hook_name: str, status: str, details: str) -> str:
        """Appends cryptographically hashed audit entry."""
        now = time.time()
        content = f"{now}|{hook_point}|{hook_name}|{status}|{details}|{self._last_hash}"
        new_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        self._last_hash = new_hash

        record = HookAuditLog(
            timestamp=now,
            hook_point=hook_point,
            hook_name=hook_name,
            status=status,
            details=details,
            chain_hash=new_hash,
        )
        self._audit_logs.append(record)
        if len(self._audit_logs) > 500:
            self._audit_logs.pop(0)
        return new_hash

    def register_hook(
        self,
        *args,
        name: Optional[str] = None,
        hook_point: Optional[str] = None,
        callback: Optional[Callable] = None,
        priority: int = 100,
        description: str = "",
        **kwargs,
    ) -> bool:
        """
        Flexible hook registration supporting multiple calling patterns:
          1) register_hook(event, callback)
          2) register_hook(name, hook_point, callback, priority, description)
          3) register_hook(name=..., hook_point=..., callback=...)
        """
        # Resolve positional args
        if len(args) == 2 and callable(args[1]):
            # register_hook(event, callback)
            ev = args[0]
            cb = args[1]
            resolved_hook_point = "safety_hook" if ev == "safety_check" else ev
            resolved_name = f"hook_{ev}_{getattr(cb, '__name__', 'fn')}_{int(time.time()*1000)}"
            resolved_callback = cb
        elif len(args) >= 3:
            # register_hook(name, hook_point, callback, [priority], [desc])
            resolved_name = args[0]
            ev = args[1]
            resolved_hook_point = "safety_hook" if ev == "safety_check" else ev
            resolved_callback = args[2]
            if len(args) >= 4:
                priority = args[3]
            if len(args) >= 5:
                description = args[4]
        else:
            # Keyword arguments
            ev = hook_point or kwargs.get("event") or (args[0] if len(args) > 0 else "")
            cb = callback or kwargs.get("cb") or (args[1] if len(args) > 1 else None)
            resolved_callback = cb
            resolved_hook_point = "safety_hook" if ev == "safety_check" else ev
            resolved_name = name or f"hook_{ev}_{getattr(cb, '__name__', 'fn')}_{int(time.time()*1000)}"

        if resolved_hook_point not in self.VALID_HOOK_POINTS:
            logger.error(f"Invalid hook point '{resolved_hook_point}'. Valid: {self.VALID_HOOK_POINTS}")
            return False

        self.unregister_hook(resolved_name)

        record = HookRecord(
            name=resolved_name,
            hook_point=resolved_hook_point,
            callback=resolved_callback,
            priority=priority,
            enabled=True,
            description=description,
        )
        self._hooks[resolved_hook_point].append(record)
        self._hooks[resolved_hook_point].sort(key=lambda h: h.priority)
        logger.info(f"Registered hook '{resolved_name}' at '{resolved_hook_point}' priority {priority}")
        return True

    def unregister_hook(self, name: str) -> bool:
        """Removes a registered hook by name."""
        removed = False
        for hp, records in self._hooks.items():
            initial_len = len(records)
            self._hooks[hp] = [h for h in records if h.name != name]
            if len(self._hooks[hp]) < initial_len:
                removed = True
        return removed

    def enable_hook(self, name: str, enabled: bool = True) -> bool:
        """Toggles an active hook."""
        for records in self._hooks.values():
            for h in records:
                if h.name == name:
                    h.enabled = enabled
                    return True
        return False

    def list_hooks(self) -> List[Dict[str, Any]]:
        """Returns catalog of all registered lifecycle hooks."""
        out = []
        for hp, records in self._hooks.items():
            for h in records:
                out.append({
                    "name": h.name,
                    "hook_point": h.hook_point,
                    "priority": h.priority,
                    "enabled": h.enabled,
                    "description": h.description,
                })
        return out

    def run_before_tool_call(
        self, tool_name: str, parameters: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        curr_params = dict(parameters)
        safe, reason = self.run_safety_check(tool_name, curr_params)
        if not safe:
            self.audit_log("before_tool_call", "safety_check", "BLOCKED", reason)
            return False, curr_params, reason

        for hook in self._hooks["before_tool_call"]:
            if not hook.enabled:
                continue
            try:
                res = hook.callback(tool_name, curr_params)
                if isinstance(res, tuple):
                    if len(res) == 3:
                        allow, mod_params, reason = res
                        if not allow:
                            self.audit_log("before_tool_call", hook.name, "BLOCKED", reason or "Denied by hook")
                            return False, curr_params, reason
                        if isinstance(mod_params, dict):
                            curr_params = mod_params
                    elif len(res) == 2:
                        allow, reason = res
                        if not allow:
                            self.audit_log("before_tool_call", hook.name, "BLOCKED", reason or "Denied by hook")
                            return False, curr_params, reason
                elif res is False:
                    self.audit_log("before_tool_call", hook.name, "BLOCKED", "Explicit false return")
                    return False, curr_params, f"Blocked by hook '{hook.name}'"
                self.audit_log("before_tool_call", hook.name, "ALLOWED", f"Tool {tool_name} approved")
            except Exception as e:
                logger.error(f"Error in hook '{hook.name}': {e}")
                self.audit_log("before_tool_call", hook.name, "ERROR", str(e))

        return True, curr_params, None

    def run_after_tool_call(
        self, tool_name: str, parameters: Dict[str, Any], result: Dict[str, Any]
    ) -> Dict[str, Any]:
        curr_res = dict(result) if isinstance(result, dict) else {"output": result}
        for hook in self._hooks["after_tool_call"]:
            if not hook.enabled:
                continue
            try:
                mod_res = hook.callback(tool_name, parameters, curr_res)
                if isinstance(mod_res, dict):
                    curr_res = mod_res
                self.audit_log("after_tool_call", hook.name, "MODIFIED", f"Tool {tool_name} result updated")
            except Exception as e:
                logger.error(f"Error in after_tool hook '{hook.name}': {e}")
        return curr_res

    def run_before_model_call(self, prompt: str, history: str) -> Tuple[bool, str]:
        curr_prompt = prompt
        for hook in self._hooks["before_model_call"]:
            if not hook.enabled:
                continue
            try:
                res = hook.callback(curr_prompt, history)
                if isinstance(res, tuple) and len(res) == 2:
                    allow, mod_p = res
                    if not allow:
                        return False, curr_prompt
                    curr_prompt = mod_p
                elif isinstance(res, str):
                    curr_prompt = res
            except Exception as e:
                logger.error(f"Error in before_model hook '{hook.name}': {e}")
        return True, curr_prompt

    def run_after_model_call(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        curr_decision = dict(decision) if isinstance(decision, dict) else {}
        for hook in self._hooks["after_model_call"]:
            if not hook.enabled:
                continue
            try:
                res = hook.callback(curr_decision)
                if isinstance(res, dict):
                    curr_decision = res
            except Exception as e:
                logger.error(f"Error in after_model hook '{hook.name}': {e}")
        return curr_decision

    def run_on_error(self, error: Exception, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        for hook in self._hooks["on_error"]:
            if not hook.enabled:
                continue
            try:
                recovery = hook.callback(error, context)
                if isinstance(recovery, dict):
                    return recovery
            except Exception as e:
                logger.error(f"Error in on_error hook '{hook.name}': {e}")
        return None

    def run_safety_check(self, action: str, payload: Dict[str, Any]) -> Tuple[bool, str]:
        for hp in ["safety_hook", "safety_check"]:
            for hook in self._hooks.get(hp, []):
                if not hook.enabled:
                    continue
                try:
                    safe, reason = hook.callback(action, payload)
                    if not safe:
                        return False, reason
                except Exception as e:
                    logger.error(f"Error in safety hook '{hook.name}': {e}")
        return True, "Safe"

    def get_audit_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [
            {
                "timestamp": a.timestamp,
                "hook_point": a.hook_point,
                "hook_name": a.hook_name,
                "status": a.status,
                "details": a.details,
                "chain_hash": a.chain_hash,
            }
            for a in reversed(self._audit_logs[-limit:])
        ]


# Global Singleton
hook_engine = HookEngine()


# Top-level standalone functions matching user requests
def register_hook(
    *args,
    name: Optional[str] = None,
    hook_point: Optional[str] = None,
    callback: Optional[Callable] = None,
    priority: int = 100,
    description: str = "",
    **kwargs,
) -> bool:
    return hook_engine.register_hook(*args, name=name, hook_point=hook_point, callback=callback, priority=priority, description=description, **kwargs)


def confirm_dangerous_actions(action: str, payload: Dict[str, Any]) -> Tuple[bool, str]:
    return hook_engine.confirm_dangerous_actions(action, payload)


def audit_log(hook_point: str, hook_name: str, status: str, details: str) -> str:
    return hook_engine.audit_log(hook_point, hook_name, status, details)


def rate_limiter(tool_name: str, parameters: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], Optional[str]]:
    return hook_engine.rate_limiter(tool_name, parameters)
