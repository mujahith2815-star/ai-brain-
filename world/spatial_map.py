"""
Spatial Map representation for P.H.A.S.S Sphere.
Maintains 2D/3D topological layout, navigable areas, and proximity lookups.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import math
from .entities import WorldEntity, Vector3D


@dataclass
class SpatialMap:
    room_name: str = "Central Laboratory Zone"
    bounds_min: Vector3D = field(default_factory=lambda: Vector3D(-10.0, -10.0, 0.0))
    bounds_max: Vector3D = field(default_factory=lambda: Vector3D(10.0, 10.0, 4.0))
    landmarks: Dict[str, Vector3D] = field(default_factory=dict)

    def __post_init__(self):
        if not self.landmarks:
            self.landmarks = {
                "Charging Dock": Vector3D(0.0, 4.5, 0.0),
                "Main Workstation": Vector3D(3.0, 2.0, 0.0),
                "Data Terminal": Vector3D(-3.5, 1.5, 0.0),
                "Entrance Portal": Vector3D(0.0, -4.8, 0.0),
            }

    def distance_between(self, pos1: Vector3D, pos2: Vector3D) -> float:
        dx = pos1.x - pos2.x
        dy = pos1.y - pos2.y
        dz = pos1.z - pos2.z
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def find_nearest_landmark(self, position: Vector3D) -> Tuple[str, float]:
        nearest_name = "Unknown"
        min_dist = float("inf")
        for name, pos in self.landmarks.items():
            dist = self.distance_between(position, pos)
            if dist < min_dist:
                min_dist = dist
                nearest_name = name
        return nearest_name, round(min_dist, 2)

    def is_within_bounds(self, position: Vector3D) -> bool:
        return (
            self.bounds_min.x <= position.x <= self.bounds_max.x
            and self.bounds_min.y <= position.y <= self.bounds_max.y
            and self.bounds_min.z <= position.z <= self.bounds_max.z
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "room_name": self.room_name,
            "bounds_min": self.bounds_min.to_dict(),
            "bounds_max": self.bounds_max.to_dict(),
            "landmarks": {k: v.to_dict() for k, v in self.landmarks.items()},
        }
