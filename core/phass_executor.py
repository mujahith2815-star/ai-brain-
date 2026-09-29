"""
Strict Execution Engine for P.H.A.S.S Sphere (Planner vs. Executor Separation).
Receives structured action plans from the Cognitive Planner, executes real system calls,
verifies outcomes, logs telemetry, and returns truthful status reports.
"""

from __future__ import annotations
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tools.executor import execute_tool, verify_action

logger = logging.getLogger("phass.core.phass_executor")


class PhassExecutor:
    """
    The strict execution engine.
    Ensures the Planner NEVER talks directly to the user about actions
    without real, verifiable execution confirmation.
    """

    def __init__(self, log_path: Optional[str] = None):
        if log_path is not None:
            self.log_path = Path(log_path)
        else:
            try:
                from core.data_hub import data_hub
                self.log_path = data_hub.resolve("logs", "execution_log.json")
            except Exception:
                self.log_path = Path("checkpoints/execution_log.json")
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
            }

        overall_success = True
        action_results: List[Dict[str, Any]] = []

        for idx, action_item in enumerate(actions, start=1):
            tool_name = action_item.get("tool") or action_item.get("action")
            args = action_item.get("args") or action_item.get("parameters") or {}

            if not tool_name:
                continue

            # Execute with up to 1 retry on verification failure
            res, verified, reason = self._execute_with_retry(tool_name, args, max_retries=1)

            is_success = verified and (isinstance(res, dict) and res.get("status") != "FAILED" and not res.get("error"))
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
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            action_results.append(action_record)

            # Persist to execution log
            self._log_action(action_record)

        # Formulate truthful summary response
        status_str = "SUCCESS" if overall_success else "FAILED"
        summary = self._synthesize_summary(actions, action_results, overall_success)

        return {
            "status": status_str,
            "actions_executed": len(action_results),
            "results": action_results,
            "summary": summary,
        }

    def _execute_with_retry(
        self,
        tool_name: str,
        args: Dict[str, Any],
        max_retries: int = 1,
    ) -> Tuple[Any, bool, str]:
        """Executes a tool and verifies it. Retries once if verification fails."""
        attempts = 0
        last_res: Any = None
        last_reason = "Not executed"

        while attempts <= max_retries:
            attempts += 1
            last_res = execute_tool(tool_name, args)
            verified, last_reason = verify_action(tool_name, args, last_res)

            if verified:
                return last_res, True, last_reason

            if attempts <= max_retries:
                logger.warning(
                    f"Verification failed on attempt {attempts} for '{tool_name}' ({last_reason}). Retrying once..."
                )
                time.sleep(0.35)

        return last_res, False, f"Verification failed after retry: {last_reason}"

    def _log_action(self, record: Dict[str, Any]):
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

            # Format log entry
            entry = {
                "timestamp": record["timestamp"],
                "tool": record["tool"],
                "args": record["args"],
                "status": record["status"],
                "verified": record["verified"],
                "verification_reason": record["verification_reason"],
                "result": record["result"],
            }
            entries.append(entry)

            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2)

            legacy_log = Path("checkpoints/execution_log.json")
            if legacy_log.resolve() != self.log_path.resolve():
                try:
                    legacy_log.parent.mkdir(parents=True, exist_ok=True)
                    with open(legacy_log, "w", encoding="utf-8") as f:
                        json.dump(entries, f, indent=2)
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"PhassExecutor failed to record log: {e}")

    def _synthesize_summary(
        self,
        actions: List[Dict[str, Any]],
        results: List[Dict[str, Any]],
        overall_success: bool,
    ) -> str:
        """Synthesizes a clean, verified, factual statement for the Planner to relay to the user."""
        if not overall_success:
            failures = [r for r in results if r["status"] == "FAILED"]
            fail_descs = [f"{f['tool']}: {f['verification_reason']}" for f in failures]
            return f"Action execution failed: {'; '.join(fail_descs)}"

        tool_names = [r["tool"] for r in results]

        # Case 1: Project start (folder + code)
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
            fp = res_dict.get("file_path") if isinstance(res_dict, dict) else (results[0]["args"].get("file_path") or results[0]["args"].get("path"))
            return f"File successfully deleted: {fp}"

        # Case 7: Advanced calculator
        if len(results) == 1 and results[0]["tool"] == "advanced_calculator":
            res_dict = results[0]["result"]
            val = res_dict.get("result") if isinstance(res_dict, dict) else str(res_dict)
            return f"The calculated total is {val}."

        # Case 8: Hardware project bootstrap
        if "bootstrap_hardware_project" in tool_names:
            proj_res = [r for r in results if r["tool"] == "bootstrap_hardware_project"][0]
            p_name = proj_res["args"].get("project_name", "Hardware Project")
            p_dir = proj_res["result"].get("project_dir", "") if isinstance(proj_res["result"], dict) else ""
            editor_note = " and editor opened." if "launch_application" in tool_names else "."
            return f"Project '{p_name}' created successfully with firmware/ and hardware/ directories at: {p_dir}{editor_note}"

        # Case 9: Hardware pinout visualize
        if len(results) == 1 and results[0]["tool"] == "pinout_visualize":
            res_dict = results[0]["result"]
            diag = res_dict.get("diagram") if isinstance(res_dict, dict) else str(res_dict)
            return str(diag)

        # Case 10: Hardware datasheet fetch
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
            return f"Datasheet Profile: {name} ({data.get('type', '')})\nPackage: {pkg}\nDescription: {desc}\n\nPinout: {pinout}\n\nKey Specifications:\n{specs}\n\nEquivalents: {eqs}{diag_str}"

        # Case 11: Hardware circuit troubleshoot
        if len(results) == 1 and results[0]["tool"] == "circuit_troubleshoot":
            res_dict = results[0]["result"]
            steps = res_dict.get("steps", []) if isinstance(res_dict, dict) else []
            summary_h = res_dict.get("summary", "Circuit Diagnostic Workflow") if isinstance(res_dict, dict) else "Circuit Diagnostic"
            return f"{summary_h}:\n\n" + "\n\n".join(steps)

        # Case 12: Hardware component test procedure
        if len(results) == 1 and results[0]["tool"] == "component_test_procedure":
            res_dict = results[0]["result"]
            proc = res_dict.get("procedure") if isinstance(res_dict, dict) else str(res_dict)
            return str(proc)

        # Case 13: Hardware voltage divider / RC calculation
        if len(results) == 1 and results[0]["tool"] in ("calculate_voltage_divider", "calculate_rc_constant"):
            res_dict = results[0]["result"]
            return res_dict.get("summary", "Calculation complete.") if isinstance(res_dict, dict) else str(res_dict)

        # Case 14: Hardware measurement interpretation
        if len(results) == 1 and results[0]["tool"] == "interpret_circuit_measurements":
            res_dict = results[0]["result"]
            return res_dict.get("analysis", "Measurements analyzed.") if isinstance(res_dict, dict) else str(res_dict)

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
        summaries = []
        for r in results:
            t = r["tool"]
            if t == "launch_application":
                pid = r["result"].get("pid") if isinstance(r["result"], dict) else None
                app = r["args"].get("app_name", "app")
                summaries.append(f"Launched {app} (PID: {pid})")
            elif t == "create_folder":
                summaries.append(f"Created folder {r['args'].get('path') or r['args'].get('folder_path')}")
            else:
                summaries.append(f"Executed {t}")
        return ", ".join(summaries) + "."

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




phass_executor = PhassExecutor()


def execute_action_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Top-level helper to execute a Planner action plan."""
    return phass_executor.execute_plan(plan)
