"""
Unit & Integration Tests for Voice Customizer, Document Ingestor, and Universal File Editor Suite.
"""

import os
import tempfile
import pytest
from voice.voice_customizer import voice_customizer, VoicePersonaType
from memory.document_ingestor import document_ingestor
from tools.universal_file_editor import universal_file_editor
from nlp.conversational_agent import conversational_agent


# 1. Voice Customizer Engine
def test_voice_customizer_personas_and_rates():
    # Switch to Cyber Android
    p_android = voice_customizer.set_persona("cyber android")
    assert p_android.persona == VoicePersonaType.CYBER_ANDROID
    assert p_android.speech_rate_wpm == 190

    # Switch to Deep Sentinel
    p_sentinel = voice_customizer.set_persona("deep sentinel")
    assert p_sentinel.persona == VoicePersonaType.DEEP_SENTINEL

    # Calibrate rate and volume
    new_rate = voice_customizer.set_speech_rate(210)
    assert new_rate == 210
    new_vol = voice_customizer.set_speech_volume(85)
    assert new_vol == 85

    txt = voice_customizer.format_voice_status_text()
    assert "VOICE CUSTOMIZER" in txt


# 2. Document & Codebase Vector Ingestor
def test_document_ingestor_file_and_search():
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write("# Autonomous Navigation Subsystem\n")
        f.write("def calculate_trajectory(pos, target):\n")
        f.write("    return (target[0] - pos[0], target[1] - pos[1])\n")
        tmp_path = f.name

    try:
        summary = document_ingestor.ingest_file(tmp_path)
        assert summary.total_chunks_created >= 1
        assert summary.file_type == ".py"
        assert len(summary.vector_doc_ids) >= 1

        # Search ingested document
        results = document_ingestor.search_ingested_documents("calculate trajectory target", top_k=2)
        assert len(results) >= 1
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# 3. Universal File Viewer & Hex Dumper
def test_universal_file_viewer_and_hex():
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("Line 1: System Boot\nLine 2: LiDAR 360 Scan\nLine 3: Kinematics Ready\n")
        tmp_path = f.name

    try:
        # 1. View slice
        view = universal_file_editor.view_file_content(tmp_path, start_line=1, end_line=2)
        assert view.total_lines == 3
        assert "Line 1: System Boot" in view.content
        assert len(view.sha256_hash) == 64

        # 2. Hex dump
        hex_dump = universal_file_editor.generate_hex_dump(tmp_path, max_bytes=32)
        assert "HEX DUMP:" in hex_dump
        assert "00000000 |" in hex_dump
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# 4. CSV Table View & Surgical Replace
def test_csv_table_and_surgical_replace():
    # CSV Table
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
        f.write("ID,Name,Role,Status\n1,Alpha,Scout,Active\n2,Beta,Worker,Active\n")
        csv_path = f.name

    try:
        csv_view = universal_file_editor.view_csv_table_preview(csv_path)
        assert "CSV TABLE PREVIEW:" in csv_view
        assert "Alpha" in csv_view

        # Surgical Replace
        edit_res = universal_file_editor.edit_file_replace(csv_path, "Alpha", "ApexAlpha", create_backup=True)
        assert edit_res.success is True
        assert edit_res.changes_made_count == 1
        assert edit_res.backup_file_path is not None
        assert os.path.exists(edit_res.backup_file_path)

        # Verify content replaced
        new_content = open(csv_path).read()
        assert "ApexAlpha" in new_content
    finally:
        if os.path.exists(csv_path):
            os.remove(csv_path)
        if os.path.exists(csv_path + ".bak"):
            os.remove(csv_path + ".bak")


# 5. Conversational Directives for Voice, Docs, and Editor
def test_conversational_voice_docs_editor():
    # A. Set Voice Persona
    res_voice = conversational_agent.handle_natural_conversation("set voice persona to Cyber Android")
    assert res_voice is not None
    assert res_voice["type"] == "VOICE_PERSONA_CHANGE"

    # B. Set Voice Speed
    res_spd = conversational_agent.handle_natural_conversation("set voice speed to 200 wpm")
    assert res_spd is not None
    assert res_spd["type"] == "VOICE_SPEED_CHANGE"
