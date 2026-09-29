"""
Unit & Integration Tests for Live Real-Time Hardware & Environmental Telemetry Hub.
Verifies genuine extraction of Windows battery %, AC charger power lines, real CPU/RAM/Disk, local clock, and network metrics.
"""

import pytest
from sensors.live_hardware_hub import live_hardware_hub, LiveBatteryChargerTelemetry, LiveSystemHardwareTelemetry
from world.world_model import world_model
from diagnostics.deep_diagnostics import deep_diagnostics
from nlp.conversational_agent import conversational_agent


# 1. Live Windows Battery & AC Charger Telemetry
def test_live_battery_and_charger():
    bat = live_hardware_hub.get_live_battery_and_charger()

    assert isinstance(bat, LiveBatteryChargerTelemetry)
    assert 0.0 <= bat.battery_percentage <= 100.0
    assert isinstance(bat.is_charging, bool)
    assert isinstance(bat.is_ac_line_connected, bool)
    assert len(bat.status_summary) > 5


# 2. Live System Clock & Precision Uptime
def test_live_system_clock_and_uptime():
    telemetry = live_hardware_hub.get_all_live_telemetry()

    assert isinstance(telemetry, LiveSystemHardwareTelemetry)
    assert len(telemetry.local_time_formatted) > 10
    assert len(telemetry.timezone_name) >= 2
    assert telemetry.system_uptime_seconds >= 0.0
    assert telemetry.cpu_core_count >= 1


# 3. Live RAM Memory & Disk Hardware
def test_live_memory_and_disk_hardware():
    tot_ram, used_ram, free_ram, ram_load = live_hardware_hub.get_live_memory()
    assert tot_ram > 0.5 # At least 512MB
    assert free_ram >= 0.0
    assert 0.0 <= ram_load <= 100.0

    tot_disk, used_disk, free_disk = live_hardware_hub.get_live_disk_space()
    assert tot_disk > 1.0 # At least 1GB
    assert free_disk > 0.0


# 4. Live Network Gateway Handshake
def test_live_network_gateway_ping():
    ping_ms = live_hardware_hub.measure_network_gateway_ping_ms()
    assert ping_ms > 0.0


# 5. Live Telemetry HUD Formatting
def test_live_telemetry_hud_format():
    hud_text = live_hardware_hub.format_telemetry_hud_text()
    assert "LIVE REAL-TIME HARDWARE" in hud_text
    assert "Local System Clock:" in hud_text
    assert "Battery & Charger:" in hud_text
    assert "CPU Processors:" in hud_text
    assert "Memory Working Set:" in hud_text


# 6. World Model & Deep Diagnostics Live Hardware Binding
def test_world_model_and_diagnostics_live_binding():
    # World model snapshot should sync live hardware
    snap = world_model.get_snapshot()
    assert "robot_state" in snap
    assert 0.0 <= snap["robot_state"]["battery_percentage"] <= 100.0

    # Deep diagnostics should use live CPU/RAM
    diag = deep_diagnostics.run_full_diagnosis()
    assert diag.cpu_metrics["logical_cores"] >= 1
    assert "ram_total_gb" in diag.memory_metrics


# 7. Conversational Directives for Clock, Charger & Hardware
def test_conversational_clock_and_battery_directives():
    # A. Clock Query
    res_clock = conversational_agent.handle_natural_conversation("what time is it")
    assert res_clock is not None
    assert res_clock["type"] == "CLOCK_QUERY"
    assert "Current local time is" in res_clock["speech_text"]

    # B. Battery & Charger Query
    res_bat = conversational_agent.handle_natural_conversation("is charger plugged in and what is battery status")
    assert res_bat is not None
    assert res_bat["type"] == "BATTERY_CHARGER_QUERY"
    assert "Live Power Telemetry" in res_bat["speech_text"]

    # C. Hardware Stats Query
    res_hw = conversational_agent.handle_natural_conversation("show hardware stats and processor load")
    assert res_hw is not None
    assert res_hw["type"] == "HARDWARE_TELEMETRY_QUERY"
    assert "LIVE REAL-TIME HARDWARE" in res_hw["speech_text"]
