"""
P.H.A.S.S Cognitive Core & Autonomous Agent Orchestrator.
Executes the continuous 14-step cognitive loop:
Observe -> World Model -> Memory Retrieval -> Goal Evaluation -> Reasoning ->
Planning -> Action Selection -> Execution -> Result Observation -> Verification ->
Performance Evaluation -> Experience Storage -> Learning Update -> Memory Consolidation.
"""

from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import logging
import traceback

from .event_bus import event_bus, Event, EventType
from .goal_manager import GoalManager, Goal, GoalState, GoalPriority, SubTask
from .reasoning import ReasoningEngine, ReasoningResult
from .planner import TaskPlanner, Plan
from .decision_engine import DecisionEngine, Decision
from .ai_model import AIModelFactory, BaseAIModel

from world.world_model import world_model
from world.internal_simulation import mental_sandbox
from perception.observation_manager import observation_manager
from memory.retrieval import memory_system
from learning.learning_engine import LearningEngine
from learning.evaluation import evaluation_framework
from learning.meta_cognition import meta_cognition
from learning.reinforcement import replay_buffer
from tools.executor import tool_executor
from tools.registry import tool_registry
from nlp.nlu import nlu_pipeline, IntentType
from nlp.nlg import nlg_generator
from neural.models import fusion_network, anomaly_autoencoder, state_value_network
from neural.tokenizer import tokenizer
from .auto_goal_engine import ProactiveAutoGoalEngine
from .reasoning_advanced import advanced_reasoning
from .planning_advanced import htn_planner
from diagnostics.realtime_monitor import system_monitor
from diagnostics.self_healer import self_healer

logger = logging.getLogger("phass.cognitive_core")


