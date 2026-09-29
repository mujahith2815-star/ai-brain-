"""
Proactive Autonomous Agent Layer for Orvix Sphere.
Provides scheduled tasks, condition/file watchers, whitelisted autonomous execution,
and human-in-the-loop approval queues.
"""

from .safety import SafetyGuard
from .scheduler import TaskScheduler
from .watchers import FileSystemWatcher, ConditionWatcher
from .triggers import Trigger, TriggerType, load_triggers, validate_trigger
from .autonomous_agent import AutonomousAgent
from config.proactive_config import proactive_config, PROACTIVE_ENABLED

__all__ = [
    "SafetyGuard",
    "TaskScheduler",
    "FileSystemWatcher",
    "ConditionWatcher",
    "Trigger",
    "TriggerType",
    "load_triggers",
    "validate_trigger",
    "AutonomousAgent",
    "proactive_config",
    "PROACTIVE_ENABLED",
]
