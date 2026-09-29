"""
Hardware Abstraction Layer (HAL) for P.H.A.S.S Sphere.
Defines clean interfaces for controllers, motors, sensors, cameras, and power subsystems,
ensuring the cognitive core remains decoupled from specific hardware platforms (ESP32, Jetson, Pi).
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class MotorInterface(ABC):
    @abstractmethod
    def set_omni_velocity(self, vx_mps: float, vy_mps: float, omega_radps: float) -> bool:
        """Sets linear velocity in X/Y plane and angular yaw velocity for spherical omni chassis."""
        pass

    @abstractmethod
    def get_motor_telemetry(self) -> Dict[str, Any]:
        """Returns motor RPM, current draw, and temperature."""
        pass

    @abstractmethod
    def emergency_brake(self) -> None:
        pass


class SensorInterface(ABC):
    @abstractmethod
    def read_imu(self) -> Dict[str, Any]:
        """Reads 6-DOF IMU (accelerometer + gyroscope)."""
        pass

    @abstractmethod
    def read_lidar_ranges(self) -> List[float]:
        """Reads 360-degree LiDAR distance ranges in meters."""
        pass

    @abstractmethod
    def read_ultrasonic(self) -> float:
        """Reads front ultrasonic distance in meters."""
        pass


class CameraInterface(ABC):
    @abstractmethod
    def capture_frame_metadata(self) -> Dict[str, Any]:
        pass


class AudioInterface(ABC):
    @abstractmethod
    def play_audio_tone(self, frequency_hz: int, duration_sec: float) -> None:
        pass

    @abstractmethod
    def synthesize_speech(self, text: str) -> None:
        pass


class BatteryInterface(ABC):
    @abstractmethod
    def get_battery_state(self) -> Dict[str, Any]:
        """Returns battery percentage, voltage, cell health, and charging status."""
        pass


class RobotController(ABC):
    @abstractmethod
    def initialize(self) -> bool:
        pass

    @abstractmethod
    def shutdown(self) -> None:
        pass

    @abstractmethod
    def get_system_telemetry(self) -> Dict[str, Any]:
        pass
