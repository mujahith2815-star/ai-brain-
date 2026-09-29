import pytest
from jarvis.persona import jarvis_persona, ChatPersonaMode
from nlp.conversational_agent import conversational_agent
from tools.ollama_manager import ollama_local_manager

def test_persona_mode_switching():
    msg_friendly = jarvis_persona.set_mode(ChatPersonaMode.FRIENDLY_COMPANION)
    assert jarvis_persona.active_mode == ChatPersonaMode.FRIENDLY_COMPANION
    assert "Friendly Companion Mode" in msg_friendly

    msg_exec = jarvis_persona.set_mode(ChatPersonaMode.SOVEREIGN_EXECUTIVE)
    assert jarvis_persona.active_mode == ChatPersonaMode.SOVEREIGN_EXECUTIVE
    assert "Sovereign Executive Mode" in msg_exec

def test_friendly_jokes_and_motivation():
    joke = jarvis_persona.get_friendly_joke()
    assert isinstance(joke, str) and len(joke) > 10

    motivation = jarvis_persona.get_friendly_motivation()
    assert isinstance(motivation, str) and len(motivation) > 10

def test_emotional_empathy():
    res_sad = jarvis_persona.format_empathy_response("i had a really bad day and feel sad")
    assert "tough days don't last forever" in res_sad or "sorry you're feeling that way" in res_sad

    res_happy = jarvis_persona.format_empathy_response("i feel so happy and excited")
    assert "fantastic" in res_happy or "positive energy" in res_happy

def test_conversational_friendly_directives():
    # 1. Joke
    res_joke = conversational_agent.handle_natural_conversation("tell me a joke")
    assert res_joke is not None
    assert res_joke["type"] == "FRIENDLY_JOKE"

    # 2. Motivation
    res_mot = conversational_agent.handle_natural_conversation("give me motivation")
    assert res_mot is not None
    assert res_mot["type"] == "FRIENDLY_MOTIVATION"

    # 3. Empathy
    res_emp = conversational_agent.handle_natural_conversation("i had a bad day")
    assert res_emp is not None
    assert res_emp["type"] == "FRIENDLY_EMPATHY"

    # 4. Mode Switch
    res_mode = conversational_agent.handle_natural_conversation("switch to friendly mode")
    assert res_mode is not None
    assert res_mode["type"] == "PERSONA_MODE_SWITCH"

def test_hai_and_casual_greetings():
    # Verify 'hai' produces clean conversational greeting, NOT robotic adaptive resolution
    jarvis_persona.set_mode(ChatPersonaMode.FRIENDLY_COMPANION)
    res_hai = ollama_local_manager.generate_response("hai")
    assert "ADAPTIVE RESOLUTION" not in res_hai["response"]
    assert any(w in res_hai["response"].lower() for w in ["hey", "hello", "hi", "how is", "day", "friend"])

    # Verify 'heyy'
    res_heyy = ollama_local_manager.generate_response("heyy")
    assert "ADAPTIVE RESOLUTION" not in res_heyy["response"]

    # Verify 'thanks'
    res_thx = ollama_local_manager.generate_response("thanks")
    assert any(w in res_thx["response"].lower() for w in ["welcome", "pleasure", "done"])
