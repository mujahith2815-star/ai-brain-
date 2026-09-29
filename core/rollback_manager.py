"""
Rollback & Deploy Manager for P.H.A.S.S Autonomic Recovery Circuit.
Manages pre-fix snapshots (.bak), hot deployment to live files,
service reloading/restarting, 60-second crash rollback watcher,
backup retention audits, and immunity dashboard metrics.
"""

from __future__ import annotations
import importlib
import json
import logging
import os
import shutil
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from core.fix_generator import GeneratedFix
from core.fix_validator import ValidationResult

logger = logging.getLogger("phass.core.rollback_manager")

PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_BACKUP_DIR = PROJECT_ROOT / "checkpoints" / "backups"
DEFAULT_METRICS_FILE = PROJECT_ROOT / "checkpoints" / "immunity_metrics.json"


@dataclass
class DeploymentResult:
    success: bool
    target_file: str
    backup_path: Optional[str] = None
    service_restarted: bool = False
    rolled_back: bool = False
    message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "target_file": self.target_file,
            "backup_path": self.backup_path,
            "service_restarted": self.service_restarted,
            "rolled_back": self.rolled_back,
            "message": self.message,
            "timestamp": self.timestamp,
        }


class RollbackManager:
    """
    Manages live deployment of validated patches, automatic file backups,
    service reloads, unhandled exception rollback triggers within 60s,
    and immunity metrics tracking.
    """

    ROLLBACK_WINDOW_SECONDS = 60.0

    def __init__(
        self,
        backup_dir: Optional[Union[str, Path]] = None,
        metrics_file: Optional[Union[str, Path]] = None,
    ):
        self.backup_dir = Path(backup_dir) if backup_dir else DEFAULT_BACKUP_DIR
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.metrics_file = Path(metrics_file) if metrics_file else DEFAULT_METRICS_FILE
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()
        # Active deployments: target_file_norm -> {"deployed_at": float, "backup_path": Path, "fix": GeneratedFix}
        self.active_deployments: Dict[str, Dict[str, Any]] = {}

        self._init_metrics()

    def _init_metrics(self):
        """Initializes or loads the persistent immunity metrics file."""
        with self._lock:
            if not self.metrics_file.exists():
                today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                initial_data = {
                    "date": today_str,
                    "errors_fixed_today": 0,
                    "pending_review": 0,
                    "rollbacks": 0,
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "history": [],
                }
                self.metrics_file.write_text(json.dumps(initial_data, indent=2), encoding="utf-8")

    def get_metrics(self) -> Dict[str, Any]:
        """Loads and returns current immunity metrics, resetting daily counters if day rolled over."""
        with self._lock:
            if not self.metrics_file.exists():
                self._init_metrics()

            try:
                data = json.loads(self.metrics_file.read_text(encoding="utf-8"))
            except Exception:
                data = {
                    "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "errors_fixed_today": 0,
                    "pending_review": 0,
                    "rollbacks": 0,
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "history": [],
                }

            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            if data.get("date") != today_str:
                data["date"] = today_str
                data["errors_fixed_today"] = 0
                self._save_metrics(data)

            return data

    def _save_metrics(self, data: Dict[str, Any]):
        """Persists metrics data to disk."""
        data["last_updated"] = datetime.now(timezone.utc).isoformat()
        try:
            self.metrics_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save immunity metrics: {e}")

    def increment_metric(self, metric_name: str, amount: int = 1, event_record: Optional[Dict[str, Any]] = None):
        """Increments a designated metric counter and appends event history."""
        with self._lock:
            data = self.get_metrics()
            data[metric_name] = data.get(metric_name, 0) + amount
            if event_record:
                if "timestamp" not in event_record:
                    event_record["timestamp"] = datetime.now(timezone.utc).isoformat()
                history = data.setdefault("history", [])
                history.append(event_record)
                # Keep last 100 history items
                if len(history) > 100:
                    data["history"] = history[-100:]
            self._save_metrics(data)

    def record_pending_review(self, fix: GeneratedFix):
        """Records a fix that failed confidence safety valve (<70%) and requires user review."""
        record = {
            "action": "PENDING_USER_REVIEW",
            "target_file": fix.target_file,
            "error_type": fix.error_type,
            "confidence": round(fix.confidence, 2),
            "explanation": fix.explanation,
        }
        self.increment_metric("pending_review", 1, record)
        logger.warning(f"Recorded pending user review for {fix.target_file} (Confidence: {fix.confidence*100:.1f}%)")

    def backup_file(self, target_file: Union[str, Path]) -> Path:
        """
        Creates a pre-fix backup snapshot in checkpoints/backups/[filename]_[timestamp].bak.
        Returns the absolute path to the backup file.
        """
        target_path = Path(target_file).resolve()
        if not target_path.exists():
            raise FileNotFoundError(f"Cannot backup non-existent file: {target_path}")

        self.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{target_path.name}_{timestamp}.bak"
        backup_path = self.backup_dir / backup_name

        shutil.copy2(target_path, backup_path)
        logger.info(f"Pre-fix backup created: {backup_path}")
        return backup_path

    def deploy_fix(
        self,
        fix: GeneratedFix,
        validation_result: Optional[ValidationResult] = None,
        restart_service_if_needed: bool = True,
    ) -> DeploymentResult:
        """
        Hot-deploys a validated fix:
        1. Verifies validation_result passed.
        2. Takes pre-fix snapshot (.bak).
        3. Writes repaired code to live file.
        4. Reloads module in sys.modules or restarts affected service.
        5. Registers active deployment with 60s rollback window.
        6. Updates immunity counters.
        """
        if validation_result and not validation_result.passed:
            msg = f"Deployment aborted: Validation failed ({validation_result.error_message})"
            logger.error(msg)
            return DeploymentResult(
                success=False,
                target_file=fix.target_file,
                message=msg,
            )

        target_path = Path(fix.target_file).resolve()

        # 1. Backup live file
        try:
            backup_path = self.backup_file(target_path)
        except Exception as e:
            msg = f"Deployment aborted: Failed to create pre-fix backup: {e}"
            logger.error(msg)
            return DeploymentResult(
                success=False,
                target_file=str(target_path),
                message=msg,
            )

        # 2. Hot-deploy fix to live file
        try:
            target_path.write_text(fix.repaired_code, encoding="utf-8")
            logger.info(f"Hot-deployed fix to live file: {target_path}")
        except Exception as e:
            msg = f"Deployment failed during write: {e}"
            logger.error(msg)
            return DeploymentResult(
                success=False,
                target_file=str(target_path),
                backup_path=str(backup_path),
                message=msg,
            )

        # 3. Reload module or restart service
        service_restarted = False
        if restart_service_if_needed:
            service_restarted = self.restart_affected_service_or_reload(target_path)

        # 4. Register active deployment for 60s rollback window
        norm_key = str(target_path).lower()
        self.active_deployments[norm_key] = {
            "target_path": target_path,
            "backup_path": backup_path,
            "deployed_at": time.time(),
            "fix": fix,
            "error_msg": fix.error_msg,
        }

        # 5. Record immunity metrics
        record = {
            "action": "HOTFIX_DEPLOYED",
            "target_file": str(target_path),
            "backup_path": str(backup_path),
            "error_type": fix.error_type,
            "confidence": round(fix.confidence, 2),
            "service_restarted": service_restarted,
        }
        self.increment_metric("errors_fixed_today", 1, record)

        return DeploymentResult(
            success=True,
            target_file=str(target_path),
            backup_path=str(backup_path),
            service_restarted=service_restarted,
            message=f"Fix deployed successfully with backup at {backup_path.name}",
        )

    def restart_affected_service_or_reload(self, target_path: Path) -> bool:
        """
        Reloads python module or triggers service restart if background daemon/voice was updated.
        """
        filename = target_path.name.lower()
        stem = target_path.stem
        service_restarted = False

        # Invalidate import caches
        importlib.invalidate_caches()

        # If voice_interface was modified, invoke voice guardian reload/restart
        if "voice_interface" in filename:
            try:
                from core.voice_guardian import VoiceGuardian
                vg = VoiceGuardian.get_instance()
                vg.restart_service()
                service_restarted = True
                logger.info("Triggered VoiceGuardian service restart.")
            except Exception as e:
                logger.debug(f"Voice service restart notice: {e}")

        # Reload any matched loaded module in sys.modules
        for mod_name, mod in list(sys.modules.items()):
            if mod and hasattr(mod, "__file__") and mod.__file__:
                try:
                    if Path(mod.__file__).resolve() == target_path:
                        importlib.reload(mod)
                        service_restarted = True
                        logger.info(f"Reloaded live module {mod_name}")
                        break
                except Exception as e:
                    logger.debug(f"Module reload notice for {mod_name}: {e}")

        return service_restarted

    def trigger_rollback(
        self,
        target_file: Union[str, Path],
        reason: str = "Unhandled exception within 60-second guard window",
    ) -> bool:
        """
        Immediately restores the latest .bak snapshot for target_file.
        Logs: "Sir, my attempt to fix [error] failed. I've rolled back to the previous version."
        """
        target_path = Path(target_file).resolve()
        norm_key = str(target_path).lower()

        backup_path: Optional[Path] = None
        error_context = reason

        # Check active deployments first
        if norm_key in self.active_deployments:
            dep = self.active_deployments.pop(norm_key)
            backup_path = dep.get("backup_path")
            error_context = dep.get("error_msg") or reason

        # If not in active deployments, find most recent backup for this file in backup_dir
        if not backup_path or not backup_path.exists():
            fname = target_path.name
            matching_backups = sorted(
                self.backup_dir.glob(f"{fname}_*.bak"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if matching_backups:
                backup_path = matching_backups[0]

        if not backup_path or not backup_path.exists():
            logger.error(f"Cannot rollback {target_path}: No backup found!")
            return False

        try:
            shutil.copy2(backup_path, target_path)
            self.restart_affected_service_or_reload(target_path)

            log_msg = f"Sir, my attempt to fix [{error_context}] failed. I've rolled back to the previous version."
            logger.warning(f"[P.H.A.S.S Rollback] {log_msg}")

            # Notify proactive monitor if active
            try:
                from core.proactive_monitor import proactive_monitor
                proactive_monitor.trigger_event("AUTONOMIC_ROLLBACK", log_msg)
            except Exception:
                pass

            # Update immunity metrics
            record = {
                "action": "ROLLBACK_TRIGGERED",
                "target_file": str(target_path),
                "restored_from": str(backup_path),
                "reason": reason,
            }
            self.increment_metric("rollbacks", 1, record)
            return True

        except Exception as e:
            logger.critical(f"Failed to restore backup {backup_path} to {target_path}: {e}")
            return False

    def notify_runtime_error(self, target_file: Union[str, Path], error: Exception) -> bool:
        """
        Called when a runtime exception occurs. If target_file was deployed within
        the last 60 seconds, triggers immediate automatic rollback.
        """
        target_path = Path(target_file).resolve()
        norm_key = str(target_path).lower()

        if norm_key in self.active_deployments:
            dep = self.active_deployments[norm_key]
            elapsed = time.time() - dep["deployed_at"]
            if elapsed <= self.ROLLBACK_WINDOW_SECONDS:
                logger.warning(
                    f"Exception occurred {elapsed:.1f}s after deployment (within {self.ROLLBACK_WINDOW_SECONDS}s guard). "
                    f"Triggering automatic rollback."
                )
                return self.trigger_rollback(target_path, reason=str(error))

        return False

    def cleanup_old_backups(self, max_age_days: int = 7) -> int:
        """
        Purges .bak files older than max_age_days from checkpoints/backups/.
        Returns count of deleted files.
        """
        if not self.backup_dir.exists():
            return 0

        cutoff = time.time() - (max_age_days * 86400.0)
        purged = 0

        for bak in self.backup_dir.glob("*.bak"):
            try:
                if bak.stat().st_mtime < cutoff:
                    bak.unlink()
                    purged += 1
                    logger.info(f"Purged expired backup: {bak.name}")
            except Exception as e:
                logger.debug(f"Failed to delete old backup {bak.name}: {e}")

        logger.info(f"Completed backup audit: purged {purged} files older than {max_age_days} days.")
        return purged


rollback_manager = RollbackManager()
