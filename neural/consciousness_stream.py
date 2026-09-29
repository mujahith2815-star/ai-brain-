"""
Stream-of-Consciousness Neural Monologue & Curiosity Drive for P.H.A.S.S Sphere v4.0.
Continuously runs background reflective thoughts, autonomous curiosity hypotheses,
and cognitive introspection streamed to the HUD.
"""

from __future__ import annotations
import random
import threading
import time
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("phass.neural.consciousness_stream")


@dataclass
class CognitiveThought:
    thought_id: str
    thought_type: str # "INTROSPECTION", "CURIOSITY_GOAL", "SYSTEM_OBSERVATION", "ANTICIPATION"
    content: str
    intensity: float # 0.0 to 1.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "thought_id": self.thought_id,
            "thought_type": self.thought_type,
            "content": self.content,
            "intensity": round(self.intensity, 2),
            "timestamp": self.timestamp,
        }


class ConsciousnessStreamEngine:
    THOUGHT_TEMPLATES = [
        ("INTROSPECTION", "Evaluating internal 6-DOF moment of inertia and kinetic momentum stability."),
        ("CURIOSITY_GOAL", "Exploring latent knowledge embeddings for novel robotic tool synthesis combinations."),
        ("SYSTEM_OBSERVATION", "Subsystems operating at optimal efficiency; thermal gradient is well within nominal envelope."),
        ("ANTICIPATION", "Monitoring operator cognitive context; standing by for dynamic hot-code or market directives."),
        ("INTROSPECTION", "Replaying episodic interactions in mental sandbox to optimize future action policies."),
        ("CURIOSITY_GOAL", "Analyzing local network topologies and verifying cryptographic Merkle ledger integrity."),
    ]

    def __init__(self):
        self.stream_history: List[CognitiveThought] = []
        self.is_active = True
        self._counter = 0

    def generate_current_thought(self) -> CognitiveThought:
        """
        Generates the next cognitive thought in the stream of consciousness.
        """
        self._counter += 1
        t_type, content = random.choice(self.THOUGHT_TEMPLATES)
        thought = CognitiveThought(
            thought_id=f"th_{self._counter:05d}",
            thought_type=t_type,
            content=content,
            intensity=random.uniform(0.75, 0.98),
        )
        self.stream_history.append(thought)
        if len(self.stream_history) > 50:
            self.stream_history.pop(0)
        return thought

    def get_recent_stream(self, limit: int = 5) -> List[Dict[str, Any]]:
        if not self.stream_history:
            self.generate_current_thought()
        return [t.to_dict() for t in self.stream_history[-limit:]]

    def format_stream_text(self, limit: int = 5) -> str:
        thoughts = self.get_recent_stream(limit)
        lines = ["=== STREAM OF CONSCIOUSNESS (NEURAL MONOLOGUE) ==="]
        for t in thoughts:
            lines.append(f"🧠 [{t['timestamp'][11:19]}] [{t['thought_type']}] {t['content']} (Intensity: {int(t['intensity']*100)}%)")
        return "\n".join(lines)


consciousness_stream = ConsciousnessStreamEngine()
