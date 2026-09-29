"""
Unit Tests for P.H.A.S.S Human Communication Layer v2.0.
Verifies the 5 human-like behavioral upgrades:
1. Proactive Interruption ([P.H.A.S.S Interrupts] Sir, I noticed...)
2. Dynamic Speech Disfluencies (natural hesitations 'um', 'ah', '...' and rate adaptation 220/120 WPM)
3. Temporal & Spatial Contextual Recall ("You calculated that on [Date] at [Time] while working on [Project]")
4. Instant TTS Cancellation & Queue Flush (Barge-In)
5. Emotional Subtext Analyzer (Frustration / Excitement scoring and empathy prefixes)
"""

import time
import pytest
from pathlib import Path

from core.proactive_monitor import proactive_monitor, ProactiveMonitor
from core.emotion_detector import emotion_detector, EmotionDetector
from core.voice_interface import get_voice_interface
from core.mind_palace import mind_palace
from core.conversation_buffer import conversation_buffer
from nlp.answer_pipeline import process_query


def test_proactive_monitor_interruption():
    """Verify that proactive monitor generates and injects interruptive notifications."""
    conversation_buffer.clear()
    received_msgs = []

    def _test_listener(msg: str):
        received_msgs.append(msg)

    proactive_monitor.add_listener(_test_listener)
    try:
        msg = proactive_monitor.trigger_event("USB_INSERTION", "a new microcontroller connected on COM4.")
        assert ("Orvix Interrupts" in msg) or ("P.H.A.S.S Interrupts" in msg)
        assert "COM4" in msg
        assert len(received_msgs) == 1
        assert received_msgs[0] == msg

        # Verify injection into conversation buffer
        assert conversation_buffer.has_pending_interruptions() is True
        pending = conversation_buffer.get_pending_interruptions()
        assert len(pending) == 1
        assert pending[0] == msg
        # Buffer should be cleared after retrieval
        assert conversation_buffer.has_pending_interruptions() is False
    finally:
        proactive_monitor.remove_listener(_test_listener)


def test_speech_disfluencies_injection():
    """Verify natural filler injection ('um', 'ah', '...') on sentences > 18 words."""
    voice = get_voice_interface()

    # Short sentence should not have disfluencies injected
    short_text = "Good day, sir. Systems are nominal."
    assert voice.inject_disfluencies(short_text) == short_text

    # Long sentence (> 18 words) should have human-like hesitation
    long_text = (
        "We have completed the compilation and the microcontroller firmware has been safely "
        "flashed to the target board without encountering any verification faults or serial parity timeouts."
    )
    injected = voice.inject_disfluencies(long_text)
    assert any(filler in injected for filler in ["um,", "ah,", "..."])
    assert len(injected.split()) > len(long_text.split())


def test_dynamic_speech_rate_modulation():
    """Verify speech rate scales up for urgency (220 WPM) and down for reflection (120 WPM)."""
    voice = get_voice_interface()

    # Urgent context -> 220 WPM
    urgent_rate = voice.determine_speech_rate("Please hurry, flash the emergency firmware quickly!")
    assert urgent_rate == 220

    # Relaxed / thoughtful context -> 120 WPM
    relax_rate = voice.determine_speech_rate("Let's relax and think through the circuit design carefully.")
    assert relax_rate == 120

    # Neutral context -> default rate
    neutral_rate = voice.determine_speech_rate("Opening document for review.")
    assert neutral_rate == voice.rate


def test_temporal_and_spatial_contextual_recall():
    """Verify that memories are recalled with exact date, time, and project folder context."""
    # Store calculation memory with explicit project folder and timestamp
    test_timestamp = 1704110400.0  # 2024-01-01 12:00:00 UTC (or local)
    mind_palace.store_conversation(
        session_id="calc_session_42",
        user_msg="calculate voltage divider 10k 10k 5v",
        assistant_msg="Output voltage is 2.5V across R2.",
        project_folder="Smart_Telemetry_Node",
        timestamp=test_timestamp,
    )

    # Contextual recall directly from mind_palace
    recalled = mind_palace.recall_temporal_spatial("calculate voltage divider 10k 10k 5v")
    assert "You calculated that on " in recalled
    assert " at " in recalled
    assert "while working on Smart_Telemetry_Node" in recalled

    # End-to-end question answering recall via process_query
    resp = process_query("When did I calculate the voltage divider 10k 10k 5v?")
    assert "You calculated that on " in resp
    assert "Smart_Telemetry_Node" in resp


def test_instant_barge_in_and_queue_flush():
    """Verify amplitude detection during speech immediately stops TTS and flushes command queue."""
    voice = get_voice_interface()
    voice.command_queue.put("task1")
    voice.command_queue.put("task2")
    assert not voice.command_queue.empty()

    voice.flush_queue()
    assert voice.command_queue.empty()

    voice.is_speaking = True
    voice.was_interrupted = False
    voice.trigger_barge_in()
    assert voice.was_interrupted is True
    assert voice.is_speaking is False


def test_emotion_detector_frustration_and_excitement():
    """Verify frustration and excitement scoring and empathic response prefixing."""
    # 1. Frustration > 70%
    frust_text = "Damn it, this stupid board is broken and why won't it flash?!"
    res_frust = emotion_detector.analyze(frust_text)
    assert res_frust.frustration > 0.70
    assert res_frust.is_frustrated is True

    resp_frust = process_query(frust_text)
    assert resp_frust.startswith("I sense your frustration, sir.")

    # 2. Excitement > 70%
    excite_text = "Wow, great! It works! The LED is blinking and it's beautiful!"
    res_excite = emotion_detector.analyze(excite_text)
    assert res_excite.excitement > 0.70
    assert res_excite.is_excited is True

    resp_excite = process_query(excite_text)
    assert resp_excite.startswith("Excellent! I'm glad it's working.")
    assert resp_excite.endswith("!")
