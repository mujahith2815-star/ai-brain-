"""
Natural Language Understanding (NLU) Subsystem for P.H.A.S.S Sphere.
Extracts semantic intent, named entities, slot parameters, urgency level, and ambiguity.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import re
import logging
from .nlp_pipeline import nlp_pipeline

logger = logging.getLogger("phass.nlp.nlu")


class IntentType(str, Enum):
    GOAL_DIRECTIVE = "GOAL_DIRECTIVE"           # e.g., "Analyze the system and fix the crash"
    DIAGNOSTIC_QUERY = "DIAGNOSTIC_QUERY"       # e.g., "Why did the service fail?"
    ENVIRONMENT_PROBE = "ENVIRONMENT_PROBE"     # e.g., "Inspect the room and report objects"
    NAVIGATION_REQUEST = "NAVIGATION_REQUEST"   # e.g., "Navigate to charging dock"
    STATUS_CHECK = "STATUS_CHECK"               # e.g., "What is your battery and system status?"
    FEEDBACK_POSITIVE = "FEEDBACK_POSITIVE"     # e.g., "Good job on that analysis"
    FEEDBACK_CORRECTION = "FEEDBACK_CORRECTION" # e.g., "No, check dependencies first before rebooting"
    EMERGENCY_COMMAND = "EMERGENCY_COMMAND"     # e.g., "Stop immediately, halt motors"
    CHITCHAT = "CHITCHAT"                       # e.g., "Who are you?"


@dataclass
class ExtractedEntity:
    entity_name: str
    category: str  # "DEVICE", "LOCATION", "OBJECT", "ACTION", "METRIC"
    confidence: float = 0.95
    raw_span: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_name": self.entity_name,
            "category": self.category,
            "confidence": round(self.confidence, 2),
            "raw_span": self.raw_span,
        }


@dataclass
class NLUUnderstandingResult:
    raw_text: str
    intent: IntentType
    intent_confidence: float
    slots: Dict[str, Any]
    entities: List[ExtractedEntity]
    urgency_score: float  # 0.0 to 1.0
    sentiment: str        # "POSITIVE", "NEUTRAL", "NEGATIVE"
    is_ambiguous: bool
    ambiguity_reason: Optional[str] = None
    extracted_keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_text": self.raw_text,
            "intent": self.intent.value,
            "intent_confidence": round(self.intent_confidence, 2),
            "slots": self.slots,
            "entities": [e.to_dict() for e in self.entities],
            "urgency_score": round(self.urgency_score, 2),
            "sentiment": self.sentiment,
            "is_ambiguous": self.is_ambiguous,
            "ambiguity_reason": self.ambiguity_reason,
            "extracted_keywords": self.extracted_keywords,
        }


class NLUPipeline:
    def __init__(self):
        # Known semantic dictionaries for entity mapping
        self.known_devices = {"computer", "server", "workstation", "terminal", "database", "sensor", "camera", "lidar", "motor"}
        self.known_locations = {"room", "sector", "zone", "dock", "charging station", "laboratory", "portal", "area"}
        self.emergency_keywords = {"stop", "halt", "emergency", "abort", "freeze", "kill", "brake", "shut down"}

    def understand(self, text: str) -> NLUUnderstandingResult:
        """
        Executes complete Natural Language Understanding analysis on input directive.
        """
        if not text:
            return NLUUnderstandingResult(
                raw_text="",
                intent=IntentType.STATUS_CHECK,
                intent_confidence=0.5,
                slots={},
                entities=[],
                urgency_score=0.0,
                sentiment="NEUTRAL",
                is_ambiguous=True,
                ambiguity_reason="Empty input text",
            )

        t_lower = text.lower().strip()
        tokens = nlp_pipeline.tokenize(text, remove_stopwords=True)
        keywords = [k for k, _ in nlp_pipeline.extract_keywords(text, top_k=6)]

        # 1. Detect Emergency
        if any(k in t_lower for k in self.emergency_keywords):
            return NLUUnderstandingResult(
                raw_text=text,
                intent=IntentType.EMERGENCY_COMMAND,
                intent_confidence=0.99,
                slots={"action": "EMERGENCY_BRAKE"},
                entities=[ExtractedEntity("Motion System", "DEVICE", 0.99, text)],
                urgency_score=1.0,
                sentiment="NEGATIVE",
                is_ambiguous=False,
                extracted_keywords=keywords,
            )

        # 2. Detect Feedback
        if any(k in t_lower for k in ["no,", "wrong", "incorrect", "instead", "you should have", "not that"]):
            return NLUUnderstandingResult(
                raw_text=text,
                intent=IntentType.FEEDBACK_CORRECTION,
                intent_confidence=0.95,
                slots={"feedback_rule": text},
                entities=[],
                urgency_score=0.7,
                sentiment="NEGATIVE",
                is_ambiguous=False,
                extracted_keywords=keywords,
            )
        elif any(k in t_lower for k in ["good job", "great", "excellent", "perfect", "well done"]):
            return NLUUnderstandingResult(
                raw_text=text,
                intent=IntentType.FEEDBACK_POSITIVE,
                intent_confidence=0.96,
                slots={},
                entities=[],
                urgency_score=0.1,
                sentiment="POSITIVE",
                is_ambiguous=False,
                extracted_keywords=keywords,
            )

        # 3. Detect Navigation
        if any(k in t_lower for k in ["navigate", "move", "dock", "charge", "patrol", "return to"]):
            target_loc = "Charging Dock" if "dock" in t_lower or "charge" in t_lower else "Designated Zone"
            return NLUUnderstandingResult(
                raw_text=text,
                intent=IntentType.NAVIGATION_REQUEST,
                intent_confidence=0.94,
                slots={"target_location": target_loc},
                entities=[ExtractedEntity(target_loc, "LOCATION", 0.95, target_loc)],
                urgency_score=0.6 if "charge" in t_lower else 0.4,
                sentiment="NEUTRAL",
                is_ambiguous=False,
                extracted_keywords=keywords,
            )

        # 4. Detect Diagnostics / Failures
        if any(k in t_lower for k in ["diagnose", "failure", "error", "troubleshoot", "reason for", "bug", "crash", "inspect log"]):
            return NLUUnderstandingResult(
                raw_text=text,
                intent=IntentType.DIAGNOSTIC_QUERY,
                intent_confidence=0.93,
                slots={"scope": "system_failure", "target": "logs_and_telemetry"},
                entities=[ExtractedEntity("System Telemetry", "METRIC", 0.92, text)],
                urgency_score=0.85,
                sentiment="NEGATIVE",
                is_ambiguous=False,
                extracted_keywords=keywords,
            )

        # 5. Detect Environment Probing
        if any(k in t_lower for k in ["scan", "inspect", "environment", "room", "surveillance", "detect object", "map"]):
            return NLUUnderstandingResult(
                raw_text=text,
                intent=IntentType.ENVIRONMENT_PROBE,
                intent_confidence=0.92,
                slots={"mode": "360_lidar_camera_sweep"},
                entities=[ExtractedEntity("Physical Environment", "LOCATION", 0.95, text)],
                urgency_score=0.4,
                sentiment="NEUTRAL",
                is_ambiguous=False,
                extracted_keywords=keywords,
            )

        # 6. Detect Status Check
        if any(k in t_lower for k in ["status", "battery", "what is happening", "how are you", "telemetry"]):
            return NLUUnderstandingResult(
                raw_text=text,
                intent=IntentType.STATUS_CHECK,
                intent_confidence=0.91,
                slots={"target": "internal_telemetry"},
                entities=[],
                urgency_score=0.2,
                sentiment="NEUTRAL",
                is_ambiguous=False,
                extracted_keywords=keywords,
            )

        # 7. Default Goal Directive
        is_too_short = len(tokens) <= 1
        return NLUUnderstandingResult(
            raw_text=text,
            intent=IntentType.GOAL_DIRECTIVE,
            intent_confidence=0.88 if not is_too_short else 0.50,
            slots={"action": text},
            entities=self._extract_entities(text),
            urgency_score=0.5,
            sentiment="NEUTRAL",
            is_ambiguous=is_too_short,
            ambiguity_reason="Command is very brief and may lack specific target parameters" if is_too_short else None,
            extracted_keywords=keywords,
        )

    def _extract_entities(self, text: str) -> List[ExtractedEntity]:
        entities: List[ExtractedEntity] = []
        t_lower = text.lower()

        for dev in self.known_devices:
            if dev in t_lower:
                entities.append(ExtractedEntity(dev.title(), "DEVICE", 0.90, dev))

        for loc in self.known_locations:
            if loc in t_lower:
                entities.append(ExtractedEntity(loc.title(), "LOCATION", 0.90, loc))

        return entities


nlu_pipeline = NLUPipeline()
