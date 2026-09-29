"""
Simulated Physical Environment for P.H.A.S.S Sphere.
Simulates a high-tech robotic laboratory arena with interactive obstacles,
workstations, portals, and charging bays.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import random
from world.entities import WorldEntity, EntityType, Vector3D


@dataclass
class ArenaObstacle:
    id: str
    name: str
    position: Vector3D
    radius_m: float
    height_m: float
    color: str = "#4A90E2"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "position": self.position.to_dict(),
            "radius_m": self.radius_m,
            "height_m": self.height_m,
            "color": self.color,
        }


class SimulationEnvironment:
    def __init__(self):
        self.arena_width_m = 10.0
        self.arena_length_m = 10.0
        self.obstacles: List[ArenaObstacle] = []
        self._init_arena()

    def _init_arena(self) -> None:
        self.obstacles = [
            ArenaObstacle("OBS-01", "Diagnostics Console", Vector3D(3.0, 2.0, 0.0), 0.7, 1.2, "#00E5FF"),
            ArenaObstacle("OBS-02", "Server Rack Tower", Vector3D(-3.5, 1.5, 0.0), 0.6, 2.0, "#7C4DFF"),
            ArenaObstacle("OBS-03", "Charging Dock Pod", Vector3D(0.0, 4.5, 0.0), 0.8, 0.3, "#00E676"),
            ArenaObstacle("OBS-04", "Structural Pillar A", Vector3D(-2.0, -2.5, 0.0), 0.5, 3.0, "#78909C"),
            ArenaObstacle("OBS-05", "Structural Pillar B", Vector3D(2.5, -2.5, 0.0), 0.5, 3.0, "#78909C"),
        ]

    def add_random_obstacle(self) -> ArenaObstacle:
        idx = len(self.obstacles) + 1
        obs = ArenaObstacle(
            id=f"OBS-{idx:02d}",
            name=f"Dynamic Hazard {idx}",
            position=Vector3D(
                random.uniform(-4.0, 4.0),
                random.uniform(-4.0, 4.0),
                0.0
            ),
            radius_m=random.uniform(0.3, 0.6),
            height_m=random.uniform(0.5, 1.5),
            color="#FF5252",
        )
        self.obstacles.append(obs)
        return obs

    def get_arena_state(self) -> Dict[str, Any]:
        return {
            "arena_dimensions": {"width_m": self.arena_width_m, "length_m": self.arena_length_m},
            "obstacles": [o.to_dict() for o in self.obstacles],
        }


simulated_env = SimulationEnvironment()
