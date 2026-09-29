"""
Unit tests for QwenEngine (Local Qwen2.5-7B on W: drive via Ollama).
Tests initialization, availability checks, CPU mode enforcement, and mock tool execution.
"""

from unittest.mock import MagicMock, patch
import pytest

from tools.qwen_engine import QwenEngine


def test_qwen_initialization():
    """Verifies QwenEngine initializes with target model and CPU safety options."""
    engine = QwenEngine(model_name="qwen2.5:7b-instruct-q4_K_M", force_cpu=True)
    assert engine.name == "qwen"
    assert engine.model_name == "qwen2.5:7b-instruct-q4_K_M"
    assert engine.force_cpu is True
    opts = engine._get_options()
    assert opts.get("num_gpu") == 0


def test_qwen_available_when_ollama_running():
    """Verifies is_available returns True when Ollama has the model tagged."""
    engine = QwenEngine()
    with patch("tools.qwen_engine.is_ollama_service_running", return_value=True):
        with patch("tools.qwen_engine.list_models", return_value=[{"name": "qwen2.5:7b-instruct-q4_K_M:latest"}]):
            assert engine.is_available() is True


def test_qwen_unavailable_when_ollama_stopped():
    """Verifies is_available returns False when Ollama daemon is down."""
    engine = QwenEngine()
    with patch("tools.qwen_engine.is_ollama_service_running", return_value=False):
        assert engine.is_available() is False


def test_qwen_generate_mock():
    """Verifies textual generation via mock Ollama HTTP response."""
    engine = QwenEngine()
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"response": "I am Orvix running on Qwen2.5-7B.", "done": true}'
    mock_resp.__enter__.return_value = mock_resp

    with patch.object(engine, "is_available", return_value=True):
        with patch("urllib.request.urlopen", return_value=mock_resp):
            ans = engine.generate("Who are you?")
            assert "Orvix" in ans
            assert "Qwen2.5-7B" in ans


def test_qwen_tool_calling_mock():
    """Verifies tool parsing from structured JSON emitted by Qwen."""
    engine = QwenEngine()
    json_str = '{"actions": [{"tool": "advanced_calculator", "args": {"expression": "100 * 5"}}]}'
    mock_resp = MagicMock()
    mock_resp.read.return_value = ('{"response": ' + f'"{json_str}"' + ', "done": true}').encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch.object(engine, "is_available", return_value=True):
        with patch.object(engine, "generate", return_value=json_str):
            res = engine.generate_with_tools("Calculate 100 times 5")
            assert res["has_tools"] is True
            assert len(res["tool_calls"]) == 1
            assert res["tool_calls"][0]["tool"] == "advanced_calculator"
