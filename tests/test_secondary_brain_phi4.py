"""
Test Suite for Secondary Brain (Phi-4) Architecture in NICON / P.H.A.S.S.
Verifies secondary brain activation, dual-brain status inspection,
and collaborative question processing.
"""

import pytest
from core.secondary_brain import secondary_brain
from nlp.conversational_agent import conversational_agent
from tools.ollama_manager import ollama_local_manager


def test_secondary_brain_activation_directive():
    res = conversational_agent.handle_natural_conversation("use secondary brain phi4")
    assert res is not None
    assert res["handled"] is True
    assert res["type"] == "SECONDARY_BRAIN_ACTIVATION"
    assert res["action_executed"] == "ACTIVATE_SECONDARY_BRAIN_PHI4"
    assert "Dual-Brain" in res["speech_text"]
    assert "Phi-4" in res["speech_text"]
    assert secondary_brain.is_active is True


def test_secondary_brain_status_directive():
    res = conversational_agent.handle_natural_conversation("secondary brain status")
    assert res is not None
    assert res["handled"] is True
    assert res["type"] == "SECONDARY_BRAIN_STATUS"
    assert "Dual-Brain" in res["speech_text"]
    assert "Primary Brain" in res["speech_text"]
    assert "Secondary Brain" in res["speech_text"]


def test_secondary_brain_query_processing():
    secondary_brain.activate("phi4")
    ans = secondary_brain.process_query("What is asyncio?")
    assert isinstance(ans, str)
    assert len(ans) > 20
    assert "asyncio" in ans.lower()
    # Ensure natural assistant tone, not rigid docs
    assert "enables non-blocking event loops and coroutines" not in ans


def test_dual_brain_separation_of_concerns():
    # A. Capability Question -> Answered naturally
    res_q = conversational_agent.handle_natural_conversation("What can you do?")
    assert res_q is not None
    assert res_q["type"] == "CAPABILITY_ANSWER"

    # B. Hardware / OS Action -> Handled by Primary Native Controller
    res_a = conversational_agent.handle_natural_conversation("open calculator")
    assert res_a is not None
    assert res_a["type"] in ("APP_LAUNCH_CALCULATOR", "OS_APP_LAUNCH")
