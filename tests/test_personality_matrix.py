"""
Tests for Personality & Emotional Matrix.
"""

import pytest
from datetime import datetime
from core.personality_matrix import PersonalityMatrix, personality_matrix


def test_available_personalities():
    avail = personality_matrix.get_available_personalities()
    assert "default" in avail
    assert "executive" in avail
    assert "friendly" in avail
    assert "creative" in avail
    assert "late_night" in avail


def test_personality_switching():
    pm = PersonalityMatrix()
    assert pm.set_personality("executive") is True
    curr = pm.get_current_personality()
    assert curr["key"] == "executive"
    assert curr["tone"] == "concise"

    # System prompt modifier reflects executive mode
    mod = pm.get_system_prompt_modifier()
    assert "EXECUTIVE" in mod
    assert "concise" in mod.lower()

    # Invalid persona
    assert pm.set_personality("non_existent_persona") is False


def test_mood_detection():
    pm = PersonalityMatrix()
    assert pm.detect_mood("I need this report done ASAP, it is an emergency!") == "urgent"
    assert pm.detect_mood("Everything is broken and nothing works, this is annoying!") == "frustrated"
    assert pm.detect_mood("I am so sleepy and exhausted after a long day.") == "tired"
    assert pm.detect_mood("This is awesome and amazing, thank you so much!") == "happy"
    assert pm.detect_mood("What is the time complexity of quicksort?") == "neutral"


def test_auto_adapt_personality():
    pm = PersonalityMatrix()
    # Daytime midday
    daytime = datetime(2026, 9, 5, 14, 30)

    # Urgent query adapts to executive
    adapted = pm.auto_adapt_personality("Fix this bug ASAP!", current_time=daytime)
    assert adapted == "executive"

    # Frustrated query adapts to friendly
    adapted2 = pm.auto_adapt_personality("I am feeling stressed and sad today", current_time=daytime)
    assert adapted2 == "friendly"

    # Late night auto adaptation (02:00 AM)
    nighttime = datetime(2026, 9, 5, 2, 0)
    adapted3 = pm.auto_adapt_personality("Hello assistant", current_time=nighttime)
    assert adapted3 == "late_night"


def test_custom_personality_loader():
    pm = PersonalityMatrix()
    custom_persona = {
        "name": "Zen Master",
        "description": "Mindful, philosophical, and calming.",
        "tone": "zen",
        "style": "koans and peaceful wisdom",
        "prompt_instruction": "Respond like a peaceful Zen master with gentle reflections.",
    }

    assert pm.load_custom_personality(custom_persona) is True
    assert "zen_master" in pm.get_available_personalities()

    pm.set_personality("zen_master")
    curr = pm.get_current_personality()
    assert curr["name"] == "Zen Master"
    assert "peaceful Zen master" in pm.get_system_prompt_modifier()
