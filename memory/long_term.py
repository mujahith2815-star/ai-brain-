"""
Long-Term and Knowledge Memory for P.H.A.S.S Sphere.
Stores durable system facts, user preferences, environment constraints, and learned truths.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import logging
from .base import MemoryRecord, MemoryTier

logger = logging.getLogger("phass.memory.long_term")


class LongTermMemory:
    """
    Stores durable semantic facts and long-term knowledge with indexing by tags and keywords.
    """

    def __init__(self):
        self.records: Dict[str, MemoryRecord] = {}
        self._seed_default_knowledge()

    def _seed_default_knowledge(self) -> None:
        self.store(
            content="P.H.A.S.S Sphere is an omni-directional non-humanoid autonomous robot.",
            tags=["robot_identity", "architecture", "kinematics"],
            importance=1.0,
            metadata={"source": "system_bootstrap"},
        )
        self.store(
            content="Critical power threshold is 15%. When battery falls below 15%, return to charging dock immediately.",
            tags=["safety", "battery", "policy"],
            importance=1.0,
            metadata={"source": "system_bootstrap"},
        )
        self.store(
            content="High-risk digital actions (system-level executions, filesystem deletions) require explicit user confirmation.",
            tags=["safety", "security", "permissions"],
            importance=1.0,
            metadata={"source": "security_policy"},
        )
        self.store(
            content="Magnetic Fast-Charge Dock is located at spatial coordinates (0.0, 4.5, 0.0).",
            tags=["location", "charging", "spatial"],
            importance=0.95,
            metadata={"source": "facility_map"},
        )

    def store(
        self,
        content: str,
        tags: Optional[List[str]] = None,
        importance: float = 0.8,
        metadata: Optional[Dict[str, Any]] = None,
        tier: MemoryTier = MemoryTier.LONG_TERM,
    ) -> MemoryRecord:
        rec = MemoryRecord(
            content=content,
            tier=tier,
            tags=tags or ["knowledge"],
            importance=importance,
            metadata=metadata or {},
        )
        self.records[rec.id] = rec
        return rec

    def search_by_tag(self, tag: str) -> List[MemoryRecord]:
        t_lower = tag.lower()
        return [r for r in self.records.values() if any(t_lower in t.lower() for t in r.tags)]

    def get_all(self) -> List[MemoryRecord]:
        return list(self.records.values())

    def update_record(self, record_id: str, new_content: str, importance: Optional[float] = None) -> bool:
        if record_id in self.records:
            rec = self.records[record_id]
            rec.content = new_content
            if importance is not None:
                rec.importance = importance
            rec.touch()
            return True
        return False
