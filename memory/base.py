"""
Base Memory System interfaces and record schemas for P.H.A.S.S Sphere.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class MemoryTier(str, Enum):
    SHORT_TERM = "SHORT_TERM"
    WORKING = "WORKING"
    LONG_TERM = "LONG_TERM"
    EPISODIC = "EPISODIC"
    SPATIAL = "SPATIAL"
    KNOWLEDGE = "KNOWLEDGE"


@dataclass
class MemoryRecord:
    content: str
    tier: MemoryTier
    id: str = field(default_factory=lambda: f"MEM-{str(uuid.uuid4())[:8].upper()}")
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    associations: List[str] = field(default_factory=list)  # Associated Memory IDs
    importance: float = 1.0  # Scale 0.1 to 1.0
    access_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_accessed: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def touch(self) -> None:
        self.access_count += 1
        self.last_accessed = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tier": self.tier.value if isinstance(self.tier, Enum) else str(self.tier),
            "content": self.content,
            "tags": self.tags,
            "metadata": self.metadata,
            "associations": self.associations,
            "importance": round(self.importance, 2),
            "access_count": self.access_count,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
        }
