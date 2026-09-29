"""
Unit & Integration Tests for P.H.A.S.S Sphere v4.0:
Humanoid Cognitive Substrate, Theory of Mind, In-Memory Hot-Coding, and Consciousness Stream.
"""

import pytest
from learning.hot_coder import hot_coder
from core.humanoid_cognition import humanoid_cognition
from neural.consciousness_stream import consciousness_stream
from nlp.conversational_agent import conversational_agent
from core.version import VERSION, VERSION_CODENAME


# 1. Version 4.0 Platform Verification
def test_v4_version_metadata():
    assert VERSION in ("4.0.0", "5.0.0", "6.0.0", "7.0.0", "8.0.0")
    assert any(k in VERSION_CODENAME for k in ("Humanoid", "Apex Sovereign", "Supreme Sovereign", "Zenith Omnipresence", "Apex Nexus Singularity"))


# 2. In-Memory Hot-Coding & AST Live Patching
def test_runtime_hot_coder():
    # Inject a new live function into dynamic module
    code = """
def dynamic_hypotenuse(a, b):
    import math
    return math.sqrt(a*a + b*b)
"""
    ok, msg = hot_coder.hot_inject_function("dynamic_sandbox_math", "dynamic_hypotenuse", code)
    assert ok is True

    import sys
    assert "dynamic_sandbox_math" in sys.modules
    mod = sys.modules["dynamic_sandbox_math"]
    assert hasattr(mod, "dynamic_hypotenuse")
    assert mod.dynamic_hypotenuse(3, 4) == 5.0

    # Evaluate dynamic expression snippet
    ok_e, val, msg_e = hot_coder.hot_execute_snippet("25 * 4 + 10")
    assert ok_e is True
    assert val == 110


# 3. Humanoid Cognitive Substrate & Theory of Mind
def test_humanoid_cognition_and_tom():
    # Record episode
    ep = humanoid_cognition.record_episode(
        event_type="COLLABORATIVE_TASK",
        summary="Synthesized custom remote controller on screen.",
        emotional_valence=0.9,
        operator_intent="OPERATE_SMART_DEVICES",
    )
    assert ep.episode_id.startswith("ep_")
    assert ep.emotional_valence == 0.9

    # Theory of mind intent update
    tom = humanoid_cognition.update_theory_of_mind("make a cyber matrix game")
    assert tom.current_focus_domain == "DEVELOPMENT_AND_MAKER"
    assert tom.estimated_cognitive_load > 0.5
    assert len(tom.anticipatory_suggestion) > 0


# 4. Stream of Consciousness & Neural Monologue
def test_consciousness_stream():
    thought = consciousness_stream.generate_current_thought()
    assert thought.thought_id.startswith("th_")
    assert 0.0 <= thought.intensity <= 1.0

    txt = consciousness_stream.format_stream_text(limit=3)
    assert "STREAM OF CONSCIOUSNESS" in txt


# 5. Conversational v4.0 Directives
def test_conversational_v4_directives():
    # A. Hot-coding execution
    res_h = conversational_agent.handle_natural_conversation("hotcode val = 12 * 12; val")
    assert res_h is not None
    assert res_h["type"] == "RUNTIME_HOT_CODE"
    assert res_h["action_executed"] == "IN_MEMORY_HOT_CODE_EXECUTION"

    # B. Theory of mind
    res_t = conversational_agent.handle_natural_conversation("theory of mind")
    assert res_t is not None
    assert res_t["type"] == "THEORY_OF_MIND"

    # C. Episodic memory
    res_m = conversational_agent.handle_natural_conversation("what do you remember about us")
    assert res_m is not None
    assert res_m["type"] == "EPISODIC_MEMORY"

    # D. Consciousness stream
    res_c = conversational_agent.handle_natural_conversation("what are you thinking right now")
    assert res_c is not None
    assert res_c["type"] == "CONSCIOUSNESS_STREAM"
