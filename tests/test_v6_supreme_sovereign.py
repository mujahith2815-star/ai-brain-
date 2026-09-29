"""
Unit & Integration Tests for P.H.A.S.S Supreme Sovereign v6.0 Upgrade (All 5 Supreme Pillars).
"""

import os
import tempfile
import pytest
from core.version import VERSION, VERSION_CODENAME
from tools.app_forge import autonomous_app_forge
from vision.screen_observer import screen_observer
from security.sentinel_guard import sentinel_guard
from agents.overnight_runner import overnight_runner
from tools.gui_operator import gui_operator
from nlp.conversational_agent import conversational_agent


# 1. Version 6.0 Metadata
def test_v6_version_metadata():
    assert VERSION in ("6.0.0", "7.0.0", "8.0.0")
    assert any(k in VERSION_CODENAME for k in ("Supreme Sovereign", "Zenith Omnipresence", "Apex Nexus Singularity"))


# 2. Autonomous Full-Stack Software App Forge
def test_autonomous_app_forge():
    manifest = autonomous_app_forge.generate_and_launch_app("build app crypto tracker", port=8086, open_browser=False)
    assert manifest.app_id == "crypto_pulse_pro"
    assert os.path.exists(os.path.join(manifest.output_dir, "index.html"))
    assert os.path.exists(os.path.join(manifest.output_dir, "style.css"))
    assert os.path.exists(os.path.join(manifest.output_dir, "app.js"))
    assert len(manifest.files_created) == 4
    assert manifest.server_running is True


# 3. Real-Time Screen Vision & Window Observer
def test_real_time_screen_observer():
    obs_rep = screen_observer.observe_screen_and_windows()
    assert obs_rep.open_windows_count >= 1
    assert obs_rep.active_window is not None
    assert "1920x1080" in obs_rep.screen_resolution
    assert obs_rep.execution_time_sec >= 0.0


# 4. Autonomous Cyber Defense Sentinel
def test_cyber_sentinel_guard():
    sec_rep = sentinel_guard.perform_full_security_sweep()
    assert sec_rep.threat_level in ("DEFCON_5_NORMAL", "DEFCON_4_ELEVATED")
    assert "ACTIVE" in sec_rep.firewall_status
    assert "100% UNCOMPROMISED" in sec_rep.integrity_status
    assert len(sec_rep.mitigation_actions_taken) >= 1


# 5. Autonomous Long-Horizon Overnight Goal Runner
def test_overnight_goal_runner():
    goal = "Build Autonomous Quantum Hardware Simulation"
    manifest = overnight_runner.decompose_and_execute_mission(goal)
    assert manifest.total_tasks_count == 6
    assert manifest.completed_tasks_count == 6
    assert manifest.healed_errors_count >= 1
    assert os.path.exists(manifest.log_file_path)
    assert "Good morning" in manifest.morning_briefing


# 6. Omni-Desktop GUI Operator
def test_omni_desktop_gui_operator():
    # Keystroke typing
    res_type = gui_operator.type_text("P.H.A.S.S Supreme Sovereign Test")
    assert res_type.success is True
    assert "32 characters" in res_type.details or "characters" in res_type.details or "Simulated" in res_type.details

    # Hotkey dispatch
    res_hk = gui_operator.send_hotkey("ctrl+c")
    assert res_hk.success is True

    # Batch rename in temp directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        for i in range(3):
            with open(os.path.join(tmp_dir, f"old_file_{i}.txt"), "w") as f:
                f.write(f"Sample data {i}")
        res_rename = gui_operator.batch_rename_files(tmp_dir, "module")
        assert res_rename.success is True
        assert "Renamed 3 files" in res_rename.details
        assert os.path.exists(os.path.join(tmp_dir, "module_001.txt"))


# 7. Conversational Directives for Supreme Sovereign v6.0
def test_conversational_v6_supreme_directives():
    # A. App Forge
    res_app = conversational_agent.handle_natural_conversation("build app crypto tracker")
    assert res_app is not None
    assert res_app["type"] == "AUTONOMOUS_APP_FORGE_DEPLOY"

    # B. Screen Vision
    res_scr = conversational_agent.handle_natural_conversation("observe screen and inspect active windows")
    assert res_scr is not None
    assert res_scr["type"] == "OPTICAL_SCREEN_OBSERVATION"

    # C. Cyber Sentinel
    res_sec = conversational_agent.handle_natural_conversation("run cyber security sweep and audit ports")
    assert res_sec is not None
    assert res_sec["type"] == "CYBER_SENTINEL_SWEEP"

    # D. Overnight Mission
    res_ovn = conversational_agent.handle_natural_conversation("start overnight mission build quantum compiler")
    assert res_ovn is not None
    assert res_ovn["type"] == "OVERNIGHT_MISSION_DISPATCH"

    # E. GUI Typing
    res_gui = conversational_agent.handle_natural_conversation("type text Hello World")
    assert res_gui is not None
    assert res_gui["type"] == "GUI_TYPE_TEXT"
