"""
Enterprise Security Audit Ledger, Threat Detection & Confirmation Gate.
Provides SHA-256 hash-chained tamper-evident logging, heuristic threat analysis,
and one-time confirmation token issuance for high-risk system operations.
"""

from __future__ import annotations
import os
import time
import json
import uuid
import hashlib
import secrets
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("phass.core.security")


@dataclass
class AuditEntry:
    index: int
    timestamp: float
    action: str
    user: str
    severity: str  # "INFO", "WARNING", "HIGH", "CRITICAL"
    status: str    # "ALLOWED", "BLOCKED", "CONFIRMED", "ERROR"
    details: Dict[str, Any]
    prev_hash: str
    entry_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "action": self.action,
            "user": self.user,
            "severity": self.severity,
            "status": self.status,
            "details": self.details,
            "prev_hash": self.prev_hash,
            "entry_hash": self.entry_hash,
        }


class SecurityAudit:
    """
    Cryptographically verified security audit ledger with threat analysis
    and confirmation gate validation.
    """

    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    def __init__(self, storage_dir: Optional[str] = None):
        if storage_dir:
            self.ledger_path = Path(storage_dir) / "security_audit_ledger.json"
        else:
            self.ledger_path = Path("memory_vault") / "security_audit_ledger.json"
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)

        self.entries: List[AuditEntry] = []
        self._tokens: Dict[str, Dict[str, Any]] = {}
        self._load_ledger()

    def _compute_hash(self, index: int, timestamp: float, action: str, user: str, status: str, details: Dict[str, Any], prev_hash: str) -> str:
        payload = f"{index}:{timestamp}:{action}:{user}:{status}:{json.dumps(details, sort_keys=True)}:{prev_hash}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _load_ledger(self):
        if not self.ledger_path.exists():
            return
        try:
            with open(self.ledger_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("entries", []):
                    self.entries.append(AuditEntry(**item))
            logger.info(f"Loaded {len(self.entries)} audit entries into security ledger.")
        except Exception as e:
            logger.warning(f"Could not load security audit ledger: {e}")

    def _save_ledger(self):
        try:
            with open(self.ledger_path, "w", encoding="utf-8") as f:
                json.dump({"entries": [e.to_dict() for e in self.entries[-500:]]}, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save security ledger: {e}")

    def log_event(
        self,
        action: str,
        user: str = "operator",
        status: str = "ALLOWED",
        details: Optional[Dict[str, Any]] = None,
        severity: str = "INFO",
    ) -> AuditEntry:
        """Appends a cryptographically chained event to the audit ledger."""
        now = time.time()
        idx = len(self.entries)
        prev_h = self.entries[-1].entry_hash if self.entries else self.GENESIS_HASH
        det = details or {}

        entry_h = self._compute_hash(idx, now, action, user, status, det, prev_h)

        entry = AuditEntry(
            index=idx,
            timestamp=now,
            action=action,
            user=user,
            severity=severity,
            status=status,
            details=det,
            prev_hash=prev_h,
            entry_hash=entry_h,
        )
        self.entries.append(entry)
        self._save_ledger()
        return entry

    def verify_ledger_integrity(self) -> Tuple[bool, int, Optional[str]]:
        """
        Validates cryptographic integrity across the entire ledger chain.
        Returns: (is_valid: bool, verified_count: int, error_message: str or None)
        """
        if not self.entries:
            return True, 0, None

        expected_prev = self.GENESIS_HASH if self.entries[0].index == 0 else self.entries[0].prev_hash
        for idx, e in enumerate(self.entries):
            if e.prev_hash != expected_prev:
                return False, idx, f"Hash chain broken at index {idx}: expected prev_hash {expected_prev}, got {e.prev_hash}"

            recalc = self._compute_hash(e.index, e.timestamp, e.action, e.user, e.status, e.details, e.prev_hash)
            if recalc != e.entry_hash:
                return False, idx, f"Data tampering detected at index {idx}: hash mismatch."

            expected_prev = e.entry_hash

        return True, len(self.entries), None

    def scan_threat(self, query_or_payload: str) -> Tuple[bool, List[str]]:
        """
        Scans input for SQL injection, path traversal, shell injection, or privilege attacks.
        Returns (threat_detected: bool, reasons: list).
        """
        text = str(query_or_payload).lower()
        threats = []

        # Path Traversal
        if any(pt in text for pt in ["../", "..\\", "..%2f", "..%5c", "/etc/shadow", "/etc/passwd"]):
            threats.append("Path Traversal attack pattern detected.")

        # SQL Injection
        sql_patterns = ["union select", "' or '1'='1", "'; drop table", "admin' --", "drop table", "alter table"]
        if any(sp in text for sp in sql_patterns):
            threats.append("SQL Injection signature detected.")

        # Remote Shell Injection
        shell_patterns = ["; rm -rf", "| rm -rf", "&& rm -rf", "; shutdown", "/dev/tcp/", "powershell -enc", "mkfifo /tmp/"]
        if any(shp in text for shp in shell_patterns):
            threats.append("Destructive shell command execution pattern detected.")

        if threats:
            self.log_event(
                action="threat_detected",
                user="threat_scanner",
                status="BLOCKED",
                details={"input": text[:200], "reasons": threats},
                severity="HIGH",
            )
            return True, threats

        return False, []

    # -------------------------------------------------------------------------
    # Confirmation Gate Management
    # -------------------------------------------------------------------------

    def create_confirmation_token(
        self,
        action: str,
        context: Dict[str, Any],
        expiry_seconds: int = 300,
    ) -> str:
        """Issues a cryptographically secure token for an action requiring explicit confirmation."""
        token = f"CONFIRM-{secrets.token_hex(4).upper()}"
        self._tokens[token] = {
            "action": action,
            "context": context,
            "expires_at": time.time() + expiry_seconds,
        }
        self.log_event(
            action="confirmation_token_issued",
            status="PENDING",
            details={"token": token, "target_action": action},
            severity="WARNING",
        )
        return token

    def validate_confirmation_token(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validates and consumes a confirmation token."""
        tok = token.strip().upper()
        record = self._tokens.get(tok)
        if not record:
            return False, None

        if time.time() > record["expires_at"]:
            self._tokens.pop(tok, None)
            return False, None

        # Token valid -> consume it
        self._tokens.pop(tok, None)
        self.log_event(
            action="confirmation_token_redeemed",
            status="CONFIRMED",
            details={"token": tok, "target_action": record["action"]},
            severity="INFO",
        )
        return True, record["context"]


# Global Singleton
security_audit = SecurityAudit()
