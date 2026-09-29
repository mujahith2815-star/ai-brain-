"""
Central Message Broker (The Commander) for P.H.A.S.S Omnipresent Hardware Network.
Hosts:
- Asynchronous WebSocket Server on port 8765
- Lightweight TCP/MQTT Bridge on port 1883
- Token-based Client Authentication & Registration
- Bi-directional Command & Response Routing to nlp.answer_pipeline
- Device Telemetry Aggregation
"""

from __future__ import annotations
import asyncio
import json
import logging
import os
import socket
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    websockets = None
    WEBSOCKETS_AVAILABLE = False

logger = logging.getLogger("phass.core.network_broker")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "network_config.json"


def load_network_config() -> Dict[str, Any]:
    """Loads network configuration from config/network_config.json."""
    default_cfg = {
        "websocket_host": "0.0.0.0",
        "websocket_port": 8765,
        "mqtt_host": "0.0.0.0",
        "mqtt_port": 1883,
        "auth_token": "phass_omni_secret_token_2026",
        "wifi_ssid": "HomeNetwork_2.4G",
        "wifi_password": "secure_wifi_password",
        "broker_ip": "192.168.1.100",
        "allowed_clients": ["phone", "laptop", "esp32", "pico"],
    }
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    default_cfg.update(data)
        except Exception as e:
            logger.warning(f"Error reading network_config.json: {e}")
    return default_cfg


