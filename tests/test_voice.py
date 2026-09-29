"""
Unit and Integration Tests for Voice Interface, Voice Tools,
and Llama Voice Integration in P.H.A.S.S Sphere.
"""

import os
import time
from unittest.mock import MagicMock, patch
import numpy as np
import pytest

from core.voice_interface import VoiceInterface, get_voice_interface
from tools.voice_tools import (
    listen_for_command,
    speak_response,
    speak_async,
    set_voice_rate,
    set_voice_volume,
    set_voice_gender,
    list_available_voices,
    wait_for_wake_word,
    start_continuous_mode,
    stop_continuous_mode,
    get_voice_status,
    VOICE_TOOLS,
)
from tools.registry import tool_registry
from core.llama_tool_agent import llama_tool_agent


class TestVoiceInterface:
    def test_voice_interface_initialization(self):
        """Verify VoiceInterface initializes with valid default parameters and status."""
        vi = VoiceInterface(wake_word="llama", rate=180, volume=0.8)
        assert vi.wake_word == "llama"
        assert vi.rate == 180
        assert vi.volume == 0.8
        status = vi.get_status()
        assert "stt_available" in status
        assert "tts_available" in status
        assert "wake_word_available" in status
        assert status["rate"] == 180
        assert status["volume"] == 0.8

    def test_set_rate_and_volume(self):
        """Verify rate and volume setters update properties and TTS engine."""
        vi = VoiceInterface()
        res_rate = vi.set_rate(220)
        assert vi.rate == 220
        assert "220" in res_rate

        res_vol = vi.set_volume(0.9)
        assert vi.volume == 0.9
        assert "90%" in res_vol

        # Test boundary clamping
        vi.set_volume(1.5)
        assert vi.volume == 1.0
        vi.set_volume(-0.5)
        assert vi.volume == 0.0

    def test_list_voices_and_set_voice(self):
        """Verify listing and switching voices."""
        vi = VoiceInterface()
        voices = vi.list_voices()
        assert isinstance(voices, list)
        if voices:
            first_id = voices[0]["id"]
            set_res = vi.set_voice(first_id)
            assert "Voice set to" in set_res
            assert vi.voice_id == first_id

    def test_text_to_speech_speak_and_async(self):
        """Verify TTS speak and speak_async methods."""
        vi = VoiceInterface()
        # Empty text
        assert vi.speak("") == "Nothing to speak."
        assert vi.speak("   ") == "Nothing to speak."

        # Mock tts_engine to verify call sequence without blocking hardware
        mock_engine = MagicMock()
        with patch.object(vi, "tts_engine", mock_engine):
            res = vi.speak("Welcome to P.H.A.S.S voice system.", async_mode=False)
            assert "Spoke:" in res
            mock_engine.say.assert_called_with("Welcome to P.H.A.S.S voice system.")
            mock_engine.runAndWait.assert_called_once()

    def test_transcription_with_mock_stt(self):
        """Verify audio transcription formats and temp file handling."""
        vi = VoiceInterface()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "Hello Llama assistant"}

        # Create dummy float32 audio data (1 second at 16kHz)
        dummy_audio = np.zeros(16000, dtype=np.float32)

        with patch.object(vi, "stt_model", mock_model):
            text = vi.transcribe(dummy_audio)
            assert text == "Hello Llama assistant"
            mock_model.transcribe.assert_called_once()

    def test_wake_word_and_continuous_listening_lifecycle(self):
        """Verify continuous listening mode background thread start and stop."""
        vi = VoiceInterface()
        callback_called = False

        def mock_callback(text):
            nonlocal callback_called
            callback_called = True

        msg = vi.start_continuous_listening(mock_callback)
        assert "continuous listening" in msg.lower()
        assert vi.is_listening is True

        stop_msg = vi.stop_listening()
        assert "Stopped listening" in stop_msg
        assert vi.is_listening is False


class TestVoiceTools:
    def test_voice_tools_dictionary_definitions(self):
        """Verify all requested voice tools are defined in VOICE_TOOLS."""
        required_tools = [
            "listen_for_command",
            "speak_response",
            "speak_async",
            "set_voice_rate",
            "set_voice_volume",
            "set_voice_gender",
            "list_available_voices",
            "wait_for_wake_word",
            "start_continuous_mode",
            "stop_continuous_mode",
            "get_voice_status",
        ]
        for tool_name in required_tools:
            assert tool_name in VOICE_TOOLS
            assert callable(VOICE_TOOLS[tool_name]["function"])
            assert len(VOICE_TOOLS[tool_name]["description"]) > 0

    def test_speak_response_and_async(self):
        """Verify speak_response tool handles inputs."""
        assert speak_response("") == "Nothing to speak."
        with patch.object(get_voice_interface(), "speak", return_value="Spoke: Testing voice..."):
            res = speak_response("Testing voice tools")
            assert "Spoke:" in res

    def test_voice_rate_and_volume_tools(self):
        """Verify set_voice_rate and set_voice_volume wrapper tools."""
        res_rate = set_voice_rate(190)
        assert "190" in res_rate

        res_vol = set_voice_volume(85)
        assert "85%" in res_vol

    def test_voice_gender_and_listing(self):
        """Verify voice gender selection and available voices listing."""
        voices_str = list_available_voices()
        assert isinstance(voices_str, str)

        gender_res = set_voice_gender("female")
        assert isinstance(gender_res, str)

    def test_voice_status_tool(self):
        """Verify get_voice_status tool returns structured dict."""
        status = get_voice_status()
        assert isinstance(status, dict)
        assert "stt_available" in status
        assert "tts_available" in status

    def test_continuous_mode_tools(self):
        """Verify starting and stopping continuous mode via tools."""
        start_msg = start_continuous_mode()
        assert "Continuous listening started" in start_msg
        stop_msg = stop_continuous_mode()
        assert "Stopped listening" in stop_msg


