"""
API Configuration for Google Gemini Flash & Model Routing in Orvix Sphere.
Manages API keys, model selection, routing preferences, rate limits, and fallback behavior.
"""

from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

# Attempt to load .env from project root if available
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path, override=False)
except Exception:
    pass


# Primary model name and candidate fallback models for Gemini API
GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip()
GEMINI_FALLBACK_MODELS: List[str] = [
    "gemini-2.0-flash-001",
    "gemini-1.5-flash-002",
    "gemini-1.5-pro",
]


@dataclass
class ApiConfig:
    """Configuration for Cloud AI models, API keys, and routing."""
    
    # API Key: loaded from GEMINI_API_KEY environment variable or .env
    gemini_api_key: str = field(
        default_factory=lambda: os.environ.get("GEMINI_API_KEY", "").strip()
    )

    # Primary model choice
    default_model: str = field(
        default_factory=lambda: os.environ.get("GEMINI_MODEL", GEMINI_MODEL).strip()
    )

    # Candidate fallback models if primary model is unavailable
    fallback_models: List[str] = field(
        default_factory=lambda: list(GEMINI_FALLBACK_MODELS)
    )

    # Routing mode: "cloud_first", "auto", "cloud_only", "local_only"
    model_mode: str = field(
        default_factory=lambda: os.environ.get("MODEL_MODE", "cloud_first").strip().lower()
    )

    # Offline / local fallback toggle
    fallback_enabled: bool = field(
        default_factory=lambda: os.environ.get("FALLBACK_ENABLED", "true").lower() in ("true", "1", "yes")
    )

    # Maximum retry attempts on transient network or rate limit errors
    max_retries: int = field(
        default_factory=lambda: int(os.environ.get("GEMINI_MAX_RETRIES", "3"))
    )

    # Rate limiting buffer (Free tier limit is 15 RPM; 14 RPM provides safety cushion)
    rate_limit_rpm: int = field(
        default_factory=lambda: int(os.environ.get("RATE_LIMIT_RPM", "14"))
    )

    # Daily token allowance tracking
    cost_tracking: bool = field(
        default_factory=lambda: os.environ.get("COST_TRACKING", "true").lower() in ("true", "1", "yes")
    )

    # Request timeout in seconds
    timeout_sec: float = field(
        default_factory=lambda: float(os.environ.get("GEMINI_TIMEOUT_SEC", "30.0"))
    )

    def refresh_key(self) -> str:
        """Refreshes API key from environment variable."""
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        return self.gemini_api_key

    def set_key(self, key: str) -> None:
        """Sets API key in memory and in the environment."""
        clean_key = key.strip()
        self.gemini_api_key = clean_key
        os.environ["GEMINI_API_KEY"] = clean_key

    def set_mode(self, mode: str) -> str:
        """Sets and validates routing mode."""
        valid_modes = {"auto", "cloud_only", "local_only", "cloud_first", "local_first"}
        clean = mode.strip().lower()
        if clean not in valid_modes:
            raise ValueError(f"Invalid mode '{mode}'. Must be one of: {', '.join(sorted(valid_modes))}")
        self.model_mode = clean
        os.environ["MODEL_MODE"] = clean
        return self.model_mode

    def has_valid_key(self) -> bool:
        """Checks if a valid non-empty API key is present."""
        return bool(self.gemini_api_key and len(self.gemini_api_key) > 5)

    def to_dict(self) -> dict:
        return {
            "has_api_key": self.has_valid_key(),
            "default_model": self.default_model,
            "model_mode": self.model_mode,
            "fallback_enabled": self.fallback_enabled,
            "max_retries": self.max_retries,
            "rate_limit_rpm": self.rate_limit_rpm,
            "cost_tracking": self.cost_tracking,
            "timeout_sec": self.timeout_sec,
        }


# Singleton configuration instance
api_config = ApiConfig()
