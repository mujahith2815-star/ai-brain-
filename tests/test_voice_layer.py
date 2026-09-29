"""
Unit tests for Orvix Sphere Voice Layer.
Tests SpeechSynthesizer, SpeechRecognizer, WakeWordDetector, and VoiceLoop.
Designed to run in headless environments with 100% mockable audio interfaces.
"""

import pytest
from unittest.mock import MagicMock, patch
import numpy as np

from config.voice_config import VoiceConfig
from voice.text_to_speech import SpeechSynthesizer
from voice.speech_to_text import SpeechRecognizer
from voice.wake_word import WakeWordDetector
from voice.voice_loop import VoiceLoop


def test_speech_synthesizer_initialization():
    """Test 1: Verifies SpeechSynthesizer rate, volume, and voice configuration."""
    synth = SpeechSynthesizer(rate=190, volume=0.85, voice_id="test_voice")
    try:
        assert synth.rate == 190
        assert synth.volume == 0.85
        assert synth.voice_id == "test_voice"
        synth.set_rate(200)
        assert synth.rate == 200
        synth.set_volume(0.7)
        assert synth.volume == 0.7
    finally:
        synth.close()


def test_speech_synthesizer_speak():
    """Test 2: Verifies speak() queues text non-blockingly and stop() clears state."""
    synth = SpeechSynthesizer(rate=180, volume=0.8)
    try:
        # Mock engine to simulate speech
        mock_engine = MagicMock()
        synth._engine = mock_engine

        res = synth.speak("Hello Orvix testing", block=False)
        assert res is True

        synth.stop()
        assert synth.is_busy is False
    finally:
        synth.close()


def test_speech_recognizer_fallback_when_no_mic():
    """Test 3: Verifies graceful fallback returning None when no microphone is present."""
    recognizer = SpeechRecognizer(model_name="tiny")

    # Patch sounddevice to simulate no input devices
    with patch("sounddevice.query_devices", return_value=[{"name": "Speaker", "max_input_channels": 0}]):
        assert recognizer.is_microphone_available() is False
        # Recording should return None
        audio = recognizer.record_audio(duration=1.0)
        assert audio is None
        # listen_and_transcribe should return None
        text = recognizer.listen_and_transcribe(timeout=1.0)
        assert text is None


def test_wake_word_fallback_to_keyboard():
    """Test 4: Verifies wake word detector fallback mechanism via trigger()."""
    detector = WakeWordDetector(hotkey="ctrl+shift+o")
    try:
        # Should timeout if not triggered
        res_timeout = detector.wait_for_wake_word(timeout=0.1)
        assert res_timeout is False

        # Should return True when trigger() is called
        detector.trigger()
        res_triggered = detector.wait_for_wake_word(timeout=0.5)
        assert res_triggered is True
    finally:
        detector.stop()


def test_voice_loop_config_loading():
    """Test 5: Verifies VoiceLoop properly loads and propagates custom VoiceConfig."""
    custom_cfg = VoiceConfig(
        wake_word="hey test agent",
        whisper_model="base",
        tts_rate=210,
        tts_volume=0.95,
        listen_timeout=8.0,
        fallback_to_text=True
    )
    mock_agent = MagicMock()
    loop = VoiceLoop(agent=mock_agent, config=custom_cfg)
    try:
        assert loop.config.wake_word == "hey test agent"
        assert loop.config.whisper_model == "base"
        assert loop.config.tts_rate == 210
        assert loop.synthesizer.rate == 210
        assert loop.recognizer.config.listen_timeout == 8.0
    finally:
        loop.stop()


def test_voice_loop_text_fallback():
    """Test 6: Verifies seamless fallback to text, agent execution, and conversation logging."""
    mock_agent = MagicMock()
    mock_result = MagicMock()
    mock_result.final_response = "Voice interaction confirmed."
    mock_agent.run.return_value = mock_result

    mock_ks = MagicMock()

    loop = VoiceLoop(
        agent=mock_agent,
        knowledge_store=mock_ks,
    )
    try:
        # Mock microphone unavailable
        loop.recognizer.is_microphone_available = MagicMock(return_value=False)

        # Run step with explicit text fallback
        response = loop.step(text_input_fallback="Status report", mock_wake=True)

        # Agent should have executed query
        mock_agent.run.assert_called_once_with("Status report")
        assert response == "Voice interaction confirmed."

        # KnowledgeStore should have logged both user and assistant turns
        assert mock_ks.log_conversation.call_count == 2
        mock_ks.log_conversation.assert_any_call(
            session_id="voice_session",
            role="user",
            content="Status report"
        )
        mock_ks.log_conversation.assert_any_call(
            session_id="voice_session",
            role="assistant",
            content="Voice interaction confirmed."
        )
    finally:
        loop.stop()
