"""
Model Router for Orvix Sphere Hybrid Dual-Engine Architecture (v1.4.0).
Intelligently routes tasks between Google Gemini 2.0 Flash (Primary Cloud)
and Qwen2.5-7B-Instruct on W: drive (Offline Local Fallback).
"""

from __future__ import annotations
import logging
import re
import time
from typing import Any, Dict, Optional, Tuple, Union

from config.api_config import api_config
from tools.gemini_engine import GeminiEngine, gemini_engine
from tools.qwen_engine import QwenEngine, qwen_engine
from tools.api_cost_tracker import api_cost_tracker

logger = logging.getLogger("orvix.tools.model_router")


class RoutedEngine(str):
    """
    Hybrid string-engine representation returned by ModelRouter.
    Satisfies string comparisons (e.g. res == 'gemini', res == 'local', res == 'qwen')
    while delegating generation calls (generate, generate_with_tools, stream)
    directly to the underlying engine instance.
    """

    name: str
    engine: Any

    def __new__(cls, name: str, engine: Any = None):
        val = "gemini" if name in ("gemini", "cloud") else "local"
        obj = super().__new__(cls, val)
        obj.name = name
        obj.engine = engine
        return obj

    def __eq__(self, other: Any) -> bool:
        s = str(self)
        if isinstance(other, str):
            low = other.lower()
            if s == "gemini":
                return low in ("gemini", "cloud")
            if s == "local":
                return low in ("local", "qwen", "qwen2.5-7b", "llama", "local_1b")
            return s == low
        if other is self.engine:
            return True
        return super().__eq__(other)

    def __getattr__(self, item: str) -> Any:
        if self.engine is not None and hasattr(self.engine, item):
            return getattr(self.engine, item)
        raise AttributeError(f"'RoutedEngine' object has no attribute '{item}'")

    def is_available(self) -> bool:
        if self.engine is not None and hasattr(self.engine, "is_available"):
            return self.engine.is_available()
        return False

    def generate(self, *args, **kwargs) -> Any:
        if self.engine is not None and hasattr(self.engine, "generate"):
            return self.engine.generate(*args, **kwargs)
        raise RuntimeError(f"Engine '{self.name}' does not implement generate.")

    def generate_with_tools(self, *args, **kwargs) -> Any:
        if self.engine is not None and hasattr(self.engine, "generate_with_tools"):
            return self.engine.generate_with_tools(*args, **kwargs)
        raise RuntimeError(f"Engine '{self.name}' does not implement generate_with_tools.")

    def stream(self, *args, **kwargs) -> Any:
        if self.engine is not None and hasattr(self.engine, "stream"):
            return self.engine.stream(*args, **kwargs)
        raise RuntimeError(f"Engine '{self.name}' does not implement stream.")


