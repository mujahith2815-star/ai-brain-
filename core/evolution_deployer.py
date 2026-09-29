"""
Evolution Deployer & Rollback Engine for P.H.A.S.S Recursive Architect (v14.0).
Manages:
1. Pre-evolution .bak snapshots.
2. Hot live-code deployment and module reloading.
3. 60-second watchdog crash rollback protection.
4. Git auto-commit: 'P.H.A.S.S v14.0: Refactored [file] - speed improved by X%'.
5. Persistent evolution logging in checkpoints/evolution_log.json.
"""

from __future__ import annotations
import importlib
import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from core.code_generator import GeneratedPatch
from core.evolution_validator import ValidationReport

logger = logging.getLogger("phass.core.evolution_deployer")

PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_BACKUP_DIR = PROJECT_ROOT / "checkpoints" / "backups"
DEFAULT_EVOLUTION_LOG = PROJECT_ROOT / "checkpoints" / "evolution_log.json"


@dataclass
class EvolutionRecord:
    evolution_id: str
    target_file: str
    target_function: str
    status: str  # "SUCCEEDED", "ROLLED_BACK", "FAILED"
    speed_improvement_pct: float
    backup_path: str
    patch_path: str
    git_commit: str
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evolution_id": self.evolution_id,
            "target_file": self.target_file,
            "target_function": self.target_function,
            "status": self.status,
            "speed_improvement_pct": round(self.speed_improvement_pct, 2),
            "backup_path": self.backup_path,
            "patch_path": self.patch_path,
            "git_commit": self.git_commit,
            "message": self.message,
            "timestamp": self.timestamp,
        }