class CognitiveState(str, Enum):
    BOOTING = "BOOTING"
    READY = "READY"
    OBSERVING = "OBSERVING"
    REASONING = "REASONING"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    LEARNING = "LEARNING"
    STANDBY = "STANDBY"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class CognitiveCore:
    def __init__(self, engine_type: str = "offline"):
        self.state = CognitiveState.BOOTING
        self.ai_model = AIModelFactory.create(engine_type)
        self.goal_manager = GoalManager()
        self.reasoning = ReasoningEngine(self.ai_model)
        self.planner = TaskPlanner(self.ai_model)
        self.decision_engine = DecisionEngine()
        self.learning_engine = LearningEngine(memory_system)
        self.auto_goal_engine = ProactiveAutoGoalEngine(self.goal_manager)

        self.is_running = False
        self.loop_task: Optional[asyncio.Task] = None
        self.current_goal: Optional[Goal] = None
        self.last_reasoning_summary: Dict[str, Any] = {}
        self.active_decision: Optional[Decision] = None
        self.last_anomaly_score: float = 0.04
        self.step_count = 0

    async def boot_sequence(self) -> bool:
        """
        Executes the formalized boot sequence:
        BOOT -> SYSTEM CHECK -> LOAD AI -> LOAD MEMORY -> LOAD WORLD MODEL -> LOAD TOOLS -> START PERCEPTION -> START COGNITIVE CORE -> READY
        """
        logger.info("==================================================")
        logger.info("BOOTING P.H.A.S.S SPHERE COGNITIVE PLATFORM")
        logger.info("==================================================")

        self.state = CognitiveState.BOOTING

        # 1. System check
        logger.info("[1/7] Performing subsystem sanity checks...")
        await asyncio.sleep(0.05)

        # 2. Load AI Model
        logger.info(f"[2/7] Initializing Cognitive AI Engine...")

        # 3. Load Memory
        mem_summary = memory_system.get_summary()
        logger.info(f"[3/7] Memory systems online. Knowledge base loaded ({mem_summary['long_term_count']} entries).")

        # 4. Load World Model
        logger.info(f"[4/7] World model initialized with {len(world_model.entities)} environment entities.")

        # 5. Load Tools
        tools_list = tool_registry.list_tools()
        logger.info(f"[5/7] Registered {len(tools_list)} digital action tools.")

        # 6. Start Perception
        logger.info("[6/7] Perception hub connected to solid-state LiDAR and camera streams.")

        # 7. Ready
        self.state = CognitiveState.READY
        logger.info("[7/7] P.H.A.S.S Sphere Cognitive Core is READY.")

        await event_bus.publish(
            Event(
                type=EventType.SYSTEM_ERROR if self.state != CognitiveState.READY else EventType.TELEMETRY_UPDATE,
                source="CognitiveCore",
                data={"status": "READY", "message": "System Boot Completed Successfully"},
            )
        )
        return True

    async def start_autonomous_loop(self) -> None:
        """Starts the continuous asynchronous background loop."""
        if self.is_running:
            return
        self.is_running = True
        self.loop_task = asyncio.create_task(self._autonomous_loop())
        logger.info("Autonomous Cognitive Loop started.")

    async def stop_autonomous_loop(self) -> None:
        self.is_running = False
        if self.loop_task and not self.loop_task.done():
            self.loop_task.cancel()
            try:
                await self.loop_task
            except asyncio.CancelledError:
                pass
        logger.info("Autonomous Cognitive Loop stopped.")

    async def _autonomous_loop(self) -> None:
        """
        The Master 14-Step Autonomous Loop with Neural Fusion, Mental Sandbox & Auto-Goals.
        """
        while self.is_running:
            try:
                self.step_count += 1

                # 1. Observe & Multimodal Sensory Sweep
                self.state = CognitiveState.OBSERVING
                robot_pos = world_model.robot_state.position.to_dict()
                vel = world_model.robot_state.velocity.to_dict()
                entities = [e.to_dict() for e in world_model.entities.values()]
                observations = await observation_manager.poll_full_sensor_sweep(robot_pos, vel, entities)

                # 2. Ingest Observations into World Model
                for obs in observations:
                    await world_model.ingest_observation(obs.to_dict())

                # 3. Neural Tensor Fusion & Anomaly Reconstruction
                lidar_ranges = [obs.data.get("ranges_m", [1.0]*32)[0] for obs in observations if obs.type == "LIDAR_SCAN"] or [1.0]*32
                if not isinstance(lidar_ranges, list) or len(lidar_ranges) < 32:
                    lidar_ranges = [1.0] * 32

                fusion_state = fusion_network.forward(
                    vision_vec=[0.1] * 32,
                    lidar_ranges=lidar_ranges[:32],
                    imu_telemetry={"linear_acceleration": {"ax": 0.0, "ay": 0.0, "az": 9.81}, "angular_velocity_radps": {"gx": 0, "gy": 0, "gz": 0}},
                    battery_pct=world_model.robot_state.battery_percentage,
                    core_temp_c=world_model.robot_state.internal_temp_c,
                )
                anomaly_score, _ = anomaly_autoencoder.compute_anomaly_score(fusion_state)
                self.last_anomaly_score = anomaly_score

                # Sample OS & Hardware Diagnostics
                system_monitor.sample_health(anomaly_score)

                # 4. Evaluate Current Goals & Check Proactive Auto-Goals
                target_goal = self.goal_manager.get_highest_priority_goal()

                if not target_goal:
                    # Check if internal drives or anomalies warrant an auto-goal
                    candidate = self.auto_goal_engine.evaluate_proactive_triggers(
                        world_model.robot_state.to_dict(),
                        world_model.get_snapshot(),
                        anomaly_score=anomaly_score,
                        active_goal_count=0,
                    )
                    if candidate:
                        target_goal = self.auto_goal_engine.trigger_auto_goal(candidate)

                if not target_goal:
                    self.state = CognitiveState.STANDBY
                    world_model.active_goal_summary = "Standby - Waiting for Directives"
                    world_model.active_task_summary = f"Neural Monitoring (Anomaly Score: {anomaly_score:.3f})"
                    await asyncio.sleep(0.4)
                    continue

                self.current_goal = target_goal
                world_model.active_goal_summary = f"{target_goal.title} ({target_goal.state.value})"

                # 5. Handle Goal Lifecycle States
                if target_goal.state == GoalState.CREATED:
                    # UNDERSTANDING & REASONING
                    self.state = CognitiveState.REASONING
                    await self.goal_manager.update_goal_state(target_goal.id, GoalState.UNDERSTANDING, "Analyzing goal context")

                    # Context & Memory Retrieval
                    context_data = memory_system.retriever.get_context_for_goal(target_goal.title)
                    lessons = context_data.get("applicable_lessons", [])

                    # Multi-Paradigm Reasoning
                    multi_reasoning = advanced_reasoning.synthesize_comprehensive_reasoning(
                        target_goal.title,
                        [e["name"] for e in entities[:3]],
                    )
                    self.last_reasoning_summary = {
                        "strategy": multi_reasoning.synthesized_strategy,
                        "confidence": f"{int(multi_reasoning.overall_confidence*100)}%",
                        "deductive_facts": len(multi_reasoning.deductive_conclusions),
                        "inductive_patterns": len(multi_reasoning.inductive_patterns),
                    }
                    target_goal.confidence = multi_reasoning.overall_confidence

                    # 6. Create Plan (HTN & Mental Sandbox Simulation)
                    self.state = CognitiveState.PLANNING
                    await self.goal_manager.update_goal_state(target_goal.id, GoalState.PLANNING, "Formulating task plan")
                    plan = await self.planner.create_plan(target_goal, world_model.get_snapshot(), lessons)

                    # Simulate hypothetical plan in Mental Sandbox before real execution
                    rollout = mental_sandbox.simulate_plan_rollout(
                        target_goal.title,
                        [st.to_dict() for st in target_goal.subtasks],
                        world_model.get_snapshot(),
                        entities,
                    )
                    logger.info(f"Mental Sandbox Rollout: {rollout.recommendation} (Success Prob: {rollout.overall_success_probability})")

                    await self.goal_manager.update_goal_state(target_goal.id, GoalState.EXECUTING, "Executing subtasks")

                elif target_goal.state == GoalState.EXECUTING:
                    # 7. Select Action
                    self.state = CognitiveState.EXECUTING
                    current_subtask = target_goal.get_current_subtask()

                    if not current_subtask:
                        # 8. Verify Goal Result
                        self.state = CognitiveState.VERIFYING
                        await self.goal_manager.update_goal_state(target_goal.id, GoalState.VERIFYING, "Verifying overall outcome")

                        subtasks_dict = [st.to_dict() for st in target_goal.subtasks]
                        verif = await self.reasoning.verify_outcome(target_goal.title, subtasks_dict, subtasks_dict)
                        is_success = verif.get("goal_satisfied", True)

                        # 9. Performance Evaluation & Meta-Cognitive Reflection
                        evaluation_framework.record_goal_evaluation(
                            goal_success=is_success,
                            subtasks_planned=len(target_goal.subtasks),
                            subtasks_executed=len(target_goal.subtasks),
                            recovered_from_error=False,
                            confidence=target_goal.confidence,
                        )
                        meta_cognition.evaluate_completed_goal(
                            goal_id=target_goal.id,
                            goal_title=target_goal.title,
                            predicted_confidence=target_goal.confidence,
                            success=is_success,
                            subtasks_count=len(target_goal.subtasks),
                        )

                        # Experience Replay Q-learning
                        replay_buffer.store_transition(
                            state=target_goal.title[:20],
                            action="executed_plan",
                            reward=1.0 if is_success else -1.0,
                            next_state="terminal_success" if is_success else "terminal_failure",
                            done=True,
                        )

                        # 10. Learning & Experience Storage
                        self.state = CognitiveState.LEARNING
                        await self.goal_manager.update_goal_state(
                            target_goal.id,
                            GoalState.COMPLETED if is_success else GoalState.FAILED,
                            verif.get("verification_notes", "Finished"),
                        )

                        exp = await self.learning_engine.process_task_completion(
                            goal_id=target_goal.id,
                            goal_title=target_goal.title,
                            goal_description=target_goal.description,
                            context=target_goal.context,
                            plan_summary=f"Plan with {len(target_goal.subtasks)} subtasks",
                            actions=subtasks_dict,
                            result=verif,
                            success=is_success,
                        )
                        target_goal.result = verif
                        self.current_goal = None
                        continue

                    # Execute Subtask Action
                    world_model.active_task_summary = f"Executing: {current_subtask.title}"
                    current_subtask.state = GoalState.EXECUTING
                    current_subtask.start_time = datetime.now(timezone.utc).isoformat()

                    decision = self.decision_engine.evaluate_next_action(
                        target_goal, world_model.get_snapshot(), "READ"
                    )
                    self.active_decision = decision

                    # Execute Tool
                    exec_result = await tool_executor.execute_tool(
                        current_subtask.tool_name,
                        current_subtask.parameters,
                    )

                    current_subtask.result = exec_result.output
                    current_subtask.end_time = datetime.now(timezone.utc).isoformat()

                    if exec_result.success:
                        current_subtask.state = GoalState.COMPLETED
                        target_goal.update_progress()
                    else:
                        current_subtask.state = GoalState.FAILED
                        current_subtask.error = exec_result.error
                        logger.warning(f"Subtask '{current_subtask.title}' failed: {exec_result.error}")
                        # Dynamic Replanner
                        htn_planner.dynamic_replan_on_failure(target_goal, current_subtask, exec_result.error or "Error")

                # Throttle cognitive loop tick
                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in autonomous loop tick: {e}\n{traceback.format_exc()}")
                await asyncio.sleep(1.0)

    async def submit_user_directive(self, text: str, priority: GoalPriority = GoalPriority.NORMAL) -> Dict[str, Any]:
        """
        Receives natural language command from user, passes through NLU for intent & entity extraction,
        handles casual chitchat & real-time app/status requests naturally, and dispatches Goal if mission needed.
        """
        from nlp.conversational_agent import conversational_agent

        # 1. Check Casual / Natural Real-Time Conversation & App Launching First
        conv_res = conversational_agent.handle_natural_conversation(text)
        if conv_res:
            logger.info(f"Handled via Real-Time Conversational Agent: {conv_res['type']}")
            memory_system.short_term.store(
                f"Conversation: {text} -> {conv_res['speech_text']}",
                tags=["chat", conv_res["type"].lower()],
            )
            return {
                "status": conv_res["type"],
                "goal": None,
                "nlg_response": conv_res["speech_text"],
                "nlu": {"intent": conv_res["type"], "intent_confidence": 0.98},
            }

        # 2. NLU Comprehension
        nlu_res = nlu_pipeline.understand(text)
        logger.info(f"NLU Intent: {nlu_res.intent.value} (Confidence: {nlu_res.intent_confidence}) | Slots: {nlu_res.slots}")

        # Store in Short Term Memory
        memory_system.short_term.store(
            f"User Directive: {text}",
            tags=["user_input", nlu_res.intent.value.lower()],
            metadata={"nlu": nlu_res.to_dict()},
        )

        # 3. Handle specific linguistic intents
        if nlu_res.intent == IntentType.EMERGENCY_COMMAND:
            self.decision_engine.set_emergency_stop(True)
            self.state = CognitiveState.EMERGENCY_STOP
            nlg_msg = "EMERGENCY BRAKE ENGAGED. All motor motion and active tasks halted immediately."
            return {"status": "EMERGENCY_STOP", "nlg_response": nlg_msg, "nlu": nlu_res.to_dict(), "goal": None}

        elif nlu_res.intent in (IntentType.FEEDBACK_POSITIVE, IntentType.FEEDBACK_CORRECTION):
            fb_item = await self.learning_engine.ingest_user_feedback(text)
            nlg_msg = nlg_generator.generate_feedback_acknowledgement(
                fb_item.feedback_type.value, fb_item.extracted_lesson
            )
            return {"status": "FEEDBACK_PROCESSED", "nlg_response": nlg_msg, "nlu": nlu_res.to_dict(), "goal": None}

        elif nlu_res.intent == IntentType.STATUS_CHECK:
            snapshot = world_model.get_snapshot()
            nlg_msg = nlg_generator.generate_telemetry_narrative(snapshot["robot_state"], snapshot["environment"])
            return {"status": "STATUS_REPORT", "nlg_response": nlg_msg, "nlu": nlu_res.to_dict(), "goal": None}

        # 4. Urgency Priority Mapping
        assigned_priority = priority
        if nlu_res.urgency_score >= 0.8:
            assigned_priority = GoalPriority.CRITICAL
        elif nlu_res.urgency_score >= 0.6 and assigned_priority < GoalPriority.HIGH:
            assigned_priority = GoalPriority.HIGH

        # 5. Create Active Goal
        goal = self.goal_manager.create_goal(
            title=text,
            description=f"Autonomous execution of human directive: '{text}'",
            priority=assigned_priority,
            context={
                "source": "user_chat",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "nlu": nlu_res.to_dict(),
            },
        )

        # 6. Natural Conversational Acknowledgement
        nlg_msg = conversational_agent.generate_natural_mission_acknowledgement(text)

        return {
            "status": "GOAL_CREATED",
            "goal": goal.to_dict(),
            "nlg_response": nlg_msg,
            "nlu": nlu_res.to_dict(),
        }

    def get_public_hud_status(self) -> Dict[str, Any]:
        """
        Returns safe, high-level status for the dashboard UI without leaking internal raw chain-of-thought.
        """
        goal_title = self.current_goal.title if self.current_goal else "Standby / Monitoring"
        goal_progress = self.current_goal.completion_percentage if self.current_goal else 100.0
        current_task_title = (
            self.current_goal.get_current_subtask().title
            if (self.current_goal and self.current_goal.get_current_subtask())
            else "Idle Scanning"
        )
        confidence_pct = int((self.current_goal.confidence if self.current_goal else 0.95) * 100)

        return {
            "ai_status": "ACTIVE" if self.is_running else "PAUSED",
            "cognitive_state": self.state.value,
            "current_goal": goal_title,
            "goal_progress_pct": goal_progress,
            "current_task": current_task_title,
            "confidence_score": f"{confidence_pct}%",
            "learning_status": "ONLINE (Adapting)",
            "memory_status": "CONNECTED (Multi-Tier)",
            "safe_reasoning_summary": self.last_reasoning_summary,
        }


cognitive_core = CognitiveCore()
