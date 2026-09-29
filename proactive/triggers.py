"""
Trigger Definitions and Loader for Proactive Autonomous Layer.
"""

import json
import logging
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger("orvix.proactive.triggers")


class TriggerType(str, Enum):
    CRON = "CRON"
    FILE_CHANGE = "FILE_CHANGE"
    CONDITION = "CONDITION"
    TIME_OF_DAY = "TIME_OF_DAY"


@dataclass
class Trigger:
    name: str
    type: str
    config: Dict[str, Any] = field(default_factory=dict)
    action: Any = field(default_factory=dict)
    requires_approval: bool = True
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Trigger":
        t_type = str(data.get("type", "CRON")).upper()
        return cls(
            name=data.get("name", "unnamed_trigger"),
            type=t_type,
            config=data.get("config", {}),
            action=data.get("action", ""),
            requires_approval=bool(data.get("requires_approval", True)),
            enabled=bool(data.get("enabled", True)),
        )


def validate_trigger(trigger: Trigger) -> Tuple[bool, str]:
    """
    Validates trigger integrity and ensures risky actions mandate user approval.
    """
    if not trigger.name or not isinstance(trigger.name, str):
        return (False, "Trigger must have a non-empty name")

    valid_types = {t.value for t in TriggerType}
    if trigger.type not in valid_types:
        return (False, f"Invalid trigger type '{trigger.type}'. Expected one of: {valid_types}")

    if not trigger.action:
        return (False, "Trigger action cannot be empty")

    from .safety import SafetyGuard
    sg = SafetyGuard()

    if isinstance(trigger.action, dict):
        tool = trigger.action.get("tool", "")
        args = trigger.action.get("args", {})
        if sg.is_destructive(tool, args) and not trigger.requires_approval:
            return (False, "Destructive trigger actions must require user approval")
    elif isinstance(trigger.action, str):
        act_lower = trigger.action.lower()
        if (
            sg.DESTRUCTIVE_PATTERN.search(trigger.action)
            or "rm -rf" in act_lower
            or "del /f" in act_lower
            or "delete all" in act_lower
            or "format " in act_lower
            or "drop table" in act_lower
            or "truncate " in act_lower
        ) and not trigger.requires_approval:
            return (False, "Destructive trigger actions must require user approval")

    return (True, "Valid trigger")


def load_triggers(path: str = "proactive/triggers.json") -> List[Trigger]:
    """
    Loads and validates triggers from a JSON file.
    """
    p = Path(path)
    if not p.is_absolute() and not p.exists():
        project_root = Path(__file__).resolve().parent.parent
        if (project_root / path).exists():
            p = project_root / path

    if not p.exists():
        logger.warning(f"Triggers file not found: {p}")
        return []

    triggers = []
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    trig = Trigger.from_dict(item)
                    valid, reason = validate_trigger(trig)
                    if valid:
                        triggers.append(trig)
                    else:
                        logger.warning(f"Skipping trigger '{trig.name}': {reason}")
    except Exception as e:
        logger.error(f"Error loading triggers from {p}: {e}")
        return []
    return triggers
