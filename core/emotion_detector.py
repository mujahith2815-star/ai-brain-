"""
Emotional Subtext Analyzer for P.H.A.S.S.
Calculates Frustration and Excitement scores using a weighted lexicon.
Applies human-empathy conversational prefixes:
- Frustration > 70%: "I sense your frustration, sir. "
- Excitement > 70%: "Excellent! I'm glad it's working. " (with exclamation mark)
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Dict, Any, Tuple


@dataclass
class EmotionResult:
    frustration: float  # 0.0 to 1.0
    excitement: float   # 0.0 to 1.0
    primary_emotion: str  # "frustrated", "excited", "neutral"

    @property
    def is_frustrated(self) -> bool:
        return self.frustration > 0.70

    @property
    def is_excited(self) -> bool:
        return self.excitement > 0.70


class EmotionDetector:
    """Lexicon-based sentiment & affective tone analyzer."""

    FRUSTRATION_STRONG = [
        "damn", "dammit", "stupid", "not working", "broken", "hate", "fail",
        "failed", "failing", "error", "buggy", "useless", "why won't", "why wont",
        "hell no", "garbage", "pissed", "frustrated", "annoying", "terrible",
        "crash", "crashed", "awful"
    ]

    FRUSTRATION_MILD = [
        "ugh", "crap", "slow", "stuck", "lost", "confused", "bad", "wrong",
        "mess", "glitch", "can't figure", "cant figure"
    ]

    EXCITEMENT_STRONG = [
        "wow", "great", "beautiful", "it works", "it worked", "working",
        "awesome", "finally", "perfect", "nailed it", "amazing", "fantastic",
        "brilliant", "hell yeah", "love it", "genius", "superb", "incredible",
        "outstanding", "lit up", "blinking"
    ]

    EXCITEMENT_MILD = [
        "good", "cool", "nice", "yay", "sweet", "glad", "happy", "success",
        "progress", "neat"
    ]

    def analyze(self, text: str) -> EmotionResult:
        """
        Analyzes text and returns normalized frustration and excitement scores (0.0 - 1.0).
        """
        clean = text.lower().strip()
        if not clean:
            return EmotionResult(0.0, 0.0, "neutral")

        # Check for punctuation markers
        exclamation_count = clean.count("!")
        question_count = clean.count("?")

        # 1. Frustration scoring
        frust_score = 0.0
        for phrase in self.FRUSTRATION_STRONG:
            if phrase in clean:
                frust_score += 0.45
        for phrase in self.FRUSTRATION_MILD:
            if re.search(r"\b" + re.escape(phrase) + r"\b", clean):
                frust_score += 0.25

        # Punctuation amplifies emotion
        if "?" in clean and "!" in clean and frust_score > 0:
            frust_score += 0.15
        elif exclamation_count >= 2 and frust_score > 0:
            frust_score += 0.15

        # Cap at 1.0
        frust_score = min(1.0, round(frust_score, 2))

        # 2. Excitement scoring
        excite_score = 0.0
        for phrase in self.EXCITEMENT_STRONG:
            if phrase in clean:
                excite_score += 0.45
        for phrase in self.EXCITEMENT_MILD:
            if re.search(r"\b" + re.escape(phrase) + r"\b", clean):
                excite_score += 0.25

        if exclamation_count >= 1 and excite_score > 0:
            excite_score += 0.15 * min(exclamation_count, 3)

        # Cap at 1.0
        excite_score = min(1.0, round(excite_score, 2))

        # Primary emotion classification
        if frust_score > 0.70 and frust_score >= excite_score:
            primary = "frustrated"
        elif excite_score > 0.70:
            primary = "excited"
        else:
            primary = "neutral"

        return EmotionResult(frust_score, excite_score, primary)

    def apply_emotional_subtext(self, user_query: str, base_response: str) -> str:
        """
        Applies conversational prefix rules based on detected emotional subtext:
        - If Frustration > 70%: Prepend "I sense your frustration, sir."
        - If Excitement > 70%: Prepend "Excellent! I'm glad it's working." and add exclamation mark.
        """
        emotion = self.analyze(user_query)
        result = base_response.strip()

        if emotion.is_frustrated:
            prefix = "I sense your frustration, sir."
            if not result.startswith(prefix):
                result = f"{prefix} {result}"
        elif emotion.is_excited:
            prefix = "Excellent! I'm glad it's working."
            if not result.startswith(prefix):
                result = f"{prefix} {result}"
            # Ensure an enthusiastic exclamation mark
            if not result.endswith("!"):
                result = result.rstrip(".") + "!"

        return result


# Global singleton
emotion_detector = EmotionDetector()
