"""
User Preferences and Personalization Loader.
"""

import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List

CONFIG_PATH = Path("config/user_config.json")

@dataclass
class UserConfig:
    user_name: str = "Operator"
    preferred_model: str = "unsloth/Llama-3.2-1B-Instruct"
    enable_voice: bool = True
    enable_web: bool = True
    watch_folders: List[str] = field(default_factory=lambda: ["knowledge/inbox", "Downloads"])

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def load(cls) -> "UserConfig":
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return cls(**data)
            except Exception:
                pass
        return cls()

    def save(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

user_config = UserConfig.load()

# =====================================================================
# W: Drive Storage Architecture & Directory Configuration (v1.4.0)
# =====================================================================
import logging
import os

_logger = logging.getLogger("orvix.config.storage")

MODELS_ROOT = "W:/PHASS_MEMORY/models"
OLLAMA_HOME = "W:/PHASS_MEMORY/ollama"
CACHE_DIR = "W:/PHASS_MEMORY/cache"
LOGS_DIR = "W:/PHASS_MEMORY/logs"

FALLBACK_ROOT = Path(__file__).resolve().parent.parent / "storage_fallback"


def is_w_drive_available() -> bool:
    """Checks whether the W: drive is mounted, accessible, and writable."""
    w_path = Path("W:/")
    if not w_path.exists():
        return False
    try:
        # Check write permissions with probe file
        test_file = Path("W:/PHASS_MEMORY/.write_probe")
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("probe", encoding="utf-8")
        if test_file.exists():
            test_file.unlink()
        return True
    except Exception:
        return False


def get_storage_paths() -> Dict[str, Path]:
    """
    Resolves storage directories. Prefers W: drive; falls back to C: project
    directory if W: drive is missing or not writable.
    """
    if is_w_drive_available():
        return {
            "models_root": Path(MODELS_ROOT),
            "qwen_model": Path(MODELS_ROOT) / "qwen2.5-7b",
            "ollama_home": Path(OLLAMA_HOME),
            "cache_dir": Path(CACHE_DIR),
            "logs_dir": Path(LOGS_DIR),
            "is_fallback": False,
        }

    _logger.warning(
        "[StorageWarning] W: drive is unavailable or not writable! "
        f"Falling back to C: disk ({FALLBACK_ROOT}). Disk space may be limited."
    )
    return {
        "models_root": FALLBACK_ROOT / "models",
        "qwen_model": FALLBACK_ROOT / "models" / "qwen2.5-7b",
        "ollama_home": FALLBACK_ROOT / "ollama",
        "cache_dir": FALLBACK_ROOT / "cache",
        "logs_dir": FALLBACK_ROOT / "logs",
        "is_fallback": True,
    }


def ensure_storage_directories() -> Dict[str, Path]:
    """Ensures all target model, ollama, cache, and log directories exist."""
    paths = get_storage_paths()
    for key, path in paths.items():
        if isinstance(path, Path):
            path.mkdir(parents=True, exist_ok=True)
    return paths
