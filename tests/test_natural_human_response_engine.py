"""
Comprehensive Test Suite for NICON Natural Human-Like Response Engine.
Verifies adaptive depth, human-like context, follow-up pronoun resolution,
natural tool interpretation (Vision, CPU, Errors, Actions), and anti-doc-speak rewriting.
"""

import pytest
from nlp.natural_response_engine import natural_response_engine, ResponseMode
from nlp.conversational_agent import conversational_agent
from tools.ollama_manager import ollama_local_manager


# 1. Natural Question Answering (No doc-speak)
def test_natural_asyncio_explanation():
    res = ollama_local_manager.generate_response("What is asyncio?")
    ans = res["response"]
    assert "asyncio" in ans.lower()
    # Must NOT sound like rigid documentation
    assert "enables non-blocking event loops and coroutines" not in ans
    assert "is a mechanism which" not in ans
    assert len(ans) > 20


# 2. Beginner Mode ("Explain simply")
def test_beginner_mode():
    res = ollama_local_manager.generate_response("Explain asyncio simply.")
    ans = res["response"]
    assert "asyncio" in ans.lower()
    # Beginner explanations should be intuitive and approachable
    assert any(w in ans.lower() for w in ["chef", "waiting", "simple terms", "stuck", "efficiently"])


# 3. Practical Explanation ("Why would I use it?")
def test_why_use_asyncio():
    res = ollama_local_manager.generate_response("Why would I use asyncio?")
    ans = res["response"]
    assert any(w in ans.lower() for w in ["waiting", "network", "freezing", "responsive", "tasks"])


# 4. Multi-Turn Context, Pronoun Resolution & Follow-ups
def test_multi_turn_context_and_followups():
    # Turn 1: Establish topic
    t1 = ollama_local_manager.generate_response("What is asyncio?")
    assert natural_response_engine.context.active_topic == "asyncio"

    # Turn 2: "Why would I need it?" -> 'it' refers to asyncio
    t2 = ollama_local_manager.generate_response("Why would I need it?")
    assert any(w in t2["response"].lower() for w in ["waiting", "network", "responsive", "freezing", "tasks"])

    # Turn 3: "Can it run my Nicon voice system?" -> 'it' refers to asyncio in Nicon context
    t3 = ollama_local_manager.generate_response("Can it run my Nicon voice system?")
    assert "nicon" in t3["response"].lower() or "voice" in t3["response"].lower() or "audio" in t3["response"].lower()

    # Turn 4: "Tell me more." -> deeper elaboration on asyncio
    t4 = ollama_local_manager.generate_response("Tell me more.")
    assert "asyncio" in t4["response"].lower() or "task" in t4["response"].lower()

    # Turn 5: "Give me an example." -> practical code / usage example
    t5 = ollama_local_manager.generate_response("Give me an example.")
    assert "python" in t5["response"].lower() or "await" in t5["response"].lower() or "def" in t5["response"].lower() or "async" in t5["response"].lower()


# 5. Natural Vision Information Conversion
def test_natural_vision_response():
    res = conversational_agent.handle_natural_conversation("What do you see?")
    assert res is not None
    assert res["type"] == "VISION_OBSERVATION"
    text = res["speech_text"]
    # Must be conversational human phrasing
    assert any(w in text.lower() for w in ["display", "screen", "window", "workspace", "active"])
    assert "raw_vision_dump" not in text


# 6. Natural CPU Telemetry Conversion
def test_natural_cpu_telemetry_response():
    res = conversational_agent.handle_natural_conversation("What is my CPU doing?")
    assert res is not None
    assert res["type"] == "CPU_TELEMETRY"
    text = res["speech_text"]
    # Must be human conversational phrasing (e.g. "Your CPU is currently running around...")
    assert "cpu" in text.lower()
    assert "%" in text
    assert "ram" in text.lower() or "memory" in text.lower()


# 7. Natural Tool Interpretation & Error Handling
def test_natural_tool_interpretation_and_errors():
    # A. Raw CPU/RAM output conversion
    raw_stats = {"cpu_percent": 42.1, "ram_used_gb": 6.2}
    human_stats = natural_response_engine.interpret_tool_output("cpu_ram", raw_stats)
    assert "42.1%" in human_stats
    assert "6.2 gb" in human_stats.lower()
    assert "running around" in human_stats.lower()

    # B. Camera busy error conversion
    human_err = natural_response_engine.interpret_tool_output("error", "OSError errno 16 Device or resource busy")
    assert "camera is currently being used" in human_err.lower()
    assert "check which process is holding it" in human_err.lower()

    # C. Natural action confirmations
    calc_act = natural_response_engine.interpret_tool_output("app_launch", "calc")
    assert calc_act == "Calculator is open."

    code_act = natural_response_engine.interpret_tool_output("app_launch", "vscode")
    assert code_act == "I've opened VS Code."


# 8. Adaptive Response Modes Detection
def test_adaptive_response_modes():
    assert natural_response_engine.detect_response_mode("Explain asyncio simply") == ResponseMode.BEGINNER
    assert natural_response_engine.detect_response_mode("Explain the event loop under the hood") == ResponseMode.TECHNICAL
    assert natural_response_engine.detect_response_mode("In one sentence, what is asyncio?") == ResponseMode.CONCISE
    assert natural_response_engine.detect_response_mode("Explain deeply how it works") == ResponseMode.DETAILED
    assert natural_response_engine.detect_response_mode("Why is it failing and crashing?") == ResponseMode.TROUBLESHOOTING


# 9. Response Quality Validation (Stripping Internal Metadata)
def test_response_quality_validation():
    bad_internal = (
        "=== P.H.A.S.S DEEP KNOWLEDGE SYNTHESIS ===\n"
        "Autonomous Synthesis:\n"
        "  • Cognitive Strategy: Deep inspection\n"
        "  • Confidence Score: 95%\n"
        "Python asyncio is useful for concurrency."
    )
    cleaned = natural_response_engine.validate_quality(bad_internal, "what is asyncio", ResponseMode.NORMAL)
    assert "Autonomous Synthesis" not in cleaned
    assert "Cognitive Strategy" not in cleaned
    assert "Confidence Score" not in cleaned
    assert "Python asyncio is useful for concurrency." in cleaned
