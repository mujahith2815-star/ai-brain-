"""
Safety Guard for Proactive Autonomous Execution.
Enforces tool whitelists, blocks destructive commands, and manages audit logging.
"""

import re
import json
import logging
from typing import Dict, Any, Tuple, Optional, List

logger = logging.getLogger("orvix.proactive.safety")


class SafetyGuard:
    """
    Validates autonomous action safety against strict whitelists and destructive command heuristics.
    """

    ALLOWED_TOOLS_WHITELIST: List[str] = [
        "file_reader",
        "search_documents",
        "recall_fact",
        "add_to_list",
        "live_search",
        "list_processes",
    ]

    BLOCKED_ACTIONS: List[str] = [
        "execute_command",
        "terminate_process",
        "file_writer",
        "delete_file",
        "delete_files",
    ]

    # Regex matching destructive system and shell commands
    DESTRUCTIVE_PATTERN = re.compile(
        r"\b(rm|del|erase|rmdir|rd|drop|truncate|format|kill|shutdown|reboot|fdisk|diskpart)\b|(\b(-rf|-f|/s|/q)\b)",
        re.IGNORECASE,
    )

    def __init__(self, custom_whitelist: Optional[List[str]] = None):
        if custom_whitelist is not None:
            self.whitelist = list(custom_whitelist)
        else:
            self.whitelist = list(self.ALLOWED_TOOLS_WHITELIST)

    def is_destructive(self, tool_name: str, args: Optional[Dict[str, Any]] = None) -> bool:
        """
        Determines if a tool and its arguments carry destructive or irreversible consequences.
        """
        args = args or {}
        low_tool = (tool_name or "").lower().strip()

        # Direct destructive tools
        if low_tool in ("terminate_process", "delete_file", "delete_files"):
            return True

        # Shell/OS command execution
        if low_tool in ("execute_command", "system_execute_script", "run_command"):
            cmd = str(args.get("cmd") or args.get("command") or "")
            if self.DESTRUCTIVE_PATTERN.search(cmd):
                return True
            # Additional check for rm -rf specifically
            if "rm -rf" in cmd.lower() or "rmdir /s" in cmd.lower() or "del /f" in cmd.lower():
                return True

        # File overwriting
        if low_tool in ("file_writer", "file_write", "write_file"):
            if args.get("overwrite") is True:
                return True

        return False

    def validate_action(self, tool_name: str, args: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """
        Validates an action against safety policy.
        Returns: (allowed: bool, reason: str)
        """
        args = args or {}
        tool_name = (tool_name or "").strip()

        # 1. Destructive check must always take precedence
        if self.is_destructive(tool_name, args):
            return (False, "blocked: destructive command")

        # 2. Check allowed whitelist
        if tool_name in self.whitelist:
            return (True, "whitelisted tool")

        # 3. Check explicitly blocked tools requiring approval
        if tool_name in self.BLOCKED_ACTIONS:
            return (False, f"blocked: {tool_name} requires explicit user approval")

        # 4. Default deny
        return (False, f"action '{tool_name}' not in allowed whitelist")

    def audit_log(self, action: str, decision: str, reason: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Logs audit decisions to knowledge store and application logger."""
        logger.info(f"[SafetyAudit] Action={action} Decision={decision} Reason={reason}")
        try:
            from knowledge.sqlite_store import KnowledgeStore
            ks = KnowledgeStore()
            ks.log_task_execution(
                task_name=f"audit:{action}",
                action=json.dumps(details or {}),
                result=f"[{decision}] {reason}",
                approved=(decision.upper() == "ALLOWED"),
            )
        except Exception as e:
            logger.debug(f"Audit log persistence notice: {e}")
