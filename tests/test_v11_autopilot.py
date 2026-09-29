"""
Enterprise Autopilot Test Suite for P.H.A.S.S v11.0 (Kernel Rewrite).
Verifies:
1. Background Intention Pre-Loader (USB hotplug, pre-loaded status, disconnect notice).
2. Semantic Error Auto-Repair (missing library installation, DTR/RTS bootloader toggle, port reset).
3. Embedded Serial Plotter & Live Waveform Monitor.
4. Lifelong Context Unified Memory ('check it' resolution, auto-context switching).
5. Zero-Latency Response Cache (<100ms execution benchmark).
"""

import json
import os
import sys
import time
from pathlib import Path
import pytest

from core.background_daemon import BackgroundIntentionDaemon, background_daemon
from core.auto_repair_engine import SemanticAutoRepairEngine, auto_repair_engine
from core.lifelong_context import LifelongContextEngine, lifelong_context
from core.response_cache import ZeroLatencyCache, response_cache
from hardware.programming_orchestrator import ProgrammingOrchestrator, programming_orchestrator
from nlp.answer_pipeline import process_query


def test_background_daemon_hotplug():
    """
    Tests background intention daemon hotplug events:
    - Connect: pre-loads hardware and sets status to '🔌 ESP32 Pre-loaded (Ready in 2s)'
    - Disconnect: sets status to '⚠️ ESP32 disconnected'
    """
    daemon = BackgroundIntentionDaemon.get_instance()
    events_received = []

    def _listener(evt, data):
        events_received.append((evt, data))

    daemon.register_listener(_listener)

    # 1. Simulate Connect
    conn_data = daemon.simulate_hotplug("connect", board="ESP32", port="COM3")
    assert "Pre-loaded" in conn_data["status_text"]
    assert conn_data["toolchain_preloaded"] is True
    assert daemon.latest_status == "🔌 ESP32 Pre-loaded (Ready in 2s)"
    assert any(e[0] == "hardware_connected" for e in events_received)

    # 2. Simulate Disconnect
    dis_data = daemon.simulate_hotplug("disconnect", board="ESP32", port="COM3")
    assert "disconnected" in dis_data["status_text"]
    # 3. Restore connect state
    daemon.simulate_hotplug("connect", board="ESP32", port="COM3")
    daemon.unregister_listener(_listener)


def test_semantic_error_auto_repair():
    """
    Tests automatic error diagnosis and self-healing:
    - Missing Library: auto-installs/generates mock header and recovers.
    - Bootloader Timeout: executes DTR/RTS pulse.
    - Orchestrator compilation recovery using auto-repair.
    """
    engine = SemanticAutoRepairEngine.get_instance()

    # 1. Missing Library Diagnosis & Repair
    missing_lib_err = "fatal error: Adafruit_Sensor.h: No such file or directory"
    repair_res = engine.diagnose_and_repair(missing_lib_err, board="ESP32", port="COM3")
    assert repair_res["repaired"] is True
    assert repair_res["cause"] == "missing_library"
    assert "Adafruit_Sensor" in repair_res["action_taken"]
    assert Path("firmware/build/esp32/include/Adafruit_Sensor.h").exists()

    # 2. Bootloader Timeout Diagnosis & Repair
    boot_err = "A fatal error occurred: Failed to connect to ESP32: Timeout waiting for bootloader packet"
    boot_res = engine.diagnose_and_repair(boot_err, board="ESP32", port="COM3")
    assert boot_res["repaired"] is True
    assert boot_res["cause"] == "bootloader_timeout"
    assert "DTR/RTS" in boot_res["action_taken"]

    # 3. Flasher Auto-Repair Recovery Loop
    orchestrator = ProgrammingOrchestrator.get_instance()
    recovered_flash = orchestrator.compile_and_flash(simulate_error="fatal error: Wire.h: No such file or directory")
    assert recovered_flash["status"] == "SUCCESS"
    assert any("Auto-Repair" in a for a in recovered_flash["attempts"])


def test_embedded_serial_plotter():
    """
    Tests embedded Matplotlib serial plotter in Holographic UI:
    - Verifies tab existence.
    - Verifies CSV stream parsing (100, 200, 300) into plot series.
    - Verifies clear functionality.
    """
    import customtkinter as ctk
    from ui.main_window import AssistantUI

    root = ctk.CTk()
    root.withdraw()

    ui = AssistantUI(root=root)

    # 1. Tab exists
    assert hasattr(ui, "tab_serial")
    assert hasattr(ui, "plot_canvas")
    assert hasattr(ui, "serial_line")

    # 2. Feed comma-separated numerical line
    ui.feed_serial_data("100, 200, 300")
    assert 100.0 in ui.serial_plot_data
    assert 200.0 in ui.serial_plot_data
    assert 300.0 in ui.serial_plot_data

    # 3. Clear plotter
    ui.clear_serial_plotter()
    assert len(ui.serial_plot_data) == 1
    assert ui.serial_plot_data[0] == 0.0

    root.destroy()


def test_lifelong_context_resolution():
    """
    Tests 3-tier lifelong unified context:
    - Short-term pronoun resolution ('check it' -> last referenced component)
    - Auto-context mode switching on board connection.
    """
    ctx = LifelongContextEngine.get_instance()

    # 1. Record component in short-term memory
    ctx.record_message("user", "Can you check the specs of 2N2222?")
    resolved = ctx.resolve_reference("check it")
    assert "2N2222" in resolved

    # 2. Context switching
    ctx.set_active_hardware("STM32", "/dev/ttyUSB1")
    assert ctx.medium_term["active_mode"] == "STM32 Mode"
    resolved_flash = ctx.resolve_reference("flash it")
    assert "STM32" in resolved_flash

    # Reset back to ESP32 default
    ctx.set_active_hardware("ESP32", "COM3")


def test_zero_latency_cache():
    """
    Tests Zero-Latency Response Cache:
    - Asserts static factual query execution time is < 0.100s (100ms).
    - Asserts cached output contains accurate data.
    """
    cache = ZeroLatencyCache.get_instance()

    start_t = time.time()
    res = cache.get("bc547 pinout")
    elapsed_ms = (time.time() - start_t) * 1000

    assert res is not None
    assert "TO-92" in res
    assert "Collector (C)" in res
    assert elapsed_ms < 100.0, f"Cache retrieval took {elapsed_ms:.2f}ms, exceeding 100ms benchmark!"

    # Test pipeline integration
    pipe_start = time.time()
    pipe_res = process_query("pinout of bc547")
    pipe_elapsed_ms = (pipe_start - time.time()) * 1000
    assert "BC547" in pipe_res
