"""
Lifelong Context Engine for P.H.A.S.S v11.0.
Unified 3-tier memory engine:
1. Short-term: Sliding window of last 10 messages.
2. Medium-term: Current project context (active folder, plugged board, active mode).
3. Long-term: SQLite / ChromaDB knowledge base.
Resolves pronouns and references ('check it') across all 3 layers.
Auto-shifts context (e.g. to 'ESP32 Mode') upon hardware connection.
"""

from __future__ import annotations
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("phass.core.lifelong_context")


class LifelongContextEngine:
    """
    Combines Short-Term, Medium-Term, and Long-Term memory into a unified context layer.
    """
    _instance: Optional[LifelongContextEngine] = None

    def __init__(self, state_file: str = "checkpoints/lifelong_context.json"):
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        # 1. Short-Term (last 10 messages)
        self.short_term: List[Dict[str, str]] = []

        # 2. Medium-Term (active project & hardware context)
        self.medium_term: Dict[str, Any] = {
            "working_dir": str(Path.cwd()),
            "project_name": "P.H.A.S.S Workspace",
            "active_board": "ESP32",
            "active_port": "COM3",
            "active_mode": "ESP32 Mode",
            "last_referenced_component": "BC547",
            "last_action": None,
        }

        self.load_state()

    @classmethod
    def get_instance(cls) -> LifelongContextEngine:
        if cls._instance is None:
            cls._instance = LifelongContextEngine()
        return cls._instance

    def load_state(self):
        """Loads state from checkpoints/lifelong_context.json."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.short_term = data.get("short_term", [])[-10:]
                        self.medium_term.update(data.get("medium_term", {}))
            except Exception as e:
                logger.warning(f"Failed to load lifelong context: {e}")

    def save_state(self):
        """Persists lifelong context to disk."""
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump({
                    "short_term": self.short_term[-10:],
                    "medium_term": self.medium_term,
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save lifelong context: {e}")

    def record_message(self, role: str, content: str):
        """Records message into short-term memory (sliding window of 10)."""
        self.short_term.append({"role": role, "content": content})
        self.short_term = self.short_term[-10:]

        # Extract referenced hardware components from content
        comp_match = re.search(r"\b(BC547|2N2222|NE555|ATmega328P|ESP32|ESP8266|STM32|RP2040|LED|resistor|capacitor)\b", content, re.IGNORECASE)
        if comp_match:
            self.medium_term["last_referenced_component"] = comp_match.group(1).upper()

        self.save_state()

    def set_active_hardware(self, board_name: str, port: str = "COM3"):
        """
        Auto-Context Switching: Automatically shifts mode (e.g. 'ESP32 Mode')
        when hardware changes without user needing to type anything.
        """
        self.medium_term["active_board"] = board_name
        self.medium_term["active_port"] = port
        self.medium_term["active_mode"] = f"{board_name} Mode"
        logger.info(f"Context shifted to {board_name} Mode ({port})")
        self.save_state()

    def query_long_term(self, query: str) -> List[str]:
        """Queries SQLite / ChromaDB long-term memory via Mind Palace."""
        memories = []
        try:
            from core.mind_palace import get_mind
            mind = get_mind()
            records = mind.recall(query, top_k=3)
            for r in records:
                if isinstance(r, dict) and "text" in r:
                    memories.append(r["text"])
                elif isinstance(r, str):
                    memories.append(r)
        except Exception:
            pass
        return memories

    def resolve_reference(self, query: str) -> str:
        """
        Resolves pronouns ('it', 'this board', 'check it', 'flash it')
        using the 3-tier memory engine.
        """
        lower_q = query.lower().strip()
        last_comp = self.medium_term.get("last_referenced_component", "BC547")
        active_board = self.medium_term.get("active_board", "ESP32")

        # Pronoun resolution for "check it" / "pinout of it"
        if lower_q in ("check it", "what is it", "pinout of it", "test it", "inspect it"):
            return f"What is the pinout and specifications of {last_comp}?"

        if lower_q in ("flash it", "program it", "compile it"):
            return f"Program {active_board} to blink an LED"

        if re.search(r"\bit\b", lower_q) and ("pinout" in lower_q or "transistor" in lower_q):
            return re.sub(r"\bit\b", last_comp, query, flags=re.IGNORECASE)

        if re.search(r"\bit\b", lower_q) and ("flash" in lower_q or "program" in lower_q or "board" in lower_q):
            return re.sub(r"\bit\b", active_board, query, flags=re.IGNORECASE)

        return query

    # Alias for pronoun resolution
    resolve_pronouns = resolve_reference

    def recall_knowledge(self, query: str) -> Optional[str]:
        """Recalls facts from Semantic Knowledge Graph via Reflective Learner."""
        try:
            from core.reflective_learner import reflective_learner
            return reflective_learner.context_free_recall(query)
        except Exception:
            return None

    def get_unified_context(self) -> Dict[str, Any]:
        """Returns unified context dict across short, medium, and long term."""
        return {
            "mode": self.medium_term.get("active_mode", "ESP32 Mode"),
            "board": self.medium_term.get("active_board", "ESP32"),
            "port": self.medium_term.get("active_port", "COM3"),
            "last_component": self.medium_term.get("last_referenced_component", "BC547"),
            "recent_turns_count": len(self.short_term),
            "working_directory": self.medium_term.get("working_dir"),
        }


lifelong_context = LifelongContextEngine.get_instance()
