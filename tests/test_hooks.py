import pytest
from core.hook_engine import (
    hook_engine,
    register_hook,
    confirm_dangerous_actions,
    audit_log,
    rate_limiter,
)


def test_safety_check_dangerous_command_veto():
    is_safe, reason = confirm_dangerous_actions("shell", {"command": "rm -rf /"})
    assert is_safe is False
    assert "Dangerous operation blocked" in reason

    safe_check, safe_reason = confirm_dangerous_actions("shell", {"command": "echo Hello"})
    assert safe_check is True
    assert safe_reason == "Passed"


def test_register_and_run_before_tool_hook():
    called = []

    def sample_before_hook(tool_name: str, params: dict):
        called.append(tool_name)
        params["intercepted"] = True
        return True, params, None

    register_hook("test_before_hook", "before_tool_call", sample_before_hook)

    allow, mod_params, reason = hook_engine.run_before_tool_call("status_check", {"param1": "val"})
    assert allow is True
    assert mod_params.get("intercepted") is True
    assert "status_check" in called

    hook_engine.unregister_hook("test_before_hook")


def test_after_tool_call_hook():
    def sample_after_hook(tool_name: str, params: dict, result: dict):
        result["enriched_by_hook"] = True
        return result

    register_hook("test_after_hook", "after_tool_call", sample_after_hook)
    res = hook_engine.run_after_tool_call("math_calc", {}, {"value": 42})
    assert res.get("enriched_by_hook") is True

    hook_engine.unregister_hook("test_after_hook")


def test_cryptographic_audit_log():
    initial_count = len(hook_engine.get_audit_logs())
    h = audit_log("tool_execution", "encrypt_data", "ALLOWED", "details payload")
    assert len(h) == 64  # SHA256 hex string
    logs = hook_engine.get_audit_logs()
    assert len(logs) == initial_count + 1
    assert logs[0]["chain_hash"] == h


def test_rate_limiter_functionality():
    # Test rate limiter checks
    ok, p, reason = rate_limiter("file_ops", {"action": "read"})
    assert ok is True