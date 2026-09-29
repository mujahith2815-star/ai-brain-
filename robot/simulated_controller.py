"""
Simulated Spherical Robot Controller for P.H.A.S.S Sphere.
Implements kinematic models for internal omni-wheel drive, gyro stabilization,
dynamic power consumption, and sensory loops.
"""

from __future__ import annotations
import math
import random
import time
from typing import Any, Dict, List, Optional
import logging
from .hardware_abstraction import (
    RobotController,
    MotorInterface,
    SensorInterface,
    BatteryInterface,
    CameraInterface,
    AudioInterface,
)

logger = logging.getLogger("phass.robot.simulated")


class SimulatedMotorDriver(MotorInterface):
    def __init__(self):
        self.vx = 0.0
        self.vy = 0.0
        self.omega = 0.0
        self.bldc_rpm = [0.0, 0.0, 0.0]  # 3 internal omni-wheels
        self.motor_temp_c = 32.0

    def set_omni_velocity(self, vx_mps: float, vy_mps: float, omega_radps: float) -> bool:
        self.vx = vx_mps
        self.vy = vy_mps
        self.omega = omega_radps
        # Inverse kinematics approximation for 3-wheel spherical omni mechanism
        speed = math.hypot(vx_mps, vy_mps)
        self.bldc_rpm[0] = speed * 120.0 + (omega_radps * 30.0)
        self.bldc_rpm[1] = speed * 115.0 - (omega_radps * 30.0)
        self.bldc_rpm[2] = speed * 125.0
        self.motor_temp_c = min(65.0, self.motor_temp_c + (speed * 0.05))
        return True

    def get_motor_telemetry(self) -> Dict[str, Any]:
        return {
            "linear_velocity_mps": {"vx": round(self.vx, 2), "vy": round(self.vy, 2)},
            "angular_velocity_radps": round(self.omega, 2),
            "wheel_rpms": [round(r, 1) for r in self.bldc_rpm],
            "motor_temperature_c": round(self.motor_temp_c, 1),
            "driver_status": "NOMINAL",
        }

    def emergency_brake(self) -> None:
        self.vx = 0.0
        self.vy = 0.0
        self.omega = 0.0
        self.bldc_rpm = [0.0, 0.0, 0.0]


class SimulatedBatteryPack(BatteryInterface):
    def __init__(self, capacity_wh: float = 120.0):
        self.capacity_wh = capacity_wh
        self.current_energy_wh = capacity_wh * 0.885
        self.voltage = 24.2
        self.charging = False
        self.temperature_c = 28.5

    def update_discharge(self, active_power_w: float = 15.0, delta_time_sec: float = 0.1) -> None:
        if self.charging:
            # Charge at 45W
            self.current_energy_wh = min(self.capacity_wh, self.current_energy_wh + (45.0 * (delta_time_sec / 3600.0)))
        else:
            consumed_wh = active_power_w * (delta_time_sec / 3600.0)
            self.current_energy_wh = max(0.0, self.current_energy_wh - consumed_wh)

        pct = (self.current_energy_wh / self.capacity_wh) * 100.0
        self.voltage = 20.0 + (pct / 100.0) * 5.2

    def get_battery_state(self) -> Dict[str, Any]:
        pct = (self.current_energy_wh / self.capacity_wh) * 100.0
        return {
            "battery_percentage": round(pct, 1),
            "battery_voltage": round(self.voltage, 2),
            "charging": self.charging,
            "temperature_c": round(self.temperature_c, 1),
            "health_pct": 98.0,
            "estimated_runtime_hours": round((self.current_energy_wh / 15.0), 1),
        }


class SimulatedRobotChassis(RobotController):
    def __init__(self):
        self.motors = SimulatedMotorDriver()
        self.battery = SimulatedBatteryPack()
        self.position = {"x": 0.0, "y": 0.0, "z": 0.25}
        self.heading_deg = 0.0
        self.is_active = True

    def initialize(self) -> bool:
        logger.info("Initializing Simulated Spherical Robot Chassis [ORB-7-ALPHA]...")
        return True

    def update_kinematics(self, dt: float = 0.05) -> None:
        """
        Euler integration for position and heading based on active motor velocity.
        """
        # Calculate heading change
        self.heading_deg = (self.heading_deg + math.degrees(self.motors.omega * dt)) % 360.0

        # Translate in world frame
        rad = math.radians(self.heading_deg)
        # omni motion: vx is forward, vy is strafe
        dx = (self.motors.vx * math.cos(rad) - self.motors.vy * math.sin(rad)) * dt
        dy = (self.motors.vx * math.sin(rad) + self.motors.vy * math.cos(rad)) * dt

        self.position["x"] += dx
        self.position["y"] += dy

        # Battery update
        speed = math.hypot(self.motors.vx, self.motors.vy)
        active_w = 12.0 + (speed * 18.0)
        self.battery.update_discharge(active_w, dt)

    def shutdown(self) -> None:
        self.motors.emergency_brake()
        self.is_active = False

    def get_system_telemetry(self) -> Dict[str, Any]:
        return {
            "position": self.position,
            "heading_deg": round(self.heading_deg, 1),
            "motors": self.motors.get_motor_telemetry(),
            "battery": self.battery.get_battery_state(),
            "status": "OPERATIONAL" if self.is_active else "SHUTDOWN",
        }


simulated_robot = SimulatedRobotChassis()
