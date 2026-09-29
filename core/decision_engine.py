"""
Decision Engine for P.H.A.S.S Sphere.
Selects optimal actions, verifies safety permissions, enforces emergency boundaries,
and arbitrates execution priorities.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import logging
from .goal_manager import Goal, SubTask

logger = logging.getLogger("phass.decision_engine")


@dataclass
class Decision:
    action_type: str
    target_subtask: Optional[SubTask]
    tool_name: str
    parameters: Dict[str, Any]
    authorized: bool
    confidence: float
    reason: str
    requires_user_confirmation: bool = False


class DecisionEngine:
    def __init__(self, emergency_stop: bool = False):
        self.emergency_stop = emergency_stop
        self.critical_power_threshold_pct = 15.0

    def set_emergency_stop(self, active: bool) -> None:
        self.emergency_stop = active
        if active:
            logger.warning("EMERGENCY STOP ENGAGED across Decision Engine!")
        else:
            logger.info("Emergency stop disengaged. Normal decision flow restored.")

    def evaluate_next_action(
        self,
        goal: Goal,
        world_state: Dict[str, Any],
        tool_risk_level: str = "READ",
    ) -> Decision:
        """
        Determines the immediate action to take for an active goal and subtask.
        """
        # Safety Check: Emergency Stop
        if self.emergency_stop:
            return Decision(
                action_type="ABORT",
                target_subtask=None,
                tool_name="",
                parameters={},
                authorized=False,
                confidence=1.0,
                reason="Emergency Stop is currently active. Action denied.",
            )

        # Safety Check: Critical Power
        robot_state = world_state.get("robot_state", {})
        battery = robot_state.get("battery_percentage", 100.0)
        if battery < self.critical_power_threshold_pct and "dock" not in goal.title.lower() and "charge" not in goal.title.lower():
            logger.warning(f"Battery at {battery}%! Intercepting action to recommend recharging.")
            return Decision(
                action_type="PRIORITIZE_RECHARGE",
                target_subtask=None,
                tool_name="robot_dock",
                parameters={"reason": "Critical battery depletion"},
                authorized=True,
                confidence=0.98,
                reason=f"Battery level ({battery}%) is below safety threshold ({self.critical_power_threshold_pct}%).",
            )

        # Retrieve next pending subtask
        subtask = goal.get_current_subtask()
        if not subtask:
            return Decision(
                action_type="COMPLETE_GOAL",
                target_subtask=None,
                tool_name="",
                parameters={},
                authorized=True,
                confidence=0.95,
                reason="All subtasks completed successfully.",
            )

        # Check for High Risk authorization requirement
        requires_confirmation = tool_risk_level in ("EXECUTE", "SYSTEM")

        return Decision(
            action_type="EXECUTE_TOOL",
            target_subtask=subtask,
            tool_name=subtask.tool_name,
            parameters=subtask.parameters,
            authorized=True,
            confidence=subtask.confidence,
            reason=f"Executing planned step: '{subtask.title}' via tool '{subtask.tool_name}'",
            requires_user_confirmation=requires_confirmation,
        )
