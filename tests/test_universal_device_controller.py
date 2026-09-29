"""
Unit & Integration Tests for Universal Multi-Device Ecosystem Controller (PC, Laptop, Smart TV, Smartphone, Smartwatch).
"""

import pytest
from mesh.universal_device_controller import (
    universal_device_controller,
    DeviceCategory,
    EcosystemDevice,
)
from nlp.conversational_agent import conversational_agent


# 1. Ecosystem Device Initialization
def test_ecosystem_initialization():
    assert len(universal_device_controller.devices) >= 5
    categories = [d.category for d in universal_device_controller.devices.values()]
    assert DeviceCategory.PC_WORKSTATION in categories
    assert DeviceCategory.REMOTE_LAPTOP in categories
    assert DeviceCategory.SMART_TV in categories
    assert DeviceCategory.SMARTPHONE in categories
    assert DeviceCategory.SMARTWATCH in categories


# 2. Smart TV Control
def test_smart_tv_control():
    # Launch App
    res_app = universal_device_controller.control_smart_tv("launch YouTube", app_name="YouTube 4K")
    assert res_app.success is True
    assert "YouTube" in res_app.details

    # Power Standby
    res_off = universal_device_controller.control_smart_tv("turn off TV")
    assert res_off.success is True
    assert "Standby" in res_off.details


# 3. Remote Laptop Control
def test_laptop_control():
    res_lock = universal_device_controller.control_laptop("lock laptop")
    assert res_lock.success is True
    assert "lock" in res_lock.details.lower()

    res_boost = universal_device_controller.control_laptop("boost laptop speed")
    assert res_boost.success is True
    assert "power plan" in res_boost.details.lower()


# 4. Smartphone Control
def test_smartphone_control():
    # Camera
    res_cam = universal_device_controller.control_smartphone("open camera on phone")
    assert res_cam.success is True
    assert "Camera" in res_cam.details

    # Battery
    res_bat = universal_device_controller.control_smartphone("battery status")
    assert res_bat.success is True
    assert "Battery" in res_bat.details


# 5. Smartwatch Alert
def test_smartwatch_control():
    res_alert = universal_device_controller.send_smartwatch_alert("Emergency Priority Briefing", vibrate=True)
    assert res_alert.success is True
    assert "Bluetooth Low Energy" in res_alert.details
    assert "Emergency Priority Briefing" in res_alert.details


# 6. Broadcast Ecosystem Command
def test_broadcast_ecosystem_command():
    results = universal_device_controller.broadcast_ecosystem_command("system audit")
    assert len(results) >= 4
    assert all(r.success for r in results)


# 7. Conversational Ecosystem Directives
def test_conversational_ecosystem_directives():
    # TV
    res_tv = conversational_agent.handle_natural_conversation("launch youtube on tv")
    assert res_tv is not None
    assert res_tv["type"] == "ECOSYSTEM_SMART_TV_CONTROL"

    # Laptop
    res_lap = conversational_agent.handle_natural_conversation("lock laptop")
    assert res_lap is not None
    assert res_lap["type"] == "ECOSYSTEM_LAPTOP_CONTROL"

    # Smartphone
    res_ph = conversational_agent.handle_natural_conversation("open camera on phone")
    assert res_ph is not None
    assert res_ph["type"] == "ECOSYSTEM_SMARTPHONE_CONTROL"

    # Smartwatch
    res_w = conversational_agent.handle_natural_conversation("send alert to smartwatch High Priority Task")
    assert res_w is not None
    assert res_w["type"] == "ECOSYSTEM_SMARTWATCH_CONTROL"

    # Master Ecosystem Status
    res_eco = conversational_agent.handle_natural_conversation("list all ecosystem devices")
    assert res_eco is not None
    assert res_eco["type"] == "ECOSYSTEM_MASTER_TELEMETRY"
