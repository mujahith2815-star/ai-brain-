"""
Permission Management & Safety RBAC for P.H.A.S.S Sphere Tools.
Enforces strict execution authorization across 6 security tiers.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger("phass.tools.permissions")


class PermissionLevel(str, Enum):
    READ = "READ"          # Non-destructive data extraction (safe)
    ANALYZE = "ANALYZE"    # In-memory computation & telemetry aggregation (safe)
    CREATE = "CREATE"      # Writing new temporary files or memory entries (low risk)
    MODIFY = "MODIFY"      # Modifying existing system configuration or entities (medium risk)
    EXECUTE = "EXECUTE"    # Executing external scripts or digital binaries (high risk)
    SYSTEM = "SYSTEM"      # Low-level OS, reboot, emergency reset (critical risk)


@dataclass
class PermissionAuditLog:
    tool_name: str
    permission_level: PermissionLevel
    parameters: Dict[str, Any]
    granted: bool
    requires_user_approval: bool
    user_approved: bool
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "permission_level": self.permission_level.value,
            "parameters": self.parameters,
            "granted": self.granted,
            "requires_user_approval": self.requires_user_approval,
            "user_approved": self.user_approved,
            "timestamp": self.timestamp,
            "reason": self.reason,
        }


class PermissionManager:
    def __init__(self, require_confirmation_for: Optional[List[PermissionLevel]] = None):
        self.require_confirmation_for = require_confirmation_for or [
            PermissionLevel.EXECUTE,
            PermissionLevel.SYSTEM,
        ]
        self.audit_log: List[PermissionAuditLog] = []

    def verify_permission(
        self,
        tool_name: str,
        level: PermissionLevel,
        parameters: Dict[str, Any],
        user_confirmed: bool = False,
    ) -> tuple[bool, bool, str]:
        """
        Returns (is_granted, requires_confirmation, reason)
        """
        requires_confirm = level in self.require_confirmation_for

        if requires_confirm and not user_confirmed:
            reason = f"Action '{tool_name}' requires explicit user confirmation (Permission Tier: {level.value})."
            self._log_audit(tool_name, level, parameters, False, True, False, reason)
            return False, True, reason

        reason = f"Permission granted for {level.value} operation on '{tool_name}'."
        self._log_audit(tool_name, level, parameters, True, requires_confirm, user_confirmed, reason)
        return True, False, reason

    def _log_audit(
        self,
        tool_name: str,
        level: PermissionLevel,
        params: Dict[str, Any],
        granted: bool,
        requires_confirm: bool,
        user_approved: bool,
        reason: str,
    ) -> None:
        entry = PermissionAuditLog(
            tool_name=tool_name,
            permission_level=level,
            parameters=params,
            granted=granted,
            requires_user_approval=requires_confirm,
            user_approved=user_approved,
            reason=reason,
        )
        self.audit_log.append(entry)
        if len(self.audit_log) > 500:
            self.audit_log.pop(0)

    def get_recent_audits(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self.audit_log[-limit:]]


permission_manager = PermissionManager()
