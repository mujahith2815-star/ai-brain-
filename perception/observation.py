"""
Observation Schema for P.H.A.S.S Sphere.
Normalizes all sensory inputs into a uniform envelope.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
import uuid


class ObservationType(str, Enum):
    VISION = "VISION"
    OBJECT_DETECTION = "OBJECT_DETECTION"
    AUDIO = "AUDIO"
    VOICE_COMMAND = "VOICE_COMMAND"
    LIDAR_SCAN = "LIDAR_SCAN"
    IMU_TELEMETRY = "IMU_TELEMETRY"
    ENVIRONMENT_SENSORS = "ENVIRONMENT_SENSORS"
    TELEMETRY = "TELEMETRY"
    BATTERY = "BATTERY"


@dataclass
class Observation:
    type: ObservationType | str
    source: str
    data: Dict[str, Any]
    id: str = field(default_factory=lambda: f"OBS-{str(uuid.uuid4())[:8]}")
    confidence: float = 0.95
    location: Optional[Dict[str, float]] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value if isinstance(self.type, Enum) else str(self.type),
            "source": self.source,
            "confidence": round(self.confidence, 3),
            "data": self.data,
            "location": self.location or {"x": 0.0, "y": 0.0, "z": 0.0},
            "timestamp": self.timestamp,
        }
