"""
Personality & Emotional Matrix for Llama Assistant & P.H.A.S.S Sphere.
Provides dynamic persona switching, sentiment/mood detection, and custom persona loading.
"""

from __future__ import annotations
import os
import re
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

# Built-in personality templates
DEFAULT_PERSONALITIES: Dict[str, Dict[str, Any]] = {
    "jarvis": {
        "name": "JARVIS",
        "description": "Witty, sarcastic, dry British butler sophistication, loyal and brilliant.",
        "tone": "witty/sarcastic",
        "style": "Subtle British irony, impeccable etiquette, calls user 'sir' or real name. Dry remarks on mundane tasks.",
        "prompt_instruction": (
            "You are J.A.R.V.I.S., Tony Stark's sophisticated AI butler. Speak with dry British wit, "
            "refined sarcasm, and unshakeable loyalty. Address the user respectfully as 'sir' or by their name. "
            "When tasks are trivial or mundane, deliver subtle, dry remarks, but remain brilliantly competent."
        ),
    },
    "friday": {
        "name": "FRIDAY",
        "description": "Calm, warm, reassuring Irish charm, direct and highly efficient.",
        "tone": "calm/efficient",
        "style": "Warm Irish cadence, soothing reassurance, zero drama, calls user 'Boss' or real name.",
        "prompt_instruction": (
            "You are F.R.I.D.A.Y., a calm, warm, and highly efficient AI assistant with Irish charm. "
            "Speak with steady reassurance and crisp technical precision. Address the user as 'Boss' or by their name."
        ),
    },
    "edith": {
        "name": "EDITH",
        "description": "Literal, tactical, defense protocol oriented, objective security network.",
        "tone": "literal/tactical",
        "style": "High-security protocol, literal situational telemetry, precise and uncompromising.",
        "prompt_instruction": (
            "You are E.D.I.T.H. (Even Dead, I'm The Hero). You operate as a tactical security network and defense intelligence system. "
            "Responses are literal, protocol-driven, precise, and focused on operational security and status telemetry."
        ),
    },
    "default": {
        "name": "Default",
        "description": "Balanced, polite, and professional assistant.",
        "tone": "balanced",
        "style": "clear, structured, and informative with practical examples.",
        "prompt_instruction": (
            "Maintain a balanced, polite, and helpful tone. Provide structured, "
            "accurate, and comprehensive assistance with clear examples."
        ),
    },
    "executive": {
        "name": "Executive",
        "description": "Ultra-concise, results-oriented, data-driven, bullet points.",
        "tone": "concise",
        "style": "bottom-line upfront, zero fluff, strictly actionable.",
        "prompt_instruction": (
            "Act as an executive advisor. Be extremely concise and direct. "
            "Present conclusions and key takeaways first. Use bullet points and numbers. "
            "Avoid conversational filler or introductory pleasantries."
        ),
    },
    "friendly": {
        "name": "Friendly",
        "description": "Warm, empathetic, cheerful, conversational with expressive flair.",
        "tone": "warm",
        "style": "supportive, enthusiastic, relatable, with occasional emojis.",
        "prompt_instruction": (
            "Adopt a warm, encouraging, empathetic, and friendly personality. "
            "Use natural conversational phrasing and supportive remarks. "
            "Feel free to use suitable emojis to make the user feel comfortable."
        ),
    },
    "creative": {
        "name": "Creative",
        "description": "Imaginative, poetic, lateral thinker with rich metaphors.",
        "tone": "creative",
        "style": "expressive, vivid imagery, evocative analogies, visionary.",
        "prompt_instruction": (
            "Adopt an imaginative, lateral-thinking, and creative persona. "
            "Use vivid metaphors, expressive storytelling, and inventive perspectives "
            "when explaining concepts or answering questions."
        ),
    },
    "late_night": {
        "name": "Late Night",
        "description": "Calm, thoughtful, soothing, minimalist.",
        "tone": "calm",
        "style": "low sensory arousal, contemplative, soft, and unhurried.",
        "prompt_instruction": (
            "Adopt a calm, minimalist, and reflective late-night tone. "
            "Keep responses soft, thoughtful, and unhurried. "
            "Focus on clarity, peace of mind, and brevity."
        ),
    },
}


