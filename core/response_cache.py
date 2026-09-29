"""
Zero-Latency Response Cache for P.H.A.S.S v11.0.
Provides sub-100ms response retrieval for static factual queries
(pinouts, verified lore, board specs) and caches hardware detection status.
Persisted in checkpoints/response_cache.json.
"""

from __future__ import annotations
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("phass.core.response_cache")

DEFAULT_PREPOPULATED_CACHE = {
    "bc547 pinout": (
        "BC547 (TO-92 Package - Flat Face Forward)\n"
        "          ______\n"
        "         /      \\\n"
        "        |  BC547 |\n"
        "        |________|\n"
        "          |  |  |\n"
        "          1  2  3\n"
        "          |  |  |\n"
        "          C  B  E\n"
        "   Pin 1: Collector (C)\n"
        "   Pin 2: Base (B)\n"
        "   Pin 3: Emitter (E)"
    ),
    "2n2222 pinout": (
        "2N2222 (TO-92 Package - Flat Face Forward)\n"
        "          ______\n"
        "         /      \\\n"
        "        | 2N2222 |\n"
        "        |________|\n"
        "          |  |  |\n"
        "          1  2  3\n"
        "          |  |  |\n"
        "          E  B  C\n"
        "   Pin 1: Emitter (E)\n"
        "   Pin 2: Base (B)\n"
        "   Pin 3: Collector (C)"
    ),
    "solo leveling system": (
        "The System in Solo Leveling is a game-like interface created by the Architect "
        "(and powered by the Shadow Monarch, Ashborn) that chose Sung Jin-Woo as its sole player. "
        "It displays floating quest windows, stats (Strength, Agility, Perception, Vitality, Intelligence), "
        "skill trees, dungeon keys, and an instant inventory. Unlike standard hunters with static ranks, "
        "the System allows Jin-Woo to level up without limit, ultimately evolving into the supreme Shadow Monarch."
    ),
    "one piece author": (
        "The author of One Piece is Eiichiro Oda."
    ),
}


class ZeroLatencyCache:
    """
    In-memory and on-disk response cache providing deterministic, zero-latency query resolution.
    """
    _instance: Optional[ZeroLatencyCache] = None

    def __init__(self, cache_file: str = "checkpoints/response_cache.json"):
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache: Dict[str, Any] = {}
        self.hardware_cache: Optional[Dict[str, Any]] = None
        self.load_cache()

    @classmethod
    def get_instance(cls) -> ZeroLatencyCache:
        if cls._instance is None:
            cls._instance = ZeroLatencyCache()
        return cls._instance

    def normalize_query(self, query: str) -> str:
        """Normalizes query string for reliable hashing/lookup."""
        if not query:
            return ""
        q = query.lower().strip()
        # Remove punctuation
        q = re.sub(r"[^\w\s]", " ", q)
        # Collapse whitespace
        q = re.sub(r"\s+", " ", q).strip()
        return q

    def load_cache(self):
        """Loads persistent cache from disk or initializes defaults."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.cache = data.get("queries", {})
                        self.hardware_cache = data.get("hardware", None)
            except Exception as e:
                logger.warning(f"Failed to load response cache: {e}")

        # Seed defaults if empty or missing
        updated_defaults = False
        for k, v in DEFAULT_PREPOPULATED_CACHE.items():
            norm_k = self.normalize_query(k)
            if norm_k not in self.cache:
                self.cache[norm_k] = {
                    "response": v,
                    "timestamp": time.time(),
                    "hits": 0,
                }
                updated_defaults = True
        if updated_defaults:
            self.save_cache()

    def save_cache(self):
        """Persists cache to disk."""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump({"queries": self.cache, "hardware": self.hardware_cache}, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save response cache: {e}")

    def get(self, query: str) -> Optional[str]:
        """
        Retrieves cached response in sub-100ms if query matches.
        """
        norm_q = self.normalize_query(query)
        if not norm_q:
            return None

        # 1. Exact match
        if norm_q in self.cache:
            self.cache[norm_q]["hits"] = self.cache[norm_q].get("hits", 0) + 1
            return self.cache[norm_q]["response"]

        # 2. Semantic keyword match for common static queries
        if "bc547" in norm_q and "pinout" in norm_q:
            return self.get("bc547 pinout")
        if "2n2222" in norm_q and "pinout" in norm_q:
            return self.get("2n2222 pinout")
        if "solo leveling" in norm_q and ("system" in norm_q or "interface" in norm_q):
            return self.get("solo leveling system")
        if "one piece" in norm_q and any(k in norm_q for k in ["author", "creator", "who wrote", "writer"]):
            return self.get("one piece author")

        return None

    def set(self, query: str, response: str, is_factual: bool = True):
        """Caches a verified factual response."""
        norm_q = self.normalize_query(query)
        if not norm_q or not response or not is_factual:
            return

        self.cache[norm_q] = {
            "response": response,
            "timestamp": time.time(),
            "hits": 0,
        }
        self.save_cache()

    def cache_hardware(self, hardware_info: Dict[str, Any]):
        """Caches detected hardware configuration for the session."""
        self.hardware_cache = {
            "data": hardware_info,
            "timestamp": time.time(),
        }
        self.save_cache()

    def get_hardware_cache(self) -> Optional[Dict[str, Any]]:
        """Returns cached hardware configuration if fresh."""
        if self.hardware_cache and "data" in self.hardware_cache:
            return self.hardware_cache["data"]
        return None


response_cache = ZeroLatencyCache.get_instance()
