"""
Entities and Objects in the P.H.A.S.S Sphere World Model.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class EntityType(str, Enum):
    OBSTACLE = "OBSTACLE"
    PERSON = "PERSON"
    WORKSTATION = "WORKSTATION"
    CHARGING_DOCK = "CHARGING_DOCK"
    DEVICE = "DEVICE"
    LANDMARK = "LANDMARK"
    UNKNOWN = "UNKNOWN"


@dataclass
class Vector3D:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {"x": round(self.x, 3), "y": round(self.y, 3), "z": round(self.z, 3)}


@dataclass
class WorldEntity:
    id: str = field(default_factory=lambda: f"ENT-{str(uuid.uuid4())[:6].upper()}")
    name: str = "Entity"
    entity_type: EntityType = EntityType.UNKNOWN
    position: Vector3D = field(default_factory=Vector3D)
    dimensions: Vector3D = field(default_factory=lambda: Vector3D(0.5, 0.5, 0.5))
    confidence: float = 0.95
    status: str = "active"
    metadata: Dict[str, Any] = field(default_factory=dict)
    first_observed: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_observed: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def update_observation(self, position: Optional[Vector3D] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        if position:
            self.position = position
        if metadata:
            self.metadata.update(metadata)
        self.last_observed = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type.value if isinstance(self.entity_type, Enum) else str(self.entity_type),
            "position": self.position.to_dict(),
            "dimensions": self.dimensions.to_dict(),
            "confidence": round(self.confidence, 2),
            "status": self.status,
            "metadata": self.metadata,
            "first_observed": self.first_observed,
            "last_observed": self.last_observed,
        }
