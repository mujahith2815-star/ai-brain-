"""
Configuration management for the P.H.A.S.S Sphere Autonomous System.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List
import yaml
import os

DEFAULT_CONFIG_YAML = """
system:
  name: "P.H.A.S.S Sphere"
  version: "1.0.0"
  robot_id: "ORB-7-ALPHA"
  log_level: "INFO"
  offline_mode: true

safety:
  max_autonomous_steps: 100
  emergency_stop_enabled: true
  require_confirmation_for_levels:
    - "EXECUTE"
    - "SYSTEM"
  allowed_workspace_dirs:
    - "."
    - "./workspace"
    - "./data"

ai_model:
  default_engine: "offline"
  ollama_endpoint: "http://localhost:11434"
  ollama_model: "llama3"
  gemini_model: "gemini-2.5-flash"
  temperature: 0.2
  max_tokens: 2048

perception:
  lidar_enabled: true
  lidar_ray_count: 64
  lidar_max_range_m: 12.0
  camera_fps: 15
  camera_fov_deg: 120.0
  imu_frequency_hz: 50
  sensor_noise_factor: 0.02

movement:
  chassis_type: "spherical_omni"
  max_linear_speed_mps: 2.5
  max_angular_speed_radps: 4.0
  turning_radius_m: 0.0
  battery_capacity_wh: 120.0
  discharge_rate_nominal_w: 15.0

memory:
  short_term_capacity: 50
  working_memory_capacity: 20
  db_path: "data/phass_memory.db"
  similarity_threshold: 0.65

server:
  host: "127.0.0.1"
  port: 8000
  telemetry_fps: 20
"""

@dataclass
class SystemConfig:
    name: str = "P.H.A.S.S Sphere"
    version: str = "1.0.0"
    robot_id: str = "ORB-7-ALPHA"
    log_level: str = "INFO"
    offline_mode: bool = True
    base_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent)

@dataclass
class SafetyConfig:
    max_autonomous_steps: int = 100
    emergency_stop_enabled: bool = True
    require_confirmation_for_levels: List[str] = field(
        default_factory=lambda: ["EXECUTE", "SYSTEM"]
    )
    allowed_workspace_dirs: List[str] = field(
        default_factory=lambda: ["./workspace", "./data"]
    )

@dataclass
class AIModelConfig:
    default_engine: str = "offline"
    ollama_endpoint: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:1b"
    gemini_model: str = "gemini-2.5-flash"
    temperature: float = 0.1
    max_tokens: int = 2048
    num_gpu: int = 0
    max_reasoning_steps: int = 12

@dataclass
class PerceptionConfig:
    lidar_enabled: bool = True
    lidar_ray_count: int = 64
    lidar_max_range_m: float = 12.0
    camera_fps: int = 15
    camera_fov_deg: float = 120.0
    imu_frequency_hz: int = 50
    sensor_noise_factor: float = 0.02

@dataclass
class MovementConfig:
    chassis_type: str = "spherical_omni"
    max_linear_speed_mps: float = 2.5
    max_angular_speed_radps: float = 4.0
    turning_radius_m: float = 0.0
    battery_capacity_wh: float = 120.0
    discharge_rate_nominal_w: float = 15.0

@dataclass
class MemoryConfig:
    short_term_capacity: int = 50
    working_memory_capacity: int = 20
    db_path: str = "data/phass_memory.db"
    similarity_threshold: float = 0.65

@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8000
    telemetry_fps: int = 20

@dataclass
class AppConfig:
    system: SystemConfig = field(default_factory=SystemConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    ai_model: AIModelConfig = field(default_factory=AIModelConfig)
    perception: PerceptionConfig = field(default_factory=PerceptionConfig)
    movement: MovementConfig = field(default_factory=MovementConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    server: ServerConfig = field(default_factory=ServerConfig)

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> "AppConfig":
        config = cls()
        if config_path and os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                if "system" in data:
                    for k, v in data["system"].items():
                        if hasattr(config.system, k):
                            setattr(config.system, k, v)
                if "safety" in data:
                    for k, v in data["safety"].items():
                        if hasattr(config.safety, k):
                            setattr(config.safety, k, v)
                if "ai_model" in data:
                    for k, v in data["ai_model"].items():
                        if hasattr(config.ai_model, k):
                            setattr(config.ai_model, k, v)
                if "perception" in data:
                    for k, v in data["perception"].items():
                        if hasattr(config.perception, k):
                            setattr(config.perception, k, v)
                if "movement" in data:
                    for k, v in data["movement"].items():
                        if hasattr(config.movement, k):
                            setattr(config.movement, k, v)
                if "memory" in data:
                    for k, v in data["memory"].items():
                        if hasattr(config.memory, k):
                            setattr(config.memory, k, v)
                if "server" in data:
                    for k, v in data["server"].items():
                        if hasattr(config.server, k):
                            setattr(config.server, k, v)
        return config

settings = AppConfig.load()
