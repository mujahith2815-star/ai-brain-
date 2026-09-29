"""
Comprehensive Test Suite for P.H.A.S.S Omnipresent Hardware Network Layer.
Validates:
1. WebSocket Broker Connection & Authentication Handshake
2. Edge Brain Firmware Generation (set_pin, read_adc, pwm)
3. Auto-Flash & Commissioning Simulation (esptool command synthesis, Wi-Fi reconnection, proactive interrupt)
4. Remote Voice Relay from Phone/Laptop Client to Host Brain
5. Natural Language Network Intent Routing & Execution
"""

import ast
import asyncio
import json
import socket
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from core.network_broker import NetworkBroker
from hardware.edge_brain_generator import EdgeBrainGenerator
from hardware.programming_orchestrator import ProgrammingOrchestrator
from nlp.answer_pipeline import process_query, route_intent


@pytest.fixture
def ephemeral_broker():
    """Provides an active NetworkBroker running on ephemeral test ports."""
    broker = NetworkBroker()
    # Find free ports
    s1 = socket.socket()
    s1.bind(("", 0))
    ws_port = s1.getsockname()[1]
    s1.close()

    s2 = socket.socket()
    s2.bind(("", 0))
    mqtt_port = s2.getsockname()[1]
    s2.close()

    broker.start(host="127.0.0.1", ws_port=ws_port, mqtt_port=mqtt_port)
    time.sleep(0.5)

    yield broker

    broker.stop()
    time.sleep(0.3)


def test_websocket_connection(ephemeral_broker):
    """Simulates a client connecting and sending a 'ping' command, verifying broker routing."""
    import websockets

    received_pong = False

    async def client_ping():
        nonlocal received_pong
        uri = f"ws://127.0.0.1:{ephemeral_broker.ws_port}"
        async with websockets.connect(uri) as ws:
            # 1. Auth Handshake
            await ws.send(json.dumps({
                "type": "auth",
                "token": ephemeral_broker.auth_token,
                "client_id": "test_tester_01",
                "client_type": "phone",
                "signal_strength": -50,
            }))
            auth_res = json.loads(await ws.recv())
            assert auth_res.get("status") == "authenticated"

            # 2. Ping command
            await ws.send(json.dumps({
                "type": "ping",
                "client_id": "test_tester_01",
            }))
            ping_res = json.loads(await ws.recv())
            if ping_res.get("type") == "pong":
                received_pong = True

            # Connected during active session
            assert "test_tester_01" in ephemeral_broker.connected_clients

    asyncio.run(client_ping())
    assert received_pong is True
    assert any(c.get("client_id") == "test_tester_01" for c in ephemeral_broker.client_history)


def test_edge_brain_generation(tmp_path):
    """Verifies generated MicroPython code contains mandatory set_pin and read_adc functions."""
    generator = EdgeBrainGenerator(output_dir=tmp_path)
    out_file = tmp_path / "test_edge_brain.py"
    res = generator.generate(board="esp32", output_file=str(out_file))

    assert res["status"] == "SUCCESS"
    assert out_file.exists()

    code = out_file.read_text(encoding="utf-8")

    # Mandatory functions check
    assert "def set_pin(" in code
    assert "def read_adc(" in code
    assert "def pwm(" in code
    assert "def connect_wifi(" in code
    assert "def collect_telemetry(" in code

    # Mandatory JSON commands in command listener
    assert '"set_pin"' in code
    assert '"read_adc"' in code
    assert '"pwm"' in code

    # AST Syntax verification
    parsed = ast.parse(code)
    func_names = {node.name for node in ast.walk(parsed) if isinstance(node, ast.FunctionDef)}
    assert "set_pin" in func_names
    assert "read_adc" in func_names
    assert "pwm" in func_names


