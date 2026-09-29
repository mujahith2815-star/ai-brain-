"""
Tests for Smart Home & IoT Hub and Tool Registry bindings.
"""

import pytest
from tools.smart_home import (
    smart_home_hub,
    smart_home_discover_devices,
    smart_home_get_state,
    smart_home_set_state,
    smart_home_toggle,
    smart_home_set_temperature,
    smart_home_set_light_brightness,
    smart_home_execute_scene,
)
from tools.registry import tool_registry


def test_discover_devices():
    devs = smart_home_discover_devices()
    assert len(devs) >= 5
    ids = [d["entity_id"] for d in devs]
    assert "light.living_room" in ids
    assert "climate.main_thermostat" in ids

    # Filtered
    lights = smart_home_discover_devices(filter_type="light")
    assert all(d["type"] == "light" for d in lights)


def test_get_and_set_device_state():
    res = smart_home_get_state("light.living_room")
    assert res["status"] == "SUCCESS"
    assert "device" in res

    set_res = smart_home_set_state("light.living_room", "off")
    assert set_res["status"] == "SUCCESS"
    assert set_res["new_state"] == "off"

    # Verify updated
    res2 = smart_home_get_state("light.living_room")
    assert res2["device"]["state"] == "off"


def test_toggle_device():
    # Turn on then toggle
    smart_home_set_state("switch.coffee_maker", "off")
    tog_res = smart_home_toggle("switch.coffee_maker")
    assert tog_res["status"] == "SUCCESS"
    assert tog_res["state"] == "on"

    tog_res2 = smart_home_toggle("switch.coffee_maker")
    assert tog_res2["state"] == "off"


def test_thermostat_temperature_control():
    res = smart_home_set_temperature("climate.main_thermostat", 23.5)
    assert res["status"] == "SUCCESS"
    assert res["target_temperature"] == 23.5

    st = smart_home_get_state("climate.main_thermostat")
    assert st["device"]["attributes"]["target_temperature"] == 23.5


def test_light_brightness_control():
    res = smart_home_set_light_brightness("light.desk", 45)
    assert res["status"] == "SUCCESS"
    assert res["brightness"] == 45
    assert res["state"] == "on"

    # Dim to 0 shuts it off
    res_zero = smart_home_set_light_brightness("light.desk", 0)
    assert res_zero["state"] == "off"


def test_smart_home_scenes():
    scene_res = smart_home_execute_scene("movie_night")
    assert scene_res["status"] == "SUCCESS"
    assert len(scene_res["actions"]) >= 1

    tv_st = smart_home_get_state("media_player.living_room_tv")
    assert tv_st["device"]["state"] == "on"


def test_tool_registry_smart_home_execution():
    tools = tool_registry.list_tools()
    tool_names = [t["name"] for t in tools]
    assert "smart_home_discover_devices" in tool_names
    assert "smart_home_toggle" in tool_names

    # Test execution through registry
    exec_res = tool_registry.execute("smart_home_toggle", entity_id="switch.workstation")
    assert exec_res["status"] == "SUCCESS"
