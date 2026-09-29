"""
Tests for Mind Palace persistent hybrid SQLite + ChromaDB memory system.
"""

import os
import pytest
from pathlib import Path
from core.mind_palace import MindPalace


@pytest.fixture
def temp_mind_palace(tmp_path):
    palace = MindPalace(memory_path=str(tmp_path / "mind_palace_test"))
    return palace


def test_mind_palace_init(temp_mind_palace):
    assert temp_mind_palace.db_path.exists()
    assert temp_mind_palace.memory_path.exists()


def test_conversation_storage_and_search(temp_mind_palace):
    row_id = temp_mind_palace.store_conversation(
        session_id="sess_001",
        user_msg="Please optimize my PostgreSQL database queries and indexes.",
        assistant_msg="I have analyzed your PostgreSQL slow query log and added compound B-Tree indexes.",
        metadata={"domain": "database"},
    )
    assert row_id > 0

    # Search by keyword
    results = temp_mind_palace.search_memory("PostgreSQL indexes", n_results=5)
    assert len(results) >= 1
    assert "postgresql" in results[0]["content"].lower()
    assert results[0]["score"] > 0


def test_preferences_storage_and_retrieval(temp_mind_palace):
    temp_mind_palace.store_user_preference("coding", "preferred_language", "Python")
    temp_mind_palace.store_user_preference("coding", "tabs_or_spaces", "spaces")
    temp_mind_palace.store_user_preference("ui", "theme", "dark")

    all_prefs = temp_mind_palace.get_user_preferences()
    assert "coding" in all_prefs
    assert all_prefs["coding"]["preferred_language"] == "Python"
    assert all_prefs["ui"]["theme"] == "dark"

    coding_prefs = temp_mind_palace.get_user_preferences(category="coding")
    assert coding_prefs["tabs_or_spaces"] == "spaces"


def test_tool_logging_and_pattern_learning(temp_mind_palace):
    for _ in range(3):
        temp_mind_palace.log_tool_execution(
            tool_name="git_manager",
            inputs={"action": "status"},
            output={"clean": True},
            success=True,
        )

    temp_mind_palace.log_tool_execution(
        tool_name="docker_manager",
        inputs={"action": "ps"},
        output={"containers": 2},
        success=True,
    )

    patterns = temp_mind_palace.get_learned_patterns(top_n=5)
    tool_keys = [p["pattern_key"] for p in patterns]
    assert "tool_usage:git_manager" in tool_keys
    git_pattern = next(p for p in patterns if p["pattern_key"] == "tool_usage:git_manager")
    assert git_pattern["frequency"] == 3
    assert git_pattern["confidence"] > 0.5


def test_knowledge_graph_triplets(temp_mind_palace):
    temp_mind_palace.store_knowledge_triple("Python", "is_created_by", "Guido van Rossum")
    temp_mind_palace.store_knowledge_triple("Python", "supports", "Asyncio")
    temp_mind_palace.store_knowledge_triple("FastAPI", "built_on", "Starlette")

    res_python = temp_mind_palace.query_knowledge_graph(subject="python")
    assert len(res_python) == 2
    predicates = [r["predicate"] for r in res_python]
    assert "is_created_by" in predicates
    assert "supports" in predicates

    res_fastapi = temp_mind_palace.query_knowledge_graph(subject="fastapi")
    assert len(res_fastapi) == 1
    assert res_fastapi[0]["object"] == "starlette"


def test_document_ingestion(temp_mind_palace, tmp_path):
    doc_file = tmp_path / "architecture.md"
    doc_file.write_text(
        "# P.H.A.S.S Sphere Architecture\n\n"
        "The cognitive engine coordinates multi-agent dispatching.\n\n"
        "The mind palace coordinates long-term memory across sessions.\n\n"
        "Shadow mode prevents catastrophic command execution.\n",
        encoding="utf-8",
    )

    ingest_res = temp_mind_palace.ingest_document(str(doc_file))
    assert ingest_res["status"] == "SUCCESS"
    assert ingest_res["chunks_indexed"] >= 3
