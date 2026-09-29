import pytest
from nlp.answer_pipeline import sanitize_response, is_internal_log

def test_detects_internal_log():
    bad_text = "Current Step: 1 of 8. Decide your next action. Return JSON only."
    assert is_internal_log(bad_text) == True

def test_sanitizes_json_action():
    raw = '{"actions": [{"tool": "web_search", "args": {"query": "naruto"}}]}'
    cleaned = sanitize_response(raw)
    assert "naruto" not in cleaned.lower()  # Should not just echo the JSON
    assert len(cleaned) > 20  # Should return a fallback or summary

def test_passes_clean_text():
    clean = "Naruto is an anime about a ninja."
    assert sanitize_response(clean) == clean
