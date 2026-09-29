"""
P.H.A.S.S SPHERE — Interactive Command-Line Software.
Terminal software interface for autonomous physical AI control, reasoning, and mission execution.
"""

from __future__ import annotations
import asyncio
import sys
import os
from typing import Any, Dict, List

# Ensure project root in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.cognitive_core import cognitive_core, CognitiveState
from core.goal_manager import GoalState
from world.world_model import world_model
from world.internal_simulation import mental_sandbox
from knowledge.graph import knowledge_graph
from neural.tokenizer import tokenizer
from diagnostics.realtime_monitor import system_monitor
from learning.evaluation import evaluation_framework


from core.version import get_version_banner

async def cli_interactive_loop():
    print(f"\n{get_version_banner()}")
    print("  Type 'help' for commands or enter any natural language directive  ")
    print("=======================================================\n")

    await cognitive_core.boot_sequence()
    await cognitive_core.start_autonomous_loop()

    while True:
        try:
            prompt_str = f"P.H.A.S.S ({cognitive_core.state.value}) > "
            user_input = await asyncio.to_thread(input, prompt_str)
            cmd = user_input.strip()

            if not cmd:
                continue

            if cmd.lower() in ("exit", "quit", "q"):
                print("[P.H.A.S.S] Shutting down autonomous engine...")
                await cognitive_core.stop_autonomous_loop()
                break

            elif cmd.lower() == "help":
                print("""
Available Commands:
  • <natural language text>  - Submit user directive (NLU -> Plan -> Execute)
  • status / telemetry       - Display current robot & system diagnostic status
  • autogoal                 - Trigger proactive auto-goal evaluation
  • kg                       - Inspect Semantic Knowledge Graph triples
  • sim                      - Run forward Mental Sandbox rollout
  • tokens                   - View Token Economics and context budgeting
  • benchmark                - Run automated mission benchmark
  • exit / quit              - Exit CLI software
""")

            elif cmd.lower() in ("status", "telemetry"):
                health = system_monitor.sample_health(cognitive_core.last_anomaly_score)
                print(f"\n--- TELEMETRY & DIAGNOSTICS ---")
                print(f"  • Core State:     {cognitive_core.state.value}")
                print(f"  • Battery Level:  {world_model.robot_state.battery_percentage:.1f}%")
                print(f"  • Internal Temp:  {world_model.robot_state.internal_temp_c:.1f}°C")
                print(f"  • Neural Anomaly: {health.neural_anomaly_score:.4f} ({health.overall_system_status})")
                print(f"  • CPU / RAM:      {health.cpu_percent}% / {health.ram_usage_mb:.0f}MB")
                print(f"  • Active Goals:   {len(cognitive_core.goal_manager.list_active_goals())}\n")

            elif cmd.lower() == "autogoal":
                candidate = cognitive_core.auto_goal_engine.evaluate_proactive_triggers(
                    world_model.robot_state.to_dict(),
                    world_model.get_snapshot(),
                    anomaly_score=0.45,
                    active_goal_count=0,
                )
                if candidate:
                    goal = cognitive_core.auto_goal_engine.trigger_auto_goal(candidate)
                    print(f"\n[AUTO-GOAL DISPATCHED] '{goal.title}' [Priority: {goal.priority.name}]\n")
                else:
                    print("\n[AUTO-GOAL] All systems nominal. No proactive auto-goal required.\n")

            elif cmd.lower() == "kg":
                print(f"\n--- SEMANTIC KNOWLEDGE GRAPH ({len(knowledge_graph.triples)} Triples) ---")
                for t in knowledge_graph.triples[:12]:
                    print(f"  • ({t.subject}) --[{t.relation}]--> ({t.object}) [Conf: {t.confidence:.2f}]")
                print()

            elif cmd.lower() == "sim":
                rollout = mental_sandbox.simulate_plan_rollout(
                    "Simulated Navigation & Diagnostics",
                    [
                        {"title": "LiDAR 360 Sweep", "tool": "sensor_probe"},
                        {"title": "Move to Server Rack", "tool": "robot_move", "parameters": {"target_pos": {"x": 3.0, "y": 2.0}}},
                        {"title": "Inspect Hardware Logs", "tool": "file_reader"},
                    ],
                    world_model.get_snapshot(),
                    [e.to_dict() for e in world_model.entities.values()],
                )
                print(f"\n--- MENTAL SANDBOX ROLLOUT ---")
                print(f"  • Recommendation:      {rollout.recommendation}")
                print(f"  • Success Probability: {int(rollout.overall_success_probability * 100)}%")
                print(f"  • Max Collision Risk:  {rollout.max_collision_risk:.3f}")
                print(f"  • Predicted Energy:    {rollout.total_predicted_energy_wh:.2f} Wh\n")

            elif cmd.lower() == "tokens":
                tel = tokenizer.telemetry.to_dict()
                print(f"\n--- TOKEN ECONOMICS ---")
                print(f"  • Total Processed: {tel['total_tokens_processed']}")
                print(f"  • Prompt Tokens:   {tel['prompt_tokens']}")
                print(f"  • Compl. Tokens:   {tel['completion_tokens']}")
                print(f"  • Context Usage:   {tel['current_context_usage']} / {tel['context_window_limit']} ({tel['context_usage_pct']}%)\n")

            elif cmd.lower() == "physics":
                from world.physics_engine import physics_engine, PhysicsVector3
                physics_engine.body.applied_motor_torque = PhysicsVector3(0.0, 1.2, 0.0) # Apply 1.2 Nm forward torque
                for _ in range(10):
                    b = physics_engine.step_rk4(dt=0.01)
                print(f"\n--- 6-DOF CONTINUOUS PHYSICS DYNAMICS (RK4) ---")
                print(f"  • Position (m):      ({b.position.x:.3f}, {b.position.y:.3f}, {b.position.z:.3f})")
                print(f"  • Linear Vel (m/s):  ({b.linear_velocity.x:.3f}, {b.linear_velocity.y:.3f}, {b.linear_velocity.z:.3f})")
                print(f"  • Angular Vel (rad): ({b.angular_velocity.x:.2f}, {b.angular_velocity.y:.2f})")
                print(f"  • Inertia Tensor I:  {b.moment_of_inertia:.5f} kg*m^2\n")

            elif cmd.lower() in ("voxels", "octomap"):
                from world.octomap_voxels import octomap_voxel_grid
                octomap_voxel_grid.update_raycast_sweep((0.0, 0.0, 0.25), [(2.0, 1.5, 0.5), (-1.5, 2.0, 0.8)])
                occupied = octomap_voxel_grid.get_voxel_snapshot_for_gui(5)
                print(f"\n--- 3D VOLUMETRIC OCTOMAP VOXELS ---")
                print(f"  • Voxel Resolution:  {octomap_voxel_grid.resolution} m")
                print(f"  • Total Tracked:     {len(octomap_voxel_grid.voxels)} voxels")
                for v in occupied:
                    print(f"    • Occupied Voxel at World: {v['world']} [P={v['prob']}]")
                print()

            elif cmd.lower() == "dream":
                from learning.dreamer_engine import dreamer_engine
                reps = dreamer_engine.run_dream_consolidation_cycle(num_episodes=3)
                print(f"\n--- SLEEP & DREAM LATENT REHEARSAL (DreamerV3 RSSM) ---")
                for r in reps:
                    print(f"  • [{r.dream_id}] {r.scenario_name}")
                    print(f"    Steps: {r.imagined_steps_count} | Reward: {r.latent_reward} | EWC Loss: {r.ewc_regularization_loss:.4f}")
                    print(f"    Discovered Policy: \"{r.discovered_recovery_strategy}\"")
                print()

            elif cmd.lower() == "synthesis":
                from tools.code_synthesis import tool_synthesizer
                sample_code = """
def custom_network_probe(query: str = "", options: dict = None) -> dict:
    return {"status": "SUCCESS", "probed_host": "192.168.1.100", "latency_ms": 1.4}
"""
                ok, msg = tool_synthesizer.synthesize_tool("custom_network_probe", "Probes network host latency", sample_code)
                print(f"\n--- AUTONOMOUS TOOL SYNTHESIS ---")
                print(f"  • Status:  {'COMPILED & REGISTERED' if ok else 'FAILED'}")
                print(f"  • Message: {msg}\n")

            elif cmd.lower() == "swarm":
                from swarm.mesh_protocol import swarm_coordinator
                winner, cost = swarm_coordinator.run_contract_net_auction("task-99", "Inspect Solar Sensor", (3.0, 4.0, 0.0))
                print(f"\n--- MULTI-AGENT SWARM AUCTION ---")
                print(f"  • Task:         Inspect Solar Sensor @ (3.0, 4.0)")
                print(f"  • Winning Peer: {winner} (Bid Cost: {cost})\n")

            elif cmd.lower() == "vsa":
                from neural.hyperdimensional import vsa_system
                vec = vsa_system.encode_relational_state("ROBOT", "STATE", "BATTERY")
                matches = vsa_system.query_similarity(vec, top_k=2)
                causal = vsa_system.causal.compute_causal_effect("motor_voltage", "cell_temperature")
                print(f"\n--- 10,000-D HYPERDIMENSIONAL COMPUTING & CAUSAL DO-CALCULUS ---")
                print(f"  • Top VSA Match:     {matches[0][0]} (Cosine Sim: {matches[0][1]})")
                print(f"  • Causal Do-Calculus: {causal['do_calculus_formula']} -> Strength: {causal['causal_effect_estimate']}")
                print(f"  • Notes:             {causal['notes']}\n")

            elif cmd.lower() == "audit":
                from diagnostics.audit_ledger import audit_ledger
                b = audit_ledger.record_decision("MANUAL_AUDIT_PROBE", {"operator": "cli_user"})
                summary = audit_ledger.get_ledger_summary()
                print(f"\n--- CRYPTOGRAPHIC MERKLE AUDIT LEDGER ---")
                print(f"  • Block Index:      {b.index}")
                print(f"  • Merkle Root:      {summary['merkle_root']}")
                print(f"  • Ledger Integrity: {'VALID & TAMPER-PROOF' if summary['is_valid'] else 'INVALID'}\n")

            elif cmd.lower() == "apps":
                from tools.os_controller import os_controller
                print(f"\n--- REGISTERED SYSTEM APPS & LAUNCHERS ---")
                for k, v in os_controller.APP_REGISTRY.items():
                    print(f"  • {k:<12} -> {v['target']} ({v['type']})")
                print("\nUse 'open <app_name>' to launch.\n")

            elif cmd.lower() in ("procs", "processes"):
                from tools.os_controller import os_controller
                procs = os_controller.list_running_processes(max_results=12)
                print(f"\n--- ACTIVE HOST SYSTEM PROCESSES ---")
                for p in procs:
                    print(f"  • PID: {p.pid:<6} | {p.name:<25} | Memory: {p.memory_mb:.1f} MB")
                print()

            elif cmd.lower() in ("sysdiag", "diagnosis", "hardware"):
                from diagnostics.deep_diagnostics import deep_diagnostics
                rep_str = deep_diagnostics.generate_human_readable_report()
                print(f"\n{rep_str}\n")

            elif cmd.lower() == "evolve":
                from learning.self_evolution import self_evolution_engine
                analysis = self_evolution_engine.analyze_self_performance()
                print(f"\n--- RECURSIVE SELF-EVOLUTION ENGINE ---")
                print(f"  • Current Generation:     Gen-{analysis['current_evolution_generation']}")
                print(f"  • Verified Self-Patches:  {analysis['total_verified_self_patches']}")
                print(f"  • Optimization Candidates:")
                for c in analysis['candidate_modules_for_optimization']:
                    print(f"    - {c['module']}: {c['reason']}")
                print()

            elif cmd.lower() == "jarvis":
                from voice.speech_engine import voice_engine
                from jarvis.persona import jarvis_persona
                msg = jarvis_persona.format_greeting("sir")
                voice_engine.speak(msg)
                print(f"\n--- J.A.R.V.I.S. EXECUTIVE CORE ONLINE ---")
                print(f"  • Voice Speech Output: {'MUTED' if voice_engine.is_muted else 'ACTIVE'}")
                print(f"  • Arc-Reactor Core:    NOMINAL")
                print(f"  • Response: \"{msg}\"\n")

            elif cmd.lower().startswith("speak "):
                from voice.speech_engine import voice_engine
                phrase = cmd[6:].strip()
                voice_engine.speak(phrase)
                print(f"\n[JARVIS VOICE SYNTHESIS] \"{phrase}\"\n")

            elif cmd.lower() in ("briefing", "status briefing"):
                from jarvis.protocol_engine import protocol_engine
                res = protocol_engine.execute_protocol("BRIEFING")
                print(f"\n--- J.A.R.V.I.S. EXECUTIVE BRIEFING ---")
                print(f"{res.spoken_narration}\n")

            elif cmd.lower() in ("workspace", "protocol workspace"):
                from jarvis.protocol_engine import protocol_engine
                res = protocol_engine.execute_protocol("WORKSPACE")
                print(f"\n--- PROTOCOL: WORKSPACE INITIALIZED ---")
                for s in res.steps_executed:
                    print(f"  • {s}")
                print()

            elif cmd.lower() in ("security", "protocol security"):
                from jarvis.protocol_engine import protocol_engine
                res = protocol_engine.execute_protocol("SECURITY_SCAN")
                print(f"\n--- PROTOCOL: SECURITY SCAN COMPLETED ---")
                for s in res.steps_executed:
                    print(f"  • {s}")
                print()

            elif cmd.lower() == "screenshot":
                from tools.screen_vision import screen_vision
                ok, path = screen_vision.capture_screenshot()
                print(f"\n--- DESKTOP SCREENSHOT CAPTURED ---")
                print(f"  • Path: {path}\n")

            elif cmd.lower() == "listen":
                from voice.speech_listener import voice_listener
                print("\n[J.A.R.V.I.S. VOICE LISTENER] Listening to microphone (3s)...")
                res = voice_listener.listen_and_transcribe(timeout_sec=3)
                print(f"  • Transcribed Audio: \"{res.text}\" (Confidence: {int(res.confidence*100)}%)\n")
                # Route to cognitive core
                if res.text:
                    c_res = await cognitive_core.submit_user_directive(res.text)
                    print(f"P.H.A.S.S SPHERE: \"{c_res.get('nlg_response')}\"\n")

            elif cmd.lower().startswith("ocr"):
                from perception.vision_ai import vision_ai
                from tools.screen_vision import screen_vision
                ok, path = screen_vision.capture_screenshot()
                analysis = vision_ai.analyze_image_or_screenshot(path)
                print(f"\n--- NEURAL VISION SCENE OCR ---")
                print(f"  • Dominant Scene: {analysis.dominant_scene_type}")
                print(f"  • Detected Text Spans:")
                for t in analysis.detected_texts:
                    print(f"    - [{t.category}] {t.text} (Box: {t.bounding_box})")
                print()

            elif cmd.lower() == "sentinel":
                from core.proactive_sentinel import proactive_sentinel
                snap = proactive_sentinel.get_sentinel_snapshot()
                print(f"\n--- PROACTIVE AUTONOMIC SENTINEL ---")
                print(f"  • Sentinel Daemon: {'ACTIVE' if snap['is_sentinel_active'] else 'STANDBY'}")
                print(f"  • Total Alerts:    {snap['total_alerts_recorded']}")
                print(f"  • Learned Routines:")
                for r in snap['learned_operator_routines']:
                    print(f"    - [{r['time_window']}] {r['predicted_action']}")
                print()

            elif cmd.lower().startswith("sound "):
                from voice.sound_effects import sound_synth
                snd = cmd[6:].strip()
                sound_synth.play_sound(snd)
                print(f"\n[CYBERNETIC AUDIO SYNTHESIS] Playing: {snd}\n")

            elif cmd.lower().startswith("train "):
                from neural.model_trainer import neural_model_trainer
                raw_input = cmd[6:].strip()
                p_text, c_text = (raw_input.split("->", 1) if "->" in raw_input else (raw_input, "Target neural response verified."))
                print(f"\n[NEURAL MLLM TRAINER] Training neural weights on: \"{p_text.strip()}\"...")
                metrics = neural_model_trainer.train_on_text(p_text.strip(), c_text.strip(), epochs=6, lr=0.02)
                chk = neural_model_trainer.save_checkpoint()
                print(f"  • Epochs:         {metrics.epoch}")
                print(f"  • Initial Loss:   {metrics.initial_loss:.4f}")
                print(f"  • Final Loss:     {metrics.final_loss:.4f}")
                print(f"  • Loss Reduction: {metrics.loss_reduction_pct:.1f}%")
                print(f"  • Tokens:         {metrics.total_tokens_trained}")
                print(f"  • LoRA Weights:   {metrics.lora_parameters_updated} params")
                print(f"  • Checkpoint:     {chk}\n")

            elif cmd.lower().startswith("cyber"):
                from security.cyber_defense import cyber_defense
                print("\n[CYBER DEFENSE SUITE] Initiating network security scan & vulnerability audit...")
                rep = cyber_defense.run_full_security_audit()
                print(f"\n{cyber_defense.format_audit_report_text(rep)}\n")

            elif cmd.lower() in ("omni", "unified", "architecture"):
                from core.unified_orchestrator import unified_orchestrator
                st = unified_orchestrator.get_unified_status()
                print(f"\n=== P.H.A.S.S SPHERE v{st.version} UNIFIED ARCHITECTURE ===")
                print(f"  • Architecture: {st.architecture}")
                print(f"  • Uptime:       {st.uptime_sec:.1f}s | Battery: {st.robot_battery_pct}% | Temp: {st.robot_internal_temp_c}°C")
                print(f"  • Security:     {st.cyber_security_score}/100 | Goals: {st.total_goals_executed}")
                print(f"  • Integrated Subsystems:")
                for k, v in st.subsystems_online.items():
                    print(f"    - {k.replace('_', ' ')}: {'ONLINE' if v else 'OFFLINE'}")
                print()

            elif cmd.lower() == "benchmark":
                from run_simulation import run_benchmark_mission
                await run_benchmark_mission()

            else:
                # Direct Natural Language Directive
                res = await cognitive_core.submit_user_directive(cmd)
                nlu = res.get("nlu", {})
                nlg = res.get("nlg_response", "Directive registered.")
                print(f"\n[NLU Intent: {nlu.get('intent', 'GENERAL')} (Confidence: {nlu.get('intent_confidence', 0.9):.2f})]")
                print(f"P.H.A.S.S SPHERE: \"{nlg}\"\n")

        except Exception as e:
            print(f"[ERROR] {e}")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--benchmark":
        from run_simulation import run_benchmark_mission
        asyncio.run(run_benchmark_mission())
    else:
        asyncio.run(cli_interactive_loop())


if __name__ == "__main__":
    main()
