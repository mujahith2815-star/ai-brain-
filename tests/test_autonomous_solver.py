"""
Unit & Integration Tests for Fully Autonomous End-to-End Problem Solver & Universal Device Control.
"""

import pytest
from knowledge.live_search import live_search_engine
from tools.dynamic_executor import dynamic_executor
from tools.device_controller import device_controller
from nlp.conversational_agent import conversational_agent


# 1. Live Knowledge Retrieval & Synthesis
def test_live_knowledge_search_parliament():
    res = live_search_engine.answer_query("yesterday what is the problem in parliament of india")
    assert res.confidence > 0.9
    assert "parliament of india" in res.headline_answer.lower() or "disruptions" in res.headline_answer.lower()
    assert len(res.key_bullet_points) >= 3
    assert len(res.sources_consulted) >= 1

    spoken = live_search_engine.format_spoken_summary(res)
    assert "Key Insights" in spoken


# 2. Instant Dynamic Code Generation & UI Effect (MUJA)
def test_dynamic_code_generator_muja():
    ok, msg = dynamic_executor.generate_and_launch_name_ui_effect("MUJA")
    assert ok is True
    assert "MUJA" in msg
    assert dynamic_executor.executed_effects_count >= 1


# 3. Universal Device & Phone Power-On Control
def test_device_controller_phone_power_on():
    report = device_controller.execute_turn_on_phone_protocol()
    assert report.final_status == "EXECUTED_MULTI_AVENUE"
    assert len(report.avenues_attempted) >= 3
    assert "phone" in report.spoken_summary.lower()

    # Verify channels attempted
    channels = [a["channel"] for a in report.avenues_attempted]
    assert "ADB_USB_AND_TCP" in channels
    assert "WAKE_ON_LAN_BROADCAST" in channels
    assert "BLUETOOTH_BLE_AND_USB_VBUS" in channels


# 4. Zero-Friction Autonomous Directive Routing
def test_zero_friction_autonomous_routing():
    # A. Current affairs question
    res_k = conversational_agent.handle_natural_conversation("yesterday what is the problem in parliament of india")
    assert res_k is not None
    assert res_k["type"] == "LIVE_KNOWLEDGE_SEARCH"
    assert res_k["action_executed"] == "LIVE_WEB_SEARCH"

    # B. Creative Dynamic UI generation
    res_ui = conversational_agent.handle_natural_conversation("create a ui effect of displaying name muja")
    assert res_ui is not None
    assert res_ui["type"] == "DYNAMIC_CODE_EXECUTION"
    assert "MUJA" in res_ui["action_executed"]

    # C. Strict Device Power-On order
    res_dev = conversational_agent.handle_natural_conversation("my phone was off on the phone")
    assert res_dev is not None
    assert res_dev["type"] == "HARDWARE_DEVICE_CONTROL"
    assert res_dev["action_executed"] == "STRICT_PHONE_POWER_ON"
