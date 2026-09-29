"""
Unit & Integration Tests for Signal Spectrum Scanner and System Accelerator.
"""

import pytest
from tools.signal_scanner import signal_scanner
from tools.system_accelerator import system_accelerator
from nlp.conversational_agent import conversational_agent


# 1. Universal Multi-Band Signal & Spectrum Scanner
def test_universal_signal_scanner():
    rep = signal_scanner.scan_all_signals()

    assert rep.total_signals_detected >= 5
    assert rep.wifi_networks_count >= 1
    assert rep.bluetooth_devices_count >= 1
    assert rep.rf_carriers_count >= 1
    assert rep.nfc_tags_count >= 1
    assert rep.lan_arp_devices_count >= 1

    txt = signal_scanner.format_signal_report_text(rep)
    assert "MULTI-BAND SPECTRUM SCAN" in txt
    assert "[Wi-Fi]" in txt
    assert "[Bluetooth]" in txt


# 2. System Accelerator & Performance Booster
def test_system_accelerator_boost():
    acc_res = system_accelerator.boost_system_performance()

    assert acc_res.success is True
    assert len(acc_res.optimizations_applied) >= 3
    assert "DNS" in acc_res.summary or "governor" in acc_res.summary

    txt = system_accelerator.format_accelerator_report_text(acc_res)
    assert "PERFORMANCE & SPEED ACCELERATOR" in txt


# 3. Master Audio Volume & Mute Controller
def test_volume_control():
    ok, msg = system_accelerator.set_volume(85)
    assert ok is True
    assert system_accelerator.master_volume_pct == 85

    ok_m, msg_m = system_accelerator.toggle_mute()
    assert ok_m is True
    assert "MUTED" in msg_m or "UNMUTED" in msg_m


# 4. Native OS Utility Launch
def test_os_utility_launch():
    ok, msg = system_accelerator.launch_os_utility("task_manager")
    assert ok is True
    assert "Task Manager" in msg


# 5. Conversational Directives with Typo Auto-Correction
def test_conversational_signal_and_acceleration():
    # A. Signal Scan Directive
    res_sig = conversational_agent.handle_natural_conversation("scan near device signal")
    assert res_sig is not None
    assert res_sig["type"] == "MULTI_BAND_SIGNAL_SCAN"
    assert "SPECTRUM SCAN" in res_sig["speech_text"]

    # B. Boost System Speed (with typo "boost sysmtem speed")
    res_boost = conversational_agent.handle_natural_conversation("boost sysmtem speed")
    assert res_boost is not None
    assert res_boost["type"] == "SYSTEM_ACCELERATION"

    # C. Set Volume
    res_vol = conversational_agent.handle_natural_conversation("set volume to 80%")
    assert res_vol is not None
    assert res_vol["type"] == "SYSTEM_VOLUME_CONTROL"

    # D. Open Device Manager
    res_dev = conversational_agent.handle_natural_conversation("open device manager")
    assert res_dev is not None
    assert res_dev["type"] == "OS_UTILITY_LAUNCH"
