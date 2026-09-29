"""
Natural Language Generation (NLG) Subsystem for P.H.A.S.S Sphere.
Converts structured robot states, telemetry, goals, plans, and evaluation metrics
into natural, fluent human-readable verbal and text communications.
"""

from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger("phass.nlp.nlg")


class NLGPersona(str, Enum):
    ROBOT_VOICE = "ROBOT_VOICE"           # Direct, confident, autonomous physical AI presence
    OPERATOR_CONCISE = "OPERATOR_CONCISE" # Short telemetry highlights for fast HUD scanning
    TECHNICAL_DEEP = "TECHNICAL_DEEP"     # Detailed architectural and failure breakdown


class NLGGenerator:
    def __init__(self, default_persona: NLGPersona = NLGPersona.ROBOT_VOICE):
        self.default_persona = default_persona

    def generate_acknowledgement(self, goal_title: str, subtasks_count: int, persona: Optional[NLGPersona] = None) -> str:
        p = persona or self.default_persona
        if p == NLGPersona.ROBOT_VOICE:
            return f"Directive received: '{goal_title}'. I have structured this into {subtasks_count} coordinated subtasks and initiated autonomous execution."
        elif p == NLGPersona.OPERATOR_CONCISE:
            return f"Goal: '{goal_title}' [Queued {subtasks_count} subtasks]."
        else:
            return f"Parsed directive '{goal_title}'. Formulated execution plan with {subtasks_count} dependency-chained steps across cognitive core."

    def generate_completion_report(
        self,
        goal_title: str,
        success: bool,
        subtasks_executed: int,
        lessons_learned: Optional[List[str]] = None,
        persona: Optional[NLGPersona] = None,
    ) -> str:
        p = persona or self.default_persona
        status_text = "successfully completed" if success else "failed to achieve completion"

        if p == NLGPersona.ROBOT_VOICE:
            msg = f"Mission report: '{goal_title}' has been {status_text} across {subtasks_executed} operations."
            if lessons_learned:
                msg += f" I have consolidated {len(lessons_learned)} new lesson(s) into my long-term memory."
            return msg
        elif p == NLGPersona.OPERATOR_CONCISE:
            return f"Goal '{goal_title}' -> {'OK' if success else 'FAILED'} ({subtasks_executed} steps)."
        else:
            lessons_str = "; ".join(lessons_learned) if lessons_learned else "None"
            return (
                f"Detailed Execution Summary:\n"
                f"• Target Goal: {goal_title}\n"
                f"• Status: {'SUCCESS' if success else 'FAILURE'}\n"
                f"• Total Subtasks: {subtasks_executed}\n"
                f"• Extracted Policy Lessons: {lessons_str}"
            )

    def generate_telemetry_narrative(self, robot_state: Dict[str, Any], env_state: Dict[str, Any]) -> str:
        """
        Converts live numbers into a coherent spoken situational update.
        """
        battery = robot_state.get("battery_percentage", 100.0)
        temp = robot_state.get("internal_temp_c", 30.0)
        amb_temp = env_state.get("ambient_temperature_c", 22.0)
        chassis = robot_state.get("chassis_type", "spherical_omni")

        status_adjective = "nominal" if battery > 30 and temp < 50 else "requiring attention"

        return (
            f"P.H.A.S.S Sphere chassis ({chassis}) is operating at {battery}% battery power. "
            f"Core temperature is {temp}°C in an ambient environment of {amb_temp}°C. "
            f"Sensory streams and internal balance are {status_adjective}."
        )

    def generate_feedback_acknowledgement(self, feedback_type: str, lesson: Optional[str] = None) -> str:
        if feedback_type == "CORRECTION":
            return f"Correction registered. I have prioritized the rule: '{lesson}' and adapted future task planning."
        elif feedback_type == "POSITIVE":
            return "Thank you. Positive reinforcement logged; reinforcing current strategy weights."
        else:
            return f"New situational information ingested into knowledge memory: '{lesson}'."


nlg_generator = NLGGenerator()
