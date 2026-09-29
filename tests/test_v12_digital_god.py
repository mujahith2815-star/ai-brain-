"""
P.H.A.S.S v12.0 "Digital God" Comprehensive Test Suite.
Validates:
1. 'import re' System-Wide Fix (web_search, reminders, context resolution)
2. Predictive Intelligence Engine (The Oracle: project forecasting & resource spikes)
3. Deep System Integration & Kernel Bridge (WMI/Registry/udev, selective syscall firewall & driver loader)
4. Autonomous Agent Swarm (The Collective: parallel specialists & reviewer audit)
5. Stateful Reflective Memory (The Hippocampus: Knowledge Graph triples, SRDP reflection & recall)
6. Always-On Autopilot (Scout Mode: unprompted hotplug, disk maintenance, follow-through staging)
"""

import os
import sys
import time
from pathlib import Path
import pytest

# Ensure environment
os.environ["TCL_LIBRARY"] = os.path.join(sys.base_prefix, "tcl", "tcl8.6")
os.environ["TK_LIBRARY"] = os.path.join(sys.base_prefix, "tcl", "tk8.6")


def test_re_module_fix():
    """
    Verifies that 'import re' is present and active across all tools,
    eliminating NameError: name 're' is not defined in web_search, reminders, and context resolution.
    """
    # 1. web_search execution without re errors
    from tools.builtin_tools import web_search
    import asyncio
    res = asyncio.run(web_search("What is Arduino Uno?"))
    assert res["status"] == "SUCCESS"
    assert "query" in res

    # 2. Context resolution with pronoun regex
    from core.lifelong_context import lifelong_context
    resolved = lifelong_context.resolve_pronouns("What is the pinout of it?")
    assert any(c in resolved for c in ["BC547", "ESP32", "2N2222"])

    # 3. Reminders check
    from core.proactive_engine import proactive_engine
    rem = proactive_engine.add_reminder("Sync telemetry logs", due_time=time.time() + 3600)
    assert rem["status"] == "SUCCESS"


def test_predictive_intelligence_oracle():
    """
    Verifies The Oracle:
    - Project context detection (predicts PlatformIO toolchain & port)
    - RAM spike anomaly prediction with high confidence
    - User decision flow (approval & dismissal)
    """
    from core.predictive_intelligence import predictive_engine

    # 1. Project Context Prediction
    pred = predictive_engine.predict_project_context("projects/ESP32_Smart_Gateway")
    assert pred is not None
    assert "ESP32" in pred["title"]
    assert pred["confidence"] >= 0.90
    assert pred["status"] == "PENDING"
    assert "PlatformIO" in pred["description"]

    # 2. RAM Anomaly Prediction
    ram_pred = predictive_engine.predict_resource_anomaly(ram_percent=88.5, delta_rate=12.0)
    assert ram_pred is not None
    assert ram_pred["confidence"] >= 0.90
    assert "RAM" in ram_pred["title"]

    # 3. Approve Action Flow
    appr = predictive_engine.approve_prediction(pred["id"])
    assert appr["status"] == "SUCCESS"
    assert appr["decision"] == "APPROVED"

    # 4. Dismiss Action Flow
    dism = predictive_engine.dismiss_prediction(ram_pred["id"])
    assert dism["status"] == "SUCCESS"
    assert dism["decision"] == "DISMISSED"


def test_deep_system_kernel_bridge():
    """
    Verifies Deep System Integration:
    - Kernel-level OS state introspection (Windows WMI/Registry or Linux)
    - Selective system call firewall (allows benign, blocks hazardous)
    - Dynamic driver synthesis & staging
    """
    from core.system_kernel_bridge import system_kernel_bridge
    from core.dynamic_driver_loader import dynamic_driver_loader

    # 1. OS Introspection
    state = system_kernel_bridge.get_deep_system_state()
    assert "platform" in state
    assert "subsystems" in state

    # 2. Selective System Call Firewall: Safe call
    safe_call = system_kernel_bridge.intercept_system_call("exec", "python server.py")
    assert safe_call["decision"] == "ALLOW"

    # 3. Selective System Call Firewall: Malicious command blocked
    hazard_call = system_kernel_bridge.intercept_system_call("exec", "rm -rf /")
    assert hazard_call["decision"] == "BLOCK"
    assert "Security Violation" in hazard_call["reason"]

    # 4. Dynamic Driver Synthesizer
    drv = dynamic_driver_loader.generate_driver("BMP280 Barometer", bus_type="I2C", baud=9600)
    assert drv["status"] == "SUCCESS"
    assert Path(drv["source_path"]).exists()
    assert Path(drv["source_path"]).stat().st_size > 50


