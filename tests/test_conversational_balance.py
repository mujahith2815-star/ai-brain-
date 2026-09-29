"""
Unit Tests for P.H.A.S.S Conversational Balance Patch.
Verifies:
1. Priority 0: Greetings & General Chat routes greetings like 'hello', 'hi', 'how are you' to 'general_chat'
   and process_query() returns a warm, friendly response without calling web_search or archive fallbacks.
2. Priority 1: Expanded Project Creation catches phrases like 'can u build a programme', 'build a program',
   'make a project' and routes to 'project_bootstrap', prompting for project name without rejection.
"""

import pytest
from nlp.answer_pipeline import route_intent, process_query


def test_greeting_routes_to_chat():
    """Verify that 'hello' and other greetings route to 'general_chat' and return a warm greeting."""
    greetings = ["hello", "hi", "hey", "good morning", "good evening", "how are you", "what's up"]
    for g in greetings:
        intent = route_intent(g)
        assert intent == "general_chat", f"Expected 'general_chat' for '{g}', got '{intent}'"

    # End-to-end process_query test for "hello"
    resp = process_query("hello")
    assert "hello" in resp.lower() or "assist" in resp.lower() or "sir" in resp.lower()
    # Ensure no archive hallucinations or search leaks
    assert "verified reference archives" not in resp.lower()
    assert "research summary" not in resp.lower()
    assert "i didn't quite catch that" not in resp.lower()


def test_build_programme_routes_to_project():
    """Verify that 'can u build a programme' routes to project_bootstrap and prompts for project name."""
    intent = route_intent("can u build a programme")
    assert intent == "project_bootstrap", f"Expected 'project_bootstrap', got '{intent}'"

    # Expanded keyword variations
    variations = [
        "can you build a program",
        "build a programme",
        "build a program",
        "make a project",
        "start a new project",
        "create a project",
        "new project",
    ]
    for var in variations:
        assert route_intent(var) == "project_bootstrap", f"Failed for '{var}'"

    # End-to-end response prompts for project name without rejection
    resp = process_query("can u build a programme")
    assert "project" in resp.lower() or "name" in resp.lower()
    assert "i didn't quite catch that" not in resp.lower()
    assert "verified reference archives" not in resp.lower()


def test_project_creation_with_named_project():
    """Verify that project creation with an explicit name still succeeds."""
    intent = route_intent("create project Drone_ESC")
    assert intent == "project_bootstrap"

    intent2 = route_intent("start a new project led_blink")
    assert intent2 == "project_bootstrap"
