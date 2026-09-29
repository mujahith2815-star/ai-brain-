"""
RAG Pipeline Unit Tests for P.H.A.S.S Sphere.
Validates context retrieval, hybrid search across SQLite and VectorStore,
and augmented prompt generation.
"""

from __future__ import annotations
import pytest
from knowledge.sqlite_store import KnowledgeStore
from knowledge.vector_store import VectorStore
from core.rag_pipeline import RAGPipeline


def test_rag_pipeline_hybrid_context(tmp_path):
    """Verify RAG pipeline pulls both vector documents and structured SQLite facts."""
    vec_path = str(tmp_path / "hybrid_vec.json")
    db_path = str(tmp_path / "hybrid_facts.db")

    vs = VectorStore(store_path=vec_path)
    ks = KnowledgeStore(db_path=db_path)
    try:
        # Ingest document
        vs.add_document("The user is lactose intolerant and avoids whole milk products.", source="diet_notes.txt")
        # Ingest structured fact
        ks.store_fact("dairy_preference", "lactose intolerant", category="health")

        rag = RAGPipeline(vector_store=vs, sql_store=ks)
        context = rag.retrieve_context("dairy milk notes")

        assert context is not None
        assert "diet_notes.txt" in context
        assert "lactose intolerant" in context

        # Augmented prompt
        prompt = rag.build_augmented_prompt("What milk should I buy?")
        assert "You have access to the following knowledge:" in prompt
        assert "diet_notes.txt" in prompt
    finally:
        ks.close()


def test_rag_empty_fallback(tmp_path):
    """Verify RAG pipeline returns exact user query when no facts or docs match."""
    vec_path = str(tmp_path / "empty_vec.json")
    db_path = str(tmp_path / "empty_facts.db")

    vs = VectorStore(store_path=vec_path)
    ks = KnowledgeStore(db_path=db_path)
    try:
        rag = RAGPipeline(vector_store=vs, sql_store=ks)
        q = "random question with zero hits"
        assert rag.retrieve_context(q) is None
        assert rag.build_augmented_prompt(q) == q
    finally:
        ks.close()
