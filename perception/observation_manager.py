"""
Observation Manager for P.H.A.S.S Sphere.
Synchronizes perception pipelines (Vision, Audio, LiDAR, IMU, Telemetry)
and delivers normalized observation events to the World Model and Event Bus.
"""

from __future__ import annotations
import asyncio
from typing import Any, Dict, List, Optional
import logging
from .observation import Observation, ObservationType
from .vision import VisionProcessor
from .audio import AudioProcessor
from .sensors import SensorHub
from core.event_bus import event_bus, Event, EventType

logger = logging.getLogger("phass.perception.manager")


class ObservationManager:
    def __init__(self):
        self.vision = VisionProcessor()
        self.audio = AudioProcessor()
        self.sensors = SensorHub()
        self.recent_observations: List[Observation] = []
        self._history_limit = 100

    async def poll_full_sensor_sweep(
        self,
        robot_pos: Dict[str, float],
        velocity: Dict[str, float],
        active_entities: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Observation]:
        """
        Executes a coordinated sensory sweep across vision, lidar, IMU, and environment.
        """
        lidar_obs = self.sensors.generate_lidar_scan(robot_pos, active_entities)
        imu_obs = self.sensors.generate_imu_telemetry(velocity)
        env_obs = self.sensors.generate_environmental_sensors()
        vision_obs = await self.vision.capture_frame_analysis(active_entities)

        observations = [lidar_obs, imu_obs, env_obs, vision_obs]

        for obs in observations:
            self.recent_observations.append(obs)
            if len(self.recent_observations) > self._history_limit:
                self.recent_observations.pop(0)

        # Notify event bus if objects detected
        if vision_obs.data.get("detected_objects"):
            await event_bus.publish(
                Event(
                    type=EventType.OBJECT_DETECTED,
                    source="ObservationManager",
                    data=vision_obs.data,
                )
            )

        return observations

    async def ingest_voice_command(self, transcript: str) -> Observation:
        obs = await self.audio.parse_voice_command(transcript)
        self.recent_observations.append(obs)
        await event_bus.publish(
            Event(
                type=EventType.VOICE_DETECTED,
                source="ObservationManager",
                data=obs.data,
            )
        )
        return obs

    def get_latest_observations(self, limit: int = 10) -> List[Dict[str, Any]]:
        return [o.to_dict() for o in self.recent_observations[-limit:]]


observation_manager = ObservationManager()
