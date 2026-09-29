"""
Dynamic World Model for P.H.A.S.S Sphere.
Maintains persistent situational awareness, physical robot state,
environmental factors, active entities, and relationship graphs.
"""

from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import logging
from .entities import WorldEntity, EntityType, Vector3D
from .spatial_map import SpatialMap
from core.event_bus import event_bus, Event, EventType as EBEventType

logger = logging.getLogger("phass.world_model")


@dataclass
class RobotPhysicalState:
    robot_id: str = "ORB-7-ALPHA"
    chassis_type: str = "spherical_omni"
    battery_percentage: float = 88.5
    battery_voltage: float = 24.2
    battery_temperature_c: float = 28.4
    charging: bool = False
    position: Vector3D = field(default_factory=lambda: Vector3D(0.0, 0.0, 0.25))
    heading_deg: float = 0.0
    velocity: Vector3D = field(default_factory=Vector3D)
    angular_velocity_degps: float = 0.0
    imu_roll: float = 0.0
    imu_pitch: float = 0.0
    imu_yaw: float = 0.0
    internal_temp_c: float = 34.2
    cpu_usage_pct: float = 18.5
    memory_usage_pct: float = 26.0
    status: str = "IDLE"
    connected_systems: List[str] = field(
        default_factory=lambda: ["AI_CORE", "LIDAR_360", "CAMERA_RGB", "IMU_6DOF", "OMNI_DRIVE", "SPEAKER"]
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "robot_id": self.robot_id,
            "chassis_type": self.chassis_type,
            "battery_percentage": round(self.battery_percentage, 1),
            "battery_voltage": round(self.battery_voltage, 2),
            "battery_temperature_c": round(self.battery_temperature_c, 1),
            "charging": self.charging,
            "position": self.position.to_dict(),
            "heading_deg": round(self.heading_deg, 1),
            "velocity": self.velocity.to_dict(),
            "angular_velocity_degps": round(self.angular_velocity_degps, 2),
            "imu_attitude": {
                "roll": round(self.imu_roll, 2),
                "pitch": round(self.imu_pitch, 2),
                "yaw": round(self.imu_yaw, 2),
            },
            "internal_temp_c": round(self.internal_temp_c, 1),
            "cpu_usage_pct": round(self.cpu_usage_pct, 1),
            "memory_usage_pct": round(self.memory_usage_pct, 1),
            "status": self.status,
            "connected_systems": self.connected_systems,
        }


@dataclass
class EnvironmentalState:
    ambient_temperature_c: float = 21.5
    ambient_humidity_pct: float = 45.0
    ambient_noise_db: float = 42.0
    ambient_lux: float = 350.0
    air_quality_index: int = 24
    wifi_signal_dbm: int = -52

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ambient_temperature_c": round(self.ambient_temperature_c, 1),
            "ambient_humidity_pct": round(self.ambient_humidity_pct, 1),
            "ambient_noise_db": round(self.ambient_noise_db, 1),
            "ambient_lux": round(self.ambient_lux, 1),
            "air_quality_index": self.air_quality_index,
            "wifi_signal_dbm": self.wifi_signal_dbm,
        }


