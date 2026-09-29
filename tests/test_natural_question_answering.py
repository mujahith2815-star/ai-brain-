"""
Unit and Integration Tests for Natural Question Answering and Capability Discovery.
Verifies that P.H.A.S.S never exposes internal execution metadata (Autonomous Synthesis,
Cognitive Strategy, Confidence Score, System Status: EXECUTED & RESOLVED) on natural questions.
"""

import pytest
from core.capability_registry import capability_registry
from nlp.answer_pipeline import generate_answer
from nlp.conversational_agent import conversational_agent
from tools.ollama_manager import ollama_local_manager


# 1. Capability Discovery Tests
def test_capability_discovery_registry():
    modules = capability_registry.discover_modules()
    assert "computer" in modules
    assert "vision" in modules
    assert "files" in modules
    assert "coding" in modules
    assert "browser" in modules
    assert "memory" in modules

    avail = capability_registry.list_available()
    assert len(avail) >= 5

    desc = capability_registry.describe()
    assert "Here is what I can do for you:" in desc
    assert "Control applications" in desc


# 2. Dynamic Capability Questions (Must NEVER return robotic debug blocks)
def test_capability_question_answering():
    queries = [
        "then what are the things u can do",
        "what can you do?",
        "what are the things you can do",
        "what features do you have?",
        "tell me what you can do",
        "what are your capabilities?",
        "what can I do with you?",
        "what can you control?",
        "which tools do you have?",
        "which modules are working?",
    ]
    for q in queries:
        res = ollama_local_manager.generate_response(q)
        ans = res["response"]
        assert ans is not None and len(ans) > 20
        # STRICT RULE: Must NEVER show internal reasoning metadata
        assert "=== UNIVERSAL ADAPTIVE RESOLUTION ===" not in ans
        assert "=== P.H.A.S.S UNIVERSAL ADAPTIVE RESOLUTION ===" not in ans
        assert "Autonomous Synthesis" not in ans
        assert "Cognitive Strategy" not in ans
        assert "Deductive Conclusions" not in ans
        assert "Confidence Score" not in ans
        assert "System Status: EXECUTED & RESOLVED" not in ans
        assert "Directive / Inquiry" not in ans


# 3. Action-Capability Questions vs Command Execution
def test_action_capability_vs_command():
    # A. Action-Capability Question: Must answer without executing action
    res_cap = conversational_agent.handle_natural_conversation("can you open Chrome?")
    assert res_cap is not None
    assert res_cap["type"] == "CAPABILITY_ANSWER"
    assert "browser" in res_cap["speech_text"].lower() or "chrome" in res_cap["speech_text"].lower()
    assert res_cap["action_executed"] is None  # Did NOT execute yet!

    res_calc_cap = conversational_agent.handle_natural_conversation("can you open Calculator?")
    assert res_calc_cap is not None
    assert res_calc_cap["type"] == "CAPABILITY_ANSWER"
    assert "calculator" in res_calc_cap["speech_text"].lower()
    assert res_calc_cap["action_executed"] is None

    # B. Action Command: Must actually execute and verify
    res_cmd = conversational_agent.handle_natural_conversation("open calculator")
    assert res_cmd is not None
    assert "APP_LAUNCH" in res_cmd["type"]
    assert "CALCULATOR" in res_cmd["action_executed"]


# 4. General Knowledge Questions (Earth, Watch, Python, Sky, AI)
def test_general_knowledge_questions():
    test_cases = [
        ("what is Earth?", "third planet from the Sun"),
        ("what is a watch?", "timepiece"),
        ("what is Python?", "programming language"),
        ("why is the sky blue?", "Rayleigh scattering"),
        ("how does AI work?", "neural networks"),
    ]
    for query, expected_snippet in test_cases:
        res = ollama_local_manager.generate_response(query)
        ans = res["response"]
        assert expected_snippet.lower() in ans.lower()
        # Ensure clean user output
        assert "Autonomous Synthesis" not in ans
        assert "System Status: EXECUTED & RESOLVED" not in ans


# 5. Identity and Explanation Questions
def test_identity_and_system_explanations():
    # Who are you
    res_id = ollama_local_manager.generate_response("who are you?")
    assert "P.H.A.S.S" in res_id["response"]
    assert "Autonomous Synthesis" not in res_id["response"]

    # How do you work
    res_work = ollama_local_manager.generate_response("how do you work?")
    assert "cognitive architecture" in res_work["response"].lower() or "transformer" in res_work["response"].lower()
    assert "System Status: EXECUTED & RESOLVED" not in res_work["response"]
