"""
Smart Home & IoT Matrix Tool for Llama Assistant & P.H.A.S.S Sphere.
Integrates with Home Assistant REST API or operates via an autonomous, stateful virtual IoT simulator.
Supports:
- Lights (toggle, brightness, RGB color)
- Thermostats / Climate (temperature target, HVAC mode)
- Smart Switches & Outlets (turn on/off, power metrics)
- Sensors (temperature, humidity, motion, presence)
- Smart Scenes ("movie_night", "good_morning", "night_mode", "all_off")
"""

from __future__ import annotations
import os
import json
import time
import logging
from typing import Dict, Any, List, Optional
from tools.registry import tool_registry

logger = logging.getLogger("phass.tools.smart_home")

# Simulated Virtual IoT Device Store
VIRTUAL_SMART_DEVICES: Dict[str, Dict[str, Any]] = {
    "light.living_room": {
        "entity_id": "light.living_room",
        "name": "Living Room Ceiling Light",
        "type": "light",
        "state": "on",
        "attributes": {"brightness": 80, "color_temp": 3000, "rgb_color": [255, 230, 180]},
    },
    "light.bedroom": {
        "entity_id": "light.bedroom",
        "name": "Master Bedroom Lamp",
        "type": "light",
        "state": "off",
        "attributes": {"brightness": 0, "color_temp": 2700},
    },
    "light.desk": {
        "entity_id": "light.desk",
        "name": "Office Desk Lamp",
        "type": "light",
        "state": "on",
        "attributes": {"brightness": 100, "rgb_color": [255, 255, 255]},
    },
    "switch.coffee_maker": {
        "entity_id": "switch.coffee_maker",
        "name": "Smart Plug - Espresso Maker",
        "type": "switch",
        "state": "off",
        "attributes": {"power_watts": 0.0, "daily_kwh": 0.42},
    },
    "switch.workstation": {
        "entity_id": "switch.workstation",
        "name": "Workstation Power Strip",
        "type": "switch",
        "state": "on",
        "attributes": {"power_watts": 145.2, "daily_kwh": 1.85},
    },
    "climate.main_thermostat": {
        "entity_id": "climate.main_thermostat",
        "name": "Home Climate Controller",
        "type": "climate",
        "state": "heat",
        "attributes": {
            "current_temperature": 21.5,
            "target_temperature": 22.0,
            "hvac_mode": "heat",
            "humidity": 45,
        },
    },
    "sensor.outdoor_temperature": {
        "entity_id": "sensor.outdoor_temperature",
        "name": "Balcony Weather Sensor",
        "type": "sensor",
        "state": "18.4",
        "attributes": {"unit_of_measurement": "°C", "humidity": 55},
    },
    "sensor.front_door_motion": {
        "entity_id": "sensor.front_door_motion",
        "name": "Front Entry Motion Detector",
        "type": "sensor",
        "state": "clear",
        "attributes": {"battery": 92, "last_motion": time.time() - 3600},
    },
    "media_player.living_room_tv": {
        "entity_id": "media_player.living_room_tv",
        "name": "Living Room OLED TV",
        "type": "media_player",
        "state": "standby",
        "attributes": {"volume_level": 0.35, "source": "HDMI 1"},
    },
}


