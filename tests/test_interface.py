import pytest
from core.interface_master import (
    interface_master,
    listen_voice_command,
    speak_voice_response,
    register_global_hotkey,
    setup_system_tray,
    launch_gui_dashboard,
    get_interface_status,
)


def test_interface_status():
    status = get_interface_status()
    assert "voice_stt_available" in status
    assert "voice_tts_available" in status
    assert "registered_hotkeys" in status


def test_voice_command_and_speech():
    voice_res = listen_voice_command(timeout=1.0)
    assert voice_res["status"] == "SUCCESS"

    speak_res = speak_voice_response("Testing speech interface", speed=150, blocking=False)
    assert speak_res["status"] == "SUCCESS"
    assert speak_res["spoken_text"] == "Testing speech interface"


def test_global_hotkey_registration_and_trigger():
    invoked = []
    reg = register_global_hotkey("Ctrl+Alt+S", lambda: invoked.append(True) or "hotkey_success")
    assert reg["status"] == "SUCCESS"

    trig = interface_master.trigger_hotkey("Ctrl+Alt+S")
    assert trig["status"] == "SUCCESS"
    assert trig["result"] == "hotkey_success"
    assert len(invoked) == 1


def test_system_tray_setup():
    res = setup_system_tray()
    assert res["status"] == "SUCCESS"
    assert res["tray_active"] is True


def test_launch_gui_dashboard_non_blocking():
    res = launch_gui_dashboard(blocking=False)
    assert res["status"] == "SUCCESS"
    assert res["dashboard_active"] is True