"""
Comprehensive Automated Test Suite for 16 Advanced Feature Domains in P.H.A.S.S Sphere.
Verifies all 16 tool modules, registry integration, safety guards, and Llama agent routing.
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path

# Ensure root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from tools.registry import tool_registry
import tools.builtin_tools
from core.llama_tool_agent import llama_tool_agent


# ---------------------------------------------------------------------------
# 1. System Deep Control Tests
# ---------------------------------------------------------------------------
def test_system_control_safety_guard():
    from tools.system_control import system_control
    # Without confirmation, destructive power actions should return PREVIEW
    res = system_control(action="shutdown", confirmed=False)
    assert res["status"] == "PREVIEW"
    assert res["requires_confirmation"] is True

def test_environment_manager():
    from tools.system_control import environment_manager
    set_res = environment_manager(action="set", var_name="PHASS_TEST_VAR", var_value="active_123")
    assert set_res["status"] == "SUCCESS"
    assert set_res["value"] == "active_123"

    get_res = environment_manager(action="get", var_name="PHASS_TEST_VAR")
    assert get_res["status"] == "SUCCESS"
    assert get_res["value"] == "active_123"

    del_res = environment_manager(action="delete", var_name="PHASS_TEST_VAR")
    assert del_res["status"] == "SUCCESS"

def test_clipboard_and_screenshot():
    from tools.system_control import clipboard_manager, screenshot_capture
    cb_set = clipboard_manager(action="set", content="PHASS_TEST_CLIPBOARD")
    assert cb_set["status"] == "SUCCESS"

    with tempfile.TemporaryDirectory() as tmpdir:
        shot_path = os.path.join(tmpdir, "test_shot.png")
        shot_res = screenshot_capture(output_path=shot_path, perform_ocr=False)
        assert shot_res["status"] == "SUCCESS"
        assert os.path.exists(shot_path)


# ---------------------------------------------------------------------------
# 2. Web & Browser Automation Tests
# ---------------------------------------------------------------------------
def test_web_scraper_and_rss():
    from tools.web_automation import web_scraper, rss_reader
    mock_html = "<html><body><h1>P.H.A.S.S Header</h1><p>Welcome to automated web testing.</p><a href='https://example.com'>Link</a></body></html>"
    res = web_scraper(url="", extract_type="all", html_content=mock_html)
    assert res["status"] == "SUCCESS"
    assert "P.H.A.S.S Header" in res["text"]
    assert len(res["links"]) == 1

def test_web_password_manager():
    from tools.web_automation import password_manager_web
    save_res = password_manager_web(action="save", domain="testservice.local", username="admin", password="SecretPass123!")
    assert save_res["status"] == "SUCCESS"

    get_res = password_manager_web(action="get", domain="testservice.local")
    assert get_res["status"] == "SUCCESS"
    assert get_res["password"] == "SecretPass123!"

def test_social_media_poster_confirmation():
    from tools.web_automation import social_media_poster
    preview_res = social_media_poster(platform="twitter", text="Hello world", confirmed=False)
    assert preview_res["status"] == "PREVIEW"
    assert preview_res["requires_confirmation"] is True

    exec_res = social_media_poster(platform="twitter", text="Hello world", confirmed=True)
    assert exec_res["status"] == "SUCCESS"
    assert exec_res["posted"] is True


# ---------------------------------------------------------------------------
# 3. Data & Document Processing Tests
# ---------------------------------------------------------------------------
def test_csv_excel_master():
    from tools.document_processing import csv_excel_master
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "test_data.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("id,dept,amount\n1,Engineering,500\n2,Sales,300\n3,Engineering,700\n")

        summary = csv_excel_master(action="summary", file_path=csv_path)
        assert summary["status"] == "SUCCESS"
        assert summary["total_rows"] == 3

        pivot = csv_excel_master(action="pivot", file_path=csv_path, pivot_group_col="dept", pivot_sum_col="amount")
        assert pivot["status"] == "SUCCESS"
        assert pivot["aggregations"]["Engineering"] == 1200.0
        assert pivot["aggregations"]["Sales"] == 300.0

def test_archive_manager():
    from tools.document_processing import archive_manager
    with tempfile.TemporaryDirectory() as tmpdir:
        f1 = os.path.join(tmpdir, "file1.txt")
        with open(f1, "w") as f:
            f.write("Archive test data.")

        zip_p = os.path.join(tmpdir, "bundle.zip")
        create_res = archive_manager(action="create", archive_path=zip_p, files_to_add=[f1])
        assert create_res["status"] == "SUCCESS"
        assert os.path.exists(zip_p)

        list_res = archive_manager(action="list", archive_path=zip_p)
        assert list_res["status"] == "SUCCESS"
        assert "file1.txt" in list_res["files"]

def test_database_connector_sqlite():
    from tools.document_processing import database_connector
    res = database_connector(query="SELECT 42 as answer, 'P.H.A.S.S' as system")
    assert res["status"] == "SUCCESS"
    assert res["data"][0]["answer"] == 42
    assert res["data"][0]["system"] == "P.H.A.S.S"


# ---------------------------------------------------------------------------
# 4. AI & ML Capabilities Tests
# ---------------------------------------------------------------------------
def test_text_summarizer():
    from tools.ai_ml_tools import text_summarizer
    long_text = (
        "Artificial intelligence systems are rapidly evolving. "
        "Autonomous agents can now coordinate multi-step workflows. "
        "Local models provide privacy and security for enterprise tasks. "
        "Antigravity connects reasoning engines with deterministic tooling. "
        "Future architectures will emphasize hybrid cognitive dual-brains."
    )
    res = text_summarizer(text=long_text, max_sentences=2)
    assert res["status"] == "SUCCESS"
    assert res["summary_sentences"] == 2

def test_sentiment_analyzer():
    from tools.ai_ml_tools import sentiment_analyzer
    pos = sentiment_analyzer("This tool is amazing, fantastic, and extremely helpful!")
    assert pos["sentiment"] == "positive"
    assert pos["polarity"] > 0

    neg = sentiment_analyzer("The system is broken, slow, and completely terrible.")
    assert neg["sentiment"] == "negative"
    assert neg["polarity"] < 0

def test_language_translator():
    from tools.ai_ml_tools import language_translator
    res = language_translator(text="Hello world, system ready", target_lang="es")
    assert res["status"] == "SUCCESS"
    assert "hola" in res["translated_text"].lower()

def test_code_generator_and_analyzer():
    from tools.ai_ml_tools import code_generator, code_analyzer
    code_res = code_generator(description="Calculate factorial", language="python")
    assert code_res["status"] == "SUCCESS"
    assert "def factorial" in code_res["code"]

    audit_res = code_analyzer(code=code_res["code"], language="python")
    assert audit_res["status"] == "SUCCESS"
    assert audit_res["syntax_valid"] is True


# ---------------------------------------------------------------------------
# 5. Device & Peripheral Control Tests
# ---------------------------------------------------------------------------
def test_device_controllers():
    from tools.device_control import webcam_controller, microphone_controller, gamepad_controller, monitor_controller
    with tempfile.TemporaryDirectory() as tmpdir:
        cam_path = os.path.join(tmpdir, "webcam_test.jpg")
        cam_res = webcam_controller(action="capture_photo", output_path=cam_path)
        assert cam_res["status"] == "SUCCESS"
        assert os.path.exists(cam_path)

        mic_path = os.path.join(tmpdir, "mic_test.wav")
        mic_res = microphone_controller(action="record", duration_sec=0.1, output_path=mic_path)
        assert mic_res["status"] == "SUCCESS"
        assert os.path.exists(mic_path)

    gp_res = gamepad_controller(action="status")
    assert gp_res["status"] == "SUCCESS"

    mon_res = monitor_controller(action="status")
    assert mon_res["status"] == "SUCCESS"


# ---------------------------------------------------------------------------
# 6. Security & Privacy Tests
# ---------------------------------------------------------------------------
def test_encryption_tools_roundtrip():
    from tools.security_tools import encryption_tools
    with tempfile.TemporaryDirectory() as tmpdir:
        orig_file = os.path.join(tmpdir, "secret.txt")
        with open(orig_file, "w", encoding="utf-8") as f:
            f.write("Top secret cryptographic payload.")

        enc_file = os.path.join(tmpdir, "secret.txt.enc")
        dec_file = os.path.join(tmpdir, "secret.dec.txt")

        # Encrypt
        enc_res = encryption_tools(action="encrypt", input_path=orig_file, output_path=enc_file, passphrase="my_secure_pass")
        assert enc_res["status"] == "SUCCESS"
        assert os.path.exists(enc_file)

        # Decrypt
        dec_res = encryption_tools(action="decrypt", input_path=enc_file, output_path=dec_file, passphrase="my_secure_pass")
        assert dec_res["status"] == "SUCCESS"
        assert os.path.exists(dec_file)

        with open(dec_file, "r", encoding="utf-8") as f:
            dec_content = f.read()
        assert dec_content == "Top secret cryptographic payload."

def test_password_vault_and_audit():
    from tools.security_tools import password_vault, audit_logger
    store_res = password_vault(action="store", service="database_prod", username="dba_user", password="SuperSecureDbaPass1!")
    assert store_res["status"] == "SUCCESS"

    ret_res = password_vault(action="retrieve", service="database_prod")
    assert ret_res["status"] == "SUCCESS"
    assert ret_res["password"] == "SuperSecureDbaPass1!"

    aud_res = audit_logger(action="log", event_type="TEST_SECURITY", details="Test audit event")
    assert aud_res["status"] == "SUCCESS"
    assert len(aud_res["hash"]) == 64


# ---------------------------------------------------------------------------
# 7. Communication & Messaging Tests
# ---------------------------------------------------------------------------
def test_communication_tools():
    from tools.communication_tools import telegram_bot, slack_integration, sms_sender, notification_system
    tg = telegram_bot(action="send_message", message="Test Telegram")
    assert tg["status"] == "SUCCESS"

    slk = slack_integration(action="post_message", message="Test Slack")
    assert slk["status"] == "SUCCESS"

    sms = sms_sender(to_number="+15551234567", message="Test SMS")
    assert sms["status"] == "SUCCESS"

    notif = notification_system(title="P.H.A.S.S Test", message="Test notification message")
    assert notif["status"] == "SUCCESS"


# ---------------------------------------------------------------------------
# 8. Storage & Backup Tests
# ---------------------------------------------------------------------------
def test_storage_backup_and_cleaner():
    from tools.storage_backup import backup_manager, disk_cleaner, data_recovery
    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "src_data")
        os.makedirs(src)
        with open(os.path.join(src, "report.txt"), "w") as f:
            f.write("Backup test content.")

        b_dir = os.path.join(tmpdir, "out_backups")
        b_res = backup_manager(action="create", source_dirs=[src], backup_dir=b_dir)
        assert b_res["status"] == "SUCCESS"
        assert b_res["files_backed_up"] == 1

    clean_preview = disk_cleaner(dry_run=True)
    assert clean_preview["status"] == "SUCCESS"
    assert clean_preview["dry_run"] is True

    rec_res = data_recovery(action="search_recycle_bin")
    assert rec_res["status"] == "SUCCESS"


# ---------------------------------------------------------------------------
# 9. Enhanced Memory & Learning Tests
# ---------------------------------------------------------------------------
def test_memory_enhancement():
    from tools.memory_enhancement import vector_memory, conversation_context, pattern_learning, knowledge_graph
    # Vector memory
    v_add = vector_memory(action="store", text="PostgreSQL connection strings require host, port, user, and database.")
    assert v_add["status"] == "SUCCESS"

    v_query = vector_memory(action="retrieve", query="database connection strings")
    assert v_query["status"] == "SUCCESS"
    assert len(v_query["memories"]) > 0

    # Knowledge Graph
    kg_res = knowledge_graph(action="add", subject="Llama3", predicate="powers", object_="PHASS_Sphere")
    assert kg_res["status"] == "SUCCESS"

    kg_find = knowledge_graph(action="query", subject="Llama3")
    assert kg_find["status"] == "SUCCESS"
    assert any(t["object"] == "PHASS_Sphere" for t in kg_find["results"])


# ---------------------------------------------------------------------------
# 10. Game & Entertainment Tests
# ---------------------------------------------------------------------------
def test_games_and_fun():
    from tools.game_tools import game_controller, joke_generator, story_generator, trivia_game
    # Tic-tac-toe
    game_controller(game_name="tictactoe", action="reset")
    move_res = game_controller(game_name="tictactoe", action="move", move=4)  # center
    assert move_res["status"] == "SUCCESS"
    assert move_res["board"][4] == "X"

    # Joke
    joke = joke_generator(category="tech")
    assert joke["status"] == "SUCCESS"
    assert "setup" in joke and "punchline" in joke

    # Story
    story = story_generator(prompt="A voyage through the event horizon")
    assert story["status"] == "SUCCESS"
    assert story["word_count"] > 30

    # Trivia
    triv = trivia_game(action="question", question_id=0)
    assert triv["status"] == "SUCCESS"
    assert len(triv["options"]) == 4


# ---------------------------------------------------------------------------
# 11. Development Tools Tests
# ---------------------------------------------------------------------------
def test_dev_tools():
    from tools.dev_tools import compiler_runner, json_validator, regex_helper, port_scanner
    # Python code execution
    exec_res = compiler_runner(language="python", code="print(7 * 6)")
    assert exec_res["status"] == "SUCCESS"
    assert exec_res["stdout"].strip() == "42"

    # JSON validator
    val_res = json_validator(json_str_or_file='{"name": "P.H.A.S.S", "version": 8.0}')
    assert val_res["status"] == "SUCCESS"
    assert val_res["valid"] is True

    # Regex helper
    reg_res = regex_helper(pattern=r'\d{3}-\d{4}', test_string="Call 555-1234 now.", action="search")
    assert reg_res["status"] == "SUCCESS"
    assert reg_res["matched"] is True
    assert reg_res["match_text"] == "555-1234"

    # Port scanner (scans localhost port 11434/8000 safely)
    p_res = port_scanner(host="127.0.0.1", ports=[11434], timeout=0.1)
    assert p_res["status"] == "SUCCESS"


# ---------------------------------------------------------------------------
# 12. IoT & Home Automation Tests
# ---------------------------------------------------------------------------
def test_iot_home():
    from tools.iot_home import home_assistant, philips_hue, temperature_sensor, smart_plug
    ha = home_assistant(action="turn_on", entity_id="light.office")
    assert ha["status"] == "SUCCESS"

    hue = philips_hue(action="set", light_id=2, brightness=240)
    assert hue["status"] == "SUCCESS"

    temp = temperature_sensor(sensor_id="ambient_office")
    assert temp["status"] == "SUCCESS"
    assert temp["temperature_celsius"] > 0

    plug = smart_plug(action="turn_on", plug_id="workstation_plug")
    assert plug["status"] == "SUCCESS"
    assert plug["power_state"] == "ON"


# ---------------------------------------------------------------------------
# 13. System Diagnostics & Remediation Tests
# ---------------------------------------------------------------------------
def test_diagnostics():
    from tools.diagnostics import performance_monitor, health_checker, automated_repair
    perf = performance_monitor()
    assert perf["status"] == "SUCCESS"
    assert "cpu_usage_pct" in perf

    health = health_checker()
    assert health["status"] == "SUCCESS"
    assert health["health_score"] > 0

    repair = automated_repair(issue_type="dns")
    assert repair["status"] == "SUCCESS"
    assert repair["resolved"] is True


# ---------------------------------------------------------------------------
# 14. Multi-Language Support Tests
# ---------------------------------------------------------------------------
def test_language_tools():
    from tools.language_tools import language_detector, localized_commands, interface_translation
    det_es = language_detector("Hola amigo, como esta el sistema?")
    assert det_es["status"] == "SUCCESS"
    assert det_es["detected_language"] == "es"

    det_en = language_detector("This is a standard English instruction.")
    assert det_en["status"] == "SUCCESS"
    assert det_en["detected_language"] == "en"

    cmd_trans = localized_commands("apagar sistema ahora")
    assert cmd_trans["is_localized"] is True
    assert "shutdown" in cmd_trans["normalized_directive"]

    ui = interface_translation(target_lang="es")
    assert ui["status"] == "SUCCESS"
    assert "Bienvenido" in ui["localized_ui"]["welcome"]


# ---------------------------------------------------------------------------
# 15. Advanced Automation Tests
# ---------------------------------------------------------------------------
def test_automation_tools():
    from tools.automation_tools import macro_recorder, form_filler, workflow_builder, webhook_listener
    m_rec = macro_recorder(action="record", macro_name="quick_refresh", steps=[{"type": "key", "key": "f5"}])
    assert m_rec["status"] == "SUCCESS"

    m_play = macro_recorder(action="play", macro_name="quick_refresh")
    assert m_play["status"] == "SUCCESS"
    assert m_play["playback_state"] == "COMPLETED"

    f_fill = form_filler()
    assert f_fill["status"] == "SUCCESS"
    assert f_fill["fields_populated"] > 0

    wh = webhook_listener(action="status")
    assert wh["status"] == "SUCCESS"
    assert "http" in wh["url"]


# ---------------------------------------------------------------------------
# 16. User Experience (UX) Tests
# ---------------------------------------------------------------------------
def test_ux_tools():
    from tools.ux_tools import profiles_manager, privacy_mode, auto_complete, undo_redo, bookmarks_manager
    prof = profiles_manager(action="switch", profile_name="developer")
    assert prof["status"] == "SUCCESS"
    assert prof["switched_to"] == "developer"

    priv_on = privacy_mode(action="enable")
    assert priv_on["status"] == "SUCCESS"
    assert priv_on["privacy_mode"] is True

    priv_off = privacy_mode(action="disable")
    assert priv_off["privacy_mode"] is False

    ac = auto_complete(prefix="system")
    assert ac["status"] == "SUCCESS"
    assert len(ac["suggestions"]) > 0

    bkm = bookmarks_manager(action="save", name="clean_disk_routine", command="disk_cleaner dry_run=False")
    assert bkm["status"] == "SUCCESS"

    undo = undo_redo(action="record", record_action={"type": "file_move", "file": "test.txt"})
    assert undo["status"] == "SUCCESS"
    undo_pop = undo_redo(action="undo")
    assert undo_pop["status"] == "SUCCESS"


# ---------------------------------------------------------------------------
# 17. End-to-End Llama Agent Semantic Dispatch & Reasoning Tests
# ---------------------------------------------------------------------------
def test_llama_agent_cross_domain_reasoning():
    agent = llama_tool_agent

    # 1. Performance Diagnostics dispatch
    res_diag = agent.run_turn("Check cpu usage and performance monitor")
    assert res_diag.success is True
    assert any(s.tool_name == "performance_monitor" for s in res_diag.steps_executed)

    # 2. Antivirus security dispatch
    res_av = agent.run_turn("Scan directory for malware with antivirus")
    assert res_av.success is True
    assert any(s.tool_name == "antivirus_scanner" for s in res_av.steps_executed)

    # 3. Joke entertainment dispatch
    res_joke = agent.run_turn("Tell me a joke")
    assert res_joke.success is True
    assert any(s.tool_name == "joke_generator" for s in res_joke.steps_executed)

    # 4. Git developer tools dispatch
    res_git = agent.run_turn("Check git status of repository")
    assert res_git.success is True
    assert any(s.tool_name == "git_manager" for s in res_git.steps_executed)

    # 5. Disk cleaner storage dispatch
    res_clean = agent.run_turn("Clean temp files with disk cleaner")
    assert res_clean.success is True
    assert any(s.tool_name == "disk_cleaner" for s in res_clean.steps_executed)

    # 6. Sentiment analysis dispatch
    res_sent = agent.run_turn("Analyze sentiment of: This product is incredibly fast and reliable")
    assert res_sent.success is True
    assert any(s.tool_name == "sentiment_analyzer" for s in res_sent.steps_executed)
