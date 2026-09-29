"""
Feedback System for P.H.A.S.S Sphere.
Classifies human and environmental feedback, distinguishing between
new contextual information and direct corrections, and extracts actionable lessons.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import logging
from core.event_bus import event_bus, Event, EventType

logger = logging.getLogger("phass.learning.feedback")


class FeedbackType(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    CORRECTION = "CORRECTION"
    CONFIRMATION = "CONFIRMATION"
    ADDITIONAL_INFO = "ADDITIONAL_INFO"
    TASK_COMPLETION = "TASK_COMPLETION"
    TASK_FAILURE = "TASK_FAILURE"


@dataclass
class FeedbackItem:
    text: str
    feedback_type: FeedbackType
    extracted_lesson: Optional[str] = None
    target_goal_id: Optional[str] = None
    source: str = "User"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "feedback_type": self.feedback_type.value,
            "extracted_lesson": self.extracted_lesson,
            "target_goal_id": self.target_goal_id,
            "source": self.source,
            "timestamp": self.timestamp,
        }


class FeedbackClassifier:
    def classify_feedback(self, text: str, target_goal_id: Optional[str] = None) -> FeedbackItem:
        """
        Analyzes feedback content and accurately identifies whether it is a
        direct correction, new situational information, confirmation, or polarity feedback.
        """
        t_lower = text.lower()
        fb_type = FeedbackType.ADDITIONAL_INFO
        extracted_lesson = None

        # 1. Direct Corrections
        if any(k in t_lower for k in ["no,", "wrong", "incorrect", "instead", "you should have", "not that", "mistake", "actually"]):
            fb_type = FeedbackType.CORRECTION
            extracted_lesson = f"Corrective Rule: {text.strip()}"
        # 2. Positive
        elif any(k in t_lower for k in ["good job", "great", "excellent", "perfect", "well done", "nice work"]):
            fb_type = FeedbackType.POSITIVE
            extracted_lesson = "Strategy reinforced by positive user feedback."
        # 3. Negative
        elif any(k in t_lower for k in ["bad", "terrible", "poor", "unacceptable", "failed"]):
            fb_type = FeedbackType.NEGATIVE
            extracted_lesson = f"Strategy penalization: Avoid repetition of {text.strip()}."
        # 4. Confirmation
        elif any(k in t_lower for k in ["yes", "confirmed", "proceed", "approved", "ok", "correct"]):
            fb_type = FeedbackType.CONFIRMATION
        # 5. Additional Information (New Fact / Update)
        else:
            fb_type = FeedbackType.ADDITIONAL_INFO
            extracted_lesson = f"Contextual Fact: {text.strip()}"

        logger.info(f"Classified feedback as [{fb_type.value}]: '{text}'")

        item = FeedbackItem(
            text=text,
            feedback_type=fb_type,
            extracted_lesson=extracted_lesson,
            target_goal_id=target_goal_id,
        )

        return item
