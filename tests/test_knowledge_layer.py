"""
Unit and Integration Tests for P.H.A.S.S Sphere Knowledge Layer.
Validates SQLite persistent memory, VectorStore semantic retrieval,
RAG context augmentation, FileWatcher auto-ingestion, and tool registrations.
"""

from __future__ import annotations
import os
import pytest
from pathlib import Path
from knowledge.sqlite_store import KnowledgeStore
from knowledge.vector_store import VectorStore
from knowledge.file_watcher import FileWatcher
from core.rag_pipeline import RAGPipeline
from tools.knowledge_tools import (
    remember_fact,
    recall_fact,
    add_to_list,
    get_list,
    search_documents,
    ingest_document,
)
import tools.builtin_tools
from tools.registry import tool_registry


def test_sqlite_store_fact_roundtrip(tmp_path):
    """Store then retrieve a fact from KnowledgeStore."""
    db_file = str(tmp_path / "test_agent_memory.db")
    ks = KnowledgeStore(db_path=db_file)
    try:
        # Store fact
        res_store = ks.store_fact("user_name", "Alex", category="personal")
        assert res_store["status"] == "SUCCESS"
        assert res_store["key"] == "user_name"

        # Retrieve fact
        fact = ks.get_fact("user_name")
        assert fact is not None
        assert fact == "Alex"
        assert fact["value"] == "Alex"
        assert fact["status"] == "SUCCESS"
        assert fact["category"] == "personal"

        # Non-existent fact
        assert ks.get_fact("non_existent_key_123") is None

        # Search facts
        search_res = ks.search_facts("Alex")
        assert len(search_res) == 1
        assert search_res[0]["key"] == "user_name"
    finally:
        ks.close()


def test_sqlite_store_list_operations(tmp_path):
    """Add items to user list and retrieve list."""
    db_file = str(tmp_path / "test_lists.db")
    ks = KnowledgeStore(db_path=db_file)
    try:
        r1 = ks.add_to_list("shopping", "milk", quantity=2, notes="almond milk")
        assert r1["status"] == "SUCCESS"
        r2 = ks.add_to_list("shopping", "eggs", quantity=12, notes="organic")
        assert r2["status"] == "SUCCESS"

        items = ks.get_list("shopping")
        assert items["status"] == "SUCCESS"
        assert len(items) == 2
        item_names = [it["item"] for it in items]
        assert "milk" in item_names
        assert "eggs" in item_names
        assert items[0]["quantity"] in (2, 12)
    finally:
        ks.close()


def test_vector_store_add_and_search(tmp_path):
    """Add a document chunk to VectorStore and verify semantic retrieval."""
    vec_file = str(tmp_path / "test_vector.json")
    vs = VectorStore(store_path=vec_file)

    doc_text = "The capital of France is Paris, famous for the Eiffel Tower and Louvre Museum."
    res = vs.add_document(doc_text, source="france_guide.txt")
    assert res["status"] == "SUCCESS"
    assert res["chunks_added"] >= 1
    assert os.path.exists(vec_file)

    # Search with semantic query
    results = vs.search("What is the French capital?", top_k=2)
    assert len(results) > 0
    assert results[0]["source"] == "france_guide.txt"
    assert "Paris" in results[0]["text"]
    assert results[0]["score"] > 0.3


def test_vector_store_empty_search(tmp_path):
    """Searching an empty VectorStore returns an empty list."""
    vec_file = str(tmp_path / "empty_vector.json")
    vs = VectorStore(store_path=vec_file)
    results = vs.search("any query")
    assert results == []


def test_rag_pipeline_with_documents(tmp_path):
    """RAG pipeline injects retrieved document and fact context into augmented prompt."""
    vec_file = str(tmp_path / "rag_vector.json")
    db_file = str(tmp_path / "rag_facts.db")

    vs = VectorStore(store_path=vec_file)
    vs.add_document("Deep neural networks rely on backpropagation for training.", source="dl_guide.md")

    ks = KnowledgeStore(db_path=db_file)
    try:
        ks.store_fact("preferred_framework", "PyTorch", category="coding")

        rag = RAGPipeline(vector_store=vs, sql_store=ks)
        augmented = rag.build_augmented_prompt("Tell me about neural networks and framework")

        assert "You have access to the following knowledge:" in augmented
        assert "neural networks" in augmented
        assert "dl_guide.md" in augmented
        assert "Based on the above, answer the user's question:" in augmented
    finally:
        ks.close()


