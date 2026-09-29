"""
Robotics Domain Ontology & Semantic Inference Rules for P.H.A.S.S Sphere.
"""

from __future__ import annotations
from typing import Any, Dict, List, Set, Tuple
from .graph import SemanticKnowledgeGraph, knowledge_graph, KnowledgeTriple


class DomainOntology:
    """
    Applies transitivity, inverse relations, and axiomatic rules across the knowledge graph.
    """

    def __init__(self, graph: SemanticKnowledgeGraph):
        self.graph = graph

    def infer_new_triples(self) -> List[KnowledgeTriple]:
        """
        Executes single inference sweep:
        Rule 1: Transitivity of location: (A located_at B) and (B located_at C) -> (A located_at C)
        Rule 2: Cause-Remedy linkage: (E causes_failure F) and (F remedied_by R) -> (E requires_strategy R)
        """
        new_inferred: List[KnowledgeTriple] = []

        for t1 in list(self.graph.triples):
            # Transitive location
            if t1.relation == "located_at":
                for t2 in self.graph.get_triples_for_subject(t1.object):
                    if t2.relation in ("located_at", "part_of"):
                        inf = self.graph.add_triple(
                            t1.subject,
                            "located_within",
                            t2.object,
                            confidence=min(t1.confidence, t2.confidence) * 0.9,
                            source="ontology_inference",
                        )
                        new_inferred.append(inf)

            # Diagnostic cause & remedy linkage
            if t1.relation == "causes_failure":
                for t2 in self.graph.get_triples_for_subject(t1.object):
                    if t2.relation == "remedied_by":
                        inf = self.graph.add_triple(
                            t1.subject,
                            "requires_intervention",
                            t2.object,
                            confidence=0.92,
                            source="ontology_inference",
                        )
                        new_inferred.append(inf)

        return new_inferred


ontology_engine = DomainOntology(knowledge_graph)
