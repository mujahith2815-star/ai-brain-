"""
Unit & Integration Tests for Complete J.A.R.V.I.S. Parity:
Live Satellite Weather, Webcam Face/Emotion Biometrics, Inbox Assistant, Smart Home Hub, and 3D Hologram.
"""

import pytest
from knowledge.live_weather import live_weather
from perception.webcam_biometrics import webcam_biometrics
from tools.inbox_assistant import inbox_assistant
from tools.smart_home_hub import smart_home_hub
from gui.hologram_3d import hologram_3d
from nlp.conversational_agent import conversational_agent


# 1. Live Weather & Doppler Satellite Feed
def test_live_weather_engine():
    w = live_weather.fetch_weather("Paris")
    assert w.temperature_c is not None
    assert w.humidity_pct >= 0
    assert len(w.condition_description) > 0
    txt = live_weather.format_weather_text(w)
    assert "METEOROLOGICAL" in txt


# 2. Webcam Face & Emotion Biometrics
def test_webcam_biometrics():
    scan = webcam_biometrics.scan_operator_biometrics()
    assert scan.is_operator_present is True
    assert scan.confidence >= 0.90
    assert scan.detected_emotion in ("FOCUSED", "CALM", "ENERGETIC", "FATIGUED")
    txt = webcam_biometrics.format_biometric_text(scan)
    assert "BIOMETRIC RECOGNITION" in txt


# 3. Autonomous Inbox & Calendar Assistant
def test_inbox_assistant():
    count, summary = inbox_assistant.get_inbox_summary()
    assert count >= 1
    assert "unread" in summary.lower()

    agenda_txt = inbox_assistant.format_full_agenda_text()
    assert "EXECUTIVE INBOX" in agenda_txt
    assert "Calendar Events" in agenda_txt


# 4. Smart Home MQTT & Matter IoT Hub
def test_smart_home_hub():
    ok, msg = smart_home_hub.toggle_device("living_room_light", desired_state=True)
    assert ok is True
    assert "ON" in msg

    rgb_msg = smart_home_hub.set_rgb_ambience("Cyan Neon")
    assert "Cyan Neon" in rgb_msg

    st_txt = smart_home_hub.format_status_text()
    assert "SMART HOME" in st_txt


# 5. 3D Holographic Perspective Renderer
def test_hologram_3d_renderer():
    hologram_3d.step_rotation(0.05, 0.05, 0.02)
    pts = hologram_3d.project_vertices_2d(150.0, 150.0)
    assert len(pts) > 20
    # Verify points have (x, y, scale)
    for px, py, scale in pts:
        assert isinstance(px, float)
        assert isinstance(py, float)
        assert scale > 0.0


# 6. Conversational Directives for 100% Complete Parity
def test_conversational_complete_parity_directives():
    # A. Weather
    res_w = conversational_agent.handle_natural_conversation("what is the weather in Tokyo")
    assert res_w is not None
    assert res_w["type"] == "LIVE_WEATHER_REPORT"

    # B. Webcam Face Scan
    res_b = conversational_agent.handle_natural_conversation("scan face")
    assert res_b is not None
    assert res_b["type"] == "WEBCAM_BIOMETRICS"

    # C. Inbox & Calendar
    res_i = conversational_agent.handle_natural_conversation("check my email inbox")
    assert res_i is not None
    assert res_i["type"] == "INBOX_AGENDA"

    # D. Smart Home
    res_sh = conversational_agent.handle_natural_conversation("turn on living room light")
    assert res_sh is not None
    assert res_sh["type"] == "SMART_HOME_IOT"

    # E. 3D Hologram
    res_h = conversational_agent.handle_natural_conversation("3d hologram wireframe")
    assert res_h is not None
    assert res_h["type"] == "HOLOGRAM_3D"
