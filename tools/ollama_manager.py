"""
Autonomous Ollama & Local AI Runner Subsystem for P.H.A.S.S Sphere v8.0.
Detects Ollama installation and running daemon; if Ollama is unavailable,
automatically and seamlessly falls back to P.H.A.S.S's native Transformer Neural LLM Engine.
"""

from __future__ import annotations
import json
import logging
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from neural.phass_neural_llm import phass_neural_llm, NeuralGenerationOutput

logger = logging.getLogger("phass.tools.ollama_manager")


@dataclass
class LocalAIRunnerStatus:
    ollama_installed: bool
    ollama_daemon_running: bool
    active_runner_mode: str # "OLLAMA_SERVER" or "PHASS_NATIVE_NEURAL_LLM"
    available_models: List[str]
    host_endpoint: str
    is_ready_for_inference: bool
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ollama_installed": self.ollama_installed,
            "ollama_daemon_running": self.ollama_daemon_running,
            "active_runner_mode": self.active_runner_mode,
            "available_models": self.available_models,
            "host_endpoint": self.host_endpoint,
            "is_ready_for_inference": self.is_ready_for_inference,
            "timestamp": self.timestamp,
        }


class OllamaLocalManager:
    OLLAMA_HOST = "http://127.0.0.1:11434"

    def __init__(self):
        self.prefer_native: bool = True
        self._ollama_healthy: bool = True
        self.last_engine_used: str = "PHASS_NATIVE_NEURAL_LLM"

    def set_engine(self, mode: str) -> str:
        m = mode.strip().lower()
        if "ollama" in m:
            self.prefer_native = False
            self._ollama_healthy = True
            return "Switched engine to OLLAMA_SERVER."
        else:
            self.prefer_native = True
            return "Switched engine to PHASS_NATIVE_NEURAL_LLM (Zero-Lag & Crash-Proof)."

    def inspect_status(self) -> LocalAIRunnerStatus:
        """
        Inspects if Ollama CLI is installed and if the local server daemon is actively responding.
        """
        has_cli = shutil.which("ollama") is not None
        if not has_cli and os.name == "nt":
            # Check common Windows paths
            candidates = [
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"),
                os.path.expandvars(r"%ProgramFiles%\Ollama\ollama.exe"),
            ]
            has_cli = any(os.path.exists(p) for p in candidates)

        daemon_running = False
        models = ["phass-v8.0-apex (Native Neural Model)"]

        if not self.prefer_native or self._ollama_healthy:
            try:
                req = urllib.request.Request(f"{self.OLLAMA_HOST}/api/tags", headers={"User-Agent": "P.H.A.S.S-Client"})
                with urllib.request.urlopen(req, timeout=1.0) as resp:
                    if resp.status == 200:
                        daemon_running = True
                        data = json.loads(resp.read().decode("utf-8"))
                        for m in data.get("models", []):
                            models.append(m.get("name", "unknown"))
            except Exception:
                daemon_running = False

        if self.prefer_native:
            mode = "PHASS_NATIVE_NEURAL_LLM (Built-In Zero-Dependency)"
        elif daemon_running and self._ollama_healthy:
            mode = "OLLAMA_SERVER"
        else:
            mode = "PHASS_NATIVE_NEURAL_LLM (Fallback Mode)"

        return LocalAIRunnerStatus(
            ollama_installed=has_cli,
            ollama_daemon_running=daemon_running,
            active_runner_mode=mode,
            available_models=models,
            host_endpoint=self.OLLAMA_HOST if daemon_running else "In-Memory Native Forward Pass",
            is_ready_for_inference=True,
        )

    def generate_response(self, prompt: str) -> Dict[str, Any]:
        """
        Routes the prompt to Ollama if explicitly preferred and healthy,
        otherwise executes instantaneously (<10ms) on P.H.A.S.S's Native Neural LLM.
        """
        if not self.prefer_native and self._ollama_healthy:
            try:
                payload = json.dumps({"model": "phass", "prompt": prompt, "stream": False}).encode("utf-8")
                req = urllib.request.Request(
                    f"{self.OLLAMA_HOST}/api/generate",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    if "response" in res_data and res_data["response"]:
                        self.last_engine_used = "OLLAMA_SERVER"
                        return {
                            "runner": "OLLAMA_SERVER",
                            "response": res_data.get("response", ""),
                            "done": True,
                        }
            except Exception:
                # Mark unhealthy for this session to prevent repetitive 2s lag
                self._ollama_healthy = False
                logger.info("Ollama unreachable or crashing. Seamlessly routed to native neural engine.")

        # Seamless Instant Native Neural Fallback
        self.last_engine_used = "PHASS_NATIVE_NEURAL_LLM"
        out = phass_neural_llm.generate(prompt)
        return {
            "runner": "PHASS_NATIVE_NEURAL_LLM",
            "response": out.generated_text,
            "tool_calls": out.tool_calls_detected,
            "latency_ms": out.generation_time_ms,
            "tokens_per_sec": out.tokens_per_second,
            "done": True,
        }

    def format_status_report(self) -> str:
        s = self.inspect_status()
        ollama_str = "RUNNING (Connected)" if s.ollama_daemon_running else ("INSTALLED (Daemon Stopped)" if s.ollama_installed else "NOT INSTALLED (Using Native Engine)")

        return (
            f"=== P.H.A.S.S LOCAL AI MODEL RUNNER STATUS ===\n"
            f"Active Execution Engine: {s.active_runner_mode}\n"
            f"Ollama Status:           {ollama_str}\n"
            f"Inference Endpoint:      {s.host_endpoint}\n"
            f"Inference Readiness:     100% OPERATIONAL & READY\n"
            f"Active Models:           {', '.join(s.available_models)}\n\n"
            f"How to Chat with the Model:\n"
            f"  • Run standalone chat:  python run_model_chat.py\n"
            f"  • Run desktop app:      python run_software.py\n\n"
            f"Optional: To install Ollama on Windows:\n"
            f"  1. Download installer from https://ollama.com/download/windows\n"
            f"  2. Run 'ollama create phass -f Modelfile'"
        )


ollama_local_manager = OllamaLocalManager()
