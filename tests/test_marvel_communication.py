"""
Unit tests for P.H.A.S.S Marvel-Level AI Communication Upgrades:
1. Personality & Voice Matrix (JARVIS, FRIDAY, EDITH)
2. Sarcasm Filter for Trivial Tasks ("Opening Notepad. Riveting, sir.")
3. Advanced NLP Emotion Detection (Frustration, Excitement, Urgency)
4. Conversational Flow & Buffer with Proactive Follow-ups
5. Lifelong Profile Persistence & Startup Greeting by Real Name
6. Interruptible Voice (Barge-In)
"""

import pytest
from core.personality_matrix import personality_matrix
from core.lifelong_profile_manager import lifelong_profile_manager
from core.conversation_buffer import conversation_buffer
from core.voice_interface import VoiceInterface
from nlp.answer_pipeline import process_query


def test_personality_matrix_modes():
    """Verify switching between JARVIS, FRIDAY, and EDITH personas."""
    assert personality_matrix.set_personality("JARVIS")
    curr = personality_matrix.get_current_personality()
    assert curr["name"] == "JARVIS"
    assert "witty" in curr["tone"]

    assert personality_matrix.set_personality("FRIDAY")
    curr = personality_matrix.get_current_personality()
    assert curr["name"] == "FRIDAY"
    assert "calm" in curr["tone"]

    assert personality_matrix.set_personality("EDITH")
    curr = personality_matrix.get_current_personality()
    assert curr["name"] == "EDITH"
    assert "tactical" in curr["tone"]

    # Reset to JARVIS
    personality_matrix.set_personality("JARVIS")


def test_jarvis_sarcasm_filter_trivial_task():
    """Verify that trivial tasks under JARVIS receive dry, witty remarks."""
    personality_matrix.set_personality("JARVIS")

    # Notepad test
    resp_notepad = process_query("open notepad")
    assert "opening notepad" in resp_notepad.lower()
    assert "riveting, sir" in resp_notepad.lower()

    # Calculator test
    resp_calc = process_query("open calculator")
    assert "calculator" in resp_calc.lower()


def test_emotion_detection_frustration():
    """Verify that frustration drops technical jargon and gives blunt step-by-step fixes."""
    query = "Ugh damn it, my circuit is broken and why won't this work?!"
    resp = process_query(query)
    low = resp.lower()
    assert "drop the jargon" in low or "step" in low or "1." in low
    assert "power" in low or "check" in low


def test_emotion_detection_excitement():
    """Verify that excitement triggers celebration with the user."""
    query = "It works! The LED is blinking and working!"
    resp = process_query(query)
    low = resp.lower()
    assert "excellent work, sir" in low or "perfect" in low or "outstanding" in low


def test_lifelong_profile_startup_greeting():
    """Verify that lifelong profile stores real name and generates personalized startup greeting."""
    assert lifelong_profile_manager.real_name == "M.Mohammed Mujahith"
    assert "ESP32" in lifelong_profile_manager.favorite_microcontrollers

    greeting = lifelong_profile_manager.get_startup_greeting("JARVIS")
    assert "M.Mohammed Mujahith" in greeting
    assert "JARVIS online" in greeting
    assert "sir" in greeting

    greeting_friday = lifelong_profile_manager.get_startup_greeting("FRIDAY")
    assert "M.Mohammed Mujahith" in greeting_friday
    assert "Boss" in greeting_friday


def test_conversation_buffer_follow_up():
    """Verify conversation buffer tracking and proactive follow-up questions."""
    conversation_buffer.clear()
    conversation_buffer.add_turn("open notepad", "Opening Notepad. Riveting, sir.", "general")

    assert len(conversation_buffer.turns) == 1
    follow_up = conversation_buffer.get_next_follow_up("general", "JARVIS")
    assert "what's next, sir?" in follow_up.lower()

    follow_up_hw = conversation_buffer.get_next_follow_up("hardware", "JARVIS")
    assert "schematic" in follow_up_hw.lower() or "serial" in follow_up_hw.lower()


def test_interruptible_voice_barge_in():
    """Verify that barge-in trigger halts active speech and registers interruption."""
    vi = VoiceInterface()
    assert vi.barge_in_enabled is True
    assert vi.barge_in_threshold == 0.04

    vi.is_speaking = True
    vi.trigger_barge_in()
    assert vi.is_speaking is False
    assert vi.was_interrupted is True