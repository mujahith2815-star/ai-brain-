"""
Episodic Memory for P.H.A.S.S Sphere.
Stores chronological records of past goals, task trajectories, outcomes, and contextual episodes.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
import logging
from .base import MemoryRecord, MemoryTier

logger = logging.getLogger("phass.memory.episodic")


@dataclass
class Episode:
    id: str = field(default_factory=lambda: f"EP-{str(uuid.uuid4())[:8].upper()}")
    goal_id: str = ""
    goal_title: str = ""
    start_time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    end_time: Optional[str] = None
    success: bool = True
    actions_taken: List[Dict[str, Any]] = field(default_factory=list)
    observations_made: List[Dict[str, Any]] = field(default_factory=list)
    outcome_summary: str = ""
    lessons_learned: List[str] = field(default_factory=list)
    user_feedback: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal_id": self.goal_id,
            "goal_title": self.goal_title,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "success": self.success,
            "actions_taken": self.actions_taken,
            "observations_made": self.observations_made,
            "outcome_summary": self.outcome_summary,
            "lessons_learned": self.lessons_learned,
            "user_feedback": self.user_feedback,
        }


class EpisodicMemory:
    def __init__(self, capacity: int = 200):
        self.capacity = capacity
        self.episodes: List[Episode] = []
        self._seed_initial_episodes()

    def _seed_initial_episodes(self) -> None:
        self.record_episode(
            Episode(
                goal_id="GOAL-BOOT-01",
                goal_title="System Cold Boot and Self-Diagnostics",
                success=True,
                actions_taken=[
                    {"tool": "system_diagnostics", "result": "All internal subsystems nominal"},
                    {"tool": "sensor_probe", "result": "LiDAR, IMU, Camera calibrated"},
                ],
                outcome_summary="System initialization completed without errors.",
                lessons_learned=["Calibrate IMU before initiating high-speed movement."],
            )
        )

    def record_episode(self, episode: Episode) -> None:
        if not episode.end_time:
            episode.end_time = datetime.now(timezone.utc).isoformat()
        self.episodes.append(episode)
        if len(self.episodes) > self.capacity:
            self.episodes.pop(0)

    def get_recent_episodes(self, limit: int = 10) -> List[Episode]:
        return self.episodes[-limit:]

    def search_episodes_by_keyword(self, keyword: str) -> List[Episode]:
        k_lower = keyword.lower()
        results = []
        for ep in self.episodes:
            if (
                k_lower in ep.goal_title.lower()
                or k_lower in ep.outcome_summary.lower()
                or any(k_lower in l.lower() for l in ep.lessons_learned)
            ):
                results.append(ep)
        return results
