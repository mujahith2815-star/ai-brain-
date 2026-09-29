"""
Sensory streams and physical telemetry processor for P.H.A.S.S Sphere.
Normalizes 360-degree LiDAR raycasts, 6-DOF IMU, ultrasonic, environmental, and battery sensors.
"""

from __future__ import annotations
import math
import random
from typing import Any, Dict, List, Optional
import logging
from .observation import Observation, ObservationType

logger = logging.getLogger("phass.perception.sensors")


class SensorHub:
    def __init__(self, lidar_ray_count: int = 64, max_range_m: float = 12.0):
        self.lidar_ray_count = lidar_ray_count
        self.max_range_m = max_range_m

    def generate_lidar_scan(self, robot_pos: Dict[str, float], obstacles: Optional[List[Dict[str, Any]]] = None) -> Observation:
        """
        Computes 360-degree 2D distance raycasts from the robot's current position.
        """
        ranges: List[float] = []
        angles_deg: List[float] = []
        step = 360.0 / self.lidar_ray_count

        for i in range(self.lidar_ray_count):
            angle = i * step
            rad = math.radians(angle)
            angles_deg.append(round(angle, 1))

            # Raycast distance calculation against boundary walls (box -5 to +5)
            # Find intersection with walls
            dx = math.cos(rad)
            dy = math.sin(rad)
            rx = robot_pos.get("x", 0.0)
            ry = robot_pos.get("y", 0.0)

            # Room bounds
            min_dist = self.max_range_m
            for bound_x in (-5.0, 5.0):
                if abs(dx) > 1e-4:
                    t = (bound_x - rx) / dx
                    if t > 0 and abs(ry + t * dy) <= 5.0 and t < min_dist:
                        min_dist = t
            for bound_y in (-5.0, 5.0):
                if abs(dy) > 1e-4:
                    t = (bound_y - ry) / dy
                    if t > 0 and abs(rx + t * dx) <= 5.0 and t < min_dist:
                        min_dist = t

            # Check obstacle entities
            if obstacles:
                for obs in obstacles:
                    ox = obs.get("position", {}).get("x", 0.0)
                    oy = obs.get("position", {}).get("y", 0.0)
                    dist_to_center = math.hypot(ox - rx, oy - ry)
                    if dist_to_center < min_dist:
                        angle_to_obs = math.degrees(math.atan2(oy - ry, ox - rx)) % 360.0
                        diff = abs(angle - angle_to_obs)
                        if diff < 15.0 or diff > 345.0:
                            min_dist = min(min_dist, max(0.2, dist_to_center - 0.4))

            # Add minor noise for realism
            noisy_dist = max(0.1, round(min_dist + random.uniform(-0.02, 0.02), 3))
            ranges.append(noisy_dist)

        return Observation(
            type=ObservationType.LIDAR_SCAN,
            source="360_SOLID_STATE_LIDAR",
            confidence=0.99,
            data={
                "ray_count": self.lidar_ray_count,
                "max_range_m": self.max_range_m,
                "ranges_m": ranges,
                "angles_deg": angles_deg,
                "min_clearance_m": min(ranges),
            },
            location=robot_pos,
        )

    def generate_imu_telemetry(self, current_velocity: Dict[str, float]) -> Observation:
        """
        Generates 6-DOF IMU and gyroscope stabilization readings.
        """
        vx = current_velocity.get("x", 0.0)
        vy = current_velocity.get("y", 0.0)
        speed = math.hypot(vx, vy)

        return Observation(
            type=ObservationType.IMU_TELEMETRY,
            source="6DOF_IMU_GYROSCOPE",
            confidence=0.98,
            data={
                "linear_acceleration": {
                    "ax": round(random.uniform(-0.05, 0.05) + (vx * 0.1), 3),
                    "ay": round(random.uniform(-0.05, 0.05) + (vy * 0.1), 3),
                    "az": round(9.81 + random.uniform(-0.02, 0.02), 3),
                },
                "angular_velocity_radps": {
                    "gx": round(random.uniform(-0.01, 0.01), 3),
                    "gy": round(random.uniform(-0.01, 0.01), 3),
                    "gz": round(random.uniform(-0.02, 0.02) + (speed * 0.05), 3),
                },
                "internal_balance_status": "LOCKED_STABLE",
            },
        )

    def generate_environmental_sensors(self) -> Observation:
        """
        Environmental temperature, humidity, and barometric pressure.
        """
        return Observation(
            type=ObservationType.ENVIRONMENT_SENSORS,
            source="ENVIRONMENTAL_SENSOR_SUITE",
            confidence=0.95,
            data={
                "temperature_c": round(21.5 + random.uniform(-0.2, 0.2), 1),
                "humidity_pct": round(45.0 + random.uniform(-0.5, 0.5), 1),
                "pressure_hpa": round(1013.25 + random.uniform(-0.5, 0.5), 1),
                "gas_resistance_kohm": round(85.4 + random.uniform(-1.0, 1.0), 1),
            },
        )
