"""
Comprehensive Unit & Integration Tests for P.H.A.S.S Sphere Advanced AI Subsystems.
"""

import pytest
import asyncio
from neural.tensor import Tensor, DenseLayer, relu, sigmoid, softmax
from neural.models import fusion_network, anomaly_autoencoder, state_value_network
from neural.tokenizer import tokenizer
from knowledge.graph import knowledge_graph
from knowledge.ontology import ontology_engine
from world.internal_simulation import mental_sandbox
from core.auto_goal_engine import ProactiveAutoGoalEngine, AutoGoalTriggerType
from core.reasoning_advanced import advanced_reasoning
from core.planning_advanced import htn_planner
from core.goal_manager import GoalManager, GoalPriority, GoalState
from learning.meta_cognition import meta_cognition
from learning.reinforcement import replay_buffer
from diagnostics.realtime_monitor import system_monitor
from diagnostics.self_healer import self_healer


# 1. Neural Systems & Tensors
def test_tensor_operations_and_activations():
    t = Tensor([[1.0, 2.0], [3.0, 4.0]])
    vec = [1.0, 1.0]
    out = t.dot(vec)
    assert out == [3.0, 7.0]

    assert relu([-2.0, 3.0]) == [0.0, 3.0]
    assert 0.45 < sigmoid([0.0])[0] < 0.55
    sm = softmax([1.0, 1.0])
    assert abs(sum(sm) - 1.0) < 1e-4


def test_multimodal_neural_fusion_and_autoencoder():
    v_vec = [0.2] * 32
    lidar = [1.5] * 32
    imu = {"linear_acceleration": {"ax": 0.0, "ay": 0.0, "az": 9.81}, "angular_velocity_radps": {"gx": 0, "gy": 0, "gz": 0}}

    fused_state = fusion_network.forward(v_vec, lidar, imu, 95.0, 31.0)
    assert len(fused_state) == 64

    # Anomaly Score
    anomaly_score, reconstruction = anomaly_autoencoder.compute_anomaly_score(fused_state)
    assert 0.0 <= anomaly_score <= 1.0
    assert len(reconstruction) == 64

    # State Value Evaluation
    val_out = state_value_network.evaluate_state(fused_state)
    assert "expected_reward" in val_out
    assert "feasibility_score" in val_out
    assert "safety_risk_index" in val_out


def test_subword_tokenizer_and_token_budget():
    text = "The autonomous spherical robot executes diagnostic plan."
    tokens = tokenizer.encode(text)
    assert len(tokens) > 0

    dec = tokenizer.decode(tokens)
    assert len(dec) > 0

    # Budget tracking
    tel = tokenizer.record_usage("Prompt", "Completion")
    assert tel.total_tokens_processed > 0


# 2. Knowledge Graph & Ontology
def test_knowledge_graph_and_shortest_path():
    knowledge_graph.add_triple("Sensor_LiDAR", "mounted_on", "Chassis_Core", 1.0)
    knowledge_graph.add_triple("Chassis_Core", "part_of", "PHASS_Sphere", 1.0)

    path = knowledge_graph.find_shortest_path("Sensor_LiDAR", "PHASS_Sphere")
    assert len(path) == 2
    assert path[0][0] == "Sensor_LiDAR"
    assert path[1][2] == "PHASS_Sphere"

    viz_data = knowledge_graph.get_graph_visualization_data()
    assert len(viz_data["nodes"]) > 0
    assert len(viz_data["links"]) > 0


def test_ontology_semantic_inference():
    inferred = ontology_engine.infer_new_triples()
    assert isinstance(inferred, list)


