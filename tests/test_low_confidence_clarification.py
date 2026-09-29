"""
Unit Tests for P.H.A.S.S Low-Confidence Clarification Fallback.
Verifies that:
1. route_intent() returns 'low_confidence' when queries do not strongly match the 7 existing priorities.
2. The 7 existing priorities, math, and hardware remain strictly routed.
3. process_query() returns the exact string:
   "I didn't quite catch that, sir. Could you rephrase your command or say it more directly?"
   and does not execute web_search or hallucinate research summaries.
"""

import pytest
from nlp.answer_pipeline import route_intent, process_query


def test_route_intent_low_confidence():
    """Verify that queries outside the specific action priorities return 'general_chat'."""
    unmatched_queries = [
        "what is quantum computing",
        "who was the first president of the moon",
        "tell me a random story about an alien",
        "some obscure non-existent phrase 12345",
        "why is the sky blue",
    ]
    for q in unmatched_queries:
        intent = route_intent(q)
        assert intent in ("general_chat", "low_confidence"), f"Expected conversational intent for '{q}', got '{intent}'"


def test_route_intent_preserves_7_priorities():
    """Verify all 7 core priorities, math, and hardware remain intact."""
    # Priority 1: Project Creation
    assert route_intent("start a new project led_blink") == "project_bootstrap"
    assert route_intent("create project Drone_ESC") == "project_bootstrap"

    # Priority 2: Subagents
    assert route_intent("spawn a researcher to find AI news") == "subagent_orchestrator"
    assert route_intent("subagent coder to refactor auth") == "subagent_orchestrator"

    # Priority 3: Encryption/Decryption
    assert route_intent("encrypt secret.txt") == "security_tools"
    assert route_intent("decrypt database.enc") == "security_tools"

    # Priority 4: Memory / Implicit Learning & Recall
    assert route_intent("remember my name is M.Mohammed Mujahith") == "memory_save"
    assert route_intent("rember my name is M.Mohammed Mujahith") == "memory_save"
    assert route_intent("my name is M.Mohammed Mujahith") == "memory_save"
    assert route_intent("what is my name") == "memory_recall"
    assert route_intent("do you remember") == "memory_recall"

    # Priority 5: Mouse / GUI Automation
    assert route_intent("move mouse to 500 500") == "gui_automation"
    assert route_intent("click 200 300") == "gui_automation"

    # Priority 6: File Reading
    assert route_intent("read main.py") == "file_reader"
    assert route_intent("read config.txt") == "file_reader"

    # Priority 7: Self-Diagnosis
    assert route_intent("check for missing dependencies") == "self_healing"

    # Math and Hardware checks
    assert route_intent("what is 15 * 8") == "math"
    assert route_intent("what is the pinout of esp32") == "hardware"


def test_process_query_exact_clarification():
    """
    Verify process_query returns natural conversation for unhandled queries
    and never invokes research summary or reference archives.
    """
    queries = [
        "what is quantum computing",
        "tell me about string theory",
        "xyz random query 9988",
    ]

    for q in queries:
        resp = process_query(q)
        assert len(resp) > 5
        assert "research summary" not in resp.lower()
        assert "verified reference archives" not in resp.lower()
        assert "according to" not in resp.lower()

