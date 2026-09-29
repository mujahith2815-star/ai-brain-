"""
FastAPI Telemetry & Web Control Center Server for P.H.A.S.S Sphere.
Provides real-time WebSockets, REST APIs for directives, feedback, tools, and 3D simulation state.
"""

from __future__ import annotations
import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

from core.cognitive_core import cognitive_core, CognitiveState
from core.event_bus import event_bus, Event, EventType
from core.goal_manager import GoalPriority
from world.world_model import world_model
from memory.retrieval import memory_system
from learning.learning_engine import LearningEngine
from learning.evaluation import evaluation_framework
from simulation.environment import simulated_env
from simulation.virtual_sensors import virtual_sensors
from tools.registry import tool_registry
from tools.permissions import permission_manager, PermissionLevel
from tools.executor import tool_executor

logger = logging.getLogger("phass.server")

app = FastAPI(title="P.H.A.S.S Sphere Control Center", version="1.0.0")

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "css").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "js").mkdir(parents=True, exist_ok=True)

# Mount static folder
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class DirectiveRequest(BaseModel):
    text: str
    priority: str = "NORMAL"


class FeedbackRequest(BaseModel):
    text: str
    target_goal_id: str | None = None


class TeleopRequest(BaseModel):
    vx: float
    vy: float
    omega: float


class ConfirmActionRequest(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]
    approved: bool


# Active WebSocket clients
connected_clients: Set[WebSocket] = set()


@app.on_event("startup")
async def on_startup():
    # 1. Boot Cognitive Core
    await cognitive_core.boot_sequence()
    # 2. Start background autonomous loop
    await cognitive_core.start_autonomous_loop()
    # 3. Start periodic telemetry broadcaster
    asyncio.create_task(telemetry_broadcast_worker())
    logger.info("P.H.A.S.S Sphere Server Startup Complete.")


@app.on_event("shutdown")
async def on_shutdown():
    await cognitive_core.stop_autonomous_loop()
    logger.info("P.H.A.S.S Sphere Server Shutdown.")


async def telemetry_broadcast_worker():
    """Broadcasts 20Hz telemetry and simulation state to connected dashboard clients."""
    while True:
        try:
            if connected_clients:
                # Gather state
                hud = cognitive_core.get_public_hud_status()
                world_snapshot = world_model.get_snapshot()
                robot_pos = world_snapshot["robot_state"]["position"]
                lidar_data = virtual_sensors.generate_lidar_point_cloud(robot_pos["x"], robot_pos["y"])
                mem_summary = memory_system.get_summary()
                learning_metrics = cognitive_core.learning_engine.get_learning_metrics()
                eval_metrics = evaluation_framework.get_latest_metrics()
                active_goals = cognitive_core.goal_manager.list_active_goals()
                all_goals = cognitive_core.goal_manager.list_all_goals(limit=10)
                recent_events = event_bus.get_recent_events(limit=25)
                arena_state = simulated_env.get_arena_state()

                packet = {
                    "type": "TELEMETRY_FRAME",
                    "hud": hud,
                    "robot_state": world_snapshot["robot_state"],
                    "environment": world_snapshot["environment"],
                    "lidar": lidar_data,
                    "arena": arena_state,
                    "entities": world_snapshot["entities"],
                    "active_goals": active_goals,
                    "all_goals": all_goals,
                    "memory_summary": mem_summary,
                    "learning_metrics": learning_metrics,
                    "evaluation_metrics": eval_metrics,
                    "recent_events": recent_events,
                }

                message_text = json.dumps(packet)
                # Dispatch to all clients
                dead_clients = set()
                for client in connected_clients:
                    try:
                        await client.send_text(message_text)
                    except Exception:
                        dead_clients.add(client)
                for dead in dead_clients:
                    connected_clients.discard(dead)

            await asyncio.sleep(0.05)  # 20 FPS
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in telemetry broadcast worker: {e}")
            await asyncio.sleep(1.0)


from nlp.nlu import nlu_pipeline
from nlp.nlg import nlg_generator, NLGPersona
from nlp.nlp_pipeline import nlp_pipeline
from nlp.llm_engine import llm_orchestrator


class NLPParseRequest(BaseModel):
    text: str


class NLGGenerateRequest(BaseModel):
    goal_title: str
    subtasks_count: int = 4
    persona: str = "ROBOT_VOICE"


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse("<h1>P.H.A.S.S Sphere Control Center Initializing...</h1>")
    return FileResponse(str(index_path))


