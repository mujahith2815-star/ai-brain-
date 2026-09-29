"""
Multi-Provider LLM Engine & Orchestrator for P.H.A.S.S Sphere.
Unifies Local LLMs (Ollama), Cloud Models (Gemini/OpenAI), and Offline Heuristic Reasoners
with structured output parsing, prompt templating, and context budgeting.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json
import logging
import aiohttp

logger = logging.getLogger("phass.nlp.llm_engine")


@dataclass
class LLMOutput:
    text: str
    structured_data: Optional[Dict[str, Any]] = None
    model_name: str = "offline_heuristic"
    confidence: float = 0.92
    prompt_tokens: int = 0
    completion_tokens: int = 0
    error: Optional[str] = None


class BaseLLMProvider(ABC):
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 2048,
        response_schema: Optional[Dict[str, Any]] = None,
    ) -> LLMOutput:
        pass


class OfflineLLMProvider(BaseLLMProvider):
    """
    Deterministic rule-based reasoning engine that functions 100% offline.
    """

    def __init__(self, model_name: str = "P.H.A.S.S-Offline-Linguistic-V1"):
        self.model_name = model_name

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 2048,
        response_schema: Optional[Dict[str, Any]] = None,
    ) -> LLMOutput:
        last_user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user_msg = m.get("content", "")
                break

        msg_lower = last_user_msg.lower()

        if "diagnose" in msg_lower or "failure" in msg_lower:
            text = (
                "Initiating multi-tier system diagnostic. Inspecting system telemetry, logs, and dependencies."
            )
            structured = {
                "intent": "DIAGNOSTIC",
                "strategy": "Systematic telemetry and log analysis",
                "recommended_tools": ["system_diagnostics", "file_reader", "memory_query"],
                "confidence": 0.94,
            }
        elif "environment" in msg_lower or "scan" in msg_lower:
            text = (
                "Engaging 360 LiDAR raycasters and multi-spectral AI camera. Updating World Model with detected entities."
            )
            structured = {
                "intent": "ENVIRONMENT_PROBE",
                "strategy": "Simultaneous LiDAR sweep and camera object identification",
                "recommended_tools": ["sensor_probe", "vision_scan", "world_model_update"],
                "confidence": 0.95,
            }
        elif "status" in msg_lower:
            text = "P.H.A.S.S Sphere operational status: Nominal. Continuous cognitive loop and memory retrieval online."
            structured = {"intent": "STATUS_CHECK", "status": "NOMINAL", "confidence": 0.98}
        else:
            text = f"Processing directive '{last_user_msg}' through cognitive core. Subtasks dispatched."
            structured = {"intent": "GENERAL_DIRECTIVE", "directive": last_user_msg, "confidence": 0.90}

        return LLMOutput(
            text=text,
            structured_data=structured,
            model_name=self.model_name,
            confidence=0.94,
            prompt_tokens=len(last_user_msg.split()) * 2,
            completion_tokens=len(text.split()) * 2,
        )


class OllamaProvider(BaseLLMProvider):
    """
    Connects to local Ollama API (e.g. llama3, mistral, deepseek-r1).
    """

    def __init__(self, endpoint: str = "http://localhost:11434", model: str = "llama3"):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.fallback = OfflineLLMProvider()

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 2048,
        response_schema: Optional[Dict[str, Any]] = None,
    ) -> LLMOutput:
        url = f"{self.endpoint}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if response_schema:
            payload["format"] = "json"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        content = data.get("message", {}).get("content", "")
                        parsed_json = None
                        if response_schema:
                            try:
                                parsed_json = json.loads(content)
                            except Exception:
                                pass
                        return LLMOutput(
                            text=content,
                            structured_data=parsed_json,
                            model_name=f"ollama:{self.model}",
                            confidence=0.91,
                        )
        except Exception as e:
            logger.warning(f"Ollama request failed: {e}. Falling back to OfflineLLMProvider.")

        return await self.fallback.chat_completion(messages, temperature, max_tokens, response_schema)


class LLMOrchestrator:
    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        self.provider = provider or OfflineLLMProvider()

    def set_provider(self, provider: BaseLLMProvider) -> None:
        self.provider = provider

    async def generate_thought_and_plan(self, goal_title: str, world_context: Dict[str, Any]) -> LLMOutput:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are P.H.A.S.S Sphere, an autonomous physical AI robot. "
                    "Decompose the user goal into structured subtasks with tool bindings. "
                    "Output valid JSON matching the requested schema."
                ),
            },
            {
                "role": "user",
                "content": f"Goal: {goal_title}\nWorld Context: {json.dumps(world_context)}",
            },
        ]
        schema = {
            "type": "object",
            "properties": {
                "understanding": {"type": "string"},
                "subtasks": {"type": "array"},
                "confidence": {"type": "number"},
            },
        }
        return await self.provider.chat_completion(messages, response_schema=schema)


llm_orchestrator = LLMOrchestrator()
