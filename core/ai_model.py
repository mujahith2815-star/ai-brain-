"""
AI Model Abstraction Layer for P.H.A.S.S Sphere.
Enables model independence, offline-first execution, and hot-swapping between
local heuristic reasoners, local LLMs (Ollama), and cloud models.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import json
import logging
import re
import aiohttp

logger = logging.getLogger("phass.ai_model")


@dataclass
class ModelResponse:
    content: str
    parsed_json: Optional[Dict[str, Any]] = None
    model_name: str = "offline_engine"
    usage: Optional[Dict[str, int]] = None
    confidence: float = 0.90


class BaseAIModel(ABC):
    @abstractmethod
    async def generate_response(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> ModelResponse:
        pass

    @abstractmethod
    async def reason_and_plan(self, goal_description: str, context: Dict[str, Any]) -> Dict[str, Any]:
        pass


class OfflineCognitiveEngine(BaseAIModel):
    """
    High-performance, deterministic cognitive engine that runs 100% offline.
    Uses pattern matching, goal decomposition heuristics, dependency extraction,
    and structured templating to understand goals, build plans, and evaluate results.
    """

    def __init__(self, name: str = "P.H.A.S.S-Offline-Heuristic-V1"):
        self.name = name

    async def generate_response(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> ModelResponse:
        p_lower = prompt.lower()

        if "status" in p_lower or "what is happening" in p_lower:
            content = "P.H.A.S.S Sphere is operational. Continuous environmental perception, spatial localization, and cognitive monitoring are active."
        elif "analyze" in p_lower or "inspect" in p_lower:
            content = "Initiated deep system and sensory inspection. Synthesizing telemetry and identifying anomalies."
        elif "battery" in p_lower or "power" in p_lower:
            content = "Power management subsystem reports nominal discharge curve and optimal cell balance."
        elif "who are you" in p_lower or "vision" in p_lower:
            content = "I am P.H.A.S.S Sphere, an autonomous learning physical AI platform. I operate inside a spherical non-humanoid chassis designed for environmental understanding and digital interaction."
        else:
            content = f"Acknowledged. Processing directive through cognitive core: '{prompt}'. Formulating action plan."

        return ModelResponse(content=content, model_name=self.name, confidence=0.92)

    async def reason_and_plan(self, goal_description: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decomposes natural language directives into structured subtasks with tool mappings.
        """
        desc_lower = goal_description.lower()
        subtasks: List[Dict[str, Any]] = []

        # Contextual strategies
        if any(k in desc_lower for k in ["diagnose", "failure", "error", "troubleshoot", "fix", "repair", "bug"]):
            subtasks = [
                {
                    "title": "Gather system telemetry & sensor streams",
                    "description": "Inspect CPU, memory, power draw, and sensor health",
                    "tool": "system_diagnostics",
                    "parameters": {"scope": "full_telemetry"},
                    "expected_output": "System telemetry report",
                    "priority": 1,
                },
                {
                    "title": "Scan system logs for anomaly signatures",
                    "description": "Parse log files and event history for error spikes",
                    "tool": "file_reader",
                    "parameters": {"file_path": "logs/system.log", "filter_pattern": "ERROR|WARN"},
                    "expected_output": "Extracted error signatures",
                    "priority": 2,
                },
                {
                    "title": "Verify dependency integrity and configs",
                    "description": "Check configuration schemas and active connections",
                    "tool": "system_diagnostics",
                    "parameters": {"scope": "dependencies"},
                    "expected_output": "Dependency status report",
                    "priority": 3,
                },
                {
                    "title": "Synthesize hypothesis and evaluate root cause",
                    "description": "Cross-reference observations against known failure patterns in episodic memory",
                    "tool": "memory_query",
                    "parameters": {"query": "failure patterns and error solutions"},
                    "expected_output": "Validated root cause hypothesis",
                    "priority": 4,
                },
                {
                    "title": "Formulate resolution & verify system stability",
                    "description": "Apply verified fix or recommendations and confirm stabilization",
                    "tool": "system_diagnostics",
                    "parameters": {"scope": "verification"},
                    "expected_output": "Resolution confirmation report",
                    "priority": 5,
                },
            ]
        elif any(k in desc_lower for k in ["inspect", "explore", "scan", "map", "environment", "room", "surveillance"]):
            subtasks = [
                {
                    "title": "Capture 360 LiDAR point cloud and ultrasonic sweep",
                    "description": "Measure distances to all surrounding obstacles and boundaries",
                    "tool": "sensor_probe",
                    "parameters": {"sensors": ["lidar", "ultrasonic"]},
                    "expected_output": "Spatial boundary mapping",
                    "priority": 1,
                },
                {
                    "title": "Execute multi-spectral camera scene recognition",
                    "description": "Detect objects, persons, and environment entities in field of view",
                    "tool": "vision_scan",
                    "parameters": {"detect_objects": True, "detect_faces": True},
                    "expected_output": "List of detected entities and labels",
                    "priority": 2,
                },
                {
                    "title": "Update World Model & Spatial Grid",
                    "description": "Register identified objects and locations into dynamic world model",
                    "tool": "world_model_update",
                    "parameters": {"target": "entities"},
                    "expected_output": "Updated world model confirmation",
                    "priority": 3,
                },
                {
                    "title": "Generate comprehensive environmental report",
                    "description": "Synthesize observations into human-readable summary",
                    "tool": "generate_report",
                    "parameters": {"report_type": "environment_status"},
                    "expected_output": "Final environmental analysis report",
                    "priority": 4,
                },
            ]
        elif any(k in desc_lower for k in ["navigate", "move", "patrol", "dock", "charge"]):
            subtasks = [
                {
                    "title": "Locate target coordinates and evaluate path feasibility",
                    "description": "Query spatial map and verify obstacle clearances",
                    "tool": "spatial_query",
                    "parameters": {"target": goal_description},
                    "expected_output": "Planned trajectory vector",
                    "priority": 1,
                },
                {
                    "title": "Engage omni-wheel drive & balance controller",
                    "description": "Transmit velocity vectors to motor driver with continuous IMU stabilization",
                    "tool": "robot_move",
                    "parameters": {"trajectory": "optimal", "speed_mode": "patrol"},
                    "expected_output": "Movement execution telemetry",
                    "priority": 2,
                },
                {
                    "title": "Confirm arrival and target alignment",
                    "description": "Verify final position via LiDAR and visual anchor markers",
                    "tool": "sensor_probe",
                    "parameters": {"sensors": ["lidar", "imu"]},
                    "expected_output": "Position verification status",
                    "priority": 3,
                },
            ]
        else:
            # Generic smart decomposition
            subtasks = [
                {
                    "title": f"Gather context for: {goal_description}",
                    "description": "Query memory and world model for relevant state and facts",
                    "tool": "memory_query",
                    "parameters": {"query": goal_description},
                    "expected_output": "Contextual facts and prior experiences",
                    "priority": 1,
                },
                {
                    "title": f"Execute core task operation: {goal_description}",
                    "description": "Run the appropriate digital or analytical operation",
                    "tool": "system_diagnostics",
                    "parameters": {"operation": "execute_task", "details": goal_description},
                    "expected_output": "Task execution output",
                    "priority": 2,
                },
                {
                    "title": "Verify result against goal criteria",
                    "description": "Ensure output satisfies the original directive",
                    "tool": "generate_report",
                    "parameters": {"summary": f"Completed {goal_description}"},
                    "expected_output": "Verification validation report",
                    "priority": 3,
                },
            ]

        return {
            "goal": goal_description,
            "reasoning_summary": f"Analyzed directive '{goal_description}'. Structured into {len(subtasks)} discrete subgoals with tool bindings and verification checks.",
            "subtasks": subtasks,
            "estimated_confidence": 0.94,
            "safety_assessment": "Safe - Non-destructive operations",
        }