@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    logger.info(f"Dashboard client connected. Total clients: {len(connected_clients)}")
    try:
        while True:
            data_text = await websocket.receive_text()
            try:
                msg = json.loads(data_text)
                msg_type = msg.get("type", "")

                if msg_type == "USER_DIRECTIVE":
                    txt = msg.get("text", "")
                    if txt:
                        res = await cognitive_core.submit_user_directive(txt)
                        # Reply directly with NLU and NLG response
                        await websocket.send_text(json.dumps({
                            "type": "NLU_RESPONSE",
                            "directive_result": res,
                        }))
                elif msg_type == "USER_FEEDBACK":
                    txt = msg.get("text", "")
                    if txt:
                        fb = await cognitive_core.learning_engine.ingest_user_feedback(txt)
                        nlg_msg = nlg_generator.generate_feedback_acknowledgement(
                            fb.feedback_type.value, fb.extracted_lesson
                        )
                        await websocket.send_text(json.dumps({
                            "type": "NLU_RESPONSE",
                            "directive_result": {
                                "status": "FEEDBACK_PROCESSED",
                                "nlg_response": nlg_msg,
                                "nlu": {"intent": fb.feedback_type.value},
                            },
                        }))
                elif msg_type == "TELEOP_COMMAND":
                    vx = float(msg.get("vx", 0.0))
                    vy = float(msg.get("vy", 0.0))
                    omega = float(msg.get("omega", 0.0))
                    world_model.robot_state.velocity.x = vx
                    world_model.robot_state.velocity.y = vy
                    world_model.robot_state.angular_velocity_degps = omega * 57.3
                    # Move position
                    world_model.robot_state.position.x += vx * 0.1
                    world_model.robot_state.position.y += vy * 0.1
                    world_model.robot_state.heading_deg = (world_model.robot_state.heading_deg + omega * 5.0) % 360.0
                elif msg_type == "EMERGENCY_STOP":
                    cognitive_core.decision_engine.set_emergency_stop(True)
                    cognitive_core.state = CognitiveState.EMERGENCY_STOP
                    await event_bus.publish(
                        Event(
                            type=EventType.EMERGENCY_STOP,
                            source="DashboardUI",
                            data={"message": "Emergency Stop engaged by operator."},
                        )
                    )
                elif msg_type == "RESUME_SYSTEM":
                    cognitive_core.decision_engine.set_emergency_stop(False)
                    cognitive_core.state = CognitiveState.STANDBY
                elif msg_type == "SPAWN_HAZARD":
                    simulated_env.add_random_obstacle()
            except Exception as e:
                logger.error(f"Error handling websocket message: {e}")
    except WebSocketDisconnect:
        connected_clients.discard(websocket)
        logger.info(f"Dashboard client disconnected. Total clients: {len(connected_clients)}")


@app.post("/api/directives")
async def post_directive(req: DirectiveRequest):
    priority_enum = GoalPriority.NORMAL
    if req.priority == "HIGH":
        priority_enum = GoalPriority.HIGH
    elif req.priority == "CRITICAL":
        priority_enum = GoalPriority.CRITICAL
    elif req.priority == "LOW":
        priority_enum = GoalPriority.LOW

    res = await cognitive_core.submit_user_directive(req.text, priority_enum)
    return res


@app.post("/api/feedback")
async def post_feedback(req: FeedbackRequest):
    item = await cognitive_core.learning_engine.ingest_user_feedback(req.text, req.target_goal_id)
    return {"status": "SUCCESS", "feedback": item.to_dict()}


@app.post("/api/nlp/parse")
async def parse_nlp_endpoint(req: NLPParseRequest):
    nlu_res = nlu_pipeline.understand(req.text)
    keywords = nlp_pipeline.extract_keywords(req.text)
    tokens = nlp_pipeline.tokenize(req.text)
    embedding = nlp_pipeline.compute_embedding(req.text, dim=16)
    return {
        "nlu": nlu_res.to_dict(),
        "tokens": tokens,
        "keywords": keywords,
        "embedding_sample": [round(v, 3) for v in embedding],
    }


@app.post("/api/nlp/generate")
async def generate_nlg_endpoint(req: NLGGenerateRequest):
    persona_enum = NLGPersona[req.persona] if req.persona in NLGPersona.__members__ else NLGPersona.ROBOT_VOICE
    narrative = nlg_generator.generate_acknowledgement(req.goal_title, req.subtasks_count, persona_enum)
    return {"status": "SUCCESS", "narrative": narrative}


@app.get("/api/memory")
async def get_memory_snapshot():
    return {
        "summary": memory_system.get_summary(),
        "long_term_knowledge": [r.to_dict() for r in memory_system.long_term.get_all()],
        "recent_episodes": [e.to_dict() for e in memory_system.episodic.get_recent_episodes(10)],
        "spatial_anchors": memory_system.spatial.get_all(),
        "short_term_dialogue": [r.to_dict() for r in memory_system.short_term.get_recent(10)],
    }


@app.get("/api/learning")
async def get_learning_snapshot():
    return {
        "metrics": cognitive_core.learning_engine.get_learning_metrics(),
        "evaluation": evaluation_framework.get_latest_metrics(),
        "experiences": [e.to_dict() for e in cognitive_core.learning_engine.exp_db.get_recent_experiences(15)],
    }


@app.get("/api/tools")
async def get_tools_list():
    return {
        "tools": tool_registry.list_tools(),
        "recent_audits": permission_manager.get_recent_audits(20),
    }


@app.post("/api/tools/execute")
async def execute_tool_endpoint(req: ConfirmActionRequest):
    res = await tool_executor.execute_tool(req.tool_name, req.parameters, user_confirmed=req.approved)
    return res.to_dict()