def test_auto_flash_simulation():
    """Mocks esptool commands to ensure they are generated correctly and proactive interrupt fired."""
    orchestrator = ProgrammingOrchestrator.get_instance()

    with patch("subprocess.run") as mock_subproc:
        mock_subproc.return_value = MagicMock(returncode=0, stdout="Flash complete", stderr="")
        
        res = orchestrator.flash_edge_brain(board="esp32", port="COM5", simulate=True)

        assert res["status"] == "SUCCESS"
        assert res["board"] == "ESP32"
        assert res["port"] == "COM5"

        commands = res["commands"]
        assert len(commands) == 2

        # Verify erase_flash command syntax
        erase_cmd = commands[0]
        assert "esptool.py" in erase_cmd[0]
        assert "erase_flash" in erase_cmd
        assert "COM5" in erase_cmd

        # Verify write_flash command syntax
        write_cmd = commands[1]
        assert "esptool.py" in write_cmd[0]
        assert "write_flash" in write_cmd
        assert "esp32" in write_cmd
        assert "921600" in write_cmd
        assert "COM5" in write_cmd

        # Verify proactive interrupt notification
        interrupt = res["interrupt_message"]
        assert ("[Orvix Interrupts]" in interrupt) or ("[P.H.A.S.S Interrupts]" in interrupt)
        assert "your ESP32 Edge Brain is online and ready" in interrupt
        assert "receiving telemetry" in interrupt


def test_remote_voice_relay(ephemeral_broker):
    """Sends a simulated transcription from phone and verifies main P.H.A.S.S processes it."""
    import websockets

    received_response = None

    async def client_voice_relay():
        nonlocal received_response
        uri = f"ws://127.0.0.1:{ephemeral_broker.ws_port}"
        async with websockets.connect(uri) as ws:
            # Authenticate
            await ws.send(json.dumps({
                "type": "auth",
                "token": ephemeral_broker.auth_token,
                "client_id": "phone_mujahith",
                "client_type": "phone",
                "signal_strength": -45,
            }))
            await ws.recv()

            # Voice command relay
            await ws.send(json.dumps({
                "type": "voice_relay",
                "query": "hello",
                "client_id": "phone_mujahith",
            }))

            res = json.loads(await ws.recv())
            if res.get("type") == "response":
                received_response = res.get("reply", "")

    asyncio.run(client_voice_relay())
    assert received_response is not None
    assert len(received_response) > 0


def test_natural_language_network_commands():
    """Verifies all 5 natural language triggers route and execute cleanly."""
    # 1. Connect phone
    intent1 = route_intent("Connect my phone.")
    assert intent1 == "network_connect_phone"
    res1 = process_query("Connect my phone.")
    assert "network broker is active" in res1

    # 2. Where is my phone
    intent2 = route_intent("Where is my phone?")
    assert intent2 == "network_phone_locate"
    res2 = process_query("Where is my phone?")
    assert "phone" in res2.lower()

    # 3. Generate edge brain
    intent3 = route_intent("Generate an edge brain for ESP32.")
    assert intent3 == "edge_brain_generate"
    res3 = process_query("Generate an edge brain for ESP32.")
    assert "Edge Brain firmware" in res3
    assert "ESP32" in res3

    # 4. Flash ESP32
    intent4 = route_intent("Flash my ESP32.")
    assert intent4 == "edge_brain_flash"
    res4 = process_query("Flash my ESP32.")
    assert "Edge Brain Commissioning SUCCESS" in res4 or "flashed and commissioned" in res4

    # 5. Remote hardware control
    intent5 = route_intent("Turn on pin 2 on my remote ESP.")
    assert intent5 == "edge_remote_control"
    res5 = process_query("Turn on pin 2 on my remote ESP.")
    assert "Pin 2 on remote ESP has been set to HIGH (ON)" in res5

    intent5_off = route_intent("Turn off pin 13 on my remote ESP.")
    assert intent5_off == "edge_remote_control"
    res5_off = process_query("Turn off pin 13 on my remote ESP.")
    assert "Pin 13 on remote ESP has been set to LOW (OFF)" in res5_off
