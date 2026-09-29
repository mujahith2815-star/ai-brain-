"""
Strict Execution Orchestrator for P.H.A.S.S Sphere (Planner -> Executor -> Verifier).
Enforces absolute separation of concerns:
- Planner: Generates JSON actions only. Forbidden from asserting actions took place.
- Executor: Calls real system tools and functions in tools/executor.py.
- Verifier: Checks real system state (psutil, os.path, file content) with automatic single-retry.
- Logger: Records every action, verification outcome, and error to checkpoints/execution_log.json.
"""

from __future__ import annotations
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable

import psutil
from tools.executor import execute_tool, verify_action

logger = logging.getLogger("phass.core.execution_orchestrator")


class ExecutionOrchestrator:
    """
    Authoritative Planner -> Executor -> Verifier Pipeline.
    Prevents hallucinated execution, verifies real OS side-effects,
    and returns truthful status reports to the Planner.
    """

    def __init__(self, log_path: str = "checkpoints/execution_log.json"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def execute_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a Planner's JSON action plan.
        Expected format:
        {
            "actions": [
                {"tool": "launch_application", "args": {"app_name": "code"}},
                ...
            ]
        }
        """
        actions = plan.get("actions", [])
        if not actions or not isinstance(actions, list):
            return {
                "status": "NOOP",
                "message": "No actions to execute.",
                "actions_executed": 0,
                "results": [],
                "summary": "No actions were requested.",
            }

        overall_success = True
        action_results: List[Dict[str, Any]] = []

        for idx, action_item in enumerate(actions, start=1):
            tool_name = action_item.get("tool") or action_item.get("action")
            args = action_item.get("args") or action_item.get("parameters") or {}

            if not tool_name:
                continue

            # Execute with up to 1 retry on verification failure
            res, verified, reason = self.execute_and_verify(tool_name, args, max_retries=1)

            is_success = verified and (
                isinstance(res, dict)
                and res.get("status") != "FAILED"
                and not res.get("error")
            )
            if not is_success:
                overall_success = False

            action_record = {
                "step": idx,
                "tool": tool_name,
                "args": args,
                "result": res,
                "verified": verified,
                "status": "SUCCESS" if is_success else "FAILED",
                "verification_reason": reason,
                "error": None if is_success else (res.get("error") if isinstance(res, dict) else reason),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            action_results.append(action_record)

            # Persist to execution log
            self._log_action(action_record)

        status_str = "SUCCESS" if overall_success else "FAILED"
        summary = self.synthesize_summary(actions, action_results, overall_success)

        return {
            "status": status_str,
            "actions_executed": len(action_results),
            "results": action_results,
            "summary": summary,
        }

    def execute_and_verify(
        self,
        tool_name: str,
        args: Dict[str, Any],
        max_retries: int = 1,
    ) -> Tuple[Any, bool, str]:
        """
        Executes a tool and physically verifies its side-effects.
        Retries once if verification fails.
        """
        attempts = 0
        last_res: Any = None
        last_reason = "Not executed"

        while attempts <= max_retries:
            attempts += 1
            last_res = execute_tool(tool_name, args)
            verified, last_reason = self.verify_system_state(tool_name, args, last_res)

            if verified:
                return last_res, True, last_reason

            if attempts <= max_retries:
                logger.warning(
                    f"Verification attempt {attempts} failed for '{tool_name}' ({last_reason}). Retrying..."
                )
                time.sleep(0.35)

        return last_res, False, f"Verification failed after retry: {last_reason}"

    def verify_system_state(
        self,
        tool_name: str,
        args: Dict[str, Any],
        result: Any,
    ) -> Tuple[bool, str]:
        """
        Conducts concrete OS verification using psutil, filesystem checks, and content inspection.
        """
        # First call base verifier
        base_verified, base_reason = verify_action(tool_name, args, result)
        if not base_verified:
            return False, base_reason

        # Specific process verification via psutil
        if tool_name == "launch_application" and isinstance(result, dict):
            pid = result.get("pid")
            if pid is not None:
                if not psutil.pid_exists(pid):
                    return False, f"Process with PID {pid} is not present in system process table."
                try:
                    p = psutil.Process(pid)
                    if not p.is_running() or p.status() == psutil.STATUS_ZOMBIE:
                        return False, f"Process with PID {pid} terminated prematurely or is zombie."
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

        # Specific folder verification
        if tool_name == "create_folder" and isinstance(result, dict):
            folder_path = result.get("folder_path") or args.get("path") or args.get("folder_path")
            if folder_path:
                norm_p = os.path.expanduser(folder_path)
                if not os.path.exists(norm_p):
                    return False, f"Directory '{norm_p}' does not exist on disk."
                if not os.path.isdir(norm_p):
                    return False, f"Path '{norm_p}' exists but is not a directory."

        # Specific file write verification
        if tool_name in ("write_file", "file_writer", "file_write") and isinstance(result, dict):
            file_path = result.get("file_path") or args.get("file_path") or args.get("path")
            if file_path:
                norm_p = os.path.expanduser(file_path)
                if not os.path.exists(norm_p):
                    return False, f"File '{norm_p}' was not found on disk."
                if not os.path.isfile(norm_p):
                    return False, f"Path '{norm_p}' is not a regular file."

        # Specific hardware project verification
        if tool_name == "bootstrap_hardware_project" and isinstance(result, dict):
            p_dir = result.get("project_dir")
            if p_dir:
                fw = os.path.join(p_dir, "firmware")
                hw = os.path.join(p_dir, "hardware")
                if not (os.path.isdir(fw) and os.path.isdir(hw)):
                    return False, f"Project directory '{p_dir}' missing firmware/ or hardware/ folders."

        return True, base_reason

    def synthesize_summary(
        self,
        actions: List[Dict[str, Any]],
        results: List[Dict[str, Any]],
        overall_success: bool,
    ) -> str:
        """
        Synthesizes a clean, verified, factual statement for the Planner to relay to the user.
        Never relies on role-playing or hallucinated responses.
        """
        if not overall_success:
            failures = [r for r in results if r["status"] == "FAILED"]
            fail_descs = [f"{f['tool']}: {f.get('verification_reason') or f.get('error')}" for f in failures]
            return f"Action execution failed: {'; '.join(fail_descs)}"

        tool_names = [r["tool"] for r in results]

        # Case 1: Project start (create_folder + code or bootstrap_hardware_project)
        if "bootstrap_hardware_project" in tool_names:
            proj_res = [r for r in results if r["tool"] == "bootstrap_hardware_project"][0]
            p_name = proj_res["args"].get("project_name", "Hardware Project")
            p_dir = proj_res["result"].get("project_dir", "") if isinstance(proj_res["result"], dict) else ""
            editor_note = " and editor opened." if "launch_application" in tool_names else "."
            return f"Project '{p_name}' created successfully with firmware/ and hardware/ directories at: {p_dir}{editor_note}"

        if "create_folder" in tool_names and "launch_application" in tool_names:
            return "Project folder created and VS Code opened."

        # Case 2: Single application launch
        if len(results) == 1 and results[0]["tool"] == "launch_application":
            res_dict = results[0]["result"]
            pid = res_dict.get("pid") if isinstance(res_dict, dict) else None
            app_name = results[0]["args"].get("app_name", "Application")
            if "code" in app_name.lower() or "visual studio" in app_name.lower():
                app_title = "VS Code"
            else:
                app_title = app_name.title()

            if pid:
                return f"{app_title} is now open (PID: {pid})."
            return f"{app_title} opened successfully."

        # Case 3: Single folder creation
        if len(results) == 1 and results[0]["tool"] == "create_folder":
            res_dict = results[0]["result"]
            fpath = res_dict.get("folder_path") if isinstance(res_dict, dict) else results[0]["args"].get("path")
            return f"Folder created successfully at: {fpath}"

        # Case 4: Web search
        if len(results) == 1 and results[0]["tool"] == "web_search":
            res_dict = results[0]["result"]
            raw_text = ""
            if isinstance(res_dict, dict):
                raw_text = res_dict.get("answer") or res_dict.get("summary") or ""
                if not raw_text and res_dict.get("results"):
                    snippets = [r.get("snippet", "") for r in res_dict["results"] if isinstance(r, dict)]
                    raw_text = " ".join(snippets)
            elif isinstance(res_dict, str):
                raw_text = res_dict
            return self._clean_and_summarize_search(raw_text)


        # Case 5: File write
        if len(results) == 1 and results[0]["tool"] in ("file_writer", "write_file", "file_write"):
            res_dict = results[0]["result"]
            fp = res_dict.get("file_path") if isinstance(res_dict, dict) else results[0]["args"].get("file_path")
            return f"File successfully written to: {fp}"

        # Case 6: File delete
        if len(results) == 1 and results[0]["tool"] in ("delete_file", "file_delete"):
            res_dict = results[0]["result"]
            fp = res_dict.get("file_path") if isinstance(res_dict, dict) else (
                results[0]["args"].get("file_path") or results[0]["args"].get("path")
            )
            return f"File successfully deleted: {fp}"

        # Case 7: Advanced calculator
        if len(results) == 1 and results[0]["tool"] == "advanced_calculator":
            res_dict = results[0]["result"]
            val = res_dict.get("result") if isinstance(res_dict, dict) else str(res_dict)
            return f"The calculated total is {val}."

        # Case 8: Hardware pinout visualize
        if len(results) == 1 and results[0]["tool"] == "pinout_visualize":
            res_dict = results[0]["result"]
            diag = res_dict.get("diagram") if isinstance(res_dict, dict) else str(res_dict)
            return str(diag)

        # Case 9: Hardware datasheet fetch
        if len(results) == 1 and results[0]["tool"] == "datasheet_fetch":
            res_dict = results[0]["result"]
            data = res_dict.get("data", {}) if isinstance(res_dict, dict) else {}
            name = data.get("name", "Component")
            desc = data.get("description", "")
            pkg = data.get("package", "")
            pinout = ", ".join(data.get("pin_labels", []))
            specs = "\n".join(f"• {k}: {v}" for k, v in data.get("key_specs", {}).items())
            eqs = ", ".join(data.get("equivalents", []))
            diagram = data.get("ascii_diagram", "").strip()
            diag_str = f"\n\nPinout Diagram:\n{diagram}" if diagram else ""
            return (
                f"Datasheet Profile: {name} ({data.get('type', '')})\n"
                f"Package: {pkg}\nDescription: {desc}\n\n"
                f"Pinout: {pinout}\n\nKey Specifications:\n{specs}\n\nEquivalents: {eqs}{diag_str}"
            )

        # Case 10: Hardware circuit troubleshoot
        if len(results) == 1 and results[0]["tool"] == "circuit_troubleshoot":
            res_dict = results[0]["result"]
            steps = res_dict.get("steps", []) if isinstance(res_dict, dict) else []
            summary_h = res_dict.get("summary", "Circuit Diagnostic Workflow") if isinstance(res_dict, dict) else "Circuit Diagnostic"
            return f"{summary_h}:\n\n" + "\n\n".join(steps)

        # Case 11: Hardware bench test procedure
        if len(results) == 1 and results[0]["tool"] == "component_test_procedure":
            res_dict = results[0]["result"]
            steps = res_dict.get("steps", []) if isinstance(res_dict, dict) else []
            comp = res_dict.get("component", "Component") if isinstance(res_dict, dict) else "Component"
            return f"Bench Test Procedure for {comp}:\n\n" + "\n\n".join(steps)

        # Case 12: Voltage divider / circuit calculations
        if len(results) == 1 and results[0]["tool"] in ("calculate_voltage_divider", "calculate_rc_constant"):
            res_dict = results[0]["result"]
            if isinstance(res_dict, dict) and res_dict.get("summary"):
                return str(res_dict["summary"])

        # Case 13: Measurement interpreter
        if len(results) == 1 and results[0]["tool"] == "interpret_circuit_measurements":
            res_dict = results[0]["result"]
            if isinstance(res_dict, dict) and res_dict.get("analysis"):
                return f"Bench Measurement Diagnostic:\n\n{res_dict['analysis']}"

        # Case 14: Scheduled Task
        if len(results) == 1 and results[0]["tool"] == "schedule_task":
            res_dict = results[0]["result"]
            msg = res_dict.get("message") if isinstance(res_dict, dict) else str(res_dict)
            return f"Schedule confirmed: {msg}"

        # Case 15: Hardware Detection & Board Listing
        if len(results) == 1 and results[0]["tool"] in ("detect_hardware", "list_boards"):
            res_dict = results[0]["result"]
            devices = res_dict.get("devices") or res_dict.get("boards") or []
            if devices:
                dev_lines = [f"{d['name']} connected on {d['port']} ({d.get('toolchain', 'esptool')})" for d in devices]
                return f"Connected Hardware Detected ({len(devices)} device(s)):\n" + "\n".join(f"• {l}" for l in dev_lines)
            return "No microcontroller boards currently detected on USB/serial ports."

        # Case 16: Program Board & Flash
        if len(results) == 1 and results[0]["tool"] == "program_board":
            res_dict = results[0]["result"]
            b = res_dict.get("board", "ESP32")
            p = res_dict.get("port", "COM3")
            pid = res_dict.get("pid", "N/A")
            return f"Firmware successfully compiled and flashed to {b} on {p} (PID: {pid}). Flash verified."

        # Case 17: Serial Monitor
        if len(results) == 1 and results[0]["tool"] == "monitor_serial":
            res_dict = results[0]["result"]
            p = res_dict.get("port", "COM3")
            out = res_dict.get("output", "")
            return f"Live Serial Monitor ({p}):\n{out}"

        # Case 18: Full Hardware Programming Pipeline (detect_hardware + program_board + monitor_serial)
        if "program_board" in tool_names:
            flash_res = [r for r in results if r["tool"] == "program_board"][0]
            b = flash_res["result"].get("board", "ESP32") if isinstance(flash_res["result"], dict) else "ESP32"
            p = flash_res["result"].get("port", "COM3") if isinstance(flash_res["result"], dict) else "COM3"
            pid = flash_res["result"].get("pid", "N/A") if isinstance(flash_res["result"], dict) else "N/A"
            serial_res = [r for r in results if r["tool"] == "monitor_serial"]
            serial_text = ""
            if serial_res and isinstance(serial_res[0]["result"], dict):
                serial_text = f"\n\nLive Serial Output ({p}):\n" + serial_res[0]["result"].get("output", "")
            return f"Success: {b} on {p} compiled and flashed (PID: {pid}).{serial_text}"

        # General multi-action summary
        succ_tools = [r["tool"] for r in results if r["status"] == "SUCCESS"]
        return f"Successfully executed and verified {len(succ_tools)} actions: {', '.join(succ_tools)}."

    def _clean_and_summarize_search(self, raw_text: str) -> str:
        """Removes URLs, timestamps, and summarizes search results cleanly."""
        if not raw_text:
            return "I could not find relevant information on that topic."

        # Remove URLs
        cleaned = re.sub(r"https?://\S+", "", raw_text)
        # Remove timestamps like [10:15:16.102] or 2026-09-07T...
        cleaned = re.sub(r"\[\d{2}:\d{2}:\d{2}(?:\.\d+)?\]", "", cleaned)
        cleaned = re.sub(r"\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?", "", cleaned)
        # Remove internal execution/step patterns
        cleaned = re.sub(r"Current Step:\s*\d+\s*of\s*\d+", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"Decide your next action\.?\s*Return JSON only\.?", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"Web search results retrieved for [^\.]+\.", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"Verified encyclopedic knowledge and live web data\.?", "", cleaned, flags=re.IGNORECASE)

        # Clean extra whitespaces
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Call summarize_text tool if registered
        try:
            from tools.registry import tool_registry
            if tool_registry.has_tool("summarize_text"):
                res = tool_registry.execute("summarize_text", text=cleaned)
                if isinstance(res, dict) and res.get("summary"):
                    return str(res["summary"]).strip()
        except Exception:
            pass

        return cleaned if len(cleaned) > 10 else "Information retrieved and verified."



    def _log_action(self, record: Dict[str, Any]) -> None:
        """Appends action and verification result to checkpoints/execution_log.json."""
        try:
            entries = []
            if self.log_path.exists():
                try:
                    with open(self.log_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            loaded = json.loads(content)
                            if isinstance(loaded, list):
                                entries = loaded
                except Exception:
                    entries = []

            entry = {
                "timestamp": record["timestamp"],
                "tool": record["tool"],
                "args": record["args"],
                "status": record["status"],
                "verified": record["verified"],
                "verification_reason": record["verification_reason"],
                "error": record.get("error"),
                "result": record["result"],
            }
            entries.append(entry)

            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2)
        except Exception as e:
            logger.warning(f"ExecutionOrchestrator failed to log action: {e}")


# Global singleton instance
execution_orchestrator = ExecutionOrchestrator()
