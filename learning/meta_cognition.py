"""
Self-Evaluation & Meta-Cognition Engine for P.H.A.S.S Sphere.
Computes self-reflection reports, measures calibration gaps (overconfidence vs underconfidence),
and refines risk tolerance heuristics based on task outcomes.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger("phass.learning.meta_cognition")


@dataclass
class MetaCognitiveReflection:
    goal_id: str
    goal_title: str
    predicted_confidence: float
    actual_outcome_success: bool
    calibration_error: float # Difference between predicted probability and binary outcome
    self_critique: str
    recommended_policy_adjustment: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "goal_title": self.goal_title,
            "predicted_confidence": round(self.predicted_confidence, 2),
            "actual_outcome_success": self.actual_outcome_success,
            "calibration_error": round(self.calibration_error, 2),
            "self_critique": self.self_critique,
            "recommended_policy_adjustment": self.recommended_policy_adjustment,
            "timestamp": self.timestamp,
        }


class MetaCognitionEngine:
    def __init__(self):
        self.reflections: List[MetaCognitiveReflection] = []
        self.confidence_calibration_offset: float = 0.0

    def evaluate_completed_goal(
        self,
        goal_id: str,
        goal_title: str,
        predicted_confidence: float,
        success: bool,
        subtasks_count: int,
        error: Optional[str] = None,
    ) -> MetaCognitiveReflection:
        actual_val = 1.0 if success else 0.0
        calib_error = abs(predicted_confidence - actual_val)

        if success:
            if predicted_confidence > 0.8:
                critique = "Accurate confidence calibration; plan execution matched expected high feasibility."
                adj = "Maintain current heuristic risk threshold."
            else:
                critique = "Underconfident prediction; task succeeded smoothly despite cautious initial score."
                adj = "Slightly increase autonomy aggressiveness score (+0.05)."
                self.confidence_calibration_offset += 0.02
        else:
            critique = f"Overconfident failure: Expected success with {int(predicted_confidence*100)}% confidence, but failed with: {error}."
            adj = "Apply defensive prerequisite checks and decrease risk threshold (-0.10)."
            self.confidence_calibration_offset -= 0.05

        reflection = MetaCognitiveReflection(
            goal_id=goal_id,
            goal_title=goal_title,
            predicted_confidence=predicted_confidence,
            actual_outcome_success=success,
            calibration_error=calib_error,
            self_critique=critique,
            recommended_policy_adjustment=adj,
        )
        self.reflections.append(reflection)
        if len(self.reflections) > 100:
            self.reflections.pop(0)

        logger.info(f"Meta-Cognitive reflection logged for {goal_id}: {critique}")
        return reflection

    def get_latest_reflections(self, limit: int = 10) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self.reflections[-limit:]]


meta_cognition = MetaCognitionEngine()
