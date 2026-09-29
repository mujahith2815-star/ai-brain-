"""
Mental Sandbox & Internal World Simulation Engine for P.H.A.S.S Sphere.
Forward simulation model predicting P(S_{t+1} | S_t, A_t).
Allows the agent to mentally "roll out" and simulate hypothetical plans
to verify physical clearance, collision risk, and energy expenditure before real execution.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger("phass.world.internal_simulation")


@dataclass
class SimulatedStepResult:
    step_index: int
    action_name: str
    predicted_position: Dict[str, float]
    predicted_battery_pct: float
    collision_risk: float  # 0.0 to 1.0
    energy_consumed_wh: float
    safety_cleared: bool
    notes: str


@dataclass
class MentalRolloutReport:
    plan_title: str
    total_steps: int
    simulated_steps: List[SimulatedStepResult]
    overall_success_probability: float
    max_collision_risk: float
    total_predicted_energy_wh: float
    recommendation: str  # "PROCEED_SAFE", "PROCEED_WITH_CAUTION", "ABORT_UNSAFE"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_title": self.plan_title,
            "total_steps": self.total_steps,
            "overall_success_probability": round(self.overall_success_probability, 2),
            "max_collision_risk": round(self.max_collision_risk, 3),
            "total_predicted_energy_wh": round(self.total_predicted_energy_wh, 2),
            "recommendation": self.recommendation,
            "timestamp": self.timestamp,
            "simulated_steps": [
                {
                    "step_index": s.step_index,
                    "action_name": s.action_name,
                    "predicted_pos": s.predicted_position,
                    "battery": round(s.predicted_battery_pct, 1),
                    "collision_risk": round(s.collision_risk, 3),
                    "safety": s.safety_cleared,
                }
                for s in self.simulated_steps
            ],
        }


class MentalSandboxEngine:
    def __init__(self):
        self.last_rollout: Optional[MentalRolloutReport] = None

    def simulate_plan_rollout(
        self,
        plan_title: str,
        actions: List[Dict[str, Any]],
        current_state: Dict[str, Any],
        known_obstacles: List[Dict[str, Any]],
    ) -> MentalRolloutReport:
        """
        Executes internal mental forward simulation across action sequence.
        """
        robot_state = current_state.get("robot_state", {})
        curr_pos = dict(robot_state.get("position", {"x": 0.0, "y": 0.0, "z": 0.25}))
        curr_batt = float(robot_state.get("battery_percentage", 100.0))

        step_results: List[SimulatedStepResult] = []
        total_energy = 0.0
        max_risk = 0.0

        for idx, act in enumerate(actions):
            act_name = act.get("tool", act.get("title", f"Action {idx+1}"))
            params = act.get("parameters", {})

            # 1. Forward Kinematics Simulation
            if "move" in act_name.lower() or "navigate" in act_name.lower():
                target_pos = params.get("target_pos", {})
                tx = target_pos.get("x", curr_pos["x"] + 0.5)
                ty = target_pos.get("y", curr_pos["y"] + 0.5)
                curr_pos["x"] = tx
                curr_pos["y"] = ty
                step_energy = 0.45  # Wh for motion
            else:
                step_energy = 0.10  # Wh for digital compute

            total_energy += step_energy
            curr_batt = max(0.0, curr_batt - (step_energy / 120.0) * 100.0)

            # 2. Collision Risk against Known Obstacles
            step_risk = 0.0
            for obs in known_obstacles:
                ox = obs.get("position", {}).get("x", 0.0)
                oy = obs.get("position", {}).get("y", 0.0)
                rad = obs.get("radius_m", 0.5)
                dist = math.hypot(curr_pos["x"] - ox, curr_pos["y"] - oy)
                if dist < rad + 0.3:
                    # High collision risk
                    step_risk = max(step_risk, (rad + 0.3 - dist) / 0.3)

            max_risk = max(max_risk, step_risk)
            cleared = step_risk < 0.3 and curr_batt > 10.0

            step_results.append(
                SimulatedStepResult(
                    step_index=idx + 1,
                    action_name=act_name,
                    predicted_position=dict(curr_pos),
                    predicted_battery_pct=curr_batt,
                    collision_risk=step_risk,
                    energy_consumed_wh=step_energy,
                    safety_cleared=cleared,
                    notes="Nominal rollout" if cleared else "Potential hazard or low energy detected",
                )
            )

        success_prob = max(0.1, 1.0 - (max_risk * 0.7) - (0.2 if curr_batt < 20 else 0.0))

        if max_risk > 0.6 or curr_batt < 12.0:
            rec = "ABORT_UNSAFE"
        elif max_risk > 0.2:
            rec = "PROCEED_WITH_CAUTION"
        else:
            rec = "PROCEED_SAFE"

        report = MentalRolloutReport(
            plan_title=plan_title,
            total_steps=len(actions),
            simulated_steps=step_results,
            overall_success_probability=success_prob,
            max_collision_risk=max_risk,
            total_predicted_energy_wh=total_energy,
            recommendation=rec,
        )

        self.last_rollout = report
        return report


mental_sandbox = MentalSandboxEngine()
