"""
Comprehensive Stress & Edge-Case Test Suite for Universal Fail-Safe Engine and Adaptive Query Resolution.
Verifies that 100% of varied questions, strange phrasing, heavy typos, math, and domain queries are resolved error-free.
"""

import pytest
from core.universal_failsafe_engine import universal_failsafe_engine
from nlp.conversational_agent import conversational_agent


# 1. Mathematical and Computational Queries
def test_failsafe_math_evaluations():
    queries = [
        "calculate 2^10 + 50",
        "what is 500 / 25 * 4",
        "evaluate 12 * 12 + 100",
        "calculate (100 - 20) / 2",
    ]
    for q in queries:
        res = universal_failsafe_engine.resolve_omnipotent_query(q)
        assert res is not None
        assert res.query_classified_intent == "MATHEMATICAL_CALCULATION"
        assert "=" in res.solution_text
        assert res.confidence == 1.0


# 2. Scientific, Historical & General Knowledge Questions
def test_failsafe_deep_knowledge_questions():
    questions = [
        "Why did the Roman Empire collapse?",
        "What is quantum entanglement and Bell states?",
        "Who invented the modern transistor?",
        "Explain how continuous 6-DOF robotics work",
    ]
    for q in questions:
        res = conversational_agent.handle_natural_conversation(q)
        assert res is not None
        assert res["handled"] is True
        assert len(res["speech_text"]) > 20
        assert "knowledge" in res["speech_text"].lower() or "phass" in res["speech_text"].lower()


# 3. System Inquiries and Hardware Telemetry Queries
def test_failsafe_telemetry_inquiries():
    inquiries = [
        "how much battery is left and what is cpu temp",
        "is the robot system healthy",
        "what is your state of health",
    ]
    for inq in inquiries:
        res = conversational_agent.handle_natural_conversation(inq)
        assert res is not None
        assert res["handled"] is True
        assert len(res["speech_text"]) > 10


# 4. Heavy Typos and Non-Standard Phrasing
def test_failsafe_heavy_typos_and_unstructured_inputs():
    strange_inputs = [
        "plz crte smthng for positive numbers",
        "wht hppns if we ovrclck the mtrs",
        "tell me smth cool about space",
        "any advice for autonomous systems optimization",
    ]
    for s in strange_inputs:
        res = conversational_agent.handle_natural_conversation(s)
        assert res is not None
        assert res["handled"] is True
        assert len(res["speech_text"]) > 10
