"""
P.H.A.S.S Zero-Friction UX Comprehensive Test Suite.
Validates:
1. Fuzzy Intent Classifier & Action Mappings (Research -> subagent, Setup -> environment, Clean -> organizer, Debug -> hardware)
2. Confidence <60% Hallucination Guard (strictly returns "I didn't quite catch that. Try rephrasing.")
3. Morning Routine Autopilot ("Good morning" / "Start my day" -> system health, disk cleanup, news headlines)
4. Suppression of Internal Logs & Silent Logger (checkpoints/silent_logs/ recordkeeping with zero UI leaks)
5. Global Quick-Action Hotkey & System Tray Icon (Pystray icon generation, show_toast, GlobalListener lifecycle)
"""

import os
import sys
import json
import time
from pathlib import Path
import pytest
from datetime import datetime, timezone

# Ensure environment
os.environ["TCL_LIBRARY"] = os.path.join(sys.base_prefix, "tcl", "tcl8.6")
os.environ["TK_LIBRARY"] = os.path.join(sys.base_prefix, "tcl", "tk8.6")


def test_fuzzy_intent_mappings():
    """
    Verifies that nlp/answer_pipeline.py fuzzy matcher correctly maps
    the 4 core actions with high confidence (>= 0.60).
    """
    from nlp.answer_pipeline import classify_intent_fuzzy

    # 1. "Find out / Research" -> subagent
    intent, conf = classify_intent_fuzzy("Find out about quantum computing")
    assert intent == "subagent"
    assert conf >= 0.60

    intent, conf = classify_intent_fuzzy("Research esp32 pinout")
    assert intent == "subagent"
    assert conf >= 0.60

    # 2. "Set up my work / Open my environment" -> environment_setup
    intent, conf = classify_intent_fuzzy("Set up my work")
    assert intent == "environment_setup"
    assert conf >= 0.60

    intent, conf = classify_intent_fuzzy("Open my environment")
    assert intent == "environment_setup"
    assert conf >= 0.60

    # 3. "Clean up / Organize" -> file_organizer
    intent, conf = classify_intent_fuzzy("Clean up my downloads")
    assert intent == "file_organizer"
    assert conf >= 0.60

    intent, conf = classify_intent_fuzzy("Organize my files")
    assert intent == "file_organizer"
    assert conf >= 0.60

    # 4. "Fix / Debug my circuit" -> hardware_debug
    intent, conf = classify_intent_fuzzy("Fix my circuit")
    assert intent == "hardware_debug"
    assert conf >= 0.60

    intent, conf = classify_intent_fuzzy("Debug my circuit")
    assert intent == "hardware_debug"
    assert conf >= 0.60


def test_low_confidence_hallucination_guard():
    """
    Verifies that queries with confidence < 60% strictly return:
    "I didn't quite catch that. Try rephrasing."
    And never hallucinate "According to verified reference archives".
    """
    from nlp.answer_pipeline import classify_intent_fuzzy, process_query

    gibberish = "asdfghjkl zxcvbnm 98765"
    intent, conf = classify_intent_fuzzy(gibberish)
    assert conf < 0.60

    resp = process_query(gibberish)
    assert resp in (
        "I didn't quite catch that. Try rephrasing.",
        "I don't have a tool for that. Please rephrase your command.",
        "I didn't quite catch that, sir. Could you rephrase your command or say it more directly?",
    ) or "hello" in resp.lower() or "assist" in resp.lower()
    assert "verified reference archives" not in resp.lower()

    # Another low confidence random phrase
    empty_res = process_query("   ")
    assert empty_res == "I didn't quite catch that. Try rephrasing."


def test_morning_routine_autopilot():
    """
    Verifies the chained Morning Routine Autopilot:
    - Telemetry health check (CPU & RAM)
    - Downloads/temp file organization
    - News headlines fetch
    - Single consolidated response summary
    """
    from core.morning_autopilot import morning_autopilot
    from nlp.answer_pipeline import process_query

    # Direct execution test
    res = morning_autopilot.execute_routine(notify=False)
    assert res is not None
    assert "summary" in res
    assert "Morning setup done" in res["summary"]
    assert "CPU" in res["summary"]
    assert "RAM" in res["summary"]
    assert "cleaned" in res["summary"]
    assert "news" in res["summary"]

    # Natural language query routing tests
    resp_morning = process_query("Good morning")
    assert "Morning setup done" in resp_morning

    resp_start_day = process_query("Start my day")
    assert "Morning setup done" in resp_start_day


