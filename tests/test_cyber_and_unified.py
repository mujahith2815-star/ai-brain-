"""
Unit & Integration Tests for Cybersecurity Defense Suite & Grand Unified Architecture.
"""

import pytest
from security.cyber_defense import cyber_defense
from core.unified_orchestrator import unified_orchestrator
from nlp.conversational_agent import conversational_agent


# 1. Cyber Defense Port Scanner & Audit
def test_cyber_defense_scan_and_audit():
    # Scan target ports on localhost
    ports = cyber_defense.scan_target_ports("127.0.0.1", timeout_sec=0.1)
    assert isinstance(ports, list)

    # Full security audit
    report = cyber_defense.run_full_security_audit("127.0.0.1")
    assert report.total_ports_scanned >= 10
    assert 20 <= report.system_security_score <= 100
    assert len(report.hardening_actions) >= 3

    txt = cyber_defense.format_audit_report_text(report)
    assert "DEFENSE AUDIT REPORT" in txt


# 2. Password Entropy & Cryptographic Evaluator
def test_password_entropy_evaluator():
    res_weak = cyber_defense.evaluate_password_entropy("123456")
    assert res_weak["is_secure"] is False
    assert res_weak["entropy_bits"] < 30

    res_strong = cyber_defense.evaluate_password_entropy("PHASS_Sphere!2026#Apex_Core")
    assert res_strong["is_secure"] is True
    assert res_strong["entropy_bits"] > 70


# 3. Grand Unified Omni-Bus Orchestrator
def test_unified_orchestrator():
    unified_orchestrator.initialize_all_systems()
    status = unified_orchestrator.get_unified_status()

    assert status.version in ("3.0.0", "4.0.0", "5.0.0", "6.0.0", "7.0.0", "8.0.0")
    assert len(status.subsystems_online) >= 8
    assert status.subsystems_online["1_Physical_Robotics_6DOF"] is True
    assert status.subsystems_online["8_Cybersecurity_Defense_Suite"] is True


# 4. Conversational Directives for Cyber & Architecture
def test_conversational_cyber_and_unified():
    # Cyber scan
    res_c = conversational_agent.handle_natural_conversation("run a cyber scan")
    assert res_c is not None
    assert res_c["type"] == "CYBER_DEFENSE_AUDIT"
    assert res_c["action_executed"] == "RUN_CYBER_DEFENSE_AUDIT"

    # Architecture status
    res_u = conversational_agent.handle_natural_conversation("omni status")
    assert res_u is not None
    assert res_u["type"] == "UNIFIED_PLATFORM_STATUS"
    assert res_u["action_executed"] == "GET_UNIFIED_STATUS"
