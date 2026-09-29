"""
Stateful Reflective Memory (The Hippocampus) for P.H.A.S.S v12.0.
Implements a 3-tier memory engine:
1. Working Memory: Ephemeral in-memory scratchpad.
2. Episodic Memory: Timestamped event logs of interactions and execution traces.
3. Semantic Knowledge Graph: Subject-Predicate-Object triple store mapping relationships.
Includes Reflective Learning Loop (SRDP) that extracts facts and learns rules from mistakes.
"""

from __future__ import annotations
import json
import logging
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("phass.core.reflective_learner")


class SemanticKnowledgeGraph:
    """Graph database storing (Subject, Predicate, Object) triples with metadata."""
    def __init__(self, filepath: str = "checkpoints/knowledge_graph.json"):
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self.triples: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.triples = json.load(f)
            except Exception:
                self.triples = []
        else:
            # Seed foundational facts
            self.add_triple("ESP32", "has_default_baud", "115200")
            self.add_triple("BC547", "is_transistor_type", "NPN BJT")
            self.add_triple("ATmega328P", "has_pin_count", "28")
            self.add_triple("Solo Leveling", "has_protagonist", "Sung Jin-Woo")
            self.add_triple("Sung Jin-Woo", "possesses_power", "The System")

    def _save(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.triples, f, indent=2)
        except Exception as e:
            logger.debug(f"Failed saving knowledge graph: {e}")

    def add_triple(self, subject: str, predicate: str, obj: str, confidence: float = 1.0, source: str = "system"):
        sub_c = subject.strip()
        pred_c = predicate.strip()
        obj_c = obj.strip()
        # Avoid duplicate triples
        for t in self.triples:
            if t["subject"].lower() == sub_c.lower() and t["predicate"].lower() == pred_c.lower():
                t["object"] = obj_c
                t["confidence"] = confidence
                t["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._save()
                return

        triple = {
            "id": f"triple_{uuid.uuid4().hex[:6]}",
            "subject": sub_c,
            "predicate": pred_c,
            "object": obj_c,
            "confidence": confidence,
            "source": source,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.triples.append(triple)
        self._save()

    def query(self, entity: str) -> List[Dict[str, Any]]:
        """Finds all triples where subject or object relates to entity."""
        e_lower = entity.lower()
        matches = []
        for t in self.triples:
            if e_lower in t["subject"].lower() or e_lower in t["object"].lower() or e_lower in t["predicate"].lower():
                matches.append(t)
        return matches

    def get_relationship(self, subject: str, predicate: str) -> Optional[str]:
        sub_l = subject.lower()
        pred_l = predicate.lower()
        for t in self.triples:
            if t["subject"].lower() == sub_l and t["predicate"].lower() == pred_l:
                return t["object"]
        return None


class ReflectiveLearner:
    """
    The Hippocampus: Integrates Working, Episodic, and Knowledge Graph tiers.
    Runs the Stateful Reflective Decision Process (SRDP) to extract rules from failures.
    """
    _instance: Optional[ReflectiveLearner] = None

    def __init__(
        self,
        episodic_file: str = "checkpoints/episodic_memory.jsonl",
        graph_file: str = "checkpoints/knowledge_graph.json",
        rules_file: str = "checkpoints/learned_rules.json",
    ):
        self.episodic_file = Path(episodic_file)
        self.episodic_file.parent.mkdir(parents=True, exist_ok=True)
        self.rules_file = Path(rules_file)
        self.graph = SemanticKnowledgeGraph(graph_file)
        self.working_memory: Dict[str, Any] = {}
        self.learned_rules: List[Dict[str, Any]] = []
        self._load_rules()

    @classmethod
    def get_instance(cls) -> ReflectiveLearner:
        if cls._instance is None:
            cls._instance = ReflectiveLearner()
        return cls._instance

    def _load_rules(self):
        if self.rules_file.exists():
            try:
                with open(self.rules_file, "r", encoding="utf-8") as f:
                    self.learned_rules = json.load(f)
            except Exception:
                self.learned_rules = []

    def _save_rules(self):
        try:
            with open(self.rules_file, "w", encoding="utf-8") as f:
                json.dump(self.learned_rules, f, indent=2)
        except Exception:
            pass

    # ================= WORKING MEMORY =================

    def set_working_memory(self, key: str, value: Any):
        self.working_memory[key] = value

    def get_working_memory(self, key: str, default: Any = None) -> Any:
        return self.working_memory.get(key, default)

    # ================= EPISODIC MEMORY =================

    def log_episode(
        self,
        event_type: str,
        user_input: str,
        system_response: str,
        tool_actions: Optional[List[Dict[str, Any]]] = None,
        success: bool = True,
        error_details: Optional[str] = None,
    ):
        """Appends timestamped interaction episode."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "user_input": user_input,
            "system_response": system_response,
            "tool_actions": tool_actions or [],
            "success": success,
            "error_details": error_details,
        }
        try:
            with open(self.episodic_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.debug(f"Failed logging episode: {e}")

        # Update working memory
        self.working_memory["last_input"] = user_input
        self.working_memory["last_response"] = system_response

    # ================= REFLECTIVE LEARNING LOOP (SRDP) =================

    def run_reflection_cycle(self) -> Dict[str, Any]:
        """
        Reflects over recent episodes:
        - Extracts factual entities and adds to Knowledge Graph.
        - Identifies errors or failures and synthesizes operational rules.
        """
        episodes = []
        if self.episodic_file.exists():
            try:
                with open(self.episodic_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            episodes.append(json.loads(line.strip()))
            except Exception:
                pass

        new_facts = 0
        new_rules = 0

        # Scan recent 30 episodes
        for ep in episodes[-30:]:
            u_text = ep.get("user_input", "")
            s_text = ep.get("system_response", "")

            # 1. Fact Extraction (e.g. project creation, component references)
            proj_match = re.search(r"(?:start|make|create|bootstrap)\s+(?:a\s+)?project\s+(?:called\s+)?([a-zA-Z0-9_\-]+)", u_text, re.IGNORECASE)
            if proj_match:
                proj_name = proj_match.group(1)
                self.graph.add_triple("User", "created_project", proj_name, source="episodic_reflection")
                self.graph.add_triple(proj_name, "status", "active", source="episodic_reflection")
                new_facts += 1

            # 2. Rule Extraction from Failures (SRDP)
            if not ep.get("success") or ep.get("error_details"):
                err = (ep.get("error_details") or "") + " " + s_text
                # Example: Port permission lock or wrong port
                port_match = re.search(r"(?:port|device)\s+(COM\d+|/dev/tty\w+).*?(?:locked|timeout|denied|failed)", err, re.IGNORECASE)
                if port_match:
                    bad_port = port_match.group(1)
                    rule_text = f"Do not use port {bad_port} for ESP32 devices when port is locked or busy"
                    if not any(r["rule"] == rule_text for r in self.learned_rules):
                        self.learned_rules.append({
                            "id": f"rule_{uuid.uuid4().hex[:4]}",
                            "rule": rule_text,
                            "trigger": f"port_{bad_port}_failure",
                            "confidence": 0.95,
                            "learned_at": datetime.now(timezone.utc).isoformat(),
                        })
                        self._save_rules()
                        new_rules += 1

        return {
            "status": "SUCCESS",
            "episodes_analyzed": len(episodes),
            "new_facts_learned": new_facts,
            "new_rules_derived": new_rules,
            "total_graph_triples": len(self.graph.triples),
            "total_learned_rules": len(self.learned_rules),
        }

    def context_free_recall(self, query: str) -> Optional[str]:
        """
        Recalls facts from Semantic Knowledge Graph even when no explicit context is provided.
        """
        # Look for entities in query
        words = re.findall(r"\b[A-Za-z0-9_\-]+\b", query)
        for w in words:
            if len(w) <= 2 or w.lower() in ["what", "where", "when", "who", "the", "and", "about", "project"]:
                continue
            matches = self.graph.query(w)
            if matches:
                facts = [f"• {m['subject']} {m['predicate'].replace('_', ' ')}: {m['object']}" for m in matches]
                return f"Knowledge Graph Recall for '{w}':\n" + "\n".join(facts)

        return None


reflective_learner = ReflectiveLearner.get_instance()
