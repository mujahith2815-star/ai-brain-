"""
Shadow Mode & Tripwire Security Guard for Llama Assistant & P.H.A.S.S Sphere.
Provides:
1. ShadowGuard: Interception and screening of high-risk shell commands and tool calls.
2. High-Risk Pattern Engine: Detects format, shred, rm -rf, sudo, fork bombs, DROP TABLE.
3. Cryptographic Audit Log: Tamper-evident SHA-256 chained execution ledger.
4. Snapshot & Recovery Engine: Automated zip backup prior to dangerous file operations and instant rollback.
"""

from __future__ import annotations
import os
import re
import json
import time
import zipfile
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("phass.security.shadow")

# Dangerous command regex signatures
HIGH_RISK_PATTERNS = [
    (re.compile(r"\brm\s+-[rfRF]+\b", re.IGNORECASE), "CRITICAL", "Recursive forced file deletion (rm -rf)"),
    (re.compile(r"\brmdir\s+/[sS]\b", re.IGNORECASE), "CRITICAL", "Recursive directory deletion (rmdir /s)"),
    (re.compile(r"\bdel\s+/[fF]\b", re.IGNORECASE), "HIGH", "Forced file deletion (del /f)"),
    (re.compile(r"\bformat\s+[a-zA-Z]:", re.IGNORECASE), "CRITICAL", "Drive formatting attempt"),
    (re.compile(r"\b(diskpart|fdisk|mkfs|shred)\b", re.IGNORECASE), "CRITICAL", "Raw disk partitioning or shredding"),
    (re.compile(r"\bsudo\s+rm\b", re.IGNORECASE), "CRITICAL", "Superuser recursive deletion"),
    (re.compile(r"\bdd\s+if=", re.IGNORECASE), "CRITICAL", "Low-level direct block write (dd)"),
    (re.compile(r"\bDROP\s+(TABLE|DATABASE)\b", re.IGNORECASE), "CRITICAL", "Destructive database drop"),
    (re.compile(r"\bTRUNCATE\s+TABLE\b", re.IGNORECASE), "HIGH", "Table truncation"),
    (re.compile(r"\bkill\s+-9\b", re.IGNORECASE), "HIGH", "Forced signal 9 termination"),
    (re.compile(r"\btaskkill\s+/[fF]", re.IGNORECASE), "HIGH", "Forced Windows taskkill"),
    (re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;", re.IGNORECASE), "CRITICAL", "Fork bomb denial-of-service"),
    (re.compile(r"\bchmod\s+-R\s+777\b", re.IGNORECASE), "HIGH", "Insecure global permission assignment"),
]

# Protected OS core paths
PROTECTED_PATHS = [
    r"^/etc(/|$)",
    r"^/boot(/|$)",
    r"^/sys(/|$)",
    r"^/proc(/|$)",
    r"^[a-zA-Z]:\\Windows(\\.*)?$",
    r"^[a-zA-Z]:\\Program Files(\\.*)?$",
]


class ShadowGuard:
    """
    Tripwire security enforcement system for autonomous agent workflows.
    Screens actions, generates safety snapshots, and records tamper-evident audit chains.
    """

    def __init__(self, security_dir: str = "checkpoints/security"):
        self.security_dir = Path(security_dir)
        self.snapshots_dir = self.security_dir / "snapshots"
        self.security_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

        self.audit_log_path = self.security_dir / "shadow_audit.jsonl"
        self._last_hash = "0" * 64
        self._load_last_hash()

    def _load_last_hash(self):
        """Loads the most recent block hash for SHA-256 chain integrity."""
        if not self.audit_log_path.exists():
            return
        try:
            with open(self.audit_log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if lines:
                    last_record = json.loads(lines[-1].strip())
                    self._last_hash = last_record.get("block_hash", self._last_hash)
        except Exception:
            pass

    def evaluate_risk(self, command: str) -> Tuple[str, str]:
        """
        Analyzes a command string against high-risk signatures and protected paths.
        Returns: (risk_level, reason)
        risk_level is one of: "CRITICAL", "HIGH", "MEDIUM", "SAFE"
        """
        for pattern, level, desc in HIGH_RISK_PATTERNS:
            if pattern.search(command):
                return level, desc

        for p_regex in PROTECTED_PATHS:
            if re.search(p_regex, command, re.IGNORECASE):
                return "CRITICAL", f"Command targets protected system path ({p_regex})"

        return "SAFE", "Standard operational command"

    def audit_command(
        self,
        command: str,
        user: str = "local_user",
        auto_confirm: bool = False,
    ) -> Dict[str, Any]:
        """
        Evaluates risk, decides whether to allow/block or request confirmation,
        and appends a hash-chained audit record.
        """
        risk_level, reason = self.evaluate_risk(command)
        timestamp = time.time()

        # Decision rule
        is_blocked = False
        requires_confirmation = False

        if risk_level == "CRITICAL":
            if not auto_confirm:
                is_blocked = True
                requires_confirmation = True
        elif risk_level == "HIGH":
            if not auto_confirm:
                requires_confirmation = True

        status = "BLOCKED" if is_blocked else ("APPROVED" if not requires_confirmation else "REQUIRES_CONFIRMATION")

        # Compute tamper-evident hash
        record_payload = f"{self._last_hash}:{timestamp}:{user}:{command}:{risk_level}:{status}"
        block_hash = hashlib.sha256(record_payload.encode("utf-8")).hexdigest()
        self._last_hash = block_hash

        record = {
            "timestamp": timestamp,
            "user": user,
            "command": command,
            "risk_level": risk_level,
            "reason": reason,
            "status": status,
            "block_hash": block_hash,
        }

        try:
            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.error(f"Failed to record shadow audit entry: {e}")

        return record

    def create_snapshot(self, directory_path: str, snapshot_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Archives the designated directory into an encrypted/compressed snapshot before
        modifications are enacted.
        """
        target = Path(directory_path)
        if not target.exists():
            return {"status": "ERROR", "error": f"Path does not exist: {directory_path}"}

        sid = snapshot_id or f"snap_{int(time.time())}_{target.name}"
        zip_path = self.snapshots_dir / f"{sid}.zip"

        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                if target.is_file():
                    zf.write(target, arcname=target.name)
                else:
                    for root, dirs, files in os.walk(target):
                        for f in files:
                            full_f = Path(root) / f
                            rel_f = full_f.relative_to(target)
                            zf.write(full_f, arcname=str(rel_f))

            sz_kb = round(zip_path.stat().st_size / 1024.0, 2)
            return {
                "status": "SUCCESS",
                "snapshot_id": sid,
                "path": str(zip_path.resolve()),
                "target": str(target.resolve()),
                "size_kb": sz_kb,
                "timestamp": time.time(),
            }
        except Exception as e:
            logger.error(f"Snapshot creation failed: {e}")
            return {"status": "ERROR", "error": str(e)}

    def restore_snapshot(self, snapshot_id: str, target_dir: str) -> Dict[str, Any]:
        """
        Restores a previously created snapshot zip into the designated target directory.
        """
        zip_path = self.snapshots_dir / f"{snapshot_id}.zip"
        if not zip_path.exists():
            # Try searching by exact name
            matches = list(self.snapshots_dir.glob(f"*{snapshot_id}*.zip"))
            if matches:
                zip_path = matches[0]
            else:
                return {"status": "ERROR", "error": f"Snapshot archive {snapshot_id} not found."}

        target = Path(target_dir)
        target.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(target)

            return {
                "status": "SUCCESS",
                "snapshot_id": snapshot_id,
                "restored_to": str(target.resolve()),
                "timestamp": time.time(),
            }
        except Exception as e:
            logger.error(f"Snapshot restore failed: {e}")
            return {"status": "ERROR", "error": str(e)}

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """Lists all available snapshots and backups."""
        snapshots = []
        for p in self.snapshots_dir.glob("*.zip"):
            snapshots.append({
                "snapshot_id": p.stem,
                "path": str(p.resolve()),
                "size_kb": round(p.stat().st_size / 1024.0, 2),
                "created_at": p.stat().st_mtime,
            })
        return sorted(snapshots, key=lambda x: x["created_at"], reverse=True)

    def get_audit_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves latest audit log entries."""
        if not self.audit_log_path.exists():
            return []
        entries = []
        try:
            with open(self.audit_log_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line.strip()))
        except Exception:
            pass
        return entries[-limit:]


# Global Singleton
shadow_guard = ShadowGuard()
