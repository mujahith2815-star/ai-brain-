"""
Omni-Interface Gateway for Llama Assistant & P.H.A.S.S Sphere.
Universal multi-channel access layer supporting:
1. Telegram Bot integration (real-time chat and push alerts)
2. Slack App integration (channels, mentions, and notifications)
3. FastAPI REST API (/chat, /status, /tools, /execute, /health) with pure-Python http.server fallback
4. Floating Desktop Widget (minimalist Tkinter overlay with push-to-talk & command entry)
5. Central OmniGateway manager to unify all endpoints.
"""

from __future__ import annotations
import os
import sys
import time
import json
import uuid
import socket
import logging
import threading
from typing import Dict, Any, List, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler

logger = logging.getLogger("phass.core.omni")

# Optional framework imports with graceful fallbacks
FASTAPI_AVAILABLE = False
try:
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False


# =============================================================================
# 1. TELEGRAM GATEWAY
# =============================================================================
class TelegramGateway:
    """
    Connects assistant to Telegram channels and private messages.
    Supports real-world bot tokens or local test simulation when offline.
    """

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.is_configured = bool(self.token)
        self.message_history: List[Dict[str, Any]] = []

    def send_message(self, chat_id: str, text: str) -> Dict[str, Any]:
        """Sends message to specified Telegram chat or records to simulation queue."""
        record = {
            "channel": "telegram",
            "chat_id": chat_id,
            "text": text,
            "timestamp": time.time(),
            "status": "SENT" if self.is_configured else "SIMULATED",
        }
        self.message_history.append(record)

        if self.is_configured:
            try:
                import urllib.request
                url = f"https://api.telegram.org/bot{self.token}/sendMessage"
                payload = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=5) as response:
                    return {"status": "SUCCESS", "chat_id": chat_id, "mode": "LIVE"}
            except Exception as e:
                logger.warning(f"Telegram live send failed ({e}), queued locally.")
                return {"status": "FAILED", "error": str(e), "chat_id": chat_id}

        return {"status": "SUCCESS", "chat_id": chat_id, "mode": "SIMULATION", "text": text}

    def poll_updates(self, offset: int = 0) -> List[Dict[str, Any]]:
        """Polls for incoming Telegram messages."""
        if not self.is_configured:
            return []
        try:
            import urllib.request
            url = f"https://api.telegram.org/bot{self.token}/getUpdates?offset={offset}"
            req = urllib.request.Request(url, headers={"User-Agent": "PHASSSphereBot"})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                return data.get("result", [])
        except Exception as e:
            logger.debug(f"Telegram poll error: {e}")
            return []


# =============================================================================
# 2. SLACK GATEWAY
# =============================================================================
class SlackGateway:
    """
    Connects assistant to Slack workspaces.
    Supports incoming webhooks, chat.postMessage, and event routing.
    """

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("SLACK_BOT_TOKEN")
        self.is_configured = bool(self.token)
        self.message_history: List[Dict[str, Any]] = []

    def post_message(self, channel: str, text: str) -> Dict[str, Any]:
        """Posts a message to a Slack channel."""
        record = {
            "channel": channel,
            "text": text,
            "timestamp": time.time(),
            "status": "SENT" if self.is_configured else "SIMULATED",
        }
        self.message_history.append(record)

        if self.is_configured:
            try:
                import urllib.request
                url = "https://slack.com/api/chat.postMessage"
                payload = json.dumps({"channel": channel, "text": text}).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json",
                    },
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode())
                    return {"status": "SUCCESS" if data.get("ok") else "FAILED", "response": data}
            except Exception as e:
                logger.warning(f"Slack post failed ({e})")
                return {"status": "FAILED", "error": str(e)}

        return {"status": "SUCCESS", "channel": channel, "mode": "SIMULATION", "text": text}


