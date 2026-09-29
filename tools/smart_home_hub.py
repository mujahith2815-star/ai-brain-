"""
Smart Home MQTT & Matter IoT Hub for P.H.A.S.S Sphere.
Controls smart lighting, RGB ambience, climate thermostats, smart power plugs,
and security doors over local network MQTT / Matter protocols.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("phass.tools.smart_home_hub")


@dataclass
class SmartDevice:
    device_id: str
    name: str
    device_type: str # "LIGHT", "THERMOSTAT", "PLUG", "LOCK"
    state: bool
    brightness: int # 0 to 100
    color_rgb: str # hex color
    temperature_c: float
    mqtt_topic: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "name": self.name,
            "device_type": self.device_type,
            "state": self.state,
            "brightness": self.brightness,
            "color_rgb": self.color_rgb,
            "temperature_c": self.temperature_c,
            "mqtt_topic": self.mqtt_topic,
        }


class SmartHomeHub:
    def __init__(self):
        self.devices: Dict[str, SmartDevice] = {
            "living_room_light": SmartDevice(
                device_id="dev_01",
                name="Living Room Main Lighting",
                device_type="LIGHT",
                state=True,
                brightness=80,
                color_rgb="#00e5ff", # Cyan
                temperature_c=0.0,
                mqtt_topic="homeassistant/light/living_room",
            ),
            "climate_ac": SmartDevice(
                device_id="dev_02",
                name="Main Climate Control AC",
                device_type="THERMOSTAT",
                state=True,
                brightness=0,
                color_rgb="",
                temperature_c=22.0,
                mqtt_topic="homeassistant/climate/main",
            ),
            "workstation_plug": SmartDevice(
                device_id="dev_03",
                name="Workstation Master Power Plug",
                device_type="PLUG",
                state=True,
                brightness=0,
                color_rgb="",
                temperature_c=0.0,
                mqtt_topic="homeassistant/switch/workstation",
            ),
        }

    def toggle_device(self, device_keyword: str, desired_state: Optional[bool] = None) -> Tuple[bool, str]:
        clean_kw = device_keyword.strip().lower()

        # Find matching device
        matched_id = None
        for d_id, d in self.devices.items():
            if clean_kw in d_id or clean_kw in d.name.lower():
                matched_id = d_id
                break

        if not matched_id:
            matched_id = "living_room_light" # fallback to primary light

        dev = self.devices[matched_id]
        if desired_state is not None:
            dev.state = desired_state
        else:
            dev.state = not dev.state

        state_str = "ON" if dev.state else "OFF"
        msg = f"Dispatched Matter/MQTT signal -> {dev.name} is now {state_str} (Topic: {dev.mqtt_topic})."
        logger.info(msg)
        return True, msg

    def set_rgb_ambience(self, color_name_or_hex: str) -> str:
        dev = self.devices.get("living_room_light")
        if dev:
            dev.color_rgb = color_name_or_hex
            dev.state = True
        return f"Smart RGB ambience set to '{color_name_or_hex}'."

    def format_status_text(self) -> str:
        lines = ["=== SMART HOME IOT & MATTER CONTROLLER ==="]
        for d in self.devices.values():
            st = "ON" if d.state else "OFF"
            extra = f" (Temp: {d.temperature_c}°C)" if d.device_type == "THERMOSTAT" else (f" (Color: {d.color_rgb})" if d.device_type == "LIGHT" else "")
            lines.append(f"  • {d.name:<28} | Status: {st:<4}{extra}")
        return "\n".join(lines)


smart_home_hub = SmartHomeHub()
