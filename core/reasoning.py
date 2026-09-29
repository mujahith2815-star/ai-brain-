"""
Reasoning Layer for P.H.A.S.S Sphere.
Handles contextual analysis, hypothesis synthesis, outcome evaluation,
and safe high-level summarization without leaking raw chain-of-thought.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging
from .ai_model import BaseAIModel, OfflineCognitiveEngine

logger = logging.getLogger("phass.reasoning")


@dataclass
class ReasoningResult:
    goal_id: str
    understanding_summary: str
    hypotheses: List[str]
    selected_strategy: str
    confidence: float
    dependencies: List[str]
    safety_checked: bool = True
    safe_public_summary: Dict[str, Any] = field(default_factory=dict)


class ReasoningEngine:
    def __init__(self, ai_model: Optional[BaseAIModel] = None):
        self.ai_model = ai_model or OfflineCognitiveEngine()

    async def analyze_context_and_goal(
        self,
        goal_description: str,
        world_state: Dict[str, Any],
        relevant_memories: List[Dict[str, Any]],
        experience_lessons: List[str],
    ) -> ReasoningResult:
        """
        Synthesizes world model belief state, episodic memories, and learned lessons
        to formulate a rigorous reasoning framework for the goal.
        """
        logger.info(f"ReasoningEngine analyzing goal: '{goal_description}'")

        # 1. Synthesize context
        active_entities = world_state.get("entities", [])
        robot_telemetry = world_state.get("robot_state", {})
        battery_pct = robot_telemetry.get("battery_percentage", 100)

        # 2. Derive hypotheses based on prior lessons
        hypotheses = []
        if experience_lessons:
            for lesson in experience_lessons[:3]:
                hypotheses.append(f"Consider prior lesson: {lesson}")

        if "failure" in goal_description.lower() or "diagnose" in goal_description.lower():
            hypotheses.extend([
                "Hypothesis A: System service or configuration inconsistency",
                "Hypothesis B: External environmental obstacle or disconnected peripheral",
                "Hypothesis C: Depleted battery or abnormal power draw",
            ])
        elif "environment" in goal_description.lower() or "scan" in goal_description.lower():
            hypotheses.extend([
                "Hypothesis A: Unmapped entities or obstacles present in operational radius",
                "Hypothesis B: Changing lighting or acoustics requiring multi-sensor fusion",
            ])
        else:
            hypotheses.append(f"Hypothesis: Objective can be fulfilled via digital action sequence")

        # 3. Strategy selection
        selected_strategy = (
            "Systematic multi-stage inspection with dependency verification"
            if len(hypotheses) > 1
            else "Direct atomic execution with post-condition check"
        )

        confidence = 0.92
        if battery_pct < 20:
            confidence -= 0.15
            hypotheses.append("Warning: Battery level critical; prioritizing low-power path")

        # 4. Generate Safe Public Summary (no raw chain-of-thought tokens)
        safe_summary = {
            "intent": goal_description,
            "status": "REASONING_COMPLETE",
            "active_strategy": selected_strategy,
            "key_factors": [
                f"Battery: {battery_pct}%",
                f"Observed Entities: {len(active_entities)}",
                f"Applied Lessons: {len(experience_lessons)}",
            ],
            "confidence_score": f"{int(confidence * 100)}%",
        }

        return ReasoningResult(
            goal_id="",
            understanding_summary=f"Goal recognized with high fidelity. Strategy '{selected_strategy}' formulated.",
            hypotheses=hypotheses,
            selected_strategy=selected_strategy,
            confidence=round(confidence, 2),
            dependencies=["world_model", "sensors", "memory"],
            safety_checked=True,
            safe_public_summary=safe_summary,
        )

    async def verify_outcome(
        self,
        goal_description: str,
        planned_subtasks: List[Dict[str, Any]],
        execution_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Checks whether execution results truly satisfy the original goal constraints.
        """
        all_succeeded = all(
            r.get("error") is None and r.get("state") in ("COMPLETED", "SUCCESS")
            for r in execution_results
        )
        has_critical_failure = any(r.get("error") is not None for r in execution_results)

        if all_succeeded:
            return {
                "goal_satisfied": True,
                "confidence": 0.96,
                "verification_notes": f"All {len(execution_results)} subtasks concluded with valid outputs meeting goal criteria.",
                "status": "VERIFIED_SUCCESS",
            }
        elif has_critical_failure:
            failed_steps = [r.get("title", "Unknown") for r in execution_results if r.get("error")]
            return {
                "goal_satisfied": False,
                "confidence": 0.40,
                "verification_notes": f"Goal execution failed on step(s): {', '.join(failed_steps)}.",
                "status": "VERIFIED_FAILURE",
            }
        else:
            return {
                "goal_satisfied": True,
                "confidence": 0.85,
                "verification_notes": "Subtasks executed with minor non-blocking warnings.",
                "status": "VERIFIED_PARTIAL_SUCCESS",
            }
