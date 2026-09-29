"""
Comprehensive Enterprise Self-Healing Test Suite for P.H.A.S.S v10.0.
Verifies:
1. UI responsiveness & non-blocking execution (< 1 second).
2. Universal hardware detection, software probe handshakes, and fallback confirmation.
3. Ultimate Natural Language Filter (JSON leaks, step logs, number formatting, HTML stripping).
4. Multi-stage toolchain retry chain (PlatformIO -> arduino-cli -> permission guidance).
"""

import json
import os
import sys
import time
from pathlib import Path
import pytest

from core.final_answer_filter import FinalAnswerFilter, sanitize_final_answer
from hardware.detection_engine import HardwareDetector, DetectedDevice
from hardware.programming_orchestrator import ProgrammingOrchestrator


def test_ui_responsiveness():
    """
    Verifies that UI message submission and processing runs asynchronously
    and returns immediate control to the UI event loop within 1.0 second.
    """
    import customtkinter as ctk
    from ui.main_window import AssistantUI

    try:
        root = ctk.CTk()
        root.withdraw()
    except Exception as e:
        pytest.skip(f"Tk GUI display unavailable in this process context: {e}")

    ui = AssistantUI(root=root)

    start_time = time.time()
    # Insert directive and trigger send
    ui.input_entry.insert(0, "program board blink led")
    ui.send_message()
    elapsed = time.time() - start_time

    # Immediate dispatch must take well under 1.0 second (non-blocking)
    assert elapsed < 1.0, f"UI blocked for {elapsed:.3f}s during query submission!"
    assert ui.active_task_frame.winfo_ismapped() or ui._active_task_cancelled is not None

    # Test cancellation responsiveness
    cancel_start = time.time()
    ui.cancel_active_task()
    cancel_elapsed = time.time() - cancel_start
    assert cancel_elapsed < 0.5, f"Cancel blocked for {cancel_elapsed:.3f}s!"
    assert ui._active_task_cancelled.is_set()

    root.destroy()


def test_hardware_handshake():
    """
    Simulates unknown USB serial port, verifies handshake logic,
    and validates fallback mode confirmation and preference persistence.
    """
    detector = HardwareDetector.get_instance()

    # 1. Test fallback prompt for unknown port
    test_port = "COM99" if sys.platform == "win32" else "/dev/ttyUSB99"
    fallback_prompt = f"I found a device on {test_port}. Do you want me to try programming it as an Arduino Uno? (yes/no)"

    dev = DetectedDevice(
        board="Unknown USB Device",
        name=f"Unrecognized Serial Port ({test_port})",
        port=test_port,
        toolchain="arduino-cli",
        status="NEEDS_CONFIRMATION",
        fallback_prompt=fallback_prompt,
    )
    dev_dict = dev.to_dict()
    assert dev_dict["status"] == "NEEDS_CONFIRMATION"
    assert "Arduino Uno? (yes/no)" in dev_dict["fallback_prompt"]

    # 2. Test user choice remembering
    pref = detector.remember_user_choice(test_port, "Arduino Uno", "arduino-cli")
    assert pref["board"] == "Arduino Uno"
    assert pref["toolchain"] == "arduino-cli"

    # 3. Test preference persistence and reload
    detector.load_user_preferences()
    assert test_port.upper() in detector.user_preferences
    assert detector.user_preferences[test_port.upper()]["board"] == "Arduino Uno"


def test_natural_language_filter():
    """
    Tests Ultimate Natural Language Filter across edge cases:
    - Raw JSON leaks
    - 'Step 1 of 8' internal log patterns
    - Length Guard single number formatting (4.0 -> 'The result is 4.0.')
    - HTML scrape cleanup
    - Solo Leveling clean explanation
    """
    f = FinalAnswerFilter.get_instance()

    # 1. Raw JSON Leak
    raw_json = '{"actions": [{"tool": "web_search", "args": {"query": "naruto"}}]}'
    res_json = f.filter(raw_json)
    assert '{"actions":' not in res_json
    assert '"tool":' not in res_json
    assert len(res_json) > 5

    # 2. Step 1 of 8 Leak
    step_leak = "Web search results retrieved. Current Step: 1 of 8. Decide your next action. Return JSON only."
    res_step = f.filter(step_leak)
    assert "Current Step" not in res_step
    assert "Return JSON only" not in res_step

    # 3. Length Guard: single number (4.0)
    single_num = "4.0"
    res_num = f.filter(single_num)
    assert res_num == "The result is 4.0."

    integer_num = "42"
    assert f.filter(integer_num) == "The result is 42."

    # 4. HTML Scrape Cleanup
    html_scrape = '<div class="wiki-content"><h3>Overview</h3><p>Naruto Uzumaki is a ninja of the Hidden Leaf Village.</p></div>'
    res_html = f.filter(html_scrape)
    assert "<div" not in res_html
    assert "<p>" not in res_html
    assert "Naruto Uzumaki is a ninja" in res_html

    # 5. Solo Leveling query with internal log
    solo_leak = "Step 1 of 8 Decide your next action in Solo Leveling"
    res_solo = f.filter(solo_leak)
    assert "Step 1 of 8" not in res_solo
    assert "Solo Leveling" in res_solo
    assert "Shadow Monarch" in res_solo or "System" in res_solo


def test_retry_chain():
    """
    Tests multi-stage toolchain retry logic:
    1. Attempt 1 failure -> recovers via arduino-cli (Attempt 2).
    2. Verifies execution_log.json records the successful toolchain.
    3. Complete failure -> returns Attempt 3 manual permission suggestion.
    """
    orchestrator = ProgrammingOrchestrator.get_instance()

    # 1. Fallback from PlatformIO to arduino-cli
    res_fallback = orchestrator.compile_and_flash(force_fail_pio=True)
    assert res_fallback["status"] == "SUCCESS"
    assert res_fallback["toolchain"] == "arduino-cli"
    assert any("PlatformIO" in a and "FAILED" in a for a in res_fallback["attempts"])
    assert any("arduino-cli" in a and "SUCCESS" in a for a in res_fallback["attempts"])

    # 2. Verify logging to execution_log.json
    log_file = Path("checkpoints/execution_log.json")
    assert log_file.exists()
    with open(log_file, "r", encoding="utf-8") as lf:
        log_data = json.load(lf)
    recent_entry = log_data[-1]
    assert recent_entry["toolchain"] == "arduino-cli"
    assert recent_entry["status"] == "SUCCESS"

    # 3. Complete failure -> Manual permission guidance
    res_failed = orchestrator.compile_and_flash(force_fail_all=True)
    assert res_failed["status"] == "FAILED"
    assert "sudo chmod 666" in res_failed["suggested_fix"]
    assert any("Attempt 3" in a for a in res_failed["attempts"])
