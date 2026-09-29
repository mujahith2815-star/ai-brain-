"""
Unit & Integration Tests for Real-Time Casual & Natural Communications.
"""

import pytest
import asyncio
from core.cognitive_core import CognitiveCore
from nlp.conversational_agent import conversational_agent


def test_conversational_greetings_and_chitchat():
    res_hi = conversational_agent.handle_natural_conversation("Hello!")
    assert res_hi is not None
    assert res_hi["handled"] is True
    assert len(res_hi["speech_text"]) > 5

    res_how = conversational_agent.handle_natural_conversation("How are you doing?")
    assert res_how is not None
    assert "battery" in res_how["speech_text"].lower() or "systems" in res_how["speech_text"].lower()


def test_conversational_app_launching():
    res_wa = conversational_agent.handle_natural_conversation("open whatsapp")
    assert res_wa is not None
    assert "whatsapp" in res_wa["speech_text"].lower()

    res_yt = conversational_agent.handle_natural_conversation("open youtube")
    assert res_yt is not None
    assert "youtube" in res_yt["speech_text"].lower()

    res_gd = conversational_agent.handle_natural_conversation("open google drive and show last message")
    assert res_gd is not None
    assert "google drive" in res_gd["speech_text"].lower()
    assert "drive.google.com" in res_gd["speech_text"].lower()


def test_conversational_realtime_queries():
    res_batt = conversational_agent.handle_natural_conversation("What is your battery?")
    assert res_batt is not None
    assert "%" in res_batt["speech_text"]


@pytest.mark.asyncio
async def test_cognitive_core_natural_routing():
    core = CognitiveCore(engine_type="offline")
    await core.boot_sequence()

    # 1. Casual Greeting -> Not an artificial 4-step mission
    res_chat = await core.submit_user_directive("Hi P.H.A.S.S!")
    assert res_chat["goal"] is None
    assert res_chat["status"] == "CHITCHAT"
    assert len(res_chat["nlg_response"]) > 10

    # 2. App Launch -> Direct execution
    res_app = await core.submit_user_directive("open whatsapp")
    assert res_app["goal"] is None
    assert "whatsapp" in res_app["nlg_response"].lower()

    # 3. Real Robotic Directive -> Natural mission acknowledgement
    res_mission = await core.submit_user_directive("Navigate to Charging Dock")
    assert res_mission["goal"] is not None
    assert "Magnetic Charging Dock" in res_mission["nlg_response"]
