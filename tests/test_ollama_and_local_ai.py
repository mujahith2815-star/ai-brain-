import pytest
from tools.ollama_manager import ollama_local_manager, LocalAIRunnerStatus
from nlp.conversational_agent import conversational_agent

def test_ollama_manager_status_inspection():
    status = ollama_local_manager.inspect_status()
    assert isinstance(status, LocalAIRunnerStatus)
    assert status.is_ready_for_inference is True
    assert status.active_runner_mode in ("OLLAMA_SERVER", "PHASS_NATIVE_NEURAL_LLM (Built-In Zero-Dependency)")
    assert len(status.available_models) > 0

def test_ollama_manager_native_generation_fallback():
    res = ollama_local_manager.generate_response("what is your name and identity")
    assert res.get("done") is True
    assert "response" in res
    assert len(res["response"]) > 0

def test_conversational_ollama_status_directive():
    res = conversational_agent.handle_natural_conversation("check ollama status")
    assert res["handled"] is True
    assert res["type"] == "LOCAL_AI_OLLAMA_STATUS"
    assert "Active Execution Engine" in res["speech_text"]
