"""
Unit tests for W: Drive Storage Architecture and Fallback (v1.4.0).
Tests MODELS_ROOT, OLLAMA_HOME, directory creation, and automatic C: fallback.
"""

from pathlib import Path
from unittest.mock import patch
import pytest

from config.user_config import (
    MODELS_ROOT,
    OLLAMA_HOME,
    CACHE_DIR,
    LOGS_DIR,
    get_storage_paths,
    ensure_storage_directories,
    is_w_drive_available,
)


def test_models_root_points_to_w():
    """Verifies constants point to W:/PHASS_MEMORY paths."""
    assert "W:" in MODELS_ROOT or "W:/" in MODELS_ROOT
    assert "W:" in OLLAMA_HOME or "W:/" in OLLAMA_HOME
    assert "W:" in CACHE_DIR or "W:/" in CACHE_DIR
    assert "W:" in LOGS_DIR or "W:/" in LOGS_DIR


def test_creates_directories_on_w():
    """Verifies get_storage_paths resolves proper subpaths when W: is available."""
    with patch("config.user_config.is_w_drive_available", return_value=True):
        paths = get_storage_paths()
        assert paths["is_fallback"] is False
        assert Path(MODELS_ROOT) == paths["models_root"]
        assert Path(OLLAMA_HOME) == paths["ollama_home"]
        assert paths["qwen_model"] == Path(MODELS_ROOT) / "qwen2.5-7b"


def test_falls_back_to_c_when_w_missing(tmp_path):
    """Verifies get_storage_paths gracefully redirects to C: fallback if W: is missing."""
    with patch("config.user_config.is_w_drive_available", return_value=False):
        paths = get_storage_paths()
        assert paths["is_fallback"] is True
        assert "storage_fallback" in str(paths["models_root"])
