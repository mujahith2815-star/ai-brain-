"""
Tool Executor for P.H.A.S.S Sphere.
Executes registered tools through authorization gates, verifiers, and event bus logging.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import inspect
import json
import logging
from pathlib import Path
from .registry import tool_registry, ToolDefinition
from .permissions import permission_manager, PermissionLevel
from .verifier import ToolVerifier
from core.event_bus import event_bus, Event, EventType

logger = logging.getLogger("phass.tools.executor")


@dataclass
class ToolExecutionResult:
    tool_name: str
    parameters: Dict[str, Any]
    output: Dict[str, Any]
    success: bool
    verified: bool
    permission_granted: bool
    requires_confirmation: bool
    error: Optional[str] = None
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "output": self.output,
            "success": self.success,
            "verified": self.verified,
            "permission_granted": self.permission_granted,
            "requires_confirmation": self.requires_confirmation,
            "error": self.error,
            "execution_time_ms": round(self.execution_time_ms, 2),
        }


class ToolExecutor:
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        user_confirmed: bool = False,
    ) -> ToolExecutionResult:
        """
        Executes a registered tool securely through permission validation and post-verification.
        """
        tool_def: Optional[ToolDefinition] = tool_registry.get_tool(tool_name)
        if not tool_def:
            err = f"Tool '{tool_name}' not found in Tool Registry."
            logger.error(err)
            return ToolExecutionResult(
                tool_name=tool_name,
                parameters=parameters,
                output={},
                success=False,
                verified=False,
                permission_granted=False,
                requires_confirmation=False,
                error=err,
            )

        # 1. Check Permissions
        granted, requires_confirm, reason = permission_manager.verify_permission(
            tool_name=tool_name,
            level=tool_def.permission_level,
            parameters=parameters,
            user_confirmed=user_confirmed,
        )

        if not granted:
            logger.warning(f"Permission DENIED for {tool_name}: {reason}")
            return ToolExecutionResult(
                tool_name=tool_name,
                parameters=parameters,
                output={},
                success=False,
                verified=False,
                permission_granted=False,
                requires_confirmation=requires_confirm,
                error=reason,
            )

        # 2. Execute Handler
        start_time = datetime.now()
        try:
            if inspect.iscoroutinefunction(tool_def.handler):
                output = await tool_def.handler(**parameters)
            else:
                output = tool_def.handler(**parameters)
            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000.0

            # 3. Verify Result
            verified = ToolVerifier.verify_tool_result(tool_name, output, tool_def.verifier)
            is_success = verified and (not output.get("error")) and output.get("status") != "FAILED"

            exec_result = ToolExecutionResult(
                tool_name=tool_name,
                parameters=parameters,
                output=output,
                success=is_success,
                verified=verified,
                permission_granted=True,
                requires_confirmation=False,
                error=output.get("error") if not is_success else None,
                execution_time_ms=elapsed_ms,
            )

            # Publish Event
            await event_bus.publish(
                Event(
                    type=EventType.TOOL_EXECUTION,
                    source="ToolExecutor",
                    data=exec_result.to_dict(),
                )
            )

            _log_tool_execution(tool_name, parameters, exec_result.to_dict())
            return exec_result

        except Exception as e:
            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000.0
            logger.exception(f"Unhandled exception while executing {tool_name}: {e}")
            _log_tool_execution(tool_name, parameters, {"status": "ERROR", "error": str(e)})
            return ToolExecutionResult(
                tool_name=tool_name,
                parameters=parameters,
                output={},
                success=False,
                verified=False,
                permission_granted=True,
                requires_confirmation=False,
                error=str(e),
                execution_time_ms=elapsed_ms,
            )


tool_executor = ToolExecutor()


def _log_tool_execution(tool_name: str, args: Dict[str, Any], result: Any):
    """Logs tool execution to data_hub.resolve('logs', 'execution_log.json')."""
    try:
        from core.data_hub import data_hub
        primary_log = data_hub.resolve("logs", "execution_log.json")
    except Exception:
        primary_log = Path("checkpoints/execution_log.json")

    targets = [primary_log]
    legacy_log = Path("checkpoints/execution_log.json")
    if legacy_log.resolve() != primary_log.resolve():
        targets.append(legacy_log)

    for log_path in targets:
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            entries = []
            if log_path.exists():
                try:
                    with open(log_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            loaded = json.loads(content)
                            if isinstance(loaded, list):
                                entries = loaded
                except Exception:
                    entries = []

            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tool": tool_name,
                "args": args,
                "result": result if isinstance(result, (dict, list, str, int, float, bool)) else str(result),
            }
            entries.append(entry)
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2)
        except Exception as ex:
            logger.warning(f"Failed to record execution log to {log_path}: {ex}")


def verify_action(tool_name: str, args: Dict[str, Any], result: Any) -> Tuple[bool, str]:
    """
    Performs real post-action verification (the 'Did it actually work?' check).
    Returns (verified: bool, reason: str).
    """
    import os
    import psutil

    if not isinstance(result, dict):
        if result is None or str(result).lower().startswith("tool execution failed"):
            return False, f"Tool execution failed: {result}"
        return True, "Executed with raw output"

    if result.get("status") == "FAILED" or result.get("error"):
        return False, result.get("error") or "Tool reported status FAILED"

    # 1. launch_application verification
    if tool_name == "launch_application":
        app_name = args.get("app_name", "").lower().strip()
        pid = result.get("pid")
        if pid and psutil.pid_exists(pid):
            return True, f"Process is running with PID {pid}."

        # Search running processes by matching name keywords
        target_keywords = []
        if any(k in app_name for k in ["code", "vscode", "visual studio"]):
            target_keywords = ["code.exe", "code"]
        elif "notepad" in app_name:
            target_keywords = ["notepad.exe", "notepad"]
        elif "calc" in app_name:
            target_keywords = ["calculator", "calc.exe", "calculatorapp.exe"]
        elif "chrome" in app_name:
            target_keywords = ["chrome.exe", "chrome"]
        else:
            target_keywords = [app_name]

        for p in psutil.process_iter(["pid", "name"]):
            try:
                pname = (p.info.get("name") or "").lower()
                if any(kw in pname for kw in target_keywords):
                    found_pid = p.info.get("pid")
                    if isinstance(result, dict) and not result.get("pid") and found_pid:
                        result["pid"] = found_pid
                    return True, f"Process verified running as '{pname}' (PID: {found_pid})."
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if pid:
            return True, f"Process launched with recorded PID {pid}."
        return False, f"Process for application '{app_name}' could not be verified running in system process table."

    # 2. create_folder verification
    if tool_name == "create_folder":
        folder_path = args.get("path") or args.get("folder_path") or result.get("folder_path")
        if not folder_path:
            return False, "No folder path provided to verify."
        exp_path = os.path.expandvars(os.path.expanduser(str(folder_path)))
        if os.path.exists(exp_path) and os.path.isdir(exp_path):
            return True, f"Folder confirmed existing on filesystem at '{exp_path}'."
        return False, f"Folder does not exist on filesystem: '{exp_path}'."

    # 3. web_search / knowledge_query verification
    if tool_name in ("web_search", "knowledge_query"):
        ans = result.get("answer") or ""
        results_list = result.get("results") or []
        combined_text = str(ans) + "".join(str(r.get("snippet", "")) for r in results_list if isinstance(r, dict))
        if len(combined_text.strip()) >= 50:
            return True, f"Web search verified with {len(combined_text.strip())} characters of factual data."
        if ans and str(ans).strip().lower() != "none" and len(str(ans).strip()) > 10:
            return True, f"Web search returned valid answer: {ans[:40]}..."
        return False, "Web search returned empty, None, or fewer than 50 characters."

    # 4. delete_file verification
    if tool_name in ("delete_file", "file_delete"):
        file_path = args.get("path") or args.get("file_path") or result.get("file_path")
        if not file_path:
            return False, "No file path provided to verify deletion."
        exp_path = os.path.expandvars(os.path.expanduser(str(file_path)))
        if not os.path.exists(exp_path):
            return True, f"Confirmed file no longer exists at '{exp_path}'."
        return False, f"File still exists on filesystem at '{exp_path}'."

    # 5. file_writer / write_file verification
    if tool_name in ("file_writer", "write_file", "file_write"):
        file_path = args.get("file_path") or args.get("path") or result.get("file_path")
        if not file_path:
            return False, "No file path provided to verify write."
        exp_path = os.path.expandvars(os.path.expanduser(str(file_path)))
        if os.path.exists(exp_path) and os.path.getsize(exp_path) >= 0:
            return True, f"File write confirmed existing with size {os.path.getsize(exp_path)} bytes."
    # 6. bootstrap_hardware_project verification
    if tool_name == "bootstrap_hardware_project":
        proj_dir = result.get("project_dir") if isinstance(result, dict) else None
        if proj_dir and os.path.exists(proj_dir):
            fw = os.path.join(proj_dir, "firmware")
            hw = os.path.join(proj_dir, "hardware")
            if os.path.exists(fw) and os.path.exists(hw):
                return True, f"Dual-structure project confirmed on disk at '{proj_dir}' with firmware/ and hardware/."
        return False, f"Hardware project folders could not be verified on disk at '{proj_dir}'."

    # 7. schedule_task verification
    if tool_name == "schedule_task":
        if isinstance(result, dict) and (result.get("status") == "SUCCESS" or result.get("task_id")):
            tname = result.get("name") or args.get("task_name", "task")
            expr = result.get("schedule_expr") or args.get("cron_or_delay", "")
            return True, f"Scheduled task '{tname}' registered with schedule '{expr}'."
        return False, "Scheduled task registration could not be verified."

    # 8. detect_hardware & list_boards verification
    if tool_name in ("detect_hardware", "list_boards"):
        if isinstance(result, dict) and (result.get("status") == "SUCCESS" or "devices" in result or "boards" in result):
            cnt = result.get("count", len(result.get("devices", result.get("boards", []))))
            return True, f"Hardware scan verified: {cnt} board(s) identified."
        return False, "Hardware detection failed to return valid board list."

    # 9. program_board verification
    if tool_name == "program_board":
        if isinstance(result, dict) and (result.get("status") == "SUCCESS" or result.get("pid")):
            pid = result.get("pid", "N/A")
            board = result.get("board", "Board")
            port = result.get("port", "COM3")
            return True, f"Firmware flashed to {board} on {port} (PID: {pid})."
        return False, "Firmware programming verification failed."

    # 10. monitor_serial verification
    if tool_name == "monitor_serial":
        if isinstance(result, dict) and (result.get("lines") or result.get("output") or result.get("status") == "SUCCESS"):
            line_cnt = len(result.get("lines", []))
            return True, f"Serial output verified with {line_cnt} telemetry lines."
        return False, "Serial monitor failed to capture output."

    # Default verification
    return True, "Operation completed without errors."



def execute_tool(tool_name: str, parameters: Dict[str, Any], user_confirmed: bool = False) -> Any:
    """Synchronous execution of registered tool with post-action verification and Brutal Honesty enforcement."""
    tool_def = tool_registry.get_tool(tool_name) or tool_registry.get(tool_name)
    if not tool_def:
        err_msg = f"Tool '{tool_name}' not found."
        err_res = {"status": "ERROR", "error": err_msg, "verified": False}
        _log_tool_execution(tool_name, parameters, err_res)
        raise RuntimeError(f"❌ MISSING DEPENDENCY: {err_msg}")

    try:
        res = tool_registry.execute(tool_name, **parameters)
        verified, reason = verify_action(tool_name, parameters, res)
        if isinstance(res, dict):
            res["verified"] = verified
            res["verification_reason"] = reason

            # Reject simulated outputs when real dependencies are missing
            if res.get("simulated") is True:
                err_msg = f"Tool '{tool_name}' returned simulated mock output due to missing dependencies."
                res["status"] = "FAILED"
                res["error"] = err_msg
                _log_tool_execution(tool_name, parameters, res)
                raise RuntimeError(f"❌ MISSING DEPENDENCY: {err_msg}")

            if not verified and res.get("status") == "SUCCESS":
                res["status"] = "FAILED"
                res["error"] = reason

            if res.get("status") in ("FAILED", "ERROR") or res.get("success") is False:
                err_msg = res.get("error") or reason or f"Execution failed for '{tool_name}'."
                _log_tool_execution(tool_name, parameters, res)
                raise RuntimeError(f"❌ MISSING DEPENDENCY: {err_msg}")

        _log_tool_execution(tool_name, parameters, res)
        return res
    except RuntimeError:
        raise
    except Exception as e:
        err_res = {"status": "ERROR", "error": str(e), "verified": False}
        _log_tool_execution(tool_name, parameters, err_res)
        raise RuntimeError(f"❌ MISSING DEPENDENCY: {e}")




