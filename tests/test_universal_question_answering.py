"""
Tests for Universal Question Answering & User Identity Memory in P.H.A.S.S/NICON.
Verifies that:
1. Name questions ("can u able to say my name", "what is my name") work dynamically without random context injection.
2. Setting user name ("my name is ...") is remembered and persisted.
3. Arbitrary universal questions ("who invented the airplane", "what is quantum entanglement") return factual, natural answers.
"""

import pytest
from nlp.conversational_agent import conversational_agent
from jarvis.persona import jarvis_persona, ChatPersonaMode


def test_user_identity_name_flow():
    jarvis_persona.set_mode(ChatPersonaMode.FRIENDLY_COMPANION)
    
    # 1. Set name
    set_res = conversational_agent.handle_natural_conversation("my name is Ph")
    assert set_res is not None
    assert set_res["type"] == "USER_IDENTITY_SET"
    assert "Ph" in set_res["speech_text"]

    # 2. Ask name
    ask_res = conversational_agent.handle_natural_conversation("can u able to say my name")
    assert ask_res is not None
    assert ask_res["type"] == "USER_IDENTITY"
    assert "Ph" in ask_res["speech_text"]
    assert "quantum entanglement" not in ask_res["speech_text"].lower()


def test_universal_questions_no_vector_vault_leak():
    jarvis_persona.set_mode(ChatPersonaMode.FRIENDLY_COMPANION)
    
    # Who invented the airplane
    res_flight = conversational_agent.handle_natural_conversation("who invented the airplane")
    assert res_flight is not None
    assert "wright" in res_flight["speech_text"].lower()
    assert "quantum entanglement" not in res_flight["speech_text"].lower()

    # Quantum entanglement
    res_quantum = conversational_agent.handle_natural_conversation("what is quantum entanglement")
    assert res_quantum is not None
    assert "quantum" in res_quantum["speech_text"].lower()
    assert "entanglement" in res_quantum["speech_text"].lower()
