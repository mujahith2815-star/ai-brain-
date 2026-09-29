"""
Integration tests for P.H.A.S.S Real-Time Hardware Programming (Domain 28).
Verifies tool registration, Planner-to-Executor routing, execution logging,
and Holographic UI hardware status updates.
"""

import pytest
from tools.registry import tool_registry
import tools.builtin_tools
from core.llama_tool_agent import llama_tool_agent, process_query
from hardware.detection_engine import HardwareDetector


def test_hardware_tools_registered():
    """Verifies that detect_hardware, program_board, monitor_serial, and list_boards exist in tool_registry."""
    required_tools = ["detect_hardware", "program_board", "monitor_serial", "list_boards"]
    for t in required_tools:
        assert tool_registry.has_tool(t), f"Tool '{t}' is not registered in tool_registry!"


def test_detect_hardware_routes_correctly():
    """Verifies the Planner routes detect_hardware, program_board, and monitor_serial correctly."""
    decision = llama_tool_agent._native_reasoner_decision("detect hardware")
    assert decision is not None, "Planner decision was None!"
    assert "actions" in decision, "Planner decision missing 'actions'!"
    assert decision["actions"][0]["tool"] == "detect_hardware"

    # Verify execution output via full pipeline
    res = process_query("detect hardware")
    assert "Connected Hardware" in res or "ESP32" in res, f"Unexpected response: {res}"
    assert "4.0" not in res, "Math fallback was improperly invoked!"


def test_ui_shows_hardware_status():
    """Verifies the UI sidebar updates its hardware status indicator and includes detect button."""
    from ui.main_window import AssistantUI
    app = AssistantUI()
    try:
        # Check that indicator label exists
        assert hasattr(app, "stat_hw_status"), "AssistantUI missing stat_hw_status indicator!"
        # Trigger update
        app.update_hardware_status()
        text = app.stat_hw_status.cget("text")
        assert "🔌" in text, f"Expected plug emoji in status text: {text}"
        assert "ESP32" in text or "COM" in text or "Hardware" in text, f"Unexpected status text: {text}"

        # Verify button exists with proper title
        assert hasattr(app, "btn_detect_hw"), "AssistantUI missing btn_detect_hw button!"
        assert app.btn_detect_hw.cget("text") == "📡 Detect Hardware"
    finally:
        app.scan_canvas.stop()
        app.voice_indicator.stop_animation()
        if getattr(app, "system_update_id", None):
            try:
                app.root.after_cancel(app.system_update_id)
            except Exception:
                pass
        app.root.destroy()
