"""
Unit & Integration Tests for Apex Frontier Capabilities:
Speech Listener, Neural Vision OCR, Proactive Sentinel, Sound Effects, and Computer Automation.
"""

import pytest
from voice.sound_effects import CyberneticSoundSynthesizer
from voice.speech_listener import JARVISVoiceListener
from perception.vision_ai import NeuralVisionAIEngine
from core.proactive_sentinel import ProactiveAutonomicSentinel
from tools.computer_automation import ComputerGUIAutomation
from nlp.conversational_agent import conversational_agent


# 1. Cybernetic Sound Synthesizer
def test_sound_effects_synthesizer():
    synth = CyberneticSoundSynthesizer()
    assert synth.is_enabled is True
    synth.play_sound("SONAR_PING", async_play=False)
    synth.play_sound("ARC_REACTOR_BOOT", async_play=False)

    synth.toggle_sounds(False)
    assert synth.is_enabled is False
    synth.toggle_sounds(True)


# 2. Voice Listener & Wake-Word Detector
def test_speech_listener_and_wake_words():
    listener = JARVISVoiceListener()

    # Injected voice command with wake-word
    res = listener.inject_voice_command("Hey JARVIS, prepare my workspace")
    assert res.text == "Hey JARVIS, prepare my workspace"
    assert res.detected_wake_word in ("hey jarvis", "jarvis")
    assert res.confidence > 0.9

    # Listen once
    res_listen = listener.listen_and_transcribe(timeout_sec=1)
    assert isinstance(res_listen.text, str)
    assert len(res_listen.text) > 0


# 3. Neural Vision & Screen OCR
def test_neural_vision_and_ocr(tmp_path):
    vision = NeuralVisionAIEngine()
    dummy_img = tmp_path / "desktop_screen.png"
    dummy_img.write_text("DUMMY_IMAGE_DATA")

    analysis = vision.analyze_image_or_screenshot(str(dummy_img))
    assert len(analysis.detected_texts) > 0
    assert analysis.dominant_scene_type == "DESKTOP_IDE"
    assert len(analysis.saliency_focal_points) > 0

    plain_txt = vision.extract_plain_text(str(dummy_img))
    assert "P.H.A.S.S" in plain_txt or "Confidence" in plain_txt


# 4. Proactive Autonomic Sentinel
def test_proactive_autonomic_sentinel():
    sentinel = ProactiveAutonomicSentinel()
    sentinel.start_sentinel()
    assert sentinel.is_running is True

    snap = sentinel.get_sentinel_snapshot()
    assert snap["is_sentinel_active"] is True
    assert len(snap["learned_operator_routines"]) >= 2

    # Threshold evaluation
    alert = sentinel.evaluate_proactive_safeguards()
    # Nominal by default
    assert alert is None or alert.severity in ("WARNING", "CRITICAL")
    sentinel.stop_sentinel()


# 5. Computer GUI Automation
def test_computer_gui_automation():
    auto = ComputerGUIAutomation()

    ok_t, msg_t = auto.type_text("PHASS_TEST_INPUT")
    assert ok_t is True

    ok_sc, msg_sc = auto.send_shortcut("COPY")
    assert ok_sc is True

    ok_m, msg_m = auto.click_mouse(100, 100)
    assert ok_m is True
    assert auto.action_count >= 3


# 6. Conversational Apex Directives
def test_conversational_apex_directives():
    # 1. OCR Directive
    res_ocr = conversational_agent.handle_natural_conversation("ocr screenshot")
    assert res_ocr is not None
    assert res_ocr["action_executed"] == "RUN_OCR"

    # 2. GUI Type Automation
    res_type = conversational_agent.handle_natural_conversation("type echo hello")
    assert res_type is not None
    assert res_type["action_executed"] in ("TYPE_TEXT", "INJECT_DESKTOP_KEYSTROKES")

    # 3. Sound Synthesis
    res_snd = conversational_agent.handle_natural_conversation("play sound sonar")
    assert res_snd is not None
    assert res_snd["action_executed"] == "PLAY_SONAR"

    # 4. Sentinel Status
    res_sent = conversational_agent.handle_natural_conversation("sentinel status")
    assert res_sent is not None
    assert res_sent["action_executed"] == "SENTINEL_SNAPSHOT"