# =============================================================================
# 3. REST API DISPATCHER (FASTAPI OR PURE-PYTHON HTTP)
# =============================================================================
def handle_api_request(method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Tuple[int, Dict[str, Any]]:
    """
    Unified request router used by both FastAPI and the fallback HTTP server.
    """
    clean_path = path.split("?")[0].rstrip("/")
    if not clean_path:
        clean_path = "/"

    # 1. Health check
    if clean_path == "/health":
        return 200, {"status": "HEALTHY", "timestamp": time.time()}

    # 2. System status
    if clean_path == "/status":
        from tools.registry import tool_registry
        return 200, {
            "status": "ONLINE",
            "name": "P.H.A.S.S Sphere Zenith",
            "version": "8.0",
            "registered_tools_count": len(tool_registry.list_tools()),
            "timestamp": time.time(),
        }

    # 3. List tools
    if clean_path == "/tools":
        from tools.registry import tool_registry
        tools = tool_registry.list_tools()
        catalog = []
        for t in tools:
            if isinstance(t, dict):
                name = t.get("name")
                desc = t.get("description", f"Tool: {name}")
            else:
                name = str(t)
                desc = tool_registry.get_description(name) or f"Tool: {name}"
            catalog.append({"name": name, "description": desc})
        return 200, {"total_tools": len(catalog), "tools": catalog}

    # 4. Chat endpoint
    if clean_path == "/chat":
        if method != "POST":
            return 405, {"error": "Method Not Allowed, use POST"}
        body = body or {}
        msg = body.get("message", "")
        session_id = body.get("session_id", str(uuid.uuid4())[:8])

        if not msg:
            return 400, {"error": "Missing 'message' in request body"}

        # Route to agent
        try:
            from core.llama_tool_agent import llama_tool_agent
            reply = llama_tool_agent.process_query(msg)
        except Exception:
            reply = f"P.H.A.S.S Zenith processed: {msg}"

        # Record in Mind Palace
        try:
            from core.mind_palace import mind_palace
            mind_palace.store_conversation(session_id, msg, reply)
        except Exception:
            pass

        return 200, {
            "session_id": session_id,
            "user_query": msg,
            "reply": reply,
            "timestamp": time.time(),
        }

    # 5. Tool execution endpoint
    if clean_path == "/execute":
        if method != "POST":
            return 405, {"error": "Method Not Allowed, use POST"}
        body = body or {}
        tool_name = body.get("tool_name")
        params = body.get("parameters", {})

        if not tool_name:
            return 400, {"error": "Missing 'tool_name'"}

        from tools.registry import tool_registry
        result = tool_registry.execute(tool_name, **params)
        return 200, {
            "tool": tool_name,
            "status": result.get("status", "SUCCESS"),
            "result": result,
            "timestamp": time.time(),
        }

    # Default root
    if clean_path == "/":
        return 200, {
            "title": "P.H.A.S.S Sphere Omni-Interface REST API",
            "version": "8.0",
            "endpoints": ["/health", "/status", "/tools", "/chat (POST)", "/execute (POST)"],
        }

    return 404, {"error": f"Endpoint not found: {path}"}


class PurePythonApiHandler(BaseHTTPRequestHandler):
    """Standard-library HTTP handler for environments where FastAPI is not installed."""

    def log_message(self, format, *args):
        pass  # Suppress console clutter

    def do_GET(self):
        code, data = handle_api_request("GET", self.path)
        self._send_json(code, data)

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = {}
        if content_length > 0:
            try:
                raw = self.rfile.read(content_length).decode("utf-8")
                body = json.loads(raw)
            except Exception:
                body = {}
        code, data = handle_api_request("POST", self.path, body)
        self._send_json(code, data)

    def _send_json(self, code: int, data: Dict[str, Any]):
        response = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response)


# Build FastAPI app if available
if FASTAPI_AVAILABLE:
    fastapi_app = FastAPI(title="P.H.A.S.S Sphere Omni-Interface", version="8.0")

    @fastapi_app.get("/health")
    def api_health():
        return {"status": "HEALTHY", "timestamp": time.time()}

    @fastapi_app.get("/status")
    def api_status():
        code, data = handle_api_request("GET", "/status")
        return data

    @fastapi_app.get("/tools")
    def api_tools():
        code, data = handle_api_request("GET", "/tools")
        return data

    @fastapi_app.post("/chat")
    async def api_chat(req: Request):
        body = await req.json()
        code, data = handle_api_request("POST", "/chat", body)
        return JSONResponse(status_code=code, content=data)

    @fastapi_app.post("/execute")
    async def api_execute(req: Request):
        body = await req.json()
        code, data = handle_api_request("POST", "/execute", body)
        return JSONResponse(status_code=code, content=data)

    @fastapi_app.get("/")
    def api_root():
        code, data = handle_api_request("GET", "/")
        return data