def test_autonomous_agent_swarm():
    """
    Verifies Autonomous Agent Swarm (The Collective):
    - Decomposes high-level goal into parallel domain tasks
    - Executes specialists in parallel (UI, Frontend, Backend, Hardware, QA)
    - Independent Reviewer Agent audits and approves deliverable
    """
    from core.agent_swarm import agent_swarm

    goal = "Build me a full-stack web app to manage my inventory"
    result = agent_swarm.execute_swarm_goal(goal, project_name="InventorySwarmApp")

    assert result["status"] == "SUCCESS"
    assert result["total_agents_spawned"] >= 5
    assert len(result["specialist_outputs"]) >= 4

    # Check Reviewer Agent Approval
    review = result["review"]
    assert review["approved"] is True
    assert review["audit_score"] >= 90
    assert len(review["verified_files"]) >= 4

    # Verify generated project files on disk
    pdir = Path(result["project_dir"])
    assert (pdir / "index.html").exists()
    assert (pdir / "server.py").exists()
    assert (pdir / "test_inventory.py").exists()


def test_stateful_reflective_memory():
    """
    Verifies Stateful Reflective Memory (The Hippocampus):
    - Semantic Knowledge Graph triple storage and queries
    - Episodic logging
    - SRDP Reflection Cycle (extracting rules from failed operations)
    - Context-free recall
    """
    from core.reflective_learner import reflective_learner

    # 1. Knowledge Graph Queries
    graph = reflective_learner.graph
    graph.add_triple("ESP32_Gateway", "uses_sensor", "BME280")
    matches = graph.query("ESP32_Gateway")
    assert len(matches) >= 1
    assert matches[0]["object"] == "BME280"

    # 2. Episodic Failure Logging & SRDP Rule Extraction
    reflective_learner.log_episode(
        event_type="flash_attempt",
        user_input="Flash ESP32 on COM3",
        system_response="Failed: port COM3 is locked by another process",
        success=False,
        error_details="device port COM3 timeout and locked",
    )

    refl = reflective_learner.run_reflection_cycle()
    assert refl["status"] == "SUCCESS"
    # Rule should be synthesized
    assert any("COM3" in r["rule"] for r in reflective_learner.learned_rules)

    # 3. Context-Free Recall
    recall = reflective_learner.context_free_recall("Tell me about Solo Leveling")
    assert recall is not None
    assert "Sung Jin-Woo" in recall


def test_always_on_autopilot_scout():
    """
    Verifies Always-On Autopilot (Scout Mode):
    - Unprompted hardware hotplug detection & notification
    - Proactive disk maintenance (<15% threshold)
    - Intelligent follow-through promise staging
    """
    from core.always_on_autopilot import always_on_autopilot

    # 1. Unprompted Hardware Detection
    notif_hw = always_on_autopilot.handle_unprompted_hardware(port="COM4", board="ESP32")
    assert notif_hw["category"] == "hardware_hotplug"
    assert "New device detected on COM4 (ESP32)" in notif_hw["message"]

    # 2. Proactive Maintenance (< 15% disk space)
    notif_maint = always_on_autopilot.check_and_perform_maintenance(forced_free_pct=12.0)
    assert notif_maint is not None
    assert notif_maint["category"] == "maintenance"
    assert "freed" in notif_maint["message"].lower()

    # 3. Intelligent Follow-Through Promise Staging
    promise_msg = "I'll send you the report by 5 PM"
    notif_follow = always_on_autopilot.inspect_and_follow_through(promise_msg)
    assert notif_follow is not None
    assert notif_follow["category"] == "follow_through"
    staged_path = Path(notif_follow["payload"]["staged_file"])
    assert staged_path.exists()