class TestBuiltinToolsRegistryIntegration:
    def test_voice_tools_registered_in_registry(self):
        """Verify voice tools are registered in tool_registry."""
        tools = tool_registry.list_tools()
        tool_names = [t["name"] for t in tools]
        assert "listen_for_command" in tool_names
        assert "speak_response" in tool_names
        assert "set_voice_speed" in tool_names
        assert "set_voice_volume" in tool_names
        assert "wake_word_detection" in tool_names

    @pytest.mark.asyncio
    async def test_speak_response_execution_via_registry(self):
        """Verify speak_response executes properly through tool_registry."""
        handler = tool_registry.get("speak_response").handler
        with patch("tools.voice_tools.speak_response", return_value="Spoke: Registered test"):
            res = await handler(text="Registered test")
            assert res["status"] == "SUCCESS"
            assert "Registered test" in res["message"]

    @pytest.mark.asyncio
    async def test_set_voice_speed_and_volume_via_registry(self):
        """Verify set_voice_speed and set_voice_volume execution."""
        speed_handler = tool_registry.get("set_voice_speed").handler
        vol_handler = tool_registry.get("set_voice_volume").handler

        s_res = await speed_handler(rate=210)
        assert s_res["status"] == "SUCCESS"

        v_res = await vol_handler(level=70)
        assert v_res["status"] == "SUCCESS"


class TestLlamaAgentVoiceIntegration:
    def test_agent_routes_speak_command(self):
        """Verify Llama agent dispatches speak_response for speak directives."""
        with patch("tools.voice_tools.speak_response", return_value="Spoke: Good morning!"):
            res = llama_tool_agent.run_turn("Speak Good morning!")
            assert res.success is True
            assert any(s.tool_name == "speak_response" for s in res.steps_executed)

    def test_agent_routes_set_voice_speed(self):
        """Verify Llama agent dispatches set_voice_speed."""
        res = llama_tool_agent.run_turn("Set voice speed to 250")
        assert res.success is True
        assert any(s.tool_name == "set_voice_speed" for s in res.steps_executed)

    def test_agent_routes_set_voice_volume(self):
        """Verify Llama agent dispatches set_voice_volume."""
        res = llama_tool_agent.run_turn("Set voice volume to 95")
        assert res.success is True
        assert any(s.tool_name == "set_voice_volume" for s in res.steps_executed)

    def test_agent_routes_listen_command(self):
        """Verify Llama agent dispatches listen_for_command."""
        with patch("tools.voice_tools.listen_for_command", return_value="Command: check system status"):
            res = llama_tool_agent.run_turn("Listen for command")
            assert res.success is True
            assert any(s.tool_name == "listen_for_command" for s in res.steps_executed)

    def test_agent_routes_wake_word_detection(self):
        """Verify Llama agent dispatches wake_word_detection."""
        with patch("tools.voice_tools.wait_for_wake_word", return_value="Command: open browser"):
            res = llama_tool_agent.run_turn("Wait for wake word Hey Llama")
            assert res.success is True
            assert any(s.tool_name == "wake_word_detection" for s in res.steps_executed)

    def test_system_prompt_includes_voice_features(self):
        """Verify system prompt contains voice capabilities."""
        catalog = llama_tool_agent.get_tool_catalog_prompt()
        assert "speak_response" in catalog
        assert "listen_for_command" in catalog
        assert "set_voice_speed" in catalog
        assert "set_voice_volume" in catalog
        assert "wake_word_detection" in catalog


# =============================================================================
# Direct Top-Level Voice Tests Matching User Specifications
# =============================================================================
def test_voice_interface_creation():
    """Test that voice interface can be created."""
    voice = VoiceInterface(wake_word="test")
    assert voice.wake_word == "test"
    assert voice.is_listening is False


def test_voice_status():
    """Test status reporting."""
    voice = VoiceInterface()
    status = voice.get_status()
    assert "stt_available" in status
    assert "tts_available" in status
    assert "wake_word_available" in status
    assert "is_listening" in status


@pytest.mark.skipif(True, reason="Requires microphone")
def test_record_audio():
    """Test audio recording (requires mic)."""
    voice = VoiceInterface()
    audio = voice.record_audio(duration=0.5)
    assert audio is not None
    assert len(audio) > 0


@pytest.mark.skipif(True, reason="Requires TTS")
def test_tts():
    """Test TTS (may require audio output)."""
    voice = VoiceInterface()
    result = voice.speak("Test", async_mode=False)
    assert "Spoke" in result or "TTS" in result


def test_list_voices():
    """Test voice listing."""
    voice = VoiceInterface()
    voices = voice.list_voices()
    assert isinstance(voices, list)


def test_process_query():
    """Test text query processing helper in run_model_chat."""
    from run_model_chat import process_query
    res = process_query("Hello there")
    assert isinstance(res, str)
    assert len(res) > 0


def test_process_voice_command():
    """Test voice command execution helper in run_model_chat."""
    from run_model_chat import process_voice_command
    with patch("core.voice_interface.VoiceInterface.speak", return_value="Spoke: test"):
        res = process_voice_command("What is your status?")
        assert isinstance(res, str)
        assert len(res) > 0


