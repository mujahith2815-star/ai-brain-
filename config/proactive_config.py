"""
Proactive Autonomous Agent Configuration for Orvix Sphere / P.H.A.S.S.
Controls background scheduling, file/condition watchers, rate limits, and safety defaults.
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List


@dataclass
class ProactiveConfig:
    # Master switch (OFF by default for safety)
    proactive_enabled: bool = False

    # Safety & Approval Guardrails
    approval_required_for_destructive: bool = True
    max_actions_per_hour: int = 20
    check_interval_sec: int = 30
    log_retention_days: int = 30

    # Whitelisted watch directories
    allowed_watch_folders: List[str] = field(default_factory=lambda: [
        "knowledge/inbox",
        "Downloads",
        "Documents/Notes"
    ])

    # Schedules and triggers files
    schedules_file: str = "proactive/schedules.json"
    triggers_file: str = "proactive/triggers.json"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def save_to_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)


# Global singleton configuration
proactive_config = ProactiveConfig()

# Top-level constant aliases for direct imports
PROACTIVE_ENABLED = proactive_config.proactive_enabled
APPROVAL_REQUIRED_FOR_DESTRUCTIVE = proactive_config.approval_required_for_destructive
MAX_ACTIONS_PER_HOUR = proactive_config.max_actions_per_hour
CHECK_INTERVAL_SEC = proactive_config.check_interval_sec
LOG_RETENTION_DAYS = proactive_config.log_retention_days
ALLOWED_WATCH_FOLDERS = proactive_config.allowed_watch_folders
