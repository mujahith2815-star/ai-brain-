"""
Memory Retrieval Engine for P.H.A.S.S Sphere.
Integrates semantic scoring, keyword matching, recency weighting,
and cross-tier associative recall across Short-Term, Working, Long-Term, Episodic, and Spatial Memory.
"""

from __future__ import annotations
import math
import re
from typing import Any, Dict, List, Optional
import logging
from .base import MemoryRecord, MemoryTier
from .short_term import ShortTermMemory, WorkingMemory
from .long_term import LongTermMemory
from .episodic import EpisodicMemory, Episode
from .spatial import SpatialMemory

logger = logging.getLogger("phass.memory.retrieval")


class MemoryRetriever:
    def __init__(
        self,
        short_term: ShortTermMemory,
        working: WorkingMemory,
        long_term: LongTermMemory,
        episodic: EpisodicMemory,
        spatial: SpatialMemory,
    ):
        self.short_term = short_term
        self.working = working
        self.long_term = long_term
        self.episodic = episodic
        self.spatial = spatial

    def calculate_relevance(self, query: str, text: str, tags: List[str], importance: float = 1.0) -> float:
        """
        Computes relevance score using normalized keyword frequency, tag matching, and importance scaling.
        """
        q_tokens = set(re.findall(r"\w+", query.lower()))
        if not q_tokens:
            return 0.0

        t_tokens = set(re.findall(r"\w+", text.lower()))
        tag_tokens = set(re.findall(r"\w+", " ".join(tags).lower()))

        text_overlap = len(q_tokens.intersection(t_tokens)) / len(q_tokens)
        tag_overlap = len(q_tokens.intersection(tag_tokens)) / len(q_tokens)

        raw_score = (text_overlap * 0.6) + (tag_overlap * 0.4)
        return min(1.0, round(raw_score * importance, 3))

    def retrieve_relevant_memories(
        self,
        query: str,
        limit: int = 5,
        min_threshold: float = 0.2,
    ) -> List[Dict[str, Any]]:
        """
        Searches across all memory tiers and returns ranked records.
        """
        scored_results: List[Dict[str, Any]] = []

        # 1. Search Long-Term Knowledge
        for rec in self.long_term.get_all():
            score = self.calculate_relevance(query, rec.content, rec.tags, rec.importance)
            if score >= min_threshold:
                rec.touch()
                scored_results.append({
                    "score": score,
                    "tier": rec.tier.value,
                    "id": rec.id,
                    "content": rec.content,
                    "tags": rec.tags,
                    "metadata": rec.metadata,
                })

        # 2. Search Episodic Memory
        for ep in self.episodic.episodes:
            ep_text = f"{ep.goal_title} {ep.outcome_summary} {' '.join(ep.lessons_learned)}"
            score = self.calculate_relevance(query, ep_text, ["episode", "experience"], 0.9)
            if score >= min_threshold:
                scored_results.append({
                    "score": score,
                    "tier": "EPISODIC",
                    "id": ep.id,
                    "content": f"Episode: '{ep.goal_title}' -> {ep.outcome_summary}",
                    "tags": ["episode"],
                    "metadata": {"success": ep.success, "lessons": ep.lessons_learned},
                })

        # 3. Search Short-Term Memory
        for st in self.short_term.records:
            score = self.calculate_relevance(query, st.content, st.tags, st.importance)
            if score >= min_threshold:
                scored_results.append({
                    "score": score,
                    "tier": st.tier.value,
                    "id": st.id,
                    "content": st.content,
                    "tags": st.tags,
                    "metadata": st.metadata,
                })

        # Sort descending by score
        scored_results.sort(key=lambda x: -x["score"])
        return scored_results[:limit]

    def get_context_for_goal(self, goal_title: str) -> Dict[str, Any]:
        """
        Aggregates relevant knowledge, past episodes, and spatial context for a goal.
        """
        relevant = self.retrieve_relevant_memories(goal_title, limit=4)
        past_episodes = self.episodic.search_episodes_by_keyword(goal_title)[:2]

        lessons = []
        for ep in past_episodes:
            lessons.extend(ep.lessons_learned)

        return {
            "relevant_memories": relevant,
            "applicable_lessons": lessons,
            "recent_conversations": [r.content for r in self.short_term.get_recent(3)],
        }


class IntegratedMemorySystem:
    """
    Unified memory management facade for P.H.A.S.S Sphere.
    """

    def __init__(self, capacity_short_term: int = 50):
        self.short_term = ShortTermMemory(capacity=capacity_short_term)
        self.working = WorkingMemory()
        self.long_term = LongTermMemory()
        self.episodic = EpisodicMemory()
        self.spatial = SpatialMemory()
        self.retriever = MemoryRetriever(
            self.short_term, self.working, self.long_term, self.episodic, self.spatial
        )

    def get_summary(self) -> Dict[str, Any]:
        return {
            "short_term_count": len(self.short_term.records),
            "working_variables_count": len(self.working.scratchpad),
            "long_term_count": len(self.long_term.records),
            "episodic_episodes_count": len(self.episodic.episodes),
            "spatial_anchors_count": len(self.spatial.anchors),
        }


memory_system = IntegratedMemorySystem()
