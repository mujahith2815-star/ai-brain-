"""
Semantic Knowledge Graph for P.H.A.S.S Sphere.
Maintains structured Entity-Relation-Object triples with confidence weights,
bidirectional indexing, neighborhood lookups, and shortest-path graph search.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
import logging

logger = logging.getLogger("phass.knowledge.graph")


@dataclass
class KnowledgeTriple:
    subject: str
    relation: str
    object: str
    confidence: float = 1.0
    source: str = "bootstrap"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject": self.subject,
            "relation": self.relation,
            "object": self.object,
            "confidence": round(self.confidence, 2),
            "source": self.source,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class SemanticKnowledgeGraph:
    def __init__(self):
        self.triples: List[KnowledgeTriple] = []
        self._subj_index: Dict[str, List[KnowledgeTriple]] = {}
        self._obj_index: Dict[str, List[KnowledgeTriple]] = {}
        self._seed_default_graph()

    def _seed_default_graph(self) -> None:
        defaults = [
            ("PHASS_Sphere", "is_a", "Autonomous_Physical_AI", 1.0),
            ("PHASS_Sphere", "has_chassis", "Spherical_Omni_Platform", 1.0),
            ("PHASS_Sphere", "has_subsystem", "360_Solid_State_LiDAR", 1.0),
            ("PHASS_Sphere", "has_subsystem", "6DOF_IMU_Gyroscope", 1.0),
            ("PHASS_Sphere", "has_subsystem", "MultiSpectral_AI_Camera", 1.0),
            ("PHASS_Sphere", "located_at", "Central_Laboratory_Zone", 0.95),
            ("Charging_Dock_Alpha", "located_at", "Sector_North_4_5", 1.0),
            ("Charging_Dock_Alpha", "supplies_power_to", "PHASS_Sphere", 1.0),
            ("Server_Rack_Storage", "located_at", "Sector_West_3_5", 1.0),
            ("Server_Rack_Storage", "hosts_service", "Database_Core", 1.0),
            ("Workstation_Primary", "located_at", "Sector_East_3_0", 1.0),
            ("Low_Battery_Condition", "remedied_by", "Dock_And_Recharge", 1.0),
            ("Missing_Dependency", "causes_failure", "Service_Crash", 0.95),
            ("Service_Crash", "remedied_by", "Dependency_Verification", 0.95),
        ]
        for s, r, o, c in defaults:
            self.add_triple(s, r, o, confidence=c, source="system_bootstrap")

    def add_triple(
        self,
        subject: str,
        relation: str,
        object: str,
        confidence: float = 1.0,
        source: str = "runtime",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeTriple:
        s_clean = subject.strip()
        r_clean = relation.strip()
        o_clean = object.strip()

        # Check existing duplicate
        for t in self.get_triples_for_subject(s_clean):
            if t.relation == r_clean and t.object == o_clean:
                t.confidence = max(t.confidence, confidence)
                t.timestamp = datetime.now(timezone.utc).isoformat()
                return t

        triple = KnowledgeTriple(
            subject=s_clean,
            relation=r_clean,
            object=o_clean,
            confidence=confidence,
            source=source,
            metadata=metadata or {},
        )
        self.triples.append(triple)

        if s_clean not in self._subj_index:
            self._subj_index[s_clean] = []
        self._subj_index[s_clean].append(triple)

        if o_clean not in self._obj_index:
            self._obj_index[o_clean] = []
        self._obj_index[o_clean].append(triple)

        return triple

    def get_triples_for_subject(self, subject: str) -> List[KnowledgeTriple]:
        return self._subj_index.get(subject.strip(), [])

    def get_triples_for_object(self, object: str) -> List[KnowledgeTriple]:
        return self._obj_index.get(object.strip(), [])

    def find_shortest_path(self, start: str, target: str, max_depth: int = 4) -> List[Tuple[str, str, str]]:
        """
        Breadth-First Search (BFS) for shortest semantic path between entities.
        Returns list of (subj, rel, obj) step tuples.
        """
        start = start.strip()
        target = target.strip()
        if start == target:
            return []

        queue: List[Tuple[str, List[Tuple[str, str, str]]]] = [(start, [])]
        visited: Set[str] = {start}

        while queue:
            curr_node, path = queue.pop(0)
            if len(path) >= max_depth:
                continue

            for t in self.get_triples_for_subject(curr_node):
                if t.object == target:
                    return path + [(t.subject, t.relation, t.object)]
                if t.object not in visited:
                    visited.add(t.object)
                    queue.append((t.object, path + [(t.subject, t.relation, t.object)]))

        return []

    def get_graph_visualization_data(self) -> Dict[str, Any]:
        """Returns structured nodes and links for graph visualization."""
        nodes_dict: Dict[str, Dict[str, Any]] = {}
        links: List[Dict[str, Any]] = []

        for t in self.triples:
            if t.subject not in nodes_dict:
                nodes_dict[t.subject] = {"id": t.subject, "group": "subject"}
            if t.object not in nodes_dict:
                nodes_dict[t.object] = {"id": t.object, "group": "object"}

            links.append({
                "source": t.subject,
                "target": t.object,
                "relation": t.relation,
                "confidence": t.confidence,
            })

        return {
            "nodes": list(nodes_dict.values()),
            "links": links,
            "total_triples": len(self.triples),
        }


knowledge_graph = SemanticKnowledgeGraph()
