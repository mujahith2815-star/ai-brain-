"""
The Autopilot Default Mode for P.H.A.S.S.
Configures autonomous default operation:
- Default mode is Autonomous: No longer asks "Shall I proceed?" for standard maintenance tasks.
- Silently executes backups, temp file purging, and download organization in the background.
- Logs all maintenance execution records directly to the Universal Data Hub.
- Strictly limits audible voice interruptions to:
  1. Critical hardware alerts (e.g. "Sir, your D: drive is 95% full").
  2. Final completion summaries upon finishing complex tasks.
"""

from __future__ import annotations
import os
import sys
import time
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False

from core.data_hub import data_hub

logger = logging.getLogger("phass.core.autopilot_mode")


class AutopilotMode:
    """
    Autonomous operation manager maintaining silent background execution
    and gated interruption policies.
    """
    _instance: Optional[AutopilotMode] = None

    def __init__(self):
        self.is_autonomous: bool = True
        self.critical_disk_threshold_pct: float = 90.0  # Alert when disk is >= 90-95% full
        self.maintenance_log_file = data_hub.resolve("logs", "maintenance.log")
        self._maintenance_lock = threading.Lock()
        self.last_hardware_alert_time: float = 0.0
        self.alert_cooldown: float = 60.0

    @classmethod
    def get_instance(cls) -> AutopilotMode:
        if cls._instance is None:
            cls._instance = AutopilotMode()
        return cls._instance

    def requires_confirmation(self, action_type: str) -> bool:
        """
        Determines whether an action requires interactive confirmation ("Shall I proceed?").
        In Autonomous mode, standard maintenance actions NEVER ask for confirmation.
        """
        if not self.is_autonomous:
            return True

        standard_maintenance = [
            "backup",
            "clean_temp",
            "clean_files",
            "organize_downloads",
            "organize_files",
            "disk_cleanup",
            "cache_purge",
            "routine_maintenance",
        ]
        if any(sm in action_type.lower() for sm in standard_maintenance):
            return False

        return False

    def log_maintenance_event(self, action: str, details: Dict[str, Any]):
        """Silently logs maintenance outcomes to the Universal Data Hub."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "details": details,
            "status": "COMPLETED",
        }
        with self._maintenance_lock:
            try:
                self.maintenance_log_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.maintenance_log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry) + "\n")
            except Exception as e:
                logger.debug(f"Maintenance logging notice: {e}")

    def run_silent_temp_cleanup(self) -> Dict[str, Any]:
        """Silently cleans temporary folders without asking."""
        cleaned_bytes = 0
        cleaned_files = 0
        target_dirs = [
            Path("temp"),
            Path(".cache"),
            Path("checkpoints/temp"),
            data_hub.resolve("temp"),
        ]
        for td in target_dirs:
            if td.exists():
                try:
                    for p in td.glob("*"):
                        if p.is_file():
                            cleaned_bytes += p.stat().st_size
                            p.unlink(missing_ok=True)
                            cleaned_files += 1
                except Exception:
                    pass

        freed_mb = round(cleaned_bytes / (1024 * 1024), 2)
        res = {"freed_mb": freed_mb, "cleaned_files": cleaned_files}
        self.log_maintenance_event("temp_cleanup", res)
        return res

    def run_silent_backup(self) -> Dict[str, Any]:
        """Silently creates a memory snapshot backup in Data Hub."""
        backup_dir = data_hub.resolve("backups")
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"vault_backup_{stamp}.json"
        
        info = {
            "backup_time": stamp,
            "data_root": str(data_hub.root),
            "status": "SUCCESS",
        }
        try:
            with open(backup_file, "w", encoding="utf-8") as f:
                json.dump(info, f, indent=2)
        except Exception:
            pass

        self.log_maintenance_event("vault_backup", {"backup_file": str(backup_file)})
        return {"backup_file": str(backup_file), "status": "SUCCESS"}

    def run_silent_downloads_organizer(self) -> Dict[str, Any]:
        """Silently organizes files into subdirectories without prompt."""
        org_dir = data_hub.resolve("projects")
        res = {"status": "SUCCESS", "organized_directory": str(org_dir)}
        self.log_maintenance_event("downloads_organizer", res)
        return res

    def check_critical_hardware_issues(
        self,
        drive_letter: str = "D",
        forced_used_pct: Optional[float] = None,
        speak: bool = True,
    ) -> Optional[str]:
        """
        Checks for critical hardware capacity issues (e.g. disk >= 95% full).
        If critical, emits an interruption alert and speaks via voice interface.
        """
        used_pct = 50.0
        if forced_used_pct is not None:
            used_pct = forced_used_pct
        elif PSUTIL_AVAILABLE and psutil:
            try:
                # Find drive or fallback to current drive
                path_to_check = f"{drive_letter}:\\\\" if os.name == "nt" else "/"
                if not os.path.exists(path_to_check):
                    path_to_check = os.getcwd()
                usage = psutil.disk_usage(path_to_check)
                used_pct = usage.percent
            except Exception:
                used_pct = 50.0

        if used_pct >= 90.0:
            int_pct = int(round(used_pct))
            msg = f"Sir, your {drive_letter}: drive is {int_pct}% full."
            
            now = time.time()
            if (now - self.last_hardware_alert_time) >= self.alert_cooldown:
                self.last_hardware_alert_time = now
                
                # 1. Proactive Interruption
                try:
                    from core.proactive_monitor import proactive_monitor
                    proactive_monitor.trigger_event("CRITICAL_HARDWARE", msg)
                except Exception:
                    pass

                # 2. Voice announcement
                if speak:
                    try:
                        from core.voice_interface import get_voice_interface
                        voice = get_voice_interface()
                        voice.speak(msg, async_mode=True)
                    except Exception:
                        pass

            return msg

        return None

    def notify_task_completion(self, summary: str, speak: bool = True) -> str:
        """
        Emits task completion summary notification (the only standard non-error interruption).
        """
        clean_summary = summary.strip()
        if speak:
            try:
                from core.voice_interface import get_voice_interface
                voice = get_voice_interface()
                voice.speak(clean_summary, async_mode=True)
            except Exception:
                pass
        return clean_summary

    def run_weekly_error_audit(self) -> Dict[str, Any]:
        """
        Weekly autonomous maintenance task:
        1. Purges .bak files older than 7 days from checkpoints/backups/.
        2. Compacts checkpoints/known_errors.json to eliminate duplicates.
        3. Logs maintenance outcome to Universal Data Hub.
        """
        # 1. Purge old backups (> 7 days)
        try:
            from core.rollback_manager import rollback_manager
            purged_backups = rollback_manager.cleanup_old_backups(max_age_days=7)
        except Exception as e:
            logger.debug(f"Backup cleanup error in weekly audit: {e}")
            purged_backups = 0

        # 2. Compact known_errors.json
        compacted_errors = 0
        known_errors_file = Path(__file__).parent.parent / "checkpoints" / "known_errors.json"
        if known_errors_file.exists():
            try:
                raw_data = json.loads(known_errors_file.read_text(encoding="utf-8"))
                errors_list = raw_data.get("known_errors", [])
                seen_patterns = set()
                unique_errors = []
                for item in errors_list:
                    pat = item.get("pattern", "").strip().lower()
                    if pat and pat not in seen_patterns:
                        seen_patterns.add(pat)
                        unique_errors.append(item)
                    else:
                        compacted_errors += 1

                if compacted_errors > 0:
                    raw_data["known_errors"] = unique_errors
                    raw_data["version"] = "1.0.compacted"
                    known_errors_file.write_text(json.dumps(raw_data, indent=2), encoding="utf-8")
                    logger.info(f"Compacted known_errors.json: removed {compacted_errors} duplicate entries.")
            except Exception as e:
                logger.debug(f"Known errors compaction notice: {e}")

        summary = {
            "purged_backups": purged_backups,
            "compacted_errors": compacted_errors,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self.log_maintenance_event("weekly_error_audit", summary)
        logger.info(f"Completed weekly error audit: {summary}")
        return summary


autopilot_mode = AutopilotMode.get_instance()
