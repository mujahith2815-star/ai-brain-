"""
Unit and Integration Tests for Google Gemini Flash Engine & Model Router (v1.3.0).
Uses comprehensive mocks so all tests execute offline without requiring a real API key or internet access.
"""

import os
import time
from unittest.mock import MagicMock, patch
import pytest

from config.api_config import api_config
from tools.api_cost_tracker import api_cost_tracker, ApiCostTracker
from tools.gemini_engine import GeminiEngine, gemini_engine
from tools.model_router import ModelRouter, model_router
from core.llama_tool_agent import llama_tool_agent


class TestGeminiEngineAndRouter:

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Resets router mode and cost tracker before and after each test."""
        orig_mode = api_config.model_mode
        orig_key = api_config.gemini_api_key
        api_cost_tracker.reset_usage_for_test()
        yield
        api_config.set_mode(orig_mode)
        api_config.set_key(orig_key)
        api_cost_tracker.reset_usage_for_test()

    def test_mode_switching(self):
        """Verifies router mode switching and validation."""
        router = ModelRouter()
        
        # Valid switches
        for mode in ["auto", "cloud_only", "local_only", "cloud_first"]:
            res = router.switch_mode(mode)
            assert res == mode
            assert router.current_mode == mode

        # Invalid mode
        with pytest.raises(ValueError) as exc:
            router.switch_mode("quantum_neural_mode")
        assert "Unknown model routing mode" in str(exc.value)

    def test_router_chooses_cloud_when_available(self):
        """Verifies router selects Gemini when key is present and cloud is preferred."""
        mock_gemini = MagicMock(spec=GeminiEngine)
        mock_gemini.is_available.return_value = True
        mock_gemini.model_name = "gemini-2.0-flash"

        router = ModelRouter(gemini=mock_gemini)

        # 1. cloud_first with cloud available -> gemini
        router.switch_mode("cloud_first")
        assert router.route("What is the capital of France?") == "gemini"

        # 2. auto mode with complex query -> gemini
        router.switch_mode("auto")
        assert router.route("Read document notes.txt, calculate total, and write to report.md") == "gemini"

        # 3. auto mode with simple greeting -> local
        assert router.route("hello") == "local"

        # 4. local_only mode -> local even if cloud is available
        router.switch_mode("local_only")
        assert router.route("Deep complex mathematical derivation") == "local"

    def test_router_falls_back_to_local_when_cloud_unavailable(self):
        """Verifies router transparently defaults to local when cloud is offline or key missing."""
        mock_gemini = MagicMock(spec=GeminiEngine)
        mock_gemini.is_available.return_value = False

        router = ModelRouter(gemini=mock_gemini)
        router.switch_mode("cloud_first")

        # Cloud not available -> falls back to local
        assert router.route("Complex query requiring advanced reasoning") == "local"

        # In cloud_only mode, missing cloud raises RuntimeError
        router.switch_mode("cloud_only")
        with pytest.raises(RuntimeError) as exc:
            router.route("Any query")
        assert "cloud_only" in str(exc.value)

    def test_router_falls_back_to_local_on_api_failure(self):
        """Verifies that when Gemini execution raises an exception, the agent falls back to local."""
        with patch.object(gemini_engine, "is_available", return_value=True):
            with patch.object(gemini_engine, "generate", side_effect=RuntimeError("Simulated 429 Rate Limit")):
                with patch.object(llama_tool_agent, "_query_qwen_json", return_value=None):
                    with patch.object(llama_tool_agent, "_query_llama_json", return_value={"action": "final_answer", "response": "30"}):
                        # Query unified engine router
                        decision, actual_model, was_fallback = llama_tool_agent._query_engine_json(
                            prompt="Calculate 10 + 20",
                            system_prompt="System instructions",
                            route_target="gemini",
                        )
                        assert was_fallback is True
                        assert decision == {"action": "final_answer", "response": "30"}

    def test_api_cost_tracker_logs_usage(self):
        """Verifies SQLite recording of tokens, requests, and daily aggregation."""
        api_cost_tracker.reset_usage_for_test()

        # Log two API calls
        api_cost_tracker.log_request("gemini-2.0-flash", tokens_in=120, tokens_out=80, cost=0.0)
        api_cost_tracker.log_request("gemini-2.0-flash", tokens_in=200, tokens_out=150, cost=0.0)

        usage = api_cost_tracker.get_usage_today()
        assert usage["requests_today"] == 2
        assert usage["tokens_in"] == 320
        assert usage["tokens_out"] == 230
        assert usage["total_tokens"] == 550
        assert usage["estimated_cost_usd"] == 0.0
        assert usage["rpm_limit"] == 14

    def test_rate_limit_handling(self):
        """Verifies rate limiter window blocks and enforces wait time after quota."""
        tracker = ApiCostTracker()
        tracker.reset_usage_for_test()

        max_allowed = 3
        # First 3 should succeed
        for _ in range(max_allowed):
            allowed, wait = tracker.check_rate_limit(max_rpm=max_allowed)
            assert allowed is True
            assert wait == 0.0
            tracker.record_request_start()

        # 4th request in the same window must be blocked
        allowed, wait = tracker.check_rate_limit(max_rpm=max_allowed)
        assert allowed is False
        assert wait > 0.0

    def test_gemini_engine_generate_and_tools_mock(self):
        """Verifies GeminiEngine parses structured tool actions from model responses."""
        engine = GeminiEngine(api_key="mock_key_test_123")

        mock_response = MagicMock()
        mock_response.text = '{"actions": [{"tool": "advanced_calculator", "args": {"expression": "25 * 4"}}]}'

        with patch.object(engine, "is_available", return_value=True):
            with patch("google.generativeai.GenerativeModel") as MockModel:
                mock_inst = MagicMock()
                mock_inst.generate_content.return_value = mock_response
                MockModel.return_value = mock_inst
                engine._model = mock_inst

                res = engine.generate_with_tools("Calculate 25 times 4")
                assert res["has_tools"] is True
                assert len(res["tool_calls"]) == 1
                assert res["tool_calls"][0]["tool"] == "advanced_calculator"
                assert res["tool_calls"][0]["args"]["expression"] == "25 * 4"

    def test_gemini_engine_count_tokens(self):
        """Verifies token counting heuristic and tokenizer interface."""
        engine = GeminiEngine(api_key="mock_key_123")
        
        # Test heuristic count
        count = engine.count_tokens("This is a test prompt with eight words here.")
        assert isinstance(count, int)
        assert count >= 8

    def test_gemini_engine_404_auto_fallback(self):
        """Verifies that on 404/NotFound error, GeminiEngine cascades to the next candidate model."""
        engine = GeminiEngine(api_key="mock_key_test_123", model_name="gemini-2.0-flash")

        mock_404 = Exception("404 models/gemini-2.0-flash is not found for API version v1beta")
        mock_success_response = MagicMock()
        mock_success_response.text = "Success from fallback model"

        model_created_names = []

        def side_effect_model(model_name, **kwargs):
            model_created_names.append(model_name)
            mock_inst = MagicMock()
            if model_name == "gemini-2.0-flash":
                mock_inst.generate_content.side_effect = mock_404
            else:
                mock_inst.generate_content.return_value = mock_success_response
            return mock_inst

        with patch.object(engine, "is_available", return_value=True):
            with patch("google.generativeai.GenerativeModel", side_effect=side_effect_model):
                res = engine.generate("Hello world")
                assert res == "Success from fallback model"
                assert "gemini-2.0-flash" in model_created_names
                assert len(model_created_names) >= 2
                assert engine.model_name != "gemini-2.0-flash"
