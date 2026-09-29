"""
Configuration management for Local Llama Model Integration in P.H.A.S.S Sphere.
Local-first architecture: Executes Llama models directly in-process via PyTorch
and Hugging Face Transformers on CPU, without external background daemons or Ollama.
"""

from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class LlamaConfig:
    """Settings for the local Llama reasoning and intelligence layer."""
    # Model name or local path: default to models/llama (local-first design)
    model_name: str = field(
        default_factory=lambda: os.environ.get("LLAMA_MODEL", "models/llama")
    )

    # Provider: "local_transformers" (pure in-process, zero external daemons), "ollama", or "native"
    provider: str = field(
        default_factory=lambda: os.environ.get("LLAMA_PROVIDER", "local_transformers")
    )

    # Device: "cpu" (standard portable CPU inference) or "cuda"
    device: str = field(
        default_factory=lambda: os.environ.get("LLAMA_DEVICE", "cpu")
    )

    # Torch data type for inference weights
    torch_dtype: str = field(
        default_factory=lambda: os.environ.get("LLAMA_TORCH_DTYPE", "float32")
    )

    # Inference temperature: 0.7 for balanced reasoning and conversational response
    temperature: float = field(
        default_factory=lambda: float(os.environ.get("LLAMA_TEMPERATURE", "0.7"))
    )

    # Max new tokens per generation step
    max_new_tokens: int = field(
        default_factory=lambda: int(os.environ.get("LLAMA_MAX_NEW_TOKENS", "512"))
    )

    # Max tokens alias (kept for backward compatibility)
    max_tokens: int = field(
        default_factory=lambda: int(os.environ.get("LLAMA_MAX_TOKENS", "512"))
    )

    # Maximum reasoning and tool-execution steps before synthesizing final answer
    max_reasoning_steps: int = field(
        default_factory=lambda: int(os.environ.get("LLAMA_MAX_STEPS", "6"))
    )

    # Provider endpoint (used if provider == "ollama")
    endpoint: str = field(
        default_factory=lambda: os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
    )

    # GPU layers: 0 for CPU, 1 requests GPU acceleration if CUDA is available
    num_gpu: int = field(
        default_factory=lambda: int(os.environ.get("LLAMA_NUM_GPU", "0"))
    )

    # Request timeout in seconds
    timeout_sec: float = field(
        default_factory=lambda: float(os.environ.get("LLAMA_TIMEOUT_SEC", "35.0"))
    )

    # Context window limit
    num_ctx: int = field(
        default_factory=lambda: int(os.environ.get("LLAMA_NUM_CTX", "4096"))
    )

    # Enable user preference memory (favorite directories, common commands)
    save_memory: bool = field(
        default_factory=lambda: os.environ.get("LLAMA_SAVE_MEMORY", "true").lower() in ("true", "1", "yes")
    )

    # Path to user preferences JSON file
    preferences_path: str = field(
        default_factory=lambda: os.environ.get("LLAMA_PREFERENCES_PATH", "checkpoints/user_preferences.json")
    )

    # Fallback to native cognitive engine or secondary brain if local model encounters an error
    fallback_enabled: bool = field(
        default_factory=lambda: os.environ.get("LLAMA_FALLBACK", "true").lower() in ("true", "1", "yes")
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "provider": self.provider,
            "device": self.device,
            "torch_dtype": self.torch_dtype,
            "endpoint": self.endpoint,
            "num_gpu": self.num_gpu,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "max_new_tokens": self.max_new_tokens,
            "timeout_sec": self.timeout_sec,
            "num_ctx": self.num_ctx,
            "max_reasoning_steps": self.max_reasoning_steps,
            "save_memory": self.save_memory,
            "preferences_path": self.preferences_path,
            "fallback_enabled": self.fallback_enabled,
        }

    def update_model(self, new_model: str) -> None:
        """Dynamically update model name at runtime."""
        self.model_name = new_model.strip()

    def update_provider(self, new_provider: str) -> None:
        """Dynamically update provider (local_transformers, ollama, native)."""
        self.provider = new_provider.strip().lower()

    def set_temperature(self, temp: float) -> None:
        """Dynamically update generation temperature."""
        self.temperature = max(0.0, min(2.0, float(temp)))


# Global singleton instance
llama_config = LlamaConfig()


def get_config() -> LlamaConfig:
    """Returns the active global LlamaConfig singleton instance."""
    return llama_config
