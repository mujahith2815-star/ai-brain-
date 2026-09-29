"""
Knowledge Tools Tests for P.H.A.S.S Sphere.
Validates remember_fact, recall_fact, add_to_list, get_list, search_documents,
and ingest_document execution via tools/knowledge_tools.py.
"""

from __future__ import annotations
import os
import pytest
from tools.knowledge_tools import (
    remember_fact,
    recall_fact,
    add_to_list,
    get_list,
    search_documents,
    ingest_document,
    ask_with_knowledge,
)


def test_remember_and_recall_facts():
    """Validates storing and retrieving structured facts."""
    res_store = remember_fact("workstation_os", "Windows 11 Pro", category="system")
    assert res_store["status"] == "SUCCESS"

    res_recall = recall_fact("workstation_os")
    assert res_recall["status"] == "SUCCESS"
    assert "Windows 11" in str(res_recall["value"])


def test_custom_lists_operations():
    """Validates user-defined list manipulation."""
    res_add = add_to_list("project_todos", "Implement RAG pipeline", quantity=1, notes="High priority")
    assert res_add["status"] == "SUCCESS"

    res_list = get_list("project_todos")
    assert res_list["status"] == "SUCCESS"
    assert res_list["count"] >= 1
    items = [it["item"] for it in res_list["items"]]
    assert "Implement RAG pipeline" in items


def test_document_ingest_and_search(tmp_path):
    """Validates ingesting a document file and querying it via search_documents."""
    doc_path = tmp_path / "spec.txt"
    doc_path.write_text("Antigravity orchestrates autonomous subagents with deep tool-calling pipelines.", encoding="utf-8")

    res_ingest = ingest_document(str(doc_path))
    assert res_ingest["status"] == "SUCCESS"
    assert res_ingest["chunks_added"] >= 1

    res_search = search_documents("autonomous subagents", top_k=1)
    assert res_search["status"] == "SUCCESS"
    assert len(res_search["results"]) > 0


def test_ask_with_knowledge_wrapper():
    """Validates the ask_with_knowledge tool helper."""
    res = ask_with_knowledge("General system inquiry")
    assert res["status"] == "SUCCESS"
    assert "augmented_prompt" in res
