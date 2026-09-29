"""
Remote Client (Digital Twin) for Laptops and Desktop Workstations.
Connects via WebSocket to P.H.A.S.S Central Network Broker:
- Transmits wake-word relay or transcribed voice commands over WebSocket
- Receives holographic HUD response push
- Speaks responses locally using local TTS (mimics Tony Stark's earpiece / laptop terminal)
"""

from __future__ import annotations
import asyncio
import json
import logging
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

try:
    import websockets
except ImportError:
    websockets = None

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

logger = logging.getLogger("phass.clients.remote_listener")


class RemoteListenerClient:
    """
    Remote companion client relaying voice directives to the host PC
    and playing back audio responses locally.
    """
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        auth_token: str = "phass_omni_secret_token_2026",
        client_id: str = "laptop_digital_twin_01",
        client_type: str = "laptop",
        enable_tts: bool = True,
    ):
        self.host = host
        self.port = port
        self.auth_token = auth_token
        self.client_id = client_id
        self.client_type = client_type
        self.enable_tts = enable_tts and TTS_AVAILABLE

        self.ws_url = f"ws://{self.host}:{self.port}"
        self.running = False
        self.connected = False
        self._ws: Any = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._client_thread: Optional[threading.Thread] = None

        self.last_reply: Optional[str] = None
        self.response_callbacks: list[Callable[[str], None]] = []

        # Initialize local TTS engine safely
        self._tts_engine = None
        if self.enable_tts:
            try:
                self._tts_engine = pyttsx3.init()
                self._tts_engine.setProperty("rate", 185)
            except Exception as e:
                logger.debug(f"Local TTS initialization warning: {e}")
                self.enable_tts = False

    def add_response_callback(self, cb: Callable[[str], None]):
        self.response_callbacks.append(cb)

    def speak(self, text: str):
        """Vocalizes response text through local speaker."""
        print(f"[Remote Voice Output] 🔊 {text}")
        if self.enable_tts and self._tts_engine:
            try:
                self._tts_engine.say(text)
                self._tts_engine.runAndWait()
            except Exception as e:
                logger.debug(f"TTS playback exception: {e}")

    async def _client_loop(self):
        """Asynchronous client loop handling handshake, outgoing commands, and incoming responses."""
        if websockets is None:
            logger.error("websockets library is required for RemoteListenerClient.")
            return

        while self.running:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    self._ws = ws
                    self.connected = True
                    logger.info(f"Connected to P.H.A.S.S Broker at {self.ws_url}")

                    # 1. Authenticate Handshake
                    auth_payload = {
                        "type": "auth",
                        "token": self.auth_token,
                        "client_id": self.client_id,
                        "client_type": self.client_type,
                        "signal_strength": -52,
                    }
                    await ws.send(json.dumps(auth_payload))

                    async for message in ws:
                        try:
                            data = json.loads(message)
                        except Exception:
                            continue

                        msg_type = data.get("type")
                        if msg_type == "auth_response":
                            if data.get("status") == "authenticated":
                                print(f"[Digital Twin] Authenticated with P.H.A.S.S Core as '{self.client_id}'")
                            else:
                                print(f"[Digital Twin] Authentication failed: {data.get('message')}")
                                break

                        elif msg_type == "response":
                            reply = data.get("reply", "")
                            self.last_reply = reply
                            print(f"\n[P.H.A.S.S Holographic HUD Remote Push]:\n{reply}\n")

                            for cb in self.response_callbacks:
                                try:
                                    cb(reply)
                                except Exception:
                                    pass

                            # Speak locally on phone/laptop speaker
                            self.speak(reply)

            except Exception as e:
                self.connected = False
                self._ws = None
                if self.running:
                    logger.debug(f"Connection lost to broker: {e}. Retrying in 2s...")
                    await asyncio.sleep(2.0)

    def start(self):
        """Starts client in a background daemon thread."""
        self.running = True
        self._client_thread = threading.Thread(target=self._run_thread, daemon=True, name="PHASS_RemoteListener")
        self._client_thread.start()

    def _run_thread(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._client_loop())
        except Exception:
            pass
        finally:
            self._loop.close()

    def stop(self):
        self.running = False
        self.connected = False
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._client_thread and self._client_thread.is_alive():
            self._client_thread.join(timeout=1.0)

    def send_voice_command(self, query: str):
        """Relays a voice or text command to the main PC."""
        if not self._ws or not self._loop or not self._loop.is_running():
            logger.warning("Cannot send command: client is not currently connected.")
            return

        payload = {
            "type": "command",
            "query": query,
            "client_id": self.client_id,
            "timestamp": time.time(),
        }
        asyncio.run_coroutine_threadsafe(self._ws.send(json.dumps(payload)), self._loop)


def run_interactive_cli(host: str = "127.0.0.1", port: int = 8765):
    """Launches an interactive prompt mimicking a phone/laptop terminal client."""
    client = RemoteListenerClient(host=host, port=port)
    client.start()
    print(f"--- P.H.A.S.S Digital Twin Client Initialized (Target: ws://{host}:{port}) ---")
    print("Type your query or simulated wake-word ('Hey P.H.A.S.S, ...'). Type 'exit' to quit.\n")

    try:
        while True:
            cmd = input("Phone/Laptop Mic > ").strip()
            if not cmd:
                continue
            if cmd.lower() in ("exit", "quit"):
                break
            client.send_voice_command(cmd)
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        client.stop()
        print("Disconnected.")


if __name__ == "__main__":
    run_interactive_cli()
