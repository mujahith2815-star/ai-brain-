"""
Unit & Integration Tests for Intelligent Phonetic & Fuzzy Spelling Auto-Correction.
"""

import pytest
from nlp.spelling_corrector import spelling_corrector
from nlp.conversational_agent import conversational_agent


# 1. Phonetic & Common Typos Correction
def test_phonetic_and_domain_typos():
    assert spelling_corrector.correct_word("wright") == "write"
    assert spelling_corrector.correct_word("posative") == "positive"
    assert spelling_corrector.correct_word("intiger") == "integer"
    assert spelling_corrector.correct_word("tryr") == "try"
    assert spelling_corrector.correct_word("cretea") == "create"
    assert spelling_corrector.correct_word("ubgrade") == "upgrade"
    assert spelling_corrector.correct_word("watsapp") == "whatsapp"
    assert spelling_corrector.correct_word("spotfy") == "spotify"
    assert spelling_corrector.correct_word("yeasterday") == "yesterday"
    assert spelling_corrector.correct_word("parliment") == "parliament"


# 2. Sentence-Level Auto-Correction
def test_sentence_spelling_correction():
    raw_sentence = "wright a code for posative intiger and open watsapp"
    corrected, modified = spelling_corrector.correct_sentence(raw_sentence)

    assert modified is True
    assert "write a code for positive integer and open whatsapp" == corrected


# 3. Fuzzy Edit Distance Matching
def test_fuzzy_edit_distance():
    assert spelling_corrector.correct_word("calculatr") == "calculator"
    assert spelling_corrector.correct_word("biometrc") == "biometric"


# 4. End-to-End Conversational Routing with Severe Typos
def test_conversational_with_typos():
    # User types "wright a code for posative intiger"
    res_code = conversational_agent.handle_natural_conversation("wright a code for posative intiger")
    assert res_code is not None
    assert res_code["type"] == "AUTONOMOUS_CODE_GENERATION"
    assert "positive_integer_finder" in res_code["speech_text"] or "positive" in res_code["speech_text"].lower()

    # User types "wether in tokyo"
    res_weather = conversational_agent.handle_natural_conversation("wether in tokyo")
    assert res_weather is not None
    assert res_weather["type"] == "LIVE_WEATHER_REPORT"

    # User types "leran quantum computing"
    res_learn = conversational_agent.handle_natural_conversation("leran quantum computing")
    assert res_learn is not None
    assert res_learn["type"] == "AUTONOMOUS_SKILL_SYNTHESIS"