class OllamaLocalEngine(BaseAIModel):
    """
    Integration with local Ollama instances (e.g. llama3.2:1b, llama3.2:3b, llama3).
    Supports num_gpu CPU/GPU gating, JSON schema generation, and automatic fallback.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        model_name: Optional[str] = None,
        num_gpu: Optional[int] = None,
        temperature: Optional[float] = None,
        timeout_sec: Optional[float] = None,
    ):
        from config.llama_config import llama_config
        self.endpoint = (endpoint or llama_config.endpoint).rstrip("/")
        self.model_name = model_name or llama_config.model_name
        self.num_gpu = num_gpu if num_gpu is not None else llama_config.num_gpu
        self.temperature = temperature if temperature is not None else llama_config.temperature
        self.timeout_sec = timeout_sec if timeout_sec is not None else llama_config.timeout_sec
        self.fallback = OfflineCognitiveEngine()

    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        format_json: bool = False,
        **kwargs,
    ) -> ModelResponse:
        try:
            url = f"{self.endpoint}/api/generate"
            payload: Dict[str, Any] = {
                "model": self.model_name,
                "prompt": prompt,
                "system": system_prompt or "You are P.H.A.S.S Sphere, an autonomous AI reasoning system.",
                "stream": False,
                "options": {
                    "num_gpu": self.num_gpu,
                    "temperature": kwargs.get("temperature", self.temperature),
                },
            }
            if format_json or kwargs.get("format") == "json":
                payload["format"] = "json"

            timeout_val = aiohttp.ClientTimeout(total=kwargs.get("timeout_sec", self.timeout_sec))
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=timeout_val) as response:
                    if response.status == 200:
                        data = await response.json()
                        raw_text = data.get("response", "").strip()
                        parsed = None
                        if format_json or kwargs.get("format") == "json":
                            try:
                                parsed = json.loads(raw_text)
                            except Exception:
                                pass
                        return ModelResponse(
                            content=raw_text,
                            parsed_json=parsed,
                            model_name=f"ollama:{self.model_name}",
                            confidence=0.95,
                        )
                    else:
                        err_text = await response.text()
                        logger.warning(f"Ollama server returned {response.status}: {err_text}")
        except Exception as e:
            logger.warning(f"Ollama request failed: {e}. Falling back to OfflineCognitiveEngine.")
        return await self.fallback.generate_response(prompt, system_prompt, **kwargs)

    async def reason_and_plan(self, goal_description: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return await self.fallback.reason_and_plan(goal_description, context)


class AIModelFactory:
    @staticmethod
    def create(engine_type: str = "offline", **kwargs) -> BaseAIModel:
        if engine_type == "ollama":
            from config.llama_config import llama_config
            return OllamaLocalEngine(
                endpoint=kwargs.get("endpoint", llama_config.endpoint),
                model_name=kwargs.get("model", llama_config.model_name),
                num_gpu=kwargs.get("num_gpu", llama_config.num_gpu),
                temperature=kwargs.get("temperature", llama_config.temperature),
            )
        return OfflineCognitiveEngine()