# 3. Mental Sandbox Forward World Simulation
def test_mental_sandbox_rollout():
    plan_actions = [
        {"title": "Inspect Area", "tool": "sensor_probe"},
        {"title": "Drive Forward", "tool": "robot_move", "parameters": {"target_pos": {"x": 2.0, "y": 1.0}}},
    ]
    obstacles = [{"name": "Wall_Obstacle", "position": {"x": 2.1, "y": 1.0}, "radius_m": 0.4}]
    current_state = {"robot_state": {"position": {"x": 0.0, "y": 0.0, "z": 0.25}, "battery_percentage": 90.0}}

    rollout = mental_sandbox.simulate_plan_rollout("Test Move", plan_actions, current_state, obstacles)
    assert rollout.total_steps == 2
    assert rollout.recommendation in ("PROCEED_SAFE", "PROCEED_WITH_CAUTION", "ABORT_UNSAFE")
    assert rollout.total_predicted_energy_wh > 0.0


# 4. Proactive Auto-Goal Engine
def test_proactive_auto_goal_generation():
    gm = GoalManager()
    engine = ProactiveAutoGoalEngine(gm)

    # 1. Low battery condition
    cand_batt = engine.evaluate_proactive_triggers(
        {"battery_percentage": 15.0, "internal_temp_c": 30.0}, {}, anomaly_score=0.04, active_goal_count=0
    )
    assert cand_batt is not None
    assert cand_batt.trigger_type == AutoGoalTriggerType.POWER_MANAGEMENT
    assert cand_batt.priority == GoalPriority.CRITICAL

    # 2. High anomaly condition
    cand_anom = engine.evaluate_proactive_triggers(
        {"battery_percentage": 85.0, "internal_temp_c": 30.0}, {}, anomaly_score=0.45, active_goal_count=0
    )
    assert cand_anom is not None
    assert cand_anom.trigger_type == AutoGoalTriggerType.SENSORY_ANOMALY


# 5. Multi-Paradigm Reasoning & Hierarchical Planning
def test_multi_paradigm_reasoning():
    out = advanced_reasoning.synthesize_comprehensive_reasoning(
        "Diagnose Service Crash", ["Server_Rack_Storage", "PHASS_Sphere"]
    )
    assert len(out.deductive_conclusions) > 0
    assert len(out.inductive_patterns) > 0
    assert len(out.abductive_hypotheses) > 0
    assert len(out.counterfactual_analyses) > 0
    assert "branch_name" in out.tree_of_thought_best_branch


def test_htn_planner_and_dynamic_replanning():
    subtasks = htn_planner.decompose_goal_htn("Analyze system failure", {})
    assert len(subtasks) == 4

    # Test Dynamic Replan on failure
    gm = GoalManager()
    goal = gm.create_goal("Test Goal", "Test Goal Description")
    goal.subtasks = subtasks
    failed_step = subtasks[1]

    replanned = htn_planner.dynamic_replan_on_failure(goal, failed_step, "Connection Timeout")
    assert any("Self-Healing Diagnostic Recovery" in st.title for st in replanned)


# 6. Meta-Cognition & Reinforcement
def test_meta_cognition_and_reinforcement_replay():
    ref = meta_cognition.evaluate_completed_goal(
        goal_id="g-101",
        goal_title="Diagnostic Routine",
        predicted_confidence=0.92,
        success=True,
        subtasks_count=3,
    )
    assert ref.calibration_error < 0.15
    assert "Accurate" in ref.self_critique

    # Replay buffer
    replay_buffer.store_transition("state_idle", "system_diagnostics", 1.0, "state_success", True)
    assert len(replay_buffer.buffer) > 0
    best_act, q_val = replay_buffer.get_best_action_for_state("state_idle", ["system_diagnostics", "robot_move"])
    assert best_act == "system_diagnostics"
    assert q_val > 0.0


# 7. Real-Time Diagnostics & Self-Healing
def test_diagnostics_monitor_and_self_healing():
    health = system_monitor.sample_health(neural_anomaly=0.05)
    assert health.active_threads_count > 0
    assert health.overall_system_status == "HEALTHY"

    heal_log = self_healer.attempt_self_heal("sensor_lag_detected", {})
    assert heal_log.status == "HEALED_SUCCESS"
    assert len(self_healer.get_recent_healing_logs(1)) > 0
