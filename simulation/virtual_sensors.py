"""
Virtual Sensors for the 3D Simulation Environment.
Generates realistic raycasted LiDAR scans, camera frame bounding boxes, and IMU telemetry.
"""

from __future__ import annotations
import math
import random
from typing import Any, Dict, List
from .environment import simulated_env
from perception.observation import Observation, ObservationType


class VirtualSensorEngine:
    def __init__(self, ray_count: int = 64, max_range_m: float = 12.0):
        self.ray_count = ray_count
        self.max_range_m = max_range_m

    def generate_lidar_point_cloud(self, robot_x: float, robot_y: float) -> Dict[str, Any]:
        """
        Calculates 2D LiDAR ray intersections against arena walls and simulation obstacles.
        """
        ranges: List[float] = []
        points: List[Dict[str, float]] = []
        step = 360.0 / self.ray_count

        for i in range(self.ray_count):
            deg = i * step
            rad = math.radians(deg)
            dx = math.cos(rad)
            dy = math.sin(rad)

            # Check boundary walls (-5 to 5)
            min_dist = self.max_range_m
            for bound_x in (-5.0, 5.0):
                if abs(dx) > 1e-4:
                    t = (bound_x - robot_x) / dx
                    if t > 0 and abs(robot_y + t * dy) <= 5.0 and t < min_dist:
                        min_dist = t
            for bound_y in (-5.0, 5.0):
                if abs(dy) > 1e-4:
                    t = (bound_y - robot_y) / dy
                    if t > 0 and abs(robot_x + t * dx) <= 5.0 and t < min_dist:
                        min_dist = t

            # Check cylindrical obstacles
            for obs in simulated_env.obstacles:
                ox = obs.position.x
                oy = obs.position.y
                # Circle ray intersection
                fx = robot_x - ox
                fy = robot_y - oy
                a = dx * dx + dy * dy
                b = 2 * (fx * dx + fy * dy)
                c = (fx * fx + fy * fy) - (obs.radius_m * obs.radius_m)
                discriminant = b * b - 4 * a * c
                if discriminant >= 0:
                    sqrt_disc = math.sqrt(discriminant)
                    t1 = (-b - sqrt_disc) / (2 * a)
                    t2 = (-b + sqrt_disc) / (2 * a)
                    if t1 > 0 and t1 < min_dist:
                        min_dist = t1
                    elif t2 > 0 and t2 < min_dist:
                        min_dist = t2

            noise = random.uniform(-0.015, 0.015)
            final_dist = max(0.15, min_dist + noise)
            ranges.append(round(final_dist, 3))

            px = robot_x + final_dist * dx
            py = robot_y + final_dist * dy
            points.append({"x": round(px, 3), "y": round(py, 3), "z": 0.25})

        return {
            "ray_count": self.ray_count,
            "ranges": ranges,
            "points": points,
            "min_distance_m": min(ranges),
        }


virtual_sensors = VirtualSensorEngine()
