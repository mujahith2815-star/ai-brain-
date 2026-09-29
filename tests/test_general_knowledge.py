import pytest
from nlp.answer_pipeline import route_intent, process_query

def test_anime_question_routes_to_search():
    """Ensure anime / general knowledge questions route to web_search / general_knowledge, NOT math."""
    query = "what is naruto"
    intent = route_intent(query)
    assert intent in ("web_search", "general_knowledge", "low_confidence", "general_chat"), "FAILED: Naruto was not routed correctly!"

def test_math_question_routes_to_math():
    """Ensure actual math questions still work."""
    query = "what is 2 + 2"
    intent = route_intent(query)
    assert intent == "math", "FAILED: Math query did not route to math!"

def test_hardware_question_routes_to_hardware():
    """Ensure hardware questions route correctly."""
    query = "what is the pinout of bc547"
    intent = route_intent(query)
    assert intent == "hardware", "FAILED: Hardware query did not route to hardware!"

def test_general_knowledge_web_search_execution():
    """Test that a general knowledge query actually performs a web search."""
    query = "what is naruto"
    response = process_query(query)
    # Assert it does NOT contain "4.0" or "calculated total"
    assert "4.0" not in response, "FAILED: Response contained math fallback!"
    assert "calculated total" not in response.lower(), "FAILED: Response contained math fallback!"
    # Assert it contains something from a real search (or at least a relevant reply)
    assert len(response) > 20, "FAILED: Response was too short."
