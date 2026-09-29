"""
Reinforcement Experience Replay & Q-Policy Learning for P.H.A.S.S Sphere.
Maintains state-action transition replay buffers and updates strategy weights based on rewards.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
import random
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ExperienceTransition:
    state_desc: str
    action_name: str
    reward: float  # +1.0 for goal success, -1.0 for failure, -0.1 for step cost
    next_state_desc: str
    done: bool
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_desc": self.state_desc,
            "action_name": self.action_name,
            "reward": round(self.reward, 2),
            "next_state_desc": self.next_state_desc,
            "done": self.done,
            "timestamp": self.timestamp,
        }


class ExperienceReplayBuffer:
    def __init__(self, capacity: int = 500):
        self.capacity = capacity
        self.buffer: List[ExperienceTransition] = []
        self.q_table: Dict[Tuple[str, str], float] = {}
        self.alpha = 0.2  # Learning rate
        self.gamma = 0.9  # Discount factor

    def store_transition(self, state: str, action: str, reward: float, next_state: str, done: bool) -> None:
        trans = ExperienceTransition(state, action, reward, next_state, done)
        self.buffer.append(trans)
        if len(self.buffer) > self.capacity:
            self.buffer.pop(0)

        # Update Q-value
        key = (state, action)
        current_q = self.q_table.get(key, 0.0)
        # Find max next Q
        max_next_q = max([self.q_table.get((next_state, a), 0.0) for a in ["system_diagnostics", "sensor_probe", "vision_scan", "robot_move", "generate_report"]], default=0.0)
        new_q = current_q + self.alpha * (reward + self.gamma * max_next_q - current_q)
        self.q_table[key] = round(new_q, 3)

    def sample_batch(self, batch_size: int = 16) -> List[ExperienceTransition]:
        if len(self.buffer) <= batch_size:
            return list(self.buffer)
        return random.sample(self.buffer, batch_size)

    def get_best_action_for_state(self, state: str, candidate_actions: List[str]) -> Tuple[str, float]:
        best_act = candidate_actions[0] if candidate_actions else "system_diagnostics"
        best_q = -float("inf")
        for act in candidate_actions:
            q = self.q_table.get((state, act), 0.0)
            if q > best_q:
                best_q = q
                best_act = act
        return best_act, round(best_q, 3)


replay_buffer = ExperienceReplayBuffer()
