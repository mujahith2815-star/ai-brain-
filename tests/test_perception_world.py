"""
Unit tests for Perception and World Model systems.
"""

import pytest
from perception.sensors import SensorHub
from perception.vision import VisionProcessor
from perception.observation import ObservationType
from world.world_model import WorldModel
from world.entities import WorldEntity, EntityType, Vector3D


def test_sensor_hub_lidar_generation():
    hub = SensorHub(lidar_ray_count=32, max_range_m=10.0)
    scan = hub.generate_lidar_scan({"x": 0.0, "y": 0.0, "z": 0.25})

    assert scan.type == ObservationType.LIDAR_SCAN
    assert len(scan.data["ranges_m"]) == 32
    assert scan.data["min_clearance_m"] > 0.0


@pytest.mark.asyncio
async def test_vision_processor():
    vision = VisionProcessor()
    obs = await vision.capture_frame_analysis()

    assert obs.type == ObservationType.OBJECT_DETECTION
    assert "detected_objects" in obs.data
    assert len(obs.data["detected_objects"]) > 0


@pytest.mark.asyncio
async def test_world_model_ingestion():
    wm = WorldModel()

    # Ingest entity
    custom_ent = WorldEntity(
        id="ENT-CUSTOM-1",
        name="Telemetry Tower",
        entity_type=EntityType.DEVICE,
        position=Vector3D(1.5, -2.0, 0.0),
    )
    wm.add_or_update_entity(custom_ent)

    assert wm.get_entity("ENT-CUSTOM-1") is not None

    # Ingest observation
    await wm.ingest_observation({
        "type": "TELEMETRY",
        "data": {"battery_percentage": 75.0, "internal_temp_c": 36.5},
    })

    assert wm.robot_state.battery_percentage == 75.0
    assert wm.robot_state.internal_temp_c == 36.5

    snapshot = wm.get_snapshot()
    assert len(snapshot["entities"]) >= 3
