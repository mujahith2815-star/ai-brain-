"""
Proactive Real-Time Auto-Goal Generation System for P.H.A.S.S Sphere.
Autonomously synthesizes high-level goals based on internal drives,
environmental anomalies, unmapped areas, and power management triggers.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import logging
from .goal_manager import GoalManager, GoalPriority, Goal
from .event_bus import event_bus, Event, EventType

logger = logging.getLogger("phass.core.auto_goal")


class AutoGoalTriggerType(str, Enum):
    POWER_MANAGEMENT = "POWER_MANAGEMENT"
    SENSORY_ANOMALY = "SENSORY_ANOMALY"
    PROACTIVE_EXPLORATION = "PROACTIVE_EXPLORATION"
    HARDWARE_HEALTH = "HARDWARE_HEALTH"
    SYSTEM_OPTIMIZATION = "SYSTEM_OPTIMIZATION"


@dataclass
class AutoGoalCandidate:
    title: str
    description: str
    trigger_type: AutoGoalTriggerType
    priority: GoalPriority
    urgency: float
    trigger_context: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "trigger_type": self.trigger_type.value,
            "priority": self.priority.name,
            "urgency": round(self.urgency, 2),
            "trigger_context": self.trigger_context,
        }


class ProactiveAutoGoalEngine:
    def __init__(self, goal_manager: GoalManager):
        self.goal_manager = goal_manager
        self.last_auto_goal_time: float = 0.0
        self.auto_goals_generated: List[AutoGoalCandidate] = []
        self.cooldown_seconds: float = 20.0

    def evaluate_proactive_triggers(
        self,
        robot_state: Dict[str, Any],
        world_snapshot: Dict[str, Any],
        anomaly_score: float = 0.0,
        active_goal_count: int = 0,
    ) -> Optional[AutoGoalCandidate]:
        """
        Evaluates world conditions and generates proactive goals if conditions are met.
        """
        # If robot is already busy executing user goals, defer low-priority auto goals
        battery_pct = float(robot_state.get("battery_percentage", 100.0))
        core_temp = float(robot_state.get("internal_temp_c", 30.0))

        # 1. Critical Power Trigger (Always high priority)
        if battery_pct < 18.0 and not any("dock" in g.get("title", "").lower() for g in self.goal_manager.list_active_goals()):
            candidate = AutoGoalCandidate(
                title="Navigate to Magnetic Fast-Charge Dock & Recharge",
                description="Autonomous safety action triggered by critical power depletion.",
                trigger_type=AutoGoalTriggerType.POWER_MANAGEMENT,
                priority=GoalPriority.CRITICAL,
                urgency=0.98,
                trigger_context={"battery_percentage": battery_pct},
            )
            return candidate

        # 2. Sensory / Hardware Anomaly Trigger
        if anomaly_score > 0.35 and active_goal_count == 0:
            candidate = AutoGoalCandidate(
                title="Investigate Sensory Anomaly & Run Hardware Diagnostics",
                description=f"Neural autoencoder flagged high sensory reconstruction loss ({anomaly_score}).",
                trigger_type=AutoGoalTriggerType.SENSORY_ANOMALY,
                priority=GoalPriority.HIGH,
                urgency=0.85,
                trigger_context={"anomaly_score": anomaly_score},
            )
            return candidate

        # 3. High Core Temperature Self-Healing Trigger
        if core_temp > 55.0 and active_goal_count == 0:
            candidate = AutoGoalCandidate(
                title="Engage Active Cooling & Diagnostic Thermal Throttle",
                description=f"Core temperature exceeded normal operating bounds ({core_temp}°C).",
                trigger_type=AutoGoalTriggerType.HARDWARE_HEALTH,
                priority=GoalPriority.HIGH,
                urgency=0.88,
                trigger_context={"core_temperature_c": core_temp},
            )
            return candidate

        # 4. Proactive Spatial Exploration (When idle and battery is healthy)
        if active_goal_count == 0 and battery_pct > 60.0 and len(self.auto_goals_generated) < 5:
            candidate = AutoGoalCandidate(
                title="Perform Autonomous 360 LiDAR Mapping & Spatial Verification",
                description="Proactive exploration drive to maintain up-to-date spatial landmark map.",
                trigger_type=AutoGoalTriggerType.PROACTIVE_EXPLORATION,
                priority=GoalPriority.NORMAL,
                urgency=0.45,
                trigger_context={"status": "idle_patrol"},
            )
            return candidate

        return None

    def trigger_auto_goal(self, candidate: AutoGoalCandidate) -> Goal:
        self.auto_goals_generated.append(candidate)
        goal = self.goal_manager.create_goal(
            title=candidate.title,
            description=candidate.description,
            priority=candidate.priority,
            context={
                "source": "proactive_auto_goal_engine",
                "trigger_type": candidate.trigger_type.value,
                "urgency": candidate.urgency,
                "trigger_context": candidate.trigger_context,
            },
        )
        logger.info(f"Auto-Goal triggered: '{candidate.title}' [Priority: {candidate.priority.name}]")
        return goal

    def get_recent_auto_goals(self, limit: int = 10) -> List[Dict[str, Any]]:
        return [g.to_dict() for g in self.auto_goals_generated[-limit:]]