class ModelRouter:
    """
    Intelligent router selecting between Google Gemini Flash (Cloud)
    and Qwen2.5-7B (Local on W: drive).
    """

    VALID_MODES = {"auto", "cloud_first", "local_first", "cloud_only", "local_only"}

    def __init__(
        self,
        gemini: Optional[GeminiEngine] = None,
        qwen: Optional[QwenEngine] = None,
        default_mode: Optional[str] = None,
    ):
        self.gemini = gemini or gemini_engine
        self.qwen = qwen or qwen_engine
        self._mode = (default_mode or api_config.model_mode or "auto").strip().lower()
        if self._mode not in self.VALID_MODES:
            self._mode = "auto"
        self._routing_stats = {
            "total_routed": 0,
            "routed_to_gemini": 0,
            "routed_to_qwen": 0,
            "fallbacks_triggered": 0,
            "last_reason": "",
        }

    @property
    def current_mode(self) -> str:
        cfg_mode = (api_config.model_mode or "").strip().lower()
        if cfg_mode in self.VALID_MODES:
            return cfg_mode
        return self._mode

    def switch_mode(self, mode: str) -> str:
        """
        Updates the routing mode.
        Supported modes: 'auto', 'cloud_first', 'local_first', 'cloud_only', 'local_only'.
        """
        clean = mode.strip().lower()
        if clean not in self.VALID_MODES:
            raise ValueError(
                f"Unknown model routing mode '{mode}'. Expected one of: {', '.join(sorted(self.VALID_MODES))}"
            )
        self._mode = clean
        api_config.set_mode(clean)
        logger.info(f"ModelRouter: Mode switched to '{clean}'.")
        return self._mode

    def assess_complexity(self, prompt: str) -> str:
        """
        Evaluates cognitive complexity of the prompt.
        Returns: 'trivial', 'simple', or 'complex'.
        """
        p_clean = prompt.strip().lower()

        # 1. Trivial queries (greetings, simple identity checks, health pings)
        if len(p_clean.split()) <= 4 and re.match(
            r"^(hello|hi|hey|good morning|good evening|who are you|status|help|ping|test)",
            p_clean,
        ):
            return "trivial"

        # 2. Indicators of multi-step complexity, calculations, or deep logic
        complex_signals = [
            "calculate", "sum", "total", "average", "convert",
            "read", "write", "edit", "create", "delete", "file",
            "terminal", "command", "powershell", "bash", "execute",
            "search", "find", "analyze", "debug", "refactor",
            "first", "then", "after", "and then", "pipeline",
            "explain why", "step by step", "multi-step",
        ]
        if any(w in p_clean for w in complex_signals) or len(p_clean.split()) > 10 or "\n" in prompt.strip():
            return "complex"

        return "simple"

    def route(self, prompt: str, complexity_hint: Optional[str] = None) -> RoutedEngine:
        """
        Selects engine for prompt execution.
        Returns a RoutedEngine instance that functions both as an Engine and as a str ('gemini' or 'local').
        """
        self._routing_stats["total_routed"] += 1
        mode = self.current_mode
        cloud_avail = self.gemini.is_available()
        local_avail = self.qwen.is_available()

        # 1. Mode: local_only
        if mode == "local_only":
            self._routing_stats["routed_to_qwen"] += 1
            self._routing_stats["last_reason"] = "User mode is 'local_only'"
            logger.info(f"[ModelRouter] Routed to Local/Qwen (reason: {self._routing_stats['last_reason']})")
            return RoutedEngine("qwen", self.qwen)

        # 2. Mode: cloud_only
        if mode == "cloud_only":
            if not cloud_avail:
                raise RuntimeError(
                    "ModelRouter is set to 'cloud_only' mode, but Google Gemini Flash is unavailable. "
                    "Set GEMINI_API_KEY or switch mode using '/router auto' or '/router cloud_first'."
                )
            self._routing_stats["routed_to_gemini"] += 1
            self._routing_stats["last_reason"] = "User mode is 'cloud_only'"
            logger.info(f"[ModelRouter] Routed to Gemini (reason: {self._routing_stats['last_reason']})")
            return RoutedEngine("gemini", self.gemini)

        # 3. Mode: local_first
        if mode == "local_first":
            if local_avail:
                self._routing_stats["routed_to_qwen"] += 1
                self._routing_stats["last_reason"] = "Mode is 'local_first' and Qwen is available"
                logger.info(f"[ModelRouter] Routed to Local/Qwen (reason: {self._routing_stats['last_reason']})")
                return RoutedEngine("qwen", self.qwen)
            elif cloud_avail:
                self._routing_stats["routed_to_gemini"] += 1
                self._routing_stats["fallbacks_triggered"] += 1
                self._routing_stats["last_reason"] = "Mode is 'local_first' but Qwen offline; fell back to Gemini"
                logger.info(f"[ModelRouter] Routed to Gemini fallback (reason: {self._routing_stats['last_reason']})")
                return RoutedEngine("gemini", self.gemini)
            else:
                self._routing_stats["routed_to_qwen"] += 1
                self._routing_stats["last_reason"] = "All engines offline; defaulted to Qwen"
                return RoutedEngine("qwen", self.qwen)

        # 4. Mode: cloud_first
        if mode == "cloud_first":
            if cloud_avail:
                self._routing_stats["routed_to_gemini"] += 1
                self._routing_stats["last_reason"] = "Mode is 'cloud_first' and Gemini is available"
                logger.info(f"[ModelRouter] Routed to Gemini (reason: {self._routing_stats['last_reason']})")
                return RoutedEngine("gemini", self.gemini)
            else:
                self._routing_stats["routed_to_qwen"] += 1
                self._routing_stats["fallbacks_triggered"] += 1
                self._routing_stats["last_reason"] = "Mode is 'cloud_first' but Gemini offline; fell back to Qwen"
                logger.info(f"[ModelRouter] Routed to Local/Qwen fallback (reason: {self._routing_stats['last_reason']})")
                return RoutedEngine("qwen", self.qwen)

        # 5. Mode: auto (Default smart routing)
        # Check network / cloud reachability
        if not cloud_avail:
            self._routing_stats["routed_to_qwen"] += 1
            self._routing_stats["fallbacks_triggered"] += 1
            self._routing_stats["last_reason"] = "Network/Gemini down; auto-routed to local Qwen"
            logger.info(f"[ModelRouter] Routed to Local/Qwen (reason: {self._routing_stats['last_reason']})")
            return RoutedEngine("qwen", self.qwen)

        # Check rate limit headroom
        allowed, wait_sec = api_cost_tracker.check_rate_limit(max_rpm=api_config.rate_limit_rpm)
        if not allowed:
            self._routing_stats["routed_to_qwen"] += 1
            self._routing_stats["fallbacks_triggered"] += 1
            self._routing_stats["last_reason"] = f"Gemini rate limit reached (wait {wait_sec}s); auto-routed to local Qwen"
            logger.info(f"[ModelRouter] Routed to Local/Qwen (reason: {self._routing_stats['last_reason']})")
            return RoutedEngine("qwen", self.qwen)

        # Evaluate complexity
        complexity = complexity_hint or self.assess_complexity(prompt)
        if complexity in ("trivial", "simple"):
            self._routing_stats["routed_to_qwen"] += 1
            self._routing_stats["last_reason"] = f"Task complexity is '{complexity}'; auto-routed to local engine"
            logger.info(f"[ModelRouter] Routed to Local/Qwen (reason: {self._routing_stats['last_reason']})")
            return RoutedEngine("qwen", self.qwen)

        # Complex reasoning tasks go to primary Gemini
        self._routing_stats["routed_to_gemini"] += 1
        self._routing_stats["last_reason"] = f"Task complexity '{complexity}'; routed to primary Gemini 2.0 Flash"
        logger.info(f"[ModelRouter] Routed to Gemini (reason: {self._routing_stats['last_reason']})")
        return RoutedEngine("gemini", self.gemini)

    def get_engine(self, engine_name: str) -> Any:
        """Retrieves engine object for the given engine identifier."""
        norm = engine_name.strip().lower()
        if norm in ("gemini", "cloud", "gemini-2.0-flash"):
            return self.gemini
        elif norm in ("qwen", "local", "qwen2.5-7b", "local_1b", "llama"):
            return self.qwen
        else:
            raise ValueError(f"Unknown engine name '{engine_name}'. Supported: 'gemini', 'qwen'.")

    def test_engines(self) -> Dict[str, Any]:
        """Tests availability and latency of both engines."""
        results: Dict[str, Any] = {}

        # 1. Test Gemini
        g_avail = self.gemini.is_available()
        g_lat = None
        if g_avail:
            try:
                t0 = time.time()
                self.gemini.count_tokens("ping")
                g_lat = round((time.time() - t0) * 1000, 1)
            except Exception:
                g_lat = None

        results["gemini"] = {
            "name": "Google Gemini 2.0 Flash",
            "type": "Cloud API (Free Tier)",
            "available": g_avail,
            "has_key": bool(api_config.has_valid_key()),
            "latency_ms": g_lat,
        }

        # 2. Test Qwen
        q_avail = self.qwen.is_available()
        results["qwen"] = {
            "name": "Qwen2.5-7B-Instruct",
            "type": "Local (W: Drive, Ollama)",
            "available": q_avail,
            "model": getattr(self.qwen, "model_name", "qwen2.5:7b-instruct-q4_K_M"),
        }

        results["current_mode"] = self.current_mode
        return results

    def record_fallback(self) -> None:
        """Logs that a model fallback occurred."""
        self._routing_stats["fallbacks_triggered"] += 1

    def get_status(self) -> Dict[str, Any]:
        """Provides status report on router configuration and activity."""
        cloud_avail = self.gemini.is_available()
        local_avail = self.qwen.is_available()
        usage = api_cost_tracker.get_usage_today()

        return {
            "mode": self.current_mode,
            "primary_engine": {
                "name": "Google Gemini 2.0 Flash",
                "model": getattr(self.gemini, "model_name", "gemini-2.0-flash"),
                "available": cloud_avail,
                "has_api_key": bool(api_config.has_valid_key()),
            },
            "fallback_engine": {
                "name": "Qwen2.5-7B-Instruct (W:)",
                "model": getattr(self.qwen, "model_name", "qwen2.5:7b-instruct-q4_K_M"),
                "available": local_avail,
            },
            "rate_limits": {
                "current_rpm": usage["current_rpm"],
                "rpm_limit": usage["rpm_limit"],
                "rpm_remaining": usage["rpm_remaining"],
            },
            "stats": self._routing_stats.copy(),
        }


# Global singleton router
model_router = ModelRouter()
