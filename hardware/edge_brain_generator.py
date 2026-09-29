"""
Edge Brain Generator for MicroPython-enabled Hardware (ESP32 / Pi Pico W).
Generates standalone, self-contained edge_brain.py firmware with:
- Auto-reconnecting Wi-Fi Manager
- Bi-directional Network Broker Client (WebSocket/TCP)
- GPIO Controller: set_pin(), read_adc(), pwm()
- Command Listener: {"action": "set_pin", "pin": 2, "state": 1}, etc.
- 5-Second Telemetry Status Publisher
"""

from __future__ import annotations
import ast
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("phass.hardware.edge_brain_generator")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "network_config.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "firmware"
TEMPLATE_FILE = PROJECT_ROOT / "hardware" / "edge_brain_template.txt"


def get_default_network_config() -> Dict[str, Any]:
    default_cfg = {
        "wifi_ssid": "HomeNetwork_2.4G",
        "wifi_password": "secure_wifi_password",
        "broker_ip": "192.168.1.100",
        "broker_port": 1883,
        "auth_token": "phass_omni_secret_token_2026",
    }
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    default_cfg["wifi_ssid"] = data.get("wifi_ssid", default_cfg["wifi_ssid"])
                    default_cfg["wifi_password"] = data.get("wifi_password", default_cfg["wifi_password"])
                    default_cfg["broker_ip"] = data.get("broker_ip", default_cfg["broker_ip"])
                    default_cfg["broker_port"] = data.get("mqtt_port", default_cfg["broker_port"])
                    default_cfg["auth_token"] = data.get("auth_token", default_cfg["auth_token"])
        except Exception as e:
            logger.warning(f"Could not read network config: {e}")
    return default_cfg


def generate_edge_brain_code(
    board: str = "esp32",
    wifi_ssid: Optional[str] = None,
    wifi_password: Optional[str] = None,
    broker_ip: Optional[str] = None,
    broker_port: Optional[int] = None,
    auth_token: Optional[str] = None,
) -> str:
    """Synthesizes valid MicroPython source code for the edge device."""
    cfg = get_default_network_config()
    ssid = wifi_ssid or cfg["wifi_ssid"]
    password = wifi_password or cfg["wifi_password"]
    host = broker_ip or cfg["broker_ip"]
    port = broker_port or cfg["broker_port"]
    token = auth_token or cfg["auth_token"]
    board_lower = board.lower()

    adc_comment = "# Supported ADC pins: 32, 33, 34, 35, 36, 39" if "esp" in board_lower else "# Supported ADC pins: 26, 27, 28"

    template = TEMPLATE_FILE.read_text(encoding="utf-8")
    result = template
    replacements = {
        "{BOARD_UPPER}": board.upper(),
        "{BOARD_LOWER}": board_lower,
        "{WIFI_SSID}": str(ssid),
        "{WIFI_PASSWORD}": str(password),
        "{BROKER_IP}": str(host),
        "{BROKER_PORT}": str(port),
        "{AUTH_TOKEN}": str(token),
        "{ADC_COMMENT}": str(adc_comment),
    }
    for k, v in replacements.items():
        result = result.replace(k, v)
    return result


class EdgeBrainGenerator:
    """Coordinates Edge Brain firmware synthesis and disk staging."""
    _instance: Optional[EdgeBrainGenerator] = None

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or DEFAULT_OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_instance(cls) -> EdgeBrainGenerator:
        if cls._instance is None:
            cls._instance = EdgeBrainGenerator()
        return cls._instance

    def generate(
        self,
        board: str = "esp32",
        output_file: Optional[str] = None,
        wifi_ssid: Optional[str] = None,
        wifi_password: Optional[str] = None,
        broker_ip: Optional[str] = None,
        broker_port: Optional[int] = None,
        auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generates and saves the edge_brain.py firmware file.
        Validates AST parsing to guarantee syntactic validity.
        """
        code = generate_edge_brain_code(
            board=board,
            wifi_ssid=wifi_ssid,
            wifi_password=wifi_password,
            broker_ip=broker_ip,
            broker_port=broker_port,
            auth_token=auth_token,
        )

        try:
            ast.parse(code)
        except SyntaxError as se:
            logger.error(f"Generated Edge Brain syntax error: {se}")
            return {
                "status": "FAILED",
                "error": f"SyntaxError line {se.lineno}: {se.msg}",
                "board": board,
            }

        target_file = Path(output_file) if output_file else (self.output_dir / "edge_brain.py")
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(code, encoding="utf-8")

        summary = (
            f"MicroPython Edge Brain generated for {board.upper()}:\n"
            f"• Output Path: {target_file}\n"
            f"• Wi-Fi Manager: Embedded SSID & auto-reconnect\n"
            f"• Remote Broker: Connecting to {broker_ip or '192.168.1.100'}:{broker_port or 1883}\n"
            f"• GPIO Capabilities: set_pin(pin, state), read_adc(pin), pwm(pin, duty)\n"
            f"• Telemetry Cadence: 5 seconds interval\n"
            f"• Syntax Status: VERIFIED 100% VALID."
        )

        return {
            "status": "SUCCESS",
            "board": board.upper(),
            "file_path": str(target_file),
            "code": code,
            "size_bytes": len(code),
            "functions": ["set_pin", "read_adc", "pwm", "collect_telemetry", "execute_command"],
            "summary": summary,
        }


edge_brain_generator = EdgeBrainGenerator.get_instance()
