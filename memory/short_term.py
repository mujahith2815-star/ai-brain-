"""
Short-Term and Working Memory modules for P.H.A.S.S Sphere.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import logging
from .base import MemoryRecord, MemoryTier

logger = logging.getLogger("phass.memory.short_term")


class ShortTermMemory:
    """
    Stores immediate conversation turns, user inputs, and sensory burst traces.
    Ring-buffered capacity with automatic aging.
    """

    def __init__(self, capacity: int = 50):
        self.capacity = capacity
        self.records: List[MemoryRecord] = []

    def store(self, content: str, tags: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None) -> MemoryRecord:
        record = MemoryRecord(
            content=content,
            tier=MemoryTier.SHORT_TERM,
            tags=tags or ["dialogue", "immediate"],
            metadata=metadata or {},
            importance=0.8,
        )
        self.records.append(record)
        if len(self.records) > self.capacity:
            self.records.pop(0)
        return record

    def get_recent(self, limit: int = 10) -> List[MemoryRecord]:
        return self.records[-limit:]

    def clear(self) -> None:
        self.records.clear()


class WorkingMemory:
    """
    Stores dynamic reasoning state, active hypotheses, intermediate tool results,
    and transient variables required for the current goal lifecycle.
    """

    def __init__(self, capacity: int = 25):
        self.capacity = capacity
        self.scratchpad: Dict[str, Any] = {}
        self.active_hypotheses: List[str] = []
        self.records: List[MemoryRecord] = []

    def set_variable(self, key: str, value: Any) -> None:
        self.scratchpad[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        return self.scratchpad.get(key, default)

    def store_hypothesis(self, hypothesis: str) -> None:
        self.active_hypotheses.append(hypothesis)
        rec = MemoryRecord(
            content=hypothesis,
            tier=MemoryTier.WORKING,
            tags=["hypothesis", "active_reasoning"],
        )
        self.records.append(rec)
        if len(self.records) > self.capacity:
            self.records.pop(0)

    def reset_for_new_goal(self) -> None:
        self.scratchpad.clear()
        self.active_hypotheses.clear()
        self.records.clear()