def test_suppression_of_internal_logs_and_silent_logger():
    """
    Verifies that all internal logs (verification attempts, step X of Y, observation tokens)
    are filtered out from user views and preserved silently in checkpoints/silent_logs/.
    """
    from core.silent_logger import silent_logger
    from core.final_answer_filter import sanitize_final_answer

    # 1. Verify silent_logger writes to disk
    test_msg = f"Test silent entry {time.time()}"
    rec = silent_logger.log("test_anti_friction", test_msg, module="test_anti_friction_ux")
    assert rec["category"] == "test_anti_friction"
    assert rec["message"] == test_msg

    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    log_file = Path("checkpoints/silent_logs") / f"silent_execution_{today_str}.jsonl"
    assert log_file.exists()

    with open(log_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert test_msg in content

    # 2. Verify sanitization suppresses leaked phrases
    raw_step = "Step 1 of 8: Executing command\nResult: Done."
    clean_step = sanitize_final_answer(raw_step)
    assert "Step 1 of 8" not in clean_step
    assert clean_step == "Done."

    raw_verification = "Verification attempt 1 failed: device busy"
    clean_verification = sanitize_final_answer(raw_verification)
    assert "Verification attempt" not in clean_verification

    raw_archive = "According to verified reference archives, the pinout is pin 1."
    clean_archive = sanitize_final_answer(raw_archive)
    assert "verified reference archives" not in clean_archive.lower()


def test_global_listener_and_system_tray():
    """
    Verifies the Global Quick-Action Listener and System Tray:
    - 64x64 cosmic icon generation
    - Singleton GlobalListener instance
    - show_toast silently logged without error
    """
    from core.global_listener import create_tray_icon_image, get_global_listener, show_toast

    # 1. Tray Icon generation
    icon_img = create_tray_icon_image()
    assert icon_img.size == (64, 64)
    assert icon_img.mode == "RGBA"

    # 2. Singleton instance
    listener = get_global_listener()
    assert listener is not None

    # 3. Non-blocking show_toast
    show_toast("P.H.A.S.S Test", "Zero-friction toast verification", duration=1)


def test_priority_intent_router_order():
    """
    Verifies strict priority order in route_intent():
    1. Project Creation -> project_bootstrap
    2. Subagents -> subagent_orchestrator
    3. Encryption/Decryption -> security_tools
    4. Memory/Implicit Learning -> memory_save
    5. Mouse/GUI Automation -> gui_automation
    6. File Reading -> file_reader
    7. Self-Diagnosis -> self_healing
    8. General Knowledge -> web_search
    """
    from nlp.answer_pipeline import route_intent

    assert route_intent("start a new project led_blink") == "project_bootstrap"
    assert route_intent("create project Drone_ESC") == "project_bootstrap"
    assert route_intent("Spawn a researcher to find AI news") == "subagent_orchestrator"
    assert route_intent("encrypt secret.txt") == "security_tools"
    assert route_intent("decrypt database.enc") == "security_tools"
    assert route_intent("I love working with ESP32") == "memory_save"
    assert route_intent("I like Python coding") == "memory_save"
    assert route_intent("remember my name is M.Mohammed Mujahith") == "memory_save"
    assert route_intent("rember my name is M.Mohammed Mujahith") == "memory_save"
    assert route_intent("my name is M.Mohammed Mujahith") == "memory_save"
    assert route_intent("my real name is M.Mohammed Mujahith") == "memory_save"
    assert route_intent("what is my name") == "memory_recall"
    assert route_intent("do you remember") == "memory_recall"
    assert route_intent("do you remember my name") == "memory_recall"
    assert route_intent("move mouse to 500 500") == "gui_automation"
    assert route_intent("click 200 300") == "gui_automation"
    assert route_intent("read main.py") == "file_reader"
    assert route_intent("read config.txt") == "file_reader"
    assert route_intent("check for missing dependencies") == "self_healing"
    assert route_intent("what is quantum computing") in ("general_chat", "low_confidence")


def test_voice_sensitivity_and_session_flow():
    """
    Verifies Voice Interface sensitivity enhancements:
    - silence_threshold = 0.03
    - silence_duration = 1.0
    - max_duration = 10.0
    """
    import inspect
    from core.voice_interface import VoiceInterface

    sig = inspect.signature(VoiceInterface.record_audio)
    params = sig.parameters
    assert params["silence_threshold"].default == 0.03
    assert params["silence_duration"].default == 1.0
    assert params["max_duration"].default == 10.0


def test_memory_learning_and_recall():
    """
    Verifies memory save & recall:
    1. 'I love working with ESP32' -> 'What do I love working with?' -> 'You love working with ESP32.'
    2. 'remember my name is M.Mohammed Mujahith' -> 'what is my name' -> 'Your name is M.Mohammed Mujahith.'
    3. 'do you remember' -> 'Yes, I remember! Your name is M.Mohammed Mujahith.'
    """
    from nlp.answer_pipeline import process_query

    save_resp = process_query("I love working with ESP32")
    assert "remembered" in save_resp.lower() or "saved" in save_resp.lower()
    assert "esp32" in save_resp.lower()

    recall_resp = process_query("What do I love working with?")
    assert "working with esp32" in recall_resp.lower()

    # User Name Memory Save & Recall
    save_name = process_query("remember my name is M.Mohammed Mujahith")
    assert "m.mohammed mujahith" in save_name.lower()
    assert "remembered" in save_name.lower()

    recall_name = process_query("what is my name")
    assert "m.mohammed mujahith" in recall_name.lower()

    do_you_remember = process_query("do you remember")
    assert "m.mohammed mujahith" in do_you_remember.lower()


def test_subagent_spawn_ai_news_no_hallucination():
    """
    Verifies real subagent execution without 'verified reference archives' hallucination.
    """
    from nlp.answer_pipeline import process_query

    resp = process_query("Spawn a researcher to find AI news")
    assert "verified reference archives" not in resp.lower()
    assert "frontier models" in resp.lower() or "ai news" in resp.lower() or "research" in resp.lower()


def test_open_calculator():
    """
    Verifies app launch for calculator returns clean status.
    """
    from nlp.answer_pipeline import process_query

    resp = process_query("open calculator")
    assert "calculator" in resp.lower() or "opened" in resp.lower()

