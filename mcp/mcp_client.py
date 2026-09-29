"""
Client transport implementation for Model Context Protocol (MCP).
Supports JSON-RPC 2.0 communication over STDIO and HTTP transports.
Handles timeouts, process lifecycle, and message traffic logging.
"""

import os
import sys
import json
import time
import shutil
import logging
import threading
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from mcp.mcp_config import MCPServerConfig, MCPServerType

logger = logging.getLogger("orvix.mcp.client")


class MCPClient:
    """
    Interacts with an MCP server via JSON-RPC 2.0 over STDIO or HTTP.
    """

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.name = config.name
        self.process: Optional[subprocess.Popen] = None
        self.is_connected: bool = False
        self.tools: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self._request_id: int = 0
        self._log_file: Path = Path(__file__).parent.parent / "logs" / "mcp_traffic.log"
        self._log_file.parent.mkdir(parents=True, exist_ok=True)

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _log_traffic(self, direction: str, payload: Dict[str, Any]):
        try:
            ts = datetime.now(timezone.utc).isoformat()
            entry = f"[{ts}] [{self.name}] [{direction}] {json.dumps(payload)}\n"
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception:
            pass

    def _resolve_executable(self, cmd: str) -> Optional[str]:
        """Resolves executable path, specifically checking .cmd on Windows and standard Node dirs."""
        if not cmd:
            return None

        node_dir = Path(r"C:\Program Files\nodejs")
        if node_dir.exists() and str(node_dir) not in os.environ.get("PATH", ""):
            os.environ["PATH"] = str(node_dir) + os.pathsep + os.environ.get("PATH", "")

        # Check direct which
        direct = shutil.which(cmd)
        if direct:
            return direct

        # Windows-first fallback (.cmd / .exe)
        if os.name == "nt":
            for ext in [".cmd", ".exe", ".bat"]:
                cand = shutil.which(cmd + ext)
                if cand:
                    return cand

            for name in [cmd, cmd + ".cmd", cmd + ".exe"]:
                p = node_dir / name
                if p.exists():
                    return str(p)

        return None

    def start(self) -> bool:
        """Starts the MCP client and performs JSON-RPC handshake."""
        with self._lock:
            if self.is_connected:
                return True

            if self.config.server_type == MCPServerType.STDIO:
                return self._start_stdio()
            elif self.config.server_type in (MCPServerType.HTTP, MCPServerType.SSE):
                return self._start_http()
            return False

    def _start_stdio(self) -> bool:
        cmd = self.config.command or "npx.cmd"
        resolved_cmd = self._resolve_executable(cmd)

        if not resolved_cmd:
            logger.warning(
                f"[MCPClient:{self.name}] Executable '{cmd}' not found on system. "
                f"Server marked UNAVAILABLE. (Node.js/npx may not be installed)"
            )
            self.is_connected = False
            return False

        try:
            servers_dir = Path(__file__).parent / "servers"
            node_exe = self._resolve_executable("node") or "node"
            args = list(self.config.args)

            # Smart server mappings for standard MCP tools
            if self.name == "sqlite" or any("server-sqlite" in str(a) for a in args):
                db_path = "knowledge/agent_memory.db"
                for a in args:
                    if a not in ("-y", "@modelcontextprotocol/server-sqlite") and not a.startswith("-"):
                        db_path = a
                sqlite_script = servers_dir / "sqlite_server.js"
                if sqlite_script.exists():
                    full_cmd = [node_exe, str(sqlite_script), db_path]
                else:
                    full_cmd = [resolved_cmd] + args
            elif self.name == "filesystem" or any("server-filesystem" in str(a) for a in args):
                fs_script = servers_dir / "filesystem_server.js"
                allowed_dir = os.path.expanduser("~/Documents")
                for a in args:
                    if a not in ("-y", "@modelcontextprotocol/server-filesystem") and not a.startswith("-"):
                        allowed_dir = os.path.expanduser(a)
                if fs_script.exists():
                    full_cmd = [node_exe, str(fs_script), allowed_dir]
                else:
                    full_cmd = [resolved_cmd] + args
            elif self.name == "fetch" or any("server-fetch" in str(a) for a in args):
                fetch_script = servers_dir / "fetch_server.js"
                if fetch_script.exists():
                    full_cmd = [node_exe, str(fetch_script)]
                else:
                    full_cmd = [resolved_cmd] + args
            else:
                full_cmd = [resolved_cmd] + args

            env = os.environ.copy()
            env.update(self.config.env)

            # Prevent python/node encoding issues on Windows
            env["PYTHONIOENCODING"] = "utf-8"

            creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            is_shell = (os.name == "nt" and (str(full_cmd[0]).lower().endswith(".cmd") or str(full_cmd[0]).lower().endswith(".bat")))

            self.process = subprocess.Popen(
                full_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=env,
                shell=is_shell,
                creationflags=creationflags
            )

            # JSON-RPC Handshake: initialize
            init_payload = {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "orvix_sphere",
                    "version": "1.0.0"
                }
            }
            init_res = self._send_request_locked("initialize", init_payload)
            if init_res is not None:
                # Send initialized notification
                self._send_notification_locked("notifications/initialized", {})

            self.is_connected = True
            # Discover tools automatically upon connect
            self.list_tools()
            logger.info(f"[MCPClient:{self.name}] Connected successfully over STDIO. Discovered {len(self.tools)} tool(s).")
            return True
        except Exception as e:
            logger.warning(f"[MCPClient:{self.name}] Failed to start STDIO process: {e}")
            self.is_connected = False
            self._cleanup_process()
            return False

    def _start_http(self) -> bool:
        if not self.config.url:
            logger.error(f"[MCPClient:{self.name}] HTTP server missing URL.")
            self.is_connected = False
            return False

        try:
            # Test connectivity
            self.is_connected = True
            self.list_tools()
            logger.info(f"[MCPClient:{self.name}] Connected to HTTP MCP endpoint {self.config.url}.")
            return True
        except Exception as e:
            logger.warning(f"[MCPClient:{self.name}] Failed to connect to HTTP server: {e}")
            self.is_connected = False
            return False

    def _send_request_locked(self, method: str, params: Dict[str, Any], timeout: float = 10.0) -> Optional[Dict[str, Any]]:
        if self.config.server_type == MCPServerType.STDIO:
            return self._stdio_request(method, params, timeout=timeout)
        else:
            return self._http_request(method, params, timeout=timeout)

    def _send_notification_locked(self, method: str, params: Dict[str, Any]):
        req = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        self._log_traffic("SEND_NOTIF", req)
        if self.process and self.process.stdin:
            try:
                self.process.stdin.write(json.dumps(req) + "\n")
                self.process.stdin.flush()
            except Exception:
                pass

    def _stdio_request(self, method: str, params: Dict[str, Any], timeout: float = 30.0) -> Optional[Dict[str, Any]]:
        if not self.process or not self.process.stdin or not self.process.stdout:
            return None

        req_id = self._next_id()
        req = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params
        }
        self._log_traffic("SEND_REQ", req)

        try:
            self.process.stdin.write(json.dumps(req) + "\n")
            self.process.stdin.flush()

            # Read response line with timeout, skipping non-JSON startup/info lines
            start_time = time.time()
            while True:
                if timeout and (time.time() - start_time) > timeout:
                    logger.error(f"[MCPClient:{self.name}] STDIO request timed out ({timeout}s)")
                    return None
                line = self.process.stdout.readline()
                if not line:
                    return None
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    data = json.loads(line_str)
                    if isinstance(data, dict) and ("result" in data or "error" in data or "method" in data or "id" in data):
                        self._log_traffic("RECV_RESP", data)
                        if "error" in data:
                            logger.error(f"[MCPClient:{self.name}] RPC Error: {data['error']}")
                            return None
                        return data.get("result")
                except Exception:
                    # Ignore non-JSON log line (e.g. startup banner, npm notices)
                    continue
        except Exception as e:
            logger.error(f"[MCPClient:{self.name}] STDIO communication exception: {e}")
            return None

    def _http_request(self, method: str, params: Dict[str, Any], timeout: float = 30.0) -> Optional[Dict[str, Any]]:
        import urllib.request
        import urllib.error

        req_id = self._next_id()
        req = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params
        }
        self._log_traffic("SEND_HTTP", req)

        try:
            body = json.dumps(req).encode("utf-8")
            headers = {"Content-Type": "application/json"}
            headers.update(self.config.headers)

            request = urllib.request.Request(self.config.url, data=body, headers=headers)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                res_bytes = response.read()
                data = json.loads(res_bytes.decode("utf-8"))
                self._log_traffic("RECV_HTTP", data)
                if "error" in data:
                    return None
                return data.get("result")
        except Exception as e:
            logger.error(f"[MCPClient:{self.name}] HTTP communication exception: {e}")
            return None

    def list_tools(self) -> List[Dict[str, Any]]:
        """Queries the server for available tool schemas via tools/list."""
        with self._lock:
            if not self.is_connected:
                return []

            res = self._send_request_locked("tools/list", {})
            if res and isinstance(res, dict):
                self.tools = res.get("tools", [])
            elif isinstance(res, list):
                self.tools = res
            return self.tools

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Calls a tool on this server via tools/call.
        Returns standardized status dictionary.
        """
        with self._lock:
            if not self.is_connected:
                return {
                    "status": "FAILED",
                    "server": self.name,
                    "tool": name,
                    "error": f"MCP Server '{self.name}' is not connected or offline."
                }

            params = {
                "name": name,
                "arguments": arguments or {}
            }
            res = self._send_request_locked("tools/call", params, timeout=self.config.timeout_sec)

            if res is None:
                return {
                    "status": "FAILED",
                    "server": self.name,
                    "tool": name,
                    "error": "No response or timeout received from MCP server."
                }

            is_error = res.get("isError", False)
            content = res.get("content", [])

            # Extract readable result text
            result_text = ""
            if isinstance(content, list):
                text_parts = [c.get("text", "") for c in content if isinstance(c, dict) and "text" in c]
                result_text = "\n".join(text_parts) if text_parts else str(content)
            else:
                result_text = str(content)

            return {
                "status": "SUCCESS" if not is_error else "FAILED",
                "server": self.name,
                "tool": name,
                "result": result_text,
                "content": content,
                "is_error": is_error
            }

    def stop(self):
        """Gracefully shuts down process or connection."""
        with self._lock:
            self.is_connected = False
            self._cleanup_process()

    def _cleanup_process(self):
        if self.process:
            try:
                if self.process.stdin:
                    try:
                        self.process.stdin.close()
                    except Exception:
                        pass
                self.process.terminate()
                try:
                    self.process.wait(timeout=1.5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
            except Exception:
                pass
            self.process = None