class WorldModel:
    def __init__(self):
        self.spatial_map = SpatialMap()
        self.robot_state = RobotPhysicalState()
        self.environment = EnvironmentalState()
        self.entities: Dict[str, WorldEntity] = {}
        self.active_goal_summary: str = "Autonomous Standby"
        self.active_task_summary: str = "Monitoring Environment"
        self.known_relationships: List[Dict[str, str]] = []
        self.observation_history_count: int = 0
        self.last_updated: str = datetime.now(timezone.utc).isoformat()
        self._lock = asyncio.Lock()

        # Seed initial default environment entities
        self._seed_default_entities()

    def _seed_default_entities(self):
        self.add_or_update_entity(
            WorldEntity(
                id="ENT-DOCK01",
                name="Magnetic Fast-Charge Dock",
                entity_type=EntityType.CHARGING_DOCK,
                position=Vector3D(0.0, 4.5, 0.0),
                dimensions=Vector3D(1.0, 1.0, 0.2),
                metadata={"voltage": 24.0, "status": "READY"},
            )
        )
        self.add_or_update_entity(
            WorldEntity(
                id="ENT-WORK01",
                name="Central Engineering Workstation",
                entity_type=EntityType.WORKSTATION,
                position=Vector3D(3.0, 2.0, 0.0),
                dimensions=Vector3D(1.5, 0.8, 0.9),
                metadata={"ip": "192.168.1.105", "os": "Linux 6.8", "status": "ONLINE"},
            )
        )
        self.add_or_update_entity(
            WorldEntity(
                id="ENT-TERM01",
                name="Diagnostic Server Rack",
                entity_type=EntityType.DEVICE,
                position=Vector3D(-3.5, 1.5, 0.0),
                dimensions=Vector3D(0.8, 0.8, 1.8),
                metadata={"services": ["database", "auth", "mqtt"], "load": "NORMAL"},
            )
        )

    def add_or_update_entity(self, entity: WorldEntity) -> None:
        self.entities[entity.id] = entity
        self.last_updated = datetime.now(timezone.utc).isoformat()

    def remove_entity(self, entity_id: str) -> bool:
        if entity_id in self.entities:
            del self.entities[entity_id]
            self.last_updated = datetime.now(timezone.utc).isoformat()
            return True
        return False

    def get_entity(self, entity_id: str) -> Optional[WorldEntity]:
        return self.entities.get(entity_id)

    async def ingest_observation(self, observation: Dict[str, Any]) -> None:
        """
        Updates the belief state based on a sensory observation.
        """
        async with self._lock:
            self.observation_history_count += 1
            obs_type = observation.get("type", "")
            data = observation.get("data", {})

            if obs_type == "TELEMETRY":
                if "battery_percentage" in data:
                    self.robot_state.battery_percentage = data["battery_percentage"]
                if "internal_temp_c" in data:
                    self.robot_state.internal_temp_c = data["internal_temp_c"]
                if "position" in data:
                    pos = data["position"]
                    self.robot_state.position = Vector3D(pos.get("x", 0), pos.get("y", 0), pos.get("z", 0))

            elif obs_type == "OBJECT_DETECTION":
                name = data.get("label", "Unknown Object")
                ent_type = EntityType.OBSTACLE
                if "person" in name.lower():
                    ent_type = EntityType.PERSON
                elif "workstation" in name.lower() or "computer" in name.lower():
                    ent_type = EntityType.WORKSTATION
                elif "dock" in name.lower() or "charger" in name.lower():
                    ent_type = EntityType.CHARGING_DOCK

                ent_id = data.get("id", f"ENT-OBS-{self.observation_history_count}")
                pos_data = data.get("position", {})
                pos = Vector3D(pos_data.get("x", 1.0), pos_data.get("y", 1.0), pos_data.get("z", 0.0))

                entity = WorldEntity(
                    id=ent_id,
                    name=name,
                    entity_type=ent_type,
                    position=pos,
                    confidence=data.get("confidence", 0.90),
                    metadata=data.get("metadata", {}),
                )
                self.add_or_update_entity(entity)

            elif obs_type == "ENVIRONMENT_SENSORS":
                if "temperature" in data:
                    self.environment.ambient_temperature_c = data["temperature"]
                if "humidity" in data:
                    self.environment.ambient_humidity_pct = data["humidity"]
                if "noise" in data:
                    self.environment.ambient_noise_db = data["noise"]

            self.last_updated = datetime.now(timezone.utc).isoformat()

    def sync_live_hardware(self) -> None:
        """Syncs robot physical state with live Windows kernel hardware telemetry."""
        try:
            from sensors.live_hardware_hub import live_hardware_hub
            telemetry = live_hardware_hub.get_all_live_telemetry()
            self.robot_state.battery_percentage = telemetry.battery_charger.battery_percentage
            self.robot_state.charging = telemetry.battery_charger.is_charging
            self.robot_state.cpu_usage_pct = telemetry.estimated_cpu_load_pct
            self.robot_state.memory_usage_pct = telemetry.ram_load_pct
        except Exception:
            pass

    def get_snapshot(self) -> Dict[str, Any]:
        """
        Returns a complete serializable representation of the current world model.
        """
        self.sync_live_hardware()
        nearest_lm, dist = self.spatial_map.find_nearest_landmark(self.robot_state.position)
        return {
            "timestamp": self.last_updated,
            "robot_state": self.robot_state.to_dict(),
            "environment": self.environment.to_dict(),
            "spatial_map": self.spatial_map.to_dict(),
            "nearest_landmark": {"name": nearest_lm, "distance_m": dist},
            "entities": [e.to_dict() for e in self.entities.values()],
            "active_goal": self.active_goal_summary,
            "active_task": self.active_task_summary,
            "known_relationships": self.known_relationships,
            "total_observations_ingested": self.observation_history_count,
        }


world_model = WorldModel()