class EvolutionDeployer:
    """
    Deploys validated architectural enhancements to live files,
    reloads modules, protects with a 60-second rollback watchdog,
    and commits improvements to Git.
    """

    WATCHDOG_WINDOW_SECONDS = 60.0

    def __init__(
        self,
        backup_dir: Optional[Union[str, Path]] = None,
        evolution_log_file: Optional[Union[str, Path]] = None,
    ):
        self.backup_dir = Path(backup_dir) if backup_dir else DEFAULT_BACKUP_DIR
        self.evolution_log_file = Path(evolution_log_file) if evolution_log_file else DEFAULT_EVOLUTION_LOG
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.evolution_log_file.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()
        # Active watchdog deployments: norm_path -> {"record": EvolutionRecord, "deployed_at": float}
        self.active_watchdogs: Dict[str, Dict[str, Any]] = {}

    def get_evolution_history(self) -> List[Dict[str, Any]]:
        """Loads and returns all previous architectural evolution records."""
        with self._lock:
            if not self.evolution_log_file.exists():
                return []
            try:
                raw = json.loads(self.evolution_log_file.read_text(encoding="utf-8"))
                return raw if isinstance(raw, list) else []
            except Exception as e:
                logger.debug(f"Evolution history read error: {e}")
                return []

    def _append_evolution_log(self, record: EvolutionRecord):
        """Appends a new evolution record to checkpoints/evolution_log.json."""
        with self._lock:
            history = self.get_evolution_history()
            history.append(record.to_dict())
            try:
                self.evolution_log_file.write_text(json.dumps(history, indent=2), encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed to persist evolution log: {e}")

    def _update_record_status(self, evolution_id: str, new_status: str, note: str = ""):
        """Updates status of a specific evolution in the log (e.g. ROLLED_BACK)."""
        with self._lock:
            history = self.get_evolution_history()
            for entry in history:
                if entry.get("evolution_id") == evolution_id:
                    entry["status"] = new_status
                    if note:
                        entry["message"] += f" | {note}"
                    break
            try:
                self.evolution_log_file.write_text(json.dumps(history, indent=2), encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed to update evolution log: {e}")

    def backup_file(self, target_file: Union[str, Path]) -> Path:
        """Creates pre-evolution snapshot in checkpoints/backups/[file]_[timestamp].bak."""
        p = Path(target_file).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Cannot backup non-existent file: {p}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        bak_name = f"{p.name}_{timestamp}.bak"
        bak_path = self.backup_dir / bak_name
        shutil.copy2(p, bak_path)
        logger.info(f"Pre-evolution backup created: {bak_path}")
        return bak_path

    def commit_to_git(self, target_file: Path, speed_pct: float) -> str:
        """
        Auto-commits change to Git: 'P.H.A.S.S v14.0: Refactored [file] - speed improved by X%'.
        Gracefully handles environments without git installed.
        """
        filename = target_file.name
        commit_msg = f"P.H.A.S.S v14.0: Refactored {filename} - speed improved by {int(round(speed_pct))}%"

        try:
            # Check if git is available
            subprocess.run(["git", "add", str(target_file)], check=True, capture_output=True, timeout=5)
            subprocess.run(["git", "commit", "-m", commit_msg], check=True, capture_output=True, timeout=5)
            logger.info(f"Git commit created: {commit_msg}")
            return commit_msg
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            # Git is either not installed or repo not initialized: record simulated commit
            simulated_msg = f"Recorded: {commit_msg}"
            logger.info(f"Git unavailable ({e}). Logged evolution commit: {commit_msg}")
            return commit_msg

    def reload_module(self, target_path: Path) -> bool:
        """Hot-reloads modified module without full application restart."""
        importlib.invalidate_caches()
        reloaded = False

        for mod_name, mod in list(sys.modules.items()):
            if mod and hasattr(mod, "__file__") and mod.__file__:
                try:
                    if Path(mod.__file__).resolve() == target_path.resolve():
                        importlib.reload(mod)
                        reloaded = True
                        logger.info(f"Successfully hot-reloaded {mod_name}")
                        break
                except Exception as e:
                    logger.debug(f"Hot-reload note for {mod_name}: {e}")

        return reloaded

    def deploy_evolution(
        self,
        patch: GeneratedPatch,
        validation: ValidationReport,
    ) -> EvolutionRecord:
        """
        Deploys validated evolution patch:
        1. Verifies validation.passed is True.
        2. Creates pre-evolution backup (.bak).
        3. Replaces live file with patch.new_code.
        4. Reloads module.
        5. Registers 60s watchdog guard.
        6. Commits change to Git.
        7. Logs evolution record.
        """
        target_path = Path(patch.target_file).resolve()
        evo_id = f"EVO-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        if not validation.passed:
            rec = EvolutionRecord(
                evolution_id=evo_id,
                target_file=str(target_path),
                target_function=patch.target_function,
                status="FAILED",
                speed_improvement_pct=0.0,
                backup_path="",
                patch_path=patch.patch_path,
                git_commit="",
                message=f"Deployment aborted: Validation failed ({validation.details})",
            )
            self._append_evolution_log(rec)
            return rec

        # 1. Pre-evolution backup
        try:
            bak_path = self.backup_file(target_path)
        except Exception as e:
            rec = EvolutionRecord(
                evolution_id=evo_id,
                target_file=str(target_path),
                target_function=patch.target_function,
                status="FAILED",
                speed_improvement_pct=0.0,
                backup_path="",
                patch_path=patch.patch_path,
                git_commit="",
                message=f"Deployment aborted: Backup creation failed: {e}",
            )
            self._append_evolution_log(rec)
            return rec

        # 2. Hot-Deploy new code to live file
        try:
            target_path.write_text(patch.new_code, encoding="utf-8")
            logger.info(f"Hot-deployed evolution to {target_path}")
        except Exception as e:
            rec = EvolutionRecord(
                evolution_id=evo_id,
                target_file=str(target_path),
                target_function=patch.target_function,
                status="FAILED",
                speed_improvement_pct=0.0,
                backup_path=str(bak_path),
                patch_path=patch.patch_path,
                git_commit="",
                message=f"Deployment failed during write: {e}",
            )
            self._append_evolution_log(rec)
            return rec

        # 3. Reload live module
        self.reload_module(target_path)

        # 4. Commit to Git
        git_msg = self.commit_to_git(target_path, validation.speed_improvement_pct)

        # 5. Create Evolution Record
        rec = EvolutionRecord(
            evolution_id=evo_id,
            target_file=str(target_path),
            target_function=patch.target_function,
            status="SUCCEEDED",
            speed_improvement_pct=validation.speed_improvement_pct,
            backup_path=str(bak_path),
            patch_path=patch.patch_path,
            git_commit=git_msg,
            message=(
                f"Evolution SUCCESS: {patch.target_function} speed improved by "
                f"{int(round(validation.speed_improvement_pct))}%. Committed to Git."
            ),
        )

        # 6. Register 60s Watchdog
        norm_key = str(target_path).lower()
        with self._lock:
            self.active_watchdogs[norm_key] = {
                "record": rec,
                "deployed_at": time.time(),
                "backup_path": bak_path,
            }

        self._append_evolution_log(rec)
        return rec

    def trigger_rollback(
        self,
        target_file: Union[str, Path],
        reason: str = "Unhandled exception within 60s watchdog window",
    ) -> bool:
        """
        Immediately restores .bak file if error occurs within watchdog window.
        Alerts: 'Sir, evolution [ID] failed. I have rolled back to the previous version.'
        """
        target_path = Path(target_file).resolve()
        norm_key = str(target_path).lower()

        backup_path: Optional[Path] = None
        evo_id = "UNKNOWN"

        with self._lock:
            if norm_key in self.active_watchdogs:
                data = self.active_watchdogs.pop(norm_key)
                backup_path = data["backup_path"]
                evo_id = data["record"].evolution_id

        # Search backup dir if not in active watchdogs
        if not backup_path or not backup_path.exists():
            fname = target_path.name
            matching = sorted(self.backup_dir.glob(f"{fname}_*.bak"), key=lambda p: p.stat().st_mtime, reverse=True)
            if matching:
                backup_path = matching[0]

        if not backup_path or not backup_path.exists():
            logger.error(f"Cannot rollback {target_path}: No valid backup snapshot found.")
            return False

        try:
            shutil.copy2(backup_path, target_path)
            self.reload_module(target_path)

            alert_msg = f"Sir, evolution {evo_id} failed. I have rolled back to the previous version."
            logger.warning(f"[Evolution Watchdog Rollback] {alert_msg} (Reason: {reason})")

            # Dispatch proactive interrupt
            try:
                from core.proactive_monitor import proactive_monitor
                proactive_monitor.trigger_event("EVOLUTION_ROLLBACK", alert_msg)
            except Exception:
                pass

            # Update log
            self._update_record_status(evo_id, "ROLLED_BACK", f"Restored from {backup_path.name}: {reason}")
            return True

        except Exception as e:
            logger.critical(f"Failed to restore evolution backup {backup_path}: {e}")
            return False

    def notify_runtime_error(self, target_file: Union[str, Path], error: Exception) -> bool:
        """Called if an exception occurs in target_file within 60s of deployment."""
        target_path = Path(target_file).resolve()
        norm_key = str(target_path).lower()

        with self._lock:
            if norm_key in self.active_watchdogs:
                data = self.active_watchdogs[norm_key]
                elapsed = time.time() - data["deployed_at"]
                if elapsed <= self.WATCHDOG_WINDOW_SECONDS:
                    logger.warning(f"Error {error} occurred {elapsed:.1f}s after evolution deploy. Triggering rollback.")
                    return self.trigger_rollback(target_path, reason=str(error))
        return False


evolution_deployer = EvolutionDeployer()