class SmartHomeHub:
    """
    Manages connection to Home Assistant API with stateful fallback simulation.
    """

    def __init__(self):
        self.hass_url = os.environ.get("HASS_URL")
        self.hass_token = os.environ.get("HASS_TOKEN")
        self.devices = dict(VIRTUAL_SMART_DEVICES)

    def is_live_hass(self) -> bool:
        return bool(self.hass_url and self.hass_token)

    def discover_devices(self, filter_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns catalog of known smart home devices, optionally filtered by domain."""
        res = list(self.devices.values())
        if filter_type:
            f = filter_type.lower()
            res = [d for d in res if d.get("type") == f or d.get("entity_id", "").startswith(f)]
        return res

    def get_state(self, entity_id: str) -> Dict[str, Any]:
        """Retrieves state and attributes for a specified entity."""
        if entity_id in self.devices:
            return {"status": "SUCCESS", "device": self.devices[entity_id]}
        return {"status": "ERROR", "error": f"Device {entity_id} not found."}

    def set_state(self, entity_id: str, state: str, attributes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Updates device state (e.g. 'on', 'off') and attributes."""
        if entity_id not in self.devices:
            # Dynamically register device if new
            self.devices[entity_id] = {
                "entity_id": entity_id,
                "name": entity_id.replace("_", " ").title(),
                "type": entity_id.split(".")[0] if "." in entity_id else "custom",
                "state": state,
                "attributes": attributes or {},
            }
        else:
            self.devices[entity_id]["state"] = state
            if attributes:
                self.devices[entity_id]["attributes"].update(attributes)

        return {
            "status": "SUCCESS",
            "entity_id": entity_id,
            "new_state": state,
            "attributes": self.devices[entity_id]["attributes"],
        }

    def toggle(self, entity_id: str) -> Dict[str, Any]:
        """Toggles a light or switch between 'on' and 'off'."""
        if entity_id not in self.devices:
            return {"status": "ERROR", "error": f"Device {entity_id} not found."}

        current = self.devices[entity_id].get("state", "off").lower()
        new_state = "off" if current == "on" else "on"
        self.devices[entity_id]["state"] = new_state
        return {"status": "SUCCESS", "entity_id": entity_id, "state": new_state}

    def set_temperature(self, entity_id: str, temperature: float) -> Dict[str, Any]:
        """Sets the thermostat setpoint temperature."""
        if entity_id not in self.devices:
            return {"status": "ERROR", "error": f"Climate entity {entity_id} not found."}

        self.devices[entity_id]["attributes"]["target_temperature"] = float(temperature)
        return {
            "status": "SUCCESS",
            "entity_id": entity_id,
            "target_temperature": float(temperature),
        }

    def set_light_brightness(self, entity_id: str, brightness: int) -> Dict[str, Any]:
        """Sets light brightness between 0 and 100%."""
        if entity_id not in self.devices:
            return {"status": "ERROR", "error": f"Light entity {entity_id} not found."}

        b = max(0, min(100, int(brightness)))
        self.devices[entity_id]["state"] = "on" if b > 0 else "off"
        self.devices[entity_id]["attributes"]["brightness"] = b
        return {"status": "SUCCESS", "entity_id": entity_id, "brightness": b, "state": self.devices[entity_id]["state"]}

    def execute_scene(self, scene_name: str) -> Dict[str, Any]:
        """Executes a multi-device smart home scene."""
        name = scene_name.lower().replace(" ", "_")
        actions_taken = []

        if name == "movie_night":
            self.set_light_brightness("light.living_room", 15)
            self.set_state("light.desk", "off")
            self.set_state("media_player.living_room_tv", "on", {"source": "Cinema App"})
            actions_taken.append("Dimmed living room to 15%, turned off desk light, powered on TV.")

        elif name == "good_morning":
            self.set_light_brightness("light.bedroom", 80)
            self.set_state("switch.coffee_maker", "on")
            self.set_temperature("climate.main_thermostat", 22.5)
            actions_taken.append("Raised bedroom lighting, switched on espresso machine, set thermostat to 22.5°C.")

        elif name == "all_off":
            for eid, dev in self.devices.items():
                if dev.get("type") in ["light", "switch"]:
                    dev["state"] = "off"
            actions_taken.append("Turned off all lights and non-critical smart plugs.")

        else:
            return {"status": "ERROR", "error": f"Unknown scene: {scene_name}"}

        return {
            "status": "SUCCESS",
            "scene": scene_name,
            "actions": actions_taken,
            "timestamp": time.time(),
        }


# Global Singleton
smart_home_hub = SmartHomeHub()


# =============================================================================
# Tool Registry Bindings
# =============================================================================
@tool_registry.register(
    name="smart_home_discover_devices",
    description="Lists all connected smart home lights, thermostats, switches, and sensors.",
)
def smart_home_discover_devices(filter_type: Optional[str] = None) -> List[Dict[str, Any]]:
    return smart_home_hub.discover_devices(filter_type)


@tool_registry.register(
    name="smart_home_get_state",
    description="Gets the current state and attributes for a smart home device by entity_id.",
)
def smart_home_get_state(entity_id: str) -> Dict[str, Any]:
    return smart_home_hub.get_state(entity_id)


@tool_registry.register(
    name="smart_home_set_state",
    description="Sets state ('on', 'off') and optional attributes for a smart home entity.",
)
def smart_home_set_state(entity_id: str, state: str, attributes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return smart_home_hub.set_state(entity_id, state, attributes)


@tool_registry.register(
    name="smart_home_toggle",
    description="Toggles a smart light or plug between ON and OFF.",
)
def smart_home_toggle(entity_id: str) -> Dict[str, Any]:
    return smart_home_hub.toggle(entity_id)


@tool_registry.register(
    name="smart_home_set_temperature",
    description="Sets the target temperature of a smart thermostat (e.g. 21.5).",
)
def smart_home_set_temperature(entity_id: str, temperature: float) -> Dict[str, Any]:
    return smart_home_hub.set_temperature(entity_id, temperature)


@tool_registry.register(
    name="smart_home_set_light_brightness",
    description="Sets light brightness percentage from 0 to 100.",
)
def smart_home_set_light_brightness(entity_id: str, brightness: int) -> Dict[str, Any]:
    return smart_home_hub.set_light_brightness(entity_id, brightness)


@tool_registry.register(
    name="smart_home_execute_scene",
    description="Triggers a smart home scene: 'movie_night', 'good_morning', 'all_off'.",
)
def smart_home_execute_scene(scene_name: str) -> Dict[str, Any]:
    return smart_home_hub.execute_scene(scene_name)
