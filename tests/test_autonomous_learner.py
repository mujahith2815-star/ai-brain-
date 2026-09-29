"""
Unit & Integration Tests for Autonomous Self-Research, Neural Learning & Skill Synthesizer.
"""

import os
import sys
import pytest
from learning.autonomous_learner import autonomous_learner
from nlp.conversational_agent import conversational_agent


# 1. Autonomous 5-Phase Self-Learning Pipeline
def test_autonomous_learner_pipeline():
    record = autonomous_learner.learn_and_synthesize_skill("quantum computing simulation")

    assert record.skill_id.startswith("skill_")
    assert record.module_name == "learned_quantum_computing_simulation"
    assert os.path.exists(record.file_path)
    assert record.hot_loaded is True
    assert record.verification_passed is True
    assert record.training_metrics.epoch == 6
    assert record.training_metrics.loss_reduction_pct >= 0.0

    # Verify that the hot-injected module can be called directly in memory
    assert "learned_quantum_computing_simulation" in sys.modules
    mod = sys.modules["learned_quantum_computing_simulation"]
    assert hasattr(mod, "run_skill")
    res = mod.run_skill("qubit_state_alpha", entanglement="bell_state")
    assert res["status"] == "SUCCESS"
    assert "Quantum Computing Simulation" in res["skill"]


# 2. Conversational Natural Language Trigger
def test_conversational_autonomous_learning():
    query = "learn how to analyze stock market trends"
    res = conversational_agent.handle_natural_conversation(query)

    assert res is not None
    assert res["handled"] is True
    assert res["type"] == "AUTONOMOUS_SKILL_SYNTHESIS"
    assert "learned_how_to_analyze_stock_market_tr" in res["speech_text"] or "stock" in res["speech_text"].lower()

    # Formatted report text
    txt = autonomous_learner.format_skill_report_text(autonomous_learner.skills_registry[list(autonomous_learner.skills_registry.keys())[-1]])
    assert "SELF-EXPANSION REPORT" in txt
