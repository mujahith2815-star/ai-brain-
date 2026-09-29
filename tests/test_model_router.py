"""
Unit tests for ModelRouter (v1.4.0 Hybrid Dual-Engine).
Mocks both Gemini and Qwen engines to test routing logic, fallback behavior,
mode switching, and rate limit redirection completely offline.
"""

from unittest.mock import MagicMock, patch
import pytest

from config.api_config import api_config
from tools.api_cost_tracker import api_cost_tracker
from tools.gemini_engine import GeminiEngine
from tools.qwen_engine import QwenEngine
from tools.model_router import ModelRouter


@pytest.fixture(autouse=True)
def reset_router_state():
    orig_mode = api_config.model_mode
    api_cost_tracker.reset_usage_for_test()
    yield
    api_config.set_mode(orig_mode)
    api_cost_tracker.reset_usage_for_test()


def test_router_auto_mode():
    """In auto mode: routes trivial queries to local Qwen, complex to Gemini."""
    mock_gemini = MagicMock(spec=GeminiEngine)
    mock_gemini.is_available.return_value = True
    mock_gemini.name = "gemini"

    mock_qwen = MagicMock(spec=QwenEngine)
    mock_qwen.is_available.return_value = True
    mock_qwen.name = "qwen"

    router = ModelRouter(gemini=mock_gemini, qwen=mock_qwen, default_mode="auto")
    router.switch_mode("auto")

    # Trivial -> Qwen
    engine = router.route("hello")
    assert engine == "qwen" or engine.name == "qwen"

    # Complex multi-step task -> Gemini
    engine = router.route("Read document notes.txt, calculate average, and write report to file")
    assert engine == "gemini" or engine.name == "gemini"


def test_router_cloud_first_when_available():
    """In cloud_first mode: prefers Gemini for all tasks when online."""
    mock_gemini = MagicMock(spec=GeminiEngine)
    mock_gemini.is_available.return_value = True
    mock_gemini.name = "gemini"

    mock_qwen = MagicMock(spec=QwenEngine)
    mock_qwen.is_available.return_value = True
    mock_qwen.name = "qwen"

    router = ModelRouter(gemini=mock_gemini, qwen=mock_qwen)
    router.switch_mode("cloud_first")

    engine = router.route("What is the capital of Japan?")
    assert engine == "gemini" or engine.name == "gemini"


def test_router_falls_back_to_local_on_network_error():
    """When Gemini is offline / network down, auto and cloud_first fall back to local Qwen."""
    mock_gemini = MagicMock(spec=GeminiEngine)
    mock_gemini.is_available.return_value = False
    mock_gemini.name = "gemini"

    mock_qwen = MagicMock(spec=QwenEngine)
    mock_qwen.is_available.return_value = True
    mock_qwen.name = "qwen"

    router = ModelRouter(gemini=mock_gemini, qwen=mock_qwen)
    router.switch_mode("cloud_first")

    engine = router.route("Complex physics simulation calculation")
    assert engine == "qwen" or engine.name == "qwen"
    assert router._routing_stats["fallbacks_triggered"] >= 1


def test_router_falls_back_to_cloud_when_local_missing():
    """In local_first mode: falls back to Gemini if Qwen is offline or uninstalled."""
    mock_gemini = MagicMock(spec=GeminiEngine)
    mock_gemini.is_available.return_value = True
    mock_gemini.name = "gemini"

    mock_qwen = MagicMock(spec=QwenEngine)
    mock_qwen.is_available.return_value = False
    mock_qwen.name = "qwen"

    router = ModelRouter(gemini=mock_gemini, qwen=mock_qwen)
    router.switch_mode("local_first")

    engine = router.route("Any prompt")
    assert engine == "gemini" or engine.name == "gemini"
    assert router._routing_stats["fallbacks_triggered"] >= 1


def test_mode_switching_persists():
    """Verifies mode switching validates modes and persists to config."""
    router = ModelRouter()

    valid_modes = ["auto", "cloud_first", "local_first", "cloud_only", "local_only"]
    for m in valid_modes:
        res = router.switch_mode(m)
        assert res == m
        assert router.current_mode == m
        assert api_config.model_mode == m

    with pytest.raises(ValueError):
        router.switch_mode("invalid_hyperspace_mode")


def test_rate_limit_redirects_to_local():
    """When Gemini rate limit window is exhausted, router redirects to local Qwen."""
    mock_gemini = MagicMock(spec=GeminiEngine)
    mock_gemini.is_available.return_value = True
    mock_gemini.name = "gemini"

    mock_qwen = MagicMock(spec=QwenEngine)
    mock_qwen.is_available.return_value = True
    mock_qwen.name = "qwen"

    router = ModelRouter(gemini=mock_gemini, qwen=mock_qwen)
    router.switch_mode("auto")

    # Mock rate limit exhausted
    with patch.object(api_cost_tracker, "check_rate_limit", return_value=(False, 12.5)):
        engine = router.route("Complex reasoning task needing cloud")
        assert engine == "qwen" or engine.name == "qwen"
        assert "rate limit" in router._routing_stats["last_reason"].lower()