# =============================================================================
# 4. FLOATING DESKTOP WIDGET
# =============================================================================
class DesktopWidget:
    """
    Minimalist floating desktop overlay widget.
    Can be launched into its own non-blocking background thread or tested headlessly.
    """

    def __init__(self):
        self.is_running = False
        self._root = None
        self._thread = None

    def launch(self, in_thread: bool = True):
        """Launches the overlay widget."""
        if in_thread:
            self._thread = threading.Thread(target=self._run_tk, daemon=True)
            self._thread.start()
        else:
            self._run_tk()

    def _run_tk(self):
        try:
            import tkinter as tk
            from tkinter import ttk

            self._root = tk.Tk()
            self._root.title("P.H.A.S.S Sphere")
            self._root.geometry("380x160+50+50")
            self._root.attributes("-topmost", True)
            self._root.configure(bg="#1e1e2e")

            # Entry
            entry = tk.Entry(self._root, bg="#313244", fg="#cdd6f4", font=("Segoe UI", 11), insertbackground="white")
            entry.pack(fill="x", padx=12, pady=(12, 6))

            status_lbl = tk.Label(self._root, text="P.H.A.S.S Omni-Sentinel Ready", bg="#1e1e2e", fg="#a6adc8", font=("Segoe UI", 9))
            status_lbl.pack(pady=2)

            def on_submit(event=None):
                q = entry.get().strip()
                if not q:
                    return
                entry.delete(0, tk.END)
                status_lbl.config(text=f"Thinking: {q[:25]}...")
                from core.llama_tool_agent import llama_tool_agent
                ans = llama_tool_agent.process_query(q)
                status_lbl.config(text=ans[:50])

            entry.bind("<Return>", on_submit)

            btn_frame = tk.Frame(self._root, bg="#1e1e2e")
            btn_frame.pack(pady=6)
            send_btn = tk.Button(btn_frame, text="Send", command=on_submit, bg="#89b4fa", fg="#11111b", padx=10)
            send_btn.pack(side="left", padx=4)

            self.is_running = True
            self._root.mainloop()
        except Exception as e:
            logger.debug(f"Tkinter desktop widget offline or headless: {e}")
            self.is_running = False

    def simulate_query(self, query: str) -> Dict[str, Any]:
        """Headless test helper for widget testing."""
        code, resp = handle_api_request("POST", "/chat", {"message": query, "session_id": "widget_sim"})
        return {"status": "SUCCESS" if code == 200 else "ERROR", "reply": resp.get("reply", "")}

    def close(self):
        if self._root:
            try:
                self._root.destroy()
            except Exception:
                pass
        self.is_running = False


# =============================================================================
# 5. CENTRAL OMNI GATEWAY
# =============================================================================
class OmniGateway:
    """
    Central gateway coordinating REST API server, Telegram, Slack, and Desktop Widget.
    """

    def __init__(self):
        self.telegram = TelegramGateway()
        self.slack = SlackGateway()
        self.widget = DesktopWidget()
        self.server = None
        self.server_thread = None
        self.host = "127.0.0.1"
        self.port = 8000

    def start_api(self, host: str = "127.0.0.1", port: int = 8000, in_thread: bool = True):
        """Starts the REST API server."""
        self.host = host
        self.port = port

        def run_server():
            if FASTAPI_AVAILABLE:
                logger.info(f"Starting FastAPI server on http://{host}:{port}")
                uvicorn.run(fastapi_app, host=host, port=port, log_level="warning")
            else:
                logger.info(f"Starting Pure-Python HTTP server on http://{host}:{port}")
                self.server = HTTPServer((host, port), PurePythonApiHandler)
                self.server.serve_forever()

        if in_thread:
            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()
            time.sleep(0.5)  # brief startup settle
        else:
            run_server()

    def stop_api(self):
        """Stops the API server if running."""
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
            except Exception:
                pass

    def send_broadcast(self, message: str) -> Dict[str, Any]:
        """Broadcasts an alert or notification across all configured channels."""
        tg_res = self.telegram.send_message("broadcast", message)
        sl_res = self.slack.post_message("general", message)
        return {
            "telegram": tg_res,
            "slack": sl_res,
            "broadcast_text": message,
            "timestamp": time.time(),
        }


# Global singleton
omni_gateway = OmniGateway()
