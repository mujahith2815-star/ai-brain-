"""
FastAPI Web Dashboard Application for Orvix Sphere.
Provides REST endpoints and WebSockets for chat, system telemetry,
approval management, and health diagnostics.
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

app = FastAPI(title="Orvix Sphere Zenith Dashboard", version="1.0.0")

current_dir = Path(__file__).parent.resolve()
app.mount("/static", StaticFiles(directory=str(current_dir / "static")), name="static")
templates = Jinja2Templates(directory=str(current_dir / "templates"))


class ChatRequest(BaseModel):
    message: str
    stream: bool = False


@app.on_event("startup")
async def startup_event():
    """Initializes external MCP servers and registers tools on application startup."""
    try:
        from mcp.mcp_manager import MCPManager
        from mcp.mcp_tool_adapter import MCPToolAdapter
        from tools.registry import tool_registry

        mcp_manager = MCPManager()
        mcp_manager.start_all()
        adapter = MCPToolAdapter(mcp_manager)
        adapter.register_all(tool_registry)
        app.state.mcp_manager = mcp_manager
    except Exception as e:
        import logging
        logging.getLogger("orvix.web").warning(f"Error initializing MCP in web server startup: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Shuts down MCP servers gracefully on application stop."""
    mcp_mgr = getattr(app.state, "mcp_manager", None)
    if mcp_mgr:
        try:
            mcp_mgr.shutdown()
        except Exception:
            pass


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serves the main Jarvis-style web dashboard."""
    from config.api_config import api_config
    from tools.model_router import model_router
    router_mode = getattr(model_router, "current_mode", api_config.model_mode or "cloud_first")
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "title": "Orvix Sphere Dashboard",
            "primary_model": "Gemini 2.0 Flash (cloud)",
            "fallback_model": "Qwen2.5-7B (local, W:)",
            "router_mode": router_mode,
        }
    )


@app.get("/api/status")
async def get_system_status():
    """Returns runtime telemetry for models, MCP, and proactive agent."""
    from config.api_config import api_config
    from tools.model_router import model_router
    from core.secondary_brain import secondary_brain

    # Access or lazily initialize MCP manager
    mcp = getattr(app.state, "mcp_manager", None)
    if mcp is None:
        try:
            from mcp.mcp_manager import MCPManager
            from mcp.mcp_tool_adapter import MCPToolAdapter
            from tools.registry import tool_registry

            mcp = MCPManager()
            mcp.start_all()
            adapter = MCPToolAdapter(mcp)
            adapter.register_all(tool_registry)
            app.state.mcp_manager = mcp
        except Exception:
            mcp = None
    elif not any(c.is_connected for c in mcp.clients.values()):
        try:
            mcp.start_all()
        except Exception:
            pass

    mcp_servers_online = 0
    mcp_servers_total = 0
    mcp_servers_detail = {}
    node_available = False
    if mcp is not None:
        mcp_servers_online = sum(1 for c in mcp.clients.values() if c.is_connected)
        mcp_servers_total = sum(1 for c in mcp.clients.values() if c.config.enabled)
        try:
            st = mcp.get_status()
            node_available = st.get("node_available", False)
            mcp_servers_detail = st.get("servers", {})
        except Exception:
            pass

    mcp_data = {
        "connected": mcp_servers_online,
        "total": mcp_servers_total,
        "available": node_available,
        "servers": mcp_servers_detail,
    }

    # Proactive agent status
    proactive_data = {"state": "DISABLED", "paused": False, "max_per_hour": 20, "enabled": False}
    try:
        from proactive.autonomous_agent import AutonomousAgent
        from config.proactive_config import proactive_config
        pa = AutonomousAgent()
        p_state = "PAUSED" if pa.is_paused() else ("ENABLED" if proactive_config.proactive_enabled else "DISABLED")
        proactive_data = {
            "state": p_state,
            "paused": pa.is_paused(),
            "enabled": proactive_config.proactive_enabled,
            "max_per_hour": proactive_config.max_actions_per_hour,
        }
    except Exception:
        pass

    # Model router & hybrid dual-engine setup
    router_mode = getattr(model_router, "current_mode", api_config.model_mode or "cloud_first")
    primary_model = "Gemini 2.0 Flash (cloud)"
    fallback_model = "Qwen2.5-7B (local, W:)"

    sec_st = secondary_brain.get_status()

    return {
        "status": "ONLINE",
        "primary_model": primary_model,
        "fallback_model": fallback_model,
        "router_mode": router_mode,
        "mcp_servers_online": mcp_servers_online,
        "mcp_servers_total": mcp_servers_total,
        "proactive_enabled": proactive_data.get("enabled", False),
        "models": {
            "primary": primary_model,
            "provider": "google",
            "fallback": fallback_model,
            "secondary": sec_st.model_name,
            "secondary_active": sec_st.is_active,
            "cognitive_mode": sec_st.cognitive_mode,
            "mode": router_mode,
        },
        "mcp": mcp_data,
        "proactive": proactive_data,
    }


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """Processes user query and returns response."""
    msg = req.message.strip()
    if not msg:
        raise HTTPException(status_code=400, detail="Empty query")

    try:
        from nlp.answer_pipeline import process_query
        ans = process_query(msg)
        return {"status": "SUCCESS", "query": msg, "response": ans}
    except Exception as e:
        return {"status": "ERROR", "query": msg, "error": str(e), "response": "Error processing query."}


@app.get("/api/tasks")
async def list_tasks():
    """Returns scheduled proactive background tasks."""
    try:
        from proactive.scheduler import TaskScheduler
        sched = TaskScheduler()
        return {"status": "SUCCESS", "tasks": sched.list_tasks()}
    except Exception as e:
        return {"status": "ERROR", "error": str(e), "tasks": []}


@app.get("/api/queue")
async def get_approval_queue():
    """Returns actions awaiting human operator review."""
    try:
        from proactive.autonomous_agent import AutonomousAgent
        agent = AutonomousAgent()
        return {"status": "SUCCESS", "queue": agent.get_approval_queue()}
    except Exception as e:
        return {"status": "ERROR", "error": str(e), "queue": []}


@app.post("/api/approve/{action_id}")
async def approve_action(action_id: int):
    """Approves and executes a queued action."""
    try:
        from proactive.autonomous_agent import AutonomousAgent
        agent = AutonomousAgent()
        res = agent.approve_action(action_id)
        return res
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


@app.post("/api/reject/{action_id}")
async def reject_action(action_id: int):
    """Rejects a queued action."""
    try:
        from proactive.autonomous_agent import AutonomousAgent
        agent = AutonomousAgent()
        res = agent.reject_action(action_id)
        return res
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


@app.get("/api/audit")
async def get_audit_trail():
    """Returns recent autonomous execution logs."""
    try:
        from knowledge.sqlite_store import KnowledgeStore
        ks = KnowledgeStore()
        return {"status": "SUCCESS", "logs": ks.get_recent_task_logs(limit=25)}
    except Exception as e:
        return {"status": "ERROR", "error": str(e), "logs": []}


@app.get("/api/health")
async def health_check():
    """Executes full diagnostic check via SystemDoctor."""
    try:
        from diagnostics.doctor import SystemDoctor
        doc = SystemDoctor()
        return doc.run_full_check()
    except Exception as e:
        return {"healthy": False, "error": str(e)}


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """Bidirectional WebSocket for live streaming chat and status updates."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                user_msg = payload.get("message", "").strip()
            except Exception:
                user_msg = data.strip()

            if not user_msg:
                continue

            if user_msg == "__PING__":
                await websocket.send_json({"type": "PONG"})
                continue

            # Stream thinking indicator
            await websocket.send_json({"type": "STATUS", "message": "Analyzing query..."})

            try:
                from nlp.answer_pipeline import process_query
                ans = process_query(user_msg)
            except Exception as ex:
                ans = f"Encountered error: {ex}"

            await websocket.send_json({
                "type": "MESSAGE",
                "role": "assistant",
                "content": ans,
            })
    except WebSocketDisconnect:
        pass
