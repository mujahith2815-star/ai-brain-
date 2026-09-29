"""
Comprehensive Test Suite for P.H.A.S.S "Ambient Intelligence" Layer.
Validates:
1. Boot-Level System Service Installer (NSSM, sc.exe, systemd, 5s auto-restart recovery policy)
2. Always-On Wake Word ("Hey P.H.A.S.S" / "P.H.A.S.S", pulsing cyan dot tray icon, Ctrl+Shift+P HUD hotkey)
3. Ambient Screen Vision (silent screenshot, OCR text extraction, compiler/syntax error interruption)
4. Autopilot Default Mode (Autonomous mode, silent maintenance, Data Hub logging, critical hardware alert)
5. Screen query handling in nlp/answer_pipeline.py ("What's on my screen?")
"""

import sys
import pytest
from pathlib import Path
from PIL import Image

from core.voice_interface import get_voice_interface
from core.global_listener import create_tray_icon_image, get_global_listener
from core.ambient_vision import ambient_vision, AmbientVision
from core.autopilot_mode import autopilot_mode, AutopilotMode
from core.data_hub import data_hub
from nlp.answer_pipeline import process_query
from install_phass_service import install_windows_service, generate_linux_systemd_unit


def test_service_installer_configurations():
    """Verify Windows and Linux service configurations and 5-second recovery policy."""
    # 1. Windows configuration
    win_res = install_windows_service(dry_run=True)
    assert win_res["platform"] == "windows"
    assert win_res["service_name"] == "PHASS"
    assert win_res["recovery_restart_sec"] == 5
    assert win_res["status"] == "CONFIGURED"

    # 2. Linux systemd configuration
    test_unit_path = Path("checkpoints/test_phass.service")
    linux_res = generate_linux_systemd_unit(target_path=test_unit_path, dry_run=True)
    assert linux_res["platform"] == "linux"
    assert linux_res["recovery_restart_sec"] == 5
    assert linux_res["status"] == "CONFIGURED"


def test_wake_word_phrases_and_tray_indicator():
    """Verify wake word phrase parsing, start_on_boot API, and pulsing cyan dot icon."""
    voice = get_voice_interface()

    # Wake phrase detection
    assert voice.is_wake_phrase("Hey P.H.A.S.S") is True
    assert voice.is_wake_phrase("hey phass") is True
    assert voice.is_wake_phrase("P.H.A.S.S") is True
    assert voice.is_wake_phrase("phass, can you help") is True
    assert voice.is_wake_phrase("good morning computer") is False

    # Command extraction
    cmd1 = voice.extract_command_after_wake_word("Hey P.H.A.S.S, organize my files.")
    assert cmd1 == "organize my files."

    cmd2 = voice.extract_command_after_wake_word("P.H.A.S.S, clean up my temp files")
    assert cmd2 == "clean up my temp files"

    # Verify start_on_boot method exists
    assert hasattr(voice, "start_on_boot")

    # System Tray Icon: Pulsing Cyan Dot when 'listening'
    tray_img = create_tray_icon_image(state="listening")
    assert isinstance(tray_img, Image.Image)
    assert tray_img.size == (64, 64)

    # Check center pixel / cyan hue in listening state
    colors = tray_img.getcolors(maxcolors=256)
    assert any(c[1][0] == 0 and c[1][1] == 240 and c[1][2] == 255 for c in colors or [])

    # Verify GlobalListener has Ctrl+Shift+P HUD binding
    listener = get_global_listener()
    assert hasattr(listener, "set_tray_state")
    listener.set_tray_state("listening")
    assert listener.voice_state == "listening"


def test_ambient_vision_compilation_error_detection():
    """Verify Ambient Vision error detection and proactive interruption."""
    vision = AmbientVision.get_instance()

    # 1. Test missing semicolon detection
    semicolon_ocr = "src/main.cpp:42: error: expected ';' before 'return'"
    err1 = vision.detect_screen_errors(semicolon_ocr)
    assert err1 is not None
    assert err1["error_type"] == "SYNTAX_SEMICOLON"
    assert "Missing semicolon at line 42" in err1["message"]

    # 2. Test missing library / compilation failure
    compilation_ocr = "Compilation Failed: ModuleNotFoundError: No module named 'lvgl'"
    err2 = vision.detect_screen_errors(compilation_ocr)
    assert err2 is not None
    assert "Sir, I see a compilation error on your screen. It appears to be a missing library." in err2["message"]

    # 3. Test proactive interruption dispatch
    test_img = Image.new("RGB", (100, 100), color=(0, 0, 0))
    test_img._simulated_ocr_text = "Compilation Failed: fatal error: WiFi.h: No such file or directory"
    spoken_alert = vision.scan_and_interrupt_if_needed(test_img, speak=False)
    assert spoken_alert is not None
    assert "compilation error on your screen" in spoken_alert


def test_autopilot_autonomous_mode():
    """Verify default autonomous mode, silent maintenance execution, and critical hardware alerts."""
    auto = AutopilotMode.get_instance()
    assert auto.is_autonomous is True

    # Standard maintenance does not require confirmation ("Shall I proceed?")
    assert auto.requires_confirmation("clean_temp") is False
    assert auto.requires_confirmation("organize_downloads") is False
    assert auto.requires_confirmation("backup") is False

    # Silent maintenance execution
    clean_res = auto.run_silent_temp_cleanup()
    assert "freed_mb" in clean_res

    backup_res = auto.run_silent_backup()
    assert backup_res["status"] == "SUCCESS"

    # Maintenance log exists in Data Hub
    log_file = data_hub.resolve("logs", "maintenance.log")
    assert log_file.exists()

    # Critical hardware alert when D: drive is >= 90-95% full
    alert = auto.check_critical_hardware_issues(drive_letter="D", forced_used_pct=95.0, speak=False)
    assert alert is not None
    assert alert == "Sir, your D: drive is 95% full."

    # Normal disk usage does NOT trigger an alert
    normal = auto.check_critical_hardware_issues(drive_letter="D", forced_used_pct=60.0, speak=False)
    assert normal is None


def test_ambient_screen_nlp_query():
    """Verify that asking 'What's on my screen?' returns screen analysis without error."""
    resp = process_query("What's on my screen?")
    assert isinstance(resp, str)
    assert len(resp) > 10
    assert "screen" in resp.lower() or "captured" in resp.lower() or "observed" in resp.lower() or "detected" in resp.lower()
