"""
Spatial Memory for P.H.A.S.S Sphere.
Maintains persistent spatial anchors, historical object positions, and visited zones.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import math
import logging
from .base import MemoryRecord, MemoryTier

logger = logging.getLogger("phass.memory.spatial")


@dataclass
class SpatialAnchor:
    name: str
    category: str
    coordinates: Dict[str, float]
    confidence: float = 0.95
    last_confirmed: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "coordinates": self.coordinates,
            "confidence": self.confidence,
            "last_confirmed": self.last_confirmed,
        }


class SpatialMemory:
    def __init__(self):
        self.anchors: Dict[str, SpatialAnchor] = {}
        self._seed_default_anchors()

    def _seed_default_anchors(self) -> None:
        self.remember_anchor("DockingStation_Alpha", "dock", {"x": 0.0, "y": 4.5, "z": 0.0})
        self.remember_anchor("Workstation_Primary", "workstation", {"x": 3.0, "y": 2.0, "z": 0.0})
        self.remember_anchor("ServerRack_Storage", "server", {"x": -3.5, "y": 1.5, "z": 0.0})

    def remember_anchor(self, name: str, category: str, coords: Dict[str, float], confidence: float = 0.95) -> SpatialAnchor:
        anchor = SpatialAnchor(
            name=name,
            category=category,
            coordinates=coords,
            confidence=confidence,
            last_confirmed=datetime.now(timezone.utc).isoformat(),
        )
        self.anchors[name] = anchor
        return anchor

    def find_nearest(self, current_pos: Dict[str, float]) -> Optional[SpatialAnchor]:
        if not self.anchors:
            return None
        cx, cy = current_pos.get("x", 0.0), current_pos.get("y", 0.0)
        nearest = None
        min_dist = float("inf")
        for anchor in self.anchors.values():
            ax, ay = anchor.coordinates.get("x", 0.0), anchor.coordinates.get("y", 0.0)
            dist = math.hypot(ax - cx, ay - cy)
            if dist < min_dist:
                min_dist = dist
                nearest = anchor
        return nearest

    def get_all(self) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self.anchors.values()]
