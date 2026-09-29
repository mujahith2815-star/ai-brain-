"""
Unit & Integration Tests for Real-Time Cyber Intrusion Shield & Threat Warning Box Overlay.
"""

import os
import pytest
from security.intrusion_shield import intrusion_shield, ThreatSeverity, ThreatEvent
from ui.threat_warning_overlay import threat_warning_overlay, ThreatAlertData
from nlp.conversational_agent import conversational_agent


# 1. Threat Detection & Automated Neutralization
def test_threat_detection_and_neutralization():
    event = intrusion_shield.detect_and_neutralize_threat(
        threat_type="Stealth SYN Port Scanning",
        source_origin="198.51.100.99",
        target_asset="Port 8080",
        severity=ThreatSeverity.DEFCON_2_HIGH,
        popup_overlay=False,
    )
    assert event.is_neutralized is True
    assert "Blacklisted" in event.mitigation_action
    assert len(event.incident_hash) == 64
    assert event.severity == ThreatSeverity.DEFCON_2_HIGH


# 2. Ransomware Canary Threat Neutralization
def test_ransomware_canary_neutralization():
    event = intrusion_shield.detect_and_neutralize_threat(
        threat_type="Ransomware Canary Modification Probe",
        source_origin="192.168.1.200",
        target_asset="Canary Vault",
        severity=ThreatSeverity.DEFCON_1_CRITICAL,
        popup_overlay=False,
    )
    assert event.is_neutralized is True
    assert "Locked target directory" in event.mitigation_action
    assert event.severity == ThreatSeverity.DEFCON_1_CRITICAL


# 3. Warning Box Overlay Formatting
def test_warning_overlay_formatting():
    alert = ThreatAlertData(
        event_id="ATK_TEST_01",
        threat_type="Unauthorized Process Injection",
        severity="DEFCON 2 - HIGH",
        source_origin="PID 8812",
        target_asset="Virtual Address Space",
        mitigation_action="Terminated PID & Sanitized Address Space",
    )
    box_ascii = threat_warning_overlay.format_threat_box_ascii(alert)
    assert "P.H.A.S.S CYBER SHIELD WARNING" in box_ascii
    assert "ATK_TEST_01" in box_ascii
    assert "100% CONTAINED & NEUTRALIZED" in box_ascii

    # Test display method non-blocking
    ok = threat_warning_overlay.display_warning_box(alert, auto_close_sec=1)
    assert ok is True


# 4. Live Cyber Attack Drill Simulation
def test_simulate_cyber_attack_drill():
    event = intrusion_shield.simulate_cyber_attack("SYN_FLOOD_PORT_SCAN")
    assert event.is_neutralized is True
    assert "Port 8085" in event.target_process_or_port
    assert len(intrusion_shield.neutralized_threats_history) >= 1


# 5. Conversational Directives for Cyber Shield
def test_conversational_cyber_attack_directives():
    # A. Simulate attack
    res_atk = conversational_agent.handle_natural_conversation("simulate cyber attack")
    assert res_atk is not None
    assert res_atk["type"] == "CYBER_ATTACK_SIMULATION_NEUTRALIZED"
    assert "intercepted and neutralized" in res_atk["speech_text"]

    # B. Shield status
    res_stat = conversational_agent.handle_natural_conversation("intrusion shield status")
    assert res_stat is not None
    assert res_stat["type"] == "INTRUSION_SHIELD_TELEMETRY"
    assert "ARMED & ENFORCED" in res_stat["speech_text"]
