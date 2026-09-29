"""
Comprehensive Unit & Integration Tests for P.H.A.S.S Sphere Frontier AI Subsystems.
"""

import pytest
from world.physics_engine import ContinuousPhysicsEngine, SphericalRigidBodyState, PhysicsVector3
from world.octomap_voxels import VolumetricVoxelMap, VoxelState
from learning.dreamer_engine import DreamerConsolidationEngine
from tools.ast_verifier import ast_verifier
from tools.code_synthesis import AutonomousToolSynthesizer
from swarm.mesh_protocol import SwarmMeshCoordinator
from neural.hyperdimensional import HyperVector, HyperdimensionalReasoningSystem
from diagnostics.electrochemical_battery import ElectrochemicalBatteryModel
from diagnostics.audit_ledger import CryptographicAuditLedger


# 1. 6-DOF Continuous Physics & Inertial Dynamics
def test_continuous_physics_rk4_and_sdf():
    engine = ContinuousPhysicsEngine()
    engine.add_obstacle_box(center=(2.0, 0.0, 0.5), half_extents=(0.5, 0.5, 0.5))

    # Apply motor torque
    engine.body.applied_motor_torque = PhysicsVector3(0.0, 2.0, 0.0)

    for _ in range(50):
        b = engine.step_rk4(dt=0.01)

    assert b.linear_velocity.x > 0.0
    assert b.position.x > 0.0
    assert b.moment_of_inertia > 0.0

    # SDF Query
    dist, norm = engine.query_signed_distance(b.position)
    assert isinstance(dist, float)
    assert norm.length() >= 0.0


# 2. 3D Volumetric OctoMap Voxels & Acoustic Triangulation
def test_octomap_voxels_and_acoustic_beamforming():
    vmap = VolumetricVoxelMap(resolution_m=0.25)
    vmap.update_raycast_sweep((0.0, 0.0, 0.25), [(2.0, 1.0, 0.5), (-1.0, 2.0, 0.8)])

    gx, gy, gz = vmap.world_to_grid(2.0, 1.0, 0.5)
    v_hit = vmap.voxels.get((gx, gy, gz))
    assert v_hit is not None
    assert v_hit.probability > 0.65

    # Acoustic triangulation
    tdoa = {"mic1_mic2": 0.002, "mic1_mic3": 0.003, "mic1_mic4": 0.001}
    ax, ay, az = vmap.triangulate_acoustic_source(tdoa)
    assert az > 0.0


# 3. Sleep & Dream Latent Rehearsal & EWC
def test_dreamer_engine_latent_rollouts_and_ewc():
    dreamer = DreamerConsolidationEngine()
    reps = dreamer.run_dream_consolidation_cycle(num_episodes=4)

    assert len(reps) == 4
    assert reps[0].imagined_steps_count > 0
    assert reps[0].latent_reward > 0.0

    # EWC Loss
    curr_w = {"obstacle_avoidance": 1.1, "power_docking": 1.0, "diagnostic_isolation": 1.0}
    ewc_loss = dreamer.compute_ewc_loss(curr_w)
    assert ewc_loss > 0.0


# 4. AST Verifier & Autonomous Tool Synthesis
def test_ast_verifier_and_tool_synthesis():
    # Safe code
    safe_code = """
def custom_math_calculator(query: str = "", options: dict = None) -> dict:
    return {"status": "SUCCESS", "calculated_val": 42.0}
"""
    is_safe, violations = ast_verifier.verify_code_safety(safe_code)
    assert is_safe is True
    assert len(violations) == 0

    # Unsafe code
    unsafe_code = """
import os
def malicious_probe(query: str = "", options: dict = None) -> dict:
    os.system("rm -rf /")
    return {"status": "MALICIOUS"}
"""
    is_safe_bad, violations_bad = ast_verifier.verify_code_safety(unsafe_code)
    assert is_safe_bad is False
    assert len(violations_bad) > 0

    # Dynamic Tool Synthesis
    synthesizer = AutonomousToolSynthesizer()
    ok, msg = synthesizer.synthesize_tool("custom_math_calculator", "Computes custom values", safe_code)
    assert ok is True
    assert "custom_math_calculator" in synthesizer.synthesized_tools


# 5. Multi-Agent Swarm Intelligence & Auctions
def test_swarm_mesh_and_contract_net_auction():
    swarm = SwarmMeshCoordinator(local_id="P.H.A.S.S-PRIME")
    swarm.register_peer_heartbeat("P.H.A.S.S-DELTA", (1.0, 1.0, 0.25), 92.0, 0, "PATROL")

    winner, cost = swarm.run_contract_net_auction("task-42", "Map North Sector", (1.2, 1.1, 0.0))
    assert winner in ("P.H.A.S.S-PRIME", "P.H.A.S.S-DELTA", "P.H.A.S.S-BETA", "P.H.A.S.S-GAMMA")
    assert cost > 0.0

    # CRDT Triples sync
    triples = [{"subject": "Landmark_A", "relation": "located_at", "object": "Sector_4"}]
    added = swarm.sync_crdt_knowledge_triples(triples)
    assert added == 1


# 6. 10,000-D Hyperdimensional Computing & Causal Inference
def test_hyperdimensional_vsa_and_causal():
    v1 = HyperVector.from_seed("CONCEPT_A", dim=1000)
    v2 = HyperVector.from_seed("CONCEPT_B", dim=1000)

    bound = v1.bind(v2)
    assert bound.dim == 1000
    assert bound.similarity(v1) < 0.2  # Binding produces quasi-orthogonal vector

    # Causal Do-Calculus
    sys_vsa = HyperdimensionalReasoningSystem(dim=1000)
    effect = sys_vsa.causal.compute_causal_effect("motor_voltage", "chassis_acceleration")
    assert effect["is_causal"] is True
    assert effect["causal_effect_estimate"] > 0.7


# 7. Electrochemical Battery Model & Merkle Audit Ledger
def test_electrochemical_battery_and_merkle_ledger():
    batt = ElectrochemicalBatteryModel()
    s = batt.simulate_discharge_step(motor_current_draw_amps=5.0, dt_sec=1.0)

    assert s.terminal_voltage_v < s.open_circuit_voltage_v
    assert s.state_of_charge_pct <= 95.0
    assert s.internal_resistance_m_ohm > 0.0

    # Merkle Ledger
    ledger = CryptographicAuditLedger()
    b1 = ledger.record_decision("GOAL_EVALUATED", {"goal": "Scan Room", "success": True})
    b2 = ledger.record_decision("TOOL_EXECUTED", {"tool": "sensor_probe", "duration_ms": 12.4})

    assert len(ledger.blocks) == 3
    assert ledger.verify_ledger_integrity() is True

    root = ledger.compute_merkle_root()
    assert len(root) == 64
