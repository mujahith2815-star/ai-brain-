"""
Unit & Integration Tests for Universal Maker & Universal Remote App.
"""

import pytest
import tkinter as tk
from tools.apps.universal_remote import UniversalRemoteApp
from tools.universal_maker import universal_maker
from nlp.conversational_agent import conversational_agent


# 1. Universal Remote Controller GUI Headless Test
def test_universal_remote_app_headless():
    root = tk.Tk()
    root.withdraw()
    app = UniversalRemoteApp(root)
    assert app.power_state is True
    assert app.current_volume == 32
    assert app.ac_temp == 22

    # Mode switching
    app._switch_mode("MEDIA")
    assert app.active_mode == "MEDIA"
    app._switch_mode("CLIMATE AC")
    assert app.active_mode == "CLIMATE AC"
    app._switch_mode("TV")
    assert app.active_mode == "TV"

    # Volume & Channel adjustments
    app._vol_up()
    assert app.current_volume == 34
    app._ch_up()
    assert app.current_channel == 105
    app._temp_up()
    assert app.ac_temp == 23

    root.destroy()


# 2. Universal Maker Tool Synthesis
def test_universal_maker_apps():
    # A. Universal Remote
    ok, title, details = universal_maker.make_and_launch_app("make a universal remote")
    assert ok is True
    assert "Remote" in title

    # B. Calculator
    ok_c, title_c, details_c = universal_maker.make_and_launch_app("build a calculator")
    assert ok_c is True
    assert "Calculator" in title_c

    # C. Arcade Game
    ok_g, title_g, details_g = universal_maker.make_and_launch_app("make a game")
    assert ok_g is True
    assert "Arcade" in title_g or "Game" in title_g

    assert universal_maker.apps_created_count >= 3


# 3. Conversational Routing for Universal Maker
def test_conversational_universal_maker():
    res = conversational_agent.handle_natural_conversation("make a universal remote")
    assert res is not None
    assert res["type"] == "UNIVERSAL_MAKER"
    assert "REMOTE" in res["action_executed"]
    assert "built and launched" in res["speech_text"].lower() or "online" in res["speech_text"].lower()
