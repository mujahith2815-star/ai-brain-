"""
Unit tests for the NLP, NLU, LLM, and NLG Language Intelligence Subsystems.
"""

import pytest
from nlp.nlp_pipeline import nlp_pipeline
from nlp.nlu import nlu_pipeline, IntentType
from nlp.llm_engine import llm_orchestrator, OfflineLLMProvider
from nlp.nlg import nlg_generator, NLGPersona


def test_nlp_pipeline_tokenization_and_keywords():
    text = "The autonomous spherical robot is inspecting the central server rack and battery cell."
    tokens = nlp_pipeline.tokenize(text, remove_stopwords=True)

    assert "autonomous" in tokens
    assert "spherical" in tokens
    assert "robot" in tokens
    assert "the" not in tokens  # Stopword removed
    assert "is" not in tokens   # Stopword removed

    keywords = nlp_pipeline.extract_keywords(text, top_k=3)
    assert len(keywords) > 0


def test_nlp_embeddings_and_cosine_similarity():
    vec1 = nlp_pipeline.compute_embedding("Inspect laboratory server rack", dim=32)
    vec2 = nlp_pipeline.compute_embedding("Examine server terminal in room", dim=32)
    vec3 = nlp_pipeline.compute_embedding("Bake strawberry cake recipe", dim=32)

    sim_related = nlp_pipeline.cosine_similarity(vec1, vec2)
    sim_unrelated = nlp_pipeline.cosine_similarity(vec1, vec3)

    assert len(vec1) == 32
    assert sim_related > sim_unrelated


def test_nlu_intent_classification():
    # 1. Diagnostics
    res_diag = nlu_pipeline.understand("Diagnose system failure and inspect error logs")
    assert res_diag.intent == IntentType.DIAGNOSTIC_QUERY
    assert res_diag.urgency_score >= 0.8

    # 2. Environment Probe
    res_env = nlu_pipeline.understand("Scan the room and detect surrounding objects")
    assert res_env.intent == IntentType.ENVIRONMENT_PROBE

    # 3. Navigation
    res_nav = nlu_pipeline.understand("Navigate to the magnetic charging dock")
    assert res_nav.intent == IntentType.NAVIGATION_REQUEST
    assert "Charging Dock" in [e.entity_name for e in res_nav.entities] or "Charging Dock" in res_nav.slots.values()

    # 4. Emergency
    res_emerg = nlu_pipeline.understand("Emergency stop immediately, halt all motors")
    assert res_emerg.intent == IntentType.EMERGENCY_COMMAND
    assert res_emerg.urgency_score == 1.0

    # 5. Feedback Correction
    res_corr = nlu_pipeline.understand("No, you should have checked the dependencies first")
    assert res_corr.intent == IntentType.FEEDBACK_CORRECTION


def test_nlu_entity_extraction():
    res = nlu_pipeline.understand("Inspect the server rack in the laboratory zone")
    entities = res.entities
    categories = [e.category for e in entities]
    assert "DEVICE" in categories or "LOCATION" in categories


@pytest.mark.asyncio
async def test_llm_orchestrator_chat_and_plan():
    provider = OfflineLLMProvider()
    res = await provider.chat_completion([
        {"role": "user", "content": "Analyze the system failure"}
    ])

    assert res.text != ""
    assert res.structured_data is not None
    assert res.structured_data.get("intent") == "DIAGNOSTIC"


def test_nlg_generator_personas_and_telemetry():
    # Acknowledgement
    ack_robot = nlg_generator.generate_acknowledgement("Inspect Room", 4, NLGPersona.ROBOT_VOICE)
    assert "Directive received" in ack_robot

    ack_concise = nlg_generator.generate_acknowledgement("Inspect Room", 4, NLGPersona.OPERATOR_CONCISE)
    assert "Goal: 'Inspect Room'" in ack_concise

    # Completion Report
    report = nlg_generator.generate_completion_report(
        "Diagnose Service", True, 3, ["Check dependencies first"]
    )
    assert "successfully completed" in report
    assert "1 new lesson" in report

    # Telemetry Narrative
    mock_robot = {"battery_percentage": 85.0, "internal_temp_c": 32.0, "chassis_type": "spherical_omni"}
    mock_env = {"ambient_temperature_c": 21.0}
    narrative = nlg_generator.generate_telemetry_narrative(mock_robot, mock_env)
    assert "85.0% battery" in narrative
    assert "32.0°C" in narrative
