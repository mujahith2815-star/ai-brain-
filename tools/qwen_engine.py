"""
Local Qwen2.5-7B Engine for Orvix Sphere.
Communicates with Ollama at localhost:11434 to run qwen2.5:7b-instruct-q4_K_M.
Employs CPU safety mode (options: {"num_gpu": 0}) on hardware with limited VRAM (e.g. 2GB)
to ensure 100% stability without llama runner memory split crashes.
"""

from __future__ import annotations
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple
import urllib.request
import urllib.error

from config.user_config import is_w_drive_available
from tools.ollama_setup import is_ollama_service_running, list_models

logger = logging.getLogger("orvix.tools.qwen_engine")

OLLAMA_API_BASE = "http://localhost:11434"
DEFAULT_MODEL_NAME = "qwen2.5:7b-instruct-q4_K_M"
LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "qwen_engine.log"


class QwenEngine:
    """Local offline reasoning engine utilizing Qwen2.5-7B-Instruct on W: drive."""

    name: str = "qwen"
    alias: str = "local"

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        api_base: str = OLLAMA_API_BASE,
        force_cpu: bool = True,
    ):
        self.model_name = model_name
        self.api_base = api_base
        # Default force_cpu=True protects 2GB VRAM GPUs from memory graph split crashes
        self.force_cpu = force_cpu
        self._last_avail_check: float = 0.0
        self._cached_available: bool = False

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            return other.lower() in ("qwen", "local", "qwen2.5-7b", "qwen2.5", "qwen_engine", "local_1b", "llama")
        return self is other

    def __hash__(self) -> int:
        return id(self)

    def is_available(self, force_refresh: bool = False) -> bool:
        """Checks if Ollama service is reachable and Qwen model is available (cached for 3s)."""
        now = time.time()
        if not force_refresh and (now - self._last_avail_check) < 3.0:
            return self._cached_available

        self._last_avail_check = now
        if not is_ollama_service_running():
            self._cached_available = False
            return False
        models = list_models()
        for m in models:
            n = m.get("name", "")
            if self.model_name in n or "qwen2.5:7b" in n:
                self._cached_available = True
                return True
        self._cached_available = False
        return False

    def _get_options(self) -> Dict[str, Any]:
        """Builds generation options payload."""
        opts: Dict[str, Any] = {
            "temperature": 0.4,
            "top_p": 0.9,
        }
        if self.force_cpu:
            opts["num_gpu"] = 0
        return opts

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.4,
    ) -> str:
        """
        Generates text using the Qwen2.5-7B model via Ollama.
        """
        if not self.is_available():
            raise RuntimeError(
                f"QwenEngine is unavailable. Ensure Ollama is running and '{self.model_name}' is downloaded."
            )

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": self._get_options(),
        }
        if system_instruction:
            payload["system"] = system_instruction
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        if temperature:
            payload["options"]["temperature"] = temperature

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.api_base}/api/generate",
            data=data_bytes,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        start_t = time.time()
        try:
            with urllib.request.urlopen(req, timeout=120.0) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                response_text = result.get("response", "").strip()
                dur = round(time.time() - start_t, 2)
                logger.info(f"Qwen generated {len(response_text)} chars in {dur}s.")
                return response_text
        except Exception as e:
            logger.error(f"Error querying Qwen API: {e}")
            raise

    def stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """Streams generation tokens from Qwen."""
        if not self.is_available():
            raise RuntimeError("QwenEngine is unavailable.")

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": True,
            "options": self._get_options(),
        }
        if system_instruction:
            payload["system"] = system_instruction

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.api_base}/api/generate",
            data=data_bytes,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=120.0) as resp:
            for line in resp:
                if line:
                    chunk = json.loads(line.decode("utf-8"))
                    text = chunk.get("response", "")
                    if text:
                        yield text
                    if chunk.get("done", False):
                        break

    def generate_with_tools(
        self,
        prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        system_instruction: Optional[str] = None,
        max_steps: int = 6,
    ) -> Dict[str, Any]:
        """
        Executes reasoning turn with tool capability using Qwen2.5-7B structured JSON output.
        """
        tool_catalog = ""
        if tools:
            tool_catalog = "\n".join(f"- {t.get('name')}: {t.get('description')}" for t in tools)

        enhanced_system = (
            (system_instruction or "You are Orvix, an intelligent assistant.")
            + "\n\nCRITICAL: Respond ONLY with valid JSON. Do not include markdown preamble."
            + '\nEither an action plan: {"actions": [{"tool": "tool_name", "args": {...}}]}'
            + '\nor final answer: {"action": "final_answer", "thought": "...", "response": "..."}'
        )

        full_prompt = prompt
        if tool_catalog:
            full_prompt += f"\n\nAvailable Tools:\n{tool_catalog}"

        raw_text = self.generate(
            prompt=full_prompt,
            system_instruction=enhanced_system,
            temperature=0.2,
        )

        # Clean code fences
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            data = json.loads(cleaned)
            if "actions" in data and isinstance(data["actions"], list):
                return {
                    "text": raw_text,
                    "has_tools": True,
                    "tool_calls": data["actions"],
                    "decision": data,
                }
            elif "action" in data:
                return {
                    "text": data.get("response", raw_text),
                    "has_tools": False,
                    "tool_calls": [],
                    "decision": data,
                }
        except Exception:
            pass

        # Fallback to plain answer if not JSON
        return {
            "text": raw_text,
            "has_tools": False,
            "tool_calls": [],
            "decision": {
                "action": "final_answer",
                "thought": "Direct Qwen textual response",
                "response": raw_text,
            },
        }


# Global singleton Qwen engine
qwen_engine = QwenEngine()