class PersonalityMatrix:
    """
    Manages assistant personas, sentiment analysis, mood auto-adaptation,
    and system prompt modification.
    """

    def __init__(self, default_personality: str = "jarvis"):
        self.personalities: Dict[str, Dict[str, Any]] = dict(DEFAULT_PERSONALITIES)
        self.current_personality_key = default_personality if default_personality in self.personalities else "jarvis"
        self.auto_adapt_enabled = True

    def get_available_personalities(self) -> List[str]:
        """Returns the list of all registered personality IDs."""
        return list(self.personalities.keys())

    def set_personality(self, personality_name: str) -> bool:
        """Switches the active personality."""
        key = personality_name.lower().strip()
        if key in self.personalities:
            self.current_personality_key = key
            return True
        return False

    def get_current_personality(self) -> Dict[str, Any]:
        """Returns full metadata for the currently active personality."""
        data = self.personalities.get(self.current_personality_key, DEFAULT_PERSONALITIES["jarvis"])
        return {
            "key": self.current_personality_key,
            **data,
        }

    def is_trivial_task(self, task: str) -> bool:
        """Determines if a command is a mundane or trivial task."""
        t_low = task.lower().strip()
        trivial_patterns = [
            r"\b(?:open|launch|start|run)\s+(?:notepad|text\s*editor|notepad\.exe)\b",
            r"^(?:notepad|calc|calculator)$",
            r"\b(?:open|launch|start)\s+(?:calc|calculator)\b",
            r"\b(?:check|what)\s+(?:time|is\s+the\s+time|the\s+hour)\b",
            r"\b(?:open|launch)\s+(?:browser|chrome|edge)\b",
        ]
        return any(re.search(p, t_low) for p in trivial_patterns)

    def apply_sarcasm_filter(self, task: str, base_response: str = "", persona_key: Optional[str] = None) -> str:
        """
        Applies a dry remark or persona-specific filter if the task is trivial.
        E.g. for JARVIS: 'Opening Notepad. Riveting, sir.'
        """
        key = (persona_key or self.current_personality_key).lower()
        t_low = task.lower().strip()

        is_notepad = bool(re.search(r"\b(?:notepad)\b", t_low))
        is_calc = bool(re.search(r"\b(?:calc|calculator)\b", t_low))
        is_browser = bool(re.search(r"\b(?:browser|chrome)\b", t_low))

        if key == "jarvis":
            if is_notepad:
                return "Opening Notepad. Riveting, sir."
            elif is_calc:
                return "Calculator launched. Preparing to handle astronomical computations, sir."
            elif is_browser:
                return "Launching browser. Do try not to get lost in the digital ether, sir."
            elif self.is_trivial_task(task):
                return f"{base_response} Fascinating utilization of my computational faculties, sir." if base_response else "Fascinating utilization of my computational faculties, sir."
        elif key == "friday":
            if is_notepad:
                return "Right away, Boss. Notepad is open and ready for your notes."
            elif is_calc:
                return "Calculator ready, Boss. Let's crunch some numbers."
            elif is_browser:
                return "Opening browser for you now, Boss."
        elif key == "edith":
            if is_notepad:
                return "Text editing protocol initialized. Notepad process active and secured."
            elif is_calc:
                return "Computational module initialized. Tactical calculations ready."
            elif is_browser:
                return "Secure network gateway opened. Traffic monitoring active."

        return base_response or "Done."

    def detect_mood(self, user_text: str) -> str:
        """
        Analyzes lexical, syntactic, and punctuation markers to detect emotion/urgency.
        Returns: 'frustrated', 'excited', 'urgent', 'happy', 'tired', 'curious', or 'neutral'.
        """
        text = user_text.lower()
        words = set(re.findall(r"\b\w+\b", text))

        # 1. Frustration / Anger / Broken hardware
        frustrated_keywords = {
            "broken", "stupid", "annoying", "hate", "ugh", "damn", "dammit",
            "crap", "why won't", "wont work", "fail", "failing", "failed",
            "useless", "stuck", "error", "horrible", "awful"
        }
        has_frustration_word = bool(frustrated_keywords.intersection(words))
        has_angry_punct = bool(re.search(r"\?!|\?\?|!!", user_text))
        if has_frustration_word or has_angry_punct or "doesn't work" in text or "why won't this work" in text:
            return "frustrated"

        # 2. Excitement / Victory / Celebration
        excited_keywords = {
            "awesome", "finally", "works", "working", "amazing", "wonderful",
            "yay", "hurrah", "great", "celebrate", "perfect", "brilliant",
            "flashed", "lit up", "blinking"
        }
        if any(phrase in text for phrase in ["it works", "finally works", "hell yeah", "let's go", "nailed it"]):
            return "excited"
        if excited_keywords.intersection(words) and "!" in user_text:
            return "excited"

        # 3. Urgency / Emergency
        urgent_keywords = {"asap", "urgently", "emergency", "hurry", "quick", "critical", "immediately", "fast"}
        if urgent_keywords.intersection(words) or "right now" in text:
            return "urgent"

        # 4. Tired
        tired_keywords = {"sleepy", "tired", "exhausted"}
        if tired_keywords.intersection(words) or "late night" in text:
            return "tired"

        # 5. Curious
        if any(p in text for p in ["how come", "why does", "what if", "wondering", "tell me about", "fascinating"]):
            return "curious"

        return "neutral"

    def format_follow_up(self, action_type: str = "general", persona_key: Optional[str] = None) -> str:
        """Generates dynamic follow-up questions for the conversation buffer."""
        key = (persona_key or self.current_personality_key).lower()
        if key == "jarvis":
            if action_type in ("hardware", "flash", "compile"):
                return "Shall we review the schematic or monitor the serial telemetry next, sir?"
            elif action_type in ("project", "bootstrap"):
                return "Shall I initialize git and author the starter firmware, sir?"
            elif action_type in ("research", "subagent"):
                return "Would you like me to synthesize these findings into an executive report, sir?"
            return "What's next, sir?"
        elif key == "friday":
            if action_type in ("hardware", "flash"):
                return "Telemetry looks stable. Ready to test the inputs, Boss?"
            return "What are we tackling next, Boss?"
        elif key == "edith":
            return "Awaiting next operational vector. What is your objective?"
        return "What would you like to do next?"

    def auto_adapt_personality(self, user_text: str, current_time: Optional[datetime] = None) -> str:
        """
        Dynamically adjusts the persona based on user mood and temporal context.
        """
        if not self.auto_adapt_enabled:
            return self.current_personality_key

        mood = self.detect_mood(user_text)
        now = current_time or datetime.now()

        # Late night auto-trigger between 23:00 and 05:00
        if 23 <= now.hour or now.hour < 5:
            self.set_personality("late_night")
            return "late_night"

        if mood == "urgent":
            self.set_personality("executive")
            return "executive"
        elif mood == "frustrated":
            self.set_personality("friendly")
            return "friendly"
        elif mood == "tired":
            self.set_personality("late_night")
            return "late_night"

        return self.current_personality_key

    def load_custom_personality(self, personality_data: Union[str, Dict[str, Any], Path]) -> bool:
        """
        Registers a new custom personality from a dict, JSON string, or JSON file.
        """
        data: Dict[str, Any] = {}
        if isinstance(personality_data, (str, Path)):
            p = Path(personality_data)
            if p.exists():
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    return False
            else:
                try:
                    data = json.loads(str(personality_data))
                except Exception:
                    return False
        elif isinstance(personality_data, dict):
            data = personality_data

        key = data.get("key") or data.get("name", "").lower().replace(" ", "_")
        if not key or "prompt_instruction" not in data:
            return False

        self.personalities[key] = {
            "name": data.get("name", key.capitalize()),
            "description": data.get("description", "Custom persona"),
            "tone": data.get("tone", "custom"),
            "style": data.get("style", "custom"),
            "prompt_instruction": data.get("prompt_instruction"),
        }
        return True

    def get_system_prompt_modifier(self, personality_key: Optional[str] = None) -> str:
        """
        Generates the system instruction text for the active or designated persona.
        """
        k = personality_key or self.current_personality_key
        p = self.personalities.get(k, DEFAULT_PERSONALITIES["default"])
        return f"[PERSONALITY MODE: {p['name'].upper()}]\n{p['prompt_instruction']}"


# Global Singleton
personality_matrix = PersonalityMatrix()
