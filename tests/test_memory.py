import pytest
import os
from core.memory_master import (
    memory_master,
    semantic_search,
    ingest_document,
    add_knowledge_triplet,
    query_knowledge_graph,
    record_pattern,
    predict_next_action,
    get_project_memory,
    save_project_memory,
)


def test_document_ingestion_and_semantic_search():
    test_file = "memory_vault/test_article.txt"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("Quantum computing leverages superposition and entanglement to solve hard computational problems.")

    res = ingest_document(test_file, project="quantum_research")
    assert res["status"] == "SUCCESS"
    assert res["chunks_created"] >= 1

    search_res = semantic_search("superposition entanglement quantum", top_k=3, project="quantum_research")
    assert len(search_res) >= 1
    assert "superposition" in search_res[0]["content"]


def test_knowledge_graph_triplets():
    tid = add_knowledge_triplet("Llama3", "supports", "Tool Calling", project="models")
    assert tid.startswith("kg-")

    results = query_knowledge_graph(subject="Llama3", project="models")
    assert len(results) >= 1
    assert results[0]["predicate"] == "supports"
    assert results[0]["object"] == "Tool Calling"


def test_pattern_learning_and_prediction():
    record_pattern("compile_code", "debugging")
    record_pattern("execute_tests", "verification")
    pred = predict_next_action("compile_code")
    assert "predicted_action" in pred
    assert pred["confidence"] > 0


def test_isolated_project_memory():
    save_project_memory("secret_agent", {"mission": "protect_core", "status": "active"})
    mem = get_project_memory("secret_agent")
    assert mem.get("mission") == "protect_core"
    assert mem.get("status") == "active"