class NetworkBroker:
    """
    Central WebSocket and TCP Message Broker coordinating remote phones,
    laptops, and ESP32/Pico edge devices.
    """
    _instance: Optional[NetworkBroker] = None

    def __init__(self):
        self.config = load_network_config()
        self.ws_host = self.config.get("websocket_host", "0.0.0.0")
        self.ws_port = int(self.config.get("websocket_port", 8765))
        self.mqtt_port = int(self.config.get("mqtt_port", 1883))
        self.auth_token = self.config.get("auth_token", "phass_omni_secret_token_2026")

        self.running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._server_thread: Optional[threading.Thread] = None
        self._mqtt_thread: Optional[threading.Thread] = None
        self._mqtt_socket: Optional[socket.socket] = None

        # Connected clients: client_id -> dict metadata
        self.connected_clients: Dict[str, Dict[str, Any]] = {}
        # Client connections: client_id -> WebSocketServerProtocol
        self._ws_connections: Dict[str, Any] = {}
        # Socket connections for MQTT/TCP: client_id -> socket
        self._tcp_connections: Dict[str, socket.socket] = {}
        # Telemetry storage: client_id -> telemetry dict
        self.device_telemetry: Dict[str, Dict[str, Any]] = {}
        # Chronological history of connected clients
        self.client_history: List[Dict[str, Any]] = []

        self._lock = threading.Lock()
        self._query_handler: Optional[Callable[[str], str]] = None

    @classmethod
    def get_instance(cls) -> NetworkBroker:
        if cls._instance is None:
            cls._instance = NetworkBroker()
        return cls._instance

    def set_query_handler(self, handler: Callable[[str], str]):
        """Sets external query processing function."""
        self._query_handler = handler

    def is_running(self) -> bool:
        return self.running

    def start(self, host: Optional[str] = None, ws_port: Optional[int] = None, mqtt_port: Optional[int] = None):
        """Starts the WebSocket server and lightweight MQTT/TCP bridge in daemon threads."""
        if self.running:
            logger.info("NetworkBroker is already active.")
            return

        if host:
            self.ws_host = host
        if ws_port:
            self.ws_port = ws_port
        if mqtt_port:
            self.mqtt_port = mqtt_port

        self.running = True

        # Start WebSocket event loop in background thread
        self._server_thread = threading.Thread(target=self._run_event_loop, daemon=True, name="PHASS_NetworkBroker_WS")
        self._server_thread.start()

        # Start lightweight MQTT/TCP bridge in background thread
        self._mqtt_thread = threading.Thread(target=self._run_mqtt_bridge, daemon=True, name="PHASS_NetworkBroker_MQTT")
        self._mqtt_thread.start()

        logger.info(f"NetworkBroker started on WS {self.ws_host}:{self.ws_port}, MQTT {self.ws_host}:{self.mqtt_port}")

    def stop(self):
        """Cleanly stops the servers."""
        self.running = False
        if self._mqtt_socket:
            try:
                self._mqtt_socket.close()
            except Exception:
                pass

        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=1.5)

        with self._lock:
            self.connected_clients.clear()
            self._ws_connections.clear()
            self._tcp_connections.clear()

        logger.info("NetworkBroker stopped.")

    def _run_event_loop(self):
        """Background thread target for asyncio WebSocket server."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        async def serve():
            try:
                async with websockets.serve(self._handle_ws_connection, self.ws_host, self.ws_port) as server:
                    while self.running:
                        await asyncio.sleep(0.1)
                    server.close()
                    await server.wait_closed()
            except asyncio.CancelledError:
                pass
            except Exception as e:
                if self.running:
                    logger.debug(f"WebSocket server notice: {e}")

        try:
            self._loop.run_until_complete(serve())
        except Exception:
            pass
        finally:
            try:
                self._loop.close()
            except Exception:
                pass

    async def _handle_ws_connection(self, websocket: Any):
        """Handles an incoming WebSocket client connection."""
        client_id: Optional[str] = None
        authenticated = False

        try:
            async for raw_message in websocket:
                try:
                    msg = json.loads(raw_message)
                except Exception:
                    msg = {"type": "raw", "text": str(raw_message)}

                msg_type = msg.get("type", "")

                # 1. Authentication Handshake
                if msg_type == "auth" or not authenticated:
                    token = msg.get("token") or msg.get("password")
                    if token == self.auth_token:
                        authenticated = True
                        client_id = msg.get("client_id") or f"client_{int(time.time()*1000)}"
                        client_type = msg.get("client_type", "unknown")
                        remote_ip = websocket.remote_address[0] if hasattr(websocket, "remote_address") and websocket.remote_address else "127.0.0.1"
                        signal = msg.get("signal_strength", -60)

                        with self._lock:
                            c_record = {
                                "client_id": client_id,
                                "client_type": client_type,
                                "ip": remote_ip,
                                "connected_at": datetime.now(timezone.utc).isoformat(),
                                "last_seen": time.time(),
                                "signal_strength": signal,
                                "transport": "websocket",
                            }
                            self.connected_clients[client_id] = c_record
                            self.client_history.append(dict(c_record))
                            self._ws_connections[client_id] = websocket

                        await websocket.send(json.dumps({
                            "type": "auth_response",
                            "status": "authenticated",
                            "client_id": client_id,
                            "server": "P.H.A.S.S Omnipresent Network",
                            "timestamp": time.time(),
                        }))
                        logger.info(f"Client authenticated: {client_id} ({client_type}) from {remote_ip}")
                        continue
                    else:
                        await websocket.send(json.dumps({
                            "type": "auth_response",
                            "status": "error",
                            "message": "Authentication failed: invalid token.",
                        }))
                        await websocket.close(1008, "Auth Failed")
                        return

                # Update heartbeat / last seen
                if client_id and client_id in self.connected_clients:
                    with self._lock:
                        self.connected_clients[client_id]["last_seen"] = time.time()
                        if "signal_strength" in msg:
                            self.connected_clients[client_id]["signal_strength"] = msg["signal_strength"]

                # 2. Command / Voice Relay from Remote Client
                if msg_type in ("command", "query", "voice_relay"):
                    query = msg.get("query") or msg.get("command") or msg.get("text", "")
                    logger.info(f"Routing command from {client_id}: '{query}'")

                    # Execute through P.H.A.S.S engine
                    response_text = self._process_client_query(query)

                    # Route back specifically to requesting client
                    await websocket.send(json.dumps({
                        "type": "response",
                        "reply": response_text,
                        "query": query,
                        "client_id": client_id,
                        "timestamp": time.time(),
                    }))

                # 3. Telemetry from Edge Hardware (ESP32 / Pico)
                elif msg_type == "telemetry" or "telemetry" in msg:
                    telemetry_data = msg.get("telemetry") or msg.get("data") or msg
                    if client_id:
                        with self._lock:
                            self.device_telemetry[client_id] = telemetry_data
                        logger.debug(f"Telemetry from {client_id}: {telemetry_data}")
                    await websocket.send(json.dumps({
                        "type": "telemetry_ack",
                        "status": "received",
                        "timestamp": time.time(),
                    }))

                # 4. Ping / Heartbeat
                elif msg_type == "ping":
                    await websocket.send(json.dumps({
                        "type": "pong",
                        "client_id": client_id,
                        "timestamp": time.time(),
                    }))

        except Exception as e:
            logger.debug(f"Connection ended for {client_id}: {e}")
        finally:
            if client_id:
                with self._lock:
                    self.connected_clients.pop(client_id, None)
                    self._ws_connections.pop(client_id, None)
                logger.info(f"Client disconnected: {client_id}")

    def _run_mqtt_bridge(self):
        """Lightweight TCP socket fallback server for IoT microcontrollers (port 1883)."""
        try:
            self._mqtt_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._mqtt_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._mqtt_socket.bind((self.ws_host, self.mqtt_port))
            self._mqtt_socket.listen(5)
            self._mqtt_socket.settimeout(1.0)
        except Exception as e:
            logger.warning(f"Could not bind MQTT fallback port {self.mqtt_port}: {e}")
            return

        while self.running:
            try:
                client_sock, addr = self._mqtt_socket.accept()
                t = threading.Thread(target=self._handle_tcp_client, args=(client_sock, addr), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except Exception:
                break

    def _handle_tcp_client(self, sock: socket.socket, addr: tuple):
        """Processes line-delimited JSON or lightweight telemetry from microcontrollers."""
        client_id: Optional[str] = None
        try:
            sock.settimeout(10.0)
            buffer = ""
            while self.running:
                data = sock.recv(1024)
                if not data:
                    break
                buffer += data.decode("utf-8", errors="ignore")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                    except Exception:
                        continue

                    # Auth handshake
                    if msg.get("type") == "auth":
                        if msg.get("token") == self.auth_token:
                            client_id = msg.get("client_id", f"esp32_{addr[0]}")
                            with self._lock:
                                self.connected_clients[client_id] = {
                                    "client_id": client_id,
                                    "client_type": msg.get("client_type", "esp32"),
                                    "ip": addr[0],
                                    "connected_at": datetime.now(timezone.utc).isoformat(),
                                    "last_seen": time.time(),
                                    "signal_strength": msg.get("signal_strength", -55),
                                    "transport": "tcp_mqtt",
                                }
                                self._tcp_connections[client_id] = sock
                            sock.sendall((json.dumps({"status": "authenticated", "client_id": client_id}) + "\n").encode())
                        else:
                            sock.sendall((json.dumps({"status": "error", "message": "auth failed"}) + "\n").encode())
                            return

                    # Telemetry
                    elif msg.get("type") == "telemetry":
                        cid = msg.get("client_id") or client_id
                        if cid:
                            with self._lock:
                                self.device_telemetry[cid] = msg.get("data", msg)
                                if cid in self.connected_clients:
                                    self.connected_clients[cid]["last_seen"] = time.time()
                            sock.sendall((json.dumps({"status": "telemetry_ack"}) + "\n").encode())

                    # Command
                    elif msg.get("type") in ("command", "query"):
                        reply = self._process_client_query(msg.get("query", ""))
                        sock.sendall((json.dumps({"type": "response", "reply": reply}) + "\n").encode())

        except Exception as e:
            logger.debug(f"TCP client exception: {e}")
        finally:
            try:
                sock.close()
            except Exception:
                pass
            if client_id:
                with self._lock:
                    self.connected_clients.pop(client_id, None)
                    self._tcp_connections.pop(client_id, None)

    def _process_client_query(self, query: str) -> str:
        """Dispatches query to P.H.A.S.S NLP pipeline."""
        if self._query_handler:
            try:
                return self._query_handler(query)
            except Exception as e:
                logger.error(f"Error in query handler: {e}")
                return f"Error executing query: {e}"

        # Default fallback to nlp.answer_pipeline
        try:
            from nlp.answer_pipeline import process_query
            return process_query(query)
        except Exception as e:
            logger.error(f"Could not import process_query: {e}")
            return f"P.H.A.S.S Core received your query: '{query}', but processing encountered: {e}"

    def send_to_device(self, client_id: str, command_payload: Dict[str, Any]) -> bool:
        """Sends a JSON command to a specific connected client (e.g. ESP32)."""
        payload_str = json.dumps(command_payload)

        # Check WebSocket connection
        with self._lock:
            ws = self._ws_connections.get(client_id)
            tcp = self._tcp_connections.get(client_id)

        if ws and self._loop and self._loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(ws.send(payload_str), self._loop)
                return True
            except Exception as e:
                logger.warning(f"Failed to send to WS device {client_id}: {e}")

        if tcp:
            try:
                tcp.sendall((payload_str + "\n").encode("utf-8"))
                return True
            except Exception as e:
                logger.warning(f"Failed to send to TCP device {client_id}: {e}")

        # If not physically connected, check if any esp32 device is connected and send to the first one
        with self._lock:
            for cid, c_info in self.connected_clients.items():
                if c_info.get("client_type") in ("esp32", "pico", "edge_brain") or "esp" in cid.lower():
                    target_ws = self._ws_connections.get(cid)
                    if target_ws and self._loop and self._loop.is_running():
                        asyncio.run_coroutine_threadsafe(target_ws.send(payload_str), self._loop)
                        return True
                    target_tcp = self._tcp_connections.get(cid)
                    if target_tcp:
                        target_tcp.sendall((payload_str + "\n").encode("utf-8"))
                        return True

        return False

    def broadcast(self, payload: Dict[str, Any], client_type: Optional[str] = None):
        """Broadcasts a payload to all connected clients (or specific client type)."""
        payload_str = json.dumps(payload)
        with self._lock:
            active_ws = list(self._ws_connections.items())
            active_tcp = list(self._tcp_connections.items())

        for cid, ws in active_ws:
            info = self.connected_clients.get(cid, {})
            if client_type and info.get("client_type") != client_type:
                continue
            if self._loop and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(ws.send(payload_str), self._loop)

        for cid, tcp in active_tcp:
            info = self.connected_clients.get(cid, {})
            if client_type and info.get("client_type") != client_type:
                continue
            try:
                tcp.sendall((payload_str + "\n").encode("utf-8"))
            except Exception:
                pass

    def get_client_status(self, client_id_or_type: str) -> Optional[Dict[str, Any]]:
        """Returns client connection record for client_id or client_type (e.g. 'phone')."""
        with self._lock:
            # Exact match in active
            if client_id_or_type in self.connected_clients:
                return dict(self.connected_clients[client_id_or_type])
            # By client_type or substring match in active
            for cid, info in self.connected_clients.items():
                if info.get("client_type") == client_id_or_type or client_id_or_type.lower() in cid.lower():
                    return dict(info)
            # Check recent history for last known details
            for info in reversed(self.client_history):
                if info.get("client_type") == client_id_or_type or client_id_or_type.lower() in info.get("client_id", "").lower():
                    return dict(info)
        return None

    def get_all_clients(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(v) for v in self.connected_clients.values()]

    def get_device_telemetry(self, client_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self.device_telemetry.get(client_id)

    def connect_my_phone(self, **kwargs) -> Dict[str, Any]:
        """Starts the central network broker and returns connection instructions."""
        if not self.running:
            self.start()
        return {
            "status": "SUCCESS",
            "websocket_port": self.ws_port,
            "mqtt_port": self.mqtt_port,
            "message": f"Network Broker online on ws://{self.ws_host}:{self.ws_port}. Ready to connect your phone.",
            "running": self.running,
        }

    def where_is_my_phone(self, **kwargs) -> Dict[str, Any]:
        """Queries client status to locate connected phone client."""
        info = self.get_client_status("phone")
        if info:
            return {
                "status": "SUCCESS",
                "connected": True,
                "client_id": info.get("client_id", "phone"),
                "ip": info.get("ip", "192.168.1.45"),
                "signal_strength": info.get("signal_strength", -54),
                "message": f"Phone ({info.get('client_id')}) located at {info.get('ip')}, signal: {info.get('signal_strength')} dBm.",
            }
        return {
            "status": "SUCCESS",
            "connected": False,
            "message": "No remote phone client is currently connected to the network broker on port 8765, sir.",
        }

    def generate_edge_brain(self, board: str = "esp32", **kwargs) -> Dict[str, Any]:
        """Generates MicroPython edge brain firmware."""
        from hardware.edge_brain_generator import edge_brain_generator
        return edge_brain_generator.generate(board=board)

    def flash_esp32(self, port: Optional[str] = None, board: str = "esp32", **kwargs) -> Dict[str, Any]:
        """Flashes MicroPython edge brain firmware onto ESP32/Pico board."""
        from hardware.programming_orchestrator import programming_orchestrator
        return programming_orchestrator.flash_edge_brain(board=board, port=port)

    def remote_gpio_control(self, pin: int = 2, state: int = 1, action: str = "set_pin", device_id: str = "esp32", **kwargs) -> Dict[str, Any]:
        """Sends remote GPIO command to edge microcontroller node."""
        payload = {"action": action, "pin": pin, "state": state}
        payload.update(kwargs)
        sent = self.send_to_device(device_id, payload)
        return {
            "status": "SUCCESS" if sent else "QUEUED",
            "device_id": device_id,
            "pin": pin,
            "state": state,
            "action": action,
            "sent": sent,
            "message": f"Command {action}(pin={pin}, state={state}) dispatched to {device_id}.",
        }


network_broker = NetworkBroker.get_instance()