def test_rag_pipeline_without_context(tmp_path):
    """RAG pipeline returns the raw query unchanged if no relevant context exists."""
    vec_file = str(tmp_path / "empty_rag_vector.json")
    db_file = str(tmp_path / "empty_rag_facts.db")

    vs = VectorStore(store_path=vec_file)
    ks = KnowledgeStore(db_path=db_file)
    try:
        rag = RAGPipeline(vector_store=vs, sql_store=ks)
        raw_query = "xyzzy_unmatched_nonsense_token_987654"
        augmented = rag.build_augmented_prompt(raw_query)
        assert augmented == raw_query
    finally:
        ks.close()


def test_knowledge_tools_registered():
    """Verify all 6 required knowledge tools are registered in tool_registry."""
    expected_tools = [
        "remember_fact",
        "recall_fact",
        "add_to_list",
        "get_list",
        "search_documents",
        "ingest_document",
    ]
    for tool_name in expected_tools:
        assert tool_registry.has_tool(tool_name), f"Tool {tool_name} is not registered in tool_registry!"


def test_remember_and_recall_via_tools():
    """End-to-end fact storage and retrieval using standalone tool functions."""
    res_store = remember_fact("favorite_color", "cerulean", category="preferences")
    assert res_store["status"] == "SUCCESS"

    res_recall = recall_fact("favorite_color")
    assert res_recall["status"] == "SUCCESS"
    assert res_recall["value"] == "cerulean"

    # Non-existent recall
    res_missing = recall_fact("unknown_phantom_key_9999")
    assert res_missing["status"] == "NOT_FOUND"


def test_file_watcher_ingest(tmp_path):
    """FileWatcher scans inbox, ingests new supported files, and ignores already processed."""
    inbox_dir = tmp_path / "inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    vec_file = str(tmp_path / "watcher_vec.json")

    vs = VectorStore(store_path=vec_file)
    watcher = FileWatcher(watch_dir=str(inbox_dir), vector_store=vs)

    # Drop a file into inbox
    sample_file = inbox_dir / "knowledge_intro.txt"
    sample_file.write_text("Orvix Sphere Knowledge Layer provides persistent facts and semantic RAG.", encoding="utf-8")

    # Initial scan
    results = watcher.scan_and_ingest()
    assert len(results) == 1
    assert results[0]["status"] == "SUCCESS"
    assert results[0]["source"] == "knowledge_intro.txt"

    # Search in vector store
    search_res = vs.search("persistent facts")
    assert len(search_res) > 0
    assert "knowledge_intro.txt" in search_res[0]["source"]

    # Re-scan: should not re-ingest already processed file
    subsequent_results = watcher.scan_and_ingest()
    assert len(subsequent_results) == 0


def test_vector_store_persistence_roundtrip(tmp_path):
    """Verify document chunks persist across instances and are searchable after reload."""
    if tmp_path:
        vec_file = str(tmp_path / "persist_test.json")
        vs1 = VectorStore(store_path=vec_file)
        vs1.add_document('Persistent test content', source='persist.txt')
        vs2 = VectorStore(store_path=vec_file)
        results = vs2.search('Persistent test', top_k=1)
        assert len(results) > 0
        assert 'Persistent test content' in results[0]['text']
    else:
        vs1 = VectorStore()
        try:
            vs1.add_document('Persistent test content', source='persist.txt')
            vs2 = VectorStore()
            results = vs2.search('Persistent test', top_k=1)
            assert len(results) > 0
            assert 'Persistent test content' in results[0]['text']
        finally:
            vs1.remove_source('persist.txt')
            vs2.remove_source('persist.txt')


def test_vector_store_survives_corrupt_file(tmp_path):
    """Writing garbage to vector_store.json should not crash, returns empty, and backs up to .corrupt."""
    vec_file = tmp_path / "corrupt_test.json"
    vec_file.write_text("{ this is completely invalid json corrupt data !!!", encoding="utf-8")
    vs = VectorStore(store_path=str(vec_file))
    assert vs.num_documents() == 0
    assert vs.search("test") == []
    corrupt_backup = vec_file.with_suffix(".corrupt")
    assert corrupt_backup.exists()


def test_vector_store_handles_empty_file(tmp_path):
    """Writing empty string to vector_store.json should not crash and loads cleanly."""
    vec_file = tmp_path / "empty_test.json"
    vec_file.write_text("", encoding="utf-8")
    vs = VectorStore(store_path=str(vec_file))
    assert vs.num_documents() == 0
    assert vs.search("test") == []


def test_num_documents_increments(tmp_path):
    """Verify num_documents returns correct counts and increments as documents are added."""
    vec_file = str(tmp_path / "increment_test.json")
    vs = VectorStore(store_path=vec_file)
    initial_count = vs.num_documents()
    assert initial_count == 0
    vs.add_document("Document one content", source="doc1.txt")
    vs.add_document("Document two content", source="doc2.txt")
    vs.add_document("Document three content", source="doc3.txt")
    assert vs.num_documents() == initial_count + 3
