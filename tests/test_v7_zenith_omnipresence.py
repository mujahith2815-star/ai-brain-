"""
Unit & Integration Tests for P.H.A.S.S Zenith Omnipresence v7.0 Upgrade (All 5 Frontier Pillars).
"""

import os
import tempfile
import pytest
from core.version import VERSION, VERSION_CODENAME
from ui.holographic_web_hud import holographic_web_hud
from mesh.mobile_device_bridge import mobile_device_bridge
from voice.hotword_listener import hotword_listener
from tools.repo_auto_architect import repo_auto_architect
from security.quantum_vault import quantum_vault
from nlp.conversational_agent import conversational_agent


# 1. Version 7.0 Metadata
def test_v7_version_metadata():
    assert VERSION in ("7.0.0", "8.0.0")
    assert any(k in VERSION_CODENAME for k in ("Zenith Omnipresence", "Apex Nexus Singularity"))


# 2. 3D WebGL Holographic Web HUD Server
def test_holographic_web_hud():
    manifest = holographic_web_hud.launch_holographic_web_hud(port=8091, open_browser=False)
    assert manifest.server_port == 8091
    assert manifest.is_active is True
    assert "8091" in manifest.local_url
    assert os.path.exists(os.path.join(holographic_web_hud.hud_dir, "index.html"))
    assert os.path.exists(os.path.join(holographic_web_hud.hud_dir, "hud.css"))
    assert os.path.exists(os.path.join(holographic_web_hud.hud_dir, "hud.js"))


# 3. Autonomous Mobile Device Mesh Bridge
def test_mobile_device_bridge():
    # Pair device
    dev = mobile_device_bridge.pair_device("Operator iPhone 16 Pro", device_type="SMARTPHONE_IOS", ip="192.168.1.188")
    assert dev.device_name == "Operator iPhone 16 Pro"
    assert dev.is_connected is True

    # Send push notification
    notif = mobile_device_bridge.send_push_notification("Mission Milestone", "Architecture optimization complete.")
    assert notif.delivered is True
    assert notif.title == "Mission Milestone"

    # Execute remote command
    rem_res = mobile_device_bridge.execute_remote_command("what time is it")
    assert rem_res["success"] is True


# 4. Hands-Free Zero-Latency Hotword Listener
def test_hands_free_hotword_listener():
    hotword_listener.start_listener()
    assert hotword_listener.is_listening is True

    # Test wakeword event
    wake_event = hotword_listener.trigger_wakeword("Hey P.H.A.S.S what is system status")
    assert wake_event.wakeword_detected == "hey phass"
    assert wake_event.confidence_score > 0.9
    assert wake_event.latency_ms > 0.0

    hotword_listener.stop_listener()
    assert hotword_listener.is_listening is False


# 5. Autonomous Codebase Auto-Architect
def test_repo_auto_architect():
    # Analyze current project
    rep = repo_auto_architect.analyze_codebase_architecture(os.getcwd())
    assert rep.total_python_files >= 10
    assert rep.total_lines_of_code > 500
    assert rep.total_functions > 20
    assert rep.average_complexity >= 1.0

    # Synthesize unit test
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write("def calculate_energy(mass, c):\n    return mass * (c ** 2)\nclass ReactorCore:\n    pass\n")
        src_path = f.name

    try:
        test_skeleton = repo_auto_architect.synthesize_unit_test_skeleton(src_path)
        assert "def test_calculate_energy_execution():" in test_skeleton
        assert "def test_reactorcore_initialization():" in test_skeleton
    finally:
        if os.path.exists(src_path):
            os.remove(src_path)


# 6. Cryptographic Zero-Trust Secret Vault
def test_cryptographic_quantum_vault():
    master_key = "TOP_SECRET_MASTER_PASSPHRASE_123"
    token_val = "sk_live_quantum_secure_agent_token_999"

    # Store
    ok = quantum_vault.store_secret("TEST_GEMINI_KEY", token_val, master_passphrase=master_key)
    assert ok is True

    # Retrieve
    decrypted = quantum_vault.retrieve_secret("TEST_GEMINI_KEY", master_passphrase=master_key)
    assert decrypted == token_val

    # Test wrong passphrase rejection
    with pytest.raises(PermissionError):
        quantum_vault.retrieve_secret("TEST_GEMINI_KEY", master_passphrase="WRONG_PASSPHRASE")

    # List keys
    keys = quantum_vault.list_secret_keys()
    assert any(k.key_name == "TEST_GEMINI_KEY" for k in keys)


# 7. Conversational Directives for Zenith v7.0
def test_conversational_v7_zenith_directives():
    # A. 3D Web HUD
    res_hud = conversational_agent.handle_natural_conversation("launch 3d holographic hud")
    assert res_hud is not None
    assert res_hud["type"] == "HOLOGRAPHIC_3D_WEB_HUD_LAUNCH"

    # B. Mobile Mesh
    res_mob = conversational_agent.handle_natural_conversation("mobile mesh status")
    assert res_mob is not None
    assert res_mob["type"] == "MOBILE_MESH_TELEMETRY"

    # C. Wakeword Status
    res_wake = conversational_agent.handle_natural_conversation("hotword status")
    assert res_wake is not None
    assert res_wake["type"] == "HOTWORD_LISTENER_STATUS"

    # D. Codebase Architecture
    res_arch = conversational_agent.handle_natural_conversation("analyze codebase architecture")
    assert res_arch is not None
    assert res_arch["type"] == "CODEBASE_ARCHITECTURE_AUDIT"

    # E. Secret Vault
    res_sec = conversational_agent.handle_natural_conversation("quantum vault status")
    assert res_sec is not None
    assert res_sec["type"] == "SECRET_VAULT_STATUS"
