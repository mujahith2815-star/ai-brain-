"""
Unit & Integration Tests for J.A.R.V.I.S. Voice, Protocols, Persona, and Screen Vision.
"""

import pytest
from pathlib import Path

from voice.speech_engine import JARVISVoiceEngine
from jarvis.persona import JARVISPersona
from jarvis.protocol_engine import JARVISProtocolEngine
from tools.screen_vision import DesktopScreenVision
from nlp.conversational_agent import conversational_agent


# 1. Voice & Speech Synthesis
def test_voice_speech_engine():
    engine = JARVISVoiceEngine()
    ev = engine.speak("Hello sir, all systems nominal.", non_blocking=True)
    assert ev.text == "Hello sir, all systems nominal."
    assert ev.duration_est_sec > 0.0

    # Mute toggle
    is_muted = engine.toggle_mute(True)
    assert is_muted is True
    ev_muted = engine.speak("Muted message")
    assert ev_muted.was_spoken is False

    engine.toggle_mute(False)
    tel = engine.get_speech_telemetry()
    assert tel["total_phrases_spoken"] >= 2


# 2. JARVIS Persona Formatter
def test_jarvis_persona():
    persona = JARVISPersona()
    greeting = persona.format_greeting("sir")
    assert "sir" in greeting.lower()

    affirmation = persona.format_affirmation()
    assert "sir" in affirmation.lower()

    briefing = persona.format_briefing(
        battery_pct=95.0,
        cpu_load_pct=12.0,
        free_disk_gb=120.0,
        active_goals_count=0,
        user_name="sir",
    )
    assert "95.0%" in briefing
    assert "120.0 GB" in briefing


# 3. JARVIS Protocol Engine Macros
def test_jarvis_protocol_engine():
    proto = JARVISProtocolEngine()

    # Workspace protocol
    res_ws = proto.execute_protocol("WORKSPACE")
    assert res_ws.success is True
    assert len(res_ws.steps_executed) >= 3

    # Security scan protocol
    res_sec = proto.execute_protocol("SECURITY_SCAN")
    assert res_sec.success is True
    assert len(res_sec.steps_executed) >= 3

    # System briefing protocol
    res_br = proto.execute_protocol("BRIEFING")
    assert res_br.success is True
    assert "battery" in res_br.spoken_narration.lower() or "power" in res_br.spoken_narration.lower()

    # Clean & optimize protocol
    res_cl = proto.execute_protocol("CLEAN_OPTIMIZE")
    assert res_cl.success is True


# 4. Screen Vision & Clipboard Awareness
def test_screen_vision_and_clipboard(tmp_path):
    sv = DesktopScreenVision()

    # Screenshot
    shot_path = tmp_path / "test_shot.png"
    ok, p = sv.capture_screenshot(str(shot_path))
    assert ok is True
    assert Path(p).exists()

    # Active window title
    w_title = sv.get_active_window_title()
    assert isinstance(w_title, str)
    assert len(w_title) > 0


# 5. Natural Conversational J.A.R.V.I.S. Routing
def test_conversational_jarvis_directives():
    # 1. JARVIS Greeting
    res_j = conversational_agent.handle_natural_conversation("Jarvis")
    assert res_j is not None
    assert "sir" in res_j["speech_text"].lower()

    # 2. Workspace Protocol
    res_ws = conversational_agent.handle_natural_conversation("code mode")
    assert res_ws is not None
    assert res_ws["action_executed"] == "PROTOCOL_DEVELOPER_WORKSPACE"

    # 3. Security Sweep
    res_sec = conversational_agent.handle_natural_conversation("run security sweep")
    assert res_sec is not None
    assert res_sec["action_executed"] in ("PROTOCOL_SECURITY_SWEEP", "PERFORM_CYBER_SECURITY_SWEEP")

    # 4. Morning Briefing
    res_mb = conversational_agent.handle_natural_conversation("morning briefing")
    assert res_mb is not None
    assert res_mb["action_executed"] == "PROTOCOL_MORNING_BRIEFING"

    # 5. Clean and Optimize
    res_co = conversational_agent.handle_natural_conversation("clean and optimize")
    assert res_co is not None
    assert res_co["action_executed"] == "PROTOCOL_CLEAN_OPTIMIZE"

    # 6. Night Sentinel
    res_ns = conversational_agent.handle_natural_conversation("night sentinel")
    assert res_ns is not None
    assert res_ns["action_executed"] == "PROTOCOL_NIGHT_SENTINEL"

    # 7. Screenshot Directive
    res_shot = conversational_agent.handle_natural_conversation("take screenshot")
    assert res_shot is not None
    assert res_shot["action_executed"] == "SCREENSHOT"